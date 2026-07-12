# Running this project on a fresh computer

Standalone instructions to get the backend and both front ends running
locally. Written for macOS/Linux; Windows deltas are called out where
relevant. Every command below is copy-pasteable and was checked against the
actual files in this repo (`package.json` scripts, ports in config files,
the pyproject build backend) — nothing here is guessed.

## Prerequisites

- **Python 3.10–3.14.** Verified end-to-end on 3.11 and 3.14
  (`vgi_api/pyproject.toml`: `python = ">=3.10,<3.15"`).
- **Node.js.** The old front end (`src/`, package.json at repo root) uses
  Vue CLI 4 / webpack 4, whose asset hashing breaks on Node's newer OpenSSL
  defaults — you must pass `NODE_OPTIONS=--openssl-legacy-provider` when
  running or building it. This is confirmed working with Node 24
  (`docker_images` and `deployment/web.dockerfile` both build the old
  front end on `node:24-slim` with this flag) — any modern Node version
  (18+) plus the flag should work; there is no known upper bound. The new
  front end (`event-frontend-v2/`) uses the same toolchain (same
  `@vue/cli-service` version) so it needs the same flag.
- **git.**
- On Windows without Node already installed: get it from
  https://nodejs.org/en/download/ (includes npm).

## Backend

All commands below assume you're starting from the repo root.

### 1. Create a virtual environment and install

```bash
cd vgi_api
python3 -m venv .venv
.venv/bin/pip install .
```

`vgi_api/pyproject.toml` declares `build-backend = "poetry.core.masonry.api"`
— pip drives this natively via PEP 517, so a plain `pip install .` resolves
and installs everything in `pyproject.toml` without needing Poetry
installed at all. (This is exactly what `docker_images/vgi_api.dockerfile`
does: `pip install /app/vgi_api`.) If you prefer Poetry for day-to-day
development (dependency locking, `poetry run`), that works too:
`poetry install` from `vgi_api/`.

All simulation data (network models, demand/generation profile CSVs) ships
inside the package under `vgi_api/vgi_api/data/` — no cloud storage,
credentials, or extra environment variables are required to run locally.

### 2. Run the server

From the **repo root** (not `vgi_api/`):

```bash
MPLBACKEND=Agg vgi_api/.venv/bin/uvicorn vgi_api.main:app --app-dir vgi_api --port 8000
```

or, equivalently, from inside `vgi_api/`:

```bash
cd vgi_api
MPLBACKEND=Agg .venv/bin/uvicorn vgi_api:app --port 8000
```

(`vgi_api/vgi_api/__init__.py` does `from .main import app`, so both
`vgi_api.main:app` with `--app-dir vgi_api` and the shorter `vgi_api:app`
from inside that directory resolve to the same app.)

`MPLBACKEND=Agg` is a belt-and-braces flag: `vgi_api/vgi_api/azure_mockup.py`
already calls `matplotlib.use("agg")` in code before anything imports
`pyplot`, so plots render headless without a display even if you omit this
— but setting it explicitly avoids any chance of a GUI backend (Tk, Qt)
being picked first on a machine that has one installed, which would error
out on a headless server or hang waiting for a display. Harmless either
way; recommended for servers, optional for a local dev machine with a
normal Python install.

Once it's running, open http://127.0.0.1:8000/docs for interactive API
documentation, or http://127.0.0.1:8000/health-check (expect `"alive"`).

**Expect the first request to be slow** (a few seconds) — the worker pool
spawns simulation subprocesses lazily on first use ("cold start"), and the
first call also extracts one of the two network-model zips
(`vgi_api/vgi_api/data/opendssnetworks/*.zip`, 9–21 MB) into a cache
directory under the system temp dir. Subsequent requests reuse the warm
worker and the extracted cache, and are much faster (~1.1 s per
simulation).

### 3. Run the tests

```bash
cd vgi_api
.venv/bin/pytest tests
```

Expect 133 passed. A few tests are marked `slow` (engine-backed
cross-checks); skip them for a quick check with `-m "not slow"`.

### Optional environment variables

| Variable | Default | Purpose |
|---|---|---|
| `VGI_CORS_ORIGINS` | permissive local default | Comma-separated allowed browser origins |
| `VGI_MAX_PARALLEL_SIMULATIONS` | 1 | Simulation worker subprocesses (~400 MB RAM each) |
| `VGI_SIMULATION_TIMEOUT` | 600 | Per-simulation timeout, seconds |

You generally don't need to set any of these for local development — the
defaults work with both front ends out of the box (see the dev-proxy setup
below).

## Old front end (`src/`, repo root)

### 1. Install

From the repo root:

```bash
npm install
```

### 2. Serve

`package.json`'s `serve` script is `vue-cli-service serve` — run it with
the legacy-OpenSSL flag:

```bash
NODE_OPTIONS=--openssl-legacy-provider npm run serve
```

This starts on Vue CLI's default port, **8080** (no `vue.config.js` at the
repo root overrides it — confirmed by checking for one; there isn't one).
If 8080 is already taken (e.g. you also have the new front end running —
see below), pass a different port explicitly:

```bash
NODE_OPTIONS=--openssl-legacy-provider npx vue-cli-service serve --port 8081
```

### 3. How it finds the API

`.env.development` at the repo root sets
`VUE_APP_API_URL="http://127.0.0.1:8000"` — so with the backend running on
port 8000 as above, the old front end calls it directly (full CORS request,
not a dev proxy). Make sure `VGI_CORS_ORIGINS` on the backend includes
whatever origin the old front end actually serves on (e.g.
`http://localhost:8081` if you used `--port 8081`), or you'll see CORS
errors in the browser console with the request succeeding via `curl`.

`.env.production` points at the (now largely superseded) Azure URL — only
relevant if you deliberately want to test against a deployed backend
instead of local.

## New front end (`event-frontend-v2/`)

### 1. No separate install needed

`event-frontend-v2/` has its own `package.json` but **reuses the parent
`node_modules`** — Node's module resolution walks up directories to find
it, so as long as you've run `npm install` at the repo root (previous
section), you do not need to run `npm install` again inside
`event-frontend-v2/`.

### 2. Serve

```bash
cd event-frontend-v2
NODE_OPTIONS=--openssl-legacy-provider npx vue-cli-service serve
```

This also defaults to port **8080** — if the old front end is already
running there, Vue CLI will prompt to use the next free port (or pass
`--port` explicitly, same as above).

### 3. How it finds the API — dev proxy, no CORS needed

Unlike the old front end, `event-frontend-v2/vue.config.js` proxies API
paths through the dev server itself:

```js
devServer: {
  proxy: {
    "^/(get-options|lv-network|lv-network-defaults|network-topology|simulate)": {
      target: process.env.VGI_API_TARGET || "http://127.0.0.1:8000",
      changeOrigin: true
    }
  }
}
```

So the browser calls same-origin (`http://localhost:8080/simulate`, etc.),
and the dev server forwards to `127.0.0.1:8000` — no CORS configuration
needed on the backend for this front end during development.
`event-frontend-v2/.env.development` sets `VUE_APP_API_URL=""` (empty —
relative URLs, which is what makes the proxy work); `.env.production` has
the absolute Azure URL, baked in only at production build time.

Override the proxy target with `VGI_API_TARGET` if your backend runs
somewhere other than `127.0.0.1:8000`.

### 4. Mock-API alternative (no Python backend needed)

For frontend-only work, `event-frontend-v2/dev-mock-api.js` is a
dependency-free mock of the API (plain Node `http`, no npm packages) that
returns realistically-shaped data (matching `azure_mockup.py`'s CSV column
layout) without running any OpenDSS simulation. Per its own header comment:

```bash
node event-frontend-v2/dev-mock-api.js
```

It listens on **port 8000** — the same port the real backend uses — so you
can point the front end at it with no config changes. Point
`VGI_API_TARGET` at a different port if you're running it alongside the
real backend, e.g.:

```bash
VGI_API_TARGET=http://127.0.0.1:8010 node event-frontend-v2/dev-mock-api.js &
cd event-frontend-v2 && VGI_API_TARGET=http://127.0.0.1:8010 NODE_OPTIONS=--openssl-legacy-provider npx vue-cli-service serve
```

## Quick reference: the four dev processes and their ports

| Process | Command | Port |
|---|---|---|
| Backend | `MPLBACKEND=Agg vgi_api/.venv/bin/uvicorn vgi_api.main:app --app-dir vgi_api --port 8000` | 8000 |
| Old front end | `NODE_OPTIONS=--openssl-legacy-provider npx vue-cli-service serve --port 8081` (from repo root) | 8081 (or 8080 if run alone) |
| New front end | `cd event-frontend-v2 && NODE_OPTIONS=--openssl-legacy-provider npx vue-cli-service serve` | 8080 |
| Mock API (optional, replaces backend) | `node event-frontend-v2/dev-mock-api.js` | 8000 |

(This matches the project's own `.claude/launch.json`, which defines
exactly these four run configurations for local preview.)

## Troubleshooting

**`Error: error:0308010C:digital envelope routines::unsupported`** (or
similar OpenSSL/webpack error) when running `npm run serve` or
`vue-cli-service build`: you forgot `NODE_OPTIONS=--openssl-legacy-provider`.
This happens on Node 17+ because webpack 4's hashing uses an MD4-based
digest that newer OpenSSL (as bundled in modern Node) rejects by default.
Add the flag to the command, or `export NODE_OPTIONS=--openssl-legacy-provider`
once per shell session before running any frontend command.

**`Error: listen EADDRINUSE: address already in use :::8080`** (or `:8000`):
something is already bound to that port. Either stop the other process, or
pass `--port <N>` (Vue CLI) — the uvicorn backend takes `--port` too. On
macOS/Linux, find what's using a port with `lsof -i :8080`.

**`/simulate` returns HTTP 500 when the backend was started in an unusual
way** (e.g. run from a plain Python REPL, `python -c "..."`, or any context
without a real `__main__` module): the simulation worker pool uses
Python's `multiprocessing` "spawn" start method, which re-executes the
interpreter and re-imports the parent process's `__main__` module for each
worker. Every normal server entrypoint — `uvicorn`, `gunicorn`, the Azure
Functions host, or plain `python -m`/script execution — has an importable
`__main__`, so this is a non-issue for every command in this document. It
only bites you if you try to start the app in a non-standard way (e.g.
importing and calling `app` interactively) — if you hit this, run it via
one of the documented commands instead.

**Plots come back blank, or the process errors trying to open a display
(`Could not connect to display`, Tkinter/Qt errors) on a headless
Linux box**: set `MPLBACKEND=Agg` explicitly when starting uvicorn (see
step 2 above) — it should not be necessary given the code's own
`matplotlib.use("agg")` call, but is a safe override if you ever see this.

**First `/simulate` request after starting the backend takes several
seconds**: expected — see "cold start" note under backend step 2. Not a
bug; subsequent requests are fast.

## Windows notes

- Use the same commands via PowerShell or WSL; `NODE_OPTIONS` set inline
  (`NODE_OPTIONS=--openssl-legacy-provider npm run serve`) is a
  bash/zsh-ism — on plain PowerShell set it as a separate statement first:
  `$env:NODE_OPTIONS="--openssl-legacy-provider"` then run the command.
- The backend's network-model cache (`vgi_api/vgi_api/funcsTuring.py`,
  `_NETWORK_CACHE_ROOT`) tries to symlink the shared read-only network-model
  tree into each simulation's temp directory; on Windows without Developer
  Mode or admin rights, symlink creation can fail with a permissions error.
  The code already falls back to a full directory copy in that case
  (slower, but correct) — no action needed, just expect the first request
  after a cold cache to take longer on Windows than on macOS/Linux.
- WSL (Windows Subsystem for Linux) is the simplest way to get a
  Linux-like environment if you hit friction with native Windows Python/Node
  tooling.
