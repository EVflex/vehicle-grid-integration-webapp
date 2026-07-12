#!/usr/bin/env python3
"""vgi_regression.py — numeric regression harness for the VGI API.

Compares two versions of the vehicle-grid-integration simulation code by
exercising their HTTP APIs with an identical, deterministic scenario matrix
and comparing the numeric simulation outputs.

Why HTTP (black box)?  The reference code (v0) and any newer code can never
share one Python environment (different pydantic/fastapi/dss-python pins),
so the only comparison surface that works for *any* future version is the
API contract itself.  The four numeric datasets in the /simulate response
(primary feeder loadings, MV bus voltages, transformer powers, LV voltage
comparison) are the ground truth of the power-flow physics; the PNG plots
are rendered from those same numbers and legitimately differ across
matplotlib versions, so they are checked for presence only.

Determinism: the simulation seeds its random generator with rand_seed=0
(azureOptsXmpls.run_dict0), so identical inputs must give identical numbers
on identical code.  Solver-stack upgrades (dss-python / numpy) introduce
differences around 1e-10 relative; genuine model bugs are orders of
magnitude larger.  The default tolerance (rtol 1e-6) sits between the two,
well below OpenDSS's own 1e-4 solution tolerance.

Usage (no third-party dependencies; any Python >= 3.8):

  # 1. capture a baseline from the reference server
  python3 vgi_regression.py capture --url http://127.0.0.1:8000 --out baselines/v0

  # 2. capture from the code under test
  python3 vgi_regression.py capture --url http://127.0.0.1:8001 --out /tmp/candidate

  # 3. compare
  python3 vgi_regression.py compare baselines/v0 /tmp/candidate --report report.md

  python3 vgi_regression.py scenarios          # list the scenario matrix

Exit codes: 0 = all comparisons pass, 1 = differences found, 2 = harness error.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import math
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

HARNESS_VERSION = "1.0"

# The response keys that contain numeric CSV datasets (the comparison ground
# truth), mapped to the file names they are stored under in a capture.
NUMERIC_DATASETS = {
    "primary_loadings_data": "primary_loadings.csv",
    "mv_voltages_data": "mv_voltages.csv",
    "trn_powers_data": "trn_powers.csv",
    "lv_comparison_data": "lv_comparison.csv",
}

# Response keys that contain base64 PNG plots (presence checked, pixels not).
PLOT_KEYS = [
    "mv_highlevel",
    "mv_highlevel_clean",
    "lv_voltages",
    "lv_comparison",
    "mv_voltages",
    "mv_powers",
    "trn_powers",
    "profile_options",
    "profile_options_dgs",
    "profile_options_fcs",
    "pmry_loadings",
    "pmry_powers",
]

# ---------------------------------------------------------------------------
# Scenario matrix
# ---------------------------------------------------------------------------


def _upload_profile_csv(n_profiles: int = 2, scale: float = 1.0) -> str:
    """A deterministic 48 x n half-hourly profile accepted by every version
    of the CSV validator (48 data rows, HH:MM:SS times, 30-minute steps)."""
    rows = ["time," + ",".join(f"profile{i + 1}" for i in range(n_profiles))]
    for step in range(48):
        hh, mm = divmod(step * 30, 60)
        vals = []
        for p in range(n_profiles):
            # Smooth, strictly positive, deterministic shape.
            v = scale * (0.5 + 0.45 * math.sin(2 * math.pi * (step + 8 * p) / 48.0))
            vals.append(f"{v:.6f}")
        rows.append(f"{hh:02d}:{mm:02d}:00," + ",".join(vals))
    return "\n".join(rows) + "\n"


# Each scenario: id, description, query params, optional file uploads.
# All scenarios are valid requests for BOTH v0 and newer code (combinations
# that crash v0 with an HTTP 500 — e.g. lv_plot_list with lv_default, or a
# single-network lv_list — are deliberately excluded from the default
# matrix; behaviour changes there are documented fixes, not regressions).
DEFAULT_SCENARIOS = [
    {
        "id": "urban_nearsub_baseload",
        "description": "Urban network, near-substation LV set, base load only",
        "params": {"n_id": "1060", "lv_default": "near-sub"},
    },
    {
        "id": "urban_nearedge_ev",
        "description": "Urban, near-edge LV set, 50% EVs (3.6 kW), Crest smart meters",
        "params": {
            "n_id": "1060",
            "lv_default": "near-edge",
            "lv_smart_meter_profile": "Crest",
            "lv_ev_profile": "Crowdcharge—3.6kW",
            "lv_ev_pen": "0.5",
        },
    },
    {
        "id": "urban_mixed_pv_hp",
        "description": "Urban, mixed LV set, 60% summer PV + 40% cold-weekday heat pumps",
        "params": {
            "n_id": "1060",
            "lv_default": "mixed",
            "lv_pv_profile": "Summer",
            "lv_pv_pen": "0.6",
            "lv_hp_profile": "Cold weekday",
            "lv_hp_pen": "0.4",
        },
    },
    {
        "id": "urban_lvlist_all_lcts_xfmr_oltc",
        "description": (
            "Urban, explicit LV list + plot list, EV+PV+HP together, "
            "non-default transformer scale, OLTC setpoint and bandwidth"
        ),
        "params": {
            "n_id": "1060",
            "lv_list": "1101,1105,1103",
            "lv_plot_list": "1101,1103",
            "xfmr_scale": "1.5",
            "oltc_setpoint": "1.06",
            "oltc_bandwidth": "0.02",
            "rs_pen": "0.9",
            "lv_ev_profile": "Crowdcharge—7kW",
            "lv_ev_pen": "0.8",
            "lv_pv_profile": "Winter",
            "lv_pv_pen": "0.3",
            "lv_hp_profile": "Mild weekend",
            "lv_hp_pen": "0.6",
        },
    },
    {
        "id": "urban_mv_solar_fcs",
        "description": "Urban, near-sub, MV solar plant (summer) + MV fast-charging stations",
        "params": {
            "n_id": "1060",
            "lv_default": "near-sub",
            "mv_solar_pv_profile": "Solar Plant Summer",
            "mv_fcs_profile": "FC Stations",
        },
    },
    {
        "id": "rural_nearsub_baseload",
        "description": "Rural network, near-substation LV set, base load only",
        "params": {"n_id": "1061", "lv_default": "near-sub"},
    },
    {
        "id": "rural_mixed_ev_hp",
        "description": "Rural, mixed LV set, 80% EVs (7 kW) + 50% mild-weekend heat pumps",
        "params": {
            "n_id": "1061",
            "lv_default": "mixed",
            "lv_ev_profile": "Crowdcharge—7kW",
            "lv_ev_pen": "0.8",
            "lv_hp_profile": "Mild weekend",
            "lv_hp_pen": "0.5",
        },
    },
    {
        "id": "urban_csv_uploads",
        "description": "Urban, near-sub, user-uploaded smart-meter and MV-solar CSV profiles",
        "params": {
            "n_id": "1060",
            "lv_default": "near-sub",
            "lv_smart_meter_profile": "csv",
            "lv_smart_meter_profile_units": "kW",
            "mv_solar_pv_profile": "csv",
            "mv_solar_pv_profile_units": "kW",
        },
        "files": {
            "lv_smart_meter_csv": {"filename": "smart_meter.csv", "profiles": 3, "scale": 1.2},
            # NB: single-column uploads crash BOTH v0 and current code
            # (1-D array reaches set_dmnd) — keep uploads >= 2 columns.
            "mv_solar_pv_csv": {"filename": "mv_solar.csv", "profiles": 2, "scale": 800.0},
        },
    },
]

# Cheap GET endpoints captured alongside /simulate as an API-contract check.
META_ENDPOINTS = [
    ("lv-network-urban", "/lv-network", {"n_id": "1060"}),
    ("lv-network-rural", "/lv-network", {"n_id": "1061"}),
    ("lv-defaults-urban-nearsub", "/lv-network-defaults", {"n_id": "1060", "lv_default": "near-sub"}),
    ("lv-defaults-rural-mixed", "/lv-network-defaults", {"n_id": "1061", "lv_default": "mixed"}),
    ("options-lv-ev", "/get-options", {"option_type": "lv-ev"}),
    ("options-lv-hp", "/get-options", {"option_type": "lv-hp"}),
    ("options-mv-solar-pv", "/get-options", {"option_type": "mv-solar-pv"}),
]


# ---------------------------------------------------------------------------
# HTTP helpers (stdlib only)
# ---------------------------------------------------------------------------


def _encode_multipart(files: dict) -> tuple[bytes, str]:
    """files: {field_name: (filename, bytes)} -> (body, content_type)."""
    boundary = "vgiRegression" + uuid.uuid4().hex
    out = io.BytesIO()
    for field, (filename, payload) in files.items():
        out.write(f"--{boundary}\r\n".encode())
        out.write(
            f'Content-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'.encode()
        )
        out.write(b"Content-Type: text/csv\r\n\r\n")
        out.write(payload)
        out.write(b"\r\n")
    out.write(f"--{boundary}--\r\n".encode())
    return out.getvalue(), f"multipart/form-data; boundary={boundary}"


def _request(url: str, method: str = "GET", files: dict | None = None, timeout: float = 600.0):
    """Return (status_code, body_text). Never raises for HTTP errors."""
    body, headers = None, {}
    if files:
        body, content_type = _encode_multipart(files)
        headers["Content-Type"] = content_type
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")


def _simulate_url(base_url: str, params: dict) -> str:
    query = urllib.parse.urlencode(params)
    return f"{base_url.rstrip('/')}/simulate?{query}"


# ---------------------------------------------------------------------------
# capture
# ---------------------------------------------------------------------------


def cmd_capture(args) -> int:
    base_url = args.url.rstrip("/")
    out_dir = Path(args.out)
    scenarios = load_scenarios(args.scenarios)
    if args.only:
        wanted = {s.strip() for s in args.only.split(",")}
        unknown = wanted - {s["id"] for s in scenarios}
        if unknown:
            print(f"error: unknown scenario id(s): {', '.join(sorted(unknown))}", file=sys.stderr)
            return 2
        scenarios = [s for s in scenarios if s["id"] in wanted]

    # Refuse to run against a dead server (clear error beats 8 timeouts).
    try:
        status, _ = _request(f"{base_url}/health-check", timeout=10)
    except (urllib.error.URLError, OSError) as e:
        print(f"error: cannot reach {base_url}/health-check: {e}", file=sys.stderr)
        return 2
    if status != 200:
        print(f"error: {base_url}/health-check returned HTTP {status}", file=sys.stderr)
        return 2

    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Capturing {len(scenarios)} scenario(s) from {base_url} into {out_dir}")

    # Contract-check GET endpoints.
    meta_results = {}
    for name, path, params in META_ENDPOINTS:
        url = f"{base_url}{path}?{urllib.parse.urlencode(params)}"
        try:
            status, text = _request(url, timeout=30)
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                payload = text
            meta_results[name] = {"status": status, "body": payload}
        except (urllib.error.URLError, OSError) as e:
            meta_results[name] = {"status": None, "error": str(e)}
    (out_dir / "meta_endpoints.json").write_text(
        json.dumps(meta_results, indent=2, sort_keys=True)
    )

    # A partial re-capture (--only) must extend the existing manifest, not
    # replace it — otherwise compare would forget the other scenarios.
    manifest_path = out_dir / "manifest.json"
    manifest_scenarios = list(scenarios)
    if manifest_path.exists():
        old = json.loads(manifest_path.read_text())
        new_ids = {s["id"] for s in manifest_scenarios}
        manifest_scenarios += [s for s in old.get("scenarios", []) if s["id"] not in new_ids]
    manifest = {
        "harness_version": HARNESS_VERSION,
        "url": base_url,
        "label": args.label or "",
        "captured_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "timeout_s": args.timeout,
        "scenarios": manifest_scenarios,
    }

    failures = 0
    for sc in scenarios:
        sc_dir = out_dir / sc["id"]
        sc_dir.mkdir(exist_ok=True)
        files = {
            field: (spec["filename"], _upload_profile_csv(spec["profiles"], spec["scale"]).encode())
            for field, spec in sc.get("files", {}).items()
        }
        url = _simulate_url(base_url, sc["params"])
        print(f"  {sc['id']} ... ", end="", flush=True)
        t0 = time.perf_counter()
        meta = {"scenario": sc, "url": url}
        try:
            status, text = _request(url, method="POST", files=files or None, timeout=args.timeout)
        except (urllib.error.URLError, OSError) as e:
            meta.update({"status": None, "error": str(e)})
            (sc_dir / "meta.json").write_text(json.dumps(meta, indent=2, sort_keys=True))
            print(f"ERROR ({e})")
            failures += 1
            continue
        elapsed = time.perf_counter() - t0
        meta.update({"status": status, "elapsed_s": round(elapsed, 3)})

        if status != 200:
            meta["error_body"] = text[:5000]
            (sc_dir / "meta.json").write_text(json.dumps(meta, indent=2, sort_keys=True))
            print(f"HTTP {status} ({elapsed:.1f}s)")
            failures += 1
            continue

        payload = json.loads(text)
        for key, fname in NUMERIC_DATASETS.items():
            (sc_dir / fname).write_text(payload.get(key, ""))
        meta["plots"] = {}
        for key in payload:
            if key in NUMERIC_DATASETS or key == "parameters":
                continue
            value = payload[key]
            # Only the base64 PNG plots are hashed here. Newer API responses
            # also carry non-plot keys — the `convergence` object (a dict) and
            # additional CSV datasets (`*_data`) that postdate the v0 baseline;
            # they are not base64 images, so skip them rather than trying to
            # decode them. `convergence` is preserved in meta for visibility.
            if not isinstance(value, str) or key.endswith("_data"):
                continue
            raw = base64.b64decode(value)
            meta["plots"][key] = {
                "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        if isinstance(payload.get("convergence"), dict):
            meta["convergence"] = payload["convergence"]
        meta["parameters"] = payload.get("parameters")
        (sc_dir / "meta.json").write_text(json.dumps(meta, indent=2, sort_keys=True))
        print(f"ok ({elapsed:.1f}s)")

    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    if failures:
        print(f"\ncapture finished with {failures} failed scenario(s) — see meta.json files")
    else:
        print("\ncapture complete")
    return 1 if failures else 0


def load_scenarios(path: str | None):
    if path:
        return json.loads(Path(path).read_text())
    return DEFAULT_SCENARIOS


# ---------------------------------------------------------------------------
# compare
# ---------------------------------------------------------------------------


def _parse_dataset(text: str):
    """Parse a '/simulate' CSV dataset: one header line, then float rows.
    Returns (header_list, rows_list_of_float_lists)."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return [], []
    header = [h.strip() for h in lines[0].split(",")]
    rows = []
    for ln in lines[1:]:
        rows.append([float(x) for x in ln.split(",")])
    return header, rows


def _close(a: float, b: float, rtol: float, atol: float) -> bool:
    if math.isnan(a) and math.isnan(b):
        return True
    if math.isinf(a) or math.isinf(b):
        return a == b
    return abs(a - b) <= atol + rtol * max(abs(a), abs(b))


def _rel_diff(a: float, b: float) -> float:
    scale = max(abs(a), abs(b))
    if scale == 0.0:
        return 0.0
    return abs(a - b) / scale


class DatasetResult:
    def __init__(self, name):
        self.name = name
        self.ok = True
        self.notes = []          # structural problems (header/shape/missing)
        self.max_abs = 0.0
        self.max_rel = 0.0
        self.n_cells = 0
        self.n_bad = 0
        self.worst = []          # [(rel, abs, row, col_name, base_val, cand_val)]


def _compare_dataset(name, base_text, cand_text, rtol, atol) -> DatasetResult:
    r = DatasetResult(name)
    bh, brows = _parse_dataset(base_text)
    ch, crows = _parse_dataset(cand_text)
    if bh != ch:
        r.ok = False
        r.notes.append(f"header mismatch: baseline {bh} vs candidate {ch}")
        return r
    if len(brows) != len(crows) or any(len(a) != len(b) for a, b in zip(brows, crows)):
        r.ok = False
        r.notes.append(
            f"shape mismatch: baseline {len(brows)}x{len(bh)} vs candidate {len(crows)}x{len(ch)}"
        )
        return r
    offenders = []
    for i, (ra, rb) in enumerate(zip(brows, crows)):
        for j, (a, b) in enumerate(zip(ra, rb)):
            r.n_cells += 1
            ad = abs(a - b) if not (math.isnan(a) or math.isnan(b)) else float("nan")
            rd = _rel_diff(a, b) if not (math.isnan(a) or math.isnan(b)) else float("nan")
            if not (math.isnan(ad)):
                r.max_abs = max(r.max_abs, ad)
                r.max_rel = max(r.max_rel, rd)
            if not _close(a, b, rtol, atol):
                r.n_bad += 1
                offenders.append((rd, ad, i, bh[j] if j < len(bh) else f"col{j}", a, b))
    if r.n_bad:
        r.ok = False
        offenders.sort(key=lambda t: (-(t[0] if not math.isnan(t[0]) else float("inf")),))
        r.worst = offenders[:5]
    return r


def _fmt(x: float) -> str:
    if x == 0:
        return "0"
    return f"{x:.2e}"


def cmd_compare(args) -> int:
    base_dir, cand_dir = Path(args.baseline), Path(args.candidate)
    for d in (base_dir, cand_dir):
        if not (d / "manifest.json").exists():
            print(f"error: {d} is not a capture directory (no manifest.json)", file=sys.stderr)
            return 2
    base_manifest = json.loads((base_dir / "manifest.json").read_text())
    cand_manifest = json.loads((cand_dir / "manifest.json").read_text())
    rtol, atol = args.rtol, args.atol

    lines = []  # markdown report
    lines.append("# VGI numeric regression report")
    lines.append("")
    lines.append(f"- baseline:  `{base_dir}` — {base_manifest.get('label') or base_manifest.get('url')}, captured {base_manifest.get('captured_at')}")
    lines.append(f"- candidate: `{cand_dir}` — {cand_manifest.get('label') or cand_manifest.get('url')}, captured {cand_manifest.get('captured_at')}")
    lines.append(f"- tolerance: |a-b| <= {atol:g} + {rtol:g}*max(|a|,|b|)  (OpenDSS solves to 1e-4; identical code gives 0)")
    lines.append("")

    scenario_ids = [s["id"] for s in base_manifest["scenarios"]]
    any_fail = False
    summary_rows = []
    detail_blocks = []

    for sid in scenario_ids:
        b_meta_p = base_dir / sid / "meta.json"
        c_meta_p = cand_dir / sid / "meta.json"
        if not c_meta_p.exists():
            any_fail = True
            summary_rows.append((sid, "MISSING", "-", "-", "scenario absent from candidate capture"))
            continue
        b_meta = json.loads(b_meta_p.read_text())
        c_meta = json.loads(c_meta_p.read_text())

        if b_meta.get("status") != c_meta.get("status"):
            any_fail = True
            summary_rows.append(
                (sid, "FAIL", "-", "-",
                 f"HTTP status differs: baseline {b_meta.get('status')} vs candidate {c_meta.get('status')}")
            )
            detail_blocks.append(
                f"## {sid}\n\nHTTP status differs: baseline {b_meta.get('status')} "
                f"vs candidate {c_meta.get('status')}.\n\n"
                f"Candidate body (truncated):\n\n```\n{c_meta.get('error_body', '')[:2000]}\n```\n"
            )
            continue
        if b_meta.get("status") != 200:
            summary_rows.append(
                (sid, "SKIP", "-", "-", f"both captures returned HTTP {b_meta.get('status')}")
            )
            continue

        results = []
        for key, fname in NUMERIC_DATASETS.items():
            bt = (base_dir / sid / fname).read_text() if (base_dir / sid / fname).exists() else ""
            ct = (cand_dir / sid / fname).read_text() if (cand_dir / sid / fname).exists() else ""
            results.append(_compare_dataset(fname.replace(".csv", ""), bt, ct, rtol, atol))

        # Plot presence (keys only — pixels differ legitimately across
        # matplotlib versions; identical hashes are reported as a bonus).
        b_plots, c_plots = b_meta.get("plots", {}), c_meta.get("plots", {})
        plot_note = ""
        missing_plots = sorted(set(b_plots) - set(c_plots))
        if missing_plots:
            plot_note = f"plots missing from candidate: {', '.join(missing_plots)}"
        else:
            identical = sum(
                1 for k in b_plots if k in c_plots and b_plots[k]["sha256"] == c_plots[k]["sha256"]
            )
            plot_note = f"plots: all {len(b_plots)} present ({identical} byte-identical)"

        max_rel = max((r.max_rel for r in results), default=0.0)
        max_abs = max((r.max_abs for r in results), default=0.0)
        failed = [r for r in results if not r.ok] or ([1] if missing_plots else [])
        if failed:
            any_fail = True
            summary_rows.append((sid, "FAIL", _fmt(max_rel), _fmt(max_abs), plot_note))
            block = [f"## {sid}", ""]
            for r in results:
                if r.ok:
                    block.append(f"- `{r.name}`: OK (max rel {_fmt(r.max_rel)}, max abs {_fmt(r.max_abs)})")
                    continue
                block.append(f"- `{r.name}`: **FAIL** — {r.n_bad}/{r.n_cells} cells out of tolerance"
                             + (f"; {'; '.join(r.notes)}" if r.notes else ""))
                for rd, ad, row, col, a, b in r.worst:
                    block.append(
                        f"    - row {row}, column `{col}`: baseline {a!r} vs candidate {b!r} "
                        f"(rel {_fmt(rd)}, abs {_fmt(ad)})"
                    )
            if missing_plots:
                block.append(f"- {plot_note}")
            detail_blocks.append("\n".join(block) + "\n")
        else:
            summary_rows.append((sid, "PASS", _fmt(max_rel), _fmt(max_abs), plot_note))

    # Meta (GET) endpoint contract comparison — informational unless different.
    meta_note = "meta endpoints: not captured"
    b_me, c_me = base_dir / "meta_endpoints.json", cand_dir / "meta_endpoints.json"
    if b_me.exists() and c_me.exists():
        bm, cm = json.loads(b_me.read_text()), json.loads(c_me.read_text())
        diffs = [k for k in bm if cm.get(k) != bm[k]]
        if diffs:
            any_fail = True
            meta_note = f"meta endpoints DIFFER: {', '.join(sorted(diffs))}"
        else:
            meta_note = f"meta endpoints: all {len(bm)} identical"

    # ---- emit ----
    lines.append("| scenario | verdict | max rel diff | max abs diff | notes |")
    lines.append("|---|---|---|---|---|")
    for sid, verdict, mr, ma, note in summary_rows:
        lines.append(f"| {sid} | {verdict} | {mr} | {ma} | {note} |")
    lines.append("")
    lines.append(f"- {meta_note}")
    lines.append("")
    verdict = "FAIL — differences found" if any_fail else "PASS — numeric outputs match within tolerance"
    lines.append(f"**Overall: {verdict}**")
    lines.append("")
    if detail_blocks:
        lines.append("---")
        lines.extend(detail_blocks)

    report = "\n".join(lines)
    if args.report:
        Path(args.report).write_text(report)

    # Console summary
    w = max(len(s[0]) for s in summary_rows) if summary_rows else 10
    print(f"{'scenario'.ljust(w)}  verdict  max rel    max abs    notes")
    for sid, v, mr, ma, note in summary_rows:
        print(f"{sid.ljust(w)}  {v.ljust(7)}  {mr.ljust(9)}  {ma.ljust(9)}  {note}")
    print(f"\n{meta_note}")
    print(f"\nOverall: {verdict}")
    if args.report:
        print(f"Report written to {args.report}")
    return 1 if any_fail else 0


# ---------------------------------------------------------------------------
# scenarios
# ---------------------------------------------------------------------------


def cmd_scenarios(args) -> int:
    scenarios = load_scenarios(args.scenarios)
    for sc in scenarios:
        print(f"{sc['id']}: {sc['description']}")
        print(f"    params: {json.dumps(sc['params'], ensure_ascii=False)}")
        if sc.get("files"):
            print(f"    uploads: {', '.join(sc['files'])}")
    return 0


# ---------------------------------------------------------------------------


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    pc = sub.add_parser("capture", help="run the scenario matrix against a server and store outputs")
    pc.add_argument("--url", required=True, help="base URL of the running API, e.g. http://127.0.0.1:8000")
    pc.add_argument("--out", required=True, help="directory to write the capture into")
    pc.add_argument("--label", help="human label stored in the manifest (e.g. 'v0 baseline')")
    pc.add_argument("--scenarios", help="JSON file overriding the built-in scenario matrix")
    pc.add_argument("--only", help="comma-separated scenario ids to run (subset)")
    pc.add_argument("--timeout", type=float, default=600.0, help="per-request timeout in seconds")
    pc.set_defaults(func=cmd_capture)

    pp = sub.add_parser("compare", help="numerically compare two capture directories")
    pp.add_argument("baseline")
    pp.add_argument("candidate")
    pp.add_argument("--rtol", type=float, default=1e-6, help="relative tolerance (default 1e-6)")
    pp.add_argument("--atol", type=float, default=1e-8, help="absolute tolerance (default 1e-8)")
    pp.add_argument("--report", help="write a markdown report to this path")
    pp.set_defaults(func=cmd_compare)

    ps = sub.add_parser("scenarios", help="list the scenario matrix")
    ps.add_argument("--scenarios", help="JSON file overriding the built-in scenario matrix")
    ps.set_defaults(func=cmd_scenarios)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
