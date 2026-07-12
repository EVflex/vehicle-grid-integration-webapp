# CHANGES (see CHANGES.md at the repository root):
#
# The previous image was broken in two independent ways:
#   1. It installed Poetry from
#      https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py
#      — that installer was deprecated and then REMOVED upstream, so the build
#      fails today with a 404.
#   2. It was based on tiangolo/uvicorn-gunicorn-fastapi:python3.8-slim: the
#      image line is deprecated by its author, and Python 3.8 is end-of-life
#      (no security fixes).
#
# This version uses a plain, maintained python base image and installs the
# package with pip. Poetry is not needed at build time at all: vgi_api's
# pyproject.toml declares the poetry-core build backend, which pip drives
# natively via PEP 517 (`pip install ./vgi_api` resolves and installs all the
# dependencies declared in pyproject.toml).
# CHANGE(py3.14): 3.11 -> 3.14 after the pydantic-v2/FastAPI migration
# (CHANGES.md §12); outputs validated bit-identical against the 3.11 baseline.
FROM python:3.14-slim

COPY vgi_api /app/vgi_api

# gunicorn supervises multiple uvicorn worker *processes*. Worker processes
# (not threads) are the right scaling unit here: each API worker offloads
# simulations to its own single-job OpenDSS subprocess (see vgi_api/main.py),
# so nothing thread-unsafe ever runs concurrently in one process.
RUN pip install --no-cache-dir /app/vgi_api gunicorn

# NOTE: set VGI_CORS_ORIGINS to the frontend's origin when running in
# production, e.g.
#   docker run -e VGI_CORS_ORIGINS="https://<your-app>.azurestaticapps.net" ...
# Concurrency model: two gunicorn API workers; each lazily starts a pool of
# simulation worker subprocesses sized by VGI_MAX_PARALLEL_SIMULATIONS
# (default 1). Total parallel simulations = gunicorn workers x pool size;
# budget ~400 MB of RAM per simulation worker while a simulation runs.
CMD ["gunicorn", "vgi_api.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "2", \
     "--bind", "0.0.0.0:80", \
     "--timeout", "900"]
