"""Types used for validating API query parameters"""
from enum import Enum
from typing import List, Dict, Union
from pathlib import Path


class NetworkID(str, Enum):
    # See https://github.com/alan-turing-institute/e4Future-collab/blob/e1b9430c594e33736c924eaf0793ef484bd146d7/mtd-dss-digital-twins/slesNtwk_turing.py#L212
    URBAN = "1060"
    RURAL = "1061"


class AllOptions(str, Enum):

    MVSolarPVOptions = "mv-solar-pv"
    MVFCSOptions = "mv-fcs"
    LVSmartMeterOptions = "lv-smartmeter"
    LVElectricVehicleOptions = "lv-ev"
    LVPVOptions = "lv-pv"
    LVHPOptions = "lv-hp"


class DefaultLV(str, Enum):

    NEAR_SUB = "near-sub"
    NEAR_EDGE = "near-edge"
    MIXED = "mixed"


class MVSolarPVOptions(str, Enum):

    NONE = "None"
    OPTION1 = "Solar Plant Summer"
    OPTION2 = "Solar Plant Winter"
    CSV = "csv"


class MVFCSOptions(str, Enum):

    NONE = "None"
    OPTION1 = "FC Stations"
    CSV = "csv"


class LVSmartMeterOptions(str, Enum):
    OPTION1 = "CLNR"
    OPTION2 = "Crest"
    CSV = "csv"


class LVElectricVehicleOptions(str, Enum):
    NONE = "None"
    OPTION1 = "Crowdcharge—3.6kW"
    OPTION2 = "Crowdcharge—7kW"
    CSV = "csv"


class LVPVOptions(str, Enum):
    NONE = "None"
    OPTION1 = "Summer"
    OPTION2 = "Winter"
    CSV = "csv"


class LVHPOptions(str, Enum):
    NONE = "None"
    OPTION1 = "Mild weekday"
    OPTION2 = "Mild weekend"
    OPTION3 = "Cold weekday"
    OPTION4 = "Cold weekend"
    CSV = "csv"


class ProfileUnits(str, Enum):

    KW = "kW"
    KWH = "kWh"


# These are defaults that could be selected
DEFAULT_LV_NETWORKS: Dict[NetworkID, Dict[DefaultLV, List[int]]] = {
    NetworkID.RURAL: {
        DefaultLV.NEAR_SUB: [1102, 1154, 1262, 1206, 1202],
        DefaultLV.NEAR_EDGE: [1321, 1254, 1387, 1194, 1109],
        DefaultLV.MIXED: [1101, 1450, 1152, 1200, 1122],
    },
    NetworkID.URBAN: {
        DefaultLV.NEAR_SUB: [1101, 1137, 1110, 1116, 1117],
        DefaultLV.NEAR_EDGE: [1103, 1109, 1166, 1145, 1131],
        DefaultLV.MIXED: [1108, 1109, 1151, 1158, 1175],
    },
}


DATA_FOLDER = Path(__file__).parent.parent / "data" / "default_profiles"
MV_PROFILES = DATA_FOLDER / "MV_data"
LV_PROFILES = DATA_FOLDER / "LV_data"


MV_SOLAR_PROFILES: Dict[MVSolarPVOptions, Path] = {
    MVSolarPVOptions.OPTION1: MV_PROFILES / "MV_solar_plant_summer.csv",
    MVSolarPVOptions.OPTION2: MV_PROFILES / "MV_solar_plant_winter.csv",
}

MV_FCS_PROFILES: Dict[MVFCSOptions, Path] = {
    MVFCSOptions.OPTION1: MV_PROFILES / "fc_stations.csv",
}


LV_SMART_METER_PROFILES: Dict[LVSmartMeterOptions, Path] = {
    LVSmartMeterOptions.OPTION1: LV_PROFILES / "sm_CLNR.csv",
    LVSmartMeterOptions.OPTION2: LV_PROFILES / "sm_CREST_CIRED.csv",
}

LV_EV_PROFILES: Dict[LVElectricVehicleOptions, Path] = {
    LVElectricVehicleOptions.OPTION1: LV_PROFILES
    / "EV-crowdCharge--3.6kW--start-2018-01-01--end-2018-12-17--30min.csv",
    LVElectricVehicleOptions.OPTION2: LV_PROFILES
    / "EV-crowdCharge--7kW--start-2018-01-01--end-2018-12-17--30min.csv",
}

LV_PV_PROFILES: Dict[LVPVOptions, Path] = {
    LVPVOptions.OPTION1: LV_PROFILES / "PV_output_UK_southwest_summer_2021.csv",
    LVPVOptions.OPTION2: LV_PROFILES / "PV_output_UK_southwest_winter_2020_2021.csv",
}


LV_HP_PROFILES: Dict[LVHPOptions, Path] = {
    LVHPOptions.OPTION1: LV_PROFILES / "hp_mid_weekday_48ts.csv",
    LVHPOptions.OPTION2: LV_PROFILES / "hp_mid_weekend_48ts.csv",
    LVHPOptions.OPTION3: LV_PROFILES / "hp_weekday_48ts.csv",
    LVHPOptions.OPTION4: LV_PROFILES / "hp_weekend_48ts.csv",
}
