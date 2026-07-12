"""Tests for the network-topology builder (Phase B).

Covers three things:
  1. The parser produces correct, self-consistent topology from the real zips
     (network/feeder/house counts, connectivity, sane distances).
  2. The committed JSON matches what the builder produces now (regeneration
     guard — fails if the zips and the committed JSON drift apart).
  3. The graph-traversal distances agree with the OpenDSS engine's own
     AllBusDistances (the slow, engine-backed cross-check).
"""

import json
import os
import tempfile
import zipfile
from pathlib import Path

import pytest

import scripts.build_network_topology as B
from vgi_api.validation import VALID_LV_NETWORKS_RURAL, VALID_LV_NETWORKS_URBAN


@pytest.fixture(scope="module")
def topo_1060():
    return B.build_topology(1060)


# ---------------------------------------------------------------------------
# 1. Parser correctness
# ---------------------------------------------------------------------------


def test_urban_has_expected_network_count(topo_1060):
    assert len(topo_1060["lv_networks"]) == 75


def test_network_1125_hand_counted_houses(topo_1060):
    """Network 1125: 4 feeders with 55 + 31 + 39 + 75 = 200 houses (counted by
    hand from the LoadsCopyUnq files)."""
    net = topo_1060["lv_networks"]["1125"]
    assert net["n_feeders"] == 4
    assert net["n_houses"] == 200
    per_feeder = {f["name"]: f["n_houses"] for f in net["feeders"]}
    assert per_feeder == {
        "Feeder_1": 55,
        "Feeder_2": 31,
        "Feeder_3": 39,
        "Feeder_4": 75,
    }
    assert net["xfmr_kva"] == 500.0
    assert net["mv_bus"] == "1125"


def test_every_house_is_reachable(topo_1060):
    """Every load bus must be connected to its transformer (no orphan houses),
    otherwise the distance metrics silently drop customers."""
    for nid, net in topo_1060["lv_networks"].items():
        for f in net["feeders"]:
            assert f["n_houses_unreachable"] == 0, (
                f"network {nid} {f['name']} has "
                f"{f['n_houses_unreachable']} unreachable houses"
            )


def test_distances_are_physically_sane(topo_1060):
    for nid, net in topo_1060["lv_networks"].items():
        assert net["elec_dist_ohm"] is not None and net["elec_dist_ohm"] > 0
        assert net["n_sections_from_sub"] is not None
        for f in net["feeders"]:
            if f["n_houses"]:
                assert 0 < f["max_house_dist_m"] < 2000, (nid, f)
                assert 0 < f["mean_house_dist_m"] <= f["max_house_dist_m"]


def test_mv_topology_shape(topo_1060):
    mv = topo_1060["mv"]
    assert mv["substation"] == B.MV_SUBSTATION_BUS
    assert len(mv["lines"]) > 0
    # The substation bus must appear as a real coordinate.
    ids = {b["id"] for b in mv["buses"]}
    assert B.MV_SUBSTATION_BUS in ids


@pytest.mark.parametrize(
    "n_id,valid",
    [(1060, VALID_LV_NETWORKS_URBAN), (1061, VALID_LV_NETWORKS_RURAL)],
)
def test_all_valid_networks_have_topology(n_id, valid):
    topo = B.build_topology(n_id)
    keys = {int(k) for k in topo["lv_networks"]}
    missing = set(valid) - keys
    assert not missing, f"valid networks with no topology: {sorted(missing)}"


# ---------------------------------------------------------------------------
# 2. Regeneration guard
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("n_id", [1060, 1061])
def test_committed_json_matches_builder(n_id):
    """The committed JSON must equal a fresh build. If this fails, run
    `python -m scripts.build_network_topology` to regenerate it."""
    committed = json.loads(B.output_path(n_id).read_text())
    fresh = B.build_topology(n_id)
    assert json.dumps(fresh, sort_keys=True) == json.dumps(
        committed, sort_keys=True
    ), f"network_topology_{n_id}.json is stale — re-run the builder"


# ---------------------------------------------------------------------------
# 3. Engine-backed cross-check (slow)
# ---------------------------------------------------------------------------


def _extract_network(zip_path: Path, net_dir: str, dest: Path) -> Path:
    """Extract one LV network subtree from the zip and return its master file."""
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            if name.replace("\\", "/").startswith(net_dir + "/"):
                zf.extract(name, dest)
    masters = list((dest / net_dir).glob("master_network_*.dss"))
    return masters[0]


@pytest.mark.slow
def test_distances_agree_with_opendss():
    """Compare our graph traversal against OpenDSS AllBusDistances for network
    1125. OpenDSS reports bus distance in km; we report metres. They must agree
    to within a couple of metres (the residual is service-cable / rounding)."""
    dss = pytest.importorskip("dss")

    zf = B._Zip(B.ZIP_BY_ID[1060])
    net_dir = "lvNetworks/network_1_1_1125"

    # Our per-load distances, rebuilt from the graph.
    our_dist = _our_load_distances(zf, net_dir)

    # OpenDSS `compile` chdir's into the .dss file's directory; that directory
    # is a TemporaryDirectory removed on exit, so restore the cwd afterwards or
    # every later test that touches the filesystem breaks with FileNotFoundError.
    cwd = os.getcwd()
    try:
        with tempfile.TemporaryDirectory() as tmp:
            master = _extract_network(B.ZIP_BY_ID[1060], net_dir, Path(tmp))
            d = dss.DSS
            d.Text.Command = "clear"
            d.Text.Command = f'compile "{master}"'
            eng = dict(
                zip(
                    [b.lower() for b in d.ActiveCircuit.AllBusNames],
                    d.ActiveCircuit.AllBusDistances,  # km
                )
            )
    finally:
        os.chdir(cwd)

    compared = 0
    max_diff = 0.0
    for bus, our_m in our_dist.items():
        if bus in eng:
            max_diff = max(max_diff, abs(our_m - eng[bus] * 1000.0))
            compared += 1
    assert compared > 100, f"too few buses compared ({compared})"
    assert max_diff < 2.0, f"max distance disagreement {max_diff:.2f} m"


def _our_load_distances(zf, net_dir):
    """Recompute the raw load-bus -> metres map the builder uses internally."""
    import re

    slave = zf.read_text(
        net_dir
        + "/"
        + net_dir.split("/")[-1].replace("network", "slave_network")
        + ".dss"
    )
    line_files, load_files, xfmr_files, switch = [], [], [], []
    for raw in slave.splitlines():
        s = raw.strip()
        low = s.lower()
        if low.startswith("redirect"):
            tgt = re.search(r"redirect\s+(\S+)", s, re.I).group(1)
            base = tgt.split("/")[-1].lower()
            if "transformer" in base:
                xfmr_files.append(B._resolve(net_dir, tgt))
            elif "line" in base and "linecode" not in base:
                line_files.append(B._resolve(net_dir, tgt))
            elif "load" in base:
                load_files.append(B._resolve(net_dir, tgt))
        elif low.startswith("new line"):
            kv = B._kv_pairs(s)
            switch.append((B._strip_phase(kv["bus1"]), B._strip_phase(kv["bus2"])))
    hv, lv, _ = B._parse_transformer(zf, xfmr_files)
    adj = {}

    def add(a, b, w):
        adj.setdefault(a, []).append((b, w))
        adj.setdefault(b, []).append((a, w))

    for a, b in switch:
        add(a, b, 0.0)
    add(hv, lv, 0.0)
    for lf in line_files:
        for a, b, w in B._parse_lines(zf, lf):
            add(a, b, w)
    dist = B._dijkstra(adj, lv)
    loads = []
    for lf in load_files:
        loads += B._parse_load_buses(zf, lf)
    return {b: dist[b] for b in loads if b in dist}


# ---------------------------------------------------------------------------
# 4. API endpoint
# ---------------------------------------------------------------------------


def test_endpoint_returns_topology():
    from fastapi.testclient import TestClient

    from vgi_api import app

    client = TestClient(app)
    resp = client.get("/network-topology", params={"n_id": "1060"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["n_id"] == 1060
    assert "1125" in body["lv_networks"]
    assert body["lv_networks"]["1125"]["n_houses"] == 200
    assert body["mv"]["substation"] == "1100"


def test_endpoint_rejects_bad_network():
    from fastapi.testclient import TestClient

    from vgi_api import app

    client = TestClient(app)
    resp = client.get("/network-topology", params={"n_id": "9999"})
    assert resp.status_code == 422
