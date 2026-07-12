"""Regression tests for the bugs fixed in this fork (see CHANGES.md).

Each test here reproduces a request that previously returned an unhandled
HTTP 500 (or crashed the process) and asserts the corrected behaviour.
"""
import datetime
import io

import pytest
from fastapi.testclient import TestClient

from vgi_api import app
from vgi_api.validation.validators import MAX_CSV_BYTES

client = TestClient(app)


def _profile_csv(first_gap_minutes: int = 30) -> str:
    """A 48-row profile whose first interval can be made invalid."""
    t = datetime.datetime(2000, 1, 1)
    times = [t, t + datetime.timedelta(minutes=first_gap_minutes)]
    while len(times) < 48:
        times.append(times[-1] + datetime.timedelta(minutes=30))
    rows = ["time,profile1"] + [f"{tt.strftime('%H:%M:%S')},1.0" for tt in times]
    return "\n".join(rows) + "\n"


def test_lv_plot_list_with_lv_default():
    """lv_plot_list together with lv_default (no lv_list) is documented as
    valid; it used to crash with AttributeError -> HTTP 500."""
    resp = client.post(
        "/simulate",
        params={
            "n_id": "1060",
            "lv_default": "near-sub",
            "lv_plot_list": "1101,1137",
            "dry_run": True,
        },
    )
    assert resp.status_code == 200


def test_lv_plot_list_not_in_lv_default():
    """Plot ids outside the chosen default set must be a 422, not accepted
    (and not a 500)."""
    resp = client.post(
        "/simulate",
        params={
            "n_id": "1060",
            "lv_default": "near-sub",
            "lv_plot_list": "1103",  # in near-edge, not near-sub
            "dry_run": True,
        },
    )
    assert resp.status_code == 422


def test_csv_option_without_file_is_422():
    """Selecting a csv profile option without uploading the file used to
    raise an unhandled IOError -> HTTP 500. Must be a 422."""
    resp = client.post(
        "/simulate",
        params={
            "n_id": "1060",
            "lv_default": "near-sub",
            "lv_smart_meter_profile": "csv",
            "dry_run": True,
        },
    )
    assert resp.status_code == 422


def test_csv_bad_first_interval_is_422():
    """The gap between the first two data rows was previously never checked."""
    csv = _profile_csv(first_gap_minutes=60)
    resp = client.post(
        "/simulate",
        params={
            "n_id": "1060",
            "lv_default": "near-sub",
            "lv_smart_meter_profile": "csv",
            "dry_run": True,
        },
        files={"lv_smart_meter_csv": ("p.csv", io.BytesIO(csv.encode()), "text/csv")},
    )
    assert resp.status_code == 422
    assert "30 min" in resp.text


def test_csv_binary_junk_is_422():
    resp = client.post(
        "/simulate",
        params={
            "n_id": "1060",
            "lv_default": "near-sub",
            "lv_smart_meter_profile": "csv",
            "dry_run": True,
        },
        files={
            "lv_smart_meter_csv": (
                "p.csv",
                io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64),
                "text/csv",
            )
        },
    )
    assert resp.status_code == 422


def test_csv_oversized_upload_is_422():
    """Uploads beyond MAX_CSV_BYTES must be rejected without being parsed."""
    big = b"0" * (MAX_CSV_BYTES + 1024)
    resp = client.post(
        "/simulate",
        params={
            "n_id": "1060",
            "lv_default": "near-sub",
            "lv_smart_meter_profile": "csv",
            "dry_run": True,
        },
        files={"lv_smart_meter_csv": ("p.csv", io.BytesIO(big), "text/csv")},
    )
    assert resp.status_code == 422
    assert "maximum allowed size" in resp.text


def test_valid_csv_still_accepted():
    """A well-formed profile must still validate after the stricter checks."""
    csv = _profile_csv(first_gap_minutes=30)
    resp = client.post(
        "/simulate",
        params={
            "n_id": "1060",
            "lv_default": "near-sub",
            "lv_smart_meter_profile": "csv",
            "dry_run": True,
        },
        files={"lv_smart_meter_csv": ("p.csv", io.BytesIO(csv.encode()), "text/csv")},
    )
    assert resp.status_code == 200
