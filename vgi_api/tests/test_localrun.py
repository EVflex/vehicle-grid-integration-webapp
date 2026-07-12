"""Full-simulation smoke test.

CHANGES: the original test in this file was permanently skipped
("I'm not sure when this last passed") and compared base64 PNGs against a
golden JSON captured with a 2-tuple return signature that the code has not
had for a long time. Byte-identical image comparison is also inherently
fragile (matplotlib point releases legitimately change rasterisation).

This version runs a real end-to-end simulation and asserts on the *contract*:
every expected key is present, every plot is a non-empty PNG, and the CSV
datasets have the expected 48 time steps.
"""
import copy

import numpy as np
import pytest

from vgi_api import azure_mockup
from vgi_api import azureOptsXmpls as aox
from vgi_api.validation import validate_profile
from vgi_api.validation.types import LVSmartMeterOptions, ProfileUnits

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

EXPECTED_PNG_KEYS = [
    "mv_highlevel_png",
    "mv_highlevel_clean_png",
    "mv_powers_png",
    "lv_voltages_png",
    "lv_comparison_png",
    "mv_voltages_png",
    "trn_powers_png",
    "profile_options_png",
    "profile_options_dgs_png",
    "profile_options_fcs_png",
    "pmry_loadings_png",
    "pmry_powers_png",
]

EXPECTED_DATASETS = [
    "primary_loadings",
    "mv_voltages",
    "trn_powers",
    "lv_comparison",
]


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
    # The smart-meter profile is always present via the API (it has no "None"
    # option), and several code paths rely on it.
    p["simulation_data"]["smart_meter_profile_array"] = validate_profile(
        LVSmartMeterOptions.OPTION1, None, ProfileUnits.KW
    )
    return p


@pytest.mark.parametrize(
    "n_id,lv_list",
    [
        (1060, ("1101", "1137", "1110")),
        # Regression: a single LV network used to crash lv_comparison
        # (enumerate over a bare matplotlib Axes).
        (1060, ("1101",)),
    ],
)
def test_simulation_contract(n_id, lv_list):
    results = azure_mockup.run_dss_simulation(build_parameters(n_id, lv_list))

    for key in EXPECTED_PNG_KEYS:
        assert key in results, f"missing plot {key}"
        assert isinstance(results[key], bytes)
        assert results[key].startswith(PNG_MAGIC), f"{key} is not a PNG"

    for ds in EXPECTED_DATASETS:
        header = results[f"{ds}_header"]
        data = results[f"{ds}_data"]
        assert isinstance(header, list) and len(header) > 0
        assert isinstance(data, np.ndarray)
        assert data.shape[0] == 48, f"{ds} should have 48 half-hour rows"
        assert data.shape[1] == len(header), f"{ds} header/data column mismatch"
        assert np.all(np.isfinite(data)), f"{ds} contains non-finite values"
