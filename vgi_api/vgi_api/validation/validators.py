"""validators.py — request validation for the /simulate endpoint.

HOW THIS FILE DIFFERS FROM THE ORIGINAL (v0) validators.py
----------------------------------------------------------
Every change is also marked inline with a FIX/CHANGE comment at the exact
location, and described in CHANGES.md at the repository root. Summary:

1. FIX(bug): combining `lv_plot_list` with `lv_default` (no `lv_list`)
   crashed with `None.strip()` → HTTP 500. Root causes: field order (the
   plot-list validator could never see `lv_default`, declared after it),
   and the plot list is now validated against whichever selection method
   was actually used.
2. FIX(bug): validate_lv_plot_list had no `return v`, so even a valid plot
   list was silently discarded (main.py used to re-parse the raw query
   string as a workaround). validate_lv_parameters now returns the plot
   list alongside the network list.
3. FIX(bug): selecting a "csv" profile option without attaching a file
   raised IOError, which pydantic does not convert into a validation error
   → HTTP 500. Now ValueError → a clean 422 with a readable message.
4. FIX(bug): the CSV 30-minute-interval check skipped the first pair of
   data rows (`len(time_deltas) > 1` → `if time_deltas`).
5. FIX(security): uploads are read through a MAX_CSV_BYTES cap instead of
   an unbounded readlines() (memory-exhaustion denial-of-service).
6. CHANGE (2026-07-09): network ids reserved for the lumped MV solar/FCS
   demand are rejected with a specific message (see network_ids.py).
7. CHANGE(py3.14): migrated pydantic v1 → v2 (v1 does not run on
   Python >= 3.13). Validation behaviour is unchanged.
"""

import logging
from typing import IO, Optional, List, Tuple, Union
from fastapi import HTTPException
from fastapi import UploadFile
from pathlib import Path
from fastapi.exceptions import RequestValidationError
# CHANGE(py3.14): migrated from pydantic v1 to v2 (pydantic v1 does not run
# on Python >= 3.13). v1 `@validator(...)` becomes `@field_validator(...)`
# (with the earlier-fields dict now on `info.data`), `always=True` validators
# become `@model_validator(mode="after")`, and ValidationError moved to the
# package root. Validation *behaviour* is unchanged; see CHANGES.md §12.
from pydantic import (
    BaseModel,
    ConfigDict,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)
from starlette.datastructures import UploadFile as StarletteUploadFile
from vgi_api import validation
from vgi_api.validation import (
    NetworkID,
    DefaultLV,
    VALID_LV_NETWORKS_RURAL,
    VALID_LV_NETWORKS_URBAN,
    RESERVED_LV_NETWORKS,
    DEFAULT_LV_NETWORKS,
)
from vgi_api.validation.types import (
    MVFCSOptions,
    MVSolarPVOptions,
    LVSmartMeterOptions,
    LVElectricVehicleOptions,
    MV_SOLAR_PROFILES,
    MV_FCS_PROFILES,
    LV_SMART_METER_PROFILES,
    LV_EV_PROFILES,
    LV_PV_PROFILES,
    LV_HP_PROFILES,
    LVHPOptions,
    LVPVOptions,
    ProfileUnits,
)
import tempfile
import numpy as np
import datetime

# FIX(security): Maximum number of bytes we are willing to *parse* from an
# uploaded CSV. Previously `validate_csv` called `v.readlines()` with no
# limit, which means a single multi-gigabyte upload would be decoded and
# split into Python lists in memory before any validation happened (a trivial
# memory-exhaustion denial-of-service).
#
# The cap is 10 MB because the largest *bundled* profile (the crowdCharge EV
# dataset, ~8.6 MB with hundreds of charger columns) is validated through this
# same function by the test suite — the limit must stay above that. NOTE:
# this caps what we parse; the overall request body size should *also* be
# limited at the platform level (Azure Functions / App Service / reverse
# proxy) — see CHANGES.md.
MAX_CSV_BYTES = 10_000_000


class ValidateLVParams(BaseModel):
    # FIX(bug): field order matters in pydantic v1 — validators receive, via
    # the `values` dict, only the fields declared *before* the field being
    # validated. `lv_plot_list` must be validated against `lv_list` *or*
    # `lv_default`, so `lv_default` has been moved above `lv_plot_list`
    # (previously it was declared after it, so the plot-list validator could
    # never see it, and passing `lv_plot_list` together with `lv_default`
    # crashed with an AttributeError → HTTP 500).
    # CHANGE(py3.14): pydantic v2 no longer treats `Optional[X]` as implicitly
    # defaulting to None — the `= None` defaults are now required.
    n_id: NetworkID
    lv_list: Optional[str] = None
    lv_default: Optional[DefaultLV] = None
    lv_plot_list: Optional[str] = None

    @field_validator("lv_list")
    @classmethod
    def validate_lv_list(cls, v: Optional[str], info: ValidationInfo):
        values = info.data

        # lv_list is not required
        if v is None:
            return v

        if v == "":
            raise ValueError("No values passed")

        lv_list_int = ValidateLVParams._parse_lv_list(v)
        lv_list_len = len(lv_list_int)

        if (lv_list_len > 5) or (lv_list_len < 1):
            raise ValueError("lv_list` must be at least 1 and up to 5 items")

        lv_set = set(lv_list_int)

        # CHANGE (2026-07-09): reject the networks reserved for the lumped MV
        # solar / FCS demand with a clear message before the generic
        # "not network ids" check below (they are excluded from the selectable
        # lists, so the subset check would otherwise flag them as unknown). See
        # CHANGES.md.
        reserved = sorted(lv_set.intersection(RESERVED_LV_NETWORKS))
        if reserved:
            raise ValueError(
                f"lv_list values {reserved} are reserved for the lumped MV "
                "solar / fast-charge-station demand and cannot be modelled in "
                "detail"
            )

        valid = False
        if values["n_id"] == NetworkID.URBAN:
            urban_set = set(VALID_LV_NETWORKS_URBAN)
            valid = lv_set.issubset(urban_set)
            difference = lv_set.difference(urban_set)
        elif values["n_id"] == NetworkID.RURAL:
            rural_set = set(VALID_LV_NETWORKS_RURAL)
            valid = lv_set.issubset(rural_set)
            difference = lv_set.difference(rural_set)
        if not valid:
            raise ValueError(f"lv_list values: {list(difference)} are not network ids")

        return v

    @field_validator("lv_default")
    @classmethod
    def validate_lv_default(cls, v: Optional[DefaultLV], info: ValidationInfo):
        values = info.data

        # `values.get(...)` (not `values[...]`) because if lv_list itself
        # failed validation it will be absent from `values`.
        if (v is None) and (values.get("lv_list", None) is None):
            raise ValueError("One of lv_list or lv_default must be provided")

        return v

    @field_validator("lv_plot_list")
    @classmethod
    def validate_lv_plot_list(cls, v: Optional[str], info: ValidationInfo):
        values = info.data

        if v is None:
            return v

        # FIX(bug): the plot list is documented as valid against *either* the
        # user-supplied `lv_list` *or* the chosen `lv_default` set. The old
        # code unconditionally parsed `values["lv_list"]`, so a request such
        # as `?lv_default=near-sub&lv_plot_list=1101,1137` (no lv_list) called
        # `None.strip()` and returned an unhandled 500 to the user. We now
        # resolve the allowed set from whichever selection method was used.
        allowed_ids: Optional[set] = None
        if values.get("lv_list") is not None:
            allowed_ids = set(ValidateLVParams._parse_lv_list(values["lv_list"]))
        elif values.get("lv_default") is not None:
            allowed_ids = set(
                DEFAULT_LV_NETWORKS[values["n_id"]][values["lv_default"]]
            )

        plot_list = ValidateLVParams._parse_lv_list(v)

        if len(plot_list) > 2:
            raise ValueError("lv_plot_list must only contain two ids")

        # If neither lv_list nor lv_default survived their own validation we
        # cannot check membership here — but a validation error has already
        # been recorded for those fields, so we simply skip the check rather
        # than raise a confusing secondary error.
        if allowed_ids is not None and not set(plot_list).issubset(allowed_ids):
            raise ValueError(
                "lv_plot_list contains ids not in `lv_list` (or the chosen `lv_default` set)"
            )

        # FIX(bug): the original validator had no `return`, so pydantic set the
        # field to None even when validation passed. The API previously worked
        # around this by re-parsing the raw query parameter in main.py.
        return v

    @classmethod
    def _parse_lv_list(cls, input: str) -> List[int]:
        # `int(i)` raises ValueError on junk (e.g. "1101;1102"), which pydantic
        # converts into a 422 validation error — exactly what we want.
        return [int(i.strip()) for i in input.strip().split(",")]

    def _get_default_list(self) -> List[int]:

        return DEFAULT_LV_NETWORKS[self.n_id][self.lv_default]

    def value(self) -> List[int]:
        """The validated list of LV network ids to simulate."""
        if self.lv_list:
            return ValidateLVParams._parse_lv_list(self.lv_list)

        if self.lv_default:
            return self._get_default_list()

    def plot_value(self) -> Optional[List[int]]:
        """The validated list of LV network ids to plot (or None if the user
        did not provide one — the caller falls back to the first two
        simulated networks)."""
        if self.lv_plot_list:
            return ValidateLVParams._parse_lv_list(self.lv_plot_list)
        return None


def validate_lv_parameters(
    lv_list: Optional[str],
    lv_default: Optional[DefaultLV],
    lv_plot_list: Optional[str],
    n_id: NetworkID,
) -> Tuple[List[int], Optional[List[int]]]:
    """Validate the Low Voltage Network parameters.

    Pass either `lv_list` or `lv_default`. If both are passed will use `lv_list`.

    Args:
        lv_list (Optional[str]): A str of comma seperated network ids
        lv_default (Optional[DefaultLV]): A DefaultLV choice
        lv_plot_list (Optional[str]): A str of comma separated network ids to plot
        n_id (NetworkID): The choice of medium voltage network

    Returns:
        Tuple[List[int], Optional[List[int]]]: (the validated list of network
        ids to simulate, the validated list of network ids to plot — or None
        if the caller should choose a default)
    """

    try:
        params = ValidateLVParams(
            n_id=n_id, lv_list=lv_list, lv_plot_list=lv_plot_list, lv_default=lv_default
        )
    except ValidationError as e:
        raise RequestValidationError(errors=e.errors())
    return params.value(), params.plot_value()


class ProfileBaseModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)


def csv_to_array(file: Union[tempfile.SpooledTemporaryFile, Path]) -> np.array:
    """Convert a csv file to numpy array"""

    if isinstance(file, tempfile.SpooledTemporaryFile):
        # Make sure we're at start of file
        file.seek(0)

        ncols = len(file.readline().decode().split(","))
        return np.loadtxt(
            file, dtype=float, skiprows=0, usecols=range(1, ncols), delimiter=","
        )

    elif isinstance(file, Path):

        with file.open() as f:
            ncols = len(f.readline().split(","))

        return np.loadtxt(
            file, dtype=float, skiprows=1, usecols=range(1, ncols), delimiter=","
        )

    else:
        raise NotImplementedError(f"Not implemented for type {type(file)}")


def validate_csv(v: Optional[Union[IO, UploadFile]]):
    """Validate an uploaded csv

    Args:
        v (IO): CSV file uploaded

    Raises:
        ValueError: A csv option was selected but no file was uploaded
        ValueError: File larger than MAX_CSV_BYTES
        ValueError: Must be 48 rows of data excluding header
        ValueError: Time deltas must be in 30 minute intervals in HH-MM-SS
        ValueError: All non header element in column 1 onwards must be parsable as floats

    Returns:
        IO: Return v
    """

    if v is None:
        # FIX(bug): this was `raise IOError(...)`. Pydantic v1 only converts
        # ValueError/TypeError/AssertionError raised inside validators into
        # validation errors; an IOError escaped the framework entirely, so
        # selecting a "csv" profile option without attaching the file returned
        # an unhandled HTTP 500 instead of a helpful 422.
        raise ValueError(
            "A CSV file was not uploaded or did not have the correct name"
        )

    if isinstance(v, StarletteUploadFile):
        v: IO = v.file

    # FIX(security): read at most MAX_CSV_BYTES + 1 bytes instead of slurping
    # the whole (attacker-controlled) upload with readlines().
    raw = v.read(MAX_CSV_BYTES + 1)
    if len(raw) > MAX_CSV_BYTES:
        raise ValueError(
            f"File is larger than the maximum allowed size of {MAX_CSV_BYTES} bytes"
        )

    # Check we have the right number of lines
    expected_n_lines_excluding_header = 24 * 2
    expect_n_lines = expected_n_lines_excluding_header + 1

    # A UnicodeDecodeError here (e.g. a binary file renamed to .csv) is a
    # subclass of ValueError, so it is reported as a 422 validation error.
    lines = [l.replace(" ", "").split(",") for l in raw.decode().splitlines()]

    # Remove empty lines
    lines = [l for l in lines if not all([i == "" for i in l])]

    n_lines = len(lines)
    if n_lines != expect_n_lines:
        raise ValueError(
            f"File has {n_lines} rows. Expecting {expect_n_lines} including header row"
        )

    # Check time delta column. Every time delta should be 30 min appart
    time_deltas = []
    for r, row in enumerate(lines[1:]):

        time = datetime.datetime.strptime(row[0], "%H:%M:%S")
        delta = datetime.timedelta(
            hours=time.hour, minutes=time.minute, seconds=time.second
        )

        # Check it is 30 min after the last time.
        # FIX(bug): this condition was `len(time_deltas) > 1`, which skipped
        # the check for the *first pair* of data rows (rows 2 and 3 of the
        # file). A profile whose first interval was e.g. 1 hour could slip
        # through undetected in some arrangements. `if time_deltas` checks
        # every consecutive pair. (The absolute start time is deliberately
        # unconstrained — the documented contract is "any values, but at 30
        # minute intervals".)
        if time_deltas and (
            (delta - time_deltas[-1])
            != datetime.timedelta(hours=0, minutes=30, seconds=0)
        ):
            raise ValueError(
                f"Time on row {r+2} of file: '{delta}' is not 30 min after last row: {time_deltas[-1]}"
            )

        time_deltas.append(delta)

        # Check everything else can be a float
        for c, elem in enumerate(row[1:]):
            try:
                float(elem)
            except ValueError:
                raise ValueError(
                    f"Value on row: {r+2}, col: {c + 2} of file (value = '{elem}') cannot be parsed as float"
                )

    # If we got this far everything looks good
    return v


class MVSolarProfile(ProfileBaseModel):
    mv_solar_pv_csv: tempfile.SpooledTemporaryFile
    positive_val: bool = True

    @field_validator("mv_solar_pv_csv", mode="before")
    @classmethod
    def _validate_csv(cls, v):
        return validate_csv(v)

    # CHANGE(py3.14): pydantic v2 — was a `@validator(..., always=True)` on
    # `positive_val`; an after-model-validator has the same semantics (runs
    # once the csv field has validated, even when positive_val is defaulted).
    @model_validator(mode="after")
    def check_positive(self):
        if self.positive_val:
            if np.any(csv_to_array(self.mv_solar_pv_csv) < 0):
                raise ValueError("All values in mv_solar_pv_csv must be greater than 0")
        return self

    def to_array(self) -> np.array:

        return csv_to_array(self.mv_solar_pv_csv)


class MVFCSProfile(ProfileBaseModel):

    mv_fcs_charger_csv: tempfile.SpooledTemporaryFile

    @field_validator("mv_fcs_charger_csv", mode="before")
    @classmethod
    def _validate_csv(cls, v):
        return validate_csv(v)

    def to_array(self) -> np.array:

        return csv_to_array(self.mv_fcs_charger_csv)


class LVSmartMeterProfile(ProfileBaseModel):

    lv_smart_meter_csv: tempfile.SpooledTemporaryFile

    @field_validator("lv_smart_meter_csv", mode="before")
    @classmethod
    def _validate_csv(cls, v):
        return validate_csv(v)

    def to_array(self) -> np.array:

        return csv_to_array(self.lv_smart_meter_csv)


class LVEVProfile(ProfileBaseModel):

    lv_ev_csv: tempfile.SpooledTemporaryFile

    @field_validator("lv_ev_csv", mode="before")
    @classmethod
    def _validate_csv(cls, v):
        return validate_csv(v)

    def to_array(self) -> np.array:

        return csv_to_array(self.lv_ev_csv)


class LVPVProfile(ProfileBaseModel):

    lv_pv_csv: tempfile.SpooledTemporaryFile
    positive_val: bool = True

    @field_validator("lv_pv_csv", mode="before")
    @classmethod
    def _validate_csv(cls, v):
        return validate_csv(v)

    @model_validator(mode="after")
    def check_positive(self):
        if self.positive_val:
            if np.any(csv_to_array(self.lv_pv_csv) < 0):
                raise ValueError("All values in lv_pv_csv must be greater than 0")
        return self

    def to_array(self) -> np.array:

        return csv_to_array(self.lv_pv_csv)


class LVHPProfile(ProfileBaseModel):

    lv_hp_csv: tempfile.SpooledTemporaryFile

    @field_validator("lv_hp_csv", mode="before")
    @classmethod
    def _validate_csv(cls, v):
        return validate_csv(v)

    def to_array(self) -> np.array:

        return csv_to_array(self.lv_hp_csv)


def validate_profile(
    options: Union[
        MVSolarPVOptions,
        MVFCSOptions,
        LVSmartMeterOptions,
        LVElectricVehicleOptions,
        LVPVOptions,
        LVHPOptions,
    ],
    csv_file: Optional[UploadFile],
    units: ProfileUnits,
) -> Optional[np.ndarray]:
    """Pass an enum of profile options: `options`. If the options enum variant is `NONE`
    will return None.

    If the variant is `CSV` it will validate the csv profiles and return
    a numpy array of the data. Raise an HTTP 422 if no CSV is uploaded.

    If the variant is anything else it will load a bundled profile and return it.

    Sign/unit conventions (unchanged from the original code, documented here
    because they are easy to trip over):
    - Generation profiles (solar PV) are *negated* (multiplied by -1) because
      the simulation treats them as negative load.
    - If the units are kWh per half-hour, values are doubled to convert to
      average kW over the half-hour interval.

    Args:
        options: A profile option enum
        csv_file (Optional[UploadFile]): An optional csv file. Only used if options is set to CSV
        units (ProfileUnits): kW or kWh

    Returns:
        Optional[np.ndarray]: A 2D numpy array with 48 rows (30 min intervals). Each column is a profile
    """

    if isinstance(options, MVSolarPVOptions):
        if options == MVSolarPVOptions.CSV:
            try:
                profile = MVSolarProfile(mv_solar_pv_csv=csv_file)
                return (
                    profile.to_array()
                    * -1.0
                    * (2.0 if units == ProfileUnits.KWH else 1.0)
                )
            except ValidationError as e:
                raise RequestValidationError(errors=e.errors())
        elif options == MVSolarPVOptions.NONE:
            return None
        else:
            return csv_to_array(MV_SOLAR_PROFILES[options]) * -1

    elif isinstance(options, MVFCSOptions):

        if options == MVFCSOptions.CSV:
            try:
                profile = MVFCSProfile(mv_fcs_charger_csv=csv_file)
                return profile.to_array() * (2.0 if units == ProfileUnits.KWH else 1.0)
            except ValidationError as e:
                raise RequestValidationError(errors=e.errors())
        elif options == MVFCSOptions.NONE:
            return None
        else:
            return csv_to_array(MV_FCS_PROFILES[options])

    elif isinstance(options, LVSmartMeterOptions):

        if options == LVSmartMeterOptions.CSV:
            try:
                profile = LVSmartMeterProfile(lv_smart_meter_csv=csv_file)
                return profile.to_array() * (2.0 if units == ProfileUnits.KWH else 1.0)
            except ValidationError as e:
                raise RequestValidationError(errors=e.errors())
        else:
            return csv_to_array(LV_SMART_METER_PROFILES[options])

    elif isinstance(options, LVElectricVehicleOptions):

        if options == LVElectricVehicleOptions.CSV:
            try:
                profile = LVEVProfile(lv_ev_csv=csv_file)
                return profile.to_array() * (2.0 if units == ProfileUnits.KWH else 1.0)
            except ValidationError as e:
                raise RequestValidationError(errors=e.errors())
        elif options == LVElectricVehicleOptions.NONE:
            return None
        else:
            return csv_to_array(LV_EV_PROFILES[options])

    elif isinstance(options, LVPVOptions):

        if options == LVPVOptions.CSV:
            try:
                profile = LVPVProfile(lv_pv_csv=csv_file)
                return (
                    profile.to_array()
                    * -1
                    * (2.0 if units == ProfileUnits.KWH else 1.0)
                )
            except ValidationError as e:
                raise RequestValidationError(errors=e.errors())
        elif options == LVPVOptions.NONE:
            return None
        else:
            return csv_to_array(LV_PV_PROFILES[options]) * -1

    elif isinstance(options, LVHPOptions):

        if options == LVHPOptions.CSV:
            try:
                profile = LVHPProfile(lv_hp_csv=csv_file)
                return profile.to_array() * (2.0 if units == ProfileUnits.KWH else 1.0)
            except ValidationError as e:
                raise RequestValidationError(errors=e.errors())
        elif options == LVHPOptions.NONE:
            return None
        else:
            return csv_to_array(LV_HP_PROFILES[options])

    raise HTTPException(status_code=422, detail="Option not implemented")
