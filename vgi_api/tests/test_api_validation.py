"""Tests related to API argument validation"""
import io
from enum import Enum

# CHANGE(py3.14): fastapi's TestClient is httpx-based now; `requests` was
# only imported for a return-type annotation.
import httpx
import pytest
from devtools import debug
from fastapi.testclient import TestClient
from pydantic import ValidationError

from vgi_api import app
from vgi_api.validation import (
    DEFAULT_LV_NETWORKS,
    RESERVED_LV_NETWORKS,
    VALID_LV_NETWORKS_RURAL,
    VALID_LV_NETWORKS_URBAN,
    DefaultLV,
    LVSmartMeterOptions,
    MVFCSOptions,
    MVSolarPVOptions,
    NetworkID,
    ValidateLVParams,
)
from vgi_api.validation.types import LVElectricVehicleOptions, LVHPOptions, LVPVOptions

client = TestClient(app)


@pytest.mark.parametrize(
    "params",
    [
        (
            dict(
                lv_list=",".join([str(i) for i in VALID_LV_NETWORKS_URBAN[:5]]),
                n_id=NetworkID.URBAN.value,
            )
        ),
        (
            dict(
                # CHANGE(py3.14): send the enum's .value — the httpx-based
                # TestClient stringifies enum members as "DefaultLV.NEAR_SUB".
                lv_default=DefaultLV.NEAR_SUB.value,
                n_id=NetworkID.URBAN.value,
            )
        ),
    ],
)
def test_valid_params_simulation(params):
    """Test we get 200 status code with valid EV Distribution Network
    parameters"""

    params["dry_run"] = True
    response = client.post(
        app.url_path_for("simulate"),
        params=params,
    )

    debug(response.json())
    assert response.status_code == 200


@pytest.mark.parametrize(
    "params,loc",
    [
        (  # No n_id
            dict(
                lv_list=",".join([str(i) for i in VALID_LV_NETWORKS_URBAN[:5]]),
                # n_id=NetworkID.URBAN.value,
            ),
            ["query", "n_id"],
        ),
        (
            # Missing lv_list and lv_default
            dict(
                n_id=NetworkID.URBAN.value,
            ),
            ["lv_default"],
        ),
        (
            # Wrond default value
            dict(
                n_id=NetworkID.URBAN.value,
                lv_default=4,
            ),
            ["query", "lv_default"],
        ),
        (
            # xfmr_scale less than zero
            dict(
                lv_list=",".join([str(i) for i in VALID_LV_NETWORKS_URBAN[:5]]),
                n_id=NetworkID.URBAN.value,
                xfmr_scale=-0.3,
            ),
            ["query", "xfmr_scale"],
        ),
    ],
)
def test_invalid_params_simulation(params, loc):
    """Test we get 200 status code with valid EV Distribution Network
    parameters"""

    params["dry_run"] = True
    response = client.post(
        app.url_path_for("simulate"),
        params=params,
    )

    payload = response.json()
    debug(payload)
    assert response.status_code == 422
    # Check the parameter that was rejected was the correct one
    assert payload["detail"][0]["loc"] == loc


@pytest.mark.parametrize(
    "lv_list,n_id, lv_default",
    [
        ("1101,1102", NetworkID.URBAN.value, None),
        (None, NetworkID.URBAN.value, DefaultLV.NEAR_SUB),
        ("1101,1102,1103,1104,1105", NetworkID.URBAN.value, None),
    ],
)
def test_success_validate_lv_params(lv_list, n_id, lv_default):

    ValidateLVParams(lv_list=lv_list, n_id=n_id, lv_default=lv_default)


@pytest.mark.parametrize(
    "lv_list,n_id, lv_default",
    [
        (None, NetworkID.URBAN.value, None),  # must pass one of lv_list of lv_default
        ("2222", NetworkID.URBAN.value, None),  # Not in the list of valid network ids
        ("", NetworkID.URBAN.value, None),
        ("1101,1102,1103,1104,1105,1106", NetworkID.URBAN.value, None),
    ],
)
def test_failure_validate_lv_params(lv_list, n_id, lv_default):

    with pytest.raises(ValidationError) as err:
        ValidateLVParams(lv_list=lv_list, n_id=n_id, lv_default=lv_default)
    debug(err)


@pytest.mark.parametrize(
    "n_id",
    [(NetworkID.RURAL), (NetworkID.URBAN)],
)
def test_lv_network(n_id):

    response = client.get(
        app.url_path_for("lv_network"), params={"n_id": n_id.value, "dry_run": True}
    )

    payload = response.json()
    debug(payload)

    assert response.status_code == 200

    if n_id == NetworkID.RURAL:
        assert payload["networks"] == VALID_LV_NETWORKS_RURAL
    elif n_id == NetworkID.URBAN:
        assert payload["networks"] == VALID_LV_NETWORKS_URBAN


def test_reserved_networks_defined():
    # The lumped MV solar (DG) and FCS demand is hosted on these networks, so
    # they must stay lumped and never be offered for detailed LV modelling.
    assert RESERVED_LV_NETWORKS == [1106, 1107, 1142, 1143]


@pytest.mark.parametrize(
    "n_id,selectable",
    [
        (NetworkID.URBAN, VALID_LV_NETWORKS_URBAN),
        (NetworkID.RURAL, VALID_LV_NETWORKS_RURAL),
    ],
)
def test_reserved_networks_excluded_from_selectable(n_id, selectable):
    # Both feeders physically contain the reserved networks, but neither may
    # offer them as a "model in full" option (would drop the MV solar/FCS
    # demand). They must appear in NO selectable list.
    for reserved in RESERVED_LV_NETWORKS:
        assert reserved not in selectable

    # And the /lv-network endpoint (which drives the frontend dropdown) must
    # also omit them.
    response = client.get(
        app.url_path_for("lv_network"), params={"n_id": n_id.value, "dry_run": True}
    )
    assert response.status_code == 200
    payload = response.json()
    for reserved in RESERVED_LV_NETWORKS:
        assert reserved not in payload["networks"]


@pytest.mark.parametrize("n_id", [NetworkID.URBAN, NetworkID.RURAL])
def test_reserved_network_rejected_by_validation(n_id):
    # Selecting a reserved network for detailed modelling is rejected with a
    # clear, reserved-specific message (not the generic "not network ids").
    with pytest.raises(ValidationError) as err:
        ValidateLVParams(
            lv_list=f"1101,{RESERVED_LV_NETWORKS[0]}",
            n_id=n_id.value,
            lv_default=None,
        )
    assert "reserved" in str(err.value)


@pytest.mark.parametrize(
    "n_id",
    [NetworkID.RURAL, NetworkID.URBAN],
)
@pytest.mark.parametrize(
    "lv_default",
    [DefaultLV.NEAR_SUB, DefaultLV.MIXED, DefaultLV.NEAR_EDGE],
)
def test_lv_network_defaults(n_id, lv_default):

    response = client.get(
        app.url_path_for("lv_network_defaults"),
        params={"n_id": n_id.value, "lv_default": lv_default.value, "dry_run": True},
    )

    payload = response.json()
    debug(payload)

    assert response.status_code == 200

    assert payload["networks"] == DEFAULT_LV_NETWORKS[n_id][lv_default]


def upload_csv(file: io.BytesIO, param_key, option, csv_name) -> httpx.Response:

    file_name = "example_profile.csv"
    upload_file = {csv_name: (file_name, file)}
    return client.post(
        app.url_path_for("simulate"),
        files=upload_file,
        params={
            "lv_default": DefaultLV.NEAR_SUB.value,
            "n_id": NetworkID.URBAN.value,
            # CHANGE(py3.14): .value — see test_valid_params_simulation.
            param_key: option.value,
            "dry_run": True,
        },
    )


@pytest.mark.parametrize(
    "param_key, option, csv_name",
    [
        ("mv_solar_pv_profile", MVSolarPVOptions.CSV, "mv_solar_pv_csv"),
        ("mv_fcs_profile", MVFCSOptions.CSV, "mv_fcs_csv"),
        ("lv_smart_meter_profile", LVSmartMeterOptions.CSV, "lv_smart_meter_csv"),
        ("lv_ev_profile", LVElectricVehicleOptions.CSV, "lv_ev_csv"),
        ("lv_pv_profile", LVPVOptions.CSV, "lv_pv_csv"),
        ("lv_hp_profile", LVHPOptions.CSV, "lv_hp_csv"),
    ],
)
def test_valid_csv(valid_profile_csv: io.BytesIO, param_key, option, csv_name):

    resp = upload_csv(valid_profile_csv, param_key, option, csv_name)
    debug(resp.json())
    assert resp.status_code == 200


@pytest.mark.parametrize(
    "param_key, option, csv_name",
    [
        ("mv_solar_pv_profile", MVSolarPVOptions.CSV, "mv_solar_pv_csv"),
        ("mv_fcs_profile", MVFCSOptions.CSV, "mv_fcs_csv"),
        ("lv_smart_meter_profile", LVSmartMeterOptions.CSV, "lv_smart_meter_csv"),
        ("lv_ev_profile", LVElectricVehicleOptions.CSV, "lv_ev_csv"),
        ("lv_pv_profile", LVPVOptions.CSV, "lv_pv_csv"),
        ("lv_hp_profile", LVHPOptions.CSV, "lv_hp_csv"),
    ],
)
def test_valid_extra_blank_lines_csv(
    valid_profile_extra_lines_csv: io.BytesIO, param_key, option, csv_name
):

    resp = upload_csv(valid_profile_extra_lines_csv, param_key, option, csv_name)
    debug(resp.json())
    assert resp.status_code == 200


@pytest.mark.parametrize(
    "param_key, option, csv_name",
    [
        ("mv_solar_pv_profile", MVSolarPVOptions.CSV, "mv_solar_pv_csv"),
        ("mv_fcs_profile", MVFCSOptions.CSV, "mv_fcs_csv"),
        ("lv_smart_meter_profile", LVSmartMeterOptions.CSV, "lv_smart_meter_csv"),
        ("lv_ev_profile", LVElectricVehicleOptions.CSV, "lv_ev_csv"),
        ("lv_pv_profile", LVPVOptions.CSV, "lv_pv_csv"),
        ("lv_hp_profile", LVHPOptions.CSV, "lv_hp_csv"),
    ],
)
def test_valid_extra_extra_blank_lines_csv(
    valid_profile_extra_extra_lines_csv: io.BytesIO, param_key, option, csv_name
):

    resp = upload_csv(valid_profile_extra_extra_lines_csv, param_key, option, csv_name)
    debug(resp.json())
    assert resp.status_code == 200


@pytest.mark.parametrize(
    "param_key, option, csv_name",
    [
        ("mv_solar_pv_profile", MVSolarPVOptions.CSV, "mv_solar_pv_csv"),
        ("mv_fcs_profile", MVFCSOptions.CSV, "mv_fcs_csv"),
        ("lv_smart_meter_profile", LVSmartMeterOptions.CSV, "lv_smart_meter_csv"),
        ("lv_ev_profile", LVElectricVehicleOptions.CSV, "lv_ev_csv"),
        ("lv_pv_profile", LVPVOptions.CSV, "lv_pv_csv"),
        ("lv_hp_profile", LVHPOptions.CSV, "lv_hp_csv"),
    ],
)
def test_invalid_csv_long(
    invalid_profile_csv_too_long: io.BytesIO, param_key, option, csv_name
):

    resp = upload_csv(invalid_profile_csv_too_long, param_key, option, csv_name)
    debug(resp.json())
    assert resp.status_code == 422


@pytest.mark.parametrize(
    "param_key, option, csv_name",
    [
        ("mv_solar_pv_profile", MVSolarPVOptions.CSV, "mv_solar_pv_csv"),
        ("mv_fcs_profile", MVFCSOptions.CSV, "mv_fcs_csv"),
        ("lv_smart_meter_profile", LVSmartMeterOptions.CSV, "lv_smart_meter_csv"),
        ("lv_ev_profile", LVElectricVehicleOptions.CSV, "lv_ev_csv"),
        ("lv_pv_profile", LVPVOptions.CSV, "lv_pv_csv"),
        ("lv_hp_profile", LVHPOptions.CSV, "lv_hp_csv"),
    ],
)
def test_invalid_csv_short(
    invalid_profile_csv_too_short: io.BytesIO, param_key, option, csv_name
):

    resp = upload_csv(invalid_profile_csv_too_short, param_key, option, csv_name)
    debug(resp.json())
    assert resp.status_code == 422


@pytest.mark.parametrize(
    "param_key, option, csv_name",
    [
        ("mv_solar_pv_profile", MVSolarPVOptions.CSV, "mv_solar_pv_csv"),
        ("mv_fcs_profile", MVFCSOptions.CSV, "mv_fcs_csv"),
        ("lv_smart_meter_profile", LVSmartMeterOptions.CSV, "lv_smart_meter_csv"),
        ("lv_ev_profile", LVElectricVehicleOptions.CSV, "lv_ev_csv"),
        ("lv_pv_profile", LVPVOptions.CSV, "lv_pv_csv"),
        ("lv_hp_profile", LVHPOptions.CSV, "lv_hp_csv"),
    ],
)
def test_invalid_csv_wrong_time(
    invalid_profile_wrong_time: io.BytesIO, param_key, option, csv_name
):

    resp = upload_csv(invalid_profile_wrong_time, param_key, option, csv_name)
    debug(resp.json())
    assert resp.status_code == 422


@pytest.mark.parametrize(
    "param_key, option, csv_name",
    [
        ("mv_solar_pv_profile", MVSolarPVOptions.CSV, "mv_solar_pv_csv"),
        ("mv_fcs_profile", MVFCSOptions.CSV, "mv_fcs_csv"),
        ("lv_smart_meter_profile", LVSmartMeterOptions.CSV, "lv_smart_meter_csv"),
        ("lv_ev_profile", LVElectricVehicleOptions.CSV, "lv_ev_csv"),
        ("lv_pv_profile", LVPVOptions.CSV, "lv_pv_csv"),
        ("lv_hp_profile", LVHPOptions.CSV, "lv_hp_csv"),
    ],
)
def test_invalid_csv_offset(
    invalid_profile_csv_offset: io.BytesIO, param_key, option, csv_name
):

    resp = upload_csv(invalid_profile_csv_offset, param_key, option, csv_name)
    debug(resp.json())
    assert resp.status_code == 422


@pytest.mark.parametrize(
    "param_key, option, csv_name",
    [
        ("mv_solar_pv_profile", MVSolarPVOptions.CSV, "mv_solar_pv_csv"),
        ("mv_fcs_profile", MVFCSOptions.CSV, "mv_fcs_csv"),
        ("lv_smart_meter_profile", LVSmartMeterOptions.CSV, "lv_smart_meter_csv"),
        ("lv_ev_profile", LVElectricVehicleOptions.CSV, "lv_ev_csv"),
        ("lv_pv_profile", LVPVOptions.CSV, "lv_pv_csv"),
        ("lv_hp_profile", LVHPOptions.CSV, "lv_hp_csv"),
    ],
)
def test_invalid_csv_not_float(
    invalid_profile_csv_not_float: io.BytesIO, param_key, option, csv_name
):

    resp = upload_csv(invalid_profile_csv_not_float, param_key, option, csv_name)
    debug(resp.json())
    assert resp.status_code == 422


@pytest.mark.parametrize(
    "param_key, option, csv_name",
    [
        ("mv_solar_pv_profile", MVSolarPVOptions.CSV, "mv_solar_pv_csv"),
        ("mv_fcs_profile", MVFCSOptions.CSV, "mv_fcs_csv"),
        ("lv_smart_meter_profile", LVSmartMeterOptions.CSV, "lv_smart_meter_csv"),
        ("lv_ev_profile", LVElectricVehicleOptions.CSV, "lv_ev_csv"),
        ("lv_pv_profile", LVPVOptions.CSV, "lv_pv_csv"),
        ("lv_hp_profile", LVHPOptions.CSV, "lv_hp_csv"),
    ],
)
def test_one_dim_csv(valid_csv_one_dim: io.BytesIO, param_key, option, csv_name):

    resp = upload_csv(valid_csv_one_dim, param_key, option, csv_name)
    debug(resp.json())
    assert resp.status_code == 200


# ToDo: We should have a test for every option
@pytest.mark.parametrize(
    "param_key, option",
    [
        ("mv_solar_pv_profile", MVSolarPVOptions.OPTION1),
        ("mv_fcs_charger_profile", MVFCSOptions.OPTION1),
        ("lv_smart_meter_profile", LVSmartMeterOptions.OPTION1),
        ("lv_ev_profile", LVElectricVehicleOptions.OPTION1),
        ("lv_pv_profile", LVPVOptions.OPTION1),
        ("lv_hp_profile", LVHPOptions.OPTION1),
    ],
)
def test_csv_options(param_key: str, option: Enum):
    """Check we dont get a validation error when uploading files"""

    resp = client.post(
        app.url_path_for("simulate"),
        params={
            "lv_default": DefaultLV.NEAR_SUB.value,
            "n_id": NetworkID.URBAN.value,
            "dry_run": True,
            param_key: option.value,
        },
    )
    debug(resp.json())
    assert resp.status_code == 200
