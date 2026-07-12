"""azureOptsXmpls.py
A file containing a list of example dict that could be sent by a user to
build a network and the run a simulation.

"""
from copy import deepcopy

# Dict values of None not yet implemented or simple possibility
run_dict0 = {
    # First: how to construct the MV-LV networks
    "network_data": {
        "n_id": 1060,  # MV-LV circuit ID, at the moment either 1060 or 1061
        "xfmr_scale": None,  # Scale all transformers (eg 1.5 for 50% bigger)
        "oltc_setpoint": None,  # Change the set point (in % pu) of the oltc
        "oltc_bandwidth": None,  # Change the bandwidth (in % pu) of the oltc
        "lv_sel": "lv_list",  # method of building the MV/LV circuit
        "n_lv": 5,  # number of LV circuits (integer >=1 ) [lv_sel]
        "lv_ilist": [
            0,
            10,
            30,
        ],  # select the ith row of the LV ckts [lv_sel]
        "lv_list": [
            "1101",
            "1141",
            "1164",
        ],  # exact lv network ids [lv_sel]
        # 'near_sub', 'near_edge', 'mixed' added below [lv_sel]
    },
    # For random number generation, either seed (with int) or not (None)
    "rand_seed": 0,  # None or int
    # Penetration numbers (in %)
    "rs_pen": 85,
    "slr_pen": 20,  # used with dgd.slr 'slr_pen' options
    "ev_pen": 30,
    "hps_pen": 40,
    # Solar distribution choices - see self.rng for options.
    "solar_dist": "uniform",
    "solar_dist_params": [
        1.5,
        3.5,
    ],  # [low, high] for uniform
    # EV distribution choices - as with solar, see self.rng
    "dytm_dist": "uniform",
    "dytm_dist_params": [0.1, 0.2],
    # Next: allocating loads and generators. See help(turingNet.set_ldsi)
    # for options; if any of these are set to None, then they will not
    # be allocated.
    "dmnd_gen_data": {
        "rs": {
            "lv": "lv",
            "mv": "rs_pen",
        },
        "ic": {
            "lv": None,
            "mv": "not_rs",
        },
        "ovnt": {
            "lv": "ev_pen",
            "mv": "rs",
        },
        "dytm": {
            "lv": None,
            "mv": "ic",
        },
        "slr": {
            "lv": "slr_pen",
            "mv": "rs",
        },
        "dgs": {
            "lv": None,
            "mv": ["1106", "1142"],
        },  # list or None
        "fcs": {
            "lv": None,
            "mv": ["1107", "1143"],
        },  # list or None
        "hps": {
            "lv": "hps_pen",
            "mv": "mv",
        },
    },
    # These are either None or a numpy array with shape (48Xm)
    "simulation_data": {
        "mv_solar_profile_array": None,
        "mv_ev_profile_array": None,
        "smart_meter_profile_array": None,
        "lv_ev_profile_array": None,
        "lv_pv_profile_array": None,
        "lv_hp_profile_array": None
        # "sim_type": None,  # type of simulation, e.g., da-ahead v2g, etc
    },
    # Various plotting options to return to the user etc.
    "plot_options": {  # Using:
        "lv_voltages": ["1101", "1105"],  # n only 2 numbers allowed.
        "lv_comparison": True,  # y
        # use [k for k,v in self.p.items() if v.ndim==2] to see
        # what can be used with profile_sel
        "profile_sel": ["hp_love_Jan"],  # No
    },
}

# Add the hard-coded lv options
lv_example_options_all = {
    1060: {
        "near_sub": [
            "1101",
            "1137",
            "1110",
            "1116",
            "1117",
        ],
        "near_edge": [
            "1103",
            "1109",
            "1166",
            "1145",
            "1131",
        ],
        "mixed": [
            "1108",
            "1109",
            "1151",
            "1158",
            "1175",
        ],
    },
    1061: {
        "near_sub": [
            "1102",
            "1154",
            "1262",
            "1206",
            "1202",
        ],
        "near_edge": [
            "1321",
            "1254",
            "1387",
            "1194",
            "1109",
        ],
        "mixed": [
            "1101",
            "1450",
            "1152",
            "1200",
            "1122",
        ],
    },
}
run_dict0["network_data"].update(
    lv_example_options_all[run_dict0["network_data"]["n_id"]]
)


# ------------- Specific dicts used for creating results.
# rd_xmpl - used to create the results for
rd_xmpl = deepcopy(run_dict0)
lv_list = [
    "1145",
    "1101",
]
rd_xmpl.update(
    {
        "slr_pen": 0,
        "hps_pen": 0,
        "ev_pen": 0,
    }
)  # without
# rd_xmpl.update({'slr_pen':0,'hps_pen':33,'ev_pen':33,}) # with
# rd_xmpl["simulation_data"]["ts_profiles"]["n"] = 48
rd_xmpl["network_data"]["lv_list"] = lv_list

# Choose the network mods - no FCS or DGs
rd_xmpl["dmnd_gen_data"]["dgs"]["mv"] = None
rd_xmpl["dmnd_gen_data"]["fcs"]["mv"] = None

# Network plotting
rd_xmpl["plot_options"]["mv_highlevel"] = False
rd_xmpl["plot_options"]["mv_highlevel_clean"] = False

# Solution plotting
rd_xmpl["plot_options"]["lv_voltages"] = [
    False,
    lv_list,
]
rd_xmpl["plot_options"]["mv_voltage_ts"] = False
rd_xmpl["plot_options"]["profile_sel"] = [
    False,
    "ev_encc",
]
