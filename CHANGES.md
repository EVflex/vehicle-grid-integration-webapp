# Changes in this fork (2026-07-05; updated — see §8-§10, §12, §13 and §17)

This folder is a modified copy of `vehicle-grid-integration-webapp-private-main`.
The original folder is untouched. Every change below is also marked in the
code with a `FIX`/`CHANGE`/`PERFORMANCE FIX` comment at the exact location.

All changes were verified by running the full simulation pipeline locally
(both the urban 1060 and rural 1061 networks), the original test suite, and a
new regression test suite (`vgi_api/tests/test_regressions.py`).

---

## 1. Bug fixes (user-visible)

### 1.1 `lv_plot_list` + `lv_default` returned HTTP 500
`vgi_api/vgi_api/validation/validators.py`

The API docs say plot ids may come from `lv_list` **or** the `lv_default`
selection, but the validator unconditionally parsed `lv_list` — calling
`None.strip()` when only `lv_default` was given → unhandled `AttributeError`.
Root causes fixed:
- pydantic v1 validators only see fields declared **above** them; `lv_default`
  was declared after `lv_plot_list`, so the plot validator could never see it.
  Field order is now `n_id, lv_list, lv_default, lv_plot_list`.
- The plot list is now validated against whichever selection method was used.
- The validator was missing `return v`, so even a *valid* plot list was
  silently discarded (main.py used to re-parse the raw query string to work
  around this). `validate_lv_parameters` now returns the validated plot list
  alongside the network list.

### 1.2 Selecting a `csv` profile option without a file returned HTTP 500
`validators.py:validate_csv` raised `IOError`; pydantic converts only
`ValueError`/`TypeError`/`AssertionError` into validation errors, so the
exception escaped the framework. Now raises `ValueError` → proper 422 with a
readable message.

### 1.3 CSV time-column check skipped the first interval
The interval check used `len(time_deltas) > 1`, so the gap between the first
two data rows was never validated. Now every consecutive pair is checked.
(The absolute start time remains unconstrained — that is the documented
contract, and the existing test fixtures rely on it.)

### 1.4 Simulating a single LV network crashed
`azure_mockup.py` (lv_comparison plot): with `ncols=1`,
`plt.subplots` returns a bare `Axes`, so `enumerate(axs)` raised `TypeError`.
`lv_list` of length 1 is valid input. Fixed with `np.atleast_1d(axs)` and
covered by a new test.

### 1.5 Duplicate plot in the response
`main.py` built the response dict with the key `"mv_highlevel"` listed twice
(second silently overwrote the first) and base64-encoded the same buffer
twice. Each plot now appears exactly once; the response **keys are unchanged**
so the frontend needs no modification.

### 1.6 Latent crashes fixed
- `azure_mockup.py`: the first "profile options" plot called
  `new_hsl_map(0)` → `ZeroDivisionError` when no 1-D profiles were selected
  (its two siblings were guarded; this one was not). All three now share one
  guarded helper and render a labelled placeholder image instead of a blank.
- `azure_mockup.py`: `sff(...)` was called when figure-saving was enabled but
  never imported → `NameError`. The dead gallery-saving branches are removed.
- `funcsTuring.py:plotLoadNos`: referenced an undefined variable `idxs` when
  called with `aln=None` → `NameError`.
- `azure_mockup.py`: `txtFss[frid0]` hard-`KeyError` for future network ids →
  `.get(frid0, "8")`.
- `azure_mockup.py`: a bare `assert` guarding the plot-list length is now a
  real `ValueError` (asserts vanish under `python -O`).
- `funcsMath_turing.py:vecSlc`: built "ragged" numpy object arrays — a
  `VisibleDeprecationWarning` on every call today and a hard error on
  numpy ≥ 1.24 (this blocked all dependency upgrades). Replaced with plain
  list indexing. numpy stays pinned `< 1.24` because `record_solution` still
  wraps per-load voltage vectors (which can be ragged on mixed 1-/3-phase
  networks) in `np.array` — lift the pin only after auditing those calls.

---

## 2. Reliability / crash isolation

`vgi_api/vgi_api/main.py`

The simulation previously ran inside the web-server process. The OpenDSS
engine (a native library behind a module-level singleton) and matplotlib's
pyplot API both hold process-global state and are not thread-safe. During
testing, running `/simulate` on a worker thread — which is exactly how the
ASGI stack and Azure Functions execute it — crashed the **entire process**
with a native signal (SIGILL inside matplotlib's C extension); two concurrent
requests did the same. A crash like this takes down every in-flight request.

The simulation now runs in a dedicated single-worker **subprocess**
(`ProcessPoolExecutor`, "spawn" context):
- one simulation at a time touches the global DSS/matplotlib state, on the
  worker's main thread (the only configuration pyplot supports);
- a worker crash produces a clean HTTP 500 and a fresh worker for the next
  request — the API process survives;
- a configurable timeout (`VGI_SIMULATION_TIMEOUT`, default 600 s) produces
  an HTTP 504 instead of a stuck request;
- the event loop is no longer blocked, so `/health-check` and the small GET
  endpoints stay responsive during a simulation.

Additionally, every matplotlib figure is closed as soon as it is rendered
(plus a `finally: plt.close("all")`). Previously ~11 figures stayed open per
request (~hundreds of MB held) until the next request happened to close them.

`azure_mockup.run_dss_simulation` consequently returns a picklable **dict**
(PNG `bytes` + numpy arrays) instead of a 21-element tuple of BytesIO
handles. The HTTP response shape is unchanged.

Non-converged power flows are now detected and logged as warnings (the
convergence flag was recorded before but never inspected).

---

## 3. Performance

Profiling (cProfile, urban network, 5 LV networks, 48 half-hour steps) showed
the OpenDSS solver was only ~10% of request time. Addressed:

### 3.1 Network model cache (`funcsTuring.py:unzip_networks`)
Every request re-extracted the full network zip (~3,800 files, 9–22 MB).
Only a handful of small top-level `.dss` text files are modified per request;
the large `lvNetworks/` tree is read-only. Networks are now extracted **once
per machine** into a shared cache (atomic rename so concurrent workers can't
see a half-extracted tree); each request gets private copies of the top-level
files and a symlink to the cached `lvNetworks/` (copy fallback where symlinks
are unavailable).

### 3.2 `record_solution` trimmed (`funcsTuring.py`)
Called after each of the 48 solves, it cost ~4× the solver itself, walking
every load/line/transformer one element at a time (~500k tuple conversions
per request). Quantities not consumed by any plot or CSV — line currents
(`Ifmv`/`Iflv`), secondary-substation sequence voltages (`Vsb`), solved load
powers (`Slds`), each a full fleet iteration per step — are now behind a
`full=True` flag for research use. **Nothing the API returns changed**, and
cheap diagnostics (losses, taps, the convergence flag, source voltage) are
still always recorded.

### 3.3 Plot rendering
The duplicated `mv_highlevel` encode is gone, the three profile plots share
one code path, and empty profile plots render a tiny placeholder instead of a
full blank figure.

Measured locally (Apple Silicon; cloud hardware is proportionally slower):
~2.5 s → ~1.6 s per request warm (≈ 35–40% faster), with identical response
content. The remaining time is dominated by matplotlib rendering and the
(unavoidable) OpenDSS network compilation per request.

### 3.4 Log noise
The `progress.Bar` terminal progress bar (ANSI control characters written to
server logs every step) and stray `print()`s were replaced with `logging`.

---

## 4. Security

- **CORS** (`main.py`): was `allow_origins=["*"]` with
  `allow_credentials=True` — an invalid combination per the CORS spec and
  needlessly wide open. Origins now come from the `VGI_CORS_ORIGINS`
  environment variable (comma-separated; defaults to the local dev
  frontend), and `allow_credentials` is False (the API is anonymous).
  Terraform now sets `VGI_CORS_ORIGINS` to the deployed static site origin.
  **If you deploy the API any other way, remember to set this variable.**
- **Upload size cap** (`validators.py`): uploaded CSVs beyond `MAX_CSV_BYTES`
  (10 MB — must stay above the ~8.6 MB bundled crowdCharge EV dataset, which
  the test suite validates through the same function) are rejected before
  parsing. Previously the entire (attacker-controlled) upload was read into
  memory line-by-line.
- **python-multipart ≥ 0.0.7**: fixes CVE-2024-24762 (ReDoS via a crafted
  Content-Type header) — directly relevant since this API parses multipart.
- **Base images / EOL runtimes**: Python 3.8 and the deprecated
  `tiangolo/uvicorn-gunicorn-fastapi` image replaced (see §5).
- Removed the unused `azure-storage-blob` dependency and dead credential
  plumbing (`config.get_settings`), and the now-unneeded storage secrets in
  CI.
- **Not done (deliberately, per request): authentication / rate limiting.**
  The API remains anonymous; a single request still consumes seconds of CPU.
  When you want it, an Azure API Management policy or a simple API-key
  dependency in FastAPI are the natural options.

---

## 5. Build & deployment

- `docker_images/vgi_api.dockerfile`: **the old build is broken today** — it
  installed Poetry from `get-poetry.py`, which was removed upstream (404).
  Rebuilt on `python:3.10-slim` with a plain `pip install ./vgi_api`
  (pip drives the poetry-core backend natively; Poetry itself is not needed
  at build time) and an explicit gunicorn/uvicorn CMD.
- `vgi_api/pyproject.toml`: Python `>=3.9,<3.11`; `dss-python` 0.10.7 →
  `0.12.x` (same `dss.dss_capi_gr` API, adds arm64/Apple-Silicon wheels);
  numpy pinned `<1.24` (see §1.6); `python-multipart` bumped;
  `azure-storage-blob` removed. `poetry.lock` was deleted because it no
  longer matches — run `poetry lock` to regenerate.
- `azure_funcs/requirements.txt`: fixed the malformed `azure - functions`
  line (invalid specifier) and replaced the bundled 2021 x86_64-only
  `dss_python` wheels with the PyPI pin. The `azure_funcs/dependencies/`
  wheels are no longer referenced.
- `.github/workflows/tests.yml`: Python 3.10; deprecated
  `checkout@v2`/`setup-python@v1`/`cache@v2` bumped; storage secrets removed;
  cache key now follows `pyproject.toml`.
- `infrastructure/terraform/main.tf`: removed the inert `APP_MODULE` setting
  (a convention of the deleted base image) and wired `VGI_CORS_ORIGINS` to
  the static site hostname.

## 6. Upgrading dss-python further (0.14/0.15) — notes

**DONE — see §8.** (Original note kept for context: `dss-python` 0.14+
removes the `dss.dss_capi_gr` module that `funcsDss_turing.dssIfc.__init__`
type-checks, so it failed at import; and the numpy < 1.24 pin was required
by ragged-array construction in `record_solution`.)

## 8. dss-python 0.15 / numpy 2 / Python 3.11 upgrade (round 2)

Implemented and validated the upgrade sketched in §6:

- `funcsDss_turing.dssIfc.__init__`: the `dss.dss_capi_gr.IDSS` type check
  (removed in dss-python 0.14) replaced with `isinstance(d.DSSObj, dss.IDSS)`
  (works from 0.12 onward).
- `funcsTuring.record_solution`: removed the ragged-object-array voltage
  handling that numpy >= 1.24 turned into a hard error (it crashed **3 of the
  6 default LV network sets** on modern numpy — networks mixing 1-phase and
  3-phase loads). Phase-A voltages are now selected up front (all any
  consumer ever used).
- Pins: `dss-python >=0.15.7`, numpy unpinned (verified on 2.x), Python
  3.9–3.11, Docker base `python:3.11-slim`, CI on 3.11.

**Validation**: 105/105 tests pass on py3.11 / dss 0.15.7 / numpy 2.4; all
24 numeric output datasets (6 network configurations x 4 CSV datasets)
compared against the dss 0.12.1 / numpy 1.23 baseline — worst relative
difference ~5e-10 (five orders of magnitude below OpenDSS's 1e-4 solution
tolerance). The physics is unchanged.

## 9. Batch result extraction (the record_solution performance lever)

`funcsTuring._build_result_index` + rewritten `record_solution`: instead of
walking every load (~1,700) and every line (~2,700) element-by-element after
each of the 48 solves (~half a million tuple conversions per request), the
code now precomputes each load's phase-A node index once per compiled
network and slices ONE `YNodeVarray` call per time step; the ~8
primary-feeder line powers are read by activating exactly those elements by
name. Full per-element extraction is still available via
`record_solution(full=True)` for research use.

Measured (same machine, same heaviest-case request, warm):

| version                         | simulation wall time |
|---------------------------------|----------------------|
| original (dss 0.10.7)           | ~3.9 s               |
| round-1 fixes (dss 0.12.1)      | ~2.2 s               |
| **round 2 (dss 0.15.7, batch)** | **~1.1 s**           |

Result extraction no longer appears among the top profile entries; the
remaining cost is matplotlib rendering (~0.5 s) and the per-request OpenDSS
network compilation. Numerically validated as part of §8 (same 24-dataset
comparison).

## 10. Parallel simulations

Simulations were serialised (one at a time per API process) — first
implicitly and unsafely in the original code (the endpoint blocked the whole
event loop; true concurrency crashed the process, see §2), then explicitly
in round 1 (single-worker pool). Parallelism is now a configuration knob:

- `VGI_MAX_PARALLEL_SIMULATIONS` (default 1) sets how many isolated worker
  subprocesses each API worker may run. Each worker owns its own OpenDSS
  engine and matplotlib state, so worker *processes* are the safe unit of
  parallelism (threads never are, for this stack). Requests beyond the limit
  queue FIFO; excess load degrades to waiting, not to failures or crashes.
- Budget ~400 MB RAM per worker while a simulation runs. Terraform sets 2
  (x 2 gunicorn workers = up to 4 concurrent simulations on the 7 GB P2v2
  plan); the local run script defaults to 2.
- Measured locally: 4 simultaneous requests complete in ~1.16 s with a warm
  4-worker pool — the same wall time as a single request, vs ~3.5 s when
  serialised.
- On a timeout with a multi-worker pool the pool is *not* disposed (that
  would cancel other users' running simulations); the abandoned job just
  occupies one slot until it finishes.

## 11. Known items intentionally left alone

- The frontend (`src/`) is unchanged — the API response contract is
  identical. Its npm dependency tree (2022) deserves its own upgrade pass.
- ~~Python 3.12+ needs the fastapi/pydantic-v2 migration (validators
  rewrite).~~ **DONE — see §12.**
- ~~`vgi_api/vgi_api/config.py` is now unused but left in place
  (harmless).~~ Deleted in §12 (it stopped being harmless: it imported
  pydantic v1's `BaseSettings`, which no longer exists).
- The two PDFs at the repository root are documentation, kept as-is.
- `slesNtwk_turing.py` / `funcsDss_turing.py` internals (network compilation)
  were not restructured beyond the fixes above. Per-request network
  compilation (~0.4 s) is the next performance frontier if ever needed: it
  would mean keeping a resident compiled network per (n_id, lv_list) and
  applying parameter changes through the OpenDSS API instead of editing
  .dss text files.

## 12. Python 3.14 migration (2026-07-06, round 3)

The last version ceiling (§11) is gone: the code now runs on **Python
3.10–3.14** and is verified end-to-end on 3.11 and 3.14. Every code change
below is marked in place with a `CHANGE(py3.14)` comment.

What set the old 3.11 ceiling was the web stack alone — pydantic v1 and
fastapi 0.71 do not run on Python >= 3.13. The OpenDSS engine needed **no
changes**: `dss-python` is pure Python and its native backend ships abi3
wheels that already cover new interpreter versions.

### 12.1 pydantic v1 → v2 (the real work)

`vgi_api/validation/validators.py` — validation behaviour is unchanged:

- `@validator(...)` → `@field_validator(...)` classmethods; the
  previously-validated-fields dict moved from a `values` argument to
  `info.data` (same "only fields declared above" semantics — the §1.1 field
  ordering still matters and is preserved).
- The two `@validator(..., always=True)` positivity checks (solar/PV
  uploads must be >= 0) became `@model_validator(mode="after")` methods.
- The reusable `pre=True` CSV validators became explicit `mode="before"`
  classmethods delegating to the same `validate_csv` function.
- `Optional[...]` fields now carry an explicit `= None` (v2 no longer
  defaults them implicitly).
- `ValidationError` import moved to the pydantic package root;
  `e.raw_errors` → `e.errors()` when re-raising as fastapi's
  `RequestValidationError`.
- `class Config: arbitrary_types_allowed` → `model_config = ConfigDict(...)`.

`vgi_api/main.py`:
- `@app.on_event("shutdown")` (deprecated) → a lifespan handler; same
  worker-pool teardown.
- `asyncio.get_event_loop()` inside a coroutine → `get_running_loop()`.
- `Query(example=...)` → `Query(examples=[...])`.

`vgi_api/config.py`: deleted — unused since round 1, and its pydantic-v1
`BaseSettings` import no longer resolves under v2.

### 12.2 Dead/abandoned dependencies

- **bunch** (last release 2011, sdist-only): its setup.py uses the Python-2
  `'rU'` file mode, removed in Python 3.11, so it cannot even be installed
  on the versions this project now targets. Only its `Bunch` class (a dict
  with attribute access) was used → vendored as `vgi_api/_bunch.py`
  (15 lines).
- **cmocean** `^2.0` → `>=3.0.3`: 2.x uses `np.unicode_`, removed in
  numpy 2. Same colormaps (`amp`, `tempo`), maintained release line.
- **progress**: removed — nothing has imported it since §3.4.
- **vgi_api/vgi_api/requirements.txt**: deleted — a stale copy of the old
  function-app requirements (still containing the malformed `azure -
  functions` line fixed in §5) that nothing references.

### 12.3 Pins, images, CI

- `pyproject.toml`: python `>=3.10,<3.15`; fastapi `>=0.115` (resolves to
  0.139 today); pydantic `^2.9` (2.13); uvicorn `>=0.30`; python-multipart
  `>=0.0.9`; dev-deps modernised (pytest 8, httpx for the TestClient) and
  moved to the `[tool.poetry.group.dev.dependencies]` table; version bumped
  to 0.3.0.
- `docker_images/vgi_api.dockerfile`: `python:3.11-slim` → `python:3.14-slim`.
- `.github/workflows/tests.yml`: test matrix now `[3.11, 3.14]` — the two
  extremes of the supported range.
- Tests: fastapi's TestClient is httpx-based now; two spots that passed enum
  *members* as query parameters (stringified as `"MVSolarPVOptions.CSV"` by
  httpx where the old client sent `"csv"`) now pass `.value`, and a
  `requests.Response` type hint became `httpx.Response`.
- **Caution (Azure only)**: the Azure Functions Python runtime lags CPython
  releases — check the runtime's supported versions before deploying
  `azure_funcs/` on 3.14; the package itself still supports 3.10–3.12 for
  that case. Local/Docker deployment is unaffected.

### 12.4 Validation

- **105/105 tests pass** on Python 3.14 (fastapi 0.139 / pydantic 2.13 /
  numpy 2.5 / dss-python 0.15.7) — same suite as the 3.11 baseline.
- **Numeric outputs are bit-for-bit identical** to the py3.11/old-stack
  baseline across 24 datasets: 6 network configurations (urban + rural,
  EV/PV/heat-pump/MV-solar/FCS profiles, non-default transformer scaling and
  OLTC settings) x 4 output datasets (primary loadings, MV voltages,
  transformer powers, LV comparison). Max relative difference: 0.0 — the
  solver stack (dss-python 0.15.7) is unchanged, so the physics is
  literally untouched.
- Live-server smoke test on 3.14: health check, GET endpoints, and a full
  `/simulate` over HTTP (exercising the spawn-based worker pool) — 200 OK,
  12 plots + 4 CSV datasets, ~2.3 s including cold worker start.

## 13. Self-hosted deployment (2026-07-06) — `deployment/` (NEW folder)

A complete single-server deployment for running the site on a purchased
domain, replacing the Azure Functions + Static Web Apps + Terraform stack.
The old `azure_funcs/` and `infrastructure/` folders are untouched and still
usable; nothing outside `deployment/` changed.

New files (each marked `NEW ... CHANGES.md §13` in a header comment):

- `deployment/docker-compose.yml` — two services: `api` (built from the
  **existing** `docker_images/vgi_api.dockerfile`, old code reused) and
  `web` (frontend + Caddy). Memory ceiling, health check, restart policy.
- `deployment/web.dockerfile` — multi-stage: compiles the **existing** Vue
  frontend (`src/`, old code reused unchanged; webpack-4 needs Node's
  legacy-OpenSSL flag — build verified locally), compiles Caddy with the
  `caddy-ratelimit` plugin, ships the static bundle in the Caddy image.
- `deployment/Caddyfile` — automatic Let's Encrypt HTTPS for
  `DOMAIN`/`www`/`api.DOMAIN`, SPA fallback, immutable-asset caching,
  security headers, 10 MB body cap, and a per-IP rate limit on
  `POST /simulate` (10/min → HTTP 429) as the abuse brake in place of
  authentication (which remains deliberately absent, per §4).
- `deployment/.env.example` — `DOMAIN`, `ACME_EMAIL`,
  `VGI_MAX_PARALLEL_SIMULATIONS`.
- `deployment/README.md` — the 7-step hosting guide (VPS → DNS → Docker →
  rsync → `.env` → `compose up` → verify), plus capacity/update notes.

Design notes: the API lives on `api.DOMAIN` (not `DOMAIN/api/...`) because
the frontend constructs URLs as `new URL("/simulate", VUE_APP_API_URL)` —
an absolute path replaces any base path, so a path prefix would require
frontend changes. `VGI_CORS_ORIGINS` is wired to the site origin;
`VUE_APP_API_URL` is baked in at image build from the same `.env`.

## 2026-07-07 — Front-end redesign handoff
- Added FRONTEND_REDESIGN_HANDOFF.md: full spec + phased plan for the front-end redesign (no code changed). Mockup: https://claude.ai/code/artifact/7c7d6821-9bc8-46da-850f-1a4b84943e62

## 14. Front-end redesign implemented (2026-07-08) — `event-frontend-v2/` (NEW folder)

The redesign in FRONTEND_REDESIGN_HANDOFF.md is implemented as a **new,
self-contained front end** in `event-frontend-v2/`. The original `src/` is
untouched. **No API/backend changes** — it uses the existing
`/get-options`, `/lv-network`, `/lv-network-defaults`, `/simulate` endpoints
as-is. New/changed code is marked in-file with `REDESIGN` / `P1`–`P4`
comments; the pass/fail verdict logic carries a `FLAGGED FOR FABLE REVIEW`
marker.

**How to run** (real API must be running on port 8000):
`cd event-frontend-v2 && NODE_OPTIONS=--openssl-legacy-provider npx vue-cli-service serve`
It reuses the parent `node_modules` (Node resolves it from the subfolder — no
reinstall). `.claude/launch.json` config `event-v2-dev` runs it for preview.

**What was implemented (all phases P1–P4):**
- P1 — humane inputs: penetration as a 0–100% slider (converted to a 0–1
  decimal before sending); each technology is an on/off toggle (off = profile
  "None"); LV networks are clickable ID chips (2–5, read-only in preset mode,
  a scrollable picker in Custom mode); network type and LV preset are
  segmented controls; OLTC / transformer-scaling / residential-share are
  sliders behind an "Advanced" disclosure. All `alert()` calls replaced by an
  inline error banner; the `/simulate` fetch now has `.catch`/`.finally` so a
  network failure always clears the spinner (the old code left it spinning).
- P2 — results lead with a verdict: three KPI cards (lowest customer voltage
  vs 0.94–1.10 pu, peak transformer loading with 80%/100% bands, MV voltage
  range vs 0.94–1.06 pu) parsed client-side from the returned CSV strings,
  plus one plain-English interpretation line (which LV network, what time,
  what to try). The nine figures are grouped into four collapsible sections
  with severity badges; per-figure CSV downloads and info popovers retained.
- P3 — structure: four scenario presets + Blank/custom (front-end constants);
  sticky scenario-summary sidebar with the Run button; Home merged into the
  top of Simulate (Home route deleted); WalkthroughModal retired into a new
  "How it works" page; token-based palette (light + dark) replacing the pastel
  boxes; numbered steps. Dead code (`rawJson`, `isShowJson`, commented-out
  GitHub-links block) dropped.
- P4 — previous-run memory (last scenario + verdict pill) and a network-map
  thumbnail toggle.

**Dev-only helpers (not for production):** `vue.config.js` proxies the API
paths to `http://127.0.0.1:8000` so the browser calls same-origin and avoids
CORS during dev (`.env.development` API base is empty; `.env.production` keeps
the absolute Azure URL). `dev-mock-api.js` is a dependency-free mock of the
API for use when the real backend isn't running.

**Verified** end-to-end against the **real** running API: lint passes; the
form renders and is keyboard-operable with no console errors; a full "2030
high EV" run returned real data and produced correct verdicts (LV 0.917 pu →
breach, transformer 92% → warning, MV within limits); penetration 60% is sent
as `lv_ev_pen=0.6`; an invalid Custom LV selection disables Run and shows the
error banner; light, dark, and 375 px layouts all render correctly.

**Verdict logic — Fable-reviewed and fixed (2026-07-08).** The pass/fail
thresholds and per-network verdict logic in `computeVerdicts` /
`interpret` (`event-frontend-v2/src/views/SimulateNetworkAPI.vue`) were
reviewed against `azure_mockup.py` (the dashed limit lines), the `fillplot`
quantile definition, and the GB ESQCR limits. The limits (LV 0.94–1.10 pu,
MV 0.94–1.06 pu) and the global-min/max envelope extraction were confirmed
correct; the review confirmed the 0%/100% quantile columns are exact
per-timestep min/max. Four issues were then fixed:

1. **Overvoltage attribution (was a real bug).** `interpret` timestamped
   overvoltage events with the location of the day's *minimum*, and the LV
   KPI card ("Lowest customer voltage") always showed the min — so a solar
   overvoltage breach displayed the wrong number and wrong time. Now a single
   `voltageVerdict()` finds the *driving* extreme (whichever violates, or sits
   nearest a limit); the KPI card title flips to "Highest customer voltage"
   and shows the violating value, and the sentence reports its time/network.
   Verified: Solar suburb (PV 70%) → "Highest customer voltage 1.149 pu,
   Above limit" at 12:30 on LV network 1137.
2. **MV feeder loadings were unchecked.** `primary_loadings_data` (% of each
   MV feeder's rating) is now parsed and folded into a `feeder` verdict that
   feeds the loadings-group badge, the overall verdict, and the interpretation
   (80%/100% bands, same as transformers). Verified: a feeder at 114% now
   badges the group "breach" even while the transformer reads 57%.
3. **MV precision.** The MV range showed 2 decimals, so 1.064 pu rendered as
   "1.06" next to an "Above limit" pill. Now 3 decimals, matching LV.
4. **Robustness.** MV breaches are always surfaced in the interpretation
   (previously suppressed when other issues existed); `parseCsv` no longer
   drops rows containing a NaN (non-finite cells are skipped in the extremes
   instead), so the row→time mapping can't shift.

Re-verified end-to-end against the real API (lint clean, 0 console errors);
the undervoltage path (2030 high EV) and overvoltage path (Solar suburb) both
now report the correct extreme, value, time, network, and feeder status.

## 15. Simulation crash when expanding a DG/FCS host network (2026-07-09)

`vgi_api/vgi_api/funcsTuring.py` — `turingNet.set_ldsi` (the `f_nms` helper).

**Symptom.** Selecting LV networks **1106, 1107, 1142 and 1143** (urban,
`n_id=1060`) — or any subset of them — made the simulation fail with no result
returned. The backend raised, uncaught:

```
ValueError: list.index(x): x not in list
  funcsTuring.py, set_ldsi -> f_nms = lambda buses: [nms.index([nn]) for nn in buses]
```

**Root cause.** The default scenario in `azureOptsXmpls.run_dict0` places lumped
MV distributed generators at buses **1106, 1142** (`dmnd_gen_data.dgs.mv`) and
lumped MV fast-charge stations at buses **1107, 1143** (`dmnd_gen_data.fcs.mv`).
These are hard-wired and never overridden by `main.py`. Each is placed by
finding a *load* whose bus name is exactly the network id, e.g.
`nms.index(["1106"])`.

That lumped load only exists while the network is represented as a single MV
load. When the user adds the same network to `lv_list`, `modify_network`
expands it into its full LV feeder and **disables the lumped load** — so the
exact lookup no longer finds `["1106"]` and raises, aborting the whole run.

The four affected ids are exactly the four default DG/FCS hosts, which is why
only these networks trigger it. The default presets (`near_sub`/`near_edge`/
`mixed`) never include them, so the demo paths and the smoke tests
(`1101/1137/1110`) never hit the bug — it only surfaces with a hand-entered
`lv_list`.

**Fix (engine backstop).** `f_nms` now skips any lumped MV DG/FCS location that
has no lumped load and logs a clear warning, instead of crashing. This is a
defensive backstop for direct engine callers (tests/scripts); the primary,
product-level fix is §16.

## 16. Reserve the MV solar/FCS host networks (2026-07-09)

`vgi_api/vgi_api/validation/network_ids.py`,
`vgi_api/vgi_api/validation/validators.py`,
`vgi_api/vgi_api/validation/__init__.py`,
`vgi_api/tests/test_api_validation.py`.

Chosen resolution for the §15 conflict: **keep the MV solar/FCS demand and
prevent the clash at the source** — the four host networks stay lumped and are
simply not offered as "model in full" options.

- `RESERVED_LV_NETWORKS` is now derived from
  `run_dict0["dmnd_gen_data"]` (`dgs.mv` + `fcs.mv` → `[1106, 1107, 1142, 1143]`),
  so it stays automatically in step with the scenario definition — no hard-coded
  duplicate to drift.
- `VALID_LV_NETWORKS_URBAN` / `VALID_LV_NETWORKS_RURAL` (served by `/lv-network`,
  which drives the frontend dropdown, and used by the validator) are now the
  full feeder membership **minus** `RESERVED_LV_NETWORKS`. The networks still
  exist in the model and stay represented as lumped MV loads, so the MV solar /
  fast-charge-station demand placed on them is always preserved.
- `validate_lv_list` rejects a reserved id with a clear, specific message
  ("… reserved for the lumped MV solar / fast-charge-station demand and cannot
  be modelled in detail") rather than the generic "not network ids".

**Applies to both feeders.** `run_dict0` is shared by urban (`1060`) and rural
(`1061`), and all four hosts exist as lumped loads in *both* redirect files, so
rural had the identical latent crash. Deriving the reserved set once and
filtering both lists fixes urban and rural together.

**Verification.**
- `RESERVED_LV_NETWORKS == [1106, 1107, 1142, 1143]`; urban selectable list
  75 → 71, rural 308 → 304, with none of the reserved ids present in either.
- Validation rejects a reserved id (e.g. `1101,1106`) for both urban and rural
  with the reserved-specific message; normal lists still accepted.
- Full end-to-end runs with MV solar **and** FCS profiles selected complete for
  both `n_id=1060` (`1101/1137/1110`) and `n_id=1061` (`1102/1154/1262`) with
  **zero** DG/FCS skip warnings — i.e. every lumped MV asset is placed and its
  demand preserved. All plots valid PNGs, all datasets 48×N and finite.
- New tests in `test_api_validation.py` lock in the reserved set, its exclusion
  from both selectable lists and the `/lv-network` payload, and the
  reserved-specific validation error (parametrised over urban and rural).

**No front-end change required — both Vue apps are covered.** The old front end
(`src/views/SimulateNetworkAPI.vue`) and the redesigned one
(`event-frontend-v2/`) both build their LV-network dropdown from the
`/lv-network` response (`this.lv_options.lv_list = JSON.parse(...).networks`) and
send either that custom list or a `lv_default` preset. Because the backend now
serves the filtered list and the presets contain no reserved id, neither app can
offer or submit a reserved network; if one is forced anyway the API returns a
clean 422 that both apps already surface as an error message. Verified over real
HTTP against the fixed backend: `/lv-network?n_id=1060` → 71 networks with none
of `{1106,1107,1142,1143}`; `POST /simulate?...&lv_list=1101,1106` → HTTP 422
with the reserved message; a valid list → HTTP 200 with all plots.

> If the deployed/old front end still shows the four networks, it is talking to a
> backend that has not been redeployed with this fix. In development both apps
> point at `http://127.0.0.1:8000` (`.env.development`); in production both point
> at the Azure backend (`.env.production`), which must be redeployed for the
> change to take effect for the hosted site.

## 17. New analysis features (2026-07-09) — convergence, network explorer, phase unbalance

Three user-facing features (plus one dropped idea) from `FEATURE_PLAN.md`.
Backend changes are additive: the four numeric regression datasets are
unchanged (harness PASS, max rel diff ~1e-10 across all 8 scenarios), and every
new backend behaviour is covered by tests. Marked in-file with
`CHANGE(feature)` comments.

### 17.1 Non-convergence surfaced to the user
`vgi_api/vgi_api/azure_mockup.py`, `main.py`,
`event-frontend-v2/src/views/SimulateNetworkAPI.vue`,
`tests/test_convergence.py`.

The power flow is solved independently at each of the 48 half-hours; a step
that fails to converge yields physically meaningless numbers. Previously this
was only logged server-side. `run_dss_simulation` now returns a `convergence`
block (`n_steps`, `n_failed`, `failed_steps`, `failed_hours`), `/simulate`
forwards it, and the frontend shows an amber banner naming the affected time
windows. Failed windows are also shaded red on the daily time-series plots
(no shading when everything converges, so converged result images — and the
regression baselines — are byte-identical). Tests force a divergence via a
patched `Cnvg` flag and assert the block, the banner data, and that plots
still render.

### 17.2 Interactive network explorer + map selector
`vgi_api/scripts/build_network_topology.py` (NEW),
`vgi_api/vgi_api/data/network_topology_{1060,1061}.json` (NEW, committed),
`vgi_api/vgi_api/main.py` (`/network-topology`),
`event-frontend-v2/src/components/NetworkExplorer.vue` (NEW),
`event-frontend-v2/src/views/SimulateNetworkAPI.vue`,
`event-frontend-v2/vue.config.js` (proxy), `dev-mock-api.js`,
`tests/test_topology_builder.py`.

An offline builder parses the network zips (following the DSS `Redirect` chain,
so it is robust to file naming) into a small topology JSON per MV network:
the MV single-line diagram (bus coordinates, lines, substation) and, per LV
network, the connecting MV bus, transformer kVA, feeder count, houses per
feeder, and house-to-LV-substation distances **in metres** (LV lines have real
lengths) computed by shortest-path graph traversal. MV distance is reported as
electrical distance (|Z1|, ohms) and hop count only — the MV model has no line
lengths. The traversal was cross-checked against the OpenDSS engine's own
`AllBusDistances` (agreement within ~1 m over ~460 m). A committed-JSON
regeneration guard fails if the zips and JSON drift apart.

The `/network-topology` endpoint serves the pre-built JSON (no OpenDSS, no
worker pool — instant). The new Vue `NetworkExplorer` replaces the old static
overview PNG: it draws the MV diagram with each LV network as a node sized by
house count, a detail panel (feeders, houses, distances, transformer) on
hover, and — in "custom" mode — click-to-select that toggles the same
`lv_selected` state as the chip list (2–5 cap enforced), so map and chips stay
in sync. In preset mode the preset's networks are highlighted read-only, making
"near substation" / "near edge" / "mixed" visible for the first time. Verified
end-to-end in the browser (selection, cap, detail panel, chip sync).

### 17.3 Phase unbalance on the LV feeders
`vgi_api/vgi_api/funcsTuring.py` (`_build_result_index`, `record_solution`),
`azure_mockup.py`, `main.py`,
`event-frontend-v2/src/views/SimulateNetworkAPI.vue`,
`tests/test_unbalance.py`.

The LV feeders are 3-phase with single-phase customers spread across the
phases; OpenDSS already solves this unbalanced, but the results pipeline
discarded it. `record_solution` now always records the IEC voltage unbalance
factor (VUF = |V2|/|V1|) at each LV substation from the transformer sequence
voltages (previously captured only under `full=True`), and `_build_result_index`
records each load's connected phase. A new `lv_unbalance` plot shows VUF over
the day against the ER P29 (1.3%) and EN 50160 (2%) planning levels, plus the
per-phase customer-voltage envelope of the first plotted network; a matching
`lv_unbalance_data` CSV is downloadable. The extra cost is one small pass over
the handful of transformers per step. Tests pin the VUF maths against a
hand-derived Fortescue value, assert a balanced base case stays < 2% and that
single-phase EV clustering does not *decrease* unbalance, and confirm the
existing datasets are unchanged.

The regression harness (`regression_harness/vgi_regression.py`) capture was
made robust to the new non-plot response keys (the `convergence` object and the
extra CSV dataset postdate the v0 baseline, so they are skipped rather than
base64-decoded as images).

### 17.4 Dropped: user-editable LV transformer settings
Proposed (LV transformer scaling / OLTC setpoint / bandwidth) and then dropped
by decision — see `FEATURE_PLAN.md` §4. The tool cannot establish the upstream
(MV) headroom or real-world feasibility that would make the knob meaningful, so
offering it risks unearned confidence.

## 18. Network explorer refinements (2026-07-11)
`vgi_api/vgi_api/validation/network_ids.py`, `main.py`,
`event-frontend-v2/src/components/NetworkExplorer.vue`,
`src/views/SimulateNetworkAPI.vue`, `src/assets/vgi_styles.css`,
`dev-mock-api.js`.

Two user-requested map improvements:

- **Click-to-toggle from any mode.** Clicking a node while a preset
  (near-sub / near-edge / mixed) is active now hands the preset's selection
  over to "custom" and toggles the clicked node, instead of doing nothing.
  Each node also gained an enlarged invisible hit circle (+5 px radius) —
  the smallest nodes were ~10 px on screen and easy to miss — plus
  Enter/Space keyboard activation on the focusable hit target.

- **Distinct colours for the lumped MV asset sites.** `/network-topology`
  now annotates the response with `mv_assets: {solar_pv: [...], fcs: [...]}`
  (derived from `run_dict0` at serve time, same source as
  `RESERVED_LV_NETWORKS`, so it cannot drift from the engine). The map
  draws solar-farm hosts in gold and fast-charging hosts in violet (new
  `--solar`/`--fcs` design tokens, light + dark), legend entries for each,
  and the hover panel explains why those networks cannot be selected.
  The dev mock mirrors the annotation.

Verified end-to-end in the browser against the mock API: preset → custom
hand-off, select/unselect by real mouse clicks, reserved nodes inert and
correctly coloured, no console errors, component lint clean.

## 19. CSV upload format hint + template (2026-07-11)
`event-frontend-v2/src/components/SelectProfile.vue`.

The upload widget said only "Upload your own (CSV)", so users reasonably
uploaded week-long single-column files and hit the validator ("File has 1007
rows. Expecting 49"). When "Upload your own (CSV)" is selected the widget now
shows the expected format inline — a header row plus 48 half-hour rows
(00:00:00–23:30:00), time in column 1, one profile per further column
("household's" for LV technologies, "site's" for MV), kW or kWh per
half-hour — and a "Download a template" link that generates a valid
48-row × 3-column starter CSV client-side. The template string was checked
against the real `validate_csv`/`csv_to_array` (loads as a (48, 3) array).

## 20. Network-map & results refinements (2026-07-11)
`event-frontend-v2/src/components/SelectProfile.vue`,
`src/layouts/NavBar.vue`, `src/components/NetworkExplorer.vue`,
`src/views/SimulateNetworkAPI.vue`, `src/assets/vgi_styles.css` (tokens),
`dev-mock-api.js`, `vgi_api/scripts/build_network_topology.py`,
`vgi_api/vgi_api/{main,azure_mockup}.py`, and the two committed
`network_topology_*.json`. Implements OPUS_IMPLEMENTATION_BRIEF.md.

- **CSV hint wording (all LV loads).** The upload hint now reads uniformly
  "…every further column is one daily profile in kW (or kWh per half-hour)"
  (dropped the household/site split). Template download unchanged.
- **Brand subtitle.** "Electric Vehicle Network analysis Tool" sits next to
  the EVENT wordmark, hidden below 560 px.
- **Feeder labels on the map.** `build_network_topology.py` now emits
  `mv.feeders` (name, far-end bus, MVA rating) in the engine's feeder order —
  parsed from the primary lines (bus1 == substation) in lines.dss, which is
  OpenDSS's line order. Verified label-for-label against the results legend
  (`simulation.fdr2pwr`) for both shipped networks. NetworkExplorer draws
  F1, F2… at each feeder's far-end MV bus. Ratings table mirrors
  `funcsTuring.set_powers`; falls back to null (labels still render) if a
  model change ever desyncs the primary-line count.
- **Bigger map, minimal hover.** Removed the per-network detail panel and the
  2-column layout — the map spans the full card. The "interactive — hover &
  click the nodes" caption moved under the heading. The only per-node info is
  now a caption line naming the reserved solar-farm / fast-charging hosts
  (from `mv_assets`), shown on hover/focus (touch- and keyboard-friendly).
- **MV advanced summary on one line.** The collapsed summary stays on a single
  row (nowrap + horizontal scroll), checked at 360 px.
- **Per-phase customer voltages: user-selectable network.** The engine's
  unbalance figure is now VUF-only; the per-phase envelope is emitted as one
  figure PER selected network in a new `lv_phase_pngs` dict (keyed by id;
  `main.py` base64-encodes each; no extra solves — `s.VlvLds` was already in
  memory). The results page adds a "Per-phase customer voltages" card with a
  network `<select>` (defaults to the first). Regression harness is
  unaffected: `lv_unbalance`/`lv_phase_pngs` are not in PLOT_KEYS and unknown
  keys are skipped on capture.
- **Graph explanations.** The LV-voltage headline now says "The lowest/highest
  simulated customer voltage reaches …"; the LV-customer-voltages and
  per-phase tooltips explain the median line, the min–max / 25–75% bands, and
  the per-phase mean line + spread.

Backend RNG (funcsTuring.py) deliberately left untouched (brief §8). Verified
end-to-end in the browser against the mock API (feeder labels F1–F8, host
hover note, per-phase selector switching networks, reworded headline, CSV
hint, single-line advanced summary at 360 px, no console errors) and against
the real engine directly (all 5 per-network per-phase PNGs, VUF-only figure,
correct base64 round-trip; topology feeders match the engine legend;
test_topology_builder + test_unbalance green).

## 21. UI refinements (2026-07-11, round 2)
`event-frontend-v2/src/assets/vgi_styles.css`,
`event-frontend-v2/src/views/SimulateNetworkAPI.vue`,
`event-frontend-v2/src/layouts/NavBar.vue`,
`event-frontend-v2/src/components/NetworkExplorer.vue`.

Six product-owner-requested fixes, all marked `CHANGE(round2-N)` in-file.

1. **Info popover contrast.** The ⓘ notes (`InputDetails.vue`, a Bootstrap 4
   modal used for every network/figure explanation app-wide) had no styling
   of their own, so they inherited the page's dark-theme `--ink` (near-white)
   text onto Bootstrap's hard-coded white modal panel — effectively
   white-on-white and almost unreadable; light theme was subtly off too.
   `vgi_styles.css` now anchors `.modal-content`/`.modal-title`/`.modal-body`/
   `.close` to the app's `--card`/`--ink`/`--line` tokens, global and
   unscoped so every popover is fixed at once, in both themes. `--ink` on
   `--card` measures ~15.6:1 (light) and ~13.4:1 (dark) contrast — both far
   past WCAG AA's 4.5:1.
2. **FIFO network selection at the 5-network cap.** `toggleLvId`
   (`SimulateNetworkAPI.vue`, ~line 849) used to block a click once 5 LV
   networks were selected. It now drops the earliest-selected network
   (`sel.shift()`) and appends the new one, since every addition pushes to
   the end of the array. The chip list and `NetworkExplorer`'s map both call
   this same method against the shared `lv_options.lv_selected` state, so
   they stay in sync automatically, including from a preset → custom
   hand-off. The minLength(2) Vuelidate rule for Run is untouched. Verified
   by scripted clicks through 6+ networks via both the chip list and the map:
   the oldest selection is dropped each time, deselect-by-click still works,
   and the count never exceeds 5.
3. **MV advanced disclosure: two-line title, one-line details.** The
   collapsed summary row used to force everything onto one nowrap line with
   horizontal scroll (§20). The title is now an explicit two-line block
   ("MV advanced" / "network parameters" via a `<br>`, `.evt-adv-label`
   fixed at 140px — wide enough that neither line wraps again), which frees
   enough width that `.evt-adv-summary` fits on one line via
   `overflow:hidden; text-overflow:ellipsis` instead of a scrollbar. At
   375 px the summary ellipsis-truncates as expected; no overlap or overflow
   at any width tested (`SimulateNetworkAPI.vue` ~lines 159–176, 1575–1620).
4. **EVENT acronym: one place, styled as a tagline.** No duplicate of
   "Electric Vehicle Network analysis Tool" was found anywhere in the page
   body (only the NavBar subtitle and the `<title>` tag, which is out of
   page-content scope) — the same-line subtitle in `NavBar.vue` was the only
   instance and is also the one the owner disliked. It now renders as a
   small uppercase tagline stacked directly under the EVENT wordmark
   (`.evt-brand` is a column flexbox; the wordmark is wrapped in
   `.evt-brand-word`), still hidden below 560 px. Alternatives considered:
   (a) a tooltip/title-attribute on the wordmark icon — rejected as
   less discoverable and inaccessible on touch; (b) a hero tagline on the
   How-it-works page — rejected because that page already opens with its own
   "How it works" heading and lede, and a second EVENT expansion there would
   just recreate the "two places" problem one page over.
5. **Per-network details restored above the map.** §20 removed the detail
   panel entirely to let the map span the full card. `NetworkExplorer.vue`
   now has a fixed-height caption strip (`.nx-detail`, `min-height: 2.5em`)
   above the SVG, under the "interactive — hover & click" line, so the
   layout never jumps between states. Hovering, keyboard-focusing, or
   clicking a network shows `describeNetwork()`'s plain-language caption —
   transformer size, household count, and distance from the substation
   expressed as "N line section(s) from the substation" with a relative
   "(close)"/"(far)" qualifier (never the `elec_dist_ohm` value). The four
   reserved solar/FCS host networks keep their existing "cannot be selected"
   explanation instead (same `hovered` state now doubles as the caption's
   data source). `onNodeClick` also sets `hovered` directly so a tap shows
   the caption immediately on touch devices. Idle state shows "Hover a
   network for details." Map size is unchanged.
6. **Feeder labels (F1, F2…): bigger, foreground, near the substation.**
   `topology.mv.feeders[].to` is actually the bus2 of each feeder's *first*
   line segment out of the substation (built from `bus1 == substation` lines
   in `build_network_topology.py`) — i.e. already the near end, not the far
   end §20's comment suggested — but the label was drawn directly on that
   bus, which for the shortest feeders coincides with the first LV node,
   causing the "sitting among the LV nodes" complaint. `feederLabels()` now
   places each label along its feeder's direction from the substation and
   greedily pushes it further out (`BASE_R=26px` steps of 8px) until its
   estimated bounding box clears both the substation's own "MV substation"
   text and every previously placed feeder label — plain angle-only spacing
   wasn't enough once the wide substation label was accounted for. Labels
   moved to the end of the SVG template (after the LV node `<g>`, so they
   paint last/foreground), font-size 10px → 13px bold, with a `--card`
   -coloured `paint-order: stroke` halo so they stay legible crossing lines
   in both themes. F-numbering/order is unchanged (still `topology.mv.feeders`
   verbatim). Verified visually (3x zoom) against both shipped networks:
   urban (8 feeders, tight angles) and rural (3 feeders, two only 6° apart) —
   no overlaps with each other or the substation marker/label in either case.

**Verification.** Ran against the mock API
(`event-frontend-v2/dev-mock-api.js` on :8000, dev server on :8080): lint
clean (`npx vue-cli-service lint --no-fix`, 0 errors, 1 pre-existing
unrelated warning in `dev-mock-api.js`); 0 browser console errors throughout;
light and dark themes and 375 px all checked; FIFO verified by scripted
clicks through 6+ LV networks via chips and the map; a full "Today's network"
run completed and rendered the KPI/verdict/figures section correctly (spot-
checked via DOM inspection — the mock's 1×1 placeholder JPEGs, stretched to
fill each figure card, intermittently produced flat-black frames from the
browser-pane screenshot tool specifically when scrolled into view; this is a
dev-mock/screenshot-tooling artifact, not a real rendering bug — `getComputedStyle`
and `elementFromPoint` at the same coordinates always showed the correct
element, text and colour, and the same page scrolled to the same offset
*before* a run — i.e. without the oversized placeholder images — screenshots
correctly every time).

**Deliberately not done:** the `MV substation` text label itself was left at
its original position/size (only feeder labels were moved and enlarged per
the brief); no in-app light/dark toggle was added (theme is still
`prefers-color-scheme`-only, unchanged from §14 — out of scope here).

## 22. Network map round 3 (2026-07-11, follow-up)
`event-frontend-v2/src/components/NetworkExplorer.vue`. Marked
`CHANGE(round3)` in-file.

Product-owner follow-ups to §21:

- **Richer detail caption.** The strip above the map now also names the
  feeder count and the per-feeder household split (e.g. "500 kVA transformer
  · 200 households · 4 feeders (55, 31, 39, 75 households) · 1 line section
  from the substation (close)"), read from the topology JSON's per-network
  `feeders[]` (`n_houses` each; falls back to a bare `n_feeders` count if the
  array is ever absent). Still plain language, still no ohm values. On
  screens ≤ 560 px the strip reserves four lines instead of two so the
  longer caption doesn't jump the layout.
- **Bigger map.** ViewBox height 320 → 460 (the width already spans the full
  card), so the whole diagram — nodes, cables, labels — renders larger.
- **Feeder labels rebuilt (the §21 placement was still wrong on the real
  networks).** Verified against the committed `network_topology_1060.json`:
  all 8 urban feeders leave the substation as short stubs before spreading
  out, so both the §20 far-end placement and §21's straight-ray placement
  crowded the labels into an illegible cluster around the substation. Each
  label is now placed by TRACING its feeder's actual polyline (first primary
  line, then following `mv.lines` outward; the network is radial) to a
  target on-screen distance where the feeders have visibly separated, then
  scored across several distances × small perpendicular offsets against the
  substation label, already-placed labels, every LV node circle and the
  viewBox edge. Font 13 → 15 px with the halo kept.

Verified in the browser against both committed topologies via the mock API
(which serves the real JSONs): urban (8 feeders) and rural (3 feeders) both
place all labels with zero label/label, label/node and label/edge overlaps
(checked programmatically from the rendered SVG geometry, not just by eye);
the caption shows the feeder split for a normal network and the reserved
explanation for a solar/FCS host; 0 console errors; lint clean (one
pre-existing warning in dev-mock-api.js). A new `event-v2-mock` launch
config runs the front end against the mock on port 8010.

## 23. Map jiggle fix + dark-mode logos (2026-07-12)
`event-frontend-v2/src/components/NetworkExplorer.vue`,
`event-frontend-v2/src/views/SimulateNetworkAPI.vue`. Marked
`CHANGE(round4)` in-file.

- **The map no longer moves when hovering/clicking nodes.** The §21
  fixed-height caption strip was silently defeated by the app-wide
  `box-sizing: border-box`: its `min-height: 2.5em` had the 12 px padding
  + 2 px border deducted from it, so it only actually reserved ONE text
  line — every two-line caption grew the strip by ~14 px and bounced the
  map (and everything below it) on every hover in/out. The strip now has a
  hard `height: calc(2 * 1.25em + 14px)` (clamped lines × line-height plus
  padding + border; 4-line variant ≤ 560 px), verified constant to the
  sub-pixel across idle/hover/leave/click.
- **The caption is sticky.** Leaving a node used to snap the strip back to
  the "Hover a network for details." hint, so the text flip-flopped as the
  pointer crossed the map. The strip now keeps showing the most recently
  hovered/focused/clicked network (new `lastId`; live hover still wins);
  the hint only shows before the first interaction.
- **Partner logos legible in dark mode.** The Turing/Newcastle/Supergen/LRF
  marks are full-colour brand assets with dark wordmarks on transparent
  PNGs — invisible on the dark paper. The logo strip now sits on a white
  plinth card (both themes; brand marks must not be recoloured).

Verified in the browser against the mock API: map SVG top measured
identical (590.914 px) across idle → hover → leave → click; caption strip
height constant at 45.2 px in every state (previously 31 ↔ 45 px); logos
screenshot-checked in dark and light schemes; 0 console errors.
