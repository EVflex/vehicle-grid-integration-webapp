# Uploading this project to a fresh GitHub repository

You want the backend, the old front end, and the new front end in the new
repo. This file tells you exactly what to copy, what to leave out, and the
commands to do it. It does not touch any code — it is a copy/paste guide.

There is no `.git` directory here yet (this checkout was never a git repo),
so "push to GitHub" means: initialise git in a copy of this folder, commit
the right files, then push.

## Sizes (measured on this checkout)

| Item | Size | Note |
|---|---|---|
| `vgi_api/` excluding `.venv/` | ~67 MB | mostly `vgi_api/vgi_api/data/` (~66 MB) |
| `vgi_api/.venv/` | ~299 MB | **never commit** — a local virtualenv |
| `vgi_api/vgi_api/data/opendssnetworks/HV_UG_full.zip` | 9.0 MB | urban network model |
| `vgi_api/vgi_api/data/opendssnetworks/HV_UG-OHa_full.zip` | 21 MB | rural network model |
| `src/` (old front end) | 680 KB | |
| `event-frontend-v2/` excluding `node_modules/` | ~0.7 MB | |
| `event-frontend-v2/node_modules/` | 4.1 MB | **never commit** — reuses the parent `node_modules` at runtime anyway |
| root `node_modules/` | 199 MB | **never commit** |
| `azure_funcs/` | 12 MB | mostly two legacy `dss-python` wheel files |
| `regression_harness/` (incl. committed baselines) | 548 KB | |
| `infrastructure/`, `deployment/`, `docker_images/`, `.github/` | <100 KB combined | |
| the two PDFs at root | 2.4 MB + 1.2 MB | |

Total repo size after excluding `.venv` and both `node_modules` trees is
roughly **80–90 MB**. That is comfortably under GitHub's 100 MB per-file
limit and its soft 1–5 GB repo-size guidance — **no Git LFS needed.** The
two largest single files are the 21 MB and 9 MB network-model zips, both
far under the 100 MB hard limit.

## What already exists

A `.gitignore` already exists at the repo root. **Do not reuse it as-is** —
it has two problems you'd otherwise ship into the new repo:

- It ignores `package.json` and `package-lock.json`. That's almost
  certainly a mistake (probably added while chasing an unrelated noisy
  diff) — both files are required for the old front end to build at all.
- It ignores `*.env`, a pattern that is easy to misread: it matches names
  *ending* in `.env` (so a bare `.env`, e.g. `deployment/.env`), while
  `.env.development` / `.env.production` are **not** matched and stay
  committed — which is correct, they carry no secrets, just the dev/prod
  API URL. The corrected file below keeps the useful part explicit
  (`deployment/.env` stays ignored — it holds the deployer's real domain
  and contact email) without the confusing wildcard.

Write a corrected `.gitignore` (below) rather than copying the existing one.

`vgi_api/vgi_api/.gitignore` also exists (a leftover from an even older
Azure Functions template — ignores `bin/`, `obj/`, `.vs/`, etc.). It's
harmless to keep or drop; none of the paths it lists exist in this project.

## Classification of every top-level item

**REQUIRED** — the three things you asked for:
- `vgi_api/` — the backend, **excluding** `vgi_api/.venv/` (local virtualenv,
  never portable across machines) and the `__pycache__/` / `.pytest_cache/`
  dirs inside it.
- `src/` — the old front end's source.
- The root files the old front end's build needs alongside `src/`:
  `package.json`, `package-lock.json`, `babel.config.js`,
  `.env.development`, `.env.production`. (There is **no** root
  `public/index.html` or `vue.config.js` for the old front end — see the
  note below; nothing is missing on your end.)
- `event-frontend-v2/` — the new front end, **excluding**
  `event-frontend-v2/node_modules/` (it resolves the parent `node_modules`
  at runtime — see `LOCAL_SETUP.md` — so its own copy is redundant and it's
  4 MB of churn on every `npm install`).

**RECOMMENDED** — not strictly "backend + two front ends," but you'll want
them:
- `CHANGES.md` — the full change log against the original codebase.
- `IMPROVEMENTS.md` — the security/architecture to-do list for before public
  launch.
- `README.md`, `LICENSE`.
- `regression_harness/` — including `regression_harness/baselines/v0/`
  (548 KB total). This is the strongest correctness guard the project has;
  worth keeping even though you won't run it yourself day to day.
- The two PDFs (`deakin-HV-LV-models.pdf`,
  `democratizing-electricity-distribution-network-analysis.pdf`) if you
  want the background documentation to travel with the code.
- `.github/workflows/tests.yml` — runs the backend test suite on
  GitHub-hosted runners on every PR/push to `main`. Free CI with no secrets
  required (it no longer needs cloud storage credentials — see CHANGES.md
  §5). The other two workflow files
  (`deploy_azurewebapp_api.yaml`, `azure-static-web-apps-*.yml`) only fire
  if you wire up Azure secrets; harmless to leave in, but you can drop them
  if you're certain you'll never use the Azure route.
- `deployment/` — the self-hosted Docker + Caddy deployment. You said you
  don't personally need this, but it's what your deployment colleague will
  use (see `HANDOVER.md`) — include it so the same repo serves both of you.
- `docker_images/` — the Dockerfile the `deployment/` compose file (and the
  legacy Azure workflow) build from. Required if you keep either deployment
  route.

**OPTIONAL / LEGACY** — the old Azure path, superseded by `deployment/` but
left in place on purpose (see CHANGES.md §13):
- `azure_funcs/` (12 MB, mostly two 2021-era `dss-python` wheel files that
  are no longer even referenced by code — see CHANGES.md §5).
- `infrastructure/` (Terraform for the Azure stack).

Keep these if there's any chance you'll fall back to Azure; drop them if
you've committed to the self-hosted route to shave 12 MB and reduce clutter.

**EXCLUDE** — never commit these:
- `node_modules/` (root, 199 MB) and `event-frontend-v2/node_modules/`
  (4 MB) — reinstalled from `package.json`/`package-lock.json`.
- `vgi_api/.venv/` (299 MB) — reinstalled from `pyproject.toml`.
- `__pycache__/`, `*.pyc`, `.pytest_cache/` — Python build artefacts,
  regenerated automatically. Present today at `vgi_api/.pytest_cache/`,
  `vgi_api/tests/__pycache__/`, `vgi_api/scripts/__pycache__/`,
  `vgi_api/vgi_api/__pycache__/`, `vgi_api/vgi_api/validation/__pycache__/`.
- `.DS_Store` — macOS Finder metadata. Present today at nine locations
  (repo root, `vgi_api/`, `vgi_api/vgi_api/`, `vgi_api/vgi_api/data/` and
  three subfolders under it, `event-frontend-v2/`,
  `event-frontend-v2/src/`). All safe to delete; regenerate themselves and
  carry no useful content.
- `dist/` — build output (doesn't exist in this checkout, but the old
  front end's `npm run build` creates it).

## Files not mentioned in the brief, for completeness

A few files sit at the repo root that weren't named above. They're
documentation/planning artefacts, not code the app needs to run:
`FEATURE_PLAN.md`, `FRONTEND_REDESIGN_HANDOFF.md`,
`OPUS_IMPLEMENTATION_BRIEF.md`, `electric_vehicles-profile-template.csv`
(a small sample CSV referenced by the frontend's upload-format hint, in
practice already inside `src/`/`event-frontend-v2/` builds — check before
dropping it, since a CSV named exactly this is what the UI links to for the
"download a template" feature). Treat these as RECOMMENDED alongside
`CHANGES.md` — they explain *why* the code looks the way it does — unless
you'd rather keep the new repo lean, in which case they're safe to drop;
nothing at runtime reads `FEATURE_PLAN.md`, `FRONTEND_REDESIGN_HANDOFF.md`,
or `OPUS_IMPLEMENTATION_BRIEF.md`.

`.claude/` (a `launch.json` used by this development environment's preview
tooling) is developer-machine-specific; leave it out unless you specifically
want it.

## A note on the old front end's build files

The brief for this document assumed there might be a root `public/` folder
or `vue.config.js` for the old front end (`src/`). There isn't one — this
checkout genuinely has no `public/index.html` and no root `vue.config.js`.
That's not a gap in what you're about to copy: `@vue/cli-service` falls back
to a built-in generic `index.html` template
(`node_modules/@vue/cli-service/lib/config/index-default.html`, title "Vue
App") when `public/index.html` is absent, and it only wires up the
`copy-webpack-plugin` step for a `public/` directory if that directory
exists (`node_modules/@vue/cli-service/lib/config/app.js`). The build
already works this way today (`deployment/web.dockerfile` builds `src/`
with exactly this file set — package.json, package-lock.json,
babel.config.js, src/ — and CHANGES.md §13 says it was verified locally).
The only user-visible effect is a generic "Vue App" browser-tab title
instead of a custom one; cosmetic, not a blocker.

## `.gitignore` to drop in (fixes the two problems above)

```gitignore
# Dependencies (reinstalled from package.json / pyproject.toml)
node_modules/
vgi_api/.venv/

# Python build artefacts
__pycache__/
*.py[cod]
.pytest_cache/

# Build output
dist/

# macOS
.DS_Store

# Editors
.vscode/
.idea/

# Local env overrides only (NOT .env.development / .env.production —
# those are committed on purpose, see HANDOVER.md)
.env.local
.env.*.local

# The deployer's real environment file (holds their domain + contact email;
# deployment/.env.example is the committed template)
deployment/.env
```

If you decide to drop `azure_funcs/` and `infrastructure/` per the
OPTIONAL/LEGACY note above, no `.gitignore` change is needed — you'd just
not copy those two folders in the `rsync` step below.

## Copying the right file set

Run this from the parent of the current project folder (adjust
`vehicle-grid-integration-webapp-features` and `new-repo` to your actual
paths):

```bash
rsync -a \
  --exclude node_modules \
  --exclude .venv \
  --exclude __pycache__ \
  --exclude .pytest_cache \
  --exclude .DS_Store \
  --exclude dist \
  --exclude .claude \
  vehicle-grid-integration-webapp-features/ new-repo/
```

This copies everything else, including `azure_funcs/` and `infrastructure/`
— delete those two afterwards in `new-repo/` if you decided to drop them:

```bash
rm -rf new-repo/azure_funcs new-repo/infrastructure
```

## Git commands to initialise and push

```bash
cd new-repo

# 1. Write the corrected .gitignore FIRST, before any add/commit, so the
#    excluded paths never enter git's index in the first place.
#    (paste the .gitignore content above into new-repo/.gitignore)

git init
git add .
git status               # sanity check — confirm no .venv/, node_modules/,
                          # __pycache__/, or .DS_Store entries are staged
git commit -m "Initial commit: VGI backend, old front end, new front end"

git remote add origin https://github.com/<your-org-or-user>/<new-repo>.git
git branch -M main
git push -u origin main
```

If `git status` after `git add .` shows anything under `vgi_api/.venv/`,
`node_modules/`, or `event-frontend-v2/node_modules/`, stop and check the
`.gitignore` is actually in place and spelled correctly before committing —
pushing 300+ MB of virtualenv/node_modules is avoidable and will make the
repo slow to clone.
