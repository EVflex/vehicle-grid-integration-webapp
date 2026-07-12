# Hosting the VGI webapp on your own domain

This folder is the complete, self-contained deployment: **one small cloud
server, two containers, automatic HTTPS**. It replaces the old Azure
Functions + Static Web Apps + Terraform stack (`azure_funcs/`,
`infrastructure/`), which remains in the repository untouched if you ever
want it back.

What runs where:

| Piece | Code | Container |
|---|---|---|
| Simulation API (FastAPI + OpenDSS) | existing `vgi_api/` + existing `docker_images/vgi_api.dockerfile` — reused unchanged | `api` |
| Frontend (Vue app) | existing `src/` — reused unchanged, compiled at image build | `web` |
| HTTPS, static file serving, rate limiting | new `deployment/Caddyfile` | `web` |

Your site answers at `https://yourdomain.com` (www redirects there) and the
API at `https://api.yourdomain.com`.

---

## Step 1 — Rent a server (~€8–15/month)

Any Linux VPS works. Suggested: **Hetzner CX32** or **DigitalOcean Basic
4 GB** — 2+ vCPUs, **4 GB RAM minimum** (8 GB if you raise
`VGI_MAX_PARALLEL_SIMULATIONS`), Ubuntu 24.04 LTS. Add your SSH key when
creating it. Note the server's public IP address.

## Step 2 — Point your domain at the server

In your domain registrar's DNS panel create three records (TTL: default):

| Type | Name | Value |
|---|---|---|
| A | `@` | your server IP |
| A | `www` | your server IP |
| A | `api` | your server IP |

Wait until `ping yourdomain.com` answers from the new IP (usually minutes,
can be up to an hour). HTTPS certificates in Step 5 only work after DNS
resolves.

## Step 3 — Install Docker on the server

```bash
ssh root@YOUR_SERVER_IP
curl -fsSL https://get.docker.com | sh
```

Optional but recommended firewall (SSH + web only):

```bash
ufw allow 22 && ufw allow 80 && ufw allow 443 && ufw --force enable
```

## Step 4 — Copy this project to the server

From your Mac, in the folder that contains this project:

```bash
rsync -a --exclude node_modules --exclude dist --exclude .git \
  ./ root@YOUR_SERVER_IP:/opt/vgi/
```

(Or push the project to a Git remote and `git clone` it on the server —
better once you iterate, see Step 7.)

## Step 5 — Configure and launch

On the server:

```bash
cd /opt/vgi/deployment
cp .env.example .env
nano .env        # set DOMAIN=yourdomain.com and ACME_EMAIL=you@...
docker compose up -d --build
```

The first build takes ~5–10 minutes (it compiles the frontend and installs
the Python stack). Caddy obtains Let's Encrypt certificates automatically on
first request — there is nothing to configure for HTTPS.

## Step 6 — Verify

```bash
curl https://api.yourdomain.com/health-check   # -> "alive"
```

Then open `https://yourdomain.com` in a browser and run a simulation
end-to-end. Useful commands:

```bash
docker compose ps                 # both services "running (healthy)"
docker compose logs -f api        # simulation logs
docker compose logs -f web        # web/TLS logs
```

## Step 7 — Updating the site later

Copy the changed files up (rsync as in Step 4, or `git pull`), then:

```bash
cd /opt/vgi/deployment && docker compose up -d --build
```

Rebuilds are incremental and take seconds unless dependencies changed.
There is no database and no user state — the only thing on the server worth
keeping is the TLS certificate volume, which Docker preserves across
rebuilds. The server is fully disposable: a new one is these 7 steps again.

---

## Operations notes

- **Capacity**: each simulation takes ~1–2 s of CPU and ~400 MB RAM while
  running. Default settings allow 2 concurrent simulations; extra requests
  queue rather than fail. For an 8 GB server set
  `VGI_MAX_PARALLEL_SIMULATIONS=2` in `.env` (≈4 concurrent).
- **Abuse brake**: `/simulate` is rate-limited to 10 requests/minute per IP
  (HTTP 429 beyond that) — see `Caddyfile` to tune. The API is otherwise
  anonymous by design.
- **OS updates**: enable unattended upgrades on the server
  (`apt install unattended-upgrades`). Rebuild images occasionally
  (`docker compose build --pull --no-cache`) to pick up patched base images.
