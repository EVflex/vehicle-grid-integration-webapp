# Adding a new network model to the dropdown

Today the app offers exactly two MV-LV network models: "urban" (`n_id`
1060) and "rural" (`n_id` 1061). This is a step-by-step checklist of every
place that needs to change to add a third, plus a frank verdict on how hard
it actually is.

## The short answer

**Will it be easy to have it work with existing simulation code?** Mostly
yes, with one real catch. The simulation engine (`funcsTuring.py`,
`slesNtwk_turing.py`) is generic over a run-dict and doesn't hard-code
network structure beyond a couple of small, findable spots (listed below).
If your new network is a **MV-LV OpenDSS model in the same file layout as
the existing two** (same top-level `.dss` file names, same `lvNetworks/`
subfolder convention — see §3), wiring it into the API is roughly **a day
of work**: a new enum value, a handful of dict entries, one validation
if/elif that currently has a latent bug you'll trip over immediately (§5),
and a topology JSON regeneration. The genuinely hard part is not the
wiring — it's **producing the OpenDSS model files themselves** in the
expected structure with correctly-named buses, feeders, and a lumped-load
representation compatible with the demand-allocation code (§4, §6). If you
already have a network in that shape (e.g. from the same UKGDS/Deakin model
family the existing two came from), budget a day for wiring plus whatever
validation and regression-testing you do. If you're building the model from
scratch, that's a separate, much larger modelling task outside this
document's scope.

**Recommended acceptance gate**: after wiring, run the full backend test
suite (`pytest tests`, 133 tests today) and, if you can get a comparable
reference simulation for the new network from elsewhere, extend the
regression harness (`regression_harness/`) with a scenario for it. Use the
existing 1061 (rural) wiring as your template throughout — it's the newer
and cleaner of the two entries in each of the touch points below.

## Step-by-step checklist

### 1. Add the enum value

**File:** `vgi_api/vgi_api/validation/types.py`

```python
class NetworkID(str, Enum):
    URBAN = "1060"
    RURAL = "1061"
    # new: MY_NETWORK = "1062"   (pick the next free id used by slesNtwk_turing.py's
    #                             fdrsLoc/fdrs dicts — 1062-1066 are already reserved
    #                             in comments there for exactly this purpose)
```

This is what FastAPI uses for `n_id` query-parameter validation on every
endpoint (`/simulate`, `/lv-network`, `/lv-network-defaults`,
`/network-topology`) — get this right first, everything downstream depends
on `NetworkID` accepting the new value.

Also add a preset-network entry to `DEFAULT_LV_NETWORKS` in the same file
(used by `/lv-network-defaults` and both front ends' "preset" scenario
buttons):

```python
DEFAULT_LV_NETWORKS: Dict[NetworkID, Dict[DefaultLV, List[int]]] = {
    NetworkID.RURAL: {...},
    NetworkID.URBAN: {...},
    NetworkID.MY_NETWORK: {
        DefaultLV.NEAR_SUB: [...],   # pick 5 real LV network ids from the new model
        DefaultLV.NEAR_EDGE: [...],
        DefaultLV.MIXED: [...],
    },
}
```

### 2. Fix the two if/elif chains that assume exactly two networks (do this or you will get an opaque crash)

Two places branch on `NetworkID.URBAN` / `NetworkID.RURAL` with **no else
clause**, which is fine for two networks but breaks silently — or not so
silently — for a third:

**`vgi_api/vgi_api/main.py`, the `/lv-network` endpoint** (~line 519):
```python
if n_id == NetworkID.URBAN:
    networks = VALID_LV_NETWORKS_URBAN
else:
    networks = VALID_LV_NETWORKS_RURAL
```
This is an `if`/`else`, not `if`/`elif`/`else` — a third network ID falls
through to the `else` and **silently serves the rural network list**. This
is the most dangerous of the two: it doesn't crash, it just returns wrong
data. Change it to an explicit per-network mapping, e.g. a
`Dict[NetworkID, List[int]]` lookup, mirroring how `DEFAULT_LV_NETWORKS` is
already structured.

**`vgi_api/vgi_api/validation/validators.py`, `validate_lv_list`** (~line
141):
```python
valid = False
if values["n_id"] == NetworkID.URBAN:
    ...
elif values["n_id"] == NetworkID.RURAL:
    ...
if not valid:
    raise ValueError(f"lv_list values: {list(difference)} are not network ids")
```
Here there genuinely is no third branch — for a new `n_id`, `valid` stays
`False` and `difference` is never assigned, so the `not valid` branch
raises `NameError: name 'difference' is not defined` instead of a clean
422 validation error. Add the new network's branch (or, better, refactor
this into a dict lookup keyed by `NetworkID`, same fix as above) before you
test anything else — this is the first place a manual `/simulate` call with
the new `n_id` will blow up.

Grep for other bare `if n_id == NetworkID.URBAN` / `RURAL` patterns before
you finish — these two are the ones found during this review, but
double-check nothing new has been added since.

### 3. Provide the network zip and register it

**File:** `vgi_api/vgi_api/data/opendssnetworks/` — add
`YOUR_NETWORK_full.zip` alongside the existing `HV_UG_full.zip` (9 MB) and
`HV_UG-OHa_full.zip` (21 MB).

**Required internal structure** (verified against the existing zips with
`unzip -l` and against `funcsTuring.modify_dss_files`, which is the code
that reads these files at request time):

```
<top level>
├── buscoords.csv
├── generators.dss
├── lines.dss
├── loads.dss
├── lds_edit.dss              # loads redirect, edited per-request by modify_network
├── master_mvlv.dss           # the master file OpenDSS compiles
├── redirect_lv_ntwx.dss      # LV-network redirect list, edited per-request
├── regcontrols.dss           # edited per-request (OLTC settings)
├── transformers.dss          # edited per-request (transformer scaling)
└── lvNetworks/
    └── network_<n>_<m>_<lv_id>/
        └── Feeder_<k>/
            ├── LinesUnq_pruned.txt
            ├── LinesUnq_pruned1_<lv_id>.txt
            ├── LoadsCopyUnq.txt
            ├── LoadsCopyUnq1_<lv_id>.txt
            ├── LineCode.txt
            ├── Transformers.txt
            └── XY_Position1_<lv_id>.csv
```

The five names in `fn_copy` inside `modify_dss_files`
(`vgi_api/vgi_api/funcsTuring.py` ~line 1945: `lds_edit`, `regcontrols`,
`transformers`, `master_mvlv`, `redirect_lv_ntwx`) must exist as top-level
`.dss` files with exactly those names — the code opens them by that literal
path. The `lvNetworks/` tree name is also literal (referenced directly in
`modify_dss_files` and shared read-only across requests via the extraction
cache in `unzip_networks`, ~line 2137).

Register the zip in `_cached_network_dir`
(`vgi_api/vgi_api/funcsTuring.py` ~line 2142):

```python
zip_names = {
    1060: DATA_FOLDER / "HV_UG_full.zip",
    1061: DATA_FOLDER / "HV_UG-OHa_full.zip",
    1062: DATA_FOLDER / "YOUR_NETWORK_full.zip",   # new
}
```

Note this dict is keyed by the **integer** id, matching `frId0` — not the
`NetworkID` enum directly (the enum's `.value` is a string; `main.py`
converts with `int(n_id.value)` before it reaches the engine — see
`main.py` ~line 436, `parameters["network_data"]["n_id"] = int(n_id.value)`).

### 4. Wire the frId/fdrsLoc mapping (research-code layer)

**File:** `vgi_api/vgi_api/slesNtwk_turing.py` — the `fdrs` dict (~line
153) and `fdrsLoc` dict (~line 240) both have `1060`/`1061` entries:

```python
fdrs = {
    ...
    1060: "HV_UG_full_turing",
    1061: "HV_UG-OHa_full_turing",
}
...
fdrsLoc = {
    ...
    1060: join("HV_UG_full", "master_mvlv"),
    1061: join("HV_UG-OHa_full", "master_mvlv"),
}
```

In practice **the API layer never uses these directly for 1060/1061** —
`azure_mockup.py` always calls `turingNet(frId=1000, frId0=<real n_id>,
...)`, and `frId=1000` resolves through `fdrsLoc[1000] = join("_network_mod",
"master_mvlv")`, which is the request-scoped directory `unzip_networks`
populates (see `_run_dss_simulation_inner` in `azure_mockup.py` ~line 178).
`frId0` is passed through separately and only consulted by the two
network-specific branches described in §6 below. **You do not strictly need
to add entries here for the API path to work** — but `slesNtwk_turing.py`
is marked "do not modify" / kept byte-identical to the original for a
reason (it's the numerically-validated reference implementation), so don't
touch it unless a specific new code path requires it. If you're unsure,
leave it alone and confirm nothing breaks; the existing tests will tell you
quickly if something does read it.

### 5. Reserved-network derivation — check it still makes sense

**File:** `vgi_api/vgi_api/validation/network_ids.py`

`RESERVED_LV_NETWORKS` is derived automatically from
`azureOptsXmpls.run_dict0["dmnd_gen_data"]["dgs"]["mv"]` and `["fcs"]["mv"]`
— currently `["1106", "1142"]` and `["1107", "1143"]`, shared by **both**
existing networks (both zips happen to contain LV networks with those exact
bus ids as lumped-MV-load hosts). This is the mechanism CHANGES.md §15/§16
introduced after a real crash: selecting one of these ids for detailed LV
modelling disables the lumped MV load that the demo's default solar/FCS
demand is attached to, and the demand-placement code
(`funcsTuring.turingNet.set_ldsi`, the `f_nms` helper) then fails to find
it.

**Two ways this can go for your new network:**
- If your new network's LV network ids **happen to include** `1106`,
  `1107`, `1142`, or `1143` as valid LV feeder ids, and `run_dict0`'s
  default scenario places lumped MV demand there too, you get the same
  protection for free — those ids are excluded from
  `VALID_LV_NETWORKS_<...>` for every network, not just urban/rural,
  because `RESERVED_LV_NETWORKS` is a flat set subtracted from every
  per-network list (see `_ALL_LV_NETWORKS_URBAN` /
  `_ALL_LV_NETWORKS_RURAL` and the equivalent you'll add for the new
  network in the next bullet).
- If your new network's lumped MV solar/FCS demand needs to sit on
  **different** bus ids than 1106/1107/1142/1143 (likely, since bus
  numbering is model-specific), `run_dict0` itself needs adapting — either
  make `dmnd_gen_data.dgs.mv` / `fcs.mv` a per-network mapping instead of a
  flat list (a real code change to `azureOptsXmpls.py` and
  `network_ids.py`'s `_lumped_mv_asset_hosts`, both currently assume one
  scenario shared by everything), or accept that the new network's
  equivalent hosts are not automatically protected and verify by hand that
  none of its default LV presets or the reserved mechanism conflict with it.
  Test this explicitly: try modelling every network from the new model's
  full list in detail (a scripted loop calling `/simulate` per id, similar
  to what CHANGES.md §16's verification did) and confirm none crash with
  `ValueError: list.index(x): x not in list`.

You'll also need to add `_ALL_LV_NETWORKS_<YOUR_NETWORK>` (the full list of
LV network ids that exist in the new zip — extract this from the zip's
`lvNetworks/` directory names or from the new network's
`redirect_lv_ntwx.dss`) and a `VALID_LV_NETWORKS_<YOUR_NETWORK>` filtered
list, following the existing `_ALL_LV_NETWORKS_URBAN` /
`VALID_LV_NETWORKS_URBAN` pattern.

### 6. The `set_powers` branch — primary-feeder MVA ratings

**File:** `vgi_api/vgi_api/funcsTuring.py`, `turingNet.set_powers` (~line
232):

```python
if self.frId0 == 1060:
    ckts2rr = {1: 6.82, 3: 6.82, 4: 8.86, 7: 8.86, 8: 8.86}
    ckts = [1, 1, 1, 3, 4, 4, 7, 8]
    rr = np.array([ckts2rr[i] for i in ckts])
elif self.frId0 == 1061:
    rr = np.ones(3) * 8.86
else:
    rr = np.nan * np.zeros(len(self.pmryLnsi))
```

This sets the thermal rating (MVA) used to compute primary-feeder loading
percentages — one of the four numeric datasets in the `/simulate` response
and one of the plotted figures. **Without a new branch here, your network
falls into the `else` and every primary-feeder loading comes back as
`NaN`** — the simulation will not crash, but that output dataset and its
plot will be meaningless for the new network. Add a third branch with the
real per-feeder MVA ratings for your network (get these from the network's
source documentation — the existing two cite "Table 4 with NPG Page 19,"
i.e. the UKGDS/Deakin documentation these networks came from — or from the
`.dss` transformer/line thermal ratings if documented there).

The same ratings, in the same feeder order, must also go into
`vgi_api/scripts/build_network_topology.py`'s `FEEDER_RATINGS_MVA` dict
(~line 65) — used to label the interactive network-map figures. Its own
comment already documents the fallback: "If a network's primary-line count
stops matching this table the ratings fall back to `None` (labels still
render) so a model change can't silently mislabel" — so this one fails
safe if you forget it, unlike `set_powers`, but you'll get unlabelled
feeder ratings on the map until you add it.

### 7. Cosmetic per-network dicts (fail safe, but worth doing properly)

**File:** `vgi_api/vgi_api/azure_mockup.py`, ~line 272:
```python
txtFss = {
    1060: "10",
    1061: "6",
}
...
"txtFs": txtFss.get(frid0, "8"),
```
Bus-label font size for the MV network-power plot, per network (bigger
networks need smaller labels to stay legible). Already uses `.get(...,
default)`, so a missing entry just uses the "8" default — safe to skip, but
add a tuned value once you've seen the new network's plot render.

### 8. Regenerate the topology JSON

**Files:** `vgi_api/scripts/build_network_topology.py`,
`vgi_api/vgi_api/data/network_topology_{1060,1061}.json` (committed),
`vgi_api/tests/test_topology_builder.py`.

The interactive network-explorer map is **not** generated live from
OpenDSS — it's pre-built offline into a committed JSON per network id and
served directly (`main.py`'s `/network-topology` endpoint just reads the
file). `build_network_topology.py`'s `ZIP_BY_ID` dict (~line 43) needs your
new network added:

```python
ZIP_BY_ID = {
    1060: DATA_DIR / "opendssnetworks" / "HV_UG_full.zip",
    1061: DATA_DIR / "opendssnetworks" / "HV_UG-OHa_full.zip",
    1062: DATA_DIR / "opendssnetworks" / "YOUR_NETWORK_full.zip",
}
```

Also check `MV_SUBSTATION_BUS = "1100"` (~line 45) — both existing networks
use bus `"1100"` as the primary substation's MV-side busbar; if your new
network uses a different substation bus id, this needs to become a
per-network mapping too (currently a single module-level constant assumed
shared by every network).

Then generate and commit the JSON:

```bash
cd vgi_api
python -m scripts.build_network_topology        # writes vgi_api/data/network_topology_<id>.json
python -m scripts.build_network_topology --check # verify it matches the zip (run this in CI too)
```

`tests/test_topology_builder.py` includes a **regeneration-guard test**
that fails if the committed JSON drifts from what the builder currently
produces from the zips — extend its fixtures
(`topo_1060` etc.) with an equivalent for the new network id, and add at
least one hand-counted sanity check (the existing
`test_network_1125_hand_counted_houses` pattern: pick one LV network from
the new model, count its houses/feeders by hand from the raw
`LoadsCopyUnq.txt` files, and assert the builder agrees).

### 9. Both front ends hardcode the network choice — update both

Neither `src/` nor `event-frontend-v2/` reads a dynamic list of available
networks from the API; the choice between urban/rural is hardcoded UI in
both.

**`src/views/SimulateNetworkAPI.vue`** (~line 28):
```html
<select v-model="network_options.n_id" class="form-control" @change="updateLVNetworksList()">
  <option value="1060">11kV urban network</option>
  <option value="1061">11kV urban - rural network</option>
</select>
```
Add a third `<option value="1062">...</option>`.

**`event-frontend-v2/src/views/SimulateNetworkAPI.vue`** (~lines 51-59): a
segmented-control pair, each option manually wired to a specific id via
`@click="setNetwork(1060)"` / `setNetwork(1061)`:
```html
<button :class="{ on: network_options.n_id === 1060 }" @click="setNetwork(1060)">...</button>
<button :class="{ on: network_options.n_id === 1061 }" @click="setNetwork(1061)">...</button>
```
Add a third button following the same pattern. Also check line ~494, which
branches UI copy/labels on `network_options.n_id === 1060` — the "urban"
vs "rural" descriptive text is hand-written per network id there too, not
derived from anything.

Everything else in both front ends (the LV-network picker, the network
map, the results parsing) is already driven by the `/lv-network`,
`/lv-network-defaults`, and `/network-topology` API responses — once the
backend serves your new `n_id` correctly, only the top-level network
*selector* needs manual UI additions, per CHANGES.md §16's note that "no
front-end change required" applied specifically to the reserved-network
filtering, not to adding a wholly new network choice.

### 10. Extend the test suite

**File:** `vgi_api/tests/test_api_validation.py`. The existing tests are
already parametrized over `NetworkID.URBAN` / `NetworkID.RURAL` in exactly
the pattern you need to extend — `test_lv_network`, `test_lv_network_defaults`,
`test_reserved_networks_excluded_from_selectable`,
`test_reserved_network_rejected_by_validation` all use
`@pytest.mark.parametrize("n_id", [NetworkID.RURAL, NetworkID.URBAN])` or
similar. Add your new `NetworkID` member to each of these parametrize lists
— that alone will immediately surface the `NameError` described in §2 if
you haven't fixed `validate_lv_list` yet, and will confirm `/lv-network`
returns the right list once you have.

Also add at least one full end-to-end `/simulate` test for the new network
(mirroring whichever full-request test exists for 1060/1061 today), and —
per CHANGES.md §16's own verification approach — a targeted check that MV
solar **and** FCS profiles both run cleanly against the new network with
zero DG/FCS skip-warnings in the logs, confirming §5's reserved-network
handling actually protects the new network's lumped loads.

### 11. Run the acceptance gate

```bash
cd vgi_api
.venv/bin/pytest tests            # all 133+ tests, including your additions
```

If you have (or can construct) a reference simulation output for the new
network from another source, add a scenario for it to
`regression_harness/` (see `regression_harness/README.md`) — this is the
strongest correctness signal in the project for the *existing* two
networks, and the same numeric-comparison approach is the right way to
validate a new one before trusting its results.

## Summary table — every file touched

| File | Change |
|---|---|
| `vgi_api/vgi_api/validation/types.py` | New `NetworkID` member; new `DEFAULT_LV_NETWORKS` entry |
| `vgi_api/vgi_api/main.py` | Fix the URBAN/else branch in `/lv-network` |
| `vgi_api/vgi_api/validation/validators.py` | Fix the URBAN/RURAL-only `if/elif` in `validate_lv_list` |
| `vgi_api/vgi_api/data/opendssnetworks/` | New zip, correct internal structure |
| `vgi_api/vgi_api/funcsTuring.py` | New `zip_names` entry; new `set_powers` branch (ratings) |
| `vgi_api/vgi_api/validation/network_ids.py` | New `_ALL_LV_NETWORKS_<...>` / `VALID_LV_NETWORKS_<...>`; verify `RESERVED_LV_NETWORKS` still applies correctly |
| `vgi_api/vgi_api/azureOptsXmpls.py` | Possibly: make `dmnd_gen_data.dgs/fcs.mv` per-network if bus ids differ |
| `vgi_api/vgi_api/azure_mockup.py` | Optional: `txtFss` font-size tuning |
| `vgi_api/scripts/build_network_topology.py` | New `ZIP_BY_ID` entry; new `FEEDER_RATINGS_MVA` entry; check `MV_SUBSTATION_BUS` |
| `vgi_api/vgi_api/data/network_topology_<id>.json` | Generated, then committed |
| `vgi_api/tests/test_topology_builder.py` | New fixture + hand-counted sanity test |
| `vgi_api/tests/test_api_validation.py` | Extend existing parametrized tests with the new `NetworkID` |
| `src/views/SimulateNetworkAPI.vue` | New `<option>` in the network `<select>` |
| `event-frontend-v2/src/views/SimulateNetworkAPI.vue` | New segmented-control button; check the hardcoded urban/rural label branch |
| `vgi_api/vgi_api/slesNtwk_turing.py` | Leave alone unless a specific failure points here (see §4) |

Use the 1061 (rural) entries as your template at every one of these touch
points — it's the more recently added and more clearly written of the two
existing networks.
