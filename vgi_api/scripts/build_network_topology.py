"""Offline builder for the network-topology JSON consumed by the frontend.

The MV-LV network models are static (they only change if the .zip archives in
``vgi_api/data/opendssnetworks`` change), so their topology is extracted ONCE,
here, into a small JSON per network id and committed alongside the zips. The
API then serves that JSON directly (see ``/network-topology`` in main.py) with
no OpenDSS involvement.

What the JSON captures, per MV network (1060 urban, 1061 urban-rural):

- ``mv``: the medium-voltage single-line diagram — bus coordinates (schematic,
  not geographic), line connections, and the primary substation bus. MV line
  lengths are NOT modelled (the .dss files give impedances only), so
  MV distance is expressed as electrical distance |Z1| in ohms and as a hop
  count, never in metres.
- ``lv_networks``: for each LV network modelled in detail, the connecting MV
  bus, transformer rating, number of feeders, and per feeder the number of
  houses and the house-to-LV-substation distances in METRES (LV line lengths
  ARE modelled, ``Length=… Units=m``), computed by shortest-path traversal of
  the LV line graph rooted at the transformer's LV terminal.

Run it after changing the network zips::

    python -m scripts.build_network_topology        # writes both JSONs
    python -m scripts.build_network_topology --check # verify committed JSON
                                                     # matches the zips (CI)

The builder is dependency-light on purpose (stdlib + numpy) so it can run in CI
without the OpenDSS engine. ``tests/test_topology_builder.py`` cross-checks a
sample of its distances against the OpenDSS engine itself.
"""

from __future__ import annotations

import argparse
import heapq
import io
import json
import math
import re
import sys
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

DATA_DIR = Path(__file__).resolve().parent.parent / "vgi_api" / "data"
ZIP_BY_ID = {
    1060: DATA_DIR / "opendssnetworks" / "HV_UG_full.zip",
    1061: DATA_DIR / "opendssnetworks" / "HV_UG-OHa_full.zip",
}

# Primary substation MV busbar (LV side of the 33/11 kV transformer). Both
# shipped networks use this bus id; asserted in the tests.
MV_SUBSTATION_BUS = "1100"

# Primary-feeder thermal ratings (MVA), per MV feeder, in the SAME order the
# engine numbers them (F1, F2, …). Mirrors funcsTuring.turingNet.set_powers,
# which is the single source of truth for the results plots' legend
# ("F1 (to 1101), 6.82 MVA"). The order matches the primary lines as they
# appear in lines.dss (bus1 == MV_SUBSTATION_BUS), which is also OpenDSS's line
# order — verified against the engine legend for both shipped networks. If a
# network's primary-line count stops matching this table the ratings fall back
# to None (labels still render) so a model change can't silently mislabel.
FEEDER_RATINGS_MVA: Dict[int, List[float]] = {
    1060: [6.82, 6.82, 6.82, 6.82, 8.86, 8.86, 8.86, 8.86],
    1061: [8.86, 8.86, 8.86],
}

# ---------------------------------------------------------------------------
# Small parsing helpers
# ---------------------------------------------------------------------------


def _strip_phase(bus: str) -> str:
    """'1_1125_12_115.1.2' -> '1_1125_12_115' (drop OpenDSS phase suffixes)."""
    return bus.split(".")[0].strip().lower()


def _kv_pairs(line: str) -> Dict[str, str]:
    """Parse OpenDSS 'key=value' tokens (case-insensitive keys).

    Handles bracketed lists like ``Buses=[1125 1_1125_1]`` by returning the raw
    inside-bracket text for that key.
    """
    out: Dict[str, str] = {}

    # Normalise bracket lists so they contain no spaces that would split tokens,
    # and drop the surrounding brackets so values are clean.
    # e.g. "Buses=[1125 1_1125_1]" -> "Buses=1125|1_1125_1"
    def _join_brackets(m: re.Match) -> str:
        inner = m.group(1).replace(",", " ").split()
        return "=" + "|".join(inner)

    line = re.sub(r"=\[([^\]]*)\]", _join_brackets, line)
    line = re.sub(r'="([^"]*)"', lambda m: "=" + m.group(1).replace(" ", "|"), line)
    for tok in line.split():
        if "=" in tok:
            k, _, v = tok.partition("=")
            out[k.strip().lower()] = v.strip()
    return out


class _Zip:
    """Reads text members of a network zip on demand, path-normalised."""

    def __init__(self, path: Path):
        self._zf = zipfile.ZipFile(path)
        # Map lower-cased normalised member path -> real name for lookup.
        self._names = {n.replace("\\", "/").lower(): n for n in self._zf.namelist()}

    def read_text(self, member: str) -> str:
        key = member.replace("\\", "/").lower().lstrip("./")
        real = self._names.get(key)
        if real is None:
            raise KeyError(member)
        return self._zf.read(real).decode("utf-8", errors="replace")

    def exists(self, member: str) -> bool:
        return member.replace("\\", "/").lower().lstrip("./") in self._names


# ---------------------------------------------------------------------------
# MV topology
# ---------------------------------------------------------------------------


def _parse_buscoords(text: str) -> Dict[str, Tuple[float, float]]:
    coords: Dict[str, Tuple[float, float]] = {}
    for row in text.splitlines():
        row = row.strip()
        if not row:
            continue
        parts = [p for p in re.split(r"[,\s]+", row) if p != ""]
        if len(parts) < 3:
            continue
        bus, x, y = parts[0], parts[1], parts[2]
        try:
            coords[_strip_phase(bus)] = (float(x), float(y))
        except ValueError:
            continue
    return coords


def _build_mv(zf: _Zip, n_id: int) -> dict:
    coords = _parse_buscoords(zf.read_text("buscoords.csv"))

    edges: List[Tuple[str, str, float]] = []  # (bus1, bus2, |Z1| ohm)
    adj_w: Dict[str, List[Tuple[str, float]]] = {}
    adj_u: Dict[str, List[str]] = {}
    lines_out = []
    primary_bus2: List[str] = []  # bus2 of each primary feeder, in file order
    for raw in zf.read_text("lines.dss").splitlines():
        low = raw.strip().lower()
        if not low.startswith("new line"):
            continue
        kv = _kv_pairs(raw)
        b1, b2 = _strip_phase(kv.get("bus1", "")), _strip_phase(kv.get("bus2", ""))
        if not b1 or not b2:
            continue
        r1 = float(kv.get("r1", 0.0))
        x1 = float(kv.get("x1", 0.0))
        z = math.hypot(r1, x1)
        edges.append((b1, b2, z))
        lines_out.append({"from": b1, "to": b2})
        adj_w.setdefault(b1, []).append((b2, z))
        adj_w.setdefault(b2, []).append((b1, z))
        adj_u.setdefault(b1, []).append(b2)
        adj_u.setdefault(b2, []).append(b1)
        if b1 == MV_SUBSTATION_BUS.lower():
            primary_bus2.append(b2)

    elec_dist = _dijkstra(adj_w, MV_SUBSTATION_BUS)
    hop_dist = _bfs_hops(adj_u, MV_SUBSTATION_BUS)

    # Primary feeders: F1, F2, … in the engine's order (see FEEDER_RATINGS_MVA).
    ratings = FEEDER_RATINGS_MVA.get(n_id, [])
    feeders_out = [
        {
            "name": f"F{i + 1}",
            "to": bus2,
            "rating_mva": ratings[i] if i < len(ratings) else None,
        }
        for i, bus2 in enumerate(primary_bus2)
    ]

    buses_out = [
        {
            "id": b,
            "x": coords.get(b, (None, None))[0],
            "y": coords.get(b, (None, None))[1],
        }
        for b in sorted(set(list(coords) + [e for ed in edges for e in ed[:2]]))
    ]
    return {
        "substation": MV_SUBSTATION_BUS,
        "buses": buses_out,
        "lines": lines_out,
        "feeders": feeders_out,
        "_elec_dist": elec_dist,
        "_hop_dist": hop_dist,
    }


# ---------------------------------------------------------------------------
# LV topology
# ---------------------------------------------------------------------------


def _list_lv_networks(zf: _Zip) -> List[Tuple[str, str, str]]:
    """Return (mv_bus, network_dir, slave_dss_member) for every LV network."""
    out = []
    for raw in zf.read_text("redirect_lv_ntwx.dss").splitlines():
        low = raw.strip().lower()
        if "redirect" not in low:
            continue
        m = re.search(r"redirect\s+(\S+)", raw.strip(), re.IGNORECASE)
        if not m:
            continue
        member = m.group(1)  # lvNetworks/network_23_1_1101/slave_network_23_1_1101.dss
        parts = member.split("/")
        net_dir = "/".join(parts[:-1])
        mv_bus = net_dir.split("_")[-1]  # trailing 4-digit id == MV bus
        out.append((mv_bus, net_dir, member))
    return out


def _resolve(net_dir: str, redirect_target: str) -> str:
    return net_dir + "/" + redirect_target.replace("\\", "/")


def _build_lv_network(zf: _Zip, net_dir: str, slave_member: str) -> dict:
    slave = zf.read_text(slave_member)

    line_files: List[str] = []
    load_files: List[str] = []
    xfmr_files: List[str] = []
    switch_edges: List[Tuple[str, str]] = []

    for raw in slave.splitlines():
        s = raw.strip()
        low = s.lower()
        if low.startswith("redirect"):
            m = re.search(r"redirect\s+(\S+)", s, re.IGNORECASE)
            if not m:
                continue
            tgt = m.group(1)
            base = tgt.split("/")[-1].lower()
            if "transformer" in base:
                xfmr_files.append(_resolve(net_dir, tgt))
            elif "line" in base and "linecode" not in base:
                line_files.append(_resolve(net_dir, tgt))
            elif "load" in base:
                load_files.append(_resolve(net_dir, tgt))
        elif low.startswith("new line"):
            # Feeder-head switch lines (bus1=<lv root> bus2=<feeder head>).
            kv = _kv_pairs(s)
            b1, b2 = _strip_phase(kv.get("bus1", "")), _strip_phase(kv.get("bus2", ""))
            if b1 and b2:
                switch_edges.append((b1, b2))

    # Transformer: HV (MV) bus, LV root bus, kVA.
    xfmr_hv, xfmr_lv, xfmr_kva = _parse_transformer(zf, xfmr_files)

    # Build the LV line graph (metres) plus zero-length switch/transformer edges.
    adj: Dict[str, List[Tuple[str, float]]] = {}

    def _add(a: str, b: str, w: float) -> None:
        adj.setdefault(a, []).append((b, w))
        adj.setdefault(b, []).append((a, w))

    for a, b in switch_edges:
        _add(a, b, 0.0)
    if xfmr_hv and xfmr_lv:
        _add(xfmr_hv, xfmr_lv, 0.0)

    # Per-feeder line + load parsing, grouped by feeder directory.
    feeder_lines: Dict[str, List[Tuple[str, str, float]]] = {}
    for lf in line_files:
        feeder = lf.split("/")[-2]
        for a, b, w in _parse_lines(zf, lf):
            _add(a, b, w)
            feeder_lines.setdefault(feeder, []).append((a, b, w))

    feeder_loads: Dict[str, List[str]] = {}
    for lf in load_files:
        feeder = lf.split("/")[-2]
        feeder_loads.setdefault(feeder, []).extend(_parse_load_buses(zf, lf))

    root = xfmr_lv or (switch_edges[0][0] if switch_edges else None)
    dist = _dijkstra(adj, root) if root else {}

    feeders_out = []
    total_houses = 0
    for feeder in sorted(set(list(feeder_lines) + list(feeder_loads))):
        houses = feeder_loads.get(feeder, [])
        total_houses += len(houses)
        d = [dist[_strip_phase(h)] for h in houses if _strip_phase(h) in dist]
        total_len = sum(w for (_, _, w) in feeder_lines.get(feeder, []))
        feeders_out.append(
            {
                "name": feeder,
                "n_houses": len(houses),
                "n_houses_unreachable": len(houses) - len(d),
                "total_line_m": round(total_len, 1),
                "max_house_dist_m": round(max(d), 1) if d else None,
                "mean_house_dist_m": round(sum(d) / len(d), 1) if d else None,
            }
        )

    return {
        "mv_bus": xfmr_hv,
        "xfmr_kva": xfmr_kva,
        "xfmr_lv_bus": xfmr_lv,
        "n_feeders": len(feeders_out),
        "n_houses": total_houses,
        "feeders": feeders_out,
    }


def _parse_transformer(
    zf: _Zip, xfmr_files: List[str]
) -> Tuple[Optional[str], Optional[str], Optional[float]]:
    for xf in xfmr_files:
        if not zf.exists(xf):
            continue
        for raw in zf.read_text(xf).splitlines():
            if not raw.strip().lower().startswith("new transformer"):
                continue
            kv = _kv_pairs(raw)
            buses = kv.get("buses", "").split("|")
            hv = _strip_phase(buses[0]) if len(buses) >= 1 else None
            lv = _strip_phase(buses[1]) if len(buses) >= 2 else None
            kvas = kv.get("kvas", "").split("|")
            kva = None
            for v in kvas:
                try:
                    kva = float(v)
                    break
                except ValueError:
                    continue
            return hv, lv, kva
    return None, None, None


def _parse_lines(zf: _Zip, member: str) -> List[Tuple[str, str, float]]:
    if not zf.exists(member):
        return []
    out = []
    for raw in zf.read_text(member).splitlines():
        if not raw.strip().lower().startswith("new line"):
            continue
        kv = _kv_pairs(raw)
        b1, b2 = _strip_phase(kv.get("bus1", "")), _strip_phase(kv.get("bus2", ""))
        if not b1 or not b2:
            continue
        length = float(kv.get("length", 0.0))
        units = kv.get("units", "m").lower()
        out.append((b1, b2, _to_metres(length, units)))
    return out


def _parse_load_buses(zf: _Zip, member: str) -> List[str]:
    if not zf.exists(member):
        return []
    out = []
    for raw in zf.read_text(member).splitlines():
        if not raw.strip().lower().startswith("new load"):
            continue
        kv = _kv_pairs(raw)
        b1 = kv.get("bus1", "")
        if b1:
            out.append(_strip_phase(b1))
    return out


def _to_metres(length: float, units: str) -> float:
    return {
        "m": 1.0,
        "km": 1000.0,
        "ft": 0.3048,
        "kft": 304.8,
        "mi": 1609.344,
    }.get(units, 1.0) * length


# ---------------------------------------------------------------------------
# Graph algorithms
# ---------------------------------------------------------------------------


def _dijkstra(adj: Dict[str, List[Tuple[str, float]]], root: str) -> Dict[str, float]:
    dist = {root: 0.0}
    pq = [(0.0, root)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist.get(u, math.inf):
            continue
        for v, w in adj.get(u, ()):
            nd = d + w
            if nd < dist.get(v, math.inf):
                dist[v] = nd
                heapq.heappush(pq, (nd, v))
    return dist


def _bfs_hops(adj: Dict[str, List[str]], root: str) -> Dict[str, int]:
    from collections import deque

    dist = {root: 0}
    q = deque([root])
    while q:
        u = q.popleft()
        for v in adj.get(u, ()):
            if v not in dist:
                dist[v] = dist[u] + 1
                q.append(v)
    return dist


# ---------------------------------------------------------------------------
# Top-level assembly
# ---------------------------------------------------------------------------


def build_topology(n_id: int) -> dict:
    zf = _Zip(ZIP_BY_ID[n_id])
    mv = _build_mv(zf, n_id)
    elec = mv.pop("_elec_dist")
    hops = mv.pop("_hop_dist")

    lv_networks = {}
    for mv_bus, net_dir, slave_member in _list_lv_networks(zf):
        net = _build_lv_network(zf, net_dir, slave_member)
        conn_bus = net.get("mv_bus") or mv_bus
        net["elec_dist_ohm"] = round(elec[conn_bus], 4) if conn_bus in elec else None
        net["n_sections_from_sub"] = hops.get(conn_bus)
        lv_networks[mv_bus] = net

    return {
        "n_id": n_id,
        "mv": {k: v for k, v in mv.items()},
        "lv_networks": lv_networks,
    }


def output_path(n_id: int) -> Path:
    return DATA_DIR / f"network_topology_{n_id}.json"


def write_all() -> None:
    for n_id in ZIP_BY_ID:
        topo = build_topology(n_id)
        output_path(n_id).write_text(json.dumps(topo, indent=1, sort_keys=True))
        print(f"wrote {output_path(n_id).name}: {len(topo['lv_networks'])} LV networks")


def check_all() -> int:
    rc = 0
    for n_id in ZIP_BY_ID:
        current = build_topology(n_id)
        committed_path = output_path(n_id)
        if not committed_path.exists():
            print(f"MISSING: {committed_path.name}")
            rc = 1
            continue
        committed = json.loads(committed_path.read_text())
        if json.dumps(current, sort_keys=True) != json.dumps(committed, sort_keys=True):
            print(f"STALE: {committed_path.name} differs from the zip — re-run builder")
            rc = 1
        else:
            print(f"OK: {committed_path.name}")
    return rc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--check",
        action="store_true",
        help="verify committed JSON matches the zips (exit 1 if stale)",
    )
    args = ap.parse_args()
    if args.check:
        return check_all()
    write_all()
    return 0


if __name__ == "__main__":
    sys.exit(main())
