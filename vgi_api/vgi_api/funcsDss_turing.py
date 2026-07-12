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
#
# DIFFERENCES FROM THE ORIGINAL (v0) funcsDss_turing.py
# -----------------------------------------------------
# One change: dssIfc.__init__ detected the dss-python engine with
# `type(DSSObj) is dss.dss_capi_gr.IDSS`; that module path was removed in
# dss-python 0.14, so the import-time check failed on every modern release.
# It is now `isinstance(DSSObj, dss.IDSS)`, which works from 0.12 onward.
# See the CHANGE comment in dssIfc.__init__ and CHANGES.md §8. Behaviour is
# identical for the packaged engine (comFlag stays False).

import numpy as np
import os, time
from scipy import sparse, linalg
import scipy.sparse.linalg as spla
import matplotlib.pyplot as plt
from matplotlib import cm
from pprint import pprint
import dss
from copy import deepcopy

from .funcsMath_turing import tp2ar, s_2_x, vecSlc, vmM, mvM, sparseSvty, rerr
from .funcsPython_turing import structDict

seq2phsB = np.array([1, np.exp(1j * np.pi * 4 / 3), np.exp(1j * np.pi * 2 / 3)])
seq2phs = np.r_[[seq2phsB ** 0, seq2phsB ** 1, seq2phsB ** 2]]
phs2seq = np.linalg.inv(seq2phs)

# Preamble END ---


def dirr(obj):  # useful for finding properties of DSS Com interface objects
    pprint(obj._prop_map_get_.keys())


class dssIfc:
    """An simple opendss interface for python.


    NOTE - for compactness the class convention here is to use
    'd' in place of the 'self' convention when calling methods.

    Also: only 'interfaces' are appropriate - it is not sensible to
    use attributes (eg YNodeOrder) as these are dependent on the
    circuit.

    Of course, the list here is not exhaustive though so do
    add more of these
    """

    objParams = {"Text": "DSSText", "ActiveCircuit": "DSSCircuit"}
    cktParams = {
        "Solution": "SLN",
        "ActiveBus": "ABE",
        "ActiveCktElement": "ACE",
        "ActiveElement": "AE",
        "SetActiveElement": "SetACE",
        "SetActiveBus": "SetABE",
        "Loads": "LDS",
        "Generators": "GEN",
        "Capacitors": "CAP",
        "Lines": "LNS",
        "RegControls": "RGC",
        "CapControls": "CPC",
        "Transformers": "TRN",
        "Vsources": "Vsrcs",
        "PDElements": "PDE",
        "Topology": "TGY",
        "Settings": "SET",
        "Meters": "MTR",
    }

    def __init__(d, DSSObj):
        d.DSSObj = DSSObj
        # CHANGE(dss-python >= 0.14 compatibility): the type check used
        # `dss.dss_capi_gr.IDSS`, a module that dss-python renamed away in
        # 0.14 — making that release line fail at import. IDSS has been
        # importable from the package root in every version from 0.12
        # onward, and isinstance() also tolerates subclasses.
        from dss import IDSS as _IDSS

        d.comFlag = not isinstance(d.DSSObj, _IDSS)
        for key, val in d.objParams.items():
            setattr(d, val, getattr(d.DSSObj, key))
        for key, val in d.cktParams.items():
            setattr(d, val, getattr(d.DSSCircuit, key))

    def resetDss(d):
        # Use this if you want to load in a new circuit.
        d.DSSObj.ClearAll()
        d.DSSObj.Reset()

    def getObjName(d, dObj):
        """Find the type of object dObj."""
        name = None
        for key, val in d.cktParams.items():
            if dObj == getattr(d.DSSCircuit, key):
                name = val
        return name

    def openCktInfo(
        d,
    ):
        """Simple wrapper to open the spreadsheet of circuit info."""
        from funcsPython_turing import fn_ntwx

        os.startfile(os.path.join(fn_ntwx, "distribution_circuits.xlsx"))

    # ==================== admittance matrix funcs
    def getYmat(
        d,
        capTap=None,
        vbs=False,
    ):
        """Build the admittance matrix initialised at capTap.

        Uses the great new GetCompressedYMatrix function from funcs_dss.

        Is based on buildYmat. Does not get the primitive admittance
        matrices for all elements.

        """
        if vbs:
            print("Building Ybus...\n", time.process_time())

        prmVrb = d.ybusPrimer()

        # set the taps and caps
        if not capTap is None:
            d.setCapTap(capTap)

        d.SLN.Solve()
        Ybus = sparse.csc_matrix(d.DSSObj.YMatrix.GetCompressedYMatrix())
        d.ybusReenable(*prmVrb)

        if vbs:
            print("Ybus built.\n", time.process_time())
        return Ybus, d.getCapPos()[0], d.getTapPos()

    def buildYmat(
        d,
        obj,
        capTap=None,
        YZidxs=None,
        vbs=False,
    ):
        """Build the admittance matrix, initiliased at capTap.

        Set obj=d.PDE to get the full Ymat, use d.CAP, d.TRN etc for other
        element types.

        NOTE that the control mode is NOT changed so taps/caps may change
        (hence the cap/tap positions are returned).

        Returns
        ---
        - the admittance matrix
        - the primitive admittance dict
        - the output cap position
        - the output tap position.

        """
        if YZidxs is None:
            YZidxs = {bus: i for i, bus in enumerate(d.DSSCircuit.YNodeOrder)}
        if vbs:
            print("Building Ybus...\n", time.process_time())

        prmVrb = d.ybusPrimer()
        # set the taps and caps
        if not capTap is None:
            d.setCapTap(capTap)

        d.SLN.Solve()

        row = []
        col = []
        data = []
        Yprm = {}

        ii = obj.First
        while ii:
            # First: if going through regcontrols, specify the xfmr instead
            if d.AE.Name.split(".")[0].lower() == "regcontrol":
                d.SetACE("Transformer." + obj.Transformer)

            YZa, YZb, YprmV = d.updateAeYprm(Yprm, YZidxs)

            d.updateRowColData(row, col, data, YZa, YZb, YprmV)

            ii = obj.Next
        nYbus = d.DSSCircuit.NumNodes
        Ybus = sparse.coo_matrix(
            (data, (row, col)), shape=(nYbus, nYbus), dtype=complex
        )
        Ybus = Ybus.tocsc()

        d.ybusReenable(*prmVrb)

        if vbs:
            print("Ybus built.\n", time.process_time())
        return Ybus, Yprm, d.getCapPos()[0], d.getTapPos()

    def ybusPrimer(
        d,
    ):
        """Disable elements that change admittance matrix."""
        ldsEnbld = d.getEnabled(d.LDS)
        genEnbld = d.getEnabled(d.GEN)

        # Take out source, load and generators elements
        d.DSSText.Command = "batchedit vsource...* enabled=no"
        d.DSSText.Command = "batchedit load..* enabled=no"
        d.DSSText.Command = "batchedit generator..* enabled=no"
        return (
            ldsEnbld,
            genEnbld,
        )

    def ybusReenable(
        d,
        ldsEnbld,
        genEnbld,
    ):
        """Reeanble elements disabled by ybusPrimer."""
        # Return lds/vsrc to their enabled states
        d.DSSText.Command = "batchedit vsource..* enabled=yes"
        d.DSSText.Command = "batchedit load..* enabled=yes"
        d.DSSText.Command = "batchedit generator..* enabled=yes"
        d.setEnabled(d.LDS, ldsEnbld)
        d.setEnabled(d.GEN, genEnbld)

    def updateAeYprm(d, Yprm, YZidxs):
        """Update the Yprm dictionary for the ACE."""
        nodeSetA, nodeSetB, nzrosIdx = d.getYprmBuses()
        YprmAll = makeYprm(d.AE.Yprim)
        YprmI = YprmAll[:, nzrosIdx]  # for getting currents incl ground
        YprmV = YprmI[nzrosIdx]  # ignoring ground current.

        nodeSetAI, nodeSetBI = d.getIids(nodeSetA.copy(), nodeSetB.copy())

        YZa = [YZidxs[yzA.upper()] for yzA in nodeSetA]
        YZb = [YZidxs[yzB.upper()] for yzB in nodeSetB]

        pdeBuses = ["".join(nodeSetA[0].split(".")[:-1])]
        if not d.PDE.IsShunt:
            pdeBuses.append("".join(nodeSetB[0].split(".")[:-1]))

        if YprmI.shape != (len(nodeSetAI + nodeSetBI), len(nodeSetA + nodeSetB)):
            print(nodeSetAI, nodeSetBI, nodeSetA, nodeSetB, YprmI.shape, d.AE.Name)
            raise Exception("Failed to get conformal index dimensions!")

        Yprm.update(
            {
                d.AE.Name: {
                    "eName": d.AE.Name,
                    "busNames": pdeBuses,  # not d.AE.BusNames
                    "YprmI": YprmI,
                    "YprmV": YprmV,
                    "YZa": YZa,
                    "YZb": YZb,
                    "yzIdx": YZa + YZb,
                    "vIds": nodeSetA + nodeSetB,
                    "iIds": nodeSetAI + nodeSetBI,
                    "BDa": nodeSetAI,
                    "BDb": nodeSetBI,
                    "IsShunt": d.PDE.IsShunt,
                    "nPh": d.AE.NumPhases,
                    "nAI": len(nodeSetAI),
                    "nBI": len(nodeSetBI),
                }
            }
        )
        return YZa, YZb, YprmV

    def get_nIprm(
        d,
    ):
        """Get nIprm, in the case YprmBd does not exist."""
        i = d.PDE.First
        nIprm = 0
        while i:
            nIprm += int(np.sqrt((len(d.AE.Yprim) // 2)))
            i = d.PDE.Next

        return nIprm

    def get_YprmFlws(d):
        """Get YprmFlws in case YprmBd does not exist."""
        i = d.PDE.First
        YpFlws = []
        while i:
            nodeSetA, nodeSetB, _ = d.getYprmBuses()
            nodeSetAI, nodeSetBI = d.getIids(nodeSetA, nodeSetB)
            YpFlws.extend(
                [d.AE.Name + "__" + busSel for busSel in nodeSetAI + nodeSetBI]
            )
            i = d.PDE.Next

        return YpFlws

    def getIids(d, nsA, nsB):
        """Append ground current indexes, if there are any.

        Is a bit of a hack to be honest, and hasn't been tested loads.
        """
        if d.comFlag:
            nGnds = d.AE.NodeOrder.count(0)
        else:
            nGnds = np.count_nonzero(d.AE.NodeOrder == 0)

        Buses = [bn.split(".")[0] for bn in d.AE.BusNames]

        if d.AE.Name.split(".")[0].lower() == "capacitor":
            for i in range(nGnds):
                nsB.append("__ground__." + str(d.AE.NodeOrder[i]))
        else:
            if len(Buses) == 3 and d.AE.NumPhases == 1:
                # This is by inspection...!
                nsA.append(Buses[0] + ".0")
                nsB = [
                    Buses[1] + ".1",
                    Buses[1] + ".0",
                    Buses[2] + ".0",
                    Buses[2] + ".2",
                ]
            elif nGnds == 1:
                if d.comFlag:
                    iGnd = d.AE.NodeOrder.index(0)
                else:
                    iGnd = np.argmin(d.AE.NodeOrder)

                if iGnd <= len(nsA):
                    nsA.append(Buses[0] + ".0")
                else:
                    nsB.append(Buses[1] + ".0")
            elif nGnds == 2:
                nsA.append(Buses[0] + ".0")
                nsB.append(Buses[1] + ".0")
        return nsA, nsB

    def updateRowColData(d, row, col, data, YZa, YZb, YprmV):
        """Update row, col, data lists with YZa, YZb, YprmV.

        Is based on the code used for building sparse admittance matrices.
        """
        for i, yzA in enumerate(YZa):
            for j, yzB in enumerate(YZa):
                row.append(yzA)
                col.append(yzB)
                data.append(YprmV[i, j].copy())

        for i, yzA in enumerate(YZb, len(YZa)):
            for j, yzB in enumerate(YZb, len(YZa)):
                row.append(yzA)
                col.append(yzB)
                data.append(YprmV[i, j])

        for i, yzA in enumerate(YZa):
            for j, yzB in enumerate(YZb, len(YZa)):
                row.append(yzA)
                col.append(yzB)
                data.append(YprmV[i, j])

                row.append(yzB)
                col.append(yzA)
                data.append(YprmV[j, i])

    def getYprmBuses(d):
        """Get the nodes in the 'to' and 'from' side of d.AE."""
        NodeOrder = d.AE.NodeOrder
        Buses = d.AE.BusNames

        if len(Buses) == 3 and d.AE.NumPhases == 1:
            # First run pesky transformers using an alternative method
            nodeSetA, nodeSetB, nzrosIdx = d.get1ph3wdYprm()
        else:
            # Other run through
            NodeSet, nodeSetA, nodeSetB, nzrosIdx = mtList(4)
            nBss = len(Buses)
            if nBss == 3:  # (!) for three-phase windings - not used RN
                busSetC = []

            bus_i = 0  # flag to indicate which bus we are looking at
            for jj, node in enumerate(NodeOrder):
                if node in NodeSet:
                    NodeSet = []
                    if bus_i == 0:
                        bus_i = 1

                # Get the bus name for the current node
                if Buses[bus_i].count(".") == 0:
                    busName = Buses[bus_i] + "." + str(node)
                else:
                    busName = Buses[bus_i].split(".")[0] + "." + str(node)

                # For non-ground nodes, add to the nodeSet
                if node != 0:
                    if bus_i == 0:
                        nodeSetA.append(busName)
                    else:
                        nodeSetB.append(busName)

                    NodeSet = NodeSet + [node]
                    nzrosIdx.append(jj)

            nzrosIdx = np.array(
                nzrosIdx,
                dtype=int,
            )

        return nodeSetA, nodeSetB, nzrosIdx

    def get1ph3wdYprm(d):
        # This is required for those pesky transformers.
        NodeOrder = d.AE.NodeOrder
        Buses = d.AE.BusNames
        nzros = [1] * len(NodeOrder)
        nodeSetA = []
        nodeSetB = []
        k = 0
        for i, node in enumerate(NodeOrder):
            j = i % 2
            if node != 0:
                busName = Buses[k].split(".")[0] + "." + str(node)
                if k == 0:
                    nodeSetA.append(busName)
                else:
                    nodeSetB.append(busName)
            else:
                nzros[i] = 0
            k += j
        nzrosIdx = np.nonzero(nzros)[0]
        return nodeSetA, nodeSetB, nzrosIdx

    def getIprm(d, nms=None):
        """Get primitive currents in elements in opendss.

        Note that just passing PDEs does not capture disabled
        elements annoyingly, passing nms seems to overcome this.
        If using slesNtwk, these are in self.IprmNms.

        The equivalent method for slesNtwk is calcIprms.
        """
        Iprm = []
        if nms is None:
            i = d.PDE.First
            nms = []
            while i:
                d.SetACE(d.PDE.Name)
                Iprm.append(tp2ar(d.ACE.Currents))
                nms.append(d.ACE.Name)
                i = d.PDE.Next
        else:
            for nm in nms:
                d.SetACE(nm)
                Iprm.append(tp2ar(d.ACE.Currents))
        return np.concatenate(Iprm), nms

    def getIxfmPosSeq(d, xfmKeys=None):
        """Get the (complex) sequence currents of all transformers.

        Does NOT use d.AE.SeqCurrents[1] as this only gives the magnitude
        of the sequence current (as noted in the manual, for example).

        Use xfmKeys (as list of 'Transformer.__namehere__') to select, e.g.,
        only non-regulator xfrms.
        """
        if xfmKeys is None:
            xfmKeys = ["Transformer." + nm for nm in d.TRN.AllNames]

        posSeq = []
        i = d.TRN.First
        while i:
            if d.AE.Name in xfmKeys:
                if d.AE.NumPhases == 3:
                    posSeq.append(phs2seq[1].dot(tp2ar(d.AE.Currents)[:3]))
                elif d.AE.NumPhases == 1:
                    posSeq.append(tp2ar(d.AE.Currents)[0])
            i = d.TRN.Next
        return np.array(posSeq)

    def get3phPower(
        d,
    ):
        """Get the total complex power in W, each phase specified seperately."""
        kMult = -1e3
        if d.Vsrcs.Count == 1:
            d.Vsrcs.First
            Sfdr = kMult * tp2ar(d.AE.Powers)[:3]
        elif d.Vsrcs.Count == 3:
            Sfdr = np.zeros(3, dtype=complex)
            i = d.Vsrcs.First
            while i:
                Sfdr[i - 1] = kMult * tp2ar(d.AE.Powers)[0]
                i = d.Vsrcs.Next

        return Sfdr

    def createYbus(d, capTap=None, vbs=True):
        """Create the admittance matrix from SystemY, pulled from OpenDSS.

        Pass in tapPos, capPos to set these values before getting the admittance matrix.
        """
        if vbs:
            print("Load Ybus\n", time.process_time())
        if not capTap is None:
            d.setCapTap(capTap)

        CtrlMode_ = d.setControlMode(-1)
        prmrVrb = d.ybusPrimer()
        d.SLN.Solve()

        SysY = d.DSSCircuit.SystemY
        SysY_dct = {}
        i = 0
        for i in range(len(SysY)):
            if i % 2 == 0:
                Yi = SysY[i] + 1j * SysY[i + 1]
                if abs(Yi) != 0.0:
                    j = i // 2
                    SysY_dct[j] = Yi
        del SysY

        SysYV = np.array(list(SysY_dct.values()))
        SysYK = np.array(list(SysY_dct.keys()))
        Ybus0 = sparse.coo_matrix((SysYV, (SysYK, np.zeros(len(SysY_dct), dtype=int))))
        n = int(np.sqrt(Ybus0.shape[0]))
        Ybus = Ybus0.reshape((n, n))
        Ybus = Ybus.tocsc()

        # return control to nominal state
        d.setControlMode(CtrlMode_)

        # Return lds/vsrc to their enabled states
        d.ybusReenable(*prmrVrb)

        if vbs:
            print("Ybus loaded\n", time.process_time())

        return Ybus, d.DSSCircuit.YNodeOrder, d.getCapPos()[0], d.getTapPos()

    def getControlMode(d):
        """Return the solution 'control mode' of the circuit."""
        return d.SLN.ControlMode

    def setControlMode(d, CtrlMode):
        """Set the control mode to CtrlMode, and returns the initial ctrlmode.

        CtrlMode options:
        - -1: 'controloff'
        -  0: 'static'
        -  1: 'event'
        -  2: 'time'
        """
        CtrlMode_ = d.getControlMode()
        d.SLN.ControlMode = CtrlMode
        return CtrlMode_

    # =================== Unbalanced circuit util functions:
    def getVseq(d, seqBus=None):
        if seqBus is None:
            seqBus = d.getSeqBuses(d.DSSCircuit)[0]
        Vseq = []
        for bus in seqBus:
            d.SetABE(bus)
            Vseq.extend(list(tp2ar(d.ABE.CplxSeqVoltages)))
        return np.array(Vseq)

    def getVps(d, seqBus=None):
        Vseq = d.getVseq(seqBus)
        return np.abs(Vseq[1::3])

    @staticmethod
    def getSeqBuses(DSSCircuit):
        seqBus = []
        seqBusPhs = []
        seqBuskV = []
        allBuses = DSSCircuit.AllBusNames
        for bus in allBuses:
            DSSCircuit.SetActiveBus(bus)
            if DSSCircuit.ActiveBus.NumNodes == 3:
                seqBus.append(bus)
                seqBusPhs.append(bus + "_0")
                seqBusPhs.append(bus + "_1")
                seqBusPhs.append(bus + "_2")
                seqBuskV.append(1e3 * DSSCircuit.ActiveBus.kVBase)
        return seqBus, seqBusPhs, np.array(seqBuskV)

    def getVc2Vcub(d, YZidxs):
        seqBus, seqBusPhs, seqBuskV = d.getSeqBuses(d.DSSCircuit)
        nYZ = len(YZidxs)
        iA = []
        iB = []
        iC = []
        for bus in seqBus:
            iA.extend([YZidxs[bus.upper() + ".1"]] * 3)
            iB.extend([YZidxs[bus.upper() + ".2"]] * 3)
            iC.extend([YZidxs[bus.upper() + ".3"]] * 3)

        idxsX = np.kron(np.ones(3, dtype=int), np.arange(len(seqBusPhs), dtype=int))
        idxsY = np.array(iA + iB + iC)

        out0 = np.kron(np.ones(len(seqBus)), phs2seq[:, 0])
        out1 = np.kron(np.ones(len(seqBus)), phs2seq[:, 1])
        out2 = np.kron(np.ones(len(seqBus)), phs2seq[:, 2])
        outs = np.r_[out0, out1, out2]
        Vc2Vcub = sparse.coo_matrix(
            (outs, (idxsX, idxsY)), shape=(len(seqBusPhs), nYZ)
        ).tocsr()
        return (seqBus, seqBusPhs, seqBuskV), Vc2Vcub

    def getPwrIdxs(
        d,
        obj,
        YZv,
    ):
        """Creates the LDS_ object and Py, Pd indexes for linear algebra.

        Returns two lists:
        - sIdx is the indexes of YZv that are non-zero
        - ldsIdx is the indexes that each individual load/generator are at.

        Based on code from OxEMF.
        Note that it also calculates the power injections, but this
        functionality has been deprecated to state2x for now.
        """

        infoStr = "Names follow the LDS order from opendss;\n" + "Indexes are in YZv."

        OBJ_ = structDict(
            {
                "Y": structDict(
                    {"Name": [], "idx": [], "bus": [], "bus2lds": {}, "info": infoStr}
                ),
                "D": structDict(
                    {"Name": [], "idx": [], "bus": [], "bus2lds": {}, "info": infoStr}
                ),
            }
        )

        sY = np.zeros(len(YZv), dtype=complex)
        sD = np.zeros(len(YZv), dtype=complex)
        sYidx = []
        sDidx = []

        YZvIdxs = {val: i for i, val in enumerate(YZv)}

        i = obj.First
        while i:
            d.SetACE("Load." + obj.Name)
            actBus = d.ACE.BusNames[0].split(".")[0].upper()
            nPh = d.ACE.NumPhases
            phs = d.ACE.BusNames[0].split(".")[1:]
            sYidx.append([])
            sDidx.append([])

            if d.AE.Properties("conn").Val.lower() == "delta":
                if nPh == 1:
                    if len(phs) == 2:
                        if "1" in phs and "2" in phs:
                            dIdx = YZvIdxs[actBus + ".1"]
                        if "2" in phs and "3" in phs:
                            dIdx = YZvIdxs[actBus + ".2"]
                        if "3" in phs and "1" in phs:
                            dIdx = YZvIdxs[actBus + ".3"]
                        sDidx[-1].append(dIdx)
                        sD[dIdx] = sD[dIdx] + obj.kW + 1j * obj.kvar
                        OBJ_.D.idx.append(dIdx)
                        OBJ_.D.Name.append(obj.Name)
                    if len(phs) == 1:
                        # if only one phase, then is Y!
                        yIdx = YZvIdxs[actBus + "." + phs[0]]
                        sY[yIdx] = sY[yIdx] + (obj.kW + 1j * obj.kvar)
                        sYidx[-1].append(yIdx)
                        OBJ_.Y.idx.append(yIdx)
                        OBJ_.Y.Name.append(obj.Name)
                if nPh == 3:
                    for i in range(3):
                        dIdx = YZvIdxs[actBus + "." + str(i + 1)]
                        sD[dIdx] = sD[dIdx] + (obj.kW + 1j * obj.kvar) / 3
                        sDidx[-1].append(dIdx)
                        OBJ_.D.idx.append(dIdx)
                        OBJ_.D.Name.append("_".join(obj.Name, str(i)))
                if nPh == 2:
                    raise Exception("2-phase Delta loads not implemented.")
            else:
                if "1" in phs or phs == []:
                    yIdx = YZvIdxs[actBus + ".1"]
                    sY[yIdx] = sY[yIdx] + (obj.kW + 1j * obj.kvar) / nPh
                    sYidx[-1].append(yIdx)
                    OBJ_.Y.idx.append(yIdx)
                    OBJ_.Y.Name.append(obj.Name)
                if "2" in phs or phs == []:
                    yIdx = YZvIdxs[actBus + ".2"]
                    sY[yIdx] = sY[yIdx] + (obj.kW + 1j * obj.kvar) / nPh
                    sYidx[-1].append(yIdx)
                    OBJ_.Y.idx.append(yIdx)
                    OBJ_.Y.Name.append(obj.Name)
                if "3" in phs or phs == []:
                    yIdx = YZvIdxs[actBus + ".3"]
                    sY[yIdx] = sY[yIdx] + (obj.kW + 1j * obj.kvar) / nPh
                    sYidx[-1].append(yIdx)
                    OBJ_.Y.idx.append(yIdx)
                    OBJ_.Y.Name.append(obj.Name)
            i = obj.Next
        OBJ_.Y.bus = [YZv[i] for i in OBJ_.Y.idx]
        # OBJ_.D.bus = [YZv[i] for i in OBJ_.Y.idx] #????
        OBJ_.D.bus = [YZv[i] for i in OBJ_.D.idx]  # ????

        for obj_ in [OBJ_.Y, OBJ_.D]:
            kys = set(obj_.bus)
            bus2lds = {ky: [] for ky in kys}
            for nm, bus in zip(obj_.Name, obj_.bus):
                bus2lds[bus].append(nm)

            obj_.bus2lds = bus2lds

        sIdx = [sY.nonzero()[0], sD.nonzero()[0]]
        objIdx = [sYidx, sDidx]
        return sIdx, objIdx, OBJ_

    def getNtwkState(
        d,
    ):
        """Get the networks state of the opendss network.

        The state dictionary consists of:
        - LoadMult
        - load values (LdsY, LdsD)
        - gen values (GenY, GenD)
        - cap & tap positions (capTap)
        - solution mode (CtrlMode)
        Generators and loads are assumed single phase.

        See help(d.setControlMode) for CtrlMode options.
        """
        stateVals = {}
        stateVals["LoadMult"] = d.SLN.LoadMult

        stateVals["CtrlMode"] = d.getControlMode()

        # NB assume just a single Voltage source.
        stateVals.update(d.getVpuNgl())

        # get tap/cap positions
        stateVals["capTap"] = d.getCapTap()

        # get LdsY, LdsD, LdsYdss, LdsDdss:
        stateVals.update(d.getYdObj(d.LDS, yStr="LdsY", dStr="LdsD"))

        # get GenY, GenD, GenYdss, GenDdss:
        stateVals.update(d.getYdObj(d.GEN, yStr="GenY", dStr="GenD"))

        return stateVals

    def setNtwkState(d, state):
        """Solve the circuit at 'state'.

        NB: CtrlMode for state is very important!
            --> See d.setCtrlMode for CtrlMode options.

        Returns
        ---
        V ( = tp2ar(d.DSSCircuit.YNodeVarray) )

        """
        d.SLN.LoadMult = state["LoadMult"]
        d.setControlMode(state["CtrlMode"])

        # NB: assume only one voltage source.
        d.setVpuNgl(state["VsrcPu"], state["VsrcNgl"])

        # Set capTap positions
        d.setCapTap(state["capTap"])

        # Set loads
        d.setYdObj(d.LDS, state["LdsY"], state["LdsD"])

        # Set generators
        d.setYdObj(d.GEN, state["GenY"], state["GenD"])

        # Solve and return the solution
        d.SLN.Solve()

        if not d.SLN.Converged:
            print("Warning! OpenDSS did not converge.")

        return tp2ar(d.DSSCircuit.YNodeVarray)

    def getVsrc(d):
        """Returns the 'theoretical' voltage source voltage.

        That is:
        - if there is only one Vsrc, then the voltage returned is the
            positive sequence voltage (NOT the 'active element voltage).
        - If there are three Vsrcs, then the voltage is given as the voltage
            for each Vsrc in sequency.
        """
        if d.Vsrcs.Count == 1:
            d.Vsrcs.First
            v0 = 1e3 * d.Vsrcs.BasekV
            ngl0 = np.exp(1j * np.pi * (d.Vsrcs.AngleDeg / 180))
            aNgl = (np.exp(-1j * 2 * np.pi / 3) ** np.array([0, 1, 2])) * ngl0
            Vsrc = aNgl * v0 * d.Vsrcs.pu / np.sqrt(3)
        elif d.Vsrcs.Count == 3:
            Vsrc = np.zeros(3, dtype=complex)
            i = d.Vsrcs.First
            while i:
                v0 = 1e3 * d.Vsrcs.BasekV
                aNgl = np.exp(1j * np.pi * (d.Vsrcs.AngleDeg / 180))
                Vsrc[i - 1] = aNgl * v0 * d.Vsrcs.pu
                i = d.Vsrcs.Next

        return Vsrc

    def getVpuNgl(
        d,
    ):
        """Get the pu and angle (degrees) of all voltages sources.

        Returns a dict of lists for the pu and ngl values.
        """
        vSrcOut = {
            "VsrcPu": [],
            "VsrcNgl": [],
        }

        i = d.Vsrcs.First
        while i:
            vSrcOut["VsrcPu"].append(d.Vsrcs.pu)
            vSrcOut["VsrcNgl"].append(d.Vsrcs.AngleDeg)
            i = d.Vsrcs.Next

        return vSrcOut

    def setVpuNgl(d, VsrcPu, VsrcNgl=None):
        """Set the voltage source[s] to the value specified in VsrcPu.

        VsrcNgl should be in DEGREES.

        Notes:
        - For one Vsrc:
            - passing only VsrcPu only updates the pu value
        - For three Vsrc:
            - Passing only a single float updates the pu value of all vsrcs
            - Passing two floats does the same, with 120 degrees between ngls
            - Otherwise, a list/array of three values should be passed.

        """
        if not d.Vsrcs.Count in [1, 3]:
            raise Exception("Only one- and three- Vsrcs makes sense rn!")

        if type(VsrcPu) is float:
            VsrcPu = [VsrcPu] * d.Vsrcs.Count
        if type(VsrcNgl) is float:
            VsrcNgl = [VsrcNgl] * d.Vsrcs.Count

        i = d.Vsrcs.First
        while i:
            d.Vsrcs.pu = VsrcPu[i - 1]
            if not VsrcNgl is None:
                d.Vsrcs.AngleDeg = VsrcNgl[i - 1]
            i = d.Vsrcs.Next

    def get_Yvbase(d, YZ, test=False):
        """Get the vbases by comparing to the possible Vbases."""
        # Get the voltage, the voltage base, and then find the values.
        V = np.abs(tp2ar(d.DSSCircuit.YNodeVarray))
        Vbase = d.SET.VoltageBases * 1e3 / np.sqrt(3)
        rto = np.abs(
            (
                V.reshape(
                    (
                        -1,
                        1,
                    )
                )
                - Vbase
            )
        )
        Yvbase = Vbase[np.argmin(rto, axis=1)]

        # But: for any very low voltages (close to zero), manually get
        # the values.
        idxLo = np.where(V < 50)[0]
        for idx in idxLo:
            bus_id = YZ[idx].split(".")
            i = d.SetABE(bus_id[0])
            Yvbase[idx] = 1e3 * d.ABE.kVBase

        # Test manually if wanted to check all is OK
        if test:
            Yvbase_ = []
            for yz in YZ:
                bus_id = yz.split(".")
                i = d.SetABE(bus_id[0])  # return needed or this prints a number
                Yvbase_.append(1e3 * d.ABE.kVBase)
            Yvbase_ = np.array(Yvbase_)
            rerrVal = rerr(Yvbase, Yvbase_, p=0)
            print(f"Yvbase relative error: {rerrVal}")

        return Yvbase

    def getTotPwr(
        d,
    ):
        """Return the total power, in kW."""
        return tp2ar(d.DSSCircuit.TotalPower)[0]

    def getLss(
        d,
    ):
        """Return the circuit losses, in kW."""
        return tp2ar(d.DSSCircuit.Losses)[0] * 1e-3

    def setObjAttr(d, obj, val, vals):
        """Cycle through obj to set each of 'val' values to vals.

        Opposite of getObjAttr - as there does NOT re-enable objects.
        """
        # if len(vals)!=obj.__getattribute__(val):
        # raise Exception('len(vals)!=obj.Count!')

        j = 0
        i = obj.First
        while i:
            obj.__setattr__(val, vals[j])
            j += 1
            i = obj.Next

    def getObjAttr(d, obj, val=None, AEval=None):
        """Cycle through obj to get each of 'val' values.

        If AEval is included, then also pulls out an attribute from d.AE.

        Opposite is setObjAttr.

        NOTE that this does not re-enable objects, so, for example, if you
        get the names d.getObjAttr(d.LDS,'Name') this is ONLY equivalent
        to d.LDS.AllNames if all loads are enabled.
        """
        if (not val is None) and (not AEval is None):
            raise Exception("Only pass in val or AEval, not both.")

        vals = []
        i = obj.First
        while i:
            if not val is None:
                vals.append(obj.__getattribute__(val))
            elif not AEval is None:
                vals.append(d.AE.__getattribute__(AEval))
            i = obj.Next

        return vals

    def getObjPhs(d, obj):
        """Cycle through obj and get all names.

        Based on getObjAttr.
        """
        # names = []
        phs = []
        i = obj.First
        while i:
            # phs = d.ACE.BusNames[0].split('.')[1:]
            if d.ACE.NumPhases == 1:
                phs.append(int(d.AE.BusNames[0][-1]))
            else:
                phs.append(None)
            i = obj.Next

        return phs

    # =================== Control funcs
    def getYdObj(d, obj, yStr, dStr):
        """Got through all loads, then seperate into Y- and D-, and return.

        Also returns the OpenDSS powers, if there is a solution; note that this
        is CORRECTED by a factor of LM, to make Lds* and Lds*dss comparable.
        """
        ydLds = {
            yStr: [],
            dStr: [],
        }

        recordSln = d.SLN.Converged and (not d.SLN.SystemYChanged)
        if recordSln:
            ydLds[yStr + "dss"] = []
            ydLds[dStr + "dss"] = []

        i = obj.First

        # First infer if the type is 'loads' (and thus to correct with lm)
        if d.AE.Name[:4].lower() == "load":
            lm0 = d.SLN.LoadMult
        else:
            lm0 = 1.0

        # Then go through and get all the powers.
        while i:
            if d.AE.Properties("conn").Val.lower() == "delta":
                ydLds[dStr].append(obj.kW + 1j * obj.kvar)
                if recordSln:
                    ydLds[dStr + "dss"].append(sum(tp2ar(d.AE.Powers)) / lm0)
            else:
                ydLds[yStr].append(obj.kW + 1j * obj.kvar)
                if recordSln:
                    ydLds[yStr + "dss"].append(sum(tp2ar(d.AE.Powers)) / lm0)
            i = obj.Next

        return ydLds

    def setYdObj(d, obj, objY, objD):
        """Set the powers of obj of the circuit to objY and objD.


        As in all of these functions, it is implicit that the order of these
        lists follows that of the obj object, which is NOT checked for
        enabled/disabled values.

        Inputs
        ---
        d - self
        obj - dss object, e.g. d.LDS
        objY, objD - the object values for Y/delta connector components

        """
        iY = 0
        iD = 0
        i = obj.First
        while i:
            if d.AE.Properties("conn").Val.lower() == "delta":
                S = objD[iD]
                iD += 1
            else:
                S = objY[iY]
                iY += 1
            obj.kW = S.real
            obj.kvar = S.imag
            i = obj.Next

    def getCapTap(d):
        """Simple wrapper to call [getCapPos[0], getTapPos]."""
        return [d.getCapPos()[0], d.getTapPos()]

    def setCapTap(d, capTap):
        """Another simple wrapper, this time setting capTap."""
        d.setCapPos(capTap[0])
        d.setTapPos(capTap[1])

    def getTapVal(d):
        """Gets the value of the tap on the SECOND winding (e.g. 1.05, 1.0...)

        Does NOT get the tap position, use getTapPos for that.
        """
        xfmrs = d.getRegXfms()
        tapVal = []
        for xfm in xfmrs:
            d.TRN.Name = xfm.split(".")[1]
            d.TRN.Wdg = 2
            tapVal.append(d.TRN.Tap)
        return tapVal

    def setTapWdgs(d, w=2):
        """Set the transformer tap winding to have value w (either 1 or 2)."""
        i = d.TRN.First
        while i != 0:
            d.TRN.Wdg = w
            i = d.TRN.Next

    def getTapPos(d):
        """Get the tap position by going through RGC.

        NB: unlike getCapPos, does not bother checking if taps are enabled.
        """
        TC_No = []
        i = d.RGC.First
        while i != 0:
            TC_No.append(d.RGC.TapNumber)
            i = d.RGC.Next
        return TC_No

    def setTapPos(d, TC_No):
        """Set the tap positions at TC_No. Opposite of getTapPos."""
        i = d.RGC.First
        while i != 0:
            d.RGC.TapNumber = TC_No[i - 1]
            i = d.RGC.Next

    def getCapPos(d):
        """Get the position of all capacitors, even if they are disabled.

        Also returns the capacitor powers as well, which is useful for
        debugging setCapPos.
        """
        # First get the 'enabled' status of all capacitors
        capEnbld = d.getEnabled(d.CAP)

        # Then, enable all capacitors and find their states:
        d.DSSText.Command = "batchedit Capacitor..* enabled=True"
        capPos = []
        capPwr = []
        i = d.CAP.First
        while i:
            capPos.append(d.CAP.States)
            capPwr.append(tp2ar(d.AE.Powers))
            i = d.CAP.Next

        # Return caps to their enabled state
        d.setEnabled(d.CAP, capEnbld)
        return capPos, capPwr

    def setCapPos(d, capPos):
        """Get the position of all capacitors, even if they are disabled.

        Dual of getCapPos.

        This has been updated now - the extra stuff about updating the
        cap controls seems to be necessary, for now obvious reason.
        """

        # First, the mysterious capcontrol modifying stuff.
        cpcEnabled = d.getEnabled(d.CPC)
        i = d.CPC.First
        while i:
            d.AE.Enabled = False
            i = d.CPC.Next

        # Then, enable all capacitors and find their states:
        capEnabled = d.getEnabled(d.CAP)
        d.DSSText.Command = "batchedit Capacitor..* enabled=True"
        i = d.CAP.First
        while i:
            d.CAP.States = capPos[i - 1]
            i = d.CAP.Next

        # return CPC,CAP to their original state
        d.setEnabled(d.CPC, cpcEnabled)
        d.setEnabled(d.CAP, capEnabled)

    def getEnabled(d, obj):
        enabled = [0] * obj.Count
        i = obj.First
        while i:
            enabled[i - 1] = 1
            i = obj.Next
        return enabled

    def setEnabled(d, obj, enabled):
        """Set the elements of obj to enabled, assuming they are all enabled."""
        i = obj.First
        while i:
            d.AE.Enabled = enabled[i - 1]
            i = obj.Next

    def getRgcZvlts(d):
        """Get the regulator R, X conversions from the current model.

        Based on getRxVltsMat from dss_voltage_funcs ('see WB 15-01-19'),
        and lumps in the old functions getRx and getRegIcVr.

        The units of R, X are in (bus) VOLTS per AMP, not in RGCs 'local' 120V
        base voltage.

        In the DPhil the way this was checked was using 809-812, 921-923 of
        the linSvdCalcs.py script.
        """
        i = d.RGC.First
        R = []
        X = []
        Z = []
        Nct = []
        Npt = []
        Vr = []
        while i:
            # assume that all are operating 'forward'
            Z.append(d.RGC.ForwardR + 1j * d.RGC.ForwardX)
            Nct.append(d.RGC.CTPrimary)
            Npt.append(d.RGC.PTratio)
            i = d.RGC.Next

        zVlts = np.array(Z) * np.array(Npt) / np.array(Nct)
        return zVlts

    def getRgcNds(
        d,
        YZvIdxs,
    ):
        """Get the regulated buses of all regulators and indexes in YZv.

        Based on get_regIdx from dss_voltage_funcs.
        """
        regXfmrs = d.getRegXfms()
        regNds = []
        regNdsIdx = []
        for regXfmr in regXfmrs:
            d.SetACE(regXfmr)
            if d.RGC.Winding != 2:
                raise Exception("Assumption of winding 2 not correct.")
            if d.TRN.IsDelta:
                raise Exception("Delta connected RGC not implemented.")
            if d.RGC.MonitoredBus == "":
                # NOTE: assume connected to .1 (true is bus='')
                phs = ".1"
            else:
                raise Exception("Monitored buses not implemented yet.")

            if d.AE.NumPhases == 1:
                regNds.append(d.AE.BusNames[1])
            elif d.AE.NumPhases == 3:
                if d.AE.BusNames[1].count(".") == 4:
                    regNds.append(d.AE.BusNames[1].split(".", 1)[0] + phs)
                else:
                    regNds.append(d.AE.BusNames[1] + phs)
            regNdsIdx.append(YZvIdxs[regNds[-1].upper()])
        return regNds, regNdsIdx

    def getRgcFlwIdx(
        d,
        YprmFlws,
        YZvIdxs,
    ):
        """Get the flows names and indexes for LTC regs in YprmFlws.

        Loosely based on getRegWlineIdx from dss_voltage_funcs.
        """
        # Initialise
        rgcNds = d.getRgcNds(YZvIdxs)[0]
        rgcXfm = d.getRegXfms()
        rgcFlws = [np.nan] * d.RGC.Count
        rgcFlwsIdx = [np.nan] * d.RGC.Count

        # Go through each node and get the downstream element.
        for i, flw in enumerate(YprmFlws):
            el, bs = flw.split("__", 1)
            if bs in rgcNds and el not in rgcXfm:
                idx = rgcNds.index(bs)
                if not np.isnan(rgcFlws[idx]):
                    raise Exception("RGC has multiple downstream elements.")

                rgcFlws[idx] = flw
                rgcFlwsIdx[idx] = i

        return rgcFlws, rgcFlwsIdx

    def getRgcVreg(d):
        """Get the voltage regulation value, in volts (not 120V base!)

        Based on get_regVreg from dss_voltage_funcs.
        """
        i = d.RGC.First
        vreg = []
        while i:
            vreg.append(d.RGC.ForwardVreg * d.RGC.PTratio)
            i = d.RGC.Next
        return vreg

    def getRgcI(d):
        """Get the currents flowing through regulator controls.

        Based on getRegI from linModel class in linSvdCalcs. Note that it
        hasn't been tested too much - it simply picks the len(current)//2-th
        element.
        """
        regXfmrs = d.getRegXfms()
        currents = []
        for regXfmr in regXfmrs:
            d.SetACE(regXfmr)
            i0 = tp2ar(d.AE.Currents)
            iChoose = len(i0) // 2
            currents.append(i0[iChoose])
        return currents

    # =================== Hosting capacity util funcs
    def addGenerators(d, genBuses, delta):
        """Add generators at each of genBuses, delta connected if flag raised.

        NB: nominal power is 0.5 + 0.3 kVar kW.
        """
        genNames = []
        genNameEnd = "_g1ph"
        for genBus in genBuses:
            d.SetABE(genBus)
            if not delta:  # ie wye
                genName = genBus.replace(".", "_") + genNameEnd
                genKV = str(d.ABE.kVBase)
                d.DSSText.Command = "".join(
                    [
                        "new generator.",
                        genName,
                        " phases=1 bus1=",
                        genBus,
                        " kV=",
                        genKV,
                        " kW=0.5 ",
                        "kvar=0.3 model=1 vminpu=0.33 vmaxpu=3.0 conn=wye",
                    ]
                )
            elif delta:
                genKV = str(d.ABE.kVBase * np.sqrt(3))
                if genBus[-1] == "1":
                    genBuses = genBus + ".2"
                if genBus[-1] == "2":
                    genBuses = genBus + ".3"
                if genBus[-1] == "3":
                    genBuses = genBus + ".1"
                genName = genBuses.replace(".", "_") + genNameEnd
                d.DSSText.Command = "".join(
                    [
                        "new generator.",
                        genName,
                        " phases=1 bus1=",
                        genBuses,
                        " kV=",
                        genKV,
                        " kW=0.6",
                        " kvar=0.4 model=1 vminpu=0.33 vmaxpu=3.0 conn=delta",
                    ]
                )
            genNames = genNames + [genName]
        return genNames

    def setGenPq(d, genNames, P, Q=None):
        """Loop and set the P, Q values of genNames, using kW/kvar units.

        If Q not set, leaves Q as-is.
        """
        i = 0
        for genName in genNames:
            d.GEN.Name = genName
            d.GEN.kW = P[i]
            if not (Q is None):
                d.GEN.kvar = Q[i]
            i += 1
        return

    # =================== graph theory funcs
    def buildIncidenceMatrix(d, Yprm):
        """Build the incidence matrix of the circuit.

        Uses the Yprm set that is found during getYbus. Use
        iMatrix.nonzero() to get the indexes, if required; the
        matrix is given in terms of branch x buses. As well as getting
        the basic incidence matrix this also returns the position of
        shunt elements and also loops caused by regulators; there are
        currently still some loops in bigger circuits though which have
        yet to have a proper method yet of removing loops if necessary.

        NB: entering Yprm is enforced! From:
            Ybus, Yprm = d.buildYmat(d.PDE,capTap)[:2]
        """
        busNs = d.DSSCircuit.AllBusNames
        branchNames = []
        idxsI = []
        idxsJ = []
        shunt = []

        ii = 0
        for bName, yps in Yprm.items():
            for bus in yps["busNames"]:
                idxsI.append(ii)
                idxsJ.append(busNs.index(bus))
            branchNames.append(bName)
            shunt.append(yps["IsShunt"])
            ii += 1
        brchNs = tuple(branchNames)
        shunt = np.where(shunt)[0].tolist()
        iMatrix = sparse.coo_matrix(
            (np.ones(len(idxsJ), dtype=bool), (idxsI, idxsJ)),
            shape=(len(brchNs), len(busNs)),
            dtype=bool,
        )
        iMatrix = iMatrix.tocsr()

        REG = d.DSSCircuit.RegControls
        i = REG.First
        regLoops = []
        regIdxs = []
        while i:
            regName = "Transformer." + REG.Transformer
            regIdx = list(iMatrix[brchNs.index(regName)].nonzero()[1])
            if regIdx in regIdxs:
                regLoops.append(brchNs.index(regName))
            else:
                regIdxs.append(regIdx)
            i = REG.Next

        return iMatrix, (brchNs, busNs), (shunt, regLoops)

    # Misc opendss functions ===========================
    def getXfmrIlims(d, notIn=[]):
        """Get the normal current ratings for transformers.

        The normHkva (normal 'high winding[?] power) is thought to be used for
        the normamps property as

        kvaHnorm/(d.TRN.kV/np.sqrt(3))/3
        """
        ilims = []
        i = d.TRN.First
        while i:
            if d.AE.Name not in notIn:
                ilims.append(float(d.AE.Properties("normamps").Val))
            i = d.TRN.Next
        return np.array(ilims)

    def getRegXfms(d):
        i = d.RGC.First
        xfms = []
        while i:
            xfms.append("Transformer." + d.RGC.Transformer)
            i = d.RGC.Next
        return xfms

    def getBranchBuses(d):
        """Get dict of all non-shunt branches and their busnames."""
        i = d.PDE.First
        branches = {}
        while i:
            if not d.PDE.IsShunt:
                branches[d.PDE.Name] = d.AE.BusNames

            i = d.PDE.Next
        return branches

    # Plotting funcs ===========
    def getBusCoords(d):
        """Get the bus co-ordinates for the given circuit.

        Based on the function of the same name from dss_python_funcs.py
        """
        # Get the name of the first line
        d.LNS.First
        lineName = d.LNS.Name

        # Make sure there is a meter
        nM = len(d.MTR.AllNames)
        if nM > 0:
            # Change the meters - not too sure why...?
            Mel = []
            i = d.MTR.First
            while i:
                Mel = Mel + [d.MTR.MeteredElement]
                d.MTR.MeteredElement = "line." + lineName
                i = d.MTR.Next
        else:
            d.DSSText.Command = "new energymeter.srcEM element=line." + lineName

        # Get the buses and make sure there are co-ordinates
        d.SLN.Solve()
        d.DSSText.Command = "interpolate"
        ABN = d.DSSCircuit.AllBusNames

        # Get the bus co-ordinates
        busCoords = {}
        for bus in ABN:
            d.SetABE(bus)
            if d.ABE.Coorddefined:
                busCoords[bus] = (d.ABE.x, d.ABE.y)
            else:
                busCoords[bus] = (np.nan, np.nan)

        # Do something with the meters...?
        if nM > 0:
            i = d.MTR.First
            while i:
                d.MTR.MeteredElement = Mel[i - 1]
                i = d.MTR.Next

        return busCoords

    def getBusCoordsAug(
        d,
    ):
        """Get augmented buscoords (making sure branches have two coords).

        Approach:
        - go through all branch elements.
        - if both coordinates defined: continue.
        - if only one coordinate defined:
            - coordinate on second element to match first.
        if neither:
            - Ignore (leave as nans)

        A simplified version of same func from dss_python_funcs.py
        """
        busCoordsAug = d.getBusCoords()

        i = d.PDE.First
        while i:
            if not d.PDE.IsShunt:
                # buses[:2] required for e.g., 3 winding xfmrs
                bus0, bus1 = [b.split(".")[0] for b in d.AE.BusNames[:2]]
                coord0, coord1 = [busCoordsAug[b] for b in [bus0, bus1]]

                # If we are missing one co-ordinate then fix up
                if np.isnan(coord0[0]) and not np.isnan(coord1[0]):
                    busCoordsAug[bus0] = busCoordsAug[bus1]
                if not np.isnan(coord0[0]) and np.isnan(coord1[0]):
                    busCoordsAug[bus1] = busCoordsAug[bus0]

            i = d.PDE.Next

        return busCoordsAug


def updateFlagState(
    state,
    flagVal=1.0,
    rvl=1.0 + 0.0j,
    lm=1.0,
    IP=False,
    w0=True,
):
    """Go through LdsY,LdsD and update all 'flagVal' kW loads to a new value.

    NB  if lm=0 passed in, simply return the original state values.

    Inputs
    ---
    state - the state to change
    flagVal - the flagVal real power to change, in kW
    rvl - the new val of the 1kw ('residential') loads
    lm - a loadmult to scale by (NB only changes rvl/flagVal, NOT other loads)
    IP - bool, if True then return the state In Place (else, deepcopy)
    w0 - zero warning, print that lm=0 has been passed in before returning

    Returns
    ---
    newState - the state with all of LdsY and LdsD changed
    """

    # Create the object
    if IP:
        newState = state
    else:
        newState = deepcopy(state)

    # First, if lm=0 passed in, return the original.
    if lm == 0:
        if w0:
            Warning("LM = 0 passed into updateFlagState.")
        return newState

    # convert to complex if required
    if type(rvl) in [float, int]:
        rvl = rvl + 0j

    # update the load values.
    for ld_ in ["LdsY", "LdsD"]:
        ldNew = []
        for ld in newState[ld_]:
            if ld.real == flagVal:
                ldNew.append(rvl / lm)
            else:
                ldNew.append(ld)
        newState[ld_] = ldNew

    return newState


def Y1_(yt):
    return np.diag([yt] * 3)


def Y2_(yt):
    return linalg.toeplitz([2 * yt, -yt, -yt], [2 * yt, -yt, -yt]) / 3


def Y3_(yt):
    return linalg.toeplitz([yt, 0, -yt], [yt, -yt, 0]) / np.sqrt(3)


def Y4_(yt):
    return np.array([[yt, -yt, 0], [-yt, 2 * yt], [0, -yt, yt]]) / 3


def Y5_(yt):
    return np.diag([yt] * 2)


def Y6_(yt):
    return linalg.toeplitz([-yt, 0], [-yt, yt, 0]) / np.sqrt(3)


def xfmrYprm(cA, cB, t, kV, kVA, ppm_a, ll, xhl):
    """Build transformer primitive admittances from data to match opendss.


    cA: connection 1, one of
        - 1 (1ph 'Y')
        - 'Y' (3ph Y)
        - 'D' (3ph D)
    cB: connection 2, as above

    t: turns ration (1 as unity)
    kV: kvbase
    kVA: kVA base
    ppm_a: antifloat parameter
    ll: loadloss, %
    xhl: leakage reactance, %
    """

    zBase = 1e3 * (kV ** 2) / kVA
    yBase = 1 / zBase

    Zs = zBase * 0.01 * (ll + 1j * xhl)
    yt = 1 / Zs

    antiFlt = ppm_a * yBase / 1e6

    if cA == 1:
        if cA != cB:
            raise Exception("cA and cB not both 1ph.")

        y11 = np.array([[yt, -yt], [-yt, yt]])
        y12 = y11 / t
        y21 = y11 / t
        y22 = y11 / (t ** 2)
        afDiag = -1j * np.diag(np.kron([1, 1], [0.5, 1]))
        yprm = np.block([[y11, y12], [y21, y22]]) + afDiag
    else:
        if cA == "D" and cB == "Y":
            yprm = np.block(
                [
                    [
                        Y2_(yt),
                        -Y3_(yt).T / t,
                    ],
                    [-Y3_(yt) / t, Y1_(yt) / (t ** 2)],
                ]
            )
            aF1 = 1 / 3
            aF2 = 0.5
        if cA == "Y" and cB == "Y":
            yprm = np.block(
                [
                    [
                        Y1_(yt),
                        -Y1_(yt).T / t,
                    ],
                    [-Y1_(yt) / t, Y1_(yt) / (t ** 2)],
                ]
            )
            aF1 = 0.5
            aF2 = 0.5

        afDiag = -1j * antiFlt * np.diag(np.kron([aF1, aF2], [1] * 3))
        yprm = yprm + afDiag

    return yprm


def get_regXfmr2(DSSCircuit):
    i = DSSCircuit.RegControls.First
    regXfmr = []
    while i:
        regXfmr.append(DSSCircuit.RegControls.Transformer)
        i = DSSCircuit.RegControls.Next
    return regXfmr


def getTotkW(DSSCircuit):
    GEN = DSSCircuit.Generators
    i = GEN.First
    kwGen = 0
    while i:
        kwGen = kwGen + GEN.kW
        i = GEN.Next
    return kwGen


def runCircuit(DSSCircuit, SLN):
    # NB assumes all generators are constant power.
    SLN.Solve()
    TG = getTotkW(DSSCircuit)
    TP = -DSSCircuit.TotalPower[0]
    TL = 1e-3 * DSSCircuit.Losses[0]
    PL = -(DSSCircuit.TotalPower[0] + 1e-3 * DSSCircuit.Losses[0] - TG)
    YNodeV = tp2ar(DSSCircuit.YNodeVarray)
    return TP, TG, TL, PL, YNodeV


def ld_vals(DSSCircuit):
    ii = DSSCircuit.FirstPCElement()
    S = []
    V = []
    I = []
    B = []
    D = []
    N = []
    while ii != 0:
        if DSSCircuit.ActiveElement.Name[0:4].lower() == "load":
            DSSCircuit.Loads.Name = DSSCircuit.ActiveElement.Name.split(sep=".")[1]
            S.append(tp2ar(DSSCircuit.ActiveElement.Powers))
            V.append(tp2ar(DSSCircuit.ActiveElement.Voltages))
            I.append(tp2ar(DSSCircuit.ActiveElement.Currents))
            B.append(DSSCircuit.ActiveElement.BusNames)
            N.append(DSSCircuit.Loads.Name)
            if B[-1][0].count(".") == 1:
                D.append(False)
            else:
                D.append(DSSCircuit.Loads.IsDelta)
        ii = DSSCircuit.NextPCElement()
    jj = DSSCircuit.FirstPDElement()
    while jj != 0:
        if DSSCircuit.ActiveElement.Name[0:4].lower() == "capa":
            DSSCircuit.Capacitors.Name = DSSCircuit.ActiveElement.Name.split(sep=".")[1]
            S.append(tp2ar(DSSCircuit.ActiveElement.Powers))
            V.append(tp2ar(DSSCircuit.ActiveElement.Voltages))
            I.append(tp2ar(DSSCircuit.ActiveElement.Currents))
            B.append(DSSCircuit.ActiveElement.BusNames)
            D.append(DSSCircuit.Capacitors.IsDelta)
            N.append(DSSCircuit.Capacitors.Name)
        jj = DSSCircuit.NextPDElement()
    return S, V, I, B, D, N


def find_node_idx(n2y, bus, D):
    idx = []
    BS = bus.split(".", 1)
    bus_id, ph = [BS[0], BS[-1]]  # catch cases where there is no phase
    if ph == "1.2.3" or bus.count(".") == 0:
        idx.append(n2y.get(bus_id + ".1", None))
        idx.append(n2y.get(bus_id + ".2", None))
        idx.append(n2y.get(bus_id + ".3", None))
    elif ph == "0.0.0" or ph == "0":
        # nb second part experimental for single phase caps
        idx.append(n2y.get(bus_id + ".1", None))
        idx.append(n2y.get(bus_id + ".2", None))
        idx.append(n2y.get(bus_id + ".3", None))
    elif ph == "1.2.3.4":
        # needed if, e.g. transformers are grounded through a reactor
        idx.append(n2y.get(bus_id + ".1", None))
        idx.append(n2y.get(bus_id + ".2", None))
        idx.append(n2y.get(bus_id + ".3", None))
        idx.append(n2y.get(bus_id + ".4", None))
    elif D:
        if bus.count(".") == 1:
            idx.append(n2y[bus])
        else:
            idx.append(n2y[bus[0:-2]])
    else:
        idx.append(n2y[bus])
    return idx


def calc_sYsD(YZ, B, I, V, S, D, n2y):
    iD = np.zeros(len(YZ), dtype=complex)
    sD = np.zeros(len(YZ), dtype=complex)
    iY = np.zeros(len(YZ), dtype=complex)
    sY = np.zeros(len(YZ), dtype=complex)
    for i in range(len(B)):
        for bus in B[i]:
            idx = find_node_idx(n2y, bus, D[i])
            BS = bus.split(".", 1)
            bus_id, ph = [BS[0], BS[-1]]  # catch cases where there is no phase
            if D[i]:
                if bus.count(".") == 2:
                    iD[idx] = iD[idx] + I[i][0]
                    sD[idx] = sD[idx] + S[i].sum()
                else:
                    iD[idx] = iD[idx] + I[i] * np.exp(1j * np.pi / 6) / np.sqrt(3)
                    VX = np.array(
                        [V[i][0] - V[i][1], V[i][1] - V[i][2], V[i][2] - V[i][0]]
                    )
                    sD[idx] = sD[idx] + iD[idx].conj() * VX * 1e-3
            else:
                if ph[0] != "0":
                    if bus.count(".") > 0:
                        iY[idx] = iY[idx] + I[i][0]
                        sY[idx] = sY[idx] + S[i][0]
                    else:
                        iY[idx] = iY[idx] + I[i][0:3]
                        sY[idx] = sY[idx] + S[i][0:3]
    return iY, sY, iD, sD


def node_to_YZ(DSSCircuit):
    n2y = {}
    YNodeOrder = DSSCircuit.YNodeOrder
    for node in DSSCircuit.AllNodeNames:
        n2y[node] = YNodeOrder.index(node.upper())
    return n2y


def get_sYsD(DSSCircuit):
    S, V, I, B, D, N = ld_vals(DSSCircuit)
    n2y = node_to_YZ(DSSCircuit)
    V0 = tp2ar(DSSCircuit.YNodeVarray) * 1e-3  # kV
    YZ = DSSCircuit.YNodeOrder
    iY, sY, iD, sD = calc_sYsD(YZ, B, I, V, S, D, n2y)
    H = create_Hmat(DSSCircuit)
    H = H[iD.nonzero()]
    sD = sD[iD.nonzero()]
    yzD = [YZ[i] for i in iD.nonzero()[0]]
    iD = iD[iD.nonzero()]
    iTot = iY + (H.T).dot(iD)
    # chka = abs((H.T).dot(iD.conj())*V0 + sY - V0*(iTot.conj()))/abs(sY) # 1a error, kW
    # sD0 = ((H.dot(V0))*(iD.conj()))
    # chkb = abs(sD - sD0)/abs(sD) # 1b error, kW
    # print('Y- error:')
    # printAB(YZ,abs(chka))
    # print('D- error:')
    # printAB(yzD,abs(chkb))
    return sY, sD, iY, iD, yzD, iTot, H


def returnXyXd(DSSCircuit, n2y):
    S, V, I, B, D, N = ld_vals(DSSCircuit)
    V0 = tp2ar(DSSCircuit.YNodeVarray) * 1e-3  # kV
    YZ = DSSCircuit.YNodeOrder
    iY, sY, iD, sD = calc_sYsD(YZ, B, I, V, S, D, n2y)
    sD = sD[iD.nonzero()]
    xY = -1e3 * s_2_x(sY[3:])
    xD = -1e3 * s_2_x(sD)
    return xY, xD


def create_Hmat(DSSCircuit):
    n2y = node_to_YZ(DSSCircuit)
    Hmat = np.zeros((DSSCircuit.NumNodes, DSSCircuit.NumNodes))
    for bus in DSSCircuit.AllBusNames:
        idx = find_node_idx(n2y, bus, False)
        if idx[0] != None and idx[1] != None:
            Hmat[idx[0], idx[0]] = 1
            Hmat[idx[0], idx[1]] = -1
        if idx[1] != None and idx[2] != None:
            Hmat[idx[1], idx[1]] = 1
            Hmat[idx[1], idx[2]] = -1
        if idx[2] != None and idx[0] != None:
            Hmat[idx[2], idx[2]] = 1
            Hmat[idx[2], idx[0]] = -1
    return Hmat


def pdIdxCmp(YZv, pdIdx):
    """Get the complement of pdIdx, that is, the 'end' node."""
    pdIdxCmp = pdIdx.copy()
    for idx, pdI in enumerate(pdIdx):
        node = YZv[pdI]
        bus = node.split(".")[0]
        phs = int(YZv[pdI][-1])
        newPhs = phs + 1 - ((phs == 3) * 3)
        iTry = [1, 2, -2, -1, None]
        for itry in iTry:
            if itry is None:
                print("Finding idx complement failed!")
                continue
            tryBus = YZv[pdI + itry].split(".")[0]
            tryPhs = int(YZv[pdI + itry][-1])
            if bus == tryBus and newPhs == tryPhs:
                pdIdxCmp[idx] = pdI + itry
                break
    pdIdxUnq = np.unique(np.r_[pdIdx, pdIdxCmp])
    return pdIdxCmp, pdIdxUnq


def cpf_get_loads(DSSCircuit, getCaps=True):
    SS = {}
    BB = {}
    i = DSSCircuit.Loads.First
    while i != 0:
        SS[i] = DSSCircuit.Loads.kW + 1j * DSSCircuit.Loads.kvar
        BB[i] = DSSCircuit.Loads.Name
        i = DSSCircuit.Loads.Next
    imax = DSSCircuit.Loads.Count
    if getCaps:
        j = DSSCircuit.Capacitors.First
        while j != 0:
            SS[imax + j] = 1j * DSSCircuit.Capacitors.kvar
            BB[imax + j] = DSSCircuit.Capacitors.Name
            j = DSSCircuit.Capacitors.Next
    return BB, SS


def cpf_set_loads(DSSCircuit, BB, SS, k, setCaps=True, capPos=None):
    i = DSSCircuit.Loads.First
    while i != 0:
        # DSSCircuit.Loads.Name=BB[i]
        DSSCircuit.Loads.kW = k * SS[i].real
        DSSCircuit.Loads.kvar = k * SS[i].imag
        i = DSSCircuit.Loads.Next
    imax = DSSCircuit.Loads.Count
    if setCaps:
        if setCaps == True:
            if capPos == None:
                capPos = [k] * DSSCircuit.Capacitors.Count
            else:
                capPos = (k * np.array(capPos)).tolist()
        elif setCaps == "linCaps":
            if capPos == None:
                capPos = [1] * DSSCircuit.Capacitors.Count
            # otherwise use capPos
        j = DSSCircuit.Capacitors.First
        while j != 0:
            DSSCircuit.Capacitors.Name = BB[j + imax]
            DSSCircuit.Capacitors.kvar = (
                capPos[j - 1] * SS[j + imax].imag + 1e-4
            )  # so that the # of caps doesn't change...
            j = DSSCircuit.Capacitors.Next

    return


def get_idxs(e_idx, DSSCircuit, ELE):
    i = ELE.First
    while i:
        for BN in DSSCircuit.ActiveElement.BusNames:
            splt = BN.upper().split(".")
            if len(splt) > 1:
                for j in range(1, len(splt)):
                    if splt[j] != "0":  # ignore ground
                        e_idx.append(
                            DSSCircuit.YNodeOrder.index(splt[0] + "." + splt[j])
                        )
            else:
                try:
                    e_idx.append(DSSCircuit.YNodeOrder.index(splt[0]))
                except:
                    for ph in range(1, 4):
                        e_idx.append(
                            DSSCircuit.YNodeOrder.index(splt[0] + "." + str(ph))
                        )
        i = ELE.Next
    return e_idx


def get_element_idxs(DSSCircuit, ele_types):
    e_idx = []
    for ELE in ele_types:
        e_idx = get_idxs(e_idx, DSSCircuit, ELE)
    return e_idx


def printAB(A, B):
    pprint(dict(zip(A, B)))


def getBranchNames(DSSCircuit, xfmrSet=False):
    if not xfmrSet:
        i = DSSCircuit.PDElements.First
        branchNames = []
        while i:
            if not DSSCircuit.PDElements.IsShunt:
                branchNames = branchNames + [DSSCircuit.PDElements.Name]
            i = DSSCircuit.PDElements.Next
    elif xfmrSet:
        # nb this does NOT get the current in regulators because that changes with tap positions.
        regXfmrs = get_regXfmr2(DSSCircuit)
        i = DSSCircuit.Transformers.First
        branchNames = []
        while i:
            if DSSCircuit.Transformers.Name not in regXfmrs:
                branchNames = branchNames + [
                    "Transformer." + DSSCircuit.Transformers.Name
                ]
            i = DSSCircuit.Transformers.Next
    return tuple(branchNames)


def makeYprm(YprmTuple):
    yprm = tp2ar(YprmTuple)
    yprm = yprm.reshape([np.sqrt(yprm.shape)[0].astype("int32")] * 2)
    return yprm


def countBranchNodes(DSSCircuit):
    i = DSSCircuit.PDElements.First
    nodeNum = 0
    while i:
        if not DSSCircuit.PDElements.IsShunt:
            nodeNum = nodeNum + len(DSSCircuit.ActiveElement.NodeOrder)
        i = DSSCircuit.PDElements.Next
    return nodeNum


def getYzW2V(WbusSet, YZ):
    yzW2V = []
    for wbus in WbusSet:
        try:
            yzW2V.append(YZ.index(wbus.upper()))
        except:
            if wbus[-1] == "0":
                yzW2V.append(-1)  # ground node error
            else:
                print("No node", wbus.upper())
    return tuple(yzW2V)


def getV2iBrY(DSSCircuit, YprmMat, busSet):
    # get the modified voltage to branch current matrix for finding branch currents from voltages
    YZ = DSSCircuit.YNodeOrder
    idx = []
    for bus in busSet:
        if bus[-1] == "0":
            idx = idx + [-1]  # ground node
        else:
            try:
                idx = idx + [YZ.index(bus)]
            except:
                try:
                    idx = idx + [YZ.index(bus.upper())]
                except:
                    idx = idx + [-1]
                    print("Bus " + bus + " not found, set to ground.")
    # YNodeV = tp2ar(DSSCircuit.YNodeVarray)
    # YNodeVgnd = np.concatenate((YNodeV,np.array([0+0j])))
    # YNodeVprm = YNodeVgnd[idx] # below is equivalent to this, but does not require reindexing
    # Iprm = YprmMat.dot(YNodeVprm)
    Adj = sparse.lil_matrix(
        (len(idx), DSSCircuit.NumNodes + 1), dtype=int
    )  # NB if not sparse this step is very slow <----!
    Adj[np.arange(0, len(idx)), idx] = 1
    Adj.tocsr()
    v2iBrY = YprmMat.dot(Adj)
    v2iBrY = v2iBrY[:, :-1]  # get rid of ground voltage
    # Iprm = v2iBrY.dot(YNodeV)
    return v2iBrY


def printBrI(Wunq, Iprm):
    i = 0  # checking currents
    for unq in Wunq:
        print(unq + ":" + str(Iprm[i].real) + ", I imag:" + str(Iprm[i].imag))
        i += 1

    t0 = time.time()
    Ainv = linalg.inv(A.A)
    print("Inverse Time:", time.time() - t0)

    derivVP = (Bwye[:, :sizeV].T.dot(Ainv.T)).T[
        : 2 * sizeV
    ]  # Ainv is not sparse hence this is required
    derivVQ = (Bwye[:, sizeV:].T.dot(Ainv.T)).T[: 2 * sizeV]
    My = np.c_[
        derivVP[:sizeV] + 1j * derivVP[sizeV::], derivVQ[:sizeV] + 1j * derivVQ[sizeV::]
    ]
    print("Inverse 1 done.", time.time() - t0)
    del derivVP
    del derivVQ

    derivVP = (Bdelta[:, :sizeV].T.dot(Ainv.T)).T[: 2 * sizeV]
    derivVQ = (Bdelta[:, sizeV:].T.dot(Ainv.T)).T[: 2 * sizeV]

    Md = np.c_[
        derivVP[:sizeV] + 1j * derivVP[sizeV::], derivVQ[:sizeV] + 1j * derivVQ[sizeV::]
    ]
    print("Inversions complete", time.time() - t0)

    a = V - My.dot(xhy) - Md.dot(xhd)

    dMy = H.dot(My)
    dMd = H.dot(Md)
    da = H.dot(a)

    return My, Md, a, dMy, dMd, da


def get_regXfmr(DSSCircuit):
    i = DSSCircuit.RegControls.First
    regXfmr = []
    while i:
        regXfmr.append(DSSCircuit.RegControls.Transformer)
        i = DSSCircuit.RegControls.Next
    return regXfmr


def in_regs(DSSCircuit, regXfmr):
    type, name = DSSCircuit.ActiveElement.Name.split(".")
    in_regs = type.lower() == "transformer" and (name.lower() in regXfmr)
    return in_regs


def getRegNms(DSSCircuit):
    regNms = {}
    i = DSSCircuit.RegControls.First
    while i:
        name = DSSCircuit.RegControls.Name
        DSSCircuit.SetActiveElement("Transformer." + DSSCircuit.RegControls.Transformer)
        regNms[name] = DSSCircuit.ActiveElement.NumPhases
        i = DSSCircuit.RegControls.Next
    return regNms


def getRegSat(DSSCircuit):
    i = DSSCircuit.RegControls.First
    regSat = []
    while i:
        if (abs(DSSCircuit.RegControls.TapNumber)) == 16:
            regSat = regSat + [0]
        else:
            regSat = regSat + [1]
        i = DSSCircuit.RegControls.Next
    return regSat


def getRegBwVrto(DSSCircuit):  # see WB 15-01-19
    i = DSSCircuit.RegControls.First
    BW = []
    Vrto = []
    while i:
        BW = BW + [DSSCircuit.RegControls.ForwardBand]
        Vrto = Vrto + [DSSCircuit.RegControls.PTratio]
        i = DSSCircuit.RegControls.Next
    return BW, Vrto


def setRx(DSSCircuit, R, X):
    i = DSSCircuit.RegControls.First
    while i:
        DSSCircuit.RegControls.ForwardR = R[i]
        DSSCircuit.RegControls.ReverseR = R[i]
        DSSCircuit.RegControls.ForwardX = X[i]
        DSSCircuit.RegControls.ReverseX = X[i]
        i = DSSCircuit.RegControls.Next
    return


def get_reIdx(regIdx, n):
    reIdx = []
    for i in range(n):
        if i not in regIdx:
            reIdx = reIdx + [i]
    reIdx = reIdx + regIdx
    return reIdx


def get_regBrIdx(DSSCircuit, busSet, brchSet):

    regXfmrs = get_regXfmr(
        DSSCircuit
    )  # needs to be in this order to match the index order of other fncs
    regBus = []
    regBrIdx = []
    for regXfmr in regXfmrs:
        DSSCircuit.SetActiveElement("Transformer." + regXfmr)
        idx0 = brchSet.index("Transformer." + regXfmr)
        buses = vecSlc(
            busSet, np.where(np.array(brchSet) == "Transformer." + regXfmr)[0]
        )

        if DSSCircuit.ActiveElement.NumPhases == 1:
            bus = DSSCircuit.ActiveElement.BusNames[1]
        elif (
            DSSCircuit.ActiveElement.NumPhases == 3
        ):  # WARNING: assume connected to .1 (true is bus='')
            if DSSCircuit.ActiveElement.BusNames[1].count(".") == 4:
                bus = DSSCircuit.ActiveElement.BusNames[1].split(".", 1)[0] + ".1"
            else:
                bus = DSSCircuit.ActiveElement.BusNames[1] + ".1"
        regBus.append(bus)
        try:
            idx1 = buses.index(bus)
        except:
            idx1 = buses.index(bus.lower())
        regBrIdx = regBrIdx + [idx0 + idx1]
        # regIdx = regIdx + find_node_idx(node_to_YZ(DSSCircuit),bus,False)
    return regBrIdx


def zB2zBs(DSSCircuit, zoneBus):
    YZ = DSSCircuit.YNodeOrder
    YZclr = {}
    for yz in YZ:
        node, ph = yz.split(".")
        if node in YZclr.keys():
            YZclr[node] = YZclr[node] + [ph]
        else:
            YZclr[node] = [ph]
    nodeIn = []
    zoneBuses = []
    for bus in zoneBus:
        node = bus.upper().split(".", 1)[0]
        if node not in nodeIn:
            nodeIn = nodeIn + [node]
            for ph in YZclr[node]:
                zoneBuses = zoneBuses + [node + "." + ph]
    return zoneBuses


def get_regZneIdx(DSSCircuit):
    DSSEM = DSSCircuit.Meters
    # get transformers with regulators, YZ, n2y
    regXfmr = get_regXfmr(DSSCircuit)
    n2y = node_to_YZ(DSSCircuit)
    YZ = DSSCircuit.YNodeOrder

    zoneNames = []
    regSze = []
    yzRegIdx = []  # for debugging
    zoneIdx = []  # for debugging
    zoneBus = []  # for debugging
    zoneRegId = []
    i = DSSEM.First
    while i:
        zoneNames.append(DSSEM.Name)
        zoneBus.append([])
        zoneIdx.append([])
        yzRegIdx.append([])
        for branch in DSSEM.AllBranchesInZone:
            DSSCircuit.SetActiveElement(branch)
            if in_regs(DSSCircuit, regXfmr):
                zoneRegId = zoneRegId + [DSSEM.Name]
            else:
                for bus in DSSCircuit.ActiveElement.BusNames:
                    zoneBus[i - 1].append(bus)
                    if bus.count(".") == 0:
                        idx = find_node_idx(n2y, bus, False)
                        zoneIdx[i - 1].append(idx)
                        for no in idx:
                            if (no in yzRegIdx[i - 1]) == False:
                                yzRegIdx[i - 1].append(no)
                    else:
                        node = bus.split(".")[0]
                        phs = bus.split(".")[1:]
                        for ph in phs:
                            if ph != "0":  # added???
                                idx = find_node_idx(n2y, node + "." + ph, False)
                                zoneIdx[i - 1].append(idx)
                                for no in idx:
                                    if (no in yzRegIdx[i - 1]) == False:
                                        yzRegIdx[i - 1].append(no)

        yzRegIdx[i - 1].sort()
        regSze.append(len(yzRegIdx[i - 1]))
        i = DSSEM.Next

    zoneBuses = []
    for zb in zoneBus:
        zoneBuses.append(zB2zBs(DSSCircuit, zb))

    regUnq = []
    zoneTree = {}
    zoneList = {}
    i = 1
    for name in zoneNames:
        regUnq = []
        j = 0
        for reg in regXfmr:
            if reg[:-1] not in regUnq and name == zoneRegId[j]:
                regUnq = regUnq + [reg[:-1]]
            j += 1
        zoneTree[name] = regUnq
        zoneList[name] = zoneBuses[i - 1]
        i += 1
    regIdx = []
    for yzReg in yzRegIdx:
        regIdx = regIdx + yzReg
    # QWE = sum(np.concatenate(yzRegIdx))
    chk = len(YZ) * ((len(YZ) - 1) // 2)

    return zoneList, regIdx, zoneTree


def getRegTrn(DSSCircuit, zoneTree):  # find the number of transformers per regulator
    regNms = getRegNms(DSSCircuit)
    regTrn = {}
    for branch in zoneTree.values():
        for reg in branch:
            nPh = 0
            phs = []
            for regPh in regNms.keys():
                if reg in regPh:
                    nPh = nPh + 1
                    if regPh[-1] == "a":
                        phs = phs + [1]
                    if regPh[-1] == "b":
                        phs = phs + [2]
                    if regPh[-1] == "c":
                        phs = phs + [3]
                    if regPh[-1] == "g":
                        phs = [1, 2, 3]
            regTrn[reg] = [nPh, phs]
    return regTrn


def getZoneSet(feeder, DSSCircuit, zoneTree):
    # to help create the right sets:
    regNms = getRegNms(
        DSSCircuit
    )  # number of phases in each regulator connected to, in the right order
    regTrn = getRegTrn(DSSCircuit, zoneTree)  # number of individually controlled taps

    # It would be good to automate this at some point!
    if feeder == "13busRegModRx" or feeder == "13busRegMod3rg":
        zoneSet = {
            "msub": {},
            "mreg": {1: [0], 2: [1], 3: [2]},
            "mregx": {1: [0, 3], 2: [1, 4], 3: [2, 5]},
            "mregy": {1: [0, 6], 2: [1, 7], 3: [2, 8]},
        }
    elif feeder == "123busMod" or feeder == "123bus":
        zoneSet = {
            "msub": {},
            "mreg1g": {1: [0], 2: [], 3: []},
            "mreg2a": {1: [0, 1]},
            "mreg3": {1: [0, 2], 3: [3]},
            "mreg4": {1: [0, 4], 2: [5], 3: [6]},
        }
    elif feeder == "13busModSng":
        zoneSet = {
            "msub": {},
            "mreg0": {1: [0], 2: [0], 3: [0]},
            "mregx": {1: [0, 1], 2: [0, 2], 3: [0, 3]},
        }
    elif feeder == "34bus":
        zoneSet = {
            "msub": {1: [], 2: [], 3: []},
            "mreg1": {1: [0], 2: [0], 3: [0]},
            "mreg2": {1: [0, 3], 2: [1, 4], 3: [2, 5]},
        }
    elif feeder == "13busMod" or feeder == "13bus":
        zoneSet = {"msub": [], "mregs": {1: [0], 2: [1], 3: [2]}}
    elif feeder == "epriK1":
        zoneSet = {"msub": [], "mt2": {1: [0], 2: [], 3: []}}
    elif feeder == "epriM1":
        zoneSet = {"msub": [], "m1_xfmr": {1: [0], 2: [], 3: []}}
    else:
        print(feeder)
        print(regNms)
        print(regTrn)
        print(zoneTree, "\n\n")
    return zoneSet


def getZoneX(
    YZx, zoneList
):  # goes through each node and adds to the regulator list if it connected to that reg.
    zoneX = []
    for yz in YZx:  # for each node
        ph = int(yz[-1])  # get the phase
        for key in zoneList:  # for each key in the list of zones
            if yz in zoneList[key]:  # if the node is in that zoneList then
                zoneX.append([key, ph])  # add to this list for that regulator
    return zoneX


def get_regIdxMatS(YZx, zoneList, zoneSet, Kp, Kq, nreg, delta):
    # Find all zones and phases of nodes to which regs are attached
    zoneX = getZoneX(YZx, zoneList)

    regIdxPx = np.zeros((nreg, len(YZx)))
    regIdxQx = np.zeros((nreg, len(YZx)))
    i = 0
    for zone in zoneX:
        for key in zoneSet:
            if zone[0] == key:
                for regIdx in zoneSet[key][zone[1]]:
                    regIdxPx[regIdx, i] = Kp[i]
                    regIdxQx[regIdx, i] = Kq[i]
                if delta:
                    for regIdx in zoneSet[key][zone[1] % 3 + 1]:
                        regIdxPx[regIdx, i] = 1 - Kp[i]
                        regIdxQx[regIdx, i] = 1 - Kq[i]
        i += 1
    regIdxMatS = np.concatenate((regIdxPx, 1j * regIdxQx), axis=1)
    return regIdxMatS


def getZbusSns(self, d):
    idxIn = self.pyIdx + 3
    Zbus = sparseSvty(self.Ybus, d.getVsrc(), idxIn=idxIn)
    czbus = self.Vnl[self.pyIdx]
    # WITH THE FOLLOWING instantiation,
    # we see that V = ZI + a has been normalised as I = conj(1/V0)P (purely real), and then
    # W = (1/V0)V, so that W(0) is purely real. The interpretation for this, therefore,
    # is that the real part of ZbusPuKva is approximately the voltage magnitude drop on
    # the output as the output is nominally purely real.
    # Increasing the generation angle (generating vars) rotates everything clockwise.
    # CONVERTS to pu per kW
    ZbusPuKva = mvM(vmM(1 / czbus, Zbus), np.conj(1e3 / czbus))
    return ZbusPuKva


def plotZbusSns(self, ZbusPuKva, zbusIs=None):
    if zbusIs is None:
        zbusIs = [0, 3, 6, 9]
    fig, axs = plt.subplots(nrows=2, ncols=2, figsize=(8, 6.5))
    for zbusI, ax in zip(zbusIs, axs.flatten()):
        tSp = 2 * np.pi * np.linspace(0, 1, 301)
        circR = np.arange(2, 20)
        ax.plot(np.cos(tSp), np.sin(tSp), "k--", linewidth=0.6)
        minThng = int(np.floor(np.min(np.log10(abs(ZbusPuKva[:, zbusI])))))
        ax.text(1 - 0.03, -0.35, "$10^{" + str(minThng) + "}$")
        ax.plot(1, 0, "k|", markersize=7)
        ax.text(np.sqrt(3) - 0.03, -0.35, "$10^{" + str(minThng + 2) + "}$")
        ax.plot(np.sqrt(3), 0, "k|", markersize=7)
        for idx, r in enumerate(circR):
            ax.plot(
                np.sqrt(r) * np.cos(tSp),
                np.sqrt(r) * np.sin(tSp),
                linewidth=0.25,
                color=cm.matlab(idx % 6),
            )
            # yy = np.sqrt(1+idx+1); ax.text(0.035,yy,'$10^{'+str(minThng+idx+1)+'}$'); ax.plot(0,yy,'k.')

        ngl = np.angle(ZbusPuKva[:, zbusI])
        rds = np.sqrt(1 + np.log10(abs(ZbusPuKva[:, zbusI])) - minThng)
        ax.plot(
            rds * np.cos(ngl),
            rds * np.sin(ngl),
            "ko",
            markersize=2.5,
            markeredgewidth=0.6,
            markerfacecolor="None",
        )
        ax.plot(
            rds[zbusI] * np.cos(ngl[zbusI]),
            rds[zbusI] * np.sin(ngl[zbusI]),
            "bx",
            markersize=3,
        )
        ax.set_aspect("equal")
        ngles = np.pi * np.array([0, 1 / 2, 0.5 + (1 / 6), -1 / 6, -4 / 6, -5 / 6])
        nglesChrt = np.arccos(0.5 ** np.arange(10))
        r0 = 10
        for ngl in ngles:
            ax.plot([0, r0 * np.cos(ngl)], [0, r0 * np.sin(ngl)], "k", linewidth=0.5)
        for ngl in nglesChrt:
            ax.plot([0, r0 * np.cos(ngl)], [0, r0 * np.sin(ngl)], "k:", linewidth=0.35)
            ax.plot([0, r0 * np.cos(ngl)], [0, -r0 * np.sin(ngl)], "k:", linewidth=0.35)
            ax.plot(
                [0, -r0 * np.cos(ngl)], [0, -r0 * np.sin(ngl)], "k:", linewidth=0.35
            )
            ax.plot([0, -r0 * np.cos(ngl)], [0, r0 * np.sin(ngl)], "k:", linewidth=0.35)
        ax.set_title("Bus " + vecSlc(self.YZ, self.pyIdx)[zbusI])
        ax.set_xlim((-2.5, 2.5))
        ax.set_ylim((-2.5, 2.5))
        ax.text(1.6, 2, "Ph1")
        ax.text(1.6, -2, "Ph2")
        ax.text(-2, 1.7, "Ph3")

    plt.tight_layout()
    # plt.show()


def ntwkBusIdx(yzPy):
    ntwks = np.zeros(len(yzPy))
    fdrs = np.zeros(len(yzPy))
    for i, yz in enumerate(yzPy):
        ntwkFdr = yz.split("_")[0]
        ntwks[i] = int(ntwkFdr[:-1])
        fdrs[i] = int(ntwkFdr[-1])
    return ntwks, fdrs


def getVset(obj, vKvbase):
    obj.vc = obj.Vc / vKvbase
    obj.V = np.abs(obj.Vc)
    obj.v = obj.V / vKvbase


def getZthevSeq(YbusV, ldIdxV):
    # NOTE: thevenin impedances are NOT the same as short circuit
    # impedances, see grainger 8.2.  Tested on a balanced circuit (IEEE
    # 33 bus). YbusV is Ybus[3:,3:] usually, and ldIdxV is in YZv usually.
    # aa = np.array([1,np.exp(1j*np.pi*4/3),np.exp(1j*np.pi*2/3)])
    iZs = 1
    iPs = 1
    iNs = 1
    di = seq2phs.dot(np.r_[iZs, iPs, iNs])
    dI = np.zeros(YbusV.shape[0], dtype=complex)
    dI[ldIdxV] = di
    # iPs/Ns/Zs are all unity
    return phs2seq.dot(spla.spsolve(YbusV, dI)[ldIdxV])


# LVNS 'Bad Feeder' Data
badFdrs = {  # (ntwk, [feeder]),
    13: [4],
    14: [3],
    # 17:[2], # also has unbalance
    18: [2],
    19: [4],
    20: [3],
    # 5:[6], # seems to be a typo?
    5: [3],  # <-- Edited from Nando - feeder 6 seems to be OK...?!
    8: [2],  # <-- NOT from Nando - this has 5.0% 0-seq unbl
    7: [4],  # <-- NOT from Nando - this has 5.5% (!) 0-seq unbl
    # 7:[1], # <-- NOT from Nando - this has 3.0% (!) 0-seq unbl
    # 12:[1], # <-- NOT from Nando - this has 2% 0-seq unbl. thoug
    # 17:[7], # <-- NOT from Nando - this has 3% 0-seq unbl
    # 2:[4], # <-- NOT from Nando - undervoltages (below 0.95)
}

setFdrs = {  # (ntwk, [fdrs to take out])
    2: [1, 4],  # too big x2
    # 2:[1,2,3,4], # too big
    17: [1, 2, 7, 6],  # Nando + unbalance + Big x2 (see above)
    # 17:[1,2,4,5,6,7], # nando + unbalance + big x3
    15: [
        1,
        2,
        4,
    ],  # too big - remove 139 loads
    # 7:[1,4,], # NOT from Nando - unbalance of 3, 5.5% 0-seq unbl
}


def commentBadFdrs(ntwk, masterText, oneFlag=False):
    """Comment unwanted feeders from masterText for the network ntwk.

    The list of bad networks is From pg 17 of Dissemination Document
    "Low Voltage Networks Models and Low Carbon Technology Profiles".
    """
    if oneFlag:
        keySet = [{i: np.arange(2, 10) for i in range(1, 26)}]
    else:
        keySet = [badFdrs, setFdrs]

    for keyset in keySet:
        if ntwk in keyset.keys():
            lines = masterText.split("\n")
            fdrs = keyset[ntwk]
            newlines = []
            for line in lines:
                condition = [
                    f"Feeder_{ff}" in line or f"feeder{ff}" in line for ff in fdrs
                ]

                if any(condition) and "Transformers" not in line:
                    newlines.append("!" + line)
                else:
                    newlines.append(line)
            masterText = "\n".join(newlines)

    return masterText
