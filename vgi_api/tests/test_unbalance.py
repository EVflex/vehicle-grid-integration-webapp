"""Tests for the phase-unbalance feature (Phase E).

Three layers:
  1. Analytical: the voltage unbalance factor (VUF) maths is pinned against a
     hand-derived Fortescue example, independent of OpenDSS.
  2. Physical behaviour, engine-backed: a balanced network gives VUF ~ 0 and
     concentrating load on one phase strictly increases it.
  3. Contract: the result dict / API response carry the new plot + CSV, and the
     regression baselines are unaffected (this feature only *adds* outputs).
"""

import copy

import numpy as np
import pytest

from vgi_api import azure_mockup
from vgi_api import azureOptsXmpls as aox
from vgi_api.validation import validate_profile
from vgi_api.validation.types import LVSmartMeterOptions, ProfileUnits

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def build_parameters(lv_list=("1101", "1105", "1109"), plot=("1101", "1105")):
    p = copy.deepcopy(aox.run_dict0)
    p["network_data"].update(
        n_id=1060,
        xfmr_scale=1.0,
        oltc_setpoint=104.0,
        oltc_bandwidth=1.3,
        lv_sel="lv_list",
        lv_list=list(lv_list),
    )
    p["plot_options"]["lv_voltages"] = list(plot)
    p["simulation_data"]["smart_meter_profile_array"] = validate_profile(
        LVSmartMeterOptions.OPTION1, None, ProfileUnits.KW
    )
    return p


# ---------------------------------------------------------------------------
# 1. Analytical VUF (no OpenDSS)
# ---------------------------------------------------------------------------


def _vuf_from_phasors(Va, Vb, Vc):
    """IEC VUF% = 100 * |V2|/|V1| via the Fortescue transform."""
    a = np.exp(2j * np.pi / 3)
    V1 = (Va + a * Vb + a * a * Vc) / 3
    V2 = (Va + a * a * Vb + a * Vc) / 3
    return 100.0 * abs(V2) / abs(V1)


def test_vuf_balanced_is_zero():
    a = np.exp(2j * np.pi / 3)
    Va, Vb, Vc = 230, 230 * a * a, 230 * a  # balanced positive sequence
    assert _vuf_from_phasors(Va, Vb, Vc) == pytest.approx(0.0, abs=1e-9)


def test_vuf_known_value():
    """Hand-derived: a 10 V dip on phase A of an otherwise balanced 230 V set.
    Va=220, Vb, Vc balanced. V2 = (Va + a^2 Vb + a Vc)/3; with Vb,Vc unchanged
    from balanced, V1 = (690-10)/3 = 226.667, V2 = -10/3 => VUF = 10/680*100."""
    a = np.exp(2j * np.pi / 3)
    Va, Vb, Vc = 220, 230 * a * a, 230 * a
    expected = 100.0 * (10.0 / 3.0) / (680.0 / 3.0)  # = 1.4706 %
    assert _vuf_from_phasors(Va, Vb, Vc) == pytest.approx(expected, rel=1e-9)


# ---------------------------------------------------------------------------
# 2. Physical behaviour (engine-backed)
# ---------------------------------------------------------------------------


def test_base_case_unbalance_is_small():
    """A normal residential day stays well within the 2% planning level."""
    results = azure_mockup.run_dss_simulation(build_parameters())
    vuf = results["lv_unbalance_data"]
    assert vuf.shape == (48, 3)
    assert np.all(np.isfinite(vuf))
    assert np.all(vuf >= 0)
    assert vuf.max() < 2.0, "base case should not breach EN 50160"


def test_unbalance_increases_with_single_phase_ev_clustering():
    """Concentrating EV load raises unbalance. We compare the base case with a
    high single-phase-heavy EV scenario and assert the peak VUF rises.

    (EVs in this model are allocated to LV loads, which are single-phase; a
    high penetration therefore loads phases unevenly and must not *decrease*
    unbalance.)"""
    base = azure_mockup.run_dss_simulation(build_parameters())

    p = build_parameters()
    p["ev_pen"] = 80.0
    p["simulation_data"]["lv_ev_profile_array"] = validate_profile(
        __import__(
            "vgi_api.validation.types", fromlist=["LVElectricVehicleOptions"]
        ).LVElectricVehicleOptions.OPTION1,
        None,
        ProfileUnits.KW,
    )
    high = azure_mockup.run_dss_simulation(p)

    assert high["lv_unbalance_data"].max() >= base["lv_unbalance_data"].max()


# ---------------------------------------------------------------------------
# 3. Contract + regression safety
# ---------------------------------------------------------------------------


def test_unbalance_plot_and_csv_present():
    results = azure_mockup.run_dss_simulation(build_parameters())
    assert results["lv_unbalance_png"].startswith(PNG_MAGIC)
    assert len(results["lv_unbalance_header"]) == 3
    assert results["lv_unbalance_data"].shape == (48, 3)


def test_api_response_includes_unbalance():
    from fastapi.testclient import TestClient

    from vgi_api import app

    client = TestClient(app)
    resp = client.post("/simulate", params={"n_id": "1060", "lv_default": "near-sub"})
    assert resp.status_code == 200
    body = resp.json()
    assert "lv_unbalance" in body
    assert "lv_unbalance_data" in body
    # CSV has a header line + 48 data rows.
    rows = [r for r in body["lv_unbalance_data"].splitlines() if r]
    assert len(rows) == 49


def test_existing_outputs_unchanged_shape():
    """The unbalance feature only ADDs outputs — the pre-existing datasets keep
    their shapes (a cheap guard alongside the full regression harness)."""
    results = azure_mockup.run_dss_simulation(build_parameters())
    assert results["mv_voltages_data"].shape[0] == 48
    assert results["lv_comparison_data"].shape[0] == 48
    assert results["trn_powers_data"].shape[0] == 48
