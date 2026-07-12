#!/usr/bin/env bash
# Create the Python environment that runs the UNMODIFIED v0 reference code.
#
# v0 pins dss-python 0.10.7, which has no Apple-Silicon wheels; the closest
# installable solver is dss-python 0.12.1 (same dss.dss_capi_gr API — the v0
# code runs on it unchanged). numpy must stay < 1.24 (v0 builds ragged
# object arrays that newer numpy rejects) and Python must be < 3.11 (the
# 'bunch' dependency does not install on 3.11+).
#
# Usage: ./setup_v0_baseline_env.sh [python3.10-executable]
set -euo pipefail

PY="${1:-python3.10}"
HERE="$(cd "$(dirname "$0")" && pwd)"
VENV="$HERE/.venv-v0-baseline"

command -v "$PY" >/dev/null || {
    echo "error: $PY not found. Pass a Python 3.9/3.10 interpreter as the first argument." >&2
    exit 1
}

"$PY" -m venv "$VENV"
"$VENV/bin/pip" install --upgrade pip
"$VENV/bin/pip" install \
    "numpy==1.23.5" \
    "dss-python==0.12.1" \
    "scipy==1.10.1" \
    "matplotlib==3.7.5" \
    "fastapi==0.71.0" \
    "pydantic<2" \
    "uvicorn==0.16.0" \
    "python-multipart==0.0.5" \
    "azure-storage-blob" \
    "cmocean==2.0" \
    "hsluv" \
    "govuk-bank-holidays" \
    "progress" \
    "bunch" \
    "python-dateutil"

echo
echo "Done. Start the v0 reference server with:"
echo "  cd <path-to-v0-repo>/vgi_api && MPLBACKEND=Agg $VENV/bin/python -m uvicorn vgi_api.main:app --host 127.0.0.1 --port 8010"
