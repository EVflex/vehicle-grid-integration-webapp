# =====
# SCRIPT AUTOMATICALLY GENERATED!
# =====
#
# This means it is liable to being overwritten, so it is suggested NOT
# to change this script, instead make a copy and work from there.
#
# Code for generating these in ./misc/copy-mtd-funcs-raw.py.
#
# =====

import glob
import os, sys, pickle, timeit, copy, time
import numpy as np
from numpy.random import default_rng
from numpy.linalg import norm
from matplotlib.collections import LineCollection, PatchCollection
from matplotlib.patches import Polygon
from matplotlib import rcParams
import matplotlib.cm as cm
from scipy import sparse
from os.path import join
from itertools import chain
import matplotlib.cm as mplcm
from copy import deepcopy
import scipy.sparse.linalg as spla
import matplotlib.pyplot as plt
from pprint import pprint
from collections import OrderedDict as odict

from .funcsMath_turing import (
    aMulBsp,
    tp2ar,
    vecSlc,
    pf2kq,
    vmM,
    mvM,
    schurSolve,
    calcDp1rSqrt,
    rerr,
    sparseInvUpdate,
    dp1rMv,
    calcVar,
    magicSlice,
    sparseBlkDiag,
    tp2arL,
)
from .funcsDss_turing import dssIfc, updateFlagState, pdIdxCmp, getVset, phs2seq
from .funcsPython_turing import (
    fPrmsInit,
    whocalledme,
    saveFigFunc,
    sff,
    struct,
    mtList,
    mtDict,
    cleanFolder,
    structDict,
    fn_ntwx,
    fn_root,
    o2o,
    rngSeed,
    sff_legacy,
    cmsq,
)
import dss

from importlib import reload

d = dssIfc(dss.DSS)
# Preamble END ---


class dNet:
    """Python-OpenDSS class with networks built-in."""

    fdrs = {
        5: "13bus",
        6: "34bus",
        7: "37bus",
        8: "123bus",
        9: "8500node",
        14: "usLv",
        17: "epri5",
        18: "epri7",
        19: "epriJ1",
        20: "epriK1",
        21: "epriM1",
        22: "epri24",
        23: "4busYy",
        24: "epriK1cvr",
        25: "epri24cvr",
        26: "123busCvr",
        27: "33bus",
        30: "eulv",
        31: "4busLv2lv",
        32: "4busLv2fdr",
        33: "33bus-eulv",
        34: "33bus-10lv",
        35: "33bus-33lv",
        36: "33bus-10lv_p",
        37: "33bus-33lv_p",
        # 38:'HV_UG_full_cut',
        38: "HV_OHa_full_cut",
        39: "HV_UG_full_one",
        # 40:'turing_working',
        40: "HV_UG-OHa_full_small",
        50: "HV_UG",
        51: "HV_UG-OHa",
        52: "HV_UG-OHb",
        53: "HV_OHa",
        54: "HV_OHb",
        55: "HV_OH-UGa",
        56: "HV_OH-UGb",
        60: "HV_UG_full",
        61: "HV_UG-OHa_full",
        62: "HV_UG-OHb_full",
        63: "HV_OHa_full",
        64: "HV_OHb_full",
        65: "HV_OH-UGa_full",
        66: "HV_OH-UGb_full",
        70: "HV_UG_mod",
        71: "HV_UG-OHa_mod",
        72: "HV_UG-OHb_mod",
        73: "HV_OHa_mod",
        74: "HV_OHb_mod",
        75: "HV_OH-UGa_mod",
        76: "HV_OH-UGb_mod",
        80: "HV_UG_full_lo",
        81: "HV_UG-OHa_full_lo",
        82: "HV_UG-OHb_full_lo",
        83: "HV_OHa_full_lo",
        84: "HV_OHb_full_lo",
        85: "HV_OH-UGa_full_lo",
        86: "HV_OH-UGb_full_lo",
        90: "HV_UG_full_hi",
        91: "HV_UG-OHa_full_hi",
        92: "HV_UG-OHb_full_hi",
        93: "HV_OHa_full_hi",
        94: "HV_OHb_full_hi",
        95: "HV_OH-UGa_full_hi",
        96: "HV_OH-UGb_full_hi",
        126: "n7f1",
        127: "n1cvr",
        128: "n1_33bus_ld31",
        "101-125": "Manc. LVNS, as-is",
        "201-225": "Manc. LVNS, pruned version",
        "226-250": "Manc. LVNS, pruned + UKGDS edits",
        "251-275": "Manc. LVNS, pruned + UKGDS, xfmr Z modded",
        "276-300": "Manc. LVNS, pruned + UKGDS fdr one, xfmr Z modded",
        "301-330": "Leuven LV networks",
        1000: "_network_mod",
        1060: "HV_UG_full_turing",
        1061: "HV_UG-OHa_full_turing",
        # 1062:'HV_UG-OHb_full',
        # 1063:'HV_OHa_full',
        # 1064:'HV_OHb_full',
        # 1065:'HV_OH-UGa_full',
        # 1066:'HV_OH-UGb_full',
    }
    fdrs_inv = {v: k for k, v in fdrs.items()}

    # 'HV_UG-OHa_full_small':str(fdrs_inv['HV_UG-OHa_full_small']),
    dn2frids = copy.copy(fdrs_inv)
    dn2frids.update(
        {
            "ukgds-master-dss": "50-56 incl.",
        }
    )

    fdrsLoc = {
        5: join("13Bus_copy\\IEEE13Nodeckt_z"),
        6: join("34Bus_copy", "ieee34Mod1_z"),
        7: join("37Bus_copy", "ieee37_z"),
        8: join("123Bus_copy", "IEEE123Master_z"),
        9: join("8500-Node_copy", "Master-unbal_z"),
        14: join("usLv", "master_z"),
        17: join("ckt5", "Master_ckt5_z"),
        18: join("ckt7", "Master_ckt7_z"),
        19: join("j1", "Master_noPV_z"),
        20: join("k1", "Master_NoPV_z"),
        21: join("m1", "Master_NoPV_z"),
        22: join("ckt24", "master_ckt24_z"),
        23: join("4Bus-YY-Bal", "4Bus-YY-Bal_z"),
        24: join("k1", "Master_NoPV_z_cvr"),
        25: join("ckt24", "master_ckt24_z_cvr"),
        26: join("123Bus_copy", "IEEE123Master_cvr"),
        27: join("33bus", "ieee33master"),
        30: join("LVTestCase_copy", "master_z"),
        31: join("4busLv2lv", "4busLv2lv"),
        32: join("4busLv2fdr", "4busLv2fdr"),
        33: join("33bus-eulv", "ieee33-eulv-master"),
        34: join("33bus-33lv", "ieee33-10lv-master"),
        35: join("33bus-33lv", "ieee33-33lv-master"),
        36: join("33bus-33lv", "ieee33-10lv-master_pruned"),
        37: join("33bus-33lv", "ieee33-33lv-master_pruned"),
        # 38:join('HV_UG_full_cut','master_full_cut'),
        38: join("HV_OHa_full_cut", "master_full_cut"),
        39: join("HV_UG_full_one", "master_full_one"),
        40: join("HV_UG-OHa_full_small", "master_mvlv_small"),
        50: join("HV_UG", "master"),
        51: join("HV_UG-OHa", "master"),
        52: join("HV_UG-OHb", "master"),
        53: join("HV_OHa", "master"),
        54: join("HV_OHb", "master"),
        55: join("HV_OH-UGa", "master"),
        56: join("HV_OH-UGb", "master"),
        60: join("HV_UG_full", "master_full"),
        61: join("HV_UG-OHa_full", "master_full"),
        62: join("HV_UG-OHb_full", "master_full"),
        63: join("HV_OHa_full", "master_full"),
        64: join("HV_OHb_full", "master_full"),
        65: join("HV_OH-UGa_full", "master_full"),
        66: join("HV_OH-UGb_full", "master_full"),
        70: join("HV_UG", "master"),
        71: join("HV_UG-OHa", "master"),
        72: join("HV_UG-OHb", "master"),
        73: join("HV_OHa", "master"),
        74: join("HV_OHb", "master"),
        75: join("HV_OH-UGa", "master"),
        76: join("HV_OH-UGb", "master"),
        80: join("HV_UG_full", "master_full_lo"),
        81: join("HV_UG-OHa_full", "master_full_lo"),
        82: join("HV_UG-OHb_full", "master_full_lo"),
        83: join("HV_OHa_full", "master_full_lo"),
        84: join("HV_OHb_full", "master_full_lo"),
        85: join("HV_OH-UGa_full", "master_full_lo"),
        86: join("HV_OH-UGb_full", "master_full_lo"),
        90: join("HV_UG_full", "master_full_hi"),
        91: join("HV_UG-OHa_full", "master_full_hi"),
        92: join("HV_UG-OHb_full", "master_full_hi"),
        93: join("HV_OHa_full", "master_full_hi"),
        94: join("HV_OHb_full", "master_full_hi"),
        95: join("HV_OH-UGa_full", "master_full_hi"),
        96: join("HV_OH-UGb_full", "master_full_hi"),
        126: join("network_7", "masterNetwork7feeder1"),
        127: join("network_27", "masterNetwork1"),
        128: join("network_28", "masterNetwork1"),
        1000: join("_network_mod", "master_mvlv"),
        1060: join("HV_UG_full", "master_mvlv"),
        1061: join("HV_UG-OHa_full", "master_mvlv"),
        # 1062:join('HV_UG-OHb_full','master_full'),
        # 1063:join('HV_OHa_full','master_full'),
        # 1064:join('HV_OHb_full','master_full'),
        # 1065:join('HV_OH-UGa_full','master_full'),
        # 1066:join('HV_OH-UGb_full','master_full'),
    }

    # Initial constraint numbers
    cns = structDict(
        {
            "vMv": structDict({"U": 1.05, "L": 0.95}),
            "vLv": structDict({"U": 1.05, "L": 0.92}),
            "Dv": structDict({"U": 0.06, "L": -np.inf}),
            "Ixfm": structDict({"U": 1.50, "L": -np.inf}),
            "Vub": structDict({"U": 0.02, "L": -np.inf}),
        }
    )
    cns.N = len(cns.kw)

    # Data for the saved caches
    caches = {
        "Ylli": {
            "name": "Ylli",
            "dn_": "YlliCache",
            "fn_": "Ylli_",
            "res_": {"Ylli", "capTap"},
        },
        # 'Ybus':{
        # 'name':'Ybus',
        # 'dn_':'YbusCache',
        # 'fn_':'Ybus_',
        # 'res_':{'Ybus','Yprm','YbusState','YbusCapTap'}
        # },
    }

    # capTaps for testing funcs
    capTapTests = {
        "13bus": [[(0,), (1,)], [9, 9, 9]],
        "34bus": [[(0,)], [6, 1, 2, 1, 1, 1]],
        "epri7": [[(0,), (0,)], []],
        "epriK1": [[(0,)], [1]],
        "n1_p": [[], []],  # 201
    }

    # For basic solution testing:
    slnVals = {
        "stateIn": {},
        "VsrcMeas": np.nan,
        "Vc": np.nan,
        "vc": np.nan,
        "V": np.nan,
        "v": np.nan,
        "stateOut": {},
        "TP": np.nan,
        "TL": np.nan,
        "Cnvg": np.nan,
    }

    _d = d

    # Number of feeders per LV circuit - e.g. ckt 1 has 4x feeders.
    # From miscScripts\explore_manc_ntwx.
    fdrNos = [
        np.nan,
        4,
        5,
        6,
        6,
        8,
        2,
        7,
        2,
        6,
        6,
        5,
        3,
        4,
        6,
        7,
        4,
        7,
        9,
        5,
        5,
        5,
        6,
        5,
        2,
        3,
    ]

    # Some plotting data - fPrm_ as figure parameters
    fPrm_ = {
        "cmap": None,
        "legLoc": None,  # e.g. 'NorthEast'. Not used...?
        "tFs": 10,  # title font size
        "ttlOn": False,
        "cms": {
            "v": cm.RdBu,
            "p": cm.GnBu,
            "q": cm.PiYG,
            "n": cm.Blues,
        },
        "pms": 50,
    }

    # 3 phase plotting scale of hexagons
    sfDict3ph = {
        "13bus": 6,
        "123bus": 60,
        "123busCvr": 60,
        "epriK1cvr": 40,
        "34bus": 80,
        "n1": 4,
        "eulv": 2,
        "epri5": 90,
        "epri7": 50,
        "n10": 3,
        "n4": 3,
        "n27": 4,
        "33bus": 12,
    }

    def __init__(
        self,
        frId=30,
        yBdInit=True,
        prmIn={},
        mod_dir=os.path.join(os.getcwd(), "_network_mod"),
        **kwargs,
    ):
        """Initialise with kwargs.

        =====
        Inputs
        =====
        frId    - the feeder ID. Use self.getCktFn(1) to get a list of options
        yBdInit - if true create derived matrices
        prmIn: a dict of nominal parameter updates:
                - nomLdLm: 0.6, load mult at the initial solution
                - pCvr: 0, p cvr coefficient at initial solution
                - qCvr: 0, q cvr coefficient at initial solution
                - tolStr: the chosen opendss solution tolerance
                - yset: 'Ybus' or 'both', the latter also getting self.Yprm
        mod_dir - directory where modified OpenDSS files are stored. Used only for frID 1000.

        =====
        kwargs
        =====
        sd: save directory for figures
        tests: list of named tests,
                - 'ybus' for checking ybus matches opendss explicitly
                - 'ykvbase' for checking the voltage bases

        """

        self.mod_dir = mod_dir

        self.prm = {
            "nomLdLm": 0.6,
            "pCvr": 0,
            "qCvr": 0,
            "tolStr": "1e-6",
            # 'tolStr':'1e-10',
            "yset": "both",
        }
        self.prm.update(prmIn)

        # load in tests list
        self.tests = kwargs.get("tests", ["ybus"])

        # figure parameters
        self.fPrm = fPrmsInit(kwargs.get("sd", __file__))

        if "lm" in kwargs.keys():
            raise Exception("'lm' not supported by dNet! Use prmIn.")

        # get ckt info
        self.frId = frId
        self.setCktFn()

        # Get initial opendss state
        print("Initialise OpenDSS, Circuit, then Get Circuit Parameters.")
        self.initialiseOpenDss()
        self.initialiseDssCkt()

        self.state0 = d.getNtwkState()
        self.getIdxPhs()

        # Get parameters of the circuit
        state_ = self.state0.copy()
        state_["CtrlMode"] = -1
        d.setNtwkState(state_)

        self.nV = d.DSSCircuit.NumNodes - 3  # following previous conventions

        self.YZ = d.DSSCircuit.YNodeOrder
        self.YZidxs = {bus: i for i, bus in enumerate(self.YZ)}
        self.YZsrc = self.YZ[:3]
        self.YZv = self.YZ[3:]  # following previous conventions
        self.YZvIdxs = {bus: i for i, bus in enumerate(self.YZv)}
        self.getSourceBus()

        # Get derived quantities
        self._V = np.abs(tp2ar(d.DSSCircuit.YNodeVarray))
        self.vKvbase = d.get_Yvbase(self.YZ, test=("ykvbase" in self.tests))[3:]
        dNet.getVolLevels(self)

        # NB slightly different from prev conv.
        self.getCounts()

        self.YZsy = vecSlc(self.YZv, self.pyIdx)
        self.YZsd = vecSlc(self.YZv, self.pdIdx)
        self.YZs = vecSlc(self.YZv, self.sIdx)

        self.qyIdx = self.pyIdx + len(self.YZv)
        self.syIdx = np.r_[self.pyIdx, self.qyIdx]
        self.qdIdx = self.pdIdx + len(self.YZv)
        self.sdIdx = np.r_[self.pdIdx, self.qdIdx]

        self.pdIdxCmp, self.pdIdxUnq = pdIdxCmp(self.YZv, self.pdIdx)

        # Initiliase self.sln
        self.getSln(None)

        # NB isn't much faster than the previous buildHmat code.
        self.buildSpHmat()

        # Get the admittance matrix
        self.getYset(
            yset=self.prm["yset"], state=self.state0, testYbus=("ybus" in self.tests)
        )

        # Get derived matrices
        if yBdInit:
            self.getUbMats(test=False)

            self.getYprmBd()
            self.getYprmBd(prmType="YprmV", dssType=d.TRN, psConv=True)

            self.xfmRatings = d.getXfmrIlims(d.getRegXfms())

            self.nIprm = self.YprmBd.shape[0]
            self.Vnl = -spla.spsolve(self.Ybus[3:, 3:], self.Ybus[3:, :3]).dot(
                d.getVsrc()
            )

    def getCounts(self):
        """Get the counts and indexes of LOADS.

        Indexes are with respect to YZv, not YZ.

        No generators are assumed for now.
        """
        self.updateLdsCount()
        self.updateGenCount()

        # WARNING: assumes that Loads and Generators are at the same buses.
        self.nPy = len(self.pyIdx)
        self.nPd = len(self.pdIdx)
        self.nP = self.nPy + self.nPd
        self.nS = self.nP * 2
        self.nT = len(self.state0["capTap"][1])
        self.nC = len(self.cap2list(self.state0["capTap"][0]))

    def updateLdsCount(self):
        # Note that these are all generally different from n.LDS.Count.
        sIdx, self.LDSidx, self.LDS_ = d.getPwrIdxs(
            d.LDS,
            self.YZv,
        )
        self.pyIdx, self.pdIdx = sIdx
        self.sIdx = np.concatenate(sIdx)
        self.nPyLds = len(self.LDS_.Y.idx)
        self.nPdLds = len(self.LDS_.D.idx)

    def updateGenCount(self):
        _, self.GENidx, self.GEN_ = d.getPwrIdxs(
            d.GEN,
            self.YZv,
        )
        # self.pyIdx, self.pdIdx = sIdx
        self.nPyGen = len(self.GEN_.Y.idx)
        self.nPdGen = len(self.GEN_.D.idx)

    @staticmethod
    def cap2list(capList):
        return list(chain(*capList))

    def clearCache(
        self,
        fldr,
    ):
        """Clear a cache.

        fldr opts are from help(self.getCacheFn).
        """
        dn = self.getCacheFn(fldr, getDn=True)
        cleanFolder(dn)

    def getYset(self, yset="both", **kwargs):
        """Get the admittance matrix at the given state.

        Inputs
        ---
        yset: either 'Ybus', 'Yprm', 'both' for Ybus or Yprm matrices (or both)

        kwargs
        ---
        fixCtrl: to fix the control or not
        state: A state to get the admittance matrix at. Note that 'fixCtrl'
               changes the state then returns it.
        capTap: An alternative to setting state.
        testYbus: If true, load the admittance matrix from opendss & compare

        Returns
        ---
        Sets the following attributes (through calcYset or updateYset)
        - yset
        - yset+'State'
        - yset+'CapTap'
        - yset+'Kwargs'

        """
        # Unpack kwargs
        capTap = kwargs.get("capTap", None)
        state = kwargs.get("state", deepcopy(self.state0))
        fixCtrl = kwargs.get("fixCtrl", True)

        # in case we want to rerun later
        if yset in ["both", "Ybus"]:
            self.YbusKwargs = kwargs
        if yset in ["both", "Yprm"]:
            self.YprmKwargs = kwargs

        if not capTap is None:
            if "state" in kwargs.keys():
                raise Exception("Specify state XOR capTap, not both.")

            state["capTap"] = capTap
            state["CtrlMode"] = -1
        else:
            # Get the state
            capTap = state["capTap"]

        CtrlMode_ = state["CtrlMode"]

        if fixCtrl:
            # Force turn-off controls
            state["CtrlMode"] = -1

        sKeys = self.__dict__.keys()

        # Update without fully rebuilding where possible.
        if (yset == "both" and "Ybus" in sKeys and "Yprm" in sKeys) or yset in sKeys:
            capTap_ = getattr(self, "YbusCapTap").copy()
            self.updateYset(
                capTap_,
                capTap,
                yset,
            )
        else:
            self.calcYset(
                state,
                yset,
            )

        # Set the control mode back to initial in case it is used elsewhere
        state["CtrlMode"] = CtrlMode_

        if kwargs.get("testYbus", False):
            Ybus2 = d.createYbus(state["capTap"])[0]
            val = spla.norm(self.Ybus - Ybus2) / spla.norm(Ybus2)
            print("YBus Equal:", val < 1e-14)
            print("YBus Equal:", val)
            self.Ybus2 = Ybus2

    def updateYset(
        self,
        capTap_,
        capTap,
        yset="both",
    ):
        """Update Ybus/Yprm to the new capTap position capTap.

        Only updates if capTap_ is different from capTap.

        Inputs
        ---
        capTap_: passed as first argument to getOldNewYmats
        capTap: passed as second argument to getOldNewYmats
        yset: the yset to update ('Ybus', 'Yprm', or 'both')

        """

        if capTap != capTap_:
            (YmOld, YmNew), (YpO, YpN) = self.getOldNewYmats(capTap_, capTap)

            if yset in ["Ybus", "both"]:
                self.Ybus = self.Ybus + YmNew - YmOld
                self.Ybus.eliminate_zeros()
                self.YbusState = d.getNtwkState()
                self.YbusCapTap = self.YbusState["capTap"]

            if yset in ["Yprm", "both"]:
                self.Yprm.update(YpN)
                self.YprmState = d.getNtwkState()
                self.YprmCapTap = self.YbusState["capTap"]

        else:
            pass

    def getOldNewYmats(self, capTap_, capTap):
        """Get primitive and admittance matrix perturbations.

        capTap_ is the OLD capTap,
        capTap is the NEW capTap.

        Returns (YmatOld,YmatNew),(YprmsOld,YprmsNew).
        """
        CtrlMode_ = d.setControlMode(-1)

        # Get the OLD capTap Ymats
        YmatCap_ = d.buildYmat(d.CAP, capTap_, self.YZidxs)[:2]
        YmatTap_ = d.buildYmat(d.RGC, capTap_, self.YZidxs)[:2]

        # Get the NEW capTap Ymats
        YmatCap = d.buildYmat(d.CAP, capTap, self.YZidxs)[:2]
        YmatTap = d.buildYmat(d.RGC, capTap, self.YZidxs)[:2]

        YmatOld = YmatCap_[0] + YmatTap_[0]
        YmatNew = YmatCap[0] + YmatTap[0]

        YprmsOld = {**YmatCap_[1], **YmatTap_[1]}
        YprmsNew = {**YmatCap[1], **YmatTap[1]}

        d.setControlMode(CtrlMode_)
        return (YmatOld, YmatNew), (YprmsOld, YprmsNew)

    def calcYset(
        self,
        state,
        yset="Ybus",
    ):
        """A wrapper to pull out Ybus, Yprm, or both.

        If 'both' is called then does a simple error check on the built
        and actual Ybus matrices.

        Inputs
        ---
        state: the state to get the Ybus at
        yset: as in getYset [can be 'both']

        Sets attributes:
        ---
        - yset
        - yset+'State'
        - yset+'CapTap'

        """
        d.setNtwkState(state)

        Res = {}
        if yset in ["Ybus", "both"]:
            Res.update({"Ybus": d.getYmat(None, True)[0]})
            Res.update({"YbusState": d.getNtwkState()})
            Res.update({"YbusCapTap": Res["YbusState"]["capTap"]})
        if yset in ["Yprm", "both"]:
            Ybus2, Yprm = d.buildYmat(
                d.PDE,
                state["capTap"],
                self.YZidxs,
                1,
            )[:2]
            Res.update({"Yprm": Yprm})
            Res.update({"YprmState": d.getNtwkState()})
            Res.update({"YprmCapTap": Res["YbusState"]["capTap"]})

        # Do a quick error check if getting both
        if yset == "both":
            if rerr(Res["Ybus"], Ybus2, p=0) > 1e14:
                print("Warning! Ybus and Ybus2 do not match!")

        self.dictSetAttr(Res)
        return Res

    def dictSetAttr(self, dct):
        """A simple wrapper to set a dictionary of attributes to self."""
        for key, val in dct.items():
            setattr(self, key, val)

    def getIdxPhs(self):
        """Run through Y- and D- LDS+GEN, record each as one-or 3-phase."""
        self.iIdxPhsY = np.zeros(
            len(self.state0["LdsY"]) + len(self.state0["GenY"]), dtype=int
        )
        self.iIdxPhsD = np.zeros(
            len(self.state0["LdsD"]) + len(self.state0["GenD"]), dtype=int
        )

        iY = 0
        iD = 0
        for obj in [d.LDS, d.GEN]:
            i = obj.First
            while i:
                if d.AE.Properties("conn").Val.lower() == "delta":
                    self.iIdxPhsD[iD] = d.ACE.NumPhases
                    iD += 1
                else:
                    self.iIdxPhsY[iY] = d.ACE.NumPhases
                    iY += 1
                i = obj.Next

    def initialiseOpenDss(self):
        """Get the dssobj into self for reference by other objects."""
        self.DSSObj = d.DSSObj

    def initialiseDssCkt(self):
        """Reset OpenDSS and compile the file.

        Remember! This resets gets rid of any changes
        e.g. self.allGenSetup()
        DSSText.Command='Compile ('+self.fn+')'

        Note that this can be quite slow for the big networks.
        """
        d.resetDss()


        cur_dir = os.getcwd()
        # The next line changes the current working directory so we change it back
        d.DSSText.Command = "Compile " + self.fn
        os.chdir(cur_dir)
        d.DSSText.Command = "Set tol=" + self.prm["tolStr"]
        d.SLN.Solve()

        d.DSSText.Command = (
            "Batchedit load..* vminpu=0.02 vmaxpu=50"
            + " model=4 status=variable cvrwatts="
            + str(self.prm["pCvr"])
            + " cvrvars="
            + str(self.prm["qCvr"])
        )

        d.SLN.LoadMult = self.prm["nomLdLm"]
        d.SLN.Solve()

    def buildSpHmat(self):
        """A fast way of building a sparse instantiation of the H-matrix."""
        dataSet = np.array([np.ones(self.nPd), -np.ones(self.nPd)]).T.flatten()
        iSet = np.array([np.arange(self.nPd)] * 2).T.flatten()
        jSet = np.array([self.pdIdx, self.pdIdxCmp]).T.flatten()
        self.Hmat = sparse.coo_matrix(
            (dataSet, (iSet, jSet)), (self.nPd, self.nV)
        ).tocsr()

    def setCktFn(
        self,
    ):
        """Set self.feeder, self.fn by calling getCktFn."""
        self.feeder, self.fn = self.getCktFn()

    def getCktFn(self, printF=False, frId=None):
        """A function to get circuit feederId and fn, or print.

        Use printF to print all options;
        Use frId to return details of other circuits.

        """
        if frId is None:
            frId = self.frId

        if printF:
            pprint(self.fdrs)
        if len(str(frId)) < 3 or len(str(frId)) >= 4:
            if frId in [
                5,
                6,
                7,
                8,
                9,
                14,
                17,
                18,
                19,
                20,
                21,
                22,
                23,
                24,
                25,
                26,
                27,
                31,
                32,
                33,
                34,
                35,
                36,
                37,
            ]:
                ND = join(fn_ntwx, "ieee_tn")
            elif frId in [30, 38, 39, 40]:
                ND = fn_ntwx
            # elif frId in [40]:
            # ND = r"D:\codeD\uk-mvlv-models-mod"
            elif frId in list(range(50, 57)):
                ND = join(fn_ntwx, "ukgds-master-dss")
            elif frId in list(range(60, 67)) + list(range(80, 87)) + list(
                range(90, 97)
            ):
                ND = join(fn_ntwx, "ukgds-master-full")
            elif frId in list(range(70, 77)):
                ND = join(fn_ntwx, "ukgds-master-mod")
            elif frId == 1000:
                ND = self.mod_dir
            elif frId > 1000:
                ND = join(
                    fn_ntwx,
                )

        elif len(str(frId)) == 3 and frId < 301:
            ND, feederId, masterFn = dNet.getLvnsFn(frId)
            self.fdrs[frId] = feederId
            self.fdrsLoc[frId] = masterFn

        elif frId > 300 and frId < 1000:
            ND = join(fn_ntwx, "leuven_models", "scriptData")
            mvIdx = "mv" + str(frId - 300)

            self.fdrs[frId] = mvIdx + "_lvn"  # leuven
            self.fdrsLoc[frId] = join(mvIdx, "master_1ph_" + mvIdx + "_slesNtwk.dss")

            # for the leuven models, copy the master script, then
            # replace the 'cd' dir so that this loads properly.
            fnRaw = join(ND, mvIdx, "master_raw_1ph_" + mvIdx + ".dss")
            with open(fnRaw) as file:
                rawTxt = file.read()
            fnUse = join(ND, self.fdrsLoc[frId])
            with open(fnUse, "w") as file:
                file.write(rawTxt.replace("_dir_name_here_", ND))

        return self.fdrs[frId], join(ND, self.fdrsLoc[frId])

    @staticmethod
    def getLvnsFn(
        frId,
    ):
        """A function for finding filename and ckt info for LVNS circuit types."""
        if frId < 100 or frId > 300:
            raise Exception("frId needs to be between 100 and 300.")

        ND0 = join(fn_ntwx, "manchester_models")

        dnA = "batch_manc_ntwx"
        dnB = "batch_manc_ntwx_mod"

        lvId = ((frId - 1) % 25) + 1
        i0 = frId - lvId
        iLv = str(lvId)

        # NB - as of 21/7/21, these could be tweaked still to get all working
        lvInfo = {  # frid0: [root, feederId end, master name end]
            100: [
                dnA,
                "",
                "",
            ],
            200: [
                dnA,
                "_p",
                "_pruned",
            ],
            225: [
                dnA,
                "",
                "_pruned_ukgds",
            ],
            250: [
                dnB,
                "_p_mod",
                "_mod",
            ],
            275: [dnA, "", "_pruned_one"],
        }

        ND = join(ND0, lvInfo[i0][0])
        feederId = "n" + iLv + lvInfo[i0][1]
        masterFn = join("network_" + iLv, "masterNetwork" + iLv + lvInfo[i0][2])

        return ND, feederId, masterFn

    def calcIprms(self, V=None):
        """Calculate the primitive currents for PDEs.

        Essentially does:
        IprmSet = []
        for yps in self.Yprm:
            IprmSet.append( yps['YprmI'].dot(V[yps['yzIdx']]) )
        IprmSet = np.concatenate(IprmSet)

        The equivalent dssIfc command is getIprm.
        """
        if V is None:
            V = np.r_[self.sln.VsrcMeas, self.sln.Vc]

        IprmSet = self.YprmBd.dot(V)
        return IprmSet

    def getYprmBd(
        self,
        **kwargs,
    ):
        """Get the block-diagonal BD primitive Y to go from V to Iprm.

        -----
        outputs
        -----
        Sets the following attributes:
        - YprmBd
        - YprmNms
        - YprmFlws
        - YprmBdKwargs
        - YprmBdCapTap

        If dssType is passed in, * is replaced with *_d.getObjName(dssType)

        -----
        kwargs
        -----
        prmType - flag is either 'YprmI' (all currents) or 'YprmV'
        dssType - is used to specify a type of element (e.g. d.TRN)
        psConv - flag indicates whether to return only pos seq admittances.
        capTap - the capTap position to get the YprmBd for

        When using psConv:
        - For three-phase transformers, the positive sequence current is found
          for winding 1.
        - For single-phase transformers, the current of winding 1 is used.
        """
        prmType = kwargs.get("prmType", "YprmI")
        dssType = kwargs.get("dssType", None)
        psConv = kwargs.get("psConv", False)
        capTap = kwargs.get("capTap", self.YbusCapTap)

        # First check if the captap positions have changed.
        capTapNm = "YprmBdCapTap"
        if dssType is not None:
            nm = d.getObjName(dssType)
            capTapNm = capTapNm + "_" + nm

        if getattr(self, capTapNm, None) == capTap:
            return

        # Then make sure we have the right Yprm:
        YbusKwargs_ = self.YbusKwargs
        self.getYset(yset="Yprm", fixCtrl=True, capTap=capTap)

        # Get the keys to loop through
        if dssType is None:
            keys = self.Yprm.keys()
        else:
            keys = []
            i = dssType.First
            while i:
                keys.append(d.AE.Name)
                i = dssType.Next
            # also, for ease we ignore transformers with regulators.
            if nm == "TRN":
                regXfm = d.getRegXfms()
                keys = [key for key in keys if key not in regXfm]

        # Loop through and pull out the required info:
        YprmBd_ = []
        yzIdxs = []
        emntNms = []
        flwNms = []
        for eName in keys:
            yp = self.Yprm[eName]
            yzIdxs.append(yp["yzIdx"])
            emntNms.append(eName)
            ypPrm = yp[prmType].copy()

            flwNms.extend(self.getFlwNms(yp, prmType, psConv))
            if not psConv:
                YprmBd_.append(ypPrm)
            else:
                if yp["nPh"] == 1:
                    YprmBd_.append(ypPrm[0].reshape(1, -1))
                elif yp["nPh"] == 3:
                    YprmBd_.append(phs2seq[1].dot(ypPrm[:3]).reshape(1, -1))
                else:
                    raise Exception("Only 1 & 3 phase xfmrs implemented.")

        # Create the YprmBd matrix and shift the voltage indices
        YprmBd = sparseBlkDiag(YprmBd_).tocsr()
        yzIdxs = np.concatenate(yzIdxs)

        idxShuff = sparse.coo_matrix(
            (np.ones(len(yzIdxs)), (np.arange(len(yzIdxs)), yzIdxs)),
            shape=(len(yzIdxs), self.nV + 3),
            dtype=int,
        ).tocsr()

        # List the new attributes to be set:
        newAttrs = {
            "YprmBd": YprmBd.dot(idxShuff),
            "YprmNms": emntNms,
            "YprmFlws": flwNms,
            "YprmBdKwargs": kwargs,
            "YprmBdCapTap": d.getCapTap(),
        }

        if dssType is not None:
            nm = d.getObjName(dssType)
            newAttrs = dict((key + "_" + nm, val) for key, val in newAttrs.items())

        # Update the setattrs as required:
        self.dictSetAttr(newAttrs)

        # Return the Ybus to the state it came in in:
        self.getYset(**YbusKwargs_)

    @staticmethod
    def getFlwNms(yp, prmType="YprmI", psConv=False):
        """Return list of flow names for the yp element.

        Inputs:
        - prmType is either 'YprmI' (default) or 'YprmV'
        - If psConv, then only the 'positive sequence name' is found.
        """
        if not psConv:
            if prmType == "YprmI":
                return [yp["eName"] + "__" + busSel for busSel in yp["iIds"]]
            elif prmType == "YprmV":
                return [yp["eName"] + "__" + busSel for busSel in yp["vIds"]]
        else:
            return [yp["eName"] + "__" + "posSeq"]

    def getYlli(self, capTap, **kwargs):
        """Find Ybus inverse, Ylli.

        If no existing inverse exists, first create the inverse and save.
        If it does exist, get it, and then update according to the taps/caps
        positions, as necessary.

        capTap: if set to None, forces a recalculationg of Ylli using the
                    current Ybus
        -----
        kwargs
        -----
        - force: relcalculates Ylli using state0's capTap
        - forceSave: recalculate Ylli using capTap
        - testYlli: compare to the full ybus.
        """
        force = kwargs.get("force", False)
        forceSave = kwargs.get("forceSave", False)
        testYlli = kwargs.get("testYlli", False)

        C = "Ylli"
        fn = self.getCacheFn(C)
        if capTap is None:
            Ylli_ = spla.inv(self.Ybus[3:, 3:]).toarray()
            capTap_ = self.YbusState["capTap"]
        elif force:
            self.getYset(yset="Ybus", fixCtrl=True, capTap=capTap)
            Ylli_ = spla.inv(self.Ybus[3:, 3:]).toarray()
            capTap_ = self.YbusState["capTap"]
        elif forceSave or (not os.path.exists(fn)):
            print("Building and saving Ylli...")
            Ylli_ = spla.inv(self.Ybus[3:, 3:]).toarray()
            capTap_ = self.YbusState["capTap"]
            dNet.saveCache(fn, {"Ylli": Ylli_, "capTap": capTap_}, cache=self.caches[C])
        elif "Ylli" in self.__dict__.keys():
            Ylli_ = self.Ylli
            capTap_ = self.YlliCapTap
        else:
            YlliRes = dNet.loadCache(fn, cache=self.caches[C])
            Ylli_ = YlliRes["Ylli"]
            capTap_ = YlliRes["capTap"]

        if capTap is None or capTap_ == capTap or force:
            self.Ylli = Ylli_
        else:
            self.Ylli = self.updateYlli(Ylli_, capTap_, capTap)
            capTap_ = capTap

        self.YlliCapTap = capTap_

        if testYlli:
            self.getYset(yset="Ybus", fixCtrl=True, capTap=capTap)
            Ylli_ = spla.inv(self.Ybus[3:, 3:]).toarray()
            val = np.linalg.norm(self.Ylli - Ylli_) / np.linalg.norm(Ylli_)
            print("Ylli Equal:", val < 1e-12)

    def updateYlli(self, Ylli_, capTap_, capTap):
        """Update admittance inverse to the positions of capTap."""

        (YmatOld, YmatNew) = self.getOldNewYmats(capTap_, capTap)[0]
        dYmat = (YmatNew - YmatOld)[3:, 3:]
        dYmat.eliminate_zeros()

        if dYmat.nnz == 0:
            raise Exception("dYmat=0 --> not calculated correctly!")

        return sparseInvUpdate(Ylli_, dYmat)

    @property
    def capTapTest(self):
        if not self.feeder in self.capTapTests.keys():
            raise Exception("Feeder " + self.feeder + " not in capTapTests.")

        return self.capTapTests[self.feeder]

    def test_getYlli(self):
        """A function for testing low-rank updating functions."""
        self.getYlli(capTap=self.state0["capTap"])
        Ylli0 = self.Ylli
        CapTap0 = self.YlliCapTap

        self.getYlli(capTap=self.capTapTest)
        Ylli = self.Ylli
        CapTap_ = self.YlliCapTap

        self.getYlli(capTap=self.capTapTest, force=True)
        YlliF = self.Ylli
        CapTapF = self.YlliCapTap
        rerr(Ylli, YlliF)

        print(CapTap0)
        print(self.capTapTest)
        print(CapTap_)
        print(CapTapF)

    def getCacheFn(self, C, getDn=False, prms={}):
        """Get the fn for cached values of C

        Inputs
        ---
        C: cache type
        getDn: if True, only returns the directory for C
        prms: parameters for modifying fn. Choose LoadMult for Vmlv.

        Options for C (corresponding to self.caches) are:
        - 'Ylli': inverse admittance matrices
        - 'Ybus': admittance matrices [not in use]
        - 'Vmlv': linear model for MLV linear models
        - 'cktInfo': bits and pieces to avoid having to recall OpenDSS

        Use 'getDn' flag to only get the directory of the files.
        """
        dn = os.path.join(fn_root, "lin_models", self.caches[C]["dn_"])
        if not getDn:
            if C in [
                "Ybus",
                "Ylli",
                "cktInfo",
            ]:
                fn = os.path.join(dn, self.caches[C]["fn_"] + self.feeder + ".pkl")
            elif C in ["Vmlv"]:
                lm = prms["LoadMult"]
                fn = os.path.join(
                    dn,
                    self.caches[C]["fn_"]
                    + self.feeder
                    + "_"
                    + f"{lm:.3f}".replace(".", "-")
                    + ".pkl",
                )
        else:
            fn = dn
        return fn

    @staticmethod
    def loadCache(fn, cache=None, vbs=True):
        """Load res from fn and return.

        If cache is set (e.g. as self.cache[C]) then check the keys align
        with the keys that should be loaded. Otherwise does no error checking.

        Use vbs flag to show/not print the data being loaded in.
        """
        with open(fn, "rb") as file:
            res = pickle.load(file)
            if vbs:
                print("Data loaded from\n\t-->" + fn)

        if not res is None:
            if set(res.keys()) != cache["res_"]:
                raise Exception("Data loaded from cache not valid.")
        return res

    @staticmethod
    def saveCache(fn, Res, cache=None, vbs=True):
        """Save Res to fn, with error checking using C (if provided).

        For options for cache, see e.g. help(self.getCacheFn) or self.caches.
        """
        if not cache is None:
            if cache["res_"] != set(Res.keys()):
                raise Exception("Data saving to cache not valid.")

        with open(fn, "wb") as file:
            pickle.dump(Res, file)
            if vbs:
                print("Data saved to\n\t-->" + fn)

    def getUbMats(self, test=False):
        """Get voltage unbalance matrices and indexes.

        Gets:
        - seqBus, the order of the three phase buses
        - seqBusPhs, the same but given unique names as to ps,ns,zs
        - Vc2Vcub, the mapping complex voltages to sequence voltages
        - nVseq, total number of sequence voltages
        - nVps, the total number of positive sequence voltages
        """
        (self.seqBus, self.seqBusPhs, self.vKvbaseSeq), self.Vc2Vcub = d.getVc2Vcub(
            self.YZidxs
        )
        self.nVseq = len(self.seqBusPhs)
        self.nVps = len(self.seqBus)
        if test:
            self.testVc2Vcub()

    def testVc2Vcub(self):
        """Test the voltage unbalance model against OpenDSS metrics."""
        self.getSln(self.state0)
        Vcub = self.Vc2Vcub.dot(np.r_[self.sln.VsrcMeas, self.sln.Vc])
        VcubDss = d.getVseq(seqBus=self.seqBus)
        print("Vcub error: {:.6g}".format(norm(VcubDss - Vcub) / norm(VcubDss)))

    # Index shuffling ======
    def xydt2x(self, YY, DD, TT, dim=1):
        """Convery YY, DD, YY triple to a single object XX.

        Recall that X is of the form as given in state2x.

        The opposite of this is x2xydt.
        """
        if YY.ndim == 1:
            if YY.shape[0] == self.nV * 2:
                YY = YY[self.syIdx]
                DD = DD[self.sdIdx]

            if YY.shape[0] == self.nPy * 2:
                XX = np.r_[
                    YY[: self.nPy], DD[: self.nPd], YY[self.nPy :], DD[self.nPd :], TT
                ]
        if YY.ndim == 2:
            if dim == 0:
                XX = np.r_[
                    YY[: self.nPy], DD[: self.nPd], YY[self.nPy :], DD[self.nPd :], TT
                ]
            elif dim == 1:
                XX = np.c_[
                    YY[:, : self.nPy],
                    DD[:, : self.nPd],
                    YY[:, self.nPy :],
                    DD[:, self.nPd :],
                    TT,
                ]
        return XX

    def x2xydt(
        self,
        XX,
        xs=None,
        nPydt=None,
    ):
        """Convert XX to individual control elements in wye, delta, tap ctrls.

        The opposite of this is xydt2x.
        - Pass in xs (int) if splitting a matrix.
        - Pass in nPdyt [nPy,nPd,nT] for other dimensions if required
        """
        # Get the indices, if not the nominal ones for this circuit
        if nPydt is None:
            nPy = self.nPy
            nPd = self.nPd
            nT = self.nT
        else:
            nPy, nPd, nT = nPydt

        nP = nPy + nPd
        nS = nP * 2
        nCtrl = nS + nT

        # If only a vector is passed, split on the first axis:
        if xs is None and XX.ndim == 1:
            xs = 0

        # Check if an xs has been passed, if required:
        if xs is None:
            raise Exception("Please pass in an axis to iterate over!")

        # Check the dimensions of XX are as expected:
        if XX.shape[xs] != (nCtrl):
            raise Exception("XX is not of conformal dimensions!")

        # Finally pull out the matrices as requested:
        if xs == 0:
            YY = np.r_[XX[:nPy], XX[nP : nP + nPy]]
            DD = np.r_[XX[nPy:nP], XX[nP + nPy : nS]]
            TT = XX[nS:]
        if xs == 1:
            YY = np.c_[XX[:, :nPy], XX[:, nP : nP + nPy]]
            DD = np.c_[XX[:, nPy:nP], XX[:, nP + nPy : nS]]
            TT = XX[:, nS:]

        return YY, DD, TT

    def x2xc(self, X, conj=False):
        """Convert real X to complex X, plus tap controls."""
        if conj:
            val = np.r_[
                X[: self.nP] - 1j * X[self.nP : self.nS], X[self.nS : self.nS + self.nT]
            ]
        else:
            val = np.r_[
                X[: self.nP] + 1j * X[self.nP : self.nS], X[self.nS : self.nS + self.nT]
            ]
        return val

    def state2xc(
        self,
        state,
        conj=False,
    ):
        """A simple wrapper for self.x2xc(self.state2x(state))."""
        return self.x2xc(self.state2x(state), conj)

    def getXc(self):
        """Alias of self.x2xc(self.getX())

        Also equivalent to self.x2xc( self.state2x( d.getNtwkState() ) )
        """
        return self.x2xc(self.getX())

    @staticmethod
    def getVolLevels(obj):
        obj.lvIdx = np.where(obj.vKvbase < 1e3)[0]
        obj.nVlv = len(obj.lvIdx)
        obj.mvIdx = np.where(obj.vKvbase > 1e3)[0]
        obj.nVmv = len(obj.mvIdx)

    def state2x(
        self,
        state,
    ):
        """Process a dssIfc state into a control X.

        Recall: X is of the form
                            X = [Py Pd Qy Qd T]

        The injection indexes are given by [possibly???]
        - Py / Qy: self.pyIdx
        - Pd / Qd: self.pdIdx (corresponding to the first phase)
        - T:  the Xfms in d.getRegXfms()

        To go from state (indexes in d.LDS, d.GEN), a list of powers is
        created from state LDS, GEN in that order, for both Y and D loads.

        The indexes for things in X are given by syIdx,sdIdx for powers.

        """
        # Create a vector of power injections from loads and gens:
        kLds = -state["LoadMult"] * 1e3
        kGen = 1e3
        injY = np.r_[kLds * np.array(state["LdsY"]), kGen * np.array(state["GenY"])]
        injD = np.r_[kLds * np.array(state["LdsD"]), kGen * np.array(state["GenD"])]

        # Put these into a longer list that specifies injections per-phase:
        nZy = self.nPyLds + self.nPyGen
        nZd = self.nPdLds + self.nPdGen

        xYlist = np.zeros(nZy, dtype=complex)
        xDlist = np.zeros(nZd, dtype=complex)
        i = 0
        for nPhs, inj in zip(self.iIdxPhsY, injY):
            xYlist[i : i + nPhs] = inj / nPhs
            i += nPhs

        i = 0
        for nPhs, inj in zip(self.iIdxPhsD, injD):
            xDlist[i : i + nPhs] = inj / nPhs
            i += nPhs

        idxY = np.r_[self.LDS_.Y.idx, self.GEN_.Y.idx]
        idxD = np.r_[self.LDS_.D.idx, self.GEN_.D.idx]

        # A little hack to add any powers together at the same node:
        xY0 = sparse.coo_matrix((xYlist, (idxY, np.zeros(nZy))), [self.nV, 1])
        xD0 = sparse.coo_matrix((xDlist, (idxD, np.zeros(nZd))), [self.nV, 1])

        Xy = xY0.toarray().ravel()
        Xy = np.r_[Xy.real, Xy.imag]
        Xd = xD0.toarray().ravel()
        Xd = np.r_[Xd.real, Xd.imag]

        # Taps are a bit messier:
        if not hasattr(self, "mdl"):
            # Xt = np.nan*np.zeros(self.nT) # WARNING < not sure why nans here?
            Xt = np.zeros(self.nT)
        else:
            Xt = np.array(state["capTap"][1]) - self.mdl.linTap

        return self.xydt2x(Xy, Xd, Xt)

    def getX(self):
        """Alias of self.state2x( d.getNtwkState() )"""
        return self.state2x(d.getNtwkState())

    def getSln(self, state, uRcrd=False, uRcrdIdx=None):
        """Find a solution at state, then save as sln struct.

        Based on "TL,PL,TC,CL,V,I,Vc,Ic = self.slnF" from lineariseDssModels

        Pass in state=None to initialise this.

        ====
        Inputs
        ====
        state: required, the state at which the solution is found
        uRcrd: whether or not to also update the update record slnr
        uRcrdIdx: If saving with uRcrd, saves only these idxs

        ====
        Creates
        ====
        sln: the solution struct, containing
            - stateIn, the state used to solve opendss
            - VsrcMeas, the voltages at the source solution
            - Vc, the voltages excluding the source
            - stateOut, the state after solving (taps etc may change)
            - vc, V, v; derived voltages in magnitude/pu etc
            - TP, total power
            - TL, total losses
            - Cnvg, converged flag
        """
        if state is None:
            # Initiliase if required
            self.sln = struct()
            for key, val in self.slnVals.items():
                setattr(self.sln, key, val)
        else:
            # Otherwise return by setting the values from slnVals.
            self.sln.stateIn = deepcopy(state)
            VcAll = d.setNtwkState(state)
            self.sln.VsrcMeas = VcAll[:3]
            self.sln.Vc = VcAll[3:]
            self.sln.stateOut = d.getNtwkState()

            getVset(self.sln, self.vKvbase)  # gets V,vc,v

            self.sln.TP = tp2ar(d.DSSCircuit.TotalPower)[0]  # kW
            self.sln.TL = tp2ar(d.DSSCircuit.Losses)[0] / 1e3  # kW
            self.sln.Cnvg = d.SLN.Converged

        if uRcrd:
            self.updateRecord(uRcrdIdx)

    def updateRecord(self, uRcrdIdx=None):
        if not hasattr(self, "slnr"):
            self.slnr = struct()
            self.slnr.stateIn = []
            self.slnr.stateOut = []
            self.slnr.TP = np.empty((0))  # so .real works
            self.slnr.TL = np.empty((0))
            self.slnr.Cnvg = []
            self.slnr.VsrcMeas = np.empty((0, 3))

            if uRcrdIdx is None:
                self.slnr.uRcrdIdx = np.arange(self.nV)
                self.slnr.YZv = self.YZv
                self.slnr.vKvbase = self.vKvbase
                self.slnr.Vc = np.empty((0, self.nV))  # run getVset() to get all
            else:
                self.slnr.uRcrdIdx = uRcrdIdx
                self.slnr.YZv0 = self.YZv
                self.slnr.YZv = vecSlc(self.YZv, uRcrdIdx)
                self.slnr.vKvbase = self.vKvbase[uRcrdIdx]
                self.slnr.Vc = np.empty((0, len(uRcrdIdx)))

        self.slnr.stateIn.append(self.sln.stateIn)
        self.slnr.stateOut.append(self.sln.stateOut)

        self.slnr.TP = np.r_[self.slnr.TP, self.sln.TP]
        self.slnr.TL = np.r_[self.slnr.TP, self.sln.TL]
        self.slnr.Cnvg.append(self.sln.Cnvg)
        self.slnr.VsrcMeas = np.r_[self.slnr.VsrcMeas, np.array([self.sln.VsrcMeas])]

        if uRcrdIdx is None:
            self.slnr.Vc = np.r_[self.slnr.Vc, np.array([self.sln.Vc])]
        else:
            self.slnr.Vc = np.r_[self.slnr.Vc, np.array([self.sln.Vc[uRcrdIdx]])]

    @staticmethod
    def cMat2rMat(cMat, pmConj=False):
        """Convert complex matrix to 2x2 real counterpart.

        If pmConj is False, is a 'normal' complex to real matrix,
        [ [R,-I],[I,R] ]. If true, is [ [R,I],[I,-R] ] (and
        cannot be represented by a single complex number).

        Can be np arrays or sparse csc/csr matrices.
        """
        if type(cMat) is np.ndarray:
            if not pmConj:
                rMat = np.block([[cMat.real, -cMat.imag], [cMat.imag, cMat.real]])
            else:
                rMat = np.block([[cMat.real, cMat.imag], [cMat.imag, -cMat.real]])
        if type(cMat) in [sparse.csr.csr_matrix, sparse.csc.csc_matrix]:
            if not pmConj:
                rMat = sparse.bmat([[cMat.real, -cMat.imag], [cMat.imag, cMat.real]])
            else:
                rMat = sparse.bmat([[cMat.real, cMat.imag], [cMat.imag, -cMat.real]])
        return rMat

    # =============================== HC funcs
    def allGenSetup(self):
        """Add single phase generators at YZsy, YZsd

        WARNING: Note that this updates state0!
        - also updates generator indexes, numbers.
        """
        self.YZsyG = tuple(d.addGenerators(self.YZsy, 0))
        self.YZsdG = tuple(d.addGenerators(self.YZsd, 1))
        self.YZsG = self.YZsyG + self.YZsdG

        state_ = d.getNtwkState()
        self.state0["GenY"] = state_["GenY"]
        self.state0["GenD"] = state_["GenD"]

        self.updateGenCount()
        self.getIdxPhs()

    def runMc(self, pdf, method, lms=[0.1, 0.6], **kwargs):
        """Run the SHC Monte Carlo analysis using pdf and method.

        ====
        Inputs
        ====
        pdf: hcDraws object, for generating MC scenarios
        method: on of
            - 'linMc'
            - 'prgMc'
            - 'fstMc'
            - 'dssMc'
            - 'dssMc_em'
        lms: list of load multipliers for MC calculations. Goes into lms_

        kwargs:
        - allVsave: calculate and save all complex voltages of a method.
        - V_: known voltages from a prior solution. *REQ* for dssMc_em
                        -> should be (nSc x nLm+1 x nMc x nV+3)
        - stateSolve: the initial state for the circuit, from which the
                      linear models and initial capTap is calculated.
        """
        if "YZsG" not in self.__dict__.keys():
            self.allGenSetup()

        # assume an upper and lower constraint for each variable
        nLm = len(lms)
        nCn = len(self.cns.kw) * nLm * 2
        nSc = pdf.meta.nP[0]
        nMc = pdf.meta.nMc
        Mu = pdf.getMuCov(prmI=np.arange(nSc), nGen=self.nP)[0]

        if method == "dssMc":
            print("===> WARNING! Turning off AllowForms, non-reversible.")
            d.DSSObj.AllowForms = False

        stateSolve = kwargs.get("stateSolve", self.state0.copy())
        stateSolve["LoadMult"] = np.mean(lms)
        stateSolve["GenY"] = [(1 + 0 * 1j) * Mu[nSc // 2] / 1e3] * self.nPy
        stateSolve["GenD"] = [(1 + 0 * 1j) * Mu[nSc // 2] / 1e3] * self.nPd
        d.setNtwkState(stateSolve)
        state_ = d.getNtwkState()

        # get string version of loadmults for calling from structs
        lms_ = [str(lms[i]) for i in range(len(lms))]
        allVsave = kwargs.get("allVsave", False)
        V_ = kwargs.get("V_", None)

        # results per scenario
        feas = np.zeros((nSc, nMc))
        fFrac = np.zeros((nSc, nCn))
        vMax = np.zeros((nSc, nMc))
        if allVsave:
            vAll = np.zeros((nSc, nLm + 1, nMc, self.nV + 3), dtype=complex)
            capTap = []

        # generate scenarios
        # Mu = pdf.halfLoadMean(self.loadScaleNom,self.xhyNtot,self.xhdNtot)
        pdfMcAll = []
        for i in range(pdf.meta.nP[0]):
            # pdfMc in kW
            pdfMcAll.append(pdf.genPdfMcSet(nMc, i, nGen=self.nP)[0])

        # Initialise
        cRes = structDict(
            {kw: structDict({lm: None for lm in lms_}) for kw in self.cns.kw}
        )
        self.cResO = [
            (kw, lm, cn) for kw in self.cns.kw for lm in lms_ for cn in ["L", "U"]
        ]
        self.getCresN()

        # Setup a few more things where required
        if method in ["linMc", "fstMc"]:
            self.lineariseSystem("fpl", [], state=state_, CtrlFix=True)
            pml = self.processLinMdl(
                lms,
            )
        elif method in ["dssMc", "dssMc_em"]:
            for kw in cRes.kw:
                for lm in cRes[kw].kw:
                    cRes[kw][lm] = np.zeros((nMc, self.cResN[kw]))

        # Do the pre
        # if method=='fstMc':
        # self.getCnsNstds(pdf,pml,)

        # For each scenario calculate the voltages
        for i, pGen in enumerate(pdfMcAll):
            if method == "prgMc":
                cRes, S = self.prgMcCalc(pGen, cRes, lms_, Mu[i], state_, lms)
            elif method == "linMc":
                cRes, S = self.linMcCalc(
                    pGen,
                    cRes,
                    pml,
                )
            elif method == "dssMc":
                print(i)
                cRes, S = self.dssMcCalc(
                    pGen,
                    cRes,
                    lms_,
                    lms,
                    state_,
                )
            elif method == "dssMc_em":
                cRes, S = self.dssMcCalc_em(
                    cRes,
                    V_[i],
                )

            feas[i], fFrac[i], = self.feasCalc(
                cRes,
                nMc,
            )
            vMax[i] = dNet.getCnsCalcVmax(cRes)
            if allVsave:
                vAll[i] = S[0]
                capTap.append(S[1])

        # return HC result
        hcCurve = np.sum(feas, axis=1) / nMc
        # hcCurveIdvl = np.sum(fFrac,axis=1)/nMc
        hcR = {
            "fs": feas,
            "fsFr": fFrac,
            "hcC": hcCurve,
            # 'hcCi':hcCurveIdvl,
            "cResO": self.cResO,
            # 'cRes':cRes, # for debugging
            "vMax": vMax,
        }

        if allVsave:
            self.saveVmc(vAll, pdf, capTap, method, lms_)

        return structDict(hcR)

    def saveVmc(self, vAll, pdf, capTap, method, lms):
        """Save key opendss solution vals into a .pkl for later study."""
        fn = self.VmcFn(method, lms, pdf)
        vmcData = {
            "pdf": pdf,
            "vAll": vAll,
            "capTap": capTap,
        }
        with open(fn, "wb") as file:
            pickle.dump(vmcData, file)
            print("Data saved to:\n\t-->  ." + fn.replace(fn_root, ""))

    def getVmc(self, pdf, method, lms):
        """Get opendss solutions and return. Oppostive of saveVmc"""
        fn = self.VmcFn(method, lms, pdf)
        with open(fn, "rb") as file:
            res = pickle.load(file)
            print("Data loaded:\n\t-->  ." + fn.replace(fn_root, ""))
        return res

    def VmcFn(
        self,
        method,
        lms,
        pdf,
    ):
        sd = os.path.join(fn_root, "lin_models", "hcRuns", self.feeder)
        if not os.path.exists(sd):
            os.mkdir(sd)
            print("Created directory:\n\t-->", sd)
        _N = [str(pdf.meta.nMc), str(pdf.meta.nP[0])]
        _lms = [str(lm).replace(".", ";") for lm in lms]
        fn = os.path.join(
            sd,
            "_".join(
                [
                    self.feeder,
                    method,
                ]
                + _lms
                + _N
            )
            + ".pkl",
        )
        return fn

    def getCresN(
        self,
    ):
        """Get a dict of the dimension of each of the constraint results."""
        cResN0 = {
            "vMv": self.nVmv,
            "vLv": self.nVlv,
            "Dv": self.nV,
            "Ixfm": len(self.YprmFlws_TRN),
            "Vub": self.nVps,
        }
        self.cResN = structDict(cResN0)

    # def prgMcCalc(self,pGen,cRes,lms_,mu,state,lms,):
    # """Calculate the SHC using 'progressive linear method' (prg)

    # """
    # state['GenY'] = [(mu + 0*1j)/1e3]*self.nPy
    # state['GenD'] = [(mu + 0*1j)/1e3]*self.nPd

    # for lm,lm_ in zip(lms,lms_):
    # state['LoadMult'] = lm
    # self.lineariseSystem('fpl',[],state=state)
    # pml = self.processLinMdl([lm],)

    # DVmv = (pml.KpuMv.dot( pGen ).T)*1e3 # convert from kW to W
    # DVlv = (pml.KpuLv.dot( pGen ).T)*1e3
    # DV = np.c_[ DVmv, DVlv ]

    # # Manually adding (most straightforward for now?)
    # cRes.vMv[lm_] = DVmv + pml.bpuMv[0]
    # cRes.vLv[lm_] = DVlv + pml.bpuLv[0]
    # cRes.Dv[lm_] = np.abs(DV)

    # return cRes, [None,None]

    def linMcCalc(
        self,
        pGen,
        cRes,
        pml,
    ):
        """Calculate the SHC using the 'base linear method'"""
        for cns, (A, b) in self.pmlPairs.items():
            if not type(A) is list:
                # Models of the form Ax + b:
                DA = (pml[A].dot(pGen).T) * 1e3
                if DA.dtype == float:
                    lNet.updateCresCns(
                        cRes[cns],
                        pml[b],
                        Ax=DA,
                    )
                elif DA.dtype == complex:
                    lNet.updateCresCns(cRes[cns], pml[b], Ax=DA, cplx=True)

            else:
                # Models of the form |A_*x + b_|/(C_*x + d_)
                A_, b_ = A
                C_, d_ = b

                DA = (pml[A_].dot(pGen).T) * 1e3
                DC = (pml[C_].dot(pGen).T) * 1e3
                lNet.updateCresCns(
                    cRes[cns], Bs=pml[b_], Ax=DA, Cx=DC, Ds=pml[d_], cplxFrac=True
                )

        return cRes, [None, None]

    def dssMcCalc(self, pGen, cRes, lms_, lms, state_):
        """Calculate the SHC using the non-linear solution from OpenDSS."""
        conv = []
        V = np.zeros((len(lms) + 1, pGen.shape[1], self.nV + 3), dtype=complex)
        capTap = []

        # Loop through the nMc values
        for i, pdfRow in enumerate(pGen.T):
            d.setGenPq(self.YZsG, pGen[:, i])

            # Solve from the same starting position each time
            d.setCapTap(state_["capTap"])

            # Solve through each of the load mult points, then flicker.
            # NB the 'old' order was to solve for minimum load last.
            for j, lm in enumerate(lms):
                d.SLN.LoadMult = lm
                d.SLN.Solve()
                conv.append(d.SLN.Converged)
                V[j, i] = tp2ar(d.DSSCircuit.YNodeVarray)
                capTap.append(d.getCapTap())

            # finally solve for voltage deviation.
            d.DSSText.Command = "Batchedit generator..* kW=0.001"
            CtrlMode_ = d.setControlMode(-1)
            d.SLN.Solve()
            V[-1, i] = tp2ar(d.DSSCircuit.YNodeVarray)
            conv.append(d.SLN.Converged)
            d.setControlMode(CtrlMode_)

            self.dssCresUpdate(cRes, V[:, i], i)

        if sum(conv) != len(conv):
            print("\nNo. Converged:", sum(conv), "/", len(conv))
        return cRes, (V, capTap)

    def dssMcCalc_em(
        self,
        cRes,
        V,
    ):
        """Emulate running dssMcCalc, but do so using known solution V.

        V should be Nlm+1 x Nmc x nV+3
        """
        for i in range(V.shape[1]):
            self.dssCresUpdate(cRes, V[:, i], idx=i)
        return cRes, [V, None]

    def dssCresUpdate(self, cRes, V_, idx):
        """Update cRes using the solution V_, with the ith index.

        V_ should be Nlm+1 x nV+3
        """
        cSlnJ = self.v2cns(V_, None, True)[0]
        for key, val in cSlnJ.items():
            lNet.updateCresCns(cRes[key], val, idx=idx)

    def v2cns(self, V, slct=None, getCns=False, linSet=None):
        """Use the voltage matrix V to build the constraints dictionary.

        V should have Nlm+1 on the first axis and nV+3 on the second axis.

        Use tp2ar(d.DSSCircuit.YNodeVarray).reshape(1,-1) if from dss direct.
        """
        nLm = V.shape[0] - 1

        Vpu = abs(V[:, 3:]) / self.vKvbase

        # Set the constraints dict according to cns
        C = {}
        if getCns:
            if "vMv" in self.cns.kw:
                C["vMv"] = [vpu[self.mvIdx] for vpu in Vpu[:-1]]
            if "vLv" in self.cns.kw:
                C["vLv"] = [vpu[self.lvIdx] for vpu in Vpu[:-1]]
            if "Dv" in self.cns.kw and nLm > 0:
                C["Dv"] = [Vpu[-2] - Vpu[-1]] * nLm
            if "Vub" in self.cns.kw:
                Vps = self.Vc2Vcub[1::3].dot(V[:-1].T).T
                Vns = self.Vc2Vcub[2::3].dot(V[:-1].T).T
                Vub = np.abs(Vns) / np.abs(Vps)
                C["Vub"] = [vub for vub in Vub]
            if "Ixfm" in self.cns.kw:
                self.getYprmBd(dssType=d.TRN, psConv=True, capTap=d.getCapTap())
                Ixfm = np.abs(self.YprmBd_TRN.dot(V[:-1].T).T) / self.xfmRatings
                C["Ixfm"] = [ixfm for ixfm in Ixfm]

        # Then if any 'selections' are chosen also get them. [For validation.]
        if slct is None:
            Vslct = None
        if slct == "V":
            Vslct = V.ravel()[3:]
        if slct == "|V|":
            Vslct = np.abs(V).ravel()[3:]
        if slct == "I":
            self.getYprmBd(capTap=d.getCapTap())
            Vslct = self.YprmBd.dot(V.T).ravel()
        if slct == "Vseq":
            Vslct = self.Vc2Vcub.dot(V.T).ravel()
        if slct == "|Vps|":
            Vslct = np.abs(self.Vc2Vcub[1::3].dot(V.T).ravel())
        if slct == "Vns":
            Vslct = self.Vc2Vcub[2::3].dot(V.T).ravel()
        if slct == "Vub":
            Vps = np.abs(self.Vc2Vcub[1::3].dot(V.T).ravel())
            Vns = self.Vc2Vcub[2::3].dot(V.T).ravel()
            Vslct = Vns / Vps
        if slct == "Ixfm":
            self.getYprmBd(dssType=d.TRN, psConv=True, capTap=d.getCapTap())
            Vslct = self.YprmBd_TRN.dot(V.T).ravel()
        if slct == "Sfdr":
            YprmV, idxV = self.getYprm3phFdr()
            YprmVc = YprmV.conj()
            V0 = d.getVsrc()
            vPrmC = np.r_[V0.reshape(-1, 1), V.T[idxV]].conj()
            Vslct = V0 * (YprmVc.dot(vPrmC))
        if slct == "V_mv":
            Vslct = V.ravel()[3:][self.mvIdx]
        if slct == "Vmlv":
            Vslct = V.ravel()[3:][self.mlvIdx]
        if slct == "|Vmlv|":
            Vslct = np.abs(V.ravel()[3:][self.mlvIdx])

        if linSet == "sqr" and slct in ["V", "|V|"]:
            Vslct = Vslct[self.sIdx]

        return C, Vslct

    def getYprm3phFdr(self):
        """Get the YprmV for the first PDE element (assumed head of feeder).

        These are assumed to be for the first element.
        """
        d.PDE.First
        elem = d.PDE.Name

        YprmV = self.Yprm[elem]["YprmV"][:3]

        idxs = self.Yprm[elem]["yzIdx"]
        idxV = [idx - 3 for idx in idxs if idx > 2]

        return (
            YprmV,
            idxV,
        )

    @staticmethod
    def updateCresCns(objCns, Bs, Ax=0, **kwargs):
        """Update objCns with Bs.

        Make sure that Bs order is correct - (list NOT dict!)
        idx is therefore used to force the index.

        Without kwargs, sets to Bs + offset (useful for Ax + b).

        -----
        kwargs
        -----
        idx: the index (as in the i-th MC run). Use with OpenDSS solutions
        cplx: flag, if True result is |Ax + b|
        cplxFrac: flag, if True result is |Ax + b|/Cx + d
        Cx: use when using cplxFrac
        Ds: use when using cplxFrac

        """
        idx = kwargs.get("idx", None)
        cplx = kwargs.get("cplx", False)
        cplxFrac = kwargs.get("cplxFrac", False)

        Cx = kwargs.get("Cx", None)
        Ds = kwargs.get("Ds", [None] * len(objCns.kw))

        for kw, B_, D_ in zip(objCns.kw, Bs, Ds):
            if cplx:
                rslt = np.abs(B_ + Ax)
            elif cplxFrac:
                rslt = np.abs(B_ + Ax) / (D_ + Cx)
            else:
                rslt = B_ + Ax

            if idx is None:
                objCns[kw] = rslt
            else:
                objCns[kw][idx] = rslt

    @staticmethod
    def getCnsCalcVmax(cRes):
        vSet = []
        for kw in ["vMv", "vLv"]:
            for lm in cRes[kw].kw:
                vSet.append(cRes[kw][lm])
        return np.max(np.concatenate(vSet, axis=1), axis=1)

    @staticmethod
    def compareHc(hcR_a, hcR_b):
        blOut = []
        for kw in hcR_a.kw:
            cmp = hcR_a[kw] == hcR_b[kw]
            if type(cmp) is bool:
                blOut.append(cmp)
            else:
                blOut.append(cmp.all())
        print(blOut)
        return blOut

    def processLinMdl(
        self,
        loadMults,
    ):
        """Turn the linear model into a model suitable for HC runs (the pml).

        The corresponding constraints are captured in the dictionary
        'pmlPairs' (a fixed attribute of lNet).

        NB! Generators are set to zero in the calculations of the
        bpuPu nominal values, all other properties of 'state' remain the same.

        The units are in 'x', which is in VA & tap number.

        Example:
        VmvPu = KpuMv*x + bpuMv

        """
        pml = {"lm": loadMults}
        linMdl = self.mdl

        # Set the sensitivity matrices, which do not change with lm:
        Kpu = vmM(1 / self.vKvbase, linMdl.K)
        pml["KpuMv"] = Kpu[self.mvIdx, : self.nP]
        pml["KpuLv"] = Kpu[self.lvIdx, : self.nP]
        pml["KpuDv"] = Kpu[:, : self.nP]

        pml["U0pu"] = vmM(1 / self.vKvbaseSeq, linMdl.U0)[:, : self.nP]
        pml["U1pu"] = vmM(1 / self.vKvbaseSeq, linMdl.U1)[:, : self.nP]
        pml["Lpu"] = vmM(1 / self.xfmRatings, linMdl.L)[:, : self.nP]

        # get the state ready to go in
        state_ = linMdl.state.copy()
        state_["GenY"] = [0j] * self.nPy
        state_["GenD"] = [0j] * self.nPd
        mtVals = ["LdsYdss", "LdsDdss", "GenYdss", "GenDdss"]
        state_.update(zip(mtVals, mtList(len(mtVals))))

        # update all of the constants and states
        lmU = ["bpuMv", "bpuLv", "b0", "e0pu", "e1pu", "fpu", "state"]
        pml.update(zip(lmU, mtList(len(lmU))))
        for lm in loadMults:
            state = state_.copy()
            state["LoadMult"] = lm
            x_ = self.state2x(state)

            bpu = (linMdl.b + linMdl.K.dot(x_)) / self.vKvbase

            pml["bpuMv"].append(bpu[self.mvIdx])
            pml["bpuLv"].append(bpu[self.lvIdx])
            pml["b0"].append(np.zeros(self.nV))

            pml["e0pu"].append((linMdl.e0 + linMdl.U0.dot(x_)) / self.vKvbaseSeq)
            pml["e1pu"].append((linMdl.e1 + linMdl.U1.dot(x_)) / self.vKvbaseSeq)
            pml["fpu"].append((linMdl.f + linMdl.L.dot(x_)) / self.xfmRatings)
            pml["state"].append(state)

        return structDict(pml)

    def feasCalc(self, cRes, nMc, **kwargs):
        """Calculate feasibility metrics, given a load flow solution.

        Originally based on cnsBdsCalc from linSvdCalcs

        ====
        kwargs
        ====
        cns: constraints, that are different from class constraints.

        """
        # pull out kwargs
        cns = kwargs.get("cns", self.cns)

        # Clean up very low voltages
        for kw in ["vMv", "vLv"]:
            for lm in cRes[kw].kw:
                cRes[kw, lm][cRes[kw, lm] < 0.5] = 1.0

        # build a nested extreme results struct
        cResFs = {}
        for (
            kw,
            lm,
            cn,
        ) in self.cResO:
            if cn == "U":
                if self.cResN[kw] == 0:
                    maxVal = np.ones((nMc,))
                else:
                    maxVal = np.max(cRes[kw, lm], axis=1)
                cResFs[kw, lm, cn,] = (
                    maxVal
                    > cns[
                        kw,
                        cn,
                    ]
                )
            elif cn == "L":
                if self.cResN[kw] == 0:
                    minVal = np.ones((nMc,))
                else:
                    minVal = np.min(cRes[kw, lm], axis=1)
                cResFs[kw, lm, cn,] = (
                    minVal
                    < cns[
                        kw,
                        cn,
                    ]
                )
        self.cResFs = cResFs

        # fFrac 'SHOULD' have length Nmc x Nprm but doesn't right now!?
        fFrac = 100 * np.array([sum(cResFs[cro]) for cro in self.cResO]) / nMc

        # feas should have len Nmc
        feas = np.any(np.array([cResFs[cro] for cro in self.cResO]), axis=0)
        return (
            feas,
            fFrac,
        )

    # =============================== Plotting Functions
    def getBusPhs(self):
        self.bus0v, self.phs0v = self.busPhsLoop(self.YZv)
        self.bus0s, self.phs0s = self.busPhsLoop(self.YZsy + self.YZsd)

        # # Legacy - not sure what this does though...
        # self.bus0vIn, self.phs0vIn = self.busPhsLoop(self.vInYNodeOrder)
        # self.bus0vIn, self.phs0vIn = self.busPhsLoop(self.vInYNodeOrder)

    def busPhsLoop(self, YZset):
        bus0 = []
        phs0 = []
        for yz in YZset:
            fullBus = yz.split(".")
            bus0.append(fullBus[0].lower())
            if len(fullBus) > 1:
                phs0.append(fullBus[1::])
            else:
                phs0.append(["1", "2", "3"])
        return np.array(bus0), np.array(phs0)

    def getSourceBus(self):
        d.Vsrcs.First
        self.vSrcBus = d.AE.BusNames[0]

    def setupPlots(self):
        """Get data required for using plotNetwork.

        Creates
        ---
        self.busCoords - dict of bus:(x,y)
        self.branches - odict of brch:[bus0,bus1]
        self.regBuses - list of buses which are regulated
        self.srcReg - flag if there is a regulator at the source node
        - also updates fPrm_['pms'] to a new size if wanted.
        - Then runs self.getBusPhs() to set
            > self.bus0v, self.phs0v, self.bus0s, self.phs0s, the buses/phases
              for different plotting types.

        """
        self.busCoords = d.getBusCoordsAug()
        self.branches = odict(d.getBranchBuses())
        self.regBuses = d.getRgcNds(self.YZvIdxs)[0]

        # if there is a regulator 'on' the source bus
        regSrc = [
            "epri24",
            "8500node",
            "123bus",
            "123busCvr",
            "epriJ1",
            "epriK1",
            "epriM1",
        ]
        self.srcReg = 1 if self.feeder in regSrc else 0

        # Update fPrm_['pms'] if wanted.
        plotMarkerDict = {
            "13bus": 150,
            "34bus": 150,
            "eulv": 100,
            "epri5": 10,
            "epriK1cvr": 15,
            "epriK1": 15,
            "8500node": 8,
        }

        if self.feeder in plotMarkerDict.keys():
            self.fPrm_["pms"] = plotMarkerDict[self.feeder]
        elif self.feeder[0] == "n":
            self.fPrm_["pms"] = 40

        # Get the bus and phase information for voltage/powers.
        self.getBusPhs()

    def plotNetwork(self, pType=None, **kwargs):
        """Plot a network with option pType and colorbar minMax vals.

        Adapted from plotNetBuses from lineariseDssModels

        -----
        INPUTS
        -----
        pType - an option to choose what thing to plot.

            --- 'Node' options:
            > None  - a basic plot with all colours identical
            > 'n'   - a basic plot with all colours identical
            > 'v'   - mean node voltage
            > 'vPh' - phase voltages
            > 'p'   - total real power injection
            > 'q'   - total reactive power injection
            > 's'   - total apparent power injection
            > 'qPh' - daisy plot of reactive powers

            --- 'Branch' options:
            > '_s' - power through each line
            > '_sLog' - same, but log taken
            > '_L' - losses in the line

        kwargs:
            minMax  - the min/max value for the colorbar, if there is one.
            score0  - force a score value to be passed into get bus_score
            cmapSet - force the colormap color to cmapSet
            cmapSetB - force the branch colormap color to cmapSetB
            cbTtl   - force the colormap title
            ax      - axis to plot onto

        """
        cmapSet = kwargs.get("cmapSet", None)
        bMinMax = kwargs.get("bMinMax", None)
        ax = kwargs.get("ax", None)
        pType = "n" if pType is None else pType

        if not hasattr(self, "busCoords"):
            self.setupPlots()

        if ax is None:
            _, ax = plt.subplots()

        # First plot the branches:
        if pType[0] != "_":
            self.plotBranches(ax)
        else:
            bch_scores, bMinMax = self.get_bch_score(
                pType,
                bMinMax,
            )
            self.plotBranches(
                ax,
                scores=bch_scores,
                kw=kwargs,
            )

            # Opts: cmsq(cm.PuBuGn,0.8,0.9),
            cmapSet = cmsq(cm.Greys, 0.6, 0.7) if cmapSet is None else cmapSet

        # self.plotSub(ax,pltSrcReg=False)
        self.plotSub(ax)

        ttl, edgeOn, pltRegs, busNans, cbTtl0, bus_score, minMax0 = self.get_bus_score(
            pType,
            kwargs,
        )

        # Set the cmaps for plotting
        if not cmapSet is None:
            self.fPrm_["cmap"] = cmapSet
        elif pType[0] in self.fPrm_["cms"].keys():
            self.fPrm_["cmap"] = self.fPrm_["cms"][pType[0]]
        else:
            self.fPrm_["cmap"] = plt.cm.viridis

        # Get the minmax values
        minMax = kwargs.get("minMax", minMax0)
        cbTtl = kwargs.get("cbTtl", cbTtl0)

        # Plot the buses
        if pType[-2:] == "Ph":
            self.plotBuses3ph(ax, bus_score, minMax)
        else:
            self.plotBuses(ax, bus_score, minMax, edgeOn=edgeOn, busNans=busNans)

        # Plot the colorbar
        if (
            pType
            not in [
                "n",
                "B",
            ]
            and pType[0] != "_"
        ):
            self.plotNetColorbar(ax, minMax, cbTtl=cbTtl)

        # Plot the regs
        if pltRegs:
            self.plotRegs(ax)

        # Tidy up the figure & set title
        ax.axis("off")
        if self.fPrm_["ttlOn"]:
            plt.title(self.feeder, loc="left")
        plt.gca().set_aspect("equal", adjustable="box")
        plt.grid(False)
        plt.tight_layout()

        # Save figure if we like using sff_legacy, fPrm
        figname = whocalledme(2) + "_" + self.feeder + "_" + pType
        self.sff_(figname)

    def get_bch_score(
        self,
        pType,
        bMinMax=None,
    ):
        """Get the branch score to pass into plotBranches.

        Inputs
        ---
        pType - the plot type
        bMinMax - the max & min plotting scale

        Returns
        ---
        scores, values between 0 (or 0.1) and 1 for each bus
        bMinMax, the corresponding max and min values
        """
        nm2ii = {nm: i for i, nm in enumerate(d.getObjAttr(d.PDE, AEval="Name"))}

        if pType in ["_s", "_sLog"]:
            pwrs = tp2arL(d.getObjAttr(d.PDE, AEval="Powers"))
            scores = np.array(
                [
                    sum(np.abs(pwrs[nm2ii[br]])[: self.Yprm[br]["nAI"]])
                    for br in self.branches.keys()
                ]
            )

            if pType == "_sLog":
                scores = np.log10(scores)
                bMinMax = (
                    [min(scores[scores > (max(scores) - 6)]), max(scores)]
                    if bMinMax is None
                    else bMinMax
                )
            else:
                bMinMax = (
                    [1e-6 * max(scores), max(scores)] if bMinMax is None else bMinMax
                )

        elif pType == "_L":
            lsss = [r[0] for r in d.getObjAttr(d.PDE, AEval="Losses")]
            scores = np.array([lsss[nm2ii[br]] for br in self.branches.keys()])

            bMinMax = [1e-10 * max(scores), max(scores)] if bMinMax is None else bMinMax

        # Remove small values
        scores[scores < bMinMax[0]] = np.nan

        # Fit to min/max
        scores = (scores - bMinMax[0]) / (bMinMax[1] - bMinMax[0])

        return scores, bMinMax

    def get_bus_score(
        self,
        pType,
        kwargs,
    ):
        """Get the bus score (and other properties) based on pType.

        Inputs
        ---
        pType - the plot type, see help(self.plotNetwork)
        kwargs - the kwargs passed into self.plotNetwork.

        Returns
        ---
        ttl - the title for the figure
        edgeOn - flag for buses to have edges or not on the lines
        pltRegs - flag to plot voltage regulators
        busNans - flag to plot buses with value of nan or not
        cbTtl0 - title for the colorbar
        bus_score - score for the buses to be plotted
        minMax0 - minimum and maximum values to scale the scores by
        """

        ttl = None
        edgeOn = True
        pltRegs = True
        busNans = True

        if pType == "n":
            bus_score0 = kwargs.get("score0", np.ones((self.nP)))
            bus_score, minMax0 = self.getScrVals(bus_score0, "s", "mean")
            edgeOn = False
            cbTtl0 = ""
        elif pType == "v":
            bus_score0 = kwargs.get("score0", np.abs(self.sln.V) / self.vKvbase)
            bus_score, minMax0 = self.getScrVals(bus_score0, "v", "mean")
            cbTtl0 = "Voltage, pu"
        elif pType == "B":
            # Build plot - based on Turing code
            bus_score0 = kwargs["score0"]  # required to be passed in
            bus_score, _ = self.getScrVals(bus_score0, "v", "mean")
            minMax0 = kwargs["minMax0"]
            pltRegs = False
            cbTtl0 = ""
        elif pType == "vPh":
            bus_score0 = kwargs.get("score0", np.abs(self.sln.V) / self.vKvbase)
            bus_score, minMax0 = self.getScrVals(bus_score0, "v", "ph")
            cbTtl0 = "Voltage, pu"
        elif pType == "p":
            bus_score0 = kwargs.get("score0", -1e-3 * self.getX()[: self.nP])
            bus_score, minMax0 = self.getScrVals(bus_score0, "s", "sum")
            cbTtl0 = "Load, kW"
        elif pType == "q":
            bus_score0 = kwargs.get("score0", -1e-3 * self.getX()[self.nP : self.nS])
            bus_score, minMax0 = self.getScrVals(bus_score0, "s", "sum")
            minMaxAbs = np.max(
                np.abs(
                    np.array(
                        [
                            np.nanmax(list(bus_score.values())),
                            np.nanmin(list(bus_score.values())),
                        ]
                    )
                )
            )
            minMax0 = [-minMaxAbs, minMaxAbs]
            cbTtl0 = "$Q$, kVAr"  # Positive implies capacitive
        elif pType == "s":
            bus_score0 = kwargs.get("score0", 1e-3 * np.abs(self.getXc()[: self.nP]))
            bus_score, minMax0 = self.getScrVals(bus_score0, "s", "sum")
            cbTtl0 = "$|S|$, kVA"
        elif pType == "qPh":
            bus_score0 = kwargs.get("score0", -1e-3 * self.getX()[self.nP : self.nS])
            bus_score, minMax0 = self.getScrVals(bus_score0, "s", "ph")
            scoresFull = (
                list(bus_score["1"].values())
                + list(bus_score["2"].values())
                + list(bus_score["3"].values())
            )
            minMaxAbs = np.max(
                np.abs(np.array([np.nanmax(scoresFull), np.nanmin(scoresFull)]))
            )
            minMax0 = [-minMaxAbs, minMaxAbs]
            cbTtl0 = "$Q$, kVAr"  # Positive implies capacitive
            # self.fPrm_['tFs'] = 8 # ttlFontsize
        elif pType[0] == "_":
            bus_score0 = kwargs.get("score0", np.ones((self.nP)))
            bus_score, minMax0 = self.getScrVals(bus_score0, "s", "mean")
            edgeOn = False
            cbTtl0 = ""
            busNans = False

        return ttl, edgeOn, pltRegs, busNans, cbTtl0, bus_score, minMax0

    def plotNetColorbar(self, ax, minMax, cbTtl=None, nCbar=150):
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        x0 = [xlim[0] - 1]
        y0 = [ylim[0] - 1]
        cntr = ax.contourf(
            np.array([x0 * 2, x0 * 2]),
            np.array([y0 * 2, y0 * 2]),
            np.array([minMax, minMax[::-1]]),
            nCbar,
            cmap=self.fPrm_["cmap"],
        )
        ax.set_xlim(xlim)
        ax.set_ylim(ylim)
        # cbar = plt.colorbar(cntr,shrink=0.75,
        # ticks=np.linspace(minMax[0],minMax[1],5))
        cbar = plt.colorbar(
            cntr, shrink=0.6, ticks=np.linspace(minMax[0], minMax[1], 5)
        )
        cbar.ax.tick_params(labelsize=self.fPrm_["tFs"])
        if cbTtl != None:
            cbar.ax.set_title(cbTtl, pad=10, fontsize=self.fPrm_["tFs"])

    def plotBuses(
        self,
        ax,
        scores,
        minMax,
        edgeOn=True,
        busNans=True,
    ):
        """Plot the buses using scores scores.

        Inputs
        ---
        ax - the axis
        scores - the sscores to uses
        minMax - linearly scale between minMax (useful for extending range)
        edgeOn - if True, puts a thin edge around each bus with a score
        busNans - if True, plots the busNans with color '#cccccc'.

        """
        cmap = plt.cm.viridis if self.fPrm_["cmap"] is None else self.fPrm_["cmap"]

        x0scr, y0scr, xyClr, x0nne, y0nne = mtList(5)
        for bus, coord in self.busCoords.items():
            if not np.isnan(self.busCoords[bus][0]):
                if np.isnan(scores[bus]):
                    x0nne.append(coord[0])
                    y0nne.append(coord[1])
                else:
                    x0scr.append(coord[0])
                    y0scr.append(coord[1])
                    if minMax == None:
                        score = scores[bus]
                    else:
                        score = (scores[bus] - minMax[0]) / (minMax[1] - minMax[0])

                    xyClr.append(cmap(score))

        plt.scatter(
            x0scr, y0scr, marker=".", color=xyClr, zorder=+10, s=self.fPrm_["pms"]
        )
        if edgeOn:
            plt.scatter(
                x0scr,
                y0scr,
                marker=".",
                zorder=+11,
                s=self.fPrm_["pms"],
                facecolors="none",
                edgecolors="k",
            )

        if busNans:
            plt.scatter(x0nne, y0nne, color="#cccccc", marker=".", zorder=+5, s=3)

    def plotBuses3ph(self, ax, scores3ph, minMax, edgeOn=True):
        if self.fPrm_["cmap"] is None:
            cmap = plt.cm.viridis
        else:
            cmap = self.fPrm_["cmap"]
        x0scr = []
        y0scr = []
        xyClr = []
        x0nne = []
        y0nne = []
        phscr = []
        scale = 50
        phsOffset = {"1": [0.0, 1.0], "2": [-0.86, -0.5], "3": [0.86, -0.5]}
        for ph, scores in scores3ph.items():
            for bus, coord in self.busCoords.items():
                if not np.isnan(self.busCoords[bus][0]):
                    if np.isnan(scores[bus]):
                        x0nne = x0nne + [coord[0]]
                        y0nne = y0nne + [coord[1]]
                    else:
                        phscr = phscr + [ph]
                        x0scr = x0scr + [coord[0]]
                        y0scr = y0scr + [coord[1]]
                        if minMax == None:
                            score = scores[bus]
                        else:
                            score = (scores[bus] - minMax[0]) / (minMax[1] - minMax[0])

                        xyClr = xyClr + [cmap(score)]

            self.hex3phPlot(
                ax, x0scr, y0scr, xyClr, phscr, sf=self.sfDict3ph[self.feeder]
            )
            # plt.scatter(x0scr,y0scr,marker='.',color=xyClr,
            # zorder=+10,s=self.plotMarkerSize)
            # if edgeOn: plt.scatter(x0scr,y0scr,marker='.',
            # zorder=+11,s=self.plotMarkerSize,
            # facecolors='none',edgecolors='k')
            plt.scatter(x0nne, y0nne, color="#cccccc", marker=".", zorder=+5, s=15)

    def hex3phPlot(self, ax, x, y, xyClr, xyPhs, sf):
        xy0 = np.exp(1j * np.linspace(np.pi / 2, 5 * np.pi / 2, 7))
        # phsOffset =  {'1':np.exp(1j*np.pi/6),'2':np.exp(1j*5*np.pi/6),
        # '3':np.exp(1j*-np.pi/2)}
        phsOffset = {
            "1": np.exp(1j * 0),
            "2": np.exp(1j * 2 * np.pi / 3),
            "3": np.exp(1j * 4 * np.pi / 3),
        }
        patches = []
        for i in range(len(x)):
            brSf = 1.15
            xyPts = np.c_[
                sf * (xy0 + brSf * phsOffset[xyPhs[i]]).real + x[i],
                sf * (xy0 + brSf * phsOffset[xyPhs[i]]).imag + y[i],
            ]
            # NB putting zorder here doesn't seem to work vvvv
            patches.append(Polygon(xyPts, True, fill=1, color=xyClr[i]))
            patches.append(
                Polygon(
                    xyPts, True, fill=0, linestyle="-", linewidth=0.4, edgecolor="k"
                )
            )
            patches.append(
                Polygon(
                    [
                        [x[i], y[i]],
                        [
                            x[i] + sf * brSf * phsOffset[xyPhs[i]].real,
                            y[i] + sf * brSf * phsOffset[xyPhs[i]].imag,
                        ],
                    ],
                    False,
                    color="k",
                    linewidth=1.0,
                )
            )
        p = PatchCollection(patches, match_original=True)
        p.set_zorder(10)
        ax.add_collection(p)

    def plotRegs(self, ax):
        if self.nT > 0:
            i = 0
            for regBus in self.regBuses:
                regCoord = self.busCoords[regBus.split(".")[0].lower()]
                if not np.isnan(regCoord[0]):
                    ax.plot(regCoord[0], regCoord[1], "r", marker=(6, 1, 0), zorder=+5)
                    # ax.annotate(str(i),(regCoord[0],regCoord[1]),zorder=+40)
                else:
                    print("Could not plot regulator bus" + regBus + ", no coordinate")
                i += 1
        else:
            print("No regulators to plot.")

    def plotBranches(self, ax, scores=[], kw={}):
        """Plot the branches.

        To plot LV networks 'per feeder', then pass in lvFdrs=True

        Inputs
        ---
        ax - the axis to plot onto
        scores - the scores to plot with (if [] then plot as #cccccc
        kw - kwargs passed into plotNetwork

        """
        cmsel = kw.get("cMapSetB", cm.cividis_r)

        segclr, segnan, clrs = mtList(3)
        for i, buses in enumerate(self.branches.values()):
            # buses[:2] required due to, e.g., 3-winding transformers
            bcs = [self.busCoords[b.split(".")[0]] for b in buses[:2]]

            if len(scores) == 0:
                segnan.append(bcs)
            else:
                if np.isnan(scores[i]):
                    segnan.append(bcs)
                else:
                    segclr.append(bcs)
                    if not kw.get("lvFdrs", False):
                        clrs.append(cmsel(scores[i]))
                    else:
                        # Get the feeder no
                        try:
                            fdri = int(buses[1].split("_")[0][-1])
                        except:
                            fdri = 0

                        clrs.append(cmsel[fdri](scores[i]))

        if len(scores) == 0:
            coll = LineCollection(segnan, colors="#cccccc")
        else:
            # At the moment, ignore segnans for colored plots. Reverse also
            # seems a little cleaner for most of these.
            coll = LineCollection(segclr[::-1], colors=clrs[::-1])

        ax.add_collection(coll)
        ax.autoscale_view()

    def plotSub(self, ax, pltSrcReg=True):
        """Plot the substation onto axis ax."""
        srcCoord = self.busCoords[self.vSrcBus]
        if np.isnan(srcCoord[0]):
            print(
                "Nominal source bus coordinate not working," + " trying z appended..."
            )
            try:
                srcCoord = self.busCoords[self.vSrcBus + "z"]
            except:
                srcCoord = [np.nan, np.nan]
        if np.isnan(srcCoord[0]):
            print("Nominal source bus coordinate not working, trying 1...")
            srcCoord = self.busCoords["1"]

        if not np.isnan(srcCoord[0]):
            ax.plot(srcCoord[0], srcCoord[1], "k", marker="H", markersize=8, zorder=+20)
            ax.plot(srcCoord[0], srcCoord[1], "w", marker="H", markersize=3, zorder=+21)
            if self.srcReg and pltSrcReg:
                ax.plot(
                    srcCoord[0], srcCoord[1], "r", marker="H", markersize=3, zorder=+21
                )
            else:
                ax.plot(
                    srcCoord[0], srcCoord[1], "w", marker="H", markersize=3, zorder=+21
                )
        else:
            print("Could not plot source bus" + self.vSrcBus + ", no coordinate")

    def getScrVals(self, Scrs, busType="v", aveType=None):
        """Get the score values for each location in the busType."""
        if aveType is None:
            aveType = "mean"
        # direct copy
        if busType == "v":
            bus0 = self.bus0v
            phs0 = self.phs0v.flatten()
        elif busType in ["s", "p", "q", "n"]:
            bus0 = self.bus0s
            phs0 = self.phs0s.flatten()
        elif busType == "vIn":
            bus0 = self.bus0vIn
            phs0 = self.phs0vIn.flatten()

        scrMin = 1e100
        scrMax = -1e100
        scrVals = {}
        if aveType == "ph":
            scrVals["1"] = {}
            scrVals["2"] = {}
            scrVals["3"] = {}
            for bus in self.busCoords:  # initialise
                scrVals["1"][bus] = np.nan
                scrVals["2"][bus] = np.nan
                scrVals["3"][bus] = np.nan
        else:
            for bus in self.busCoords:
                scrVals[bus] = np.nan  # initialise

        for bus in self.busCoords:
            if not np.isnan(self.busCoords[bus][0]):
                if aveType == "ph":
                    phs = phs0[bus0 == bus.lower()]

                vals = Scrs[bus0 == bus.lower()]
                vals = vals[~np.isnan(vals)]
                if len(vals) > 0:
                    if aveType == "mean":
                        scrVals[bus] = np.mean(vals)
                        scrMax = max(scrMax, np.mean(vals))
                        scrMin = min(scrMin, np.mean(vals))
                    elif aveType == "sum":
                        scrVals[bus] = np.sum(vals)
                        scrMax = max(scrMax, np.sum(vals))
                        scrMin = min(scrMin, np.sum(vals))
                    elif aveType == "max":
                        scrVals[bus] = np.max(vals)
                        scrMax = max(scrMax, np.max(vals))
                        scrMin = min(scrMin, np.max(vals))
                    elif aveType == "min":
                        scrVals[bus] = np.min(vals)
                        scrMax = max(scrMax, np.min(vals))
                        scrMin = min(scrMin, np.min(vals))
                    elif aveType == "ph":
                        i = 0
                        for ph in phs:
                            scrVals[ph[0]][bus] = vals[i]
                            scrMax = max(scrMax, np.min(vals[i]))
                            scrMin = min(scrMin, np.min(vals[i]))
                            i += 1

        if scrMin == scrMax:
            scrMinMax = None
        else:
            scrMinMax = [scrMin, scrMax]
        return scrVals, scrMinMax

    def sff_(self, figName=None):
        """Alias for sff_legacy(self.fPrm,figName)."""
        sff_legacy(self.fPrm, figName)


class lNet(dNet):
    """A linearised network of the dNet.

    There are a couple of different ways of linearising the system,
    this class is intended to try and capture the use of FPL and FOT
    linearizations.

    Creates a linear model object that can create:
    V    = Mx + a                  - complex voltages in (control) x
    |V|* = Kx + b                  - voltage magnitudes in x
    I    = Wx + c                  - complex currents in x
    Vseq = Ux + e                  - complex seq voltages in x
    |Vps|= U1x + e1                - (real) ps voltage in x
    Vns  = U2x + e2                - (complex) ns voltage in x
    Vub  = (U0x + e0)/|Vps|        - complex unbalance in x at 3ph buses
    Ixfm = Lx + f                  - xfmr wdg-1 positive seq current in x
    Sfdr = Nx + g                  - complex three-phase feeder power in x
    V_mv = Ox + h                  - complex MV volts in x (with schur's cmpl)

    MLV circuit low-rank models (use the mlvNet child class instead):
    Vmlv = M1x1 + CFx + i          - complex voltages in x
    |Vmlv|=K1x1 + DFx + j          - abs voltages in x

    ========
    Unbalance is negative sequence, following IEC/TR 61000-3-14:2011
    (EMC Compatability BSI standard)

    *Note that this can be used for voltage flicker, setting x[iTaps] = 0

    """

    linDir = join(sys.path[0], "lin_models")

    lmPairs = {
        "M": ["a", "V"],
        "K": ["b", "|V|"],
        "U": ["e", "Vseq"],
        "U1": ["e1", "|Vps|"],
        "U2": ["e2", "Vns"],
        "U0": ["e0", "Vub"],
        "W": ["c", "I"],
        "L": ["f", "Ixfm"],
        "N": ["g", "Sfdr"],
        "O": ["h", "V_mv"],
    }

    pmlPairs = {
        "vMv": ["KpuMv", "bpuMv"],
        "vLv": ["KpuLv", "bpuLv"],
        "Dv": ["KpuDv", "b0"],
        "Vub": [["U0pu", "e0pu"], ["U1pu", "e1pu"]],
        "Ixfm": ["Lpu", "fpu"],
    }

    lmSets = {
        "all": list(lmPairs.keys()),
        "bare": ["M"],
        "bareMv": ["O"],
        "sqr": ["M"],
    }

    def __init__(
        self,
        frId=5,
        tests=[],
    ):
        """Basic initialisation using dNet class, not using any tests."""
        dNet.__init__(
            self,
            frId,
            tests=tests,
        )

    def lineariseSystem(self, mtype="fpl", tests=["bsc"], **kwargs):
        """Linearise a lNet object around state, using method mtype.

        ====
        Arguments
        ====
        mtype: method type, one of
                - fot, first order taylor (ie Jacobian)
                - fpl, fixed point linearization
        tests: list of strings of test types
                - 'bsc', a quick, basic test of all models
                - 'cpf', test using a cpf (a range of values through 0)
        linSet: which linearisation to get, one of
                - all, fully gets most models
                - bare, only gets the complex voltage model
                - bareMv, only gets the complex voltage model in MV voltages
                - sqr, only gets the complex voltage model in load voltages

        ====
        kwargs
        ====
        state: dss network state which linearization is calculated at.
        CtrlFix: set to True to lock control during linearization.

        """
        state = kwargs.get("state", self.state0.copy())
        CtrlFix = kwargs.get("CtrlFix", False)
        linSet = kwargs.get("linSet", "all")

        if CtrlFix:
            CtrlMode0 = state["CtrlMode"]
            state["CtrlMode"] = -1

        # Get the initial linearization in complex voltages
        if linSet in [
            "all",
            "bare",
            "bareMv",
            "sqr",
        ]:
            Mt0 = self.newTapModel(state)

        if linSet in [
            "all",
            "bare",
        ]:
            if mtype == "fpl":
                My0, Md0, a = self.fplLinM(state)
            if mtype == "fot":
                My0, Md0, a = self.fotLinM(state)

            M = self.xydt2x(My0, Md0, Mt0)

        linTap = np.array(state["capTap"][1])

        # Medium voltage models
        if linSet in [
            "all",
            "bareMv",
        ]:
            MyMv, MdMv, h = self.fotLinM(state, mvOnly=True)
            O = self.xydt2x(MyMv, MdMv, Mt0[self.mvIdx])

        # Square voltage model
        if linSet in ["sqr"]:
            My, Md, a = self.fotLinM(state, sqr=True)
            M = self.xydt2x(My, Md, Mt0[self.sIdx])

        # Voltage magnitude model
        if linSet in ["all"]:
            K, b = self.nrelLinKspd(M, a, state)

        # Voltage unbalance models
        if linSet in ["all"]:
            U2 = self.Vc2Vcub[2::3, 3:].dot(M)
            e2 = self.Vc2Vcub[2::3].dot(np.r_[d.getVsrc(), a])
            U0 = U2
            e0 = e2

            U = self.Vc2Vcub[:, 3:].dot(M)
            e = self.Vc2Vcub.dot(np.r_[d.getVsrc(), a])

            Mps = self.Vc2Vcub[1::3, 3:].dot(M)
            aps = self.Vc2Vcub[1::3].dot(np.r_[d.getVsrc(), a])
            U1, e1 = self.nrelLinKspd(Mps, aps, state)

        # Current models
        if linSet in ["all"]:
            Vhat = np.r_[d.getVsrc(), M.dot(self.getX()) + a]
            self.getYprmBd()
            c = self.YprmBd.dot(np.r_[d.getVsrc(), a])

            WS = self.YprmBd[:, 3:].dot(M[:, : self.nS])
            W1t = self.YprmBd[:, 3:].dot(M[:, self.nS :])

            _, dYprm_dtSet = self.getdYdt(
                yset="Yprm",
            )
            W0t = np.zeros((self.nIprm, 0))
            for dYdt in dYprm_dtSet:
                W0t = np.c_[W0t, dYdt.dot(Vhat)]

            W = np.c_[WS, W0t + W1t]

            self.getYprmBd(dssType=d.TRN, psConv=True)
            L = self.YprmBd_TRN[:, 3:].dot(M)
            f = self.YprmBd_TRN.dot(np.r_[d.getVsrc(), a])

        # Feeder power model, assuming the first element is at the head
        # of the feeder.
        if linSet in ["all"]:
            YprmV, idxV = self.getYprm3phFdr()
            YprmVc = YprmV.conj()
            V0 = d.getVsrc()
            V0C = d.getVsrc().conj()
            vPrm = np.r_[V0C, a[idxV].conj()]

            g = V0 * (YprmVc.dot(vPrm))
            N = np.diag(V0).dot(YprmVc[:, 3:].dot(M[idxV].conj()))

        # Put all of the models into the mdl dictionary.
        lmSet = self.lmSets[linSet]
        mdlDict = {
            "mtype": mtype,
            "state_": state,
            "state": d.getNtwkState(),
            "linSet": linSet,
            "lmSet": lmSet,
            "linTap": linTap,
        }

        for key in lmSet:
            val = self.lmPairs[key]
            mdlDict.update({key: locals()[key]})
            mdlDict.update({val[0]: locals()[val[0]]})
        self.mdl = structDict(mdlDict)

        # Run specified tests
        if "bsc" in tests:
            self.fastTest()
        if "cpf" in tests:
            self.cpfTest()

        # Return control to before, if changed to off
        if CtrlFix:
            state["CtrlMode"] = CtrlMode0

    def loadLinModel(self, loadInfo={}):
        """Load a pre-saved linear model.

        loadInfo
        """
        if not "LoadMult" in loadInfo.keys():
            loadInfo["LoadMult"] = self.state0["LoadMult"]
        if not "mtype" in loadInfo.keys():
            loadInfo["mtype"] = "fot"

        filename = "_".join(
            [self.feeder, "{:.0%}".format(loadInfo["LoadMult"]), loadInfo["mtype"]]
        )
        fn = join(self.linDir, self.feeder, filename + ".pkl")
        with open(fn, "rb") as file:
            self.mdl = structDict(pickle.load(file))

    def saveLinModel(self, filename=None):
        if filename is None:
            filename = "_".join(
                [
                    self.feeder,
                    "{:.0%}".format(self.mdl.state["LoadMult"]),
                    self.mdl.mtype,
                ]
            )
        sd = join(self.linDir, self.feeder)
        if not os.path.exists(sd):
            os.mkdir(sd)
        fn = join(sd, filename + ".pkl")
        with open(fn, "wb") as file:
            pickle.dump(self.mdl.asdict(), file)
            print("File saved to:\n\t", fn)

    def fplLinM(self, state):
        Vh = d.setNtwkState(state)[3:]

        # Get the admittance matrix (includes caching in here)
        self.getYlli(
            capTap=state["capTap"],
        )

        My0_ = mvM(self.Ylli, 1 / Vh.conj())[:, self.pyIdx]
        Md0_ = mvM(aMulBsp(self.Ylli, self.Hmat.T), 1 / (self.Hmat.dot(Vh.conj())))
        a = -self.Ylli.dot(self.Ybus[3:, :3].dot(d.getVsrc()))

        My0 = np.c_[My0_, -1j * My0_]
        Md0 = np.c_[Md0_, -1j * Md0_]

        return My0, Md0, a

    def nrelLinKspd(self, M, a, state):
        """Create K (magnitude sensitivity) matrices from complex matrices.

        Takes a complex-valued function of a real argument
            yy = Mx + a
        and convert to the real-valued func (at xHat)
            |yy| = Kx + b
        giving real K, b.

        See just before (17) of Bernstein or thesis eqn (44) pg 99/119.

        Based on nrelLinK.
        """
        # First check M is good:
        if M.shape[1] != (self.nS + self.nT):
            raise Exception("Non-compatible dimensions of M!")

        # Get the value of 'yhat' at the linearization point
        d.setNtwkState(state)
        x_ = self.state2x(d.getNtwkState())

        yyHat = M.dot(x_) + a

        K = vmM(yyHat.conj() / np.abs(yyHat), M).real
        b = abs(yyHat) - K.dot(x_)

        return K, b

    def createTapModel(self, state=None):
        """Based on legacy code, for checking the numerical method.

        Compared to the old method, puts out in terms of Volts per Tap no,
        rather than volts per 'tap pu'.
        """
        if state is None:
            d.setNtwkState(self.YbusState)
        else:
            d.setNtwkState(state)

        CtrlMode_ = d.setControlMode(-1)

        j = d.RGC.First
        dVdt = np.zeros((self.nV, d.RGC.Count))
        dVdt_cplx = np.zeros((d.DSSCircuit.NumNodes - 3, d.RGC.Count), dtype=complex)
        dVpsdt = np.zeros((self.nVps, d.RGC.Count))
        dVseqdt = np.zeros((self.nVseq, d.RGC.Count), dtype=complex)
        dIdt = np.zeros((self.nIprm, d.RGC.Count), dtype=complex)

        while j != 0:
            tap0 = d.RGC.TapNumber
            d.TRN.Name = d.RGC.Transformer
            dt_ = (d.TRN.MaxTap - d.TRN.MinTap) / d.TRN.NumTaps
            if abs(tap0) < 16:
                tap_hi = tap0 + 1
                tap_lo = tap0 - 1
                dt = 2 * dt_
            elif tap0 == 16:
                tap_hi = tap0
                tap_lo = tap0 - 1
                dt = dt_
            else:
                tap_hi = tap0 + 1
                tap_lo = tap0
                dt = dt_
            d.RGC.TapNumber = tap_hi
            d.SLN.Solve()
            # V1 NOT the same order as AllBusVmag! vvvvv
            V1 = abs(tp2ar(d.DSSCircuit.YNodeVarray)[3:])
            V1_cplx = tp2ar(d.DSSCircuit.YNodeVarray)[3:]
            V1seq = d.getVseq(self.seqBus)
            V1ps = d.getVps(self.seqBus)
            I1 = d.getIprm(self.YprmNms)[0]

            d.RGC.TapNumber = tap_lo
            d.SLN.Solve()

            V0 = abs(tp2ar(d.DSSCircuit.YNodeVarray)[3:])
            V0_cplx = tp2ar(d.DSSCircuit.YNodeVarray)[3:]
            V0seq = d.getVseq(self.seqBus)
            V0ps = d.getVps(self.seqBus)
            I0 = d.getIprm(self.YprmNms)[0]

            dVdt[:, j - 1] = dt_ * (V1 - V0) / dt
            dVdt_cplx[:, j - 1] = dt_ * (V1_cplx - V0_cplx) / dt
            dVpsdt[:, j - 1] = dt_ * (V1ps - V0ps) / dt
            dVseqdt[:, j - 1] = dt_ * (V1seq - V0seq) / dt
            dIdt[:, j - 1] = dt_ * (I1 - I0) / dt

            d.RGC.TapNumber = tap0
            j = d.RGC.Next

        d.SLN.Solve()
        d.setControlMode(CtrlMode_)

        return dVdt_cplx, dVdt, dVpsdt, dVseqdt, dIdt

    def fotLinM(self, state, **kwargs):
        """Calculate linearization using the FOT method.

        Notes:
        - based on the m-file firstOrderTaylor.
        - V is YNodeV[3:]

        NB: Note that the use of sparse matrices requires some slightly odd
        matrix calculation orders.

        -----
        kwargs
        -----
        - mvOnly: bool, if true then only solve for mvIdx buses
        - sqr: bool, if true then only solve for sIdx buses [NB misses D-ld Vs]
        - lvFull: bool, if true get an LV model with an upstream network dmvdx
        - lvFullSqr: bool, same as lvFull but a 'sqr' version
        - lvRankFczn: bool, calculate MV low-rank factorization part
        - lvFullData: dict of data required for lvFull;
            1. dmvdx: 3 x nX complex array of MV circuit values,
            2. lvIdx: the locations of the LV injections in dmvdx,
            3. xY: the xY value (for all x)
            4. xD: the xD value (for all x)
            5. N: The number of controls in x.
            6. nPydt: [nPy, nPd, nT] for all controls in x

        """
        mvOnly = kwargs.get("mvOnly", False)
        sqr = kwargs.get("sqr", False)
        lvFull = kwargs.get("lvFull", False)
        lvFullSqr = kwargs.get("lvFullSqr", False)
        lvRankFczn = kwargs.get("lvRankFczn", False)
        lvFullData = kwargs.get("lvFullData", None)

        # First: if mvOnly is specified and no MV (e.g. some
        # LV circuits with a source to xfmr) then return empty matrices.
        if mvOnly and self.nVmv == 0:
            My = np.zeros((0, self.nPy * 2), dtype=complex)
            Md = np.zeros((0, self.nPd * 2), dtype=complex)
            a = np.zeros((0,), dtype=complex)
            return My, Md, a

        # Get circuit parameters and
        Vh = d.setNtwkState(state)[3:]
        fotMats = self.getFotMatrices(
            state,
        )

        # Solve using schurSolve
        t0 = time.time()
        if mvOnly:
            fotMats = self.schurShift(fotMats, "mv")
            scAonD = schurSolve(*fotMats)

            nVlin = self.nVmv
            VhLin = Vh[self.mvIdx]
            xY, xD = self.x2xydt(self.state2x(state))[:2]
            nPydt = [self.nPy, self.nPd, 0]
        elif sqr:
            fotMats = self.schurShift(fotMats, "sqr")
            scAonD = schurSolve(*fotMats)

            nVlin = self.nP
            VhLin = Vh[self.sIdx]
            xY, xD = self.x2xydt(self.state2x(state))[:2]
            nPydt = [self.nPy, self.nPd, 0]
        elif lvFull or lvFullSqr:
            B1, B2 = fotMats[4:]
            YL0 = self.Ybus[3:, :3]
            B1_ = vmM(Vh, YL0.conj()).dot(sparse.csc_matrix(lvFullData["dmvdx"].conj()))

            B1_ = sparse.vstack((B1_.real, B1_.imag)).tolil()
            B1_[:, lvFullData["lvIdx"]] = B1 + B1_[:, lvFullData["lvIdx"]]

            B2_ = sparse.lil_matrix((self.nPd * 2, lvFullData["N"]))
            B2_[:, lvFullData["lvIdx"]] = B2

            fotMats[4] = B1_.tocsc()
            fotMats[5] = B2_.tocsc()

            if lvFull:
                scAonD = schurSolve(*fotMats)
                nVlin = self.nV
                VhLin = Vh
            elif lvFullSqr:
                fotMats = self.schurShift(fotMats, "sqr")
                scAonD = schurSolve(*fotMats)

                nVlin = self.nP
                VhLin = Vh[self.sIdx]

            xY, xD = [lvFullData[xId] for xId in ["xY", "xD"]]
            nPydt = lvFullData["nPydt"][:2] + [0]
        elif lvRankFczn:
            YL0 = self.Ybus[3:, :3]
            B1_ = vmM(Vh, YL0.conj()).tocsc()
            # fotMats[4] = sparse.vstack((B1_.real,B1_.imag)).tocsc()
            fotMats[4] = dNet.cMat2rMat(B1_).tocsc()

            B2_ = sparse.csc_matrix((self.nPd * 2, 6))
            fotMats[5] = B2_

            fotMats = self.schurShift(fotMats, "sqr")
            scAonD = schurSolve(*fotMats)

            nVlin = self.nP
        else:
            # Copied from below for convenience
            M5i = sparse.dia_matrix(
                (1 / (self.Hmat.dot(Vh)), 0), shape=(self.nPd, self.nPd)
            ).tocsr()
            DDi = dNet.cMat2rMat(M5i.conj(), True).tocsr()
            BDi = fotMats[1].dot(DDi)
            scAonD = schurSolve(*fotMats, Di=DDi, BDi=BDi)

            nVlin = self.nV
            VhLin = Vh
            xY, xD = self.x2xydt(self.state2x(state))[:2]
            nPydt = [self.nPy, self.nPd, 0]

        print("Inversions complete", time.time() - t0)

        # Pull out My, Md
        scAonD_s = scAonD[:nVlin] + 1j * scAonD[nVlin::]
        if lvRankFczn:
            My = scAonD_s
            Md = None
            a = Vh[self.sIdx]
        else:
            My, Md, _ = self.x2xydt(scAonD_s, xs=1, nPydt=nPydt)
            a = VhLin - My.dot(xY) - Md.dot(xD)

        # # Used in some old code
        # dMy = self.Hmat.dot(My)
        # dMd = self.Hmat.dot(Md)
        # da = self.Hmat.dot(a)

        return (
            My,
            Md,
            a,
        )

    def getFotMatrices(
        self,
        state,
    ):
        """Get the 'base' matrices used for the FOT method variants."""
        # Get circuit parameters
        Vh = d.setNtwkState(state)[3:]
        YL0 = self.Ybus[3:, :3]
        YLL = self.Ybus[3:, 3:]

        shd = self.state2xc(state)[self.nPy : self.nP]
        iDconj = shd / (self.Hmat.dot(Vh))

        # Build the circuit matrices 'A' [in Ax=B]
        M1 = sparse.dia_matrix(
            ((self.Hmat.T).dot(iDconj), 0), shape=(self.nV, self.nV)
        ).tocsr()
        M2 = vmM(Vh, self.Hmat.T)
        M3 = vmM(Vh, YLL.conj())
        M4 = sparse.dia_matrix(
            ((YL0.conj()).dot(d.getVsrc().conj()) + (YLL.conj()).dot(Vh.conj()), 0),
            shape=(self.nV, self.nV),
        ).tocsr()

        M5 = sparse.dia_matrix(
            (self.Hmat.dot(Vh), 0), shape=(self.nPd, self.nPd)
        ).tocsr()
        M5i = sparse.dia_matrix(
            (1 / (self.Hmat.dot(Vh)), 0), shape=(self.nPd, self.nPd)
        ).tocsr()

        M6 = vmM(iDconj, self.Hmat)

        A11 = (M1 - M4 - M3).real
        A12 = (-M1 + M4 - M3).imag
        A21 = (M1 - M4 - M3).imag
        A22 = (M1 - M4 + M3).real

        # Build the equation 'A' matrices for A.dot(XX) = B
        # -- Order of XX ('outputs'): [dvR_dx,dvI_dx,dIdR_dx,dIdI_dx]
        AA = sparse.bmat([[A11, A12], [A21, A22]]).tocsr()
        BB = dNet.cMat2rMat(M2, True).tocsr()
        CC = dNet.cMat2rMat(M6, False).tocsc()
        DD = dNet.cMat2rMat(M5, True).tocsc()

        # Build the circuit 'B' matrices
        # -- Order of B ('control'): [Py,Pd,Qy,Qd]
        Bpy = sparse.coo_matrix(
            (-np.ones(self.nPy), (self.syIdx[: self.nPy], np.arange(self.nPy))),
            shape=(self.nV * 2, self.nPy),
        ).tocsc()
        Bqy = sparse.coo_matrix(
            (-np.ones(self.nPy), (self.syIdx[self.nPy :], np.arange(self.nPy))),
            shape=(self.nV * 2, self.nPy),
        ).tocsc()
        Bpd = sparse.eye((self.nPd))
        Bqd = sparse.eye((self.nPd))
        ZroY = sparse.csc_matrix((self.nV * 2, self.nPd))
        ZroDY = sparse.csc_matrix((self.nPd, self.nPy))
        ZroDD = sparse.csc_matrix((self.nPd, self.nPd))
        B_D = sparse.bmat([[ZroDY, Bpd, ZroDY, ZroDD], [ZroDY, ZroDD, ZroDY, Bqd]])
        B_Y = sparse.hstack([Bpy, ZroY, Bqy, ZroY])
        B = sparse.vstack([B_Y, B_D]).tocsc()

        B1 = B[: self.nV * 2]
        B2 = B[self.nV * 2 : :]

        return [AA, BB, CC, DD, B1, B2]

    def schurShift(
        self,
        fotMats,
        mtype,
    ):
        """Change the model so that is only 'in' the mtype voltages.

        (Main reason for this method is shown in WB 26-6-20.)
        """
        if mtype == "mv":
            idxI = np.r_[self.mvIdx, self.mvIdx + self.nV]
            idxJ = np.r_[self.lvIdx, self.lvIdx + self.nV]
        elif mtype == "sqr":
            idxI = np.r_[self.sIdx, self.sIdx + self.nV]
            idxJ = np.arange(self.nV * 2)
            idxJ = np.delete(idxJ, idxI)

        AA, BB, CC, DD, B1, B2 = fotMats

        AA_ = AA[idxI][:, idxI]
        BB_ = sparse.hstack((AA[idxI][:, idxJ], BB[idxI])).tocsr()
        CC_ = sparse.vstack((AA[idxJ][:, idxI], CC[:, idxI])).tocsc()
        DD_ = sparse.bmat(
            [
                [AA[idxJ][:, idxJ], BB[idxJ]],
                [CC[:, idxJ], DD],
            ]
        ).tocsc()

        BB1_ = B1[idxI]
        BB2_ = sparse.vstack((B1[idxJ], B2))

        return AA_, BB_, CC_, DD_, BB1_, BB2_

    # Model testing ========
    def fastTest(
        self,
    ):
        """A fast test just to check the key lin. points have come out.

        Bits of this are similar to cpfTest.
        """
        print("\n".join(["-" * 30, self.feeder + ": " + self.mdl.mtype, "-" * 30]))

        state0 = self.mdl.state
        state = state0.copy()
        state["CtrlMode"] = -1

        for mSel in self.mdl.lmSet:
            c_vrbl = self.lmPairs[mSel]

            print("\nModel: {} = {}x + {}".format(c_vrbl[1], mSel, c_vrbl[0]))

            xx = self.state2x(self.mdl.state)

            MdlC = getattr(self.mdl, c_vrbl[0])
            if c_vrbl[1] in ["Vmlv", "|Vmlv|"]:
                xx1 = [xx[idxS] for idxS in self.ckts.LvYZsIdx_S]
                MdlC = np.concatenate(MdlC)
                dMdlSa = [
                    M_K1.dot(x1) for M_K1, x1 in zip(getattr(self.mdl, mSel), xx1)
                ]
                dMdlSb = [
                    C_D.dot(F.dot(xx))
                    for C_D, F in zip(
                        getattr(self.mdl, c_vrbl[2]), getattr(self.mdl, c_vrbl[3])
                    )
                ]
                dMdlS = np.concatenate([dA + dB for dA, dB in zip(dMdlSa, dMdlSb)])
            else:
                dMdlS = getattr(self.mdl, mSel).dot(xx)

                if c_vrbl[1] == "Vub":
                    MdlC_ = self.mdl.e1
                    dMdlS_ = self.mdl.U1.dot(xx)

            dH = 0.03
            kk = [0, 1.00, 1 - 0.5 * dH, 1 + 0.5 * dH]

            sln = mtDict(
                [
                    "act",
                    "actV",
                    "apx",
                    "err",
                    "errV",
                ]
            )
            sln["kk"] = kk
            sln = structDict(sln)
            for k in sln.kk:
                lm = k * self.mdl.state["LoadMult"]
                state["LoadMult"] = lm
                state["GenY"] = list(lm * np.array(state0["GenY"]) / state0["LoadMult"])
                state["GenD"] = list(lm * np.array(state0["GenD"]) / state0["LoadMult"])
                d.setNtwkState(state)
                sln.act.append(self.getVderivs(c_vrbl[1], self.mdl.linSet))

                V_ = tp2ar(d.DSSCircuit.YNodeVarray).reshape(1, -1)
                sln.actV.append(self.v2cns(V_, c_vrbl[1], linSet=self.mdl.linSet)[1])

                if c_vrbl[1] == "Vub":
                    sln.apx.append((MdlC + k * dMdlS) / (MdlC_ + k * dMdlS_))
                else:
                    sln.apx.append(MdlC + k * dMdlS)

                sln.err.append(self.pctRerr(sln.act[-1], sln.apx[-1]))
                sln.errV.append(self.pctRerr(sln.actV[-1], sln.apx[-1]))

            print("\t- No-load error: {:.3g}%".format(sln.err[0]))
            print("\t- Lin point error: {:.3g}%".format(sln.err[1]))
            print(
                "\t- Lin point dErr/dH: {:.3g}%".format((sln.err[3] - sln.err[2]) / dH)
            )
            # print('\n\tCheck v2cns:')
            # print('\t- No-load error: {:.3g}%'.format(errV[0]))
            # print('\t- Lin point error: {:.3g}%'.format(errV[1]))
            # print('\t- Lin point dErr/dH: {:.3g}%'.format(
            # (errV[3]-errV[2])/dH))

    @staticmethod
    def pctRerr(x0, x1):
        """Calculate the percentage relative error."""
        return 100 * norm(x0 - x1) / norm(x0)

    def cpfTest(self, **kwargs):
        """Test the voltage model, assuming fixed controls.

        Use pprint(self.lmPairs) to see which models can be run.

        Examples:
        - Basic complex voltage model test but do not plot:
            sln = self.cpfTest(pShw=False)
        - Test the LDC model forwards + backwards:
            self.cpfTest(mdl=self.mdlLdc,lm='M',lckd=False,hyst=True)
        - Test the tap linearisation in currents:
            self.cpfTest(mdl=self.mdl,lm='W',cpfType='T')

        -----
        kwargs
        -----
        - mdl: the model to test
        - k: the points to calculate the values at
        - lckd: locked voltage/cap controls
        - pShw: if False then suppress plotting
        - lm: the linear model to test, default as 'M' (variable Vc)
        - hyst: if True then get hysteresis loop (forwards then backwards).
        - cpfType: either 'S' (powers, nominal) or 'T' (taps)

        """
        # Pull out the initial functionality
        mdl = kwargs.get("mdl", self.mdl)
        lckd = kwargs.get("lckd", True)
        pShw = kwargs.get("pShw", True)
        lm = kwargs.get("lm", "M")
        hyst = kwargs.get("hyst", False)
        cpfType = kwargs.get("cpfType", "S")

        # Check options make sense:
        if cpfType == "T":
            if self.nT == 0:
                print("CPF on taps T not relevant, nT = 0 --> skipping.")
                return
            if "ldc" in mdl.mtype:
                raise Exception("Tap-LDC combination does not make sense!")
            if not lckd:
                raise Exception('Tap modelling must be "locked".')
            if hyst:
                raise Exception("Fixed taps should not exhibit hysteresis.")

        # A few derived variables
        c_vrbl = self.lmPairs[lm]

        # Get the linear model multiplications
        state_ = mdl.state  # state_ does NOT change.
        state = copy.deepcopy(state_)  # make a local copy of this for changing
        if state_["LoadMult"] == 0:
            sLM = 1
            state__ = copy.deepcopy(state_)
            state__["LoadMult"] = sLM
            xM_ = self.state2x(state__)
        else:
            sLM = state_["LoadMult"]
            xM_ = self.state2x(state_)

        if "ldc" in mdl.mtype:
            xM = xM_[: self.nS]
            dT = mdl.Ktap.dot(xM) / sLM
        else:
            xM = xM_

        if cpfType == "S":
            k_ = kwargs.get("k", np.arange(-0.7, 1.4, 0.05))

            mdl0 = getattr(mdl, c_vrbl[0])
            if c_vrbl[1] in ["Vmlv", "|Vmlv|"]:
                xx1 = [xM[idxS] for idxS in self.ckts.LvYZsIdx_S]
                dMdlSa = [M_K1.dot(x1) for M_K1, x1 in zip(getattr(self.mdl, lm), xx1)]
                dMdlSb = [
                    C_D.dot(F.dot(xM))
                    for C_D, F in zip(
                        getattr(self.mdl, c_vrbl[2]), getattr(self.mdl, c_vrbl[3])
                    )
                ]
                dMdl0 = np.concatenate([dA + dB for dA, dB in zip(dMdlSa, dMdlSb)])
                dMdl = dMdl0 / sLM
                mdl0 = np.concatenate(mdl0)
            else:
                dMdl = getattr(mdl, lm).dot(xM) / sLM

            if c_vrbl[1] == "Vub":
                MdlC_ = mdl.e1
                dMdlS_ = mdl.U1.dot(xM) / sLM
        elif cpfType == "T":
            k_ = kwargs.get("k", np.arange(-4, 5))
            tap_ = state_["capTap"][1].copy()

            dMdl = getattr(mdl, lm)[:, self.nS :].dot(np.ones(self.nT))
            mdl0 = getattr(mdl, lm).dot(xM) + getattr(mdl, c_vrbl[0])

        if hyst:
            kk = np.r_[k_, k_[::-1]]
        else:
            kk = k_

        d.setNtwkState(state)

        # Check the locked status of the model
        if lckd:
            state["CtrlMode"] = -1
        else:
            if "ldc" in mdl.mtype:
                # Get the locked/unlocked tap position stuff for comparison
                kwargsLL = kwargs.copy()
                kwargsLL.update({"pShw": False, "lckd": 1, "mdl": self.mdl})
                slnLL = self.cpfTest(**kwargsLL)

                kwargsLU = kwargs.copy()
                kwargsLU.update({"pShw": False, "lckd": 0, "mdl": self.mdl})
                slnLU = self.cpfTest(**kwargsLU)
            state["CtrlMode"] = 0

        print("--> Start CPF test.")
        # error; actual sln; apx sln; captaps; lin tap; cnvrg, dss/lin pwr
        sln = mtDict(["err", "act", "apx", "cts", "tLn", "cvg", "sDs", "sLn"])
        sln["kk"] = kk
        sln = structDict(sln)
        for i, k in enumerate(kk):
            if (i % (len(kk) // 4)) == 0:
                print(i + 1, "oo", len(kk))
            # Get the opendss solution
            if cpfType == "S":
                state["LoadMult"] = k
                state["GenY"] = list(k * np.array(state_["GenY"]) / sLM)
                state["GenD"] = list(k * np.array(state_["GenD"]) / sLM)
            elif cpfType == "T":
                state["capTap"][1] = [tp_ + k for tp_ in tap_]

            d.setNtwkState(state)
            sln.act.append(self.getVderivs(c_vrbl[1], self.mdl.linSet))

            if hyst:
                state = d.getNtwkState()

            # Get the linear solution & error
            if c_vrbl[1] == "Vub":
                sln.apx.append((dMdl * k + mdl0) / (MdlC_ + k * dMdlS_))
            else:
                sln.apx.append(dMdl * k + mdl0)

            sln.err.append(self.pctRerr(sln.act[-1], sln.apx[-1]))

            # Save tap positions for linear & real model
            if "ldc" in mdl.mtype:
                sln.tLn.append((dT * k) + mdl.btap + self.mdl.linTap)
            else:
                sln.tLn.append(self.mdl.linTap + self.getX()[self.nS :])

            sln.cts.append(d.getCapTap())

            # Save convergence/total power for debugging
            sln.cvg.append(d.SLN.Converged)
            sln.sDs.append(tp2ar(d.DSSCircuit.TotalPower)[0])

        cm_ = lambda x: getattr(mplcm, x[0])(np.linspace(0.5, 1.0, x[1]))
        if pShw:
            fig, axs = plt.subplots(
                5,
                figsize=(4, 7),
                sharex=True,
                gridspec_kw={"height_ratios": [1, 1, 0.25, 0.25, 0.5]},
            )

            # First do the error plots
            axs[0].plot(kk, sln.err, ".-", label="Error, " + lm)
            if not lckd:
                axs[0].plot(kk, slnLL.err, "C1-", label="errLL")
                if "ldc" in mdl.mtype:
                    axs[0].plot(kk, slnLU.err, "k.-", label="errLU")

            # Then show what the capTaps are doing
            xtraArgs = {"Linewidth": 0.8, "Markersize": 1.0}
            capMat, tapMat = self.cts2capTapMats(sln.cts)
            if len(tapMat[0]) != 0:
                axs[1].set_prop_cycle(color=cm_(("Blues", self.nT)))
                axs[1].plot(kk, tapMat, ".-", **xtraArgs)
                axs[1].set_prop_cycle(color=cm_(("PuRd", self.nT)))
                axs[1].plot(kk, sln.tLn, ".-", **xtraArgs)

            if len(capMat[0]) != 0:
                axs[2].set_prop_cycle(color=cm_(("Blues", self.nC)))
                axs[2].plot(kk, capMat, ".-")
                if not lckd:
                    capLlMat, tapLlMat = self.cts2capTapMats(slnLL.cts)
                    axs[2].set_prop_cycle(color=cm_(("Oranges", self.nC)))
                    axs[2].plot(kk, capLlMat, "C1.-", markersize=2, linewidth=0.8)

            axs[3].plot(kk, sln.cvg, "k.-")
            axs[4].plot(kk, np.array(sln.sDs).real, "C0.-")

            # A few things to tidy up the figures:
            axs[0].legend()
            axs[1].set_yticks(np.arange(-16, 20, 4))
            axs[2].set_yticks(np.arange(0, 2, 1))
            axs[3].set_yticks(np.arange(0, 2, 1))

            ylbls = ["% Err, " + lm, "Tap pos.", "Cap pos.", "Cnvrgd.", "DSS Pwr"]
            for ax, ylbl in zip(axs, ylbls):
                ax.grid(True)
                ax.set_ylabel(ylbl)

            axs[-1].set_xlabel("CPF parameter k")
            axs[0].set_title(self.feeder)
            plt.tight_layout()
            plt.show()

        print("cpfTest, converged:", 100 * sum(sln.cvg) / len(sln.cvg), "%")
        return sln

    def cts2capTapMats(self, capTap):
        """Take a list of capTaps and convert to an np array for plotting."""
        capMat = np.array([self.cap2list(row[0]) for row in capTap])
        tapMat = np.array([row[1] for row in capTap])
        return capMat, tapMat

    def makeSquareFotModel(self):
        """Create a square model self.mdlSquare from an FOT model.

        Useful, e.g., when only the voltages at loads are of interest.
        """
        self.mdlSquare = structDict
        self.mdlSquare.mtype = self.mdl.mtype
        self.mdlSquare.state = self.mdl.state
        self.mdlSquare.a = self.mdl.a[self.sIdx]
        self.mdlSquare.M = self.mdl.M[self.sIdx][:, : self.nS]
        self.mdlSquare.b = self.mdl.b[self.sIdx]
        self.mdlSquare.K = self.mdl.K[self.sIdx][:, : self.nS]
        self.mdlSquare.vKvbase = self.vKvbase[self.sIdx]

    def getVderivs(self, vrbl, linSet=None):
        """A wrapper for getting dss state variables (V, I, Vps, etc)"""
        if vrbl == "V":
            val = tp2ar(d.DSSCircuit.YNodeVarray)[3:]
        elif vrbl == "|V|":
            val = np.abs(tp2ar(d.DSSCircuit.YNodeVarray))[3:]
        elif vrbl in ["Vseq", "|Vps|", "Vns", "Vub"]:
            Vseq = d.getVseq(self.seqBus)
            if vrbl == "Vseq":
                val = Vseq
            elif vrbl == "|Vps|":
                val = np.abs(Vseq[1::3])
            elif vrbl == "Vns":
                val = Vseq[2::3]
            elif vrbl == "Vub":
                val = Vseq[2::3] / np.abs(Vseq[1::3])
        elif vrbl in ["I"]:
            val = d.getIprm(self.YprmNms)[0]
        elif vrbl in ["Ixfm"]:
            val = d.getIxfmPosSeq(xfmKeys=self.YprmNms_TRN)
        elif vrbl in ["Sfdr"]:
            d.Vsrcs
            val = d.get3phPower()
        elif vrbl in ["V_mv"]:
            val = tp2ar(d.DSSCircuit.YNodeVarray)[3:][self.mvIdx]
        elif vrbl in ["Vmlv"]:
            # NB only gets the LV voltages.
            val = tp2ar(d.DSSCircuit.YNodeVarray)[3:][self.mlvIdx]
        elif vrbl in ["|Vmlv|"]:
            val = np.abs(tp2ar(d.DSSCircuit.YNodeVarray)[3:][self.mlvIdx])

        if linSet == "sqr" and vrbl in ["V", "|V|"]:
            val = val[self.sIdx]

        return val

    def newTapModel(self, state):
        """Build the tap model, based on the work from 01-05-20.

        This is in Volts per Tap (previous models were in 'tap per tap' -
        normalised so that the response was either close to 1 or zero).

        Key insight: The sparse admittance matrix inversions ARE much faster
        than dense matrix inversions. Random Sparse matrices are MUCH slower
        to solve using sparse solve than the inverse admittance matrices of
        the same density, perhaps surprisingly.
        """

        # Basically a task in building the appropriate submatrices.
        Vsrc = d.getVsrc()
        Vh = d.setNtwkState(state)[3:]

        self.getYset(yset="Ybus", state=state)

        shd = self.state2xc(state)[self.nPy : self.nP]
        iDconj = shd / (self.Hmat.dot(Vh))

        xx = self.Ybus[3:].conj().dot(np.r_[d.getVsrc(), Vh].conj())

        f11 = sparse.dia_matrix(
            (((self.Hmat.T).dot(iDconj) - xx), [0]), (self.nV, self.nV)
        )

        f11hat = -vmM(Vh, self.Ybus[3:, 3:].conj())

        f12 = vmM(Vh, self.Hmat.T)
        f21 = vmM(iDconj, self.Hmat)
        f22 = sparse.dia_matrix((self.Hmat.dot(Vh), [0]), (self.nPd, self.nPd)).tocsr()

        A11 = f11.real + f11hat.real
        A12 = -f11.imag + f11hat.imag
        A21 = f11.imag + f11hat.imag
        A22 = f11.real - f11hat.real
        AA = sparse.bmat([[A11, A12], [A21, A22]]).tocsr()
        BB = dNet.cMat2rMat(f12, True).tocsr()
        CC = dNet.cMat2rMat(f21, False).tocsr()
        DD = dNet.cMat2rMat(f22, True).tocsr()

        F = sparse.bmat([[AA, BB], [CC, DD]]).tocsc()

        dYbus_dtSet, _ = self.getdYdt(
            yset="Ybus",
        )

        b_ = np.zeros((self.nV, 0))
        for dYdt in dYbus_dtSet:
            b_ = np.c_[b_, Vh * (dYdt[3:].conj().dot(np.r_[Vsrc, Vh].conj()))]

        b = np.r_[b_.real, b_.imag, np.zeros((self.nPd * 2, self.nT))]

        rslt = spla.spsolve(F, b)
        Mt_a = rslt[: self.nV] + 1j * rslt[self.nV : 2 * self.nV]

        return Mt_a.reshape((self.nV, self.nT))

    def getdYdt(
        self,
        yset="both",
        test=False,
    ):
        """Get dY/dt for each of the voltage regulators, in bus/prm formats.

        Work for this done on 01/05/20 and 03/05/20 in the WB and on notes.

        Inputs
        ---
        yset: 'both', 'Ybus' or 'Yprm', as usual.
        test: testing by building the matrices explicitly

        Returns
        ---
        dYbus_dtSet: units of in Siemens per Tap [NOT in Siemens per dt]
        dYprm_dtSet: units of in Siemens per Tap [NOT in Siemens per dt]

        """
        CtrlMode_ = d.setControlMode(-1)
        i = d.RGC.First
        rgcPrms = {}

        dYbus_dtSet = []
        dYprm_dtSet = []

        while i:
            # Set the transformer and quick error check
            name_ = d.RGC.Transformer
            name = "Transformer." + name_
            d.SetACE(name)
            dt_ = (d.TRN.MaxTap - d.TRN.MinTap) / d.TRN.NumTaps

            if d.RGC.TapWinding != 2:
                raise Exception("Regulator tap not on winding no. 2.")

            # Get the primitive Y without antifloat
            ppm_ = float(d.AE.Properties("ppm_antifloat").Val)
            d.AE.Properties("ppm_antifloat").Val = 0
            d.SLN.Solve()
            d.updateAeYprm(rgcPrms, self.YZidxs)  # get all the yprm crap
            d.AE.Properties("ppm_antifloat").Val = ppm_

            # With the RGC yprm data get dYdt.
            rgcPrm = rgcPrms[name]

            t = d.RGC.TapNumber * dt_
            rgcPrm["dYdtV"] = self.calc_dYdt(rgcPrm, t, "YprmV")
            rgcPrm["dYdtI"] = self.calc_dYdt(rgcPrm, t, "YprmI")

            nYbus = self.nV + 3

            # Get dYbus_dt
            if yset in ["both", "Ybus"]:

                row = []
                col = []
                data = []
                d.updateRowColData(
                    row, col, data, rgcPrm["YZa"], rgcPrm["YZb"], rgcPrm["dYdtV"]
                )
                dYbus_dt = sparse.coo_matrix(
                    (data, (row, col)), shape=(nYbus, nYbus), dtype=complex
                )
                rgcPrm["dYbus_dt"] = dYbus_dt.tocsc()

                # Convert back from 'per unit' taps to actual taps.
                dYbus_dtSet.append(rgcPrms[name]["dYbus_dt"] * dt_)

            # Get dYprm_dt
            if yset in ["both", "Yprm"]:
                nYprm = self.nIprm

                dYprm_dt = sparse.lil_matrix((nYprm, nYbus), dtype=complex)
                vIdxs = [self.YZidxs[yz.upper()] for yz in rgcPrm["vIds"]]

                iIdxs = [
                    self.YprmFlws.index(yz) for yz in self.getFlwNms(rgcPrm, "YprmI")
                ]
                dYprm_dt = magicSlice(dYprm_dt, rgcPrm["dYdtI"], iIdxs, vIdxs)

                rgcPrm["dYprm_dt"] = dYprm_dt.tocsc()

                # Convert back from 'per unit' taps to actual taps.
                dYprm_dtSet.append(rgcPrms[name]["dYprm_dt"] * dt_)

            d.SLN.Solve()

            if test:
                # TEST dYprm_dt
                print(
                    "\n",
                    "-" * 25,
                    "\n",
                    name,
                    "\n",
                    "-" * 25,
                )
                rgcPrms_ = {}

                # Turn off ppm:
                d.SetACE(name)
                ppm_ = float(d.AE.Properties("ppm_antifloat").Val)
                d.AE.Properties("ppm_antifloat").Val = 0

                # Check both the Ybus and Yprm individual elements & matrices.
                for prmType, yptype, mat in zip(
                    ["YprmV", "YprmI"],
                    ["dYdtV", "dYdtI"],
                    ["dYbus_dt", "dYprm_dt"],
                ):
                    Yprm_DT = []
                    Ymat_DT = []
                    for DT in [-1, +2]:
                        # Set the RGC, get Yprm at tap up and tap down:
                        d.RGC.Name = name_
                        d.RGC.TapNumber = d.RGC.TapNumber + DT
                        d.SLN.Solve()
                        d.SetACE(name)
                        d.updateAeYprm(rgcPrms_, self.YZidxs)
                        Yprm_DT.append(rgcPrms_[name][prmType])

                        # Then also get the matrices:
                        if prmType == "YprmV":
                            Ymat_DT.append(d.createYbus(vbs=False)[0].A)
                        elif prmType == "YprmI":
                            _capTap = d.getCapTap()
                            _state = d.getNtwkState()
                            self.getYprmBd(capTap=_capTap)
                            d.setNtwkState(_state)
                            Ymat_DT.append(self.YprmBd.copy().A)

                    # Set the model back to how it started:
                    d.RGC.Name = name_
                    d.RGC.TapNumber = d.RGC.TapNumber - 1
                    d.SetACE(name)
                    d.AE.Properties("ppm_antifloat").Val = ppm_
                    d.SLN.Solve()

                    # Finally print the differences
                    for Yprm_, varType in zip([Yprm_DT, Ymat_DT], [yptype, mat]):
                        dydt = (Yprm_[1] - Yprm_[0]) / (2 * dt_)
                        dydt_ = dydt.copy()
                        dydt_[dydt_ == 0] = 1
                        vldt = (dydt - rgcPrms[name][varType]) / dydt_
                        nzs = np.nonzero(vldt)
                        print("Rerr, " + varType + " \n", vldt[nzs])

            i = d.RGC.Next

        d.setControlMode(CtrlMode_)
        return dYbus_dtSet, dYprm_dtSet

    @staticmethod
    def calc_dYdt(
        rgcPrm,
        t,
        prmType="YprmV",
    ):
        """Convenience function for calculating dYdt as either YprmV or YprmI."""
        yprm = rgcPrm[prmType]

        # Get index splitters:
        if prmType == "YprmV":
            iIdx = len(rgcPrm["YZa"])
        elif prmType == "YprmI":
            iIdx = len(rgcPrm["BDa"])

        vIdx = len(rgcPrm["YZa"])

        y11 = yprm[:iIdx, :vIdx]
        y12 = yprm[:iIdx, vIdx:] * (1 + t)
        y21 = yprm[iIdx:, :vIdx] * (1 + t)
        y22 = yprm[iIdx:, vIdx:] * ((1 + t) ** 2)

        return np.block(
            [
                [0 * y11, -y12 * ((1 + t) ** -2)],
                [-y21 * ((1 + t) ** -2), -2 * y22 * ((1 + t) ** -3)],
            ]
        )

    def test_newTapModel(self, state):
        Mt_a = self.newTapModel(state)
        Mt, Kt, U1t, Ut, Wt = self.createTapModel(state)
        error = np.abs((Mt_a - Mt) / np.max(np.abs(Mt), axis=0))

        plt.plot(error)
        plt.title(self.feeder)
        plt.tight_layout()
        plt.show()

    def ldcUpdate(
        self,
        mdl,
    ):
        """A script to take the linear model 'mdl' and create an 'ldc' model.

        Based on notes from 25/5/20.

        Using information from
        - pages 101-103 of my thesis, and
        - createLtcModel method in lineariseDssModels.py, and
        - ltc_voltage_testing lines 156-217.

        Note there appears to be a slight error in the thesis. (See email rcd)
        """
        # Get the nodes etc for the circuits
        zVlts = d.getRgcZvlts()
        rgcFlws, rgcFlwsIdx = d.getRgcFlwIdx(
            self.YprmFlws,
            self.YZvIdxs,
        )
        rgcNds, rgcNdsIdx = d.getRgcNds(self.YZvIdxs)
        vrgcVlts = d.getRgcVreg()

        # Pull out the current indices
        Wrgc = mdl.W[rgcFlwsIdx]
        crgc = mdl.c[rgcFlwsIdx]
        Mrgc = mdl.M[rgcNdsIdx]
        argc = mdl.a[rgcNdsIdx]

        # Get the voltage and current 'measured' by the regulator
        Mmsrd = Mrgc - vmM(zVlts, Wrgc)
        amsrd = argc - zVlts * crgc

        Kmsrd, bmsrd = self.nrelLinKspd(Mmsrd, amsrd, mdl.state)

        # Run the kron reduction using the conversion matrices
        Ktap = -np.linalg.solve(Kmsrd[:, self.nS :], Kmsrd[:, : self.nS])
        btap = np.linalg.solve(Kmsrd[:, self.nS :], vrgcVlts - bmsrd)

        mdlDict = {"mtype": mdl.mtype + "ldc", "state_": mdl.state_, "state": mdl.state}
        mdlDict["Ktap"] = Ktap
        mdlDict["btap"] = btap
        mdlDict["Wrgc"] = Wrgc
        mdlDict["crgc"] = crgc

        for sns, (fst, _) in self.lmPairs.items():
            snsVal_ = mdl[sns]
            fstVal_ = mdl[fst]
            snsVal = snsVal_[:, : self.nS] + snsVal_[:, self.nS :].dot(Ktap)
            fstVal = fstVal_ + snsVal_[:, self.nS :].dot(btap)

            mdlDict.update({sns: snsVal})
            mdlDict.update({fst: fstVal})
        self.mdlLdc = structDict(mdlDict)

    # -------------- Hosting capacity variance/correlation funcs
    @staticmethod
    def getPmlNsets(A, B, pdfX, cns, nGen):
        """Calculate the number of standard deviations to a constraint.

        Assumes a model of the form

        Y = AX + B[i],

        with X having mean Xmu and covariance matrix Xcorr, for each i of B.

        pdfX should have a method to create Mu & cov.

        Xcov is represented as a tuple (u,v,n), with u the diagonal, v the
        off-diagonal, and n the size of the matrix.

        INPUTS
        ------
        A - a real numpy array of nY x nX
        B - a list of len nLm of real vectors of dimension nY
        Xmu - a real vector of dimension nX
        Xcorr - a tuple of (real,real,int)

        RETURNS
        -------
        Nset - a dict of L, U Nstds, with +ve implying mean outside a
                constraint.
        """

        # First calc diag(A.dot(A)) as this only needs calculating once:
        ATA = calcVar(A)
        nuA = A.dot(np.ones(A.shape[1]))

        Nsets = []
        for i in range(pdfX.meta.nP[0]):
            Nsets.append([])
            # Get the covariance square root
            xmu, Xcov = pdfX.getMuCov(prmI=i, nGen=nGen)
            Xmu = xmu * np.ones(nGen)

            XcovSqrt = calcDp1rSqrt(*Xcov)

            # Calculate the mean and variance
            Yvar = lNet.calcAdotDp1rVar(ATA, nuA, XcovSqrt)
            Ymu_ = A.dot(Xmu)

            # Calculate the number of standard deviations
            for b in B:
                Ymu = Ymu_ + b
                Nset = {}
                for lim, mult in zip(["L", "U"], [1, -1]):
                    if not np.isinf(cns[lim]):
                        # Allow divide by zero:
                        rrs = np.seterr(divide="ignore")

                        Nset[lim] = mult * (cns[lim] - Ymu) / np.sqrt(Yvar)

                        np.seterr(divide=rrs["divide"])
                    else:
                        Nset[lim] = -np.inf * np.ones((A.shape[0]))
                Nsets[-1].append(Nset)
        return Nsets

    def getCnsNstds(
        self,
        pdf,
        pml,
    ):
        """Loop through each constraint and find Nset."""
        Nstds = {}

        for cn, (A_, b_) in self.pmlPairs.items():
            A = pml[A_]
            b = pml[b_]
            Nstds[cn] = lNet.getPmlNsets(A, b, pdf, self.cns[cn], self.nP)

        return Nstds

    @staticmethod
    def calcAdotDp1rVar(ATA, nuA, XcovSqrt):
        """Calculate the variance of AX + B[i], given sqrt(X).

        Is designed to be a fast alternative to

        Ky = dp1rMv(A,XcovSqrt),
        Yvar = calcVar(Ky).

        See those functions for more info as to, e.g., what dp1r looks like.

        Working in WB 18-5-20 (pg 3), validated the same date.

        -----
        INPUTS
        -----
        - ATA = calcVar(A) for the matrix A
        - nuA = A.dot(np.ones(A.shape[1])), also for matrix A
        - XcovSqrt as a d,e,n triple

        """
        d, e, n = XcovSqrt

        a_ = ((d - e) ** 2) * ATA
        b_ = (nuA ** 2) * e * (2 * (d - e) + n * e)

        return a_ + b_


class mlvNet(lNet):
    """A derivative of the basic lNet, designed for large MV-LV systems.

    Based on the decomposition of
    V = Mx + a
    into the form
    V = Mx + CFx + a
    where M is sparse block-diagonal, C and F are 'thin' matrices, to reduce
    the computational overhead.

    Notes.
    - lmPairs and lmSets should override those variables from lNet

    """

    lmPairs = {
        "M1": ["i", "Vmlv", "C", "F"],
        "K1": ["j", "|Vmlv|", "D", "F"],
        # '_K1':['_j','_|Vmlv|','_D','_F'],
        "O": ["h", "V_mv"],
    }

    lmSets = {
        "all": list(lmPairs.keys()),
        "bareMv": [
            "O",
        ],
    }

    caches = dNet.caches
    caches.update(
        {
            "Vmlv": {
                "name": "Vmlv",
                "dn_": "VmlvCache",
                "fn_": "Ymlv_",
                "res_": {
                    "mdl",
                    "ckts",
                    "mlvIdx",
                    "mlvNsplt",
                    "mlvKvbase",
                },
            },
            "cktInfo": {
                "name": "cktInfo",
                "dn_": "cktInfo",
                "fn_": "cktInfo_",
                "res_": {
                    "cktInfo",
                },
            },
        }
    )

    # Set the names of the circuits for figures etc
    tidyCktNames = {
        90: "UG",
        91: "UG/OH, A",
        92: "UG/OH, B",
        93: "OH, A",
        94: "OH, B",
        95: "OH/UG, A",
        96: "OH/UG, B",
    }
    tidyCktNames.update({key - 10: val for key, val in tidyCktNames.items()})

    # cktInfo is a dict of circuit info to save to avoid having to
    # load/reload opendss where possible. Functions which this should allow:
    # - self.state2x
    # - self.xydt2x
    # - self.state2xc
    cktInfoHead = [
        "nPyLds",  # state2x
        "nPyGen",
        "nPdLds",
        "nPdGen",
        "iIdxPhsY",
        "iIdxPhsD",
        "LDS_",
        "GEN_",
        "nV",
        "nT",
        "syIdx",  # xydt2x
        "sdIdx",
        "nPd",
        "nPy",
        "nP",  # state2xc
        "nS",
    ]

    def __init__(
        self,
        frId=39,
        reloadDss=True,
    ):
        """Calls the dNet class with specific values.

        Inputs
        ---
        frId - feeder ID
        reloadDss - whether to call dNet.__init__ to reload opendss etc

        """
        self.frId = frId
        self.setCktFn()
        self.getSln(None)

        C = "cktInfo"
        fn = self.getCacheFn(C)
        if reloadDss:
            # get ckt info
            prmIn = {"yset": "Ybus"}
            dNet.__init__(
                self,
                frId,
                yBdInit=False,
                prmIn=prmIn,
                tests=[],
            )
            self.getCktInfo()
            Res = {"cktInfo": self.cktInfo}
            dNet.saveCache(fn, Res=Res, vbs=False)
        else:
            res = dNet.loadCache(fn, cache=self.caches[C], vbs=False)
            self.cktInfo = res["cktInfo"]
            self.setCktInfo()

    def getCktInfo(
        self,
    ):
        """Populate cktInfo dict attribute using cktInfoHead."""
        self.cktInfo = {val: getattr(self, val) for val in self.cktInfoHead}

    def setCktInfo(
        self,
    ):
        """Set cktInfo dict attribute to self."""
        for key, val in self.cktInfo.items():
            setattr(self, key, val)

    def setAuxCktAttributes(
        self,
    ):
        """Sets a useful derived quantities from ckts.

        Call after getLvCktInfo or after loadMlvMdl.
        """
        self.idxPlv = np.concatenate(self.ckts.LvYZsIdx)
        self.idxQlv = self.idxPlv + self.nP
        self.nPlv = len(self.idxPlv)
        self.mlvNedges = np.r_[0, np.cumsum(self.mlvNsplt)]

    def lineariseSystem(self, state=None, tests=[], saveLin=True, rvl=None):
        """Overloading lineariseSystem for lNet to linearise a network.

        Inputs
        ---
        state   - the state to linearise at
        tests   - a set of tests to run, if wanted, either 'bsc' (basic) or
                'cpf' (continuation power flow) lNet.lineariseSystem, or
                the tests that go into self.linLvCkt
        saveLin - if true, save all of the linear models
        rvl     - the residential load value, in kVA, to flag 1 kW loads to
                (used in linLvCkt).

        Sets attributes
        ---
        self.mdl - the model values in self.lmPairs
        self.ckts et al from getLvCktInfo()
        """
        if state is None:
            state = self.state0

        # Get the medium voltage model Ox + h
        lNet.lineariseSystem(
            self, mtype="fot", tests=tests, linSet="bareMv", state=state
        )

        # Manually update lmSets
        self.mdl.lmSet = self.lmSets["all"]

        # Get the LV circuit info
        self.getLvCktInfo(state=state)
        self.setAuxCktAttributes()

        # Linearise all of the LV circuits to get M1x + CFx + i
        # i = 0
        # lvNet = self.linLvCkt(i,'bare')
        # lvNet,mdl__,= self.linLvCkt(i,'lvFull',tests=[])
        # lvNet,mdl_, = self.linLvCkt(i,'lvFullSqr',tests=[])
        # lvNet,mdl = self.linLvCkt(i,'lvRankFczn',tests=[])
        # lvNet,mdl = self.linLvCkt(i,'lvRankFczn',)

        xx = self.state2x(state)
        xx1 = [xx[idxS] for idxS in self.ckts.LvYZsIdx_S]

        self.mdl.M1 = []
        self.mdl.C = []
        self.mdl.F = []
        self.mdl.i = []

        self.mdl.K1 = []
        self.mdl.D = []
        self.mdl.j = []

        for i in range(self.ckts["N"]):
            lvNet, mdls = self.linLvCkt(
                i, "lvRankFczn", tests=tests, LoadMult=state["LoadMult"], rvl=rvl
            )

            self.lvNet = lvNet

            # F is in both the real and imag models
            self.mdl.F.append(mdls[2])

            # Get the complex model
            self.mdl.M1.append(mdls[0])
            self.mdl.C.append(mdls[1])
            self.mdl.i.append(mdls[3])

            # Get the magnitude model (based on nrelLinKspd)
            yyhat = (
                self.mdl.M1[-1].dot(xx1[i])
                + self.mdl.C[-1].dot(self.mdl.F[-1].dot(xx))
                + self.mdl.i[-1]
            )
            argI = o2o(yyhat.conj() / np.abs(yyhat))

            self.mdl.K1.append((mdls[0] * argI).real)
            self.mdl.D.append((mdls[1] * argI).real)
            self.mdl.j.append(
                np.abs(yyhat)
                - self.mdl.K1[-1].dot(xx1[i])
                - self.mdl.D[-1].dot(self.mdl.F[-1].dot(xx))
            )

        # Reload the DSS Circuit
        self.initialiseDssCkt()

        # Run specified tests (as in the original file)
        if "bsc" in tests:
            self.fastTest()
        if "cpf" in tests:
            self.cpfTest()

        if saveLin:
            C = "Vmlv"
            fn = dNet.getCacheFn(self, C, prms={"LoadMult": self.mdl.state["LoadMult"]})
            data = {
                "mdl": self.mdl,
                "ckts": self.ckts,
                "mlvIdx": self.mlvIdx,
                "mlvNsplt": self.mlvNsplt,
                "mlvKvbase": self.mlvKvbase,
            }
            dNet.saveCache(fn, data, cache=self.caches[C])

    def loadMlvMdl(self, lm=None, _pf=False):
        """Load the MLV model.

        If _pf is input, then also create a fixed power factor model too.
        NB - note though that only unity power factor is implemented!

        """
        if lm is None:
            lm = self.state0["LoadMult"]

        C = "Vmlv"
        fn = dNet.getCacheFn(self, C, prms={"LoadMult": lm})
        res = dNet.loadCache(fn, cache=self.caches[C])
        for key, val in res.items():
            setattr(self, key, val)

        self.setAuxCktAttributes()

        # in addition, add self.mdl.FF for speeding up calculations
        self.mdl.FF = np.concatenate(self.mdl.F)

        if _pf:
            pf = 0.0  # the only implementation we have so far!
            Vlin = self.getVmlvLin(state=self.mdl.state, mSel="K1")
            self.mdl._pf = pf

            N_s = self.mlvNsplt
            self.mdl._K1 = [
                K1[:, :n_s] + pf * K1[:, n_s:] for K1, n_s in zip(self.mdl.K1, N_s)
            ]
            self.mdl._F = [
                F[:, : self.nP] + pf * F[:, self.nP :]
                for F, n_s in zip(self.mdl.F, N_s)
            ]
            self.mdl._D = self.mdl.D

            idxs = np.cumsum(np.r_[0, self.mlvNsplt])
            self.mdl._j = [Vlin[i0:i1] for i0, i1 in zip(idxs[:-1], idxs[1:])]

            self.mdl._xx = self.state2x(self.mdl.state)[: self.nP]
            self.mdl._FF = np.concatenate(self.mdl._F)

    def loadMlvFlatMdl(
        self,
        lm,
        test=False,
        testKw={"pShw": False},
    ):
        """Build a 'flat' MV-LV model for analysis.

        Wraps around loadMlvMdl quite a bit.

        WARNING - presently only updates the model in abs voltages!
        """
        slns = {}
        # First load the flat model and pull our the required matrices
        self.loadMlvMdl(lm=0.0)
        mdlPrms = {
            k: deepcopy(getattr(self.mdl, k))
            for k in [
                "K1",
                "FF",
                "D",
                "F",
            ]
        }

        # Test if wanted
        if test:
            slns[0] = self.cpfTest(lm="K1", **testKw)

        # First load the flat model and pull our the required matrices
        self.loadMlvMdl(lm=lm)
        for k, v in mdlPrms.items():
            setattr(self.mdl, k, v)

        # Update the offset j as appropriate
        V1 = np.abs(d.setNtwkState(self.mdl.state)[3:])
        xx = self.state2x(self.mdl.state)
        xx1 = [xx[idxS] for idxS in self.ckts.LvYZsIdx_S]
        vv1 = [V1[idxV] for idxV in self.ckts.LvYZvIdx_V]
        self.mdl.j = [
            vv1[i]
            - self.mdl.K1[i].dot(xx1[i])
            - self.mdl.D[i].dot(self.mdl.F[i].dot(xx))
            for i in range(self.ckts.N)
        ]

        # Test if wanted
        if test:
            slns[lm] = self.cpfTest(lm="K1", **testKw)

        return slns

    @staticmethod
    def getCtype(fn, lvFrid, ldNo):
        """Get the type ('ukgds' or 'one') of a given load.

        TBH quite cumbersome at this stage - it manually goes and checks the
        filename of the corresponding circuit.
        """
        lvFrid = str(lvFrid)
        dn0 = os.path.dirname(fn)
        dn = join(dn0, "lvNetworks", "_".join(["network", lvFrid, "1", ldNo]))

        fls = os.listdir(dn)
        mn0 = "masterNetwork" + lvFrid
        ndings = ["_pruned_ukgds.dss", "_pruned_one.dss", "_pruned.dss"]
        for nding in ndings:
            if mn0 + nding in fls:
                return nding

    def getLvCktInfo(
        self,
        state=None,
        fn0=None,
    ):
        """Get LV circuit info from the current circuit.

        Assumes that there are a set of 3 phase trasformers off the
        main MV backbone. These transformers are assumed to have the name
        'transformer_...'.

        Returns a structDict self.ckts with the following properties:
        - trnIdx: the index of the transformer in d.TRN
        - lvFrid: the lv fdId base
        - ldNo: the load number on the MV circuit that is being used
        - N: the number of transformers
        - ctype: either 'ukgds' or 'one'

        - YZvIdx: the TRN bus indexes, with respect to self.YZv
        - YZmvIdx: the TRN bus indexes, with respect to self.YZv[self.mvIdx]

        - pwrs: the per-phase power through the TRN
        - V: the complex voltages on the TRN MV side
        - Vbase: the voltage base for V

        - LvYZsIdx: the YZs order for the circuit in the Full circuit
        - LvYZs: the YZs order for the circuit (with the load ID stripped)

        - LvYZvIdx: the indexes of the LV circuit buses in self.YZv
        - LvYZv: the names of the LV circuit buses (with the load ID stripped)

        - lvPrp: the string at the start of all elements in this LV ckt
        - LvYZvIdx_V: as LvYZvIdx but only output voltage indexes
        - LvYZsIdx_S: as LvYZsIdx but with P & Q indexes

        """
        cktKeys = [
            "trnIdx",
            "lvFrid",
            "ldNo",
            "YZvIdx",
            "YZmvIdx",
            "lvPrp",
            "V",
            "Vbase",
            "pwrs",
            "LvYZsIdx",
            "LvYZs",
            "LvYZvIdx",
            "LvYZv",
            "LvYZvIdx_V",
            "LvYZsIdx_S",
            "ctype",
        ]
        cc = mtDict(cktKeys)
        cc["N"] = 0

        state = self.state0 if state is None else state
        fn0 = self.fn if fn0 is None else fn0

        V0 = d.setNtwkState(state)[3:] / self.vKvbase
        i = d.TRN.First
        while i:
            if not d.TRN.Name.split("_")[0] == "transformer":
                # Basic info/updates
                ldNo = d.TRN.Name.split("_")[1][:-1]
                cc["trnIdx"].append(i)
                cc["lvFrid"].append(
                    int(d.TRN.Name.split("_")[0][2:-1]),
                )
                cc["ldNo"].append(ldNo)
                cc["ctype"].append(None)  # getCtype method has been superceded.
                cc["N"] += 1

                # Transformer indexes
                idxs = [self.YZv.index(ldNo + phs) for phs in [".1", ".2", ".3"]]
                YZvMv = vecSlc(self.YZv, self.mvIdx)
                idxsMv = [self.YZv.index(ldNo + phs) for phs in [".1", ".2", ".3"]]
                cc["YZvIdx"].append(idxs)
                cc["YZmvIdx"].append(idxsMv)

                # Circuit state
                cc["V"].append(V0[idxs])
                cc["Vbase"].append(self.vKvbase[idxs])
                cc["pwrs"].append(tp2ar(d.AE.Powers)[:3])

                # Input/output indexes
                lvPrp = "1_" + ldNo + "_"
                nPrp = len(lvPrp)
                cc["lvPrp"].append(lvPrp)
                cc["LvYZsIdx"].append(
                    np.array([i for i, yz in enumerate(self.YZs) if yz[:nPrp] == lvPrp])
                )
                cc["LvYZs"].append([yz[nPrp:] for yz in self.YZs if yz[:nPrp] == lvPrp])

                cc["LvYZvIdx"].append(
                    np.array([i for i, yz in enumerate(self.YZv) if yz[:nPrp] == lvPrp])
                )
                cc["LvYZv"].append([yz[nPrp:] for yz in self.YZ if yz[:nPrp] == lvPrp])

                cc["LvYZvIdx_V"].append(
                    np.array([i for i in cc["LvYZvIdx"][-1] if i in self.sIdx])
                )
                cc["LvYZsIdx_S"].append(
                    np.r_[cc["LvYZsIdx"][-1], cc["LvYZsIdx"][-1] + self.nP]
                )

            i = d.TRN.Next

        self.mlvIdx = np.concatenate([idxV for idxV in cc["LvYZvIdx_V"]])
        self.mlvNsplt = np.array([len(idxs) for idxs in cc["LvYZvIdx_V"]])
        self.mlvKvbase = self.vKvbase[self.mlvIdx]

        self.ckts = structDict(cc)

    def linLvCkt(self, i_, mtype="lvFull", **kwargs):
        """Linearise the i_-th LV circuit of self.ckts.

        If calling 'lvRankFczn', requires a model in dvmvdx for this to be
        already there.

        NB: **ONLY** 'LoadMult' and 'rvl' parameters can be specified in
        terms of the 'state' of the linearization at this point!

        ***SIDE EFFECT***
        - changes the DSS object to be this particular circuit.

        -----
        INPUTS
        -----
        i_: index in self.ckts
        mtype: linearisation method, one of
            - 'bare'
            - 'lvFull'
            - 'lvFullSqr'
            - 'lvRankFczn'

        -----
        KWARGS
        -----
        LoadMult: the LoadMult of the linearization.
        rvl: the residential power value, rvl to pass 1 kW as. (In kW.)
        tests: list, which can contain
        - 'V' to check the voltage at the xfmr is correct
        - 'Sfdr' to check the power drawn from the xfmr is correct
        - 'idxs' to check the LV index orders match the Full circuit
        - 'apx' to check the rough linearisation error for a circuit
        - 'lin' to check the linearisation using a CPF
        - 'fczn' to check the rank factorization code

        """
        tests = kwargs.get("tests", ["V", "Sfdr", "idxs", "apx", "lin", "fczn"])

        if self.ckts["ctype"][i_] == "_pruned_ukgds.dss":
            frId = 250 + self.ckts["lvFrid"][i_]
        elif self.ckts["ctype"][i_] == "_pruned_one.dss":
            frId = 275 + self.ckts["lvFrid"][i_]

        lvNet = lNet(
            frId=frId,
        )
        state0 = deepcopy(lvNet.state0)
        state0["VsrcPu"] = np.abs(self.ckts["V"][i_])
        state0["VsrcNgl"] = np.angle(self.ckts["V"][i_]) * 180 / np.pi
        state0["LoadMult"] = kwargs.get("LoadMult", state0["LoadMult"])

        rvl = kwargs.get("rvl", None)
        if not rvl is None:
            updateFlagState(
                state0, flagVal=1.0, rvl=rvl, lm=state0["LoadMult"], IP=True
            )

        # Linearise the system
        if mtype == "bare":
            lvNet.lineariseSystem("fot", state=state0, linSet="bare", tests=[])
            Mlv = lvNet.mdl.M
            aLv = lvNet.mdl.a
            mdl = [Mlv, aLv]
        elif mtype in ["lvFull", "lvFullSqr", "lvRankFczn"]:
            dmvdx = self.mdl.O[self.ckts["YZmvIdx"][i_]]

            xFull = self.state2x(self.mdl.state)
            xFullY, xFullD, _ = self.x2xydt(xFull)

            lvFullData = {
                "dmvdx": dmvdx,
                "lvIdx": self.ckts["LvYZsIdx_S"][i_],
                "xY": xFullY,
                "xD": xFullD,
                "N": self.nS + self.nT,
                "nPydt": [self.nPy, self.nPd, self.nT],
            }

            Mt = lvNet.newTapModel(state0)

            if mtype == "lvFull":
                MyLv, MdLv, aLv = lvNet.fotLinM(
                    state0,
                    lvFull=True,
                    lvFullData=lvFullData,
                )
                Mlv = self.xydt2x(MyLv, MdLv, Mt)
                mdl = [Mlv, aLv]
            if mtype == "lvFullSqr":
                MyLv, MdLv, aLv = lvNet.fotLinM(
                    state0,
                    lvFullSqr=True,
                    lvFullData=lvFullData,
                )
                Mlv = self.xydt2x(MyLv, MdLv, Mt[lvNet.sIdx])
                mdl = [Mlv, aLv]
            if mtype == "lvRankFczn":
                # Build a model of the form [NB 'i_' passed into the func...!]
                # V = M1x1 + CC*FF*x + i

                # First get the normal square model
                My1, Md1, _ = lvNet.fotLinM(
                    state0,
                    sqr=True,
                )
                M1 = self.xydt2x(My1, Md1, Mt[lvNet.sIdx])

                # Then get the tank factorization stuff
                CC, _, Vh = lvNet.fotLinM(
                    state0,
                    lvRankFczn=True,
                )
                # FF = lvFullData['dmvdx'].conj()
                FF = np.r_[
                    lvFullData["dmvdx"].real,
                    -lvFullData["dmvdx"].imag,
                ]

                x1 = lvNet.state2x(state0)

                i = Vh - M1.dot(x1) - CC.dot(FF.dot(xFull))
                mdl = [M1, CC, FF, i]

        # Error checking & tests:
        if len(tests) > 0:
            V = d.setNtwkState(state0)
            if "V" in tests:
                # Test the voltages at the head of the feeder match
                rerr(V[:3], self.ckts["V"][i_] * self.ckts["Vbase"][i_], p=1)
            if "Sfdr" in tests:
                # Test the powers at the head of the feeder match
                d.TRN.First
                rerr(tp2ar(d.AE.Powers)[:3], self.ckts["pwrs"][i_], p=1)
            if "idxs" in tests:
                # Check the LV circuit voltages and powers are as expected
                print(lvNet.YZv == self.ckts["LvYZv"][i_])
                print(lvNet.YZs == self.ckts["LvYZs"][i_])
            if "apx" in tests and mtype == "bare":
                # Compare the full model sensitivity with circuit only vals.
                MlvFull_ = self.mdl.M[self.ckts["LvYZvIdx"][i_]][
                    :, self.ckts["LvYZsIdx_S"][i_]
                ]
                rerr(lvNet.mdl.M, MlvFull_, p=1)
            if "lin" in tests and mtype == "lvFull":
                # Compare the voltage at the linearization point against the
                # value from opendss (similar to fastTest on v)
                self.initialiseDssCkt()
                d.setNtwkState(self.mdl.state)

                aOld = deepcopy(self.mdl.a)
                Mold = deepcopy(self.mdl.M)
                aNew = deepcopy(self.mdl.a)
                MNew = deepcopy(self.mdl.M)

                rerr(aNew[self.ckts["LvYZvIdx"][i_]], aLv)
                rerr(MNew[self.ckts["LvYZvIdx"][i_]], Mlv)

                MNew[self.ckts["LvYZvIdx"][i_]] = Mlv
                aNew[self.ckts["LvYZvIdx"][i_]] = aLv
                self.mdl.M = MNew
                self.mdl.a = aNew
                self.cpfTest()
                self.mdl.M = Mold
                self.mdl.a = aOld
            if "fczn" in tests and mtype == "lvRankFczn":
                _, mdl_, = self.linLvCkt(
                    i_, "lvFullSqr", tests=[], LoadMult=state0["LoadMult"], rvl=rvl
                )
                in1 = self.ckts["LvYZsIdx_S"][i_]
                Mmdl = mdl[1].dot(mdl[2])
                Mmdl[:, in1] = Mmdl[:, in1] + mdl[0]

                rerr(mdl[-1], mdl_[-1], p=1)
                rerr(Mmdl, mdl_[0], p=1)

        return (
            lvNet,
            mdl,
        )

    def getVmlvSln(self, state):
        """Calculate mlvSln, a 'mlv-ified' version of sln.

        To see which headings go into this, see self.getSln. The main change
        is only in terms of the voltages which are returned being in the
        mlv indexes.
            - Vc, the voltages excluding the source
            - vc, V, v; derived voltages in magnitude/pu etc
            - TP, total power
            - TL, total losses
            - Cnvg, converged flag

        As with mlvCalc, returns a list of values of V for each LV circuit.
        """
        # First, recompile the circuit to the MV one if they don't match
        if self.feeder.lower() != d.DSSCircuit.Name.lower():
            self.initialiseDssCkt()

        # Then get the solution as per the normal way
        self.getSln(state)

        mlvSln = {
            "stateIn": self.sln.stateIn,
            "VsrcMeas": self.sln.VsrcMeas,
            "stateOut": self.sln.stateOut,
            "TP": self.sln.TP,
            "TL": self.sln.TL,
            "Cnvg": self.sln.Cnvg,
            "Vc": self.sln.Vc[self.mlvIdx],
            "V": self.sln.V[self.mlvIdx],
            "vc": self.sln.vc[self.mlvIdx],
            "v": self.sln.v[self.mlvIdx],
        }
        self.mlvSln = structDict(mlvSln)

    def getVmlvHyb(self, muLv, state=None, xx=None, mSel="K1"):
        """Calculate the voltages using the quasi-newton approach.

        -> Sign convention: +ve muLv implies +ve generation (negative load).


        General idea (see notes 23-7-20):
        ----
        - Calculating the jacobian is very slow.
        - Therefore, we sacrifice some speed to improve accuracy by
          running at the MEAN of the new points and then calculating the
          offsets from there.
        - This has the same asymptotic properties as a Jacobian but reduces
          the error significantly, as the error is only in the variations
          in S rather than there also being a mean error.

        Notes + references:
        ----
        - related somewhat to Broyden's method, which is one of the flavours
          of quasi-newton methods in optimization. See 9.6 - 9.7 of Teukolsky
          et al's Numerical Recipes.
        - Also related to the 'chord method'. Discussed in Kelley "Iterative
          Methods for Linear and Nonlinear Equations", 1995, section 5.4.

        Assumptions:
        ----
        - only loads smaller than 2 kW are changed

        Inputs:
        ----
        - state as the new state, XOR with xx
        - xx as the new state, XOR with state
        - muLv as the mean the find 'state' at in both P & Q
        - mSel as the type of voltage to get

        Returns:
        ----
        - Vlin, as the voltage using the hybrid model
        - Vnom, as the voltage at the linearization point
        - Cnvg [bool], to check if the solution converged

        """

        # Firstly: get xx if state passed in
        if xx is None:
            xx = self.state2x(state)

        # Get the updated linear injection. (NB: injections in xx are +ve,
        # hence the sign here and below are the same.)
        dxx = xx
        for idxs in self.ckts.LvYZsIdx:
            dxx[idxs] += 1e3 * muLv.real
            dxx[idxs + self.nP] += 1e3 * muLv.imag

        if mSel[0] == "_":
            dxx = dxx[: self.nP]

        rmax = 2.0  # kW

        # Get the updated nonlinear voltage at muLv
        Vupd0, Cnvg = self.getVupd0(muLv, rmax=rmax)

        if mSel in ["K1", "_K1"]:
            Vupd0 = np.abs(Vupd0)

        # Calculate the hybrid solution
        VlinNom = self.getVmlvLin(state=self.mdl.state, mSel=mSel)
        VlinLin = self.getVmlvLin(xx=dxx, mSel=mSel)
        if xx.ndim == 2:
            VlinNom = o2o(VlinNom)
            Vupd0 = o2o(Vupd0)

        DVlin_ = VlinLin - VlinNom
        Vlin = Vupd0 + DVlin_

        return Vlin, VlinNom, Cnvg

    def getVupd0(
        self,
        muLv,
        rmax=2,
    ):
        """Get the voltage update Vupd at a mean power injections muLv.

        Inputs
        ---
        rmax: If a load is smaller than this then add muLv/lm

        Outputs
        ---
        Vupd0: the voltage at muLv
        Cnvg: convergence flag

        """
        # Get the updated nonlinear injection
        stateNom = deepcopy(self.mdl.state)
        lm = stateNom["LoadMult"]
        for i in range(len(self.LDSidx[0])):
            if np.abs(stateNom["LdsY"][i]) < rmax:
                stateNom["LdsY"][i] = stateNom["LdsY"][i] + (muLv / lm)

        # Calculate the nonlinear solution
        Vupd0 = d.setNtwkState(stateNom)[3:][self.mlvIdx]
        Cnvg = d.SLN.Converged

        return Vupd0, Cnvg

    def getVmlvLin(
        self,
        state=None,
        xx=None,
        mSel="K1",
    ):
        """Calculate V = M_K1*xx1 + C_D*F*xx + a.

        The original version of this proceeded as follows:

        # Version 1
        xx1 = [xx[idxS] for idxS in self.ckts.LvYZsIdx_S]
        dMdlSa = [M_K1.dot(x1) for M_K1,x1 in zip(
                                getattr(self.mdl,mSel),xx1)]
        dMdlSb = [C_D.dot(F.dot(xx)) for C_D,F in zip(
                        getattr(self.mdl,self.lmPairs[mSel][2]),self.mdl.F)]
        V = MdlC + np.concatenate([dA+dB for dA,dB in zip(dMdlSa,dMdlSb)])

        This was replaced with the current code which seems to be 4-5 times
        faster for large circuits.

        NB: if _K1 is called and xx is the shape of K1 (ie self.nS) then it
        returns the output of K1.

        Inputs
        ---
        - state XOR xx to multiply the model by
        - mSel as K1, _K1 or M1.

        """
        if not state is None and not xx is None:
            raise Exception("Pass in state XOR xx, not both.")

        if xx is None:
            xx = self.state2x(state)

        MdlC = np.concatenate(getattr(self.mdl, self.lmPairs[mSel][0]))
        if xx.ndim == 2:
            MdlC = o2o(MdlC)

        if mSel[0] == "_":
            if xx.shape[0] == self.nS:
                print("Running K1")
                return self.getVmlvLin(
                    state=None,
                    xx=xx,
                    mSel="K1",
                )
            elif xx.shape[0] == self.nP:
                if xx.ndim == 2:
                    _xx = o2o(self.mdl._xx)
                else:
                    _xx = self.mdl._xx

                xx = xx - _xx
                FFx = self.mdl._FF.dot(xx)
                IdxSS = self.ckts.LvYZsIdx
        else:
            FFx = self.mdl.FF.dot(xx)
            IdxSS = self.ckts.LvYZsIdx_S

        if xx.ndim == 2:
            V = np.empty((sum(self.mlvNsplt), xx.shape[1]))
        else:
            V = np.empty((sum(self.mlvNsplt),))

        i0 = 0
        for M_K1, idxS, C_D, i in zip(
            getattr(self.mdl, mSel),
            IdxSS,
            getattr(self.mdl, self.lmPairs[mSel][2]),
            range(self.ckts.N),
        ):
            i1 = i0 + self.mlvNsplt[i]
            V[i0:i1] = M_K1.dot(xx[idxS]) + C_D.dot(FFx[i * 6 : (i + 1) * 6])
            i0 = i1

        V = V + MdlC

        return V

    def mlvPlot(self, Vset, ax=None, pKwArgs={}, ff=None, ylm=None):
        """Utility function for plotting Vset.

        Inputs:
        - Vset: an iterable of voltages/objects
        - ax: axes to plot onto
        - pKwArgs: a dict of kwargs to go into 'plot'
        - ff: a function to transform V by (e.g. divide by voltage base)
        - ylm: y-limits (required for vlines)

        """
        if ax is None:
            fig, ax = plt.subplots()

        if ff is None:
            ff = lambda x: x

        plt.plot(ff(Vset), **pKwArgs)

        if ylm is None:
            ylm = ax.get_ylim()

        plt.vlines(
            np.r_[-0.5, np.cumsum(self.mlvNsplt) + 0.5],
            *ylm,
            linestyles="dotted",
            linewidth=0.5,
        )
        ax.set_ylim(ylm)

        ax.set_xlabel("Load index")
        ax.set_ylabel("Voltage, pu")
        plt.tight_layout()
        if self.fPrm["showFig"]:
            plt.show()

    def getMemoryEfficiency(self, mSel="K1", vbs=True):
        """Comparing how memory efficient the decomposition is.

        Requires the model self.mdl to be made already.

        Inputs
        ---
        mSel - M1 or K1/_K1 to select complex or float data sizes.
        """

        if mSel in ["K1", "_K1"]:
            dMul = 1 * 8
        elif mSel == "M1":
            dMul = 2 * 8

        if mSel in ["K1", "M1"]:
            nX = self.nS
        elif mSel == "_K1":
            nX = self.nP

        lmps = self.lmPairs[mSel]
        N1 = sum([MK1.nbytes for MK1 in self.mdl[mSel]]) / 1e3
        N2 = sum([CD.nbytes for CD in self.mdl[lmps[2]]]) / 1e3
        N3 = sum([FF.nbytes for FF in self.mdl[lmps[3]]]) / 1e3
        N = N1 + N2 + N3

        N1_ = sum([M1.shape[0] for M1 in self.mdl.M1])
        N_ = dMul * nX * N1_ / 1e3

        if vbs:
            print(
                f"\nAll M1 sizes: {N1}k\nAll C size: {N2}k"
                + f"\nAll F size:{N3}k\n- Total size of decomposition: {N}k"
            )

            print(
                f"\n- Size of full model: {N_}k"
                + f"\n\n---> Memory ratio: {100*N/N_:.2f} %"
            )

        return N, N_

    def getTryCktN(
        self,
        mSel="K1",
    ):
        """Get the theoretical best no. of circuits.

        Interestingly, the value calculated is independent of the second
        dimension of decomposition.

        See WB 27/7/20.

        Inputs
        ---
        mSel - either K1 or _K1 (changes the n_try value but not N_try)

        Returns
        ---
        N_try - best no. circuits in theory
        n_try - corresponding memory footprint

        """
        m = sum([M1.shape[0] for M1 in self.mdl.M1])
        if mSel == "K1":
            n = self.nS
        elif mSel == "_K1":
            n = self.nP

        bytesPerVal = 8
        N_try = np.sqrt(m / 6)  # optimal

        n_try = bytesPerVal * ((m * n / N_try) + 6 * m + 6 * N_try * n) / 1e3

        return N_try, n_try

    def getThryEta(self, mSel="K1", vbs=True):
        """Calculate the theoretical computational efficiency.

        Note that the memory and flop efficiencies are the same!
        """
        # Get the memory efficiency values
        N_try, n_try = self.getTryCktN(mSel)
        n_act, n_fll = self.getMemoryEfficiency(mSel=mSel, vbs=False)

        eta_act_fll = n_fll / n_act

        if vbs:
            print(
                f"\nMEMORY\n---\nTheoretic: {n_try}k,"
                + "\nActual:{n_act},\nFull:{n_fll}\n"
            )
            print(f"Speedup, (estimated): {n_fll/n_act:.2f}\n")
            print(
                f"CKT_N\n---\nTheoretic Nckt: {N_try:.1f},"
                + f"\nActual N:{self.ckts.N}"
            )

        return N_try, n_try, n_act, n_fll, eta_act_fll

    def getRndX(
        self,
        pp=3,
        frac=0.1,
        nSc=1,
        reseed=False,
        method="nom",
    ):
        """Method to get a set of values of x for subsequent MC runs.

        Parts of this are based on hcDraws.

        Inputs
        ---
        pp - float or list of floats, for the powers, in kW
        frac - the fraction of demands with power pp
        nSc - the number of scenarios (cols of xx)
        reseed - bool - set to True to reseed the random no. generator
        method - one of:
         (i) 'nom', with all loads modelled as binomial with p=frac
         (ii) '40%', with 40% loads 3 kW and the rest a mix of 1 & 6 kW
         (iii) '0-1', where 10% of LV circuits are selected
         (iv) '0-3', as above, but 30%.
         (v) 'X__', as 'nom' but with X kW loads
         (vi) 'Xpf', as 'nom' but with X kW loads at 0.95 pf lagging


        Returns
        ---
        xx - a set of values of x
        muLv - the mean power injection of the LV buses as P + jQ [in kW]

        Assigns
        ---
        self.rngs, if reseed (or not existing)
        self.xx0, as the value of xx at self.mdl.state

        """

        # Seed the generator, if wanted
        if not hasattr(self, "rngs") or reseed:
            self.rngs = rngSeed()

        if not hasattr(self, "xx0"):
            self.xx0 = o2o(self.state2x(self.mdl.state))

        if method[1:] == "__" and float(pp) != float(method[0]):
            print(f"Updating pp to X for X__ mode, X = {method[0]} kW")
            pp = float(method[0])

        if method[1:] == "pf":
            print(f"Updating pp to X for Xpf mode, X = {method[0]}")
            pp = float(method[0]) * (1 + 1j * pf2kq(0.95))

        # Initialise xx as this is used in all of the methods
        xx = np.zeros((self.nS, nSc))

        if method == "nom" or method[1:] in ["__", "pf"]:
            bnSmpl = self.rngs.binomial(1, frac, size=(self.nPlv, nSc))
            xx[self.idxPlv] = -bnSmpl * pp.real * 1e3
            xx[self.idxQlv] = -bnSmpl * pp.imag * 1e3
            muLv = frac * pp + 0j
        elif method in [
            "40%",
            "20%",
            "60%",
        ]:
            # See WB 3/8/20 for derivation of these
            f3 = 0.01 * int(method[:2])
            f6 = 0.4 * (1 - f3)
            f1 = 0.6 * (1 - f3)
            pf6 = 0.9  # assume 0.9 pf 6 kW loads

            # Get the splitting integers
            int1 = hcDraws.frac2int(
                f1,
                self.nPlv,
            )
            int3 = hcDraws.frac2int(
                f3,
                self.nPlv,
            )
            int6 = self.nPlv - int3 - int1

            # Draw the location 'types'
            prms = hcDraws.genPermutation(
                self.nPlv,
                nSc,
            )
            set1 = prms < int1
            set3 = (prms >= int1) * (prms < (int3 + int1))
            set6 = prms >= (int1 + int3)

            # Draw the demand locations
            pSet = [
                -1e3 * pp * self.rngs.binomial(1, frac, size=(ii * nSc))
                for pp, ii in zip([1, 3, 6], [int1, int3, int6])
            ]
            q6 = pSet[-1] * pf2kq(pf6)

            # Set the demands
            xxPlv = np.zeros((self.nPlv, nSc))
            for setsel, psel in zip(
                [set1, set3, set6],
                pSet,
            ):
                xxPlv[setsel] = psel

            xxQlv = np.zeros((self.nPlv, nSc))
            xxQlv[set6] = q6

            xx[self.idxPlv] = xxPlv
            xx[self.idxQlv] = xxQlv
            muLv = frac * ((f3 * 3 + f6 * 6 + f1 * 1) + 1j * (f6 * 6 * pf2kq(pf6)))

        elif method in ["0-1", "0-3"]:
            if method == "0-1":
                # fckt = 0.1
                fckt = 0.107
            elif method == "0-3":
                # fckt = 0.3
                fckt = 0.333

            # First select the circuits
            prms = hcDraws.genPermutation(
                self.ckts.N,
                nSc,
            )
            intN = hcDraws.frac2int(
                fckt,
                self.ckts.N,
            )
            fcktTru = intN / self.ckts.N

            setN = prms < intN

            idxPset = [
                np.concatenate(vecSlc(self.ckts.LvYZsIdx, cktIdx)) for cktIdx in setN.T
            ]
            idxPsetN = [len(idxP) for idxP in idxPset]

            for (i, idxP), nP in zip(enumerate(idxPset), idxPsetN):
                if frac / fcktTru >= 1:
                    bnSmpl = np.ones((nP,), dtype=int)
                else:
                    bnSmpl = self.rngs.binomial(1, frac / fcktTru, size=(nP,))

                xx[idxP, i] = -bnSmpl * pp * 1e3

            if frac / fcktTru >= 1:
                muLv = fcktTru * pp + 0j
            else:
                muLv = frac * pp + 0j

        # Finally, add the nominal demand back on.
        xx += self.xx0
        return xx, muLv

    def getNset(
        self,
        Vpu,
        DVlin,
        Vp,
        Vm,
        DVp,
        nSc,
    ):
        """Calculate the indexes where there are voltage violations.

        Returns EITHER Nset or Nset_, depending on how many violations there
        are.

        """

        # mask: 'if any bad, record bad'
        mask = (Vpu.T > Vp) + (Vpu.T < Vm) + (DVlin.T > DVp)
        if (np.sum(mask) / nSc) < (self.nP // 2):
            Nset = [np.where(rr)[0].astype("int16") for rr in mask]
            Nset_ = np.nan
        else:
            # mask: 'if all good, record good'
            mask = (Vpu.T < Vp) * (Vpu.T > Vm) * (DVlin.T < DVp)
            Nset = np.nan
            Nset_ = [np.where(rr)[0].astype("int16") for rr in mask]

        return Nset, Nset_

    def vAll2vLv(self, Vlv):
        """Convert a list of Vlv to a list of V in each LV circuit."""
        Vdcmp = []
        for i0, i1 in zip(self.mlvNedges[:-1], self.mlvNedges[1:]):
            Vdcmp.append(Vlv[i0:i1])

        return Vdcmp

    @staticmethod
    def fridlm2id(frId, lm):
        """Convert frid + lm to a unique ID. as f'{frId}_{lm}'."""
        return f"{frId}_{lm}"

    @staticmethod
    def processAllResults(fn, Vp, Vm, DVp):
        """Process the results files of buildAllResults in workflowMixergy.

        Inputs
        ---
        fn - the results file name
        Vp, Vm, DVp - the max, min voltages and voltage deviation limits

        Returns
        ---
        rr - the results structDict
        vltnsAll - the violations of all circuits (before mashing lo + hi)
        vltns - the violations per circuit (including lo + hi)

        """
        with open(fn, "rb") as file:
            rr = structDict(pickle.load(file))

        # Get the violations from the data
        vltnsAll = {
            key: [
                np.any(np.c_[vmax > Vp, vmin < Vm, dvmax > DVp], axis=1)
                for [vmax, vmin, dvmax] in vals
            ]
            for key, vals in rr.vltnsIdvl.items()
        }

        vltns = {}
        for fridA, fridB in zip(rr.fridSetA, rr.fridSetB):
            kkA = mlvNet.fridlm2id(fridA, rr.lmA)
            kkB = mlvNet.fridlm2id(fridB, rr.lmB)

            vltns[fridA] = [
                sum(np.any(np.c_[vvA, vvB], axis=1)) / rr.nSc
                for vvA, vvB in zip(vltnsAll[kkA], vltnsAll[kkB])
            ]

        return rr, vltnsAll, vltns


# =================================== CLASS: hcDraws
class hcDraws:
    """

    Based on hdPdfs on previous work
    """

    # 0,1,2 as locked, LDC and decoupled models.
    circuitK = {
        0: {
            "eulv": 1.8,
            "usLv": 5.0,
            "13bus": 4.8,
            "34bus": 5.4,
            "123bus": 3.0,
            "8500node": 1.2,
            "epri5": 2.4,
            "epri7": 2.0,
            "epriJ1": 1.2,
            "epriK1": 1.2,
            "epriM1": 1.5,
            "epri24": 1.5,
        },
        1: {"13bus": 6.0, "34bus": 8.0, "123bus": 3.6},
        2: {
            "8500node": 2.5,
            "epriJ1": 6.0,
            "epriK1": 1.5,
            "epriM1": 1.8,
            "epri24": 1.5,
        },
    }

    def __init__(self, feeder, dMu=None, **kwargs):
        """Initialise the hcDraws.

        Four different models are implemented:
        - gammaFrac
            Parameters: np.array([frac0,frac1,...])
        - gammaXoff
            Parameters: np.array([[frac0,xOff0],[frac1,xOff1],...])
        - gammaWght
            Parameters: np.array([k0,k1,...])
        - gammaFlat
            Parameters: np.array([k0,k1,...])

        ====
        kwargs
        ====
        nMc: number of MC runs
        pdfName: options are as above
        slrPrm: solar params, requiring gamma shape parameters k, th
        rndSeed: random seed integer as 32 bit unsigned integer
        netModel: model setting for choosing circuitK (only Wght/Flat models)
        prms: a set of parameters to go through for sequential analysis
        dMu: 'mean parameter' value, usually [?]

        """

        # Set random seed, as a 32 bit unsigned integer (up to 2**32)
        self.rndSeed = kwargs.get("rndSeed", 0)
        pdfName = kwargs.get("pdfName", "gammaFrac")

        # Solar parameters from plot_california_pv.py
        slrPrm = kwargs.get("slrPrm", {"k": 4.21423544, "th_kW": 1.2306995})
        nMc = kwargs.get("nMc", 100)

        if pdfName in ["gammaWght", "gammaFlat"]:
            netModel = kwargs.get("netModel", 0)
            self.dMu = kwargs.get("dMu", 0.02)

            mu_k = circuitK[netModel][feeder] * np.arange(self.dMu, 1.0, self.dMu)
            prms = kwargs.get("prms", np.array([slrPrm["k"]]))
            meta = {"slrPrm": None}
        elif pdfName in ["gammaFrac", "gammaXoff"]:
            self.dMu = kwargs.get("dMu", 1.0)
            mu_k = np.array([self.dMu])
            if pdfName == "gammaFrac":
                # if none, use values from santoso paper
                prms = kwargs.get("prms", np.arange(0.02, 1.02, 0.02))
            elif pdfName == "gammaXoff":
                prms = kwargs.get("prms", np.array([[0.50, 8]]))
            meta = {"slrPrm": slrPrm}

        meta.update(
            {
                "name": pdfName,
                "prms": prms,
                "mu_k": mu_k,
                "nMc": nMc,
                "nP": (len(prms), len(mu_k)),
            }
        )
        self.meta = structDict(meta)

    @staticmethod
    def halfLoadMean(scale, xhyN, xhdN):
        """Not actually sure what this does for now?

        Scale suggested as: LM.scaleNom = lp0data['kLo'] - lp0data['k']
        """

        roundI = 1e0
        # latter required to make sure that this is negative vvvv
        Mu0_y = (
            -scale
            * roundI
            * np.round(
                xhyN[: xhyN.shape[0] // 2] / roundI - 1e6 * np.finfo(np.float64).eps
            )
        )
        Mu0_d = (
            -scale
            * roundI
            * np.round(
                xhdN[: xhdN.shape[0] // 2] / roundI - 1e6 * np.finfo(np.float64).eps
            )
        )
        Mu0 = np.concatenate((Mu0_y, Mu0_d))

        Mu0[Mu0 > (10 * Mu0.mean())] = Mu0.mean()
        Mu0[Mu0 > (10 * Mu0.mean())] = Mu0.mean()
        return Mu0

    def getMuCov(self, **kwargs):
        """Get the mean and

        Only gammaWght and gammaFrac have been implemented. gammaWght needs
        the linear model to be loaded in.

        Based on getMuCov from linSvdCalcs.

        RETURNS
        - Mu as mean power injection, in WATTS
        - Cov as (var,cov,nGen,) tuple OR (var,), in WATTS-SQUARED (req nGen)

        Note that there is a non-linear mapping from real numbers to rational
        fractions when using gammaFrac which mostly affects systems with
        small numbers of generators (e.g., the 13 bus).

        -----
        kwargs [pdf type]
        -----
        [gammaWght]
        - LM: the lin model (not used for a while...)
        [gammaFrac]
        - prmI: the index of the prms chosen
        - nGen: the number of generators

        """
        if self.meta.name == "gammaWght":
            LM = kwargs["LM"]
            # Both of these in W
            Mu = hcDraws.halfLoadMean(LM.loadScaleNom, LM.xhyNtot, LM.xhdNtot)
            Sgm = Mu / np.sqrt(self.meta.prms[0])
            Cov = None
        if self.meta.name == "gammaFrac":
            prmI = kwargs["prmI"]
            nGen = kwargs["nGen"]

            # Get the 'true' rational fraction
            frac = self.frac2int(self.meta.prms[prmI], nGen) / nGen

            k, th = self.meta.slrPrm.values()
            MuPv = k * th * 1e3
            SgmPv = np.sqrt(k) * th * 1e3
            Mu = frac * MuPv

            # see FrÃ¼hwirth-Schnatter chapter 1
            var = frac * (MuPv ** 2 + SgmPv ** 2) - Mu ** 2
            if nGen is None:
                Cov = (var,)
            else:
                covar = (MuPv ** 2) * frac * (frac - 1) / (nGen - 1)
                Cov = (
                    var,
                    covar,
                    nGen,
                )

        return (
            Mu,
            Cov,
        )

    @staticmethod
    def frac2int(frac, nGen):
        """Calculate the whole no. of loads given a 'fraction' frac."""
        return np.ceil(frac * nGen).astype(int)

    def genPdfMcSet(self, nMc, prmI, getMcU=False, **kwargs):
        """Generate a set of Monte Carlo draws for MC analysis.

        nMc: no. MC runs
        prmI: choose which parameter index of prms to get
        getMcU: bool


        -----
        kwargs
        -----
        Mu0: Generation mean - only used in gammaXoff.
        nGen: number of PV generators

        Returns
        -----
        pdfMc  - the raw output
        pdfMcU - the output, but with zero mean, unit variance

        """
        Mu0 = kwargs.get("Mu0", [])
        nGen = kwargs.get("nGen", None)

        if self.meta.name == "gammaWght":
            k = self.meta.prms[prmI]
            pdfMc0 = np.random.gamma(k, 1 / np.sqrt(k), (nGen, nMc))
            pdfMc = vmM(1e-3 * Mu0 / np.sqrt(k), pdfMc0)  # in kW
            if getMcU:
                pdfMcU = pdfMc0 - np.sqrt(k)  # zero mean, unit variance

        elif self.meta.name == "gammaFlat":
            k = self.meta.prms[prmI]
            Mu0mean = Mu0.mean()
            # pdfMc0 = np.random.gamma(shape=k,scale=1/np.sqrt(k),
            # size=(nGen,nMc))
            # pdfMc = (1e-3*Mu0mean/np.sqrt(k))*pdfMc0
            pdfMc0 = np.random.gamma(
                shape=k,
                scale=(1e-3 * Mu0mean / np.sqrt(k)) / np.sqrt(k),
                size=(nGen, nMc),
            )
            if getMcU:
                # pdfMcU = pdfMc0 - np.sqrt(k) # zero mean, unit variance
                # zero mean, unit variance
                pdfMcU = (pdfMc0 / (1e-3 * Mu0mean / np.sqrt(k))) - np.sqrt(k)

        elif self.meta.name == "gammaFrac":
            nDraw = self.frac2int(self.meta.prms[prmI], nGen)

            if not hasattr(self, "_nMc") or self._nMc != nMc:
                self.genPrmtn = self.genPermutation(nGen, nMc)
                slrPrm = self.meta.slrPrm
                self.genGamma = np.random.gamma(
                    shape=slrPrm["k"], scale=slrPrm["th_kW"], size=(nGen, nMc)
                )
                self._nMc = nMc

            pdfMc = self.genGamma * (self.genPrmtn < nDraw)

            if getMcU:
                pdfMeans = np.mean(pdfMc)  # NB these are uniformly distributed
                pdfStd = np.std(pdfMc)  # NB these are uniformly distributed
                pdfMcU = (pdfMc - pdfMeans) / pdfStd

        elif self.meta.name == "gammaXoff":
            slrPrm = self.slrPrm

            frac = self.meta.prms[prmI][0]
            xOff = self.meta.prms[prmI][1]

            genIn = np.random.binomial(1, frac, (nGen, nMc))
            pGen = np.random.gamma(
                shape=slrPrm["k"], scale=slrPrm["th_kW"], size=(nGen, nMc)
            )
            pGen = np.minimum(pGen, xOff * np.ones(pGen.shape))
            pdfMc = pGen * genIn

            if getMcU:
                pdfMeans = np.mean(pdfMc)  # NB these are uniformly distributed
                pdfStd = np.std(pdfMc)  # NB these are uniformly distributed
                pdfMcU = (pdfMc - pdfMeans) / pdfStd

        if not getMcU:
            pdfMcU = None
        return pdfMc, pdfMcU

    @staticmethod
    def genPermutation(nGen, nMc, seed=0):
        rng = default_rng(seed=seed)
        permutation = np.zeros((nGen, nMc), dtype=int)
        for i in range(nMc):
            idxs = rng.permutation(
                range(nGen),
            )
            permutation[:, i] = idxs

        return permutation


# Some scripting functions for workflowShc -----------------
def runFull(feeder, lms, css):
    self = lNet(
        feeder,
    )
    pdf = hcDraws(self.feeder, nMc=css["nMc"], prms=css["prm"])
    dssHc = self.runMc(pdf, "dssMc", lms=lms, allVsave=True)


def testFot(feeder):
    self = lNet(
        feeder,
    )
    self.lineariseSystem("fot", state=d.getNtwkState())


def testFpl(feeder):
    self = lNet(
        feeder,
    )
    self.lineariseSystem("fpl", state=d.getNtwkState())


def pltCns(self, pdf, lms, dataSets, **kwargs):
    """

    kwargs
    ----
    clrs: ['C0-','C1--','C2-.']
    dataLbls: ['dssHc','LinHc','PrgHc']
    """
    dataLbls = kwargs.get("dataLbls", ["dssHc", "LinHc", "PrgHc"])
    clrs = kwargs.get("clrs", ["C0-", "C1--", "C2-."])

    fig, axs = plt.subplots(
        nrows=self.cns.N, ncols=2 * len(lms), sharex=True, sharey=True, figsize=(11, 7)
    )
    axs = axs.flatten()
    for kw, ax, i in zip(self.cResO, axs, range(len(self.cResO))):
        for data, lbl, clr in zip(dataSets, dataLbls, clrs):
            ax.plot(100 * pdf.meta.prms, data.fsFr[:, i], clr, label=lbl)

        ax.set_xlabel("Parameter val")
        ax.set_ylabel("% violations")
        ax.set_ylim((-2, 102))
        ax.set_title(kw)

    axs[0].legend()
    plt.tight_layout()
    plt.show()


def pltCnsPair(self, pdf, lms, dataSets, **kwargs):
    """

    kwargs
    ----
    clrs: [['C0','C5'],['C1','C6']]
    dataLbls: ['dssHc','LinHc']
    """
    dataLbls = kwargs.get("dataLbls", ["dssHc", "LinHc"])
    clrPrs = kwargs.get("clrs", [["C2", "C0"], ["C1", "C3"]])

    mults = [1, -1]

    fig, axs = plt.subplots(ncols=2 * len(lms) * self.cns.N, sharey=True)
    axs = axs.flatten()
    for kw, ax, i in zip(self.cResO, axs, range(len(self.cResO))):

        for data, lbl, clrs, m in zip(dataSets, dataLbls, clrPrs, mults):
            ax.plot(m * data.fsFr[:, i], 100 * pdf.meta.prms, "k", linewidth=0.6)
            ax.plot([0, 0], [0, 100], "k:", linewidth=0.6)

            ax.fill_betweenx(
                100 * pdf.meta.prms,
                m * data.fsFr[:, i],
                color=clrs[1],
                alpha=0.6,
                label=lbl,
            )
            ax.fill_betweenx(
                100 * pdf.meta.prms,
                m * data.fsFr[:, i],
                np.ones(pdf.meta.nP[0]) * m * 100,
                color=clrs[0],
                alpha=0.2,
            )

        ax.set_xlabel(kw, rotation=90, fontsize="small")
        ax.set_xlim((-102, 102))
        ax.set_xticks((-100, 0, 100))
        ax.set_xticklabels(("", "", ""), fontsize="small")

    axs[0].set_ylim((-0, 100))
    axs[0].set_ylabel("PV Penetration, %")
    axs[-1].legend(title=self.feeder, loc=(1.2, 0.4), fontsize="small")
    plt.subplots_adjust(wspace=0.2, top=0.95, bottom=0.35, right=0.82)

    plt.annotate("Constraint type", (0.35, 0.01), xycoords="figure fraction")
    # plt.tight_layout()
    plt.show()


def testLin(fdrT, cs):
    N = 3

    self = lNet(
        fdrT,
    )
    d = self._d
    pdf = hcDraws(self.feeder, nMc=cs["nMc"], prms=cs["prm"])
    nSc = pdf.meta.nP[0]
    Mu = pdf.getMuCov(prmI=np.arange(nSc), nGen=self.nP)[0]
    self.allGenSetup()

    stateSolve = self.state0.copy()
    stateSolve["LoadMult"] = 0.2
    stateSolve["GenY"] = [(1 + 0 * 1j) * Mu[nSc // 2] / 1e3] * self.nPy
    stateSolve["GenD"] = [(1 + 0 * 1j) * Mu[nSc // 2] / 1e3] * self.nPd
    d.setNtwkState(stateSolve)
    state_ = d.getNtwkState()

    txt = "self.lineariseSystem('fpl',[],state=state_,)"
    zxc = timeit.Timer(txt, globals={"state_": state_, "self": self}).timeit(N)

    print("\n------\n", self.feeder, "\n------\nnV, Time:", self.nV, zxc / N, "\n\n")


def test_getPmlNsets(self, pdf, lms):
    # Testing getPmlNsets

    self.runMc(pdf, "linMc", lms=lms)  # required for cro.
    pml = self.processLinMdl(lms)
    Nstds = self.getCnsNstds(
        pdf,
        pml,
    )

    idx = -1
    for cro in self.cResO:
        i = lms.index(float(cro[1]))
        vals = Nstds[cro[0]][idx][i][cro[2]]
        print(cro, max(vals))

    lm = 0.2
    cn = "vMv"
    A_, b_ = self.pmlPairs[cn]
    i = pml.lm.index(lm)
    A = pml[A_]
    b = pml[b_][i]

    idx = -1
    Pgen = pdf.genPdfMcSet(nMc=1000, prmI=idx, nGen=self.nP)[0] * 1e3
    PgenMu, PgenCov = pdf.getMuCov(prmI=idx, nGen=self.nP)
    Pmu = PgenMu * np.ones(self.nP)

    Nset = self.getPmlNsets(A, b, pdf, self.cns[cn], self.nP)

    Y = (A.dot(Pgen).T + b).T
    vMean = np.mean(Y, axis=1)
    vStd = np.std(Y, axis=1)
    VpCns = np.ones(self.nVmv) * self.cns.vMv.U

    plt.plot(VpCns, "_", markersize=2)
    plt.plot(vMean, ".", markersize=2)
    plt.plot(vMean + 10 * vStd, "k_", markersize=1)
    plt.plot(vMean - 10 * vStd, "k_", markersize=1)
    plt.show()

    # Also: testing the fast calc method: calcAdotDp1rVar
    XcovSqrt = calcDp1rSqrt(*PgenCov)
    Yvar = self.calcAdotDp1rVar(calcVar(A), A.dot(np.ones(A.shape[1])), XcovSqrt)
    print(PgenCov)
    print(XcovSqrt)
    Ky = dp1rMv(A, XcovSqrt)
    Yvar2 = calcVar(Ky)
    rerr(Yvar, Yvar2)
