# VGI numeric regression harness

A tool for answering one question: **does new code still produce the same
simulation results as the trusted v0 reference?**

It treats every version of the code as a black box behind its HTTP API,
runs an identical, deterministic set of `/simulate` requests against each,
and compares the **numeric power-flow outputs** cell by cell. Because v0
and newer code can never share one Python environment (incompatible
pydantic / fastapi / dss-python pins), the HTTP API is the only comparison
surface that will keep working for every future version — no imports, no
shared dependencies, nothing to keep in sync.

```
vgi_regression.py           the tool (pure standard library, any Python >= 3.8)
setup_v0_baseline_env.sh    creates the environment that runs the v0 reference
baselines/v0/               the captured v0 reference outputs (commit this!)
```

## What is compared, and why

| output | role in comparison |
|---|---|
| `primary_loadings_data`, `mv_voltages_data`, `trn_powers_data`, `lv_comparison_data` | **Ground truth.** The four numeric CSV datasets in the `/simulate` response (48 half-hour steps each). Compared element-wise against tolerance. |
| the 12 PNG plots | Presence only. Plots are rendered *from* the numbers above, and their bytes legitimately change with matplotlib versions — comparing pixels would only produce false alarms. Byte-identical plots are reported as a bonus. |
| `/lv-network`, `/lv-network-defaults`, `/get-options` | Exact JSON equality (API contract check). |
| HTTP status per scenario | Must match (a scenario that starts erroring — or starts succeeding — is flagged). |

**Determinism.** The simulation seeds its random number generator with
`rand_seed = 0` (`azureOptsXmpls.run_dict0`), and the API never overrides
it. Identical inputs on identical code therefore give *identical* numbers
— every EV/PV/heat-pump allocation included. This is what makes exact
comparison possible; if that seed is ever removed or made request-dependent,
comparison at tight tolerance stops being meaningful.

**Tolerance.** Default: `|a-b| <= 1e-8 + 1e-6 * max(|a|,|b|)`.
Calibration points:

- identical code, identical solver: difference is exactly **0**;
- solver-stack upgrades (dss-python 0.12 → 0.15, numpy 1.23 → 2.x):
  observed max relative difference **~5e-10**;
- OpenDSS's own power-flow convergence tolerance: **1e-4**;
- a genuine modelling bug (wrong load allocated, wrong profile, wrong
  transformer): typically **>> 1e-4**.

The default `rtol 1e-6` sits comfortably between "numerical noise" and
"real physics change". Tighten with `--rtol 0 --atol 0` to demand
bit-for-bit identity (appropriate when you did not change the solver
stack); loosen only with a written justification.

## Workflow

### One-time: capture the v0 baseline

```bash
# environment for the unmodified v0 code (needs python 3.9/3.10 — see script header)
./setup_v0_baseline_env.sh python3.10

# run the v0 reference server
cd <v0-repo>/vgi_api
MPLBACKEND=Agg <this-dir>/.venv-v0-baseline/bin/python -m uvicorn vgi_api.main:app --port 8010

# capture (from this directory)
python3 vgi_regression.py capture --url http://127.0.0.1:8010 \
    --out baselines/v0 --label "v0 reference"
```

`baselines/v0/` is now the durable reference — **commit it to git**. You
never need to run v0 again unless you extend the scenario matrix.

### Every time you change simulation code

```bash
# run YOUR code's API (its own environment, any port)
cd <your-repo>/vgi_api && python -m uvicorn vgi_api.main:app --port 8001

python3 vgi_regression.py capture --url http://127.0.0.1:8001 --out /tmp/candidate
python3 vgi_regression.py compare baselines/v0 /tmp/candidate --report report.md
echo $?   # 0 = pass, 1 = differences found
```

The console (and `report.md`) show one line per scenario with the worst
relative/absolute difference, and for failures, the exact rows/columns and
values that diverged.

### Reading a failure

- `max rel diff` around `1e-10` … `1e-9`: numerical noise from a
  solver/numpy upgrade. Fine. (Confirm you actually changed the stack.)
- differences above `1e-4`, or confined to specific columns (one LV
  network, one transformer): a real behaviour change — inspect the
  offending columns listed in the report before trusting the new code.
- `header mismatch` / `shape mismatch`: the output format changed —
  the frontend and any downstream users are affected.
- `HTTP status differs`: a request that used to work now errors (or vice
  versa). Deliberate bug-fixes look like this too — the default scenario
  matrix avoids requests that crash v0, so on the default matrix this
  always deserves attention.

## The scenario matrix

`python3 vgi_regression.py scenarios` lists it. Eight deterministic
scenarios cover: both networks (urban 1060, rural 1061), all three default
LV sets and an explicit `lv_list` + `lv_plot_list`, EV / PV / heat-pump
penetrations separately and combined, non-default transformer scaling and
OLTC settings, built-in MV solar + fast-charging-station profiles, and
user-uploaded CSV profiles (generated deterministically by the harness).

Add scenarios by copying `DEFAULT_SCENARIOS` to a JSON file and passing
`--scenarios my_scenarios.json` to both `capture` and `compare` runs —
then re-capture the v0 baseline once with the same file.

Two known v0 crashes are deliberately *excluded* (they 500 on v0, so there
is nothing numeric to compare): `lv_plot_list` combined with `lv_default`,
and a single-network `lv_list`. Both are fixed in this repo (CHANGES.md
§1.1, §1.4).

## Caveats

- **The baseline solver is dss-python 0.12.1, not v0's pinned 0.10.7**,
  because 0.10.7 has no Apple-Silicon wheels. The v0 *code* is unmodified;
  only the solver library differs, and the 0.12-vs-0.15 comparison already
  bounds solver-version noise at ~5e-10 relative. On an x86_64 machine you
  can build the baseline env with dss-python 0.10.7 for a fully faithful
  reference.
- The harness compares **what the API returns**. Quantities computed but
  not returned (e.g. `record_solution(full=True)` research extras) are out
  of scope; validate those with the in-repo test suite.
- Capture times: first request per network unzips the network models —
  the first scenario on each network is slow on v0 (no cache). Expect a
  full v0 capture to take a few minutes.
