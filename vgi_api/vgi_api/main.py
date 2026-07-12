"""main.py — the FastAPI application (all HTTP endpoints).

HOW THIS FILE DIFFERS FROM THE ORIGINAL (v0) main.py
----------------------------------------------------
Every change is also marked inline with a FIX/CHANGE comment at the exact
location, and described in CHANGES.md at the repository root. Summary:

1. FIX(reliability): the simulation no longer runs inside the web-server
   process. OpenDSS and matplotlib hold process-global state and are not
   thread-safe — concurrent requests crashed the whole v0 process. The
   simulation now runs in dedicated worker subprocesses (see the
   "Simulation worker pool" section) with a configurable timeout
   (VGI_SIMULATION_TIMEOUT) and parallelism (VGI_MAX_PARALLEL_SIMULATIONS).
2. FIX(security): CORS was `allow_origins=["*"]` + `allow_credentials=True`
   (invalid per the CORS spec and wide open). Origins now come from the
   VGI_CORS_ORIGINS environment variable; credentials are off.
3. FIX(bug): the /simulate response dict listed the "mv_highlevel" key twice
   (the duplicate silently overwrote the first). Every original response key
   is preserved, each exactly once — the old frontend needs no changes.
4. FIX(bug): the validated lv_plot_list is now returned by
   validate_lv_parameters instead of being re-parsed from the raw query
   string here (the v0 validator dropped it — see validators.py).
5. CHANGE(feature): additive response keys — "convergence" (which of the 48
   power-flow steps failed to converge), "lv_unbalance"/"lv_unbalance_data"
   (phase-unbalance plot + CSV) and "lv_phase_pngs" (per-network per-phase
   voltage figures).
6. CHANGE(feature): new GET /network-topology endpoint serving the pre-built
   network JSON for the frontend's interactive map (no OpenDSS involved).
7. CHANGE(py3.14): deprecated FastAPI/asyncio idioms replaced (lifespan
   handler instead of on_event, get_running_loop, Query(examples=[...])).

The numeric outputs of /simulate are unchanged from v0 — verified against
the captured v0 baseline by regression_harness/vgi_regression.py (all 8
scenarios pass; worst relative difference ~5e-10, i.e. solver-stack noise).
"""

import asyncio
import base64
import concurrent.futures
import contextlib
import copy
import functools
import io
import json
import logging
import multiprocessing
import os
from pathlib import Path
from typing import Any, List, Optional

import fastapi
import numpy as np
from fastapi import File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from vgi_api import azureOptsXmpls as aox
from vgi_api.validation import (
    MV_FCS_HOSTS,
    MV_SOLAR_HOSTS,
    VALID_LV_NETWORKS_RURAL,
    VALID_LV_NETWORKS_URBAN,
    DefaultLV,
    LVElectricVehicleOptions,
    LVHPOptions,
    LVPVOptions,
    LVSmartMeterOptions,
    MVFCSOptions,
    MVSolarPVOptions,
    NetworkID,
    ProfileUnits,
    response_models,
    validate_lv_parameters,
    validate_profile,
)
from vgi_api.validation.types import DEFAULT_LV_NETWORKS, AllOptions


# CHANGE(py3.14): `@app.on_event("shutdown")` is deprecated in current
# FastAPI; the worker-pool teardown now lives in this lifespan handler.
@contextlib.asynccontextmanager
async def _lifespan(app: fastapi.FastAPI):
    yield
    _dispose_pool()


app = fastapi.FastAPI(lifespan=_lifespan)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
# FIX(security): the original configuration was
#     allow_origins=["*"] with allow_credentials=True
# which is both invalid per the CORS specification (browsers refuse to honour
# a wildcard origin when credentials are allowed) and needlessly permissive:
# any website on the internet could script requests against this API from its
# visitors' browsers.
#
# The allowed origins are now read from the VGI_CORS_ORIGINS environment
# variable (comma-separated), defaulting to the local dev frontend. In
# production set e.g.:
#     VGI_CORS_ORIGINS="https://<your-static-web-app>.azurestaticapps.net"
# `allow_credentials` is False because the API is anonymous — it neither sets
# nor reads cookies or Authorization headers.
origins = [
    o.strip()
    for o in os.environ.get(
        "VGI_CORS_ORIGINS",
        "http://localhost:8080,http://127.0.0.1:8080",
    ).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Simulation worker pool
# ---------------------------------------------------------------------------
# FIX(reliability): the simulation used to run *inside* the web-server
# process/thread. That had two serious consequences:
#
#   1. The OpenDSS engine (a native library behind a module-level singleton)
#      and matplotlib's pyplot interface both hold process-global state and
#      are not thread-safe. Two overlapping /simulate requests in one process
#      corrupted that state — during testing this crashed the whole worker
#      with a native signal (SIGILL inside matplotlib's C extension), taking
#      down every in-flight request.
#   2. The endpoint was `async def` running multi-second blocking work
#      directly on the event loop, so even /health-check stalled while a
#      simulation ran.
#
# The simulation is now executed in dedicated *subprocesses* via a
# ProcessPoolExecutor:
#
#   - Each worker process owns its own OpenDSS engine and matplotlib state,
#     and executes one job at a time on its main thread (the only
#     configuration pyplot supports). The thread-safety problem therefore
#     disappears *per process* — and the safe way to run simulations in
#     PARALLEL is simply more worker processes, never more threads.
#   - VGI_MAX_PARALLEL_SIMULATIONS (default 1) sets the pool size. Budget
#     roughly 400 MB of RAM per worker while a simulation runs: e.g. on the
#     P2v2 App Service plan (7 GB) a value of 2-4 is comfortable. Requests
#     beyond the pool size queue (fairly, FIFO) instead of failing.
#   - The "spawn" start method gives the worker a clean interpreter rather
#     than a fork()ed copy of the server (fork is unsafe with native libraries
#     that hold locks/state, such as the DSS engine).
#   - If the worker crashes (native fault) or exceeds the timeout, the API
#     process survives: we return a 500/504 to that request, dispose of the
#     broken pool and lazily build a fresh one for the next request.
#
# DEEP-DIVE: the first request after a cold start pays ~1-2 s extra while the
# worker process imports numpy/matplotlib/OpenDSS. The pool is kept alive
# between requests so subsequent requests do not pay this again.
_SIMULATION_TIMEOUT_S = float(os.environ.get("VGI_SIMULATION_TIMEOUT", "600"))

# How many simulations may run at the same time (in separate worker
# processes). See the comment block above before raising it: the constraint
# is memory, not correctness.
_MAX_PARALLEL_SIMULATIONS = max(
    1, int(os.environ.get("VGI_MAX_PARALLEL_SIMULATIONS", "1"))
)

_pool: Optional[concurrent.futures.ProcessPoolExecutor] = None


def _get_pool() -> concurrent.futures.ProcessPoolExecutor:
    # NOTE: the "spawn" start method re-executes the Python interpreter for
    # the worker and re-imports the parent's __main__ module. Every real
    # server entrypoint (uvicorn, gunicorn, the Azure Functions host, plain
    # `python -m` / script execution) has an importable __main__, so this is
    # transparent — but it means you cannot exercise /simulate from code piped
    # into `python` on stdin or from a bare REPL (the worker would fail to
    # start and the request returns 500). Use a script file for ad-hoc tests.
    global _pool
    if _pool is None:
        _pool = concurrent.futures.ProcessPoolExecutor(
            max_workers=_MAX_PARALLEL_SIMULATIONS,
            mp_context=multiprocessing.get_context("spawn"),
        )
    return _pool


def _dispose_pool() -> None:
    """Throw away a broken/hung pool. The next request builds a new one."""
    global _pool
    if _pool is not None:
        # cancel_futures requires py>=3.9; wait=False so the request that hit
        # the failure is not further delayed by worker teardown.
        _pool.shutdown(wait=False, cancel_futures=True)
        _pool = None


def _worker_run(parameters: dict) -> dict:
    """Executed inside the worker process (see _get_pool).

    The import happens here, in the worker, so the API (parent) process never
    loads the heavy simulation stack (OpenDSS engine, matplotlib, scipy) at
    all — it only ships this function's dotted name plus the pickled
    parameters to the worker.
    """
    from vgi_api import azure_mockup

    return azure_mockup.run_dss_simulation(parameters)


async def _run_simulation_in_subprocess(parameters: dict) -> dict:
    """Run the simulation in the worker process.

    Raises HTTPException(500) if the worker dies and HTTPException(504) if it
    exceeds the timeout.
    """
    # CHANGE(py3.14): get_event_loop() inside a coroutine is deprecated /
    # removed behaviour on modern Python; get_running_loop() is the intent.
    loop = asyncio.get_running_loop()
    try:
        return await asyncio.wait_for(
            loop.run_in_executor(_get_pool(), _worker_run, parameters),
            timeout=_SIMULATION_TIMEOUT_S,
        )
    except concurrent.futures.process.BrokenProcessPool:
        logging.exception("Simulation worker process crashed")
        _dispose_pool()
        raise HTTPException(
            status_code=500,
            detail="The simulation engine crashed while processing this request. "
            "Please try again; if the problem persists report the parameters used.",
        )
    except asyncio.TimeoutError:
        logging.error("Simulation timed out after %ss", _SIMULATION_TIMEOUT_S)
        # The worker is still busy with the abandoned job. With a single
        # worker, dispose of the pool so the next request gets a fresh worker
        # instead of queueing behind a possibly-hung job. With a parallel
        # pool (VGI_MAX_PARALLEL_SIMULATIONS > 1) we must NOT dispose — that
        # would cancel other users' in-flight simulations; the abandoned job
        # simply occupies one worker slot until it finishes on its own.
        if _MAX_PARALLEL_SIMULATIONS == 1:
            _dispose_pool()
        raise HTTPException(
            status_code=504,
            detail=f"Simulation did not complete within {_SIMULATION_TIMEOUT_S:.0f}s",
        )


def _b64(data: bytes) -> str:
    """Base64-encode PNG bytes for embedding in the JSON response."""
    return base64.b64encode(data).decode("utf-8")


def _prepare_csv(header: List[str], plot_data: np.ndarray) -> str:
    """Render a header + 2D array as CSV text for the download links."""
    handle = io.StringIO()
    np.savetxt(handle, X=plot_data, header=",".join(header), delimiter=",", comments="")
    handle.seek(0)
    return handle.read()


@app.post("/simulate")
async def simulate(
    dry_run: bool = Query(
        False,
        title="Dry run",
        description="Check all simulation arguments are valid without running simulation",
    ),
    n_id: NetworkID = Query(
        ...,
        title="Network ID",
        description="Choice of 11 kV integrated Medium-Low Voltage network",
    ),
    xfmr_scale: float = Query(
        1.0,
        ge=0.5,
        le=4,
        description="Medium Voltage transformer scaling",
    ),
    oltc_setpoint: float = Query(
        1.04,
        ge=0.95,
        le=1.10,
        description="Medium Voltage transformer on-load tap charger (OLTC) set point. Change the set point (in % pu) of the oltc",
    ),
    oltc_bandwidth: float = Query(
        0.013,
        ge=0.01,
        le=0.05,
        description="Change the bandwidth (in % pu) of the oltc",
    ),
    rs_pen: float = Query(
        0.8,
        ge=0,
        le=1,
        description="Percentage residential loads",
    ),
    lv_list: Optional[str] = Query(
        None,
        description="Provide a comma seperated list of up to 5 Low Voltage Network ids. If not provided you must select an option from `lv_default`",
        examples=["1101, 1105, 1103"],
    ),
    lv_plot_list: Optional[str] = Query(
        None,
        description="Provide a comma seperated list of up to 2 Low Voltage Network ids to plot. They must be either in `lv_list` or the networks in the `default_lv` selection",
    ),
    lv_default: Optional[DefaultLV] = Query(
        None,
        description="Choose a default set of Low Voltage Networks. If `lv_list` is provided `lv_list` takes precedence",
    ),
    mv_solar_pv_profile: MVSolarPVOptions = Query(
        MVSolarPVOptions.NONE,
        description="Select a example solar pv profile or select CSV to upload your own. If CSV selected you must provide `mv_solar_pv_csv`",
    ),
    mv_solar_pv_csv: Optional[UploadFile] = File(
        None, description="11kV connected solar photovoltaic (PV)"
    ),
    mv_solar_pv_profile_units: ProfileUnits = Query(
        ProfileUnits.KW,
        description="If `mv_solar_pv_csv` provided gives the units",
    ),
    mv_fcs_profile: MVFCSOptions = Query(
        MVFCSOptions.NONE,
        description="Select a example ev profile or select CSV to upload your own. If CSV selected you must provide `mv_fcs_charger_csv`",
    ),
    mv_fcs_csv: Optional[UploadFile] = File(
        None, description="11kV connected EV fast chargers' stations"
    ),
    mv_fcs_profile_units: ProfileUnits = Query(
        ProfileUnits.KW,
        description="If `mv_fcs_charger` provided gives the units",
    ),
    lv_smart_meter_profile: LVSmartMeterOptions = Query(
        LVSmartMeterOptions.OPTION1,
        description="",
    ),
    lv_smart_meter_csv: Optional[UploadFile] = File(None, description=""),
    lv_smart_meter_profile_units: ProfileUnits = Query(
        ProfileUnits.KW,
        description="",
    ),
    lv_ev_profile: LVElectricVehicleOptions = Query(
        LVElectricVehicleOptions.NONE,
        description="",
    ),
    lv_ev_csv: Optional[UploadFile] = File(None, title=""),
    lv_ev_profile_units: ProfileUnits = Query(
        ProfileUnits.KW,
        description="",
    ),
    lv_ev_pen: float = Query(
        0.0,
        ge=0,
        le=1,
        description="Percentage Electric Vehicle Penetration",
    ),
    lv_pv_profile: LVPVOptions = Query(
        LVPVOptions.NONE,
        description="",
    ),
    lv_pv_csv: Optional[UploadFile] = File(None, title=""),
    lv_pv_profile_units: ProfileUnits = Query(
        ProfileUnits.KW,
        description="",
    ),
    lv_pv_pen: float = Query(
        0.0,
        ge=0,
        le=1,
        description="Percentage PV Penetration",
    ),
    lv_hp_profile: LVHPOptions = Query(
        LVHPOptions.NONE,
        description="",
    ),
    lv_hp_csv: Optional[UploadFile] = File(None, title=""),
    lv_hp_profile_units: ProfileUnits = Query(
        ProfileUnits.KW,
        description="",
    ),
    lv_hp_pen: float = Query(
        0.0,
        ge=0,
        le=1,
        description="Percentage Heat Pump Penetration",
    ),
):

    # MV parameters are already valid. LV parameters need additional validation.
    # FIX(bug): validate_lv_parameters now also returns the *validated* plot
    # list (or None). Previously the endpoint re-parsed the raw lv_plot_list
    # query string itself, because the validator forgot to `return` the value
    # (see validators.py) — and crashed when lv_plot_list was combined with
    # lv_default.
    lv_list_validated, lv_plot_list_validated = validate_lv_parameters(
        lv_list, lv_default, lv_plot_list, n_id
    )

    # Validate Demand and Generation Profiles
    mv_solar_profile_array = validate_profile(
        mv_solar_pv_profile, mv_solar_pv_csv, mv_solar_pv_profile_units
    )

    mv_fcs_profile_array = validate_profile(
        mv_fcs_profile, mv_fcs_csv, mv_fcs_profile_units
    )

    smart_meter_profile_array = validate_profile(
        lv_smart_meter_profile, lv_smart_meter_csv, lv_smart_meter_profile_units
    )

    lv_ev_profile_array = validate_profile(
        lv_ev_profile, lv_ev_csv, lv_ev_profile_units
    )

    lv_pv_profile_array = validate_profile(
        lv_pv_profile, lv_pv_csv, lv_pv_profile_units
    )
    lv_hp_profile_array = validate_profile(
        lv_hp_profile, lv_hp_csv, lv_hp_profile_units
    )

    logging.info("Passing params to dss")

    if dry_run:
        return "valid"

    # Default plot selection: the first two simulated LV networks.
    plot_list = (
        lv_plot_list_validated if lv_plot_list_validated else lv_list_validated[:2]
    )

    # Pass parameters to dss
    parameters = copy.deepcopy(aox.run_dict0)

    parameters["network_data"]["n_id"] = int(n_id.value)
    parameters["network_data"]["xfmr_scale"] = xfmr_scale
    parameters["network_data"]["oltc_setpoint"] = oltc_setpoint * 100
    parameters["network_data"]["oltc_bandwidth"] = oltc_bandwidth * 100
    parameters["network_data"]["lv_sel"] = "lv_list"
    parameters["network_data"]["lv_list"] = [str(i) for i in lv_list_validated]
    parameters["rs_pen"] = rs_pen * 100
    parameters["slr_pen"] = lv_pv_pen * 100
    parameters["ev_pen"] = lv_ev_pen * 100
    parameters["hps_pen"] = lv_hp_pen * 100

    parameters["plot_options"]["lv_voltages"] = [str(i) for i in plot_list]

    # Add profiles to parameters. All profile arrays are in kW by this point
    # (validate_profile converts kWh and applies generation sign conventions).
    parameters["simulation_data"]["mv_solar_profile_array"] = mv_solar_profile_array
    parameters["simulation_data"]["mv_fcs_profile_array"] = mv_fcs_profile_array
    parameters["simulation_data"][
        "smart_meter_profile_array"
    ] = smart_meter_profile_array
    parameters["simulation_data"]["lv_ev_profile_array"] = lv_ev_profile_array
    parameters["simulation_data"]["lv_pv_profile_array"] = lv_pv_profile_array
    parameters["simulation_data"]["lv_hp_profile_array"] = lv_hp_profile_array

    # Run the simulation in the isolated worker process (see comments at the
    # top of this file). `results` is a plain dict of PNG bytes and numpy
    # arrays — see azure_mockup.run_dss_simulation for the exact contract.
    results = await _run_simulation_in_subprocess(parameters)

    # The numpy profile arrays are not JSON serialisable (and the client does
    # not need them echoed back), so drop them before returning the parameters.
    parameters.pop("simulation_data")

    # FIX(bug): the original response dict listed the "mv_highlevel" key twice
    # (the second entry silently overwrote the first) and base64-encoded the
    # same buffer twice. Each plot now appears exactly once.
    resultdict = {
        "parameters": parameters,
        # CHANGE(feature): convergence summary so the client can warn the user
        # when one or more of the 48 power-flow steps failed to converge (the
        # results for those half-hours are not physically meaningful). See
        # azure_mockup.run_dss_simulation for the exact contract.
        "convergence": results["convergence"],
        "mv_highlevel": _b64(results["mv_highlevel_png"]),
        "mv_highlevel_clean": _b64(results["mv_highlevel_clean_png"]),
        "lv_voltages": _b64(results["lv_voltages_png"]),
        "lv_comparison": _b64(results["lv_comparison_png"]),
        "lv_unbalance": _b64(results["lv_unbalance_png"]),
        # Per-phase customer-voltage figure per selected network, keyed by
        # network id, so the frontend can offer a network picker.
        "lv_phase_pngs": {
            net_id: _b64(png) for net_id, png in results["lv_phase_pngs"].items()
        },
        "mv_voltages": _b64(results["mv_voltages_png"]),
        "mv_powers": _b64(results["mv_powers_png"]),
        "trn_powers": _b64(results["trn_powers_png"]),
        "profile_options": _b64(results["profile_options_png"]),
        "profile_options_dgs": _b64(results["profile_options_dgs_png"]),
        "profile_options_fcs": _b64(results["profile_options_fcs_png"]),
        "pmry_loadings": _b64(results["pmry_loadings_png"]),
        "pmry_powers": _b64(results["pmry_powers_png"]),
        "primary_loadings_data": _prepare_csv(
            results["primary_loadings_header"], results["primary_loadings_data"]
        ),
        "mv_voltages_data": _prepare_csv(
            results["mv_voltages_header"], results["mv_voltages_data"]
        ),
        "trn_powers_data": _prepare_csv(
            results["trn_powers_header"], results["trn_powers_data"]
        ),
        "lv_comparison_data": _prepare_csv(
            results["lv_comparison_header"], results["lv_comparison_data"]
        ),
        "lv_unbalance_data": _prepare_csv(
            results["lv_unbalance_header"], results["lv_unbalance_data"]
        ),
    }

    return resultdict


@app.get("/lv-network", response_model=response_models.LVNetworks)
async def lv_network(
    n_id: NetworkID = Query(
        ...,
        title="Network ID",
        description="Choice of 11 kV integrated MV-LV network",
    ),
):
    """Return a list of valid LV networks"""

    if n_id == NetworkID.URBAN:
        networks = VALID_LV_NETWORKS_URBAN
    else:
        networks = VALID_LV_NETWORKS_RURAL

    return {"networks": networks}


@app.get("/lv-network-defaults", response_model=response_models.LVNetworks)
async def lv_network_defaults(
    n_id: NetworkID = Query(
        ...,
        title="Network ID",
        description="Choice of 11 kV integrated MV-LV network",
    ),
    lv_default: DefaultLV = Query(
        ...,
        description="Choose a default set of Low Voltage Networks. If `lv_list` is provided `lv_list` takes precedence",
    ),
):
    """Return the network ids of the network option"""

    return {"networks": DEFAULT_LV_NETWORKS[n_id][lv_default]}


@app.get("/get-options", response_model=List[str])
async def get_options(option_type: AllOptions):
    def get_members(option: Any) -> List[str]:

        return [member.value for _, member in option.__members__.items()]

    if option_type == AllOptions.MVSolarPVOptions:

        return get_members(MVSolarPVOptions)

    elif option_type == AllOptions.MVFCSOptions:

        return get_members(MVFCSOptions)

    elif option_type == AllOptions.LVSmartMeterOptions:

        return get_members(LVSmartMeterOptions)

    elif option_type == AllOptions.LVElectricVehicleOptions:

        return get_members(LVElectricVehicleOptions)

    elif option_type == AllOptions.LVPVOptions:

        return get_members(LVPVOptions)

    elif option_type == AllOptions.LVHPOptions:

        return get_members(LVHPOptions)


# CHANGE(feature): pre-built network topology served for the frontend's
# interactive network explorer / selector. The JSON files are generated offline
# by scripts/build_network_topology.py from the same .zip archives the
# simulation uses, and committed next to them — so this endpoint is a plain
# file read (no OpenDSS, no worker pool) and returns instantly.
_TOPOLOGY_DIR = Path(__file__).parent / "data"


@functools.lru_cache(maxsize=None)
def _load_topology(n_id: int) -> dict:
    path = _TOPOLOGY_DIR / f"network_topology_{n_id}.json"
    return json.loads(path.read_text())


@app.get("/network-topology")
async def network_topology(
    n_id: NetworkID = Query(
        ...,
        title="Network ID",
        description="Choice of 11 kV integrated MV-LV network",
    ),
):
    """Return the pre-built MV/LV topology for the network explorer.

    Shape (see scripts/build_network_topology.py for the full contract):
    ``{n_id, mv: {substation, buses[], lines[]},
       lv_networks: {"<mv_bus>": {mv_bus, xfmr_kva, n_feeders, n_houses,
                                  elec_dist_ohm, n_sections_from_sub,
                                  feeders[]}},
       mv_assets: {solar_pv[], fcs[]}}``

    ``mv_assets`` lists the LV network ids that host the lumped MV solar-farm
    and fast-charging-station demand (the RESERVED_LV_NETWORKS), so the
    frontend map can mark them distinctly. Added at serve time rather than in
    the pre-built JSON so it stays in step with run_dict0.
    """
    try:
        # Shallow copy: _load_topology's result is lru_cached and must not be
        # mutated.
        topology = dict(_load_topology(int(n_id.value)))
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"No topology data bundled for network {n_id.value}",
        )

    present = topology.get("lv_networks", {})
    topology["mv_assets"] = {
        "solar_pv": [n for n in MV_SOLAR_HOSTS if str(n) in present],
        "fcs": [n for n in MV_FCS_HOSTS if str(n) in present],
    }
    return topology


@app.get("/health-check")
def health_check():
    return "alive"


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
