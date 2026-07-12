# VGI_API

The Vehicle Grid Integration API: a FastAPI application that runs OpenDSS
simulations of integrated MV-LV distribution networks.

**Python: 3.10 – 3.14.** (See CHANGES.md §12 at the repository root — the
code was migrated to pydantic v2 / current FastAPI and is verified on 3.11
and 3.14.)

All data (network models and demand/generation profiles) ships inside the
package under `vgi_api/data/` — no cloud storage, credentials, or environment
variables are required to run locally.

## Run the API locally (plain pip)

From the directory containing this README:

```bash
python3 -m venv .venv
.venv/bin/pip install .
.venv/bin/uvicorn vgi_api:app --port 8000
```

Then open http://127.0.0.1:8000/docs for the interactive API documentation.

## Development mode (Poetry)

Alternatively install [Poetry](https://python-poetry.org/docs/), which
manages a virtual environment and the dev dependencies for you:

```bash
poetry install
poetry run uvicorn vgi_api:app --reload --port 8000
```

The `--reload` flag restarts the server whenever you alter code.

### Optional environment variables

| Variable                       | Default | Info                                             |
| ------------------------------ | ------- | ------------------------------------------------ |
| `VGI_CORS_ORIGINS`             | local dev frontend | Comma-separated allowed browser origins |
| `VGI_MAX_PARALLEL_SIMULATIONS` | 1       | Simulation worker subprocesses (~400 MB RAM each) |
| `VGI_SIMULATION_TIMEOUT`       | 600     | Per-simulation timeout in seconds                |

### Run unit tests

```bash
poetry run pytest tests
```
