"""Tests for the non-convergence reporting feature (Phase A).

A simulation solves the power flow independently at each of 48 half-hour
steps. When a step fails to converge its numbers are not physically
meaningful, so run_dss_simulation now reports per-step convergence in the
results dict and /simulate forwards it to the client. These tests pin that
contract and prove the failure path is actually detected (not just the happy
path).
"""

import copy

import numpy as np
import pytest

from vgi_api import azure_mockup
from vgi_api import azureOptsXmpls as aox
from vgi_api.validation import validate_profile
from vgi_api.validation.types import LVSmartMeterOptions, ProfileUnits


def build_parameters(n_id=1060, lv_list=("1101", "1137", "1110")):
    """Mirror what main.simulate builds from validated query parameters."""
    p = copy.deepcopy(aox.run_dict0)
    p["network_data"]["n_id"] = n_id
    p["network_data"]["xfmr_scale"] = 1.0
    p["network_data"]["oltc_setpoint"] = 104.0
    p["network_data"]["oltc_bandwidth"] = 1.3
    p["network_data"]["lv_sel"] = "lv_list"
    p["network_data"]["lv_list"] = list(lv_list)
    p["plot_options"]["lv_voltages"] = list(lv_list)[:2]
    p["simulation_data"]["smart_meter_profile_array"] = validate_profile(
        LVSmartMeterOptions.OPTION1, None, ProfileUnits.KW
    )
    return p


def test_convergence_block_present_and_shaped():
    """Every run reports a convergence block with the expected shape."""
    results = azure_mockup.run_dss_simulation(build_parameters())
    conv = results["convergence"]

    assert conv["n_steps"] == 48
    assert conv["n_failed"] == len(conv["failed_steps"])
    assert len(conv["failed_hours"]) == len(conv["failed_steps"])
    # failed_steps are valid step indices; failed_hours are their clock times.
    assert all(0 <= i < 48 for i in conv["failed_steps"])
    assert all(0.0 <= h < 24.0 for h in conv["failed_hours"])


def test_nominal_scenario_converges():
    """A normal scenario should converge at every step (n_failed == 0)."""
    results = azure_mockup.run_dss_simulation(build_parameters())
    assert results["convergence"]["n_failed"] == 0
    assert results["convergence"]["failed_steps"] == []


def test_failed_steps_are_detected(monkeypatch):
    """Force two steps to report non-convergence and assert they surface.

    We patch the recorded solution's Cnvg flag rather than trying to build a
    physically diverging network — this isolates the reporting/plumbing from
    the (separately tested) numerical behaviour, and guarantees a deterministic
    failed-step set (steps 10 and 11).
    """
    real_run = azure_mockup.ft.turingNet.run_dss_lds
    forced_failures = {10, 11}

    def fake_run(self, lds):
        slns, sln0 = real_run(self, lds)
        for i in forced_failures:
            slns[i].Cnvg = False
        return slns, sln0

    monkeypatch.setattr(azure_mockup.ft.turingNet, "run_dss_lds", fake_run)

    results = azure_mockup.run_dss_simulation(build_parameters())
    conv = results["convergence"]

    assert conv["n_failed"] == 2
    assert set(conv["failed_steps"]) == forced_failures
    # tt = arange(0, 24, 0.5) so step 10 -> 5.0 h, step 11 -> 5.5 h.
    assert conv["failed_hours"] == [5.0, 5.5]
    # The plots must still render (shading path exercised, no crash).
    assert results["mv_voltages_png"].startswith(b"\x89PNG\r\n\x1a\n")
    assert results["trn_powers_png"].startswith(b"\x89PNG\r\n\x1a\n")


def test_api_response_includes_convergence():
    """The /simulate response forwards the convergence block to the client."""
    from fastapi.testclient import TestClient

    from vgi_api import app

    client = TestClient(app)
    resp = client.post(
        "/simulate",
        params={
            "n_id": "1060",
            "lv_default": "near-sub",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "convergence" in body
    assert body["convergence"]["n_steps"] == 48
    assert body["convergence"]["n_failed"] == 0
