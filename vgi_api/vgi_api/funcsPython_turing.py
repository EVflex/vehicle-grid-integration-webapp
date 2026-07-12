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
# DIFFERENCES FROM THE ORIGINAL (v0) funcsPython_turing.py
# --------------------------------------------------------
# One change: `from bunch import *` became `from ._bunch import Bunch`.
# The abandoned `bunch` package (last release 2011) cannot be installed on
# Python >= 3.11, and only its Bunch class was ever used — it is vendored in
# vgi_api/_bunch.py. See the CHANGE(py3.14) comment at the import site and
# CHANGES.md §12.2. No functional change.

import sys, os, csv, socket, shutil, pickle, subprocess
from matplotlib import rcParams
import traceback
import matplotlib.pyplot as plt
from scipy import sparse
import numpy as np
from pprint import pprint
from datetime import datetime
from datetime import datetime, date, timedelta
from dateutil import tz
from time import ctime
# CHANGE(py3.14): the abandoned `bunch` package no longer installs on
# Python >= 3.11; only its Bunch class was used (see vgi_api/_bunch.py).
from ._bunch import Bunch
from collections import OrderedDict as odict

from matplotlib.collections import PatchCollection
from matplotlib.patches import Rectangle
from matplotlib.colors import ListedColormap, LinearSegmentedColormap
from numpy.random import MT19937, Generator, SeedSequence
from govuk_bank_holidays.bank_holidays import BankHolidays
from matplotlib import cm
from cmocean import cm as cmo
from hsluv import hsluv_to_rgb


# A useful set of directories for saving/loading data from etc
fd = os.path.dirname(__file__)

computerName = socket.gethostname()
if computerName in ["20s-merz-201148", "19s-merz-100030"]:
    supergenDir = r"H:\supergen"
    fnD = r"D:\DocumentsD_l\turing_vgi\e4Future-collab\mtd-dss-digital-twins".lower()
    if fnD in sys.argv[0].lower():
        fn_root = fnD
    else:
        fn_root = fnD

    papersDir = r"D:\DocumentsD_l\papersWorking"
elif computerName == "MattsPC":
    supergenDir = r"C:\Users\Matt\Documents\supergen"
else:
    current_dir = os.path.dirname(os.path.realpath(__file__))
    print(
        "\n*****\nUnidentified computer\nUsing {} as root folder\n*****\n".format(
            current_dir
        )
    )
    fn_root = current_dir

scriptCallingName = sys.argv[0].split("\\")[-1].split(".")[0]
gDir = os.path.join(fn_root, "gallery", scriptCallingName)

fn_mx = os.path.join(fd, "demand", "mixergyData")
fn_ntwx = os.path.join(fd, "networks")
fn_rslt0 = os.path.join(fn_root, "results")
fn_misc = os.path.join(fn_root, "miscScripts")
fn_wthr = os.path.join(fd, "weatherData")
fn_spnt = os.path.join(os.path.dirname(fd), "SenSprint", "processed")

es = "exec( open(r'" + sys.argv[0] + "').read() )"


def rngSeed(
    seed=0,
):
    """Create a numpy random number generator, seeded with seed.

    If seed is None, then return an unseeded random number generator."""
    if seed is None:
        return Generator(MT19937())
    else:
        return Generator(MT19937(SeedSequence(seed)))


def oss(fn):
    """Convenience function, as os.startfile(fn)."""
    os.startfile(fn)


def ossf(obj):
    """Convenience function, runs oss(obj.__file__)."""
    oss(obj.__file__)


def ossm(package):
    """Import [str] package, then open the location using ossf."""
    exec("import " + package)
    exec(f"ossf({package})")


def checkGi():
    with open(os.path.join(sys.path[0], ".gitignore")) as file:
        gi = file.read()
    subset = ["demand"]
    gi = gi.split("\n")
    gi = [line.split("/") for line in gi]
    dirs = [os.path.join(sys.path[0], *file) for file in gi[1:-1]]
    notIn = [path for path in dirs if not os.path.exists(path)]
    notInStp = [line[len(sys.path[0]) + 1 :] for line in notIn]
    gIn = [path for path in dirs if os.path.exists(path)]
    gInTms = [ctime(os.path.getmtime(path)) for path in gIn]
    gInStp = [[line[len(sys.path[0]) + 1 :], tms] for line, tms in zip(gIn, gInTms)]

    maxLenA = max([len(line[0]) for line in gInStp])
    lenB = len(gInStp[0][1])

    ctoff = "-" * 12
    print("\n" + ctoff + "\nFiles/folders that do not exist:\n" + ctoff)
    pprint(notInStp)
    print(ctoff + "\n\n" + ctoff + "\nFiles/folders that exist:\n" + ctoff)
    header = ["FILENAME:", "DATE MODIFIED:"]
    row_format = "{:" + str(maxLenA + 4) + "}{:" + str(lenB) + "}"
    print(row_format.format(*header))
    for row in gInStp:
        print(row_format.format(*row))
    print(ctoff + "\n")


def fPrmsInit(sd=None, fs0=None):
    """A dict for collecting various figure plotting options, functions etc.

    These are often used with sff/saveFigFunc, so see help for them for some
    ideas to make kwargs most appropriate.
    """
    if fs0 is None:
        fs0 = rcParams["figure.figsize"]
    if sd is None:
        sd = os.path.dirname(__file__)
    fPrmDict = {
        "saveFig": False,
        "showFig": True,
        "figSze": fs0,
        "figSzeSubfig": [fs0[0] / 1.8, fs0[1]],  # reduce somewhat
        "sd": sd,
        "figname": None,
        "dpi": 300,  # From here, kwargs are for saveFigFunc.
        "pdf": True,
        "svg": False,
        "gOn": True,
        "pad_inches": 0.02,
    }
    return fPrmDict


class struct(object):
    # from https://stackoverflow.com/questions/1878710/struct-objects-in-python
    pass


class structKeyword(struct):
    def __init__(self, kw=[], kwDict={}):
        self.kw = kw
        self.kwInit(kwDict)

    def kwInit(self, kwDict):
        for key, val in kwDict.items():
            if key in self.kw:
                setattr(self, key, val)
            else:
                print("Not setting key-value pair to Lin Model:", key, val)
        for key in self.kw:
            if not hasattr(self, key):
                setattr(self, key, None)

    def additem(self, kw, kwval):
        self.kw = self.kw + [kw]
        setattr(self, kw, kwval)

    def setitem(self, kw, kwval):
        if kw in self.kw:
            setattr(self, kw, kwval)
        else:
            raise AttributeError("No keyword of type", kw)

    def __getitem__(self, keys):
        """k[key] <=> k.key

        Is 'overloaded' to allow a set of keys, as in k[a,b] <=> k.a.b,
        or k[(a,b,)] = k.a.b
        """
        if type(keys) is tuple:
            val = getattr(self, keys[0])
            for k in keys[1:]:
                val = getattr(val, k)
        else:
            val = getattr(self, keys)
        return val

    def __setitem__(self, key, val):
        """Defined to allow self[key] = val"""
        if type(key) is tuple:
            obj = self[key[:-1]]
            setattr(obj, key[-1], val)
        else:
            setattr(self, key, val)

    def asdict(self):
        return {key: getattr(self, key) for key in self.kw}

    def __iter__(self):
        return iter(self.asdict().items())


class structDict(structKeyword):
    """Enter a kwDict [kw:val] to create with __init__."""

    def __init__(self, kwDict):
        self.kw = list(kwDict.keys())
        self.kwInit(kwDict)

    def setitem(self, kw, kwval):
        super().setitem(kw, kwval)


def whocalledme(depth=2):
    """Use traceback to find the name (string) of a function that calls it.

    Depth:
    1 - this function
    2 - is the default number, finds the function that calls this function
    3 - the function above that
    4 - the function above that (etc...)
    """
    names = []
    for line in traceback.format_stack():
        whereNwhat = line.strip().split("\n")[0]
        names.append(whereNwhat.split(" ")[-1])
    return names[-depth]


def csvIn(
    fn,
    hh=True,
):
    """Uses the CSV object reader to read in a csv file.

    Assumes the first line is a header with the row names, the rest the
    data of the file.

    Inputs
    ---
    fn - the filename to read
    hh - if True, the return a head first.

    Returns
    ---
    head - the first line of the csv
    data - the rest of the lines of the data.

    """
    with open(fn, "r") as file:
        csvR = csv.reader(file)
        if hh:
            head = csvR.__next__()

        data = list(csvR)

    if hh:
        return head, data
    else:
        return data


def sff_legacy(fPrm, figname=None):
    """Use fPrm['figname'] to overwrite figname names to saveFigFunc.

    Side effect of reversing the title back to None, if 'saveFig' is on.

    Appears to be intended for use when saving multiple figures to a
    particular place.

    Also, it can be convenient to define a self._sff() function to
    call in self.fPrm automatically to save a few lines of code.

    The 'fPrm' dict should have
    - 'saveFig': flag to save or not
    - 'figname': if saveFig, then saves figure as this then set to None
    - 'showFig': flag to show figure
    - 'sd':      save directory to send to saveFigFunc

    WARNING - note that 'fPrm' figname has priority over passing in figname.

    """
    if fPrm["saveFig"]:
        if fPrm["figname"] is None:
            if figname is None:
                fPrm["figname"] = whocalledme(depth=3)
            else:
                fPrm["figname"] = figname

        saveFigFunc(**fPrm)
        fPrm["figname"] = None  # revert back to base after setting

    if fPrm["showFig"]:
        plt.show()


def sff(fn, tlFlag=True, **kwargs):
    """Convenience func to call saveFigFunc with fn as the figname arg.

    kwargs passed in go straight through to saveFigFunc; the exception is
    tlFlag which calls tight_layout() to tidy things up; this can be disabled
    as necessary for some figures.
    """
    if tlFlag:
        tl()

    saveFigFunc(
        figname=fn,
        **kwargs,
    )


def o2o(x, T=False):
    """If x is ndim=1, convert to ndim=2 as a vector; and vice versa.

    o2o as in 'one-to-one' vectors - is intended to allow statements such as
    X/y when y is only one dimension (and numpy then complains).

    If x.ndim==1:
    - T flag False [default] -> column vector
    - T flag True -> row vector.
    """
    if x.ndim == 2:
        return x.flatten()
    elif x.ndim == 1:
        if T:
            return x.reshape((1, -1))
        else:
            return x.reshape((-1, 1))


def saveFigFunc(sd=gDir, **kwargs):
    """A simple wrapper function to save figures to sd.

    Always writes to a png file.

    If figname is not passed, the figure is named after the function that
    calls this function (as if by magic! ;) )

    If you want an EMF for inclusion with Word etc, the process is only
    semi-automated, as it seems that an inkscape conversion is required, which
    (at the moment) is called outside of python in svg_to_emf (see NCL
    emails). This would be nice functionality to add in future though :)

    By default, the script saves a lo-res png to the gallery as well.

    Use 'cleanGallery' to clear all pngs in a gallery.
    ----
    kwargs
    ----
    figname: if specified, is the name of the figure saved to sd directory.
    dpi: dpi for png
    pdf: if True, also save as pdf
    svg: if True, also save as svg
    emf: if True, also save as an emf (saves both emf + svg)
    gOn: whether or not to save a (lo-res) png to the gallery folder
    pad_inches: inches to pad around fig, nominally 0.05
    sd_mod: if passed in, modifies the sd to sd/sd_mod

    """
    kwd = {
        "dpi": 300,
        "pdf": False,
        "svg": False,
        "emf": False,
        "gOn": True,
        "pad_inches": 0.05,
        "figname": None,
        "sd_mod": None,
    }
    kwd.update(kwargs)
    sd_mod = kwd["sd_mod"]

    # create the gallery directory if not existing
    if not os.path.exists(gDir):
        os.mkdir(gDir)
        print("Created new gallery folder:", gDir)

    # For sd_mod, create file if not existing (first checks for sd)
    gDir_dn = gDir if sd_mod is None else os.path.join(gDir, sd_mod)

    if not sd_mod is None:
        if not os.path.exists(sd):
            raise Exception("Create initial sd first!")

        # Then create sd if it doesn't exist
        sd = sd if sd_mod is None else os.path.join(sd, sd_mod)
        _ = os.mkdir(sd) if not os.path.exists(sd) else None
        _ = os.mkdir(gDir_dn) if not os.path.exists(gDir_dn) else None

    # simple script that, by default, uses the name of the function that
    # calls it to save to the file directory sd.
    print(whocalledme())
    if kwd["figname"] is None:
        kwd["figname"] = whocalledme(depth=3)

    fn = os.path.join(sd, kwd["figname"])
    print("\nSaved with saveFigFunc to\n ---->", fn)
    plt.savefig(fn + ".png", dpi=kwd["dpi"], pad_inches=kwd["pad_inches"])

    # Then save extra copies as specified.
    if kwd["pdf"]:
        plt.savefig(fn + ".pdf", pad_inches=kwd["pad_inches"])
    if kwd["svg"] or kwd["emf"]:
        plt.savefig(fn + ".svg", pad_inches=kwd["pad_inches"])
    if kwd["emf"]:
        iscpPath = r"C:\Program Files\Inkscape\bin\inkscape.exe"
        subprocess.run(
            [
                iscpPath,
                fn + ".svg",
                "--export-filename",
                fn + ".emf",
            ]
        )
    if kwd["gOn"]:
        fn_gallery = os.path.join(gDir_dn, kwd["figname"])
        if fn_gallery != fn:
            plt.savefig(fn_gallery + ".png", dpi=100, pad_inches=kwd["pad_inches"])


def dds(data, n=5, *, cut=False, nan=False):
    """Data down-sample by n.

    data: dataset to downsample,
    n: number of downsample points,
    cut (keyword): remove datapoints at the end of data if not whole no. sets
    nan (keyword): calculated the nanmean rather than mean

    NB: if data is a time series and 'cut' is True, then the time variable t
    needs to be t = [::n][:-1].
    """

    if (data.shape[0] % n) != 0:
        if not cut:
            raise ValueError(
                "\n\nDDS data shape: {},\nDDS n = {},".format(*[data.shape, n])
                + "\n\t--> DDS failed!"
                + "\n\nUse cut=True opt to cut data.)"
            )
        else:
            data = data.copy()  # get rid of link to input data
            data = data[: -((len(data) % n))]
    if nan:
        # Not that well studied - updated 3/3/21
        x = []
        for i in range(len(data) // n):
            x.append(np.nanmean(data[i * n : (i + 1) * n]))
        return x
    else:
        return sparse.kron(sparse.eye(len(data) // n), np.ones(n)).dot(data) / n


def ppd(thing, fltr=None):
    """Pretty print dir(thing); with a simple first letter filter fltr."""
    pprint(letterFilter(dir(thing), fltr))


def ppdd(thing, fltr=None):
    """Pretty print sorted(vars(thing)), with optional first letter fltr."""
    pprint(letterFilter(sorted(vars(thing)), fltr))


def letterFilter(nms, fltr):
    if not fltr is None:
        nms = [nm for nm in nms if nm[0] == fltr]
    else:
        pass
    return nms


def getIdxMask(strList, strMatch):
    mask = []
    for i, item in enumerate(strList):
        if strMatch in item:
            mask.append(i)
    return mask


def ms2date(ms):
    if len(ms) == 1:
        dts = datetime.fromtimestamp(ms / 1e3)
    else:
        dts = []
        for t in ms:
            dts.append(datetime.fromtimestamp(t / 1e3))
    return dts


def sp2utc(dtm, sp):
    """Convert datetime-sp pair to UTC time.

    Note that 'loadSp2utcDict' might be faster if a load of
    these are required.
    """
    utc = tz.gettz("UTC")
    toZne = tz.gettz("London")
    if dtm.tzinfo is None:
        dtm = dtm.astimezone(toZne)
    dtm = dtm + (sp - 1) * timedelta(0, 60 * 30)
    return dtm.astimezone(utc)


def printNsum(dct, full=True):
    if full:
        n = 0
        P = 0
        for key, val in dct.items():
            n += len(val)
            P += sum(val)
    if not full:
        pprint(dct)
        print(sum(dct.values()))


def mtList(N):
    return [[] for _ in range(N)]


def mtDict(keys):
    """Return a dict with all of keys set to empty lists."""
    mtDict = {}
    mtDict.update(zip(keys, mtList(len(keys))))
    return mtDict


def mtDicts(N):
    return [{} for _ in range(N)]


def cleanFolder(folder):
    """Delete all files in folder.

    From stackoverflow "How to delete the contents of a folder?" for python.
    """
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print("Failed to delete %s. Reason: %s" % (file_path, e))


def get_path_dirs(path, mode="paths"):
    """Get directories/folders in path (is reasonably reliable).

    Sometimes fails, e.g., with .git files, for whatever reason.

    See email notes for where this comes from.

    mode: either
    - 'paths' (returns full path), or
    - 'names' (returns just the directory names)
    """
    if mode == "paths":
        return [f.path for f in os.scandir(path) if f.is_dir()]
    elif mode == "names":
        return [f.name for f in os.scandir(path) if f.is_dir()]


def get_path_files(path, mode="paths", ext=None):
    """Get the files in the folder path.

    Dual of get_path_dirs - see for doc.
    """
    if mode == "paths":
        lst = [f.path for f in os.scandir(path) if not f.is_dir()]
    elif mode == "names":
        lst = [f.name for f in os.scandir(path) if not f.is_dir()]

    if ext is None:
        return lst
    else:
        return [f for f in lst if f.split(".")[-1] == ext]


def cleanGallery(scriptName=None):
    """Clean the gallery folder for the current script."""
    if scriptName is None:
        folder = gDir
    else:
        folder = os.path.join(sys.path[0], "gallery", scriptName)

    cleanFolder(folder)


def openGallery():
    """Equivalent to os.startfile(gDir)."""
    os.startfile(gDir)


def tset2stamps(t0, t1, dt):
    """Numpy timeseries starting at t0, ending t1, timestep dt."""
    return np.arange(t0, t1 + dt, dt, dtype=object)


def tDict2stamps(tDict):
    """Parameter tDict has keys t0, t1, dt.

    Uses tset2stamps to build the time set."""
    return tset2stamps(tDict["t0"], tDict["t1"], tDict["dt"])


def listT(l):
    """Return the 'transpose' of a list."""
    return list(map(list, zip(*l)))


def boxplotcolor(xx, c0=None, c1=None, ax=None, flierprops=None, **pargs):
    """A convenience function for creating colored boxplots.

    Inputs
    ---
    *pargs - plotting arguments to go into plt.boxplot, could include
            - positions, the locations of xx
            - widths, the widths of the boxes
    ax - ax to plot on
    flierprops - properties to pass to the boxplot
    c0 - the main color of the boxplot
    c1 - the secondary color of the boxplot

    Returns
    ---
    ax - the axes that it has been plotted on

    """
    if ax is None:
        fig, ax = plt.subplots()

    if c0 is None:
        c0 = "C1"
    if c1 is None:
        c1 = c0

    if flierprops is None:
        flierprops = {
            "marker": ".",
            "markeredgecolor": c1,
            "markerfacecolor": c1,
            "markersize": 3,
            "zorder": -10,
        }

    flierprops["markeredgecolor"] = c1
    flierprops["markeredgecolor"] = c1

    box1 = ax.boxplot(xx, **pargs, flierprops=flierprops)
    for item in ["boxes", "whiskers", "fliers", "medians", "caps"]:
        plt.setp(box1[item], color=c0)


def boxplotqntls(qVals, ax=None, **kwargs):
    """A function for plotting boxplots with given quantiles.

    Similar to 'fillplot'

    Inputs
    ---
    qVals - 5 x N
    ax - the axis to plot onto

    kwargs
    ---
    - xPos as the N-length positions of the qVals
    - width as the width of the plots as a function of xPos (0 to 1)
    - lw as the plot linewidths
    - edgecolors as the color[s] of the box edges & whiskers
    - facecolors as the color[s] of the box face (default None)
    - alpha as the alpha of the box face (default 1)

    Returns
    ---
    ax - the axis plotted onto

    """
    width = kwargs.get("width", 0.6)
    lw = kwargs.get("lw", 0.8)
    N = len(qVals[0])
    xPos = kwargs.get("xPos", np.arange(N))

    ec = kwargs.get("edgecolors", ["k"] * N)
    fc = kwargs.get("facecolors", ["None"] * N)
    lph = kwargs.get("alpha", 1)

    if len(ec) == 1:
        ec = [ec] * N
    if len(fc) == 1:
        fc = [fc] * N

    if ax is None:
        fig, ax = plt.subplots()

    if len(xPos) == 1:
        dw0 = 1
        if type(ec) is list:
            ec = ec[0]
        if type(fc) is list:
            fc = fc[0]
    else:
        dw0 = width * (xPos[1] - xPos[0])

    dw1 = dw0 * 0.6

    ax.vlines(xPos, qVals[0], qVals[1], linewidth=lw, color=ec)
    ax.vlines(xPos, qVals[-2], qVals[-1], linewidth=lw, color=ec)
    ax.hlines(qVals[0], xPos - dw0 / 2, xPos + dw0 / 2, linewidth=lw, color=ec)
    ax.hlines(qVals[-1], xPos - dw0 / 2, xPos + dw0 / 2, linewidth=lw, color=ec)

    # plot the box and median
    ax.hlines(qVals[2], xPos - dw1 / 2, xPos + dw1 / 2, linewidth=lw, color=ec)

    boxes = [
        Rectangle(
            (xPos[i] - (dw1 / 2), qVals[1][i]),
            width=dw1,
            height=qVals[3][i] - qVals[1][i],
            angle=0,
            linewidth=lw,
            facecolor=fc[i],
            edgecolor=ec[i],
            alpha=lph,
        )
        for i in range(N)
    ]

    # Why: see SO "How do I set color to Rectangle in Matplotlib?"
    for box in boxes:
        ax.add_artist(
            box,
        )

    return ax


def fillplot(data, t, qntls=None, **kwargs):
    """A function for creating/reminding to create a 'fill plot'.

    Inputs
    ----
    data - either a ready-made set of quantiles as a list, or a dataset.
    t - the corresponding independent variable (ie 'time' or the y value)
    qntls - if passing in a dataset, this calculates quantile vals
    kwargs - Options are:
            1. figsize, for the size of the figure.
            2. ax, if there is an axis ready to plot onto
            3. fillKwargs, to change the kwargs passed to fill_between
            4. lineClrs, Colours of the quantile lines

    Returns
    ----
    ax - the figure axis

    """

    fillKwargs = {
        "alpha": 0.15,
        "zorder": -10,
        "color": "C0",
    }

    fillKwargs.update(kwargs.get("fillKwargs", {}))

    figsize = kwargs.get("figsize", rcParams["figure.figsize"])
    ax = kwargs.get("ax", None)
    lineClrs = kwargs.get("lineClrs", ["C0-", "C0-", "k-"])

    if qntls is None and not type(data) is list:
        qntls = [0, 0.25, 0.5, 0.75, 1]

    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)

    if type(t) is datetime:
        axPlt = ax.plot_date
    else:
        axPlt = ax.plot

    if not type(data) is list:
        iSet = np.quantile(data, qntls, axis=1)
    else:
        iSet = data

    iMedian = iSet[len(iSet) // 2]
    iPairs = [[iSet[i], iSet[-i - 1]] for i in range(len(iSet) // 2)]

    pltStf = axPlt(t, iMedian, lineClrs[-1], linewidth=0.8)
    for iXs, clr in zip(iPairs, lineClrs):
        for iX in iXs:
            axPlt(pltStf[0]._x, iX, clr, linewidth=0.3)

    for iValA, iValB in iPairs:
        ax.fill_between(pltStf[0]._x, iMedian, iValA, **fillKwargs)
        ax.fill_between(pltStf[0]._x, iMedian, iValB, **fillKwargs)

    return ax, iSet


# ================================ developed alongside 'workflowRiskday.py'
def basicTblDict(caption, label, dataDict, TD, headRpl=None):
    """Takes dict with key,vals as head/data and runs basicTblSgn.

    Is just a simple convenience function for basicTblSgn really.

    Inputs
    ---
    caption, label, TD, headRpl - see basicTblSgn
    dataDict - a dict with key as the heading of a row and values as a list of
                strings to populate the table with.

    Returns
    ---
    latexText - see basicTblSgn

    """
    heading = list(dataDict.keys())
    data = listT([val for val in dataDict.values()])

    return basicTblSgn(
        caption,
        label,
        heading,
        data,
        TD,
        headRpl=headRpl,
    )


def basicTblSgn(caption, label, heading, data, TD, headRpl=None, cp=0):
    """Creates a latex-style table.

    NB Based on 'basicTable' from 'dss_python_funcs.py'
    creates a simple table. caption, label, TD (table directory) are strings;
    heading is a list of strings, and data is a list of lists of strings,
    each sublist the same length as heading.

    See also: basicTblDict

    Inputs
    ---
    caption: the table caption
    label: the table label, i.e., \ref{t:label}
    heading: The headings for each row of the table
    data: a list of lists of strings to populate the table
    TD: the table directory.
    headRpl: use this to replace the heading prior to saving. Useful when
            creating more complex tables with multiple rows etc.
    cp: caption Position - if 1, sets to bottom, otherwise top.

    Returns
    ---
    latexText - the text written to TD + label + '.tex'.

    """
    if not (TD[-1] == "\\"):
        TD = TD + "\\"

    if headRpl is None:
        headTxt = ""
        for head in heading:
            headTxt = headTxt + head + " & "

        headTxt = headTxt[:-3]
        headTxt = headTxt + " \\\\\n"
    else:
        headTxt = headRpl
    nL = len(heading) * "l"

    dataTxt = ""
    for line in data:
        if len(line) != len(heading):
            print("\nWarning: length of line does not match heading length.\n")
        for point in line:
            dataTxt = dataTxt + point + " & "
        dataTxt = dataTxt[:-3]
        dataTxt = dataTxt + " \\\\\n"

    if cp == 0:
        latexText = (
            "% Generated using basicTblSgn.\n\\centering\n\\caption{"
            + caption
            + "}\\label{t:"
            + label
            + "}\n\\begin{tabular}{"
            + nL
            + "}\n\\toprule\n"
            + headTxt
            + "\\midrule\n"
            + dataTxt
            + "\\bottomrule\n\\end{tabular}\n"
        )
    elif cp == 1:
        latexText = (
            "% Generated using basicTblSgn.\n\\centering\n"
            "\n\\begin{tabular}{"
            + nL
            + "}\n\\toprule\n"
            + headTxt
            + "\\midrule\n"
            + dataTxt
            + "\\bottomrule\n\\end{tabular}\n\\caption{"
            + caption
            + "}\\label{t:"
            + label
            + "}\n"
        )

    with open(TD + label + ".tex", "wt") as handle:
        handle.write(latexText)
    return latexText


# ================================


def getBankHolidays():
    """Use the gov.uk Python package to get bank holiday data."""
    bank_holidays = BankHolidays()
    bHols = bank_holidays.load_backup_data()["england-and-wales"]["events"]
    bHolD = []
    for event in bHols:
        bHolD.append(date(*[int(v) for v in event["date"].split("-")]))
    return bHolD


def getNonBusiness(t):
    """Return a Bunch object, returning True if a weekend or bank holiday.

    Note that the old version of this code seemed to be dud (!)

    """
    bHolD = getBankHolidays()
    B = [(dt.weekday() > 4) or (dt.date() in bHolD) for dt in t]
    return Bunch({"t": t, "x": np.array(B, dtype=bool)})


def data2csv(fn, data, head=None):
    """Write list of lists 'data' to a csv.

    If head is passed, put as the first row.
    """
    if not head is None:
        data = [head] + data

    with open(fn, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(data)


def saveDataFunc(fn, mode="pkl", **kwargs):
    """A simple function for saving data as a .pkl file in a standard way.

    The data is picked straight into fn - this function is mostly used to
    provide a nice standard interface for later.

    NB - copied from MiscUtils from the Sprint.

    Inputs
    -----
    - mode: 'pkl' (default) or 'csv'. Former is one file, later has a seperate
            readme text file.

    kwargs
    --
    Metadata options:
    - readme: string

    Data options:
    - data: numpy array, preferably of FLOAT/INT data
    - dataHead: provide with data, listing the column headings
    # - flags: numpy array of BOOL data # <- out of use
    # - flagsHead: provide with flags to list column headings # <- out of use

    Time series time options:
    - tStamps: full timestamps numpy array, in terms of python datetime obj
    - tDict: option to save as {t0,t1,dt} dictionary to save on memory
            (use tDict2stamps func (above) to convert back to tStamps)

    Note that this only has very rudimentary error checking at this stage.
    """
    keysAllowed = {
        "readme",
        "data",
        "dataHead",
        "tStamps",
        "tDict",
    }

    if not set(kwargs.keys()).issubset(keysAllowed):
        raise Exception("Illegal kws passed to saveDataFunc")

    if fn.split(".")[-1] != mode:
        fn0 = fn
        fn += "." + mode
    else:
        fn0 = fn.split(".")[0]

    if mode == "pkl":
        with open(fn, "wb") as file:
            pickle.dump(kwargs, file)
            print(f"\nData written to:\n--->\t{fn}\n")

    elif mode == "csv":
        head = ["IsoDatetime"] + kwargs.get("dataHead", ["data"])
        if "tDict" in kwargs.keys():
            tt = tDict2stamps(kwargs["tDict"])
        elif "tStamps" in kwargs.keys():
            tt = kwargs["tStamps"]

        data = kwargs["data"]
        if data.ndim == 1:
            data = data.reshape((-1, 1))

        csvData = [[t.isoformat()] + x.tolist() for t, x in zip(tt, data)]
        data2csv(fn, csvData, head)

        if "readme" in kwargs.keys():
            with open(fn0 + "_readme.txt", "w") as file:
                file.write(kwargs["readme"])

        print(f"\nData written to:\n--->\t{fn}\n")


def tl():
    """Convenience function, plt.tight_layout()"""
    plt.tight_layout()


def tlps():
    """Convenience: plt.tight_layout(), plt.show()"""
    tl()
    plt.show()


def set_day_label(
    hr=3,
    t=False,
    ax=None,
):
    """Convenience function for setting the x label/ticks for day plots.

    hr - number of hours to 'jump' in xticks
    t - 'tight' or not, if True then fit to (0,23), else (-0.3,23.3)
    ax - the axis to plot on, if wanted.
    """
    if ax is None:
        plt.xticks(np.arange(0, 24, hr))
        if t:
            plt.xlim((0, 23))
        else:
            plt.xlim((-0.3, 23.3))

        plt.xlabel("Hour of the day")
    else:
        ax.set_xticks(np.arange(0, 24, hr))
        if t:
            ax.set_xlim((0, 23))
        else:
            ax.set_xlim((-0.3, 23.3))

        ax.set_xlabel("Hour of the day")


def gdv(dd, n=0):
    """Get-dict-val; returns n-th val of dict dd."""
    return dd[list(dd.keys())[n]]


def gdk(dd, n=0):
    """Get-dict-key; returns n-th key of dict dd."""
    return list(dd.keys())[n]


def mtOdict(ll):
    """Create an odict with not-linked lists as elements for each key in ll."""
    od = odict()
    [od.__setitem__(k, []) for k in ll]
    return od


# Colormap functions and data
def cmsq(
    cmap,
    ds0=0,
    ds1=1,
    n=256,
):
    """Squash/squish/sqsh a colormap that runs between 0 and 1.

    See:
    https://matplotlib.org/stable/tutorials/colors/colormap-manipulation.html
    """
    return ListedColormap(cmap(np.linspace(ds0, ds1, n)))


cmList0 = [
    cm.Greys,
    cm.Blues,
    cmo.amp,
    cm.Greens,
    cm.Purples,
    cmo.tempo,
    cm.bone_r,
    cm.PuRd,
    cm.Oranges,
]


def make_hsl_colormaps(
    nn=9,
    ltnss_tpl=(87, 15, 256),
    sat=100,
):
    """Use hsluv package to create equidistance colormaps for plotting.

    Inputs
    ---
    nn - number of hues to get, integer
    ltnss_tpl - the lightness tuple to get (hi,lo,N)
    sat - saturation, between 0 and 100
    """
    cmaps_ = []
    for hue in 360 * np.linspace(0, 1, nn)[::-1]:
        cmaps_.append(
            [hsluv_to_rgb((hue, sat, ltnss)) for ltnss in np.linspace(*ltnss_tpl)]
        )

    return [ListedColormap(cmap) for cmap in cmaps_]


def new_hsl_map(
    nn,
    sat=80,
    ll=50,
):
    """New hsluv colormap, cycling through nn colors."""
    return [hsluv_to_rgb((v, sat, ll)) for v in np.arange(0, 360, 360 / nn)]


def og():
    """Run openGallery(). [See help(openGallery)]"""
    return openGallery()
