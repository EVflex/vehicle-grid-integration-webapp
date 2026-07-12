# IMPROVEMENTS.md — critique and improvement instructions (do not implement yet)

Reviewed 2026-07-11 (Fable). This file is a critique of the **current state of
the new backend** (`vgi_api/`) plus instructions for improvements, mainly
architectural improvements and security enhancements for running the site on
the public internet. **Nothing in this file is implemented** — it is a to-do
list for a future pass. Items are ordered by priority within each section.

Context for the reviewer's verdict: the new backend was verified against the
original (`..._v0`) — 133/133 tests pass, and the regression harness shows all
8 numeric scenarios match the captured v0 baseline to ~5e-10 relative
difference (solver-stack noise; OpenDSS's own tolerance is 1e-4). The physics
is unchanged. The items below are about robustness, security, and
maintainability — not correctness.

---

## 1. Security — do these before (or at) public launch

### 1.1 Make abuse protection deployment-independent (HIGH)
**Where:** `vgi_api/vgi_api/main.py`.
**Problem:** one `/simulate` request costs ~1–2 s of CPU and ~400 MB RAM in a
worker. The only rate limit today lives in `deployment/Caddyfile` (the
compiled-in `rate_limit` plugin). If the API is ever deployed any other way —
Azure Functions, a bare `docker run`, a different reverse proxy — there is
**no** brake at all: anyone can saturate the worker pool with a `for` loop.
**Instruction:** add app-level per-IP rate limiting on `POST /simulate`
(e.g. the `slowapi` package, or a 10-line token-bucket dependency keyed on
`request.client.host` honouring `X-Forwarded-For` only from a trusted proxy).
Keep the Caddy limit too — defence in depth.

### 1.2 Cap the simulation queue (HIGH)
**Where:** `main.py`, `_run_simulation_in_subprocess`.
**Problem:** requests beyond `VGI_MAX_PARALLEL_SIMULATIONS` queue FIFO with no
bound. A burst of N requests holds N event-loop tasks and N pickled parameter
sets (each embedding up to six 48-row profile arrays) in memory for up to
`N × timeout` seconds. Combined with 1.1 this is the DoS surface.
**Instruction:** track in-flight + queued jobs with an `asyncio.Semaphore`
(size ≈ 2× pool size); when exhausted return **429 Too Many Requests** with a
`Retry-After` header instead of queueing. The frontend already surfaces error
banners, so a clean 429 is user-visible.

### 1.3 Kill timed-out worker jobs instead of abandoning them (MEDIUM)
**Where:** `main.py`, timeout branch of `_run_simulation_in_subprocess`.
**Problem:** on timeout with a multi-worker pool the abandoned job keeps
occupying a slot until it finishes "on its own" (it may never). Repeated
timeouts can exhaust every slot, and 1.2's queue cap would then reject
everyone. The single-worker case is handled (pool disposal) but that cancels
nothing on multi-worker pools.
**Instruction:** replace `concurrent.futures.ProcessPoolExecutor` with a pool
that supports per-job timeout kill (the `pebble` package's `ProcessPool` does
exactly this), or record each worker's PID (via an initializer writing to a
shared dict) and `SIGKILL` the specific worker on timeout, letting the pool
respawn it.

### 1.4 Run the container as a non-root user (MEDIUM)
**Where:** `docker_images/vgi_api.dockerfile`.
**Problem:** no `USER` directive — gunicorn and the OpenDSS engine run as
root inside the container. Any code-execution bug becomes root-in-container.
**Instruction:** create an unprivileged user (`useradd --system app`), `USER
app`, and bind to port 8000+ (non-privileged) — adjust the compose file /
Caddy upstream accordingly. Consider `read_only: true` +
`tmpfs: /tmp` in `deployment/docker-compose.yml` (the app writes only to the
temp dir and the network cache, both under `/tmp`).

### 1.5 Harden the shared network-model cache path (MEDIUM on shared hosts, LOW in containers)
**Where:** `funcsTuring.py`, `_NETWORK_CACHE_ROOT = Path(tempfile.gettempdir()) / "vgi_network_cache"`.
**Problem:** a fixed, predictable path in the world-writable system temp dir.
On a multi-user host, another local user can pre-create
`/tmp/vgi_network_cache/1060` with **modified network models**, silently
changing simulation results (the code trusts any existing cache dir). Inside
a single-tenant container this is a non-issue, but the code shouldn't assume
its deployment.
**Instruction:** either (a) place the cache under the package/app directory
or an env-configurable `VGI_CACHE_DIR` with `0700` permissions and verify
ownership before trusting it, or (b) verify content integrity — record the
zip's SHA-256 in a marker file on extraction and re-extract on mismatch.

### 1.6 Keep the dependency chain auditable (MEDIUM)
**Where:** `vgi_api/pyproject.toml` (no lock file — `poetry.lock` was
deliberately deleted when the pins changed).
**Problem:** ranged dependencies (`fastapi>=0.115`, unpinned numpy) mean two
builds weeks apart can ship different dependency trees — bad for both
reproducibility and supply-chain review.
**Instruction:** regenerate a lock (`poetry lock`) or adopt `pip-compile`,
commit it, and make the Docker build install from the lock. Add `pip-audit`
(or GitHub Dependabot alerts) to `.github/workflows/tests.yml` so known CVEs
in the tree surface automatically.

### 1.7 Small hygiene items (LOW)
- **Security headers on the API origin:** the Caddyfile sets HSTS etc. only on
  the frontend host block; mirror `Strict-Transport-Security` and
  `X-Content-Type-Options: nosniff` on the `api.{$DOMAIN}` block.
- **Stale comment:** the Caddyfile says "The API itself caps CSV uploads at
  5 MB" — the code cap (`MAX_CSV_BYTES`, validators.py) is 10 MB. Align the
  comment (the 10 MB `request_body max_size` is correct).
- **Generic 500 body:** already good (no stack traces leak). Keep it that way
  if adding error detail — include a request ID (see 3.2), never internals.
- **`/network-topology` cache mutation:** `_load_topology` is `lru_cache`d and
  the endpoint takes a shallow `dict()` copy before adding `mv_assets`. Safe
  today, but a future edit that mutates a *nested* key would poison the cache
  for all later requests. Add a one-line comment-test or return a deep copy.
- **Authentication:** deliberately absent (anonymous public tool). If that
  ever changes, prefer an API-management layer (Azure APIM / Cloudflare) or a
  FastAPI API-key dependency over rolling your own.

---

## 2. Architecture

### 2.1 Give the research engine a narrow, typed seam (HIGH, incremental)
**Where:** `funcsTuring.py` (~2,200 lines), `slesNtwk_turing.py` (~5,900
lines, deliberately untouched), `funcsDss_turing.py`, `funcsMath_turing.py`.
**Critique:** the API sits directly on research code — three of the files
carry a "SCRIPT AUTOMATICALLY GENERATED — do not modify" header yet are now
(necessarily) modified; `turingNet` is configured through a nested run-dict
(`azureOptsXmpls.run_dict0`) that is deep-copied and mutated in `main.py`;
`d = dssIfc(dss.DSS)` is a module-level singleton shared across files. This
was the right call for preserving numerical fidelity, but every future
feature keeps threading through the same dict.
**Instruction:** do NOT rewrite the engine. Instead, extract the API-facing
surface into one small module (e.g. `vgi_api/engine.py`) exposing roughly
`build_network(params) -> Network`, `run_daily(Network) -> Solutions`,
`extract_datasets(Solutions) -> TypedResults` — with the run-dict construction
(currently inline in `main.py:simulate`) behind a typed
pydantic model. New code then depends on the seam, not the research modules;
the regression harness pins behaviour while doing it.

### 2.2 Type the /simulate response (MEDIUM)
**Where:** `main.py` (hand-built `resultdict`), consumed by both frontends.
**Critique:** the response contract lives implicitly in a dict literal and in
two Vue apps' parsing code. The v0 duplicate-key bug (`"mv_highlevel"` twice)
is exactly the class of error a typed model prevents.
**Instruction:** define a pydantic `SimulateResponse` model (fields for the
12 plot strings, the 5 CSV strings, `convergence`, `lv_phase_pngs`) and set
it as `response_model`. FastAPI then documents it in OpenAPI, and the
frontends have a schema to code against.

### 2.3 Cache identical simulation requests (MEDIUM — cheap win)
**Where:** `main.py`.
**Critique:** the simulation is fully deterministic (`rand_seed = 0`), so
identical parameters always produce identical output — the demo presets in
the new frontend make repeated identical requests likely (every user clicking
"2030 high EV" runs the same simulation).
**Instruction:** hash the canonicalised parameters (including uploaded CSV
bytes) and keep a small LRU (say 32 entries, or on-disk with TTL) of complete
response dicts. Skip caching when a CSV upload is present if memory is a
concern. This turns the common demo path into a ~0 ms response.

### 2.4 Consider moving plot rendering to the client, eventually (LOW)
**Critique:** the API returns ~12 base64 PNGs per request (payload in the
MBs) rendered by matplotlib in the worker — matplotlib rendering is now the
dominant per-request cost (~0.5 s), and the new frontend already parses the
CSV datasets client-side for its verdict cards.
**Instruction:** long-term, return the numeric datasets only (they exist for
4 of the plots already; add the remaining series) and render charts in Vue.
Keep the PNGs during the transition — the old frontend depends on them. Do
this only after 2.2 gives the contract a type.

### 2.5 Centralise configuration (LOW)
**Where:** `os.environ.get(...)` calls scattered at module import time in
`main.py` (`VGI_CORS_ORIGINS`, `VGI_SIMULATION_TIMEOUT`,
`VGI_MAX_PARALLEL_SIMULATIONS`).
**Instruction:** one `pydantic_settings.BaseSettings` class (`Settings`) with
documented defaults, instantiated once; endpoints and pool code read from it.
Also makes the values testable without monkeypatching `os.environ` before
import.

### 2.6 Split main.py (LOW)
**Critique:** `main.py` now mixes three concerns: worker-pool lifecycle, CORS
/app setup, and endpoints.
**Instruction:** when next touched, move the pool into
`vgi_api/worker_pool.py` and topology serving into `vgi_api/topology.py`;
keep `main.py` as app assembly + endpoints.

### 2.7 Plan the old frontend's retirement (LOW)
**Critique:** two full Vue apps (`src/` from 2022 with its aged npm tree, and
`event-frontend-v2/`) must both track the API contract; §16/§18-20 changes
already required verifying both.
**Instruction:** once the new frontend is signed off, archive `src/` (keep a
git tag), and make `event-frontend-v2/` the single app. Until then, run both
against the regression harness's meta-endpoint checks after any API change.

---

## 3. Operations & observability (for the deployed site)

### 3.1 Expose minimal metrics (MEDIUM)
**Instruction:** add a `/metrics` endpoint (prometheus-fastapi-instrumentator
or hand-rolled counters): simulation duration histogram, queue depth, worker
restarts (BrokenProcessPool count), timeout count, convergence-failure count
per request. These five numbers answer almost every "is it healthy?" question.

### 3.2 Structured logs with request IDs (LOW)
**Instruction:** add a middleware assigning a UUID per request, include it in
every log line (and in the generic 500 body), switch worker logs to include
the parameter hash from 2.3. Makes "user reports a failed run" debuggable.

### 3.3 Run the regression harness in CI (MEDIUM)
**Where:** `regression_harness/` (currently a manual tool), `.github/workflows/tests.yml`.
**Instruction:** add a CI job that boots the API (uvicorn on a port), runs
`vgi_regression.py capture` + `compare baselines/v0`, and fails on numeric
drift. The committed v0 baseline makes this the strongest guard the project
has — automate it so it cannot be forgotten. Expect and allowlist the two
*intentional* meta-endpoint diffs (the 4 reserved network ids).

### 3.4 Container healthcheck & restart (LOW)
**Instruction:** `deployment/docker-compose.yml` already has a healthcheck +
restart policy — mirror the same in any other deployment path the colleague
chooses (App Service health probe → `/health-check`).

---

## 4. Known accepted trade-offs (documented, not to "fix")

- **Anonymous API** — a product decision; revisit only with rate limiting in
  place (1.1/1.2).
- **Per-request OpenDSS network compilation (~0.4 s)** — the next performance
  frontier would be a resident compiled network per `(n_id, lv_list)` with
  parameter changes applied through the OpenDSS API instead of editing .dss
  text; only worth it if traffic grows (CHANGES.md §11).
- **numpy `record_solution` full=True path** still builds potentially ragged
  arrays for research use — deliberately guarded by try/except, not used by
  the API.
- **Base64-PNGs-in-JSON** — kept for old-frontend compatibility (see 2.4).
- **`slesNtwk_turing.py` untouched** — right call; it is byte-identical to
  v0, which is what makes the equivalence argument easy.
