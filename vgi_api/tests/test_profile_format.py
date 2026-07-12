from pathlib import Path
from typing import Dict, Union, List
import pytest
from vgi_api.validation.types import (
    LV_EV_PROFILES,
    LV_HP_PROFILES,
    LV_PV_PROFILES,
    LV_SMART_METER_PROFILES,
    MV_FCS_PROFILES,
    MV_SOLAR_PROFILES,
    LVElectricVehicleOptions,
    LVHPOptions,
    LVPVOptions,
    LVSmartMeterOptions,
    MVFCSOptions,
    MVSolarPVOptions,
)

from vgi_api.validation.validators import validate_csv


def all_profiles():
    ALL_PROFILES: Dict[
        Union[
            MVSolarPVOptions,
            MVFCSOptions,
            LVSmartMeterOptions,
            LVElectricVehicleOptions,
            LVPVOptions,
            LVHPOptions,
        ],
        Path,
    ] = {}

    ALL_PROFILES.update(MV_SOLAR_PROFILES)
    ALL_PROFILES.update(MV_FCS_PROFILES)
    ALL_PROFILES.update(MV_FCS_PROFILES)
    ALL_PROFILES.update(LV_SMART_METER_PROFILES)
    ALL_PROFILES.update(LV_EV_PROFILES)
    ALL_PROFILES.update(LV_PV_PROFILES)
    ALL_PROFILES.update(LV_HP_PROFILES)

    return ALL_PROFILES


def test_expected_n_profiles():

    all_profile_paths: List[Path] = all_profiles().values()

    assert len(all_profile_paths) == 13


@pytest.mark.parametrize("profile_path", all_profiles().values())
def test_all_profiles_valid(profile_path):

    assert profile_path.exists()

    with profile_path.open(mode="rb") as f:

        validate_csv(f)
