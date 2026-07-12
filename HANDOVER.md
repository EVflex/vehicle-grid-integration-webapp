# Handover: deploying the VGI web app on your own domain

You've been asked to put this site live on a domain that's already been
bought. This document is everything you need: what the app is, what every
part of the repo does, how it's wired together at runtime, your two
deployment options, and the practical steps to get from "domain purchased"
to "site live and verified." It assumes you're a competent developer who
has never seen this project before.

## 1. What this is

This is "EVENT" (Electric VEhicle Network Tool) — a demo web app that lets
someone pick a real UK 11kV medium-voltage / low-voltage electricity
network, dial in assumptions about electric vehicles, solar panels, heat
pumps and EV fast-charging stations, and run a full power-flow simulation
(via the open-source OpenDSS engine) to see the effect on grid voltages and
equipment loading over a 48-half-hour day. The backend is a Python FastAPI
service wrapping the simulation engine; the frontend is a Vue single-page
app that renders the inputs and the resulting charts. It's a public,
anonymous research/demo tool — no accounts, no user data stored.

## 2. Repo map — what matters for deployment

```
vgi_api/                    Backend: FastAPI + OpenDSS simulation engine. REQUIRED.
  vgi_api/main.py             All HTTP endpoints (/simulate, /get-options, /lv-network, /network-topology, /health-check).
  vgi_api/funcsTuring.py,     The simulation engine (network compilation, demand
  funcsDss_turing.py,         allocation, result extraction). You will not need to
  funcsMath_turing.py,        touch these to deploy.
  slesNtwk_turing.py
  vgi_api/data/                Network models (two zips, ~30 MB total), demand/generation
                                profile CSVs, pre-built topology JSON for the map view.
  vgi_api/validation/          Query-parameter validation (which network IDs, which
                                profile options are legal).
  pyproject.toml               Backend dependencies (Python 3.10–3.14).
  tests/                       133 automated tests. Not required to deploy, but
                                useful to confirm a checkout is healthy before you build.

src/                         Old (2022) Vue front end. One of your two frontend options — see §4.
event-frontend-v2/           New, redesigned Vue front end (plain-language UI, verdict
                              cards, network map). The other frontend option — see §4.

deployment/                  READY-MADE self-hosted deployment (Docker + Caddy). Your
                              fastest path to live — see §5.
docker_images/vgi_api.dockerfile   Builds the backend container. Used by both deployment
                                    routes.
azure_funcs/, infrastructure/      LEGACY Azure Functions + Static Web Apps + Terraform
                                    route. Still usable, not recommended for a fresh
                                    deploy — see §6.
regression_harness/          A tool to numerically verify a deployed backend matches
                              the trusted reference. Use it as your final smoke test —
                              see §7.
CHANGES.md                   Full change log versus the original codebase — read if
                              you need historical context on any file.
IMPROVEMENTS.md              Security/architecture work identified but NOT YET DONE.
                              Read §1 before public launch — see §8.
.github/workflows/tests.yml  CI: runs the 133 backend tests on every push/PR to `main`
                              (GitHub-hosted runner, no secrets needed).
```

Everything else at the repo root (the two PDFs, `FEATURE_PLAN.md`,
`FRONTEND_REDESIGN_HANDOFF.md`, `OPUS_IMPLEMENTATION_BRIEF.md`) is
background documentation — irrelevant to getting the site running.

## 3. Runtime architecture

Two independent pieces, on two different origins:

- **Frontend**: a static Vue single-page app (just HTML/CSS/JS files) served
  by a plain web server.
- **Backend** (`vgi_api`): a FastAPI process that runs the actual power-flow
  simulations. CPU- and memory-heavy (~1–2 s CPU and ~400 MB RAM per
  simulation), so it runs as its own service, not embedded in the frontend
  server.

**Why the API needs its own subdomain (`api.DOMAIN`), not `DOMAIN/api/...`:**
the frontend builds every API request as `new URL(path, VUE_APP_API_URL)` —
an absolute URL. If `VUE_APP_API_URL` were `https://DOMAIN` and you tried to
route `/api/*` to the backend at the reverse-proxy level, it would still
work for the base path, but the frontend never puts `/api` in front of its
own request paths — it would call `https://DOMAIN/simulate`, not
`https://DOMAIN/api/simulate`. Making a subdirectory scheme work would mean
editing the frontend's fetch calls. Putting the API on its own subdomain
(`api.DOMAIN`) needs zero frontend code changes — this is the setup both
deployment routes below use.

**CORS**: the backend only accepts browser requests from origins listed in
the `VGI_CORS_ORIGINS` environment variable (comma-separated). Set this to
your frontend's origin(s), e.g. `https://yourdomain.com`. Get this wrong and
the browser console will show CORS errors while `curl` against the API
works fine — that's the tell.

**`VUE_APP_API_URL` is baked in at build time**, not read at runtime. It's a
Vue CLI environment variable, compiled into the static JS bundle when you
run `vue-cli-service build`. If you change the domain later, you must
**rebuild** the frontend image/bundle — editing a config file on a running
server does nothing.

## 4. Which frontend to deploy

There are two complete Vue apps in this repo and **you need to pick one**
(or run both, but that's unusual for a single public site):

- `src/` — the original 2022 UI. This is what `deployment/web.dockerfile`
  builds **today, by default**.
- `event-frontend-v2/` — the redesigned UI (plain-language sliders instead
  of raw parameter boxes, pass/fail verdict cards, an interactive network
  map). This is the newer, actively developed one.

**Check which one your team wants live before you deploy.** If it's
`event-frontend-v2/`, the ready-made `deployment/web.dockerfile` needs a
small edit — right now its frontend build stage does `COPY src ./src` and
builds that; you'd change it to copy and build `event-frontend-v2/` instead
(same `npx vue-cli-service build` command, same legacy-OpenSSL requirement,
different `COPY` source and `WORKDIR`/output path). IMPROVEMENTS.md §2.7
flags this exact ambiguity ("two full Vue apps... must both track the API
contract") — this project has not yet formally retired the old one, so
`deployment/` still defaults to it. If you're unsure, ask before you build
and ship the wrong UI.

## 5. Route A — the ready-made self-hosted deployment (recommended)

`deployment/` is a complete, self-contained Docker Compose + Caddy setup.
Two containers: `api` (backend) and `web` (frontend + Caddy, which also
terminates HTTPS automatically via Let's Encrypt). Full walkthrough is in
`deployment/README.md`; summary:

1. **Rent a Linux VPS.** 4 GB RAM minimum (8 GB if you raise
   `VGI_MAX_PARALLEL_SIMULATIONS` above 1), Ubuntu 24.04 LTS suggested.
   Note its public IP.
2. **DNS**: in your registrar's panel, create three `A` records pointing at
   the server's IP — `@` (apex/bare domain), `www`, and `api`. Wait for
   `ping yourdomain.com` to resolve before continuing (HTTPS in step 5 only
   works once DNS resolves).
3. **Install Docker** on the server: `curl -fsSL https://get.docker.com | sh`.
   Optionally lock down the firewall to SSH + web:
   `ufw allow 22 && ufw allow 80 && ufw allow 443 && ufw --force enable`.
4. **Copy the project** to the server — `rsync` from your machine, or (once
   you've followed `GITHUB_UPLOAD.md`) `git clone` the repo directly on the
   server. `git clone` is the better long-term choice — it makes "Step 7:
   updating the site" a `git pull`.
5. **Configure and launch**:
   ```bash
   cd /opt/vgi/deployment   # or wherever you cloned/copied to
   cp .env.example .env
   nano .env                # set DOMAIN=yourdomain.com, ACME_EMAIL=you@yourdomain.com
   docker compose up -d --build
   ```
   First build takes 5–10 minutes. Caddy fetches the Let's Encrypt
   certificate automatically on first HTTPS request — nothing to configure.
6. **Verify** — see §7 below.
7. **Updating later**: `git pull` (or rsync), then
   `docker compose up -d --build` again from `deployment/`. No database, no
   user state; the only thing worth preserving across rebuilds is the TLS
   certificate volume, which Docker keeps automatically.

## 6. Route B — the legacy Azure route

`azure_funcs/` (the API, as an Azure Function App) and `infrastructure/`
(Terraform provisioning Azure Web App + Static Web App + Container
Registry) together reproduce how this project was hosted before
`deployment/` existed. It's still usable, but:

- It needs an Azure subscription, `az` CLI login, and Terraform ≥1.0 — more
  moving parts than a single VPS.
- **Caution on Python version**: CHANGES.md §12.3 flags that the Azure
  Functions Python runtime lags behind CPython releases — before deploying
  `azure_funcs/` on a recent Python, check which versions Azure Functions
  actually supports at the time you deploy. The `vgi_api` package itself
  still supports Python 3.10–3.12 for this reason (it targets 3.10–3.14
  overall, but the Azure path specifically should stay in the
  Azure-supported sub-range). This caveat does not apply to Route A — Docker
  deployment is unaffected, since you control the base image.
- `infrastructure/README.md` walks through `terraform apply`, wiring GitHub
  Actions secrets (`REGISTRY_USERNAME`, `REGISTRY_PASSWORD`, `REGISTRY_URL`,
  `AZURE_STATIC_WEB_APPS_API_TOKEN`), and setting `VUE_APP_API_URL` in
  `.env.production` after `terraform output api_hostname`.

Recommendation: use Route A unless you have a specific reason to be on
Azure (existing subscription, org policy, etc.) — it's simpler, cheaper, and
is the actively maintained path (CHANGES.md §13 describes it replacing this
stack; `azure_funcs/`/`infrastructure/` are kept "untouched" but not the
primary path going forward).

## 7. Verifying the deployment

After `docker compose up -d --build` (or the equivalent Azure deploy)
finishes:

```bash
curl https://api.yourdomain.com/health-check      # expect: "alive"
```

Then open `https://yourdomain.com` in a browser and run one full simulation
end to end — pick any preset, hit run, confirm charts render and no console
errors appear.

For a deeper check, use the regression harness in `regression_harness/`
against your live URL — it replays a fixed set of numeric scenarios and
compares outputs to a trusted reference to 5 decimal places of relative
precision:

```bash
cd regression_harness
python3 vgi_regression.py capture --url https://api.yourdomain.com --out /tmp/deployed-capture
python3 vgi_regression.py compare baselines/v0 /tmp/deployed-capture --report report.md
```

If this reports scenario mismatches beyond the four intentionally-reserved
network IDs (1106, 1107, 1142, 1143 — deliberately excluded from
`/lv-network`, see CHANGES.md §16), something is wrong with the deployment,
not the code — check `docker compose logs -f api`.

Useful ongoing commands:

```bash
docker compose ps                 # both services should show "running (healthy)"
docker compose logs -f api        # simulation logs
docker compose logs -f web        # web/TLS logs
```

## 8. Practical tips

**Memory sizing.** Each simulation costs ~400 MB RAM while running, in a
dedicated worker subprocess. Total concurrent simulations =
`VGI_MAX_PARALLEL_SIMULATIONS` × number of gunicorn/uvicorn workers. The
`deployment/` compose file defaults `VGI_MAX_PARALLEL_SIMULATIONS=1`; the
compose `mem_limit: 3g` on the `api` container is your hard ceiling — a
pathological request can't take the whole server down, the container just
restarts. Raise `VGI_MAX_PARALLEL_SIMULATIONS` only alongside more server
RAM (rule of thumb from `deployment/README.md`: 4 GB server →
`VGI_MAX_PARALLEL_SIMULATIONS=1`, 8 GB → `=2`).

**Health checks.** `/health-check` on the API returns a plain "alive" — use
it for your load balancer / uptime monitor / Docker healthcheck probe (the
compose file already wires this up for you).

**Abuse protection already in place.** The Caddyfile shipped in
`deployment/` caps request bodies at 10 MB and rate-limits `POST /simulate`
to 10 requests/minute per IP (HTTP 429 beyond that) — this is the only
brake on the anonymous, CPU-expensive simulate endpoint, so don't remove it
without adding something equivalent. (Note: the Caddyfile's own comment
currently says the cap is "5 MB" — that comment is stale, the enforced
limit is 10 MB; a cosmetic mismatch, not a functional one, tracked in
IMPROVEMENTS.md §1.7.)

**DNS records to create** (for Route A): `A` records for `@`, `www`, and
`api`, all pointing at your server's IP. `www` redirects to the bare domain
at the Caddy layer — you don't need a separate certificate step for it.

**Smoke-test checklist after every deploy:**
1. `curl https://api.yourdomain.com/health-check` → `"alive"`.
2. Run one full simulation through the browser UI.
3. Run the regression harness against the live URL (§7).

## 9. Security items to close before public launch

`IMPROVEMENTS.md` §1 is a prioritised list of security work identified but
**not yet implemented**. Read the full file before going live publicly; the
highlights, by item number so you can cross-reference:

- **§1.1 (HIGH)** — app-level rate limiting on `/simulate` doesn't exist yet
  independent of Caddy; if you ever front the API with anything other than
  the shipped Caddyfile (a different reverse proxy, Azure Functions, bare
  `docker run`), there is currently **no** abuse brake at all.
- **§1.2 (HIGH)** — the simulation queue has no depth cap; a burst of
  requests can pile up memory with no bound.
- **§1.3 (MEDIUM)** — timed-out simulation workers aren't killed on
  multi-worker pools, just abandoned; repeated timeouts can exhaust worker
  slots.
- **§1.4 (MEDIUM)** — the API container currently runs as root; no `USER`
  directive in `docker_images/vgi_api.dockerfile`.
- **§1.5 (MEDIUM on shared hosts, LOW in containers)** — the network-model
  extraction cache lives at a predictable path in the system temp dir;
  a non-issue in a single-tenant container (which is what Route A gives
  you), worth hardening if you ever run multi-tenant.
- **§1.6 (MEDIUM)** — no dependency lock file committed; two builds weeks
  apart can pull different dependency versions.
- **§1.7 (LOW)** — assorted hygiene items (missing security headers on the
  API origin, the stale 5 MB/10 MB comment above, generic-500-body
  discipline).

None of these block getting the site running for a first look — they matter
before you point real public traffic at it and leave it unattended.

## 10. What does not exist yet

- **No authentication.** The API and site are fully anonymous by design —
  anyone with the URL can run simulations. This is a deliberate product
  decision (see IMPROVEMENTS.md §4), not an oversight, but it's exactly why
  §1's rate-limiting/abuse items matter.
- **No monitoring/metrics.** There's no `/metrics` endpoint, no error
  tracking, no alerting. IMPROVEMENTS.md §3 sketches what a minimal version
  would look like (simulation duration histogram, queue depth, timeout
  count) — worth adding once the site is live and you want visibility into
  whether it's healthy, rather than finding out from a user complaint.

If either of these becomes a requirement, treat IMPROVEMENTS.md as the
starting spec rather than starting from scratch.
