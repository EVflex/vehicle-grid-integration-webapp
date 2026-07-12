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
# DIFFERENCES FROM THE ORIGINAL (v0) funcsMath_turing.py
# ------------------------------------------------------
# One function changed: vecSlc no longer round-trips through np.array for
# fancy indexing (that built "ragged" object arrays for lists of
# different-length vectors — deprecated in numpy 1.20 and a hard ValueError
# from numpy 1.24, which blocked all dependency upgrades). Plain Python list
# indexing is equivalent for the integer index lists every call site uses.
# See the FIX(compat) comment on vecSlc itself and CHANGES.md §1.6/§8.

import numpy as np
from scipy import sparse, linalg
import scipy.sparse.linalg as spla
from scipy import sparse
import matplotlib.pyplot as plt
from numpy.linalg import norm
import scipy.stats as stats
from itertools import cycle


def equalMat(n):
    return toeplitz([1] + [0] * (n - 2), [1, -1] + [0] * (n - 2))


def QtoH(Q):
    L, D, P = ldl(
        Q
    )  # NB not implemented here, but could also use spectral decomposition.
    Pinv = np.argsort(P)
    if min(np.diag(D)) < 0:
        print("Warning: not PSD, removing negative D elements")
        D[D < 0] = 0

    H = dsf.mvM(L[P], np.sqrt(np.diag(D)))  # get rid of the smallest eigenvalue,
    print("Q error norm:", np.linalg.norm(H[Pinv].dot(H[Pinv].T) - Q))
    return H, Pinv


def bMatUdt(M, idxA, idxB, A):
    for i, m in enumerate(idxA):
        for j, n in enumerate(idxB):
            M[m, n] = M[m, n] + A[i, j]


def aMulBsp(a, b):
    """Returns a.dot(b) if b is sparse, as a numpy array."""
    val = (b.T.dot(a.T)).T
    if sparse.issparse(val):
        val = val.toarray()
    return val


def getTrilIdxs(n):
    idxI = []
    idxJ = []
    for i in range(n):
        for j in range(i + 1):
            idxI.append(i)
            idxJ.append(j)

    return idxI, idxJ


def nanlt(a, b):
    """Find a < b elementwise, for a and b with nan elements.

    Dual is nangt(a,b)
    """
    # mask = np.zeros((len(a)),dtype=bool)
    mask = np.zeros(a.shape, dtype=bool)
    np.less(a, b, out=mask, where=~(np.isnan(a) + np.isnan(b)))
    return mask


def nangt(a, b):
    """Find a > b elementwise, for a and b with nan elements.

    Dual is nanlt(a,b)
    """
    # mask = np.zeros((len(a)),dtype=bool)
    mask = np.zeros(a.shape, dtype=bool)
    # np.greater(a,b,out=mask,where=~np.isnan(a))
    np.greater(a, b, out=mask, where=~(np.isnan(a) + np.isnan(b)))
    return mask


def tp2ar(tuple_ex):
    ar = np.array(tuple_ex[0::2]) + 1j * np.array(tuple_ex[1::2])
    return ar


def tp2mat(tuple_ex):
    n = int(np.sqrt(len(tuple_ex)))
    mat = np.zeros((n, n))
    for i in range(n):
        mat[i] = tuple_ex[i * n : (i + 1) * n]
    return mat


def s_2_x(s):
    return np.concatenate((s.real, s.imag))


def vecSlc(vec_like, new_idx):
    """Select the elements of vec_like at positions new_idx.

    FIX(compat): this used to round-trip through np.array(vec_like) purely to
    get fancy indexing. When vec_like is a list of *different-length* arrays
    (e.g. per-load voltage vectors on mixed 1-/3-phase networks) that creates
    a "ragged" object array — deprecated since numpy 1.20 (a
    VisibleDeprecationWarning on every call) and a hard ValueError from numpy
    1.24 onward, which blocked any dependency upgrade. Plain Python indexing
    is equivalent, has no raggedness restriction, and avoids copying the data
    into a temporary array.
    """
    picked = [vec_like[i] for i in new_idx]
    return tuple(picked) if type(vec_like) == tuple else picked


# def yzD2yzI(yzD,n2y):
# # Doesn't look like this will work...
# yzI = []
# for bus in yzD:
# yzI = yzI+find_node_idx(n2y,bus,False)
# return yzI


def idx_shf(x_idx, reIdx):
    x_idx_i = []
    for idx in x_idx:
        x_idx_i.append(reIdx.index(idx))

    x_idx_new = np.array([], dtype=int)

    x_idx_srt = x_idx_i.copy()
    x_idx_srt.sort()
    x_idx_shf = np.array([], dtype=int)
    for i in x_idx_srt:
        x_idx_shf = np.concatenate((x_idx_shf, [x_idx_i.index(i)]))
        x_idx_new = np.concatenate((x_idx_new, [reIdx[i]]))

    return x_idx_shf, x_idx_new


def pf2kq(pf):
    """Return kq = Q/P, for a given PF (+ve or -ve)."""
    return np.sqrt(1 - pf ** 2) / pf


def kq2pf(kq):
    return np.sign(kq) / np.sqrt(1 + kq ** 2)


def np2lsStr(npArray, nF=2):
    strThing = "%." + str(nF) + "f"
    if npArray.ndim == 1:
        listArray = []
        for elem in npArray:
            listArray.append((strThing % elem))
    elif npArray.ndim == 2:
        listArray = []
        for row in npArray:
            listArray.append([])
            for elem in row:
                listArray[-1].append((strThing % elem))
    return listArray


def set_ax_size(w, h, ax=None):
    """w, h: width, height in inches"""
    if not ax:
        ax = plt.gca()
    l = ax.figure.subplotpars.left
    r = ax.figure.subplotpars.right
    t = ax.figure.subplotpars.top
    b = ax.figure.subplotpars.bottom
    figw = float(w) / (r - l)
    figh = float(h) / (t - b)
    ax.figure.set_size_inches(figw, figh)


def vmM(vec, Mat):
    """Perform row-wise multiplication, i.e. np.diag(vec).dot(Mat)

    Ref: see multiplying-across-in-a-numpy-array on stack overflow.

    Implemented for
    - vec + Mat as np arrays
    - Mat as csc or csr matrix, and vec as np arrays
    """
    if type(Mat) is np.ndarray:
        if vec.shape[0] != Mat.shape[0]:
            raise Exception("vec.shape[0]!=Mat.shape[0]")
        MatOut = Mat * vec[:, None]
    elif (
        type(Mat) in [sparse.csc.csc_matrix, sparse.csr.csr_matrix]
        and type(vec) is np.ndarray
    ):
        V_diag = sparse.dia_matrix((vec, 0), shape=(len(vec), len(vec)))
        MatOut = V_diag.dot(Mat)
    else:
        raise Exception("vmM vec-matrix type not implemented.")
    return MatOut


def mvM(Mat, vec):
    """Perform columnwise multiplication, i.e. Mat.dot(np.diag(vec))

    Ref: see multiplying-across-in-a-numpy-array on stack overflow.

    Implemented for
    - Mat & vec as np arrays
    - vec as np array and Mat as csc matrix
    """
    if type(Mat) is np.ndarray:
        if len(vec) != Mat.shape[1]:
            raise Exception("len(vec)!=Mat.shape[1]")
        MatOut = Mat * vec
    elif type(vec) is np.ndarray and type(Mat) is sparse.csc.csc_matrix:
        V_diag = sparse.dia_matrix((vec, 0), shape=(len(vec), len(vec)))
        MatOut = Mat.dot(V_diag)
    else:
        raise Exception("mvM vec-matrix type not implemented.")
    return MatOut


def vmvM(vec0, Mat, vec1):
    if type(Mat) is np.ndarray or type(Mat) is sparse.csc.csc_matrix:
        mat0 = mvM(Mat, vec1)
        MatOut = vmM(vec0, mat0)
    else:
        print("Matrix is not a numpy array!!!")
    return MatOut


def nrel_linearization(Ybus, Vh, V0, H):
    Yll = Ybus[3:, 3:].tocsc()
    Yl0 = Ybus[3:, 0:3].tocsc()
    H0 = sparse.csc_matrix(H[:, 3:])

    Ylli = spla.inv(Yll)

    Vh_diagi = sparse.dia_matrix(
        (1 / Vh.conj(), 0), shape=(len(Vh), len(Vh))
    ).tocsc()  # NB: this looks slow
    HVh_diagi = sparse.dia_matrix(
        (1 / (H0.dot(Vh.conj())), 0), shape=(H0.shape[0], H0.shape[0])
    ).tocsc()  # NB: this looks slow

    My_0 = Ylli.dot(Vh_diagi)
    Md_0 = Ylli.dot(H0.T.dot(HVh_diagi))

    My = sparse.hstack((My_0, -1j * My_0)).toarray()
    Md = sparse.hstack((Md_0, -1j * Md_0)).toarray()

    a = -Ylli.dot(Yl0.dot(V0))

    return My, Md, a


def nrel_linearization_My(Ybus, Vh, V0):
    Yll = Ybus[3:, 3:].tocsc()
    Yl0 = Ybus[3:, 0:3].tocsc()
    a = spla.spsolve(Yll, Yl0.dot(-V0))
    Vh_diag = sparse.dia_matrix((Vh.conj(), 0), shape=(len(Vh), len(Vh)))
    My_i = Vh_diag.dot(Yll)
    My_0 = spla.inv(My_i.tocsc())
    My = sparse.hstack((My_0, -1j * My_0)).toarray()
    return My, a


def nrel_linearization_Ky(My, Vh, sY):
    # an old version of this function; see nrelLinKy() below
    Vh_diag = sparse.dia_matrix((Vh.conj(), 0), shape=(len(Vh), len(Vh)))
    Vhai_diag = sparse.dia_matrix(
        (np.ones(len(Vh)) / abs(Vh), 0), shape=(len(Vh), len(Vh))
    )
    Ky = Vhai_diag.dot(Vh_diag.dot(My).real)
    b = abs(Vh) - Ky.dot(-1e3 * s_2_x(sY[3:]))
    return Ky, b


def nrel_linearization_K(My, Md, Vh, sY, sD):
    # an old version of this function; see nrelLinKy() below
    Vh_diag = sparse.dia_matrix((Vh.conj(), 0), shape=(len(Vh), len(Vh)))
    Vhai_diag = sparse.dia_matrix(
        (np.ones(len(Vh)) / abs(Vh), 0), shape=(len(Vh), len(Vh))
    )
    Ky = Vhai_diag.dot(Vh_diag.dot(My).real)
    Kd = Vhai_diag.dot(Vh_diag.dot(Md).real)
    b = abs(Vh) - Ky.dot(-1e3 * s_2_x(sY[3:])) - Kd.dot(-1e3 * s_2_x(sD))
    return Ky, Kd, b


def nrelLinKy(My, Vh, xY):
    # based on nrel_linearization_Ky
    Vh_diag = sparse.dia_matrix((Vh.conj(), 0), shape=(len(Vh), len(Vh)))
    Vhai_diag = sparse.dia_matrix(
        (np.ones(len(Vh)) / abs(Vh), 0), shape=(len(Vh), len(Vh))
    )
    Ky = Vhai_diag.dot(Vh_diag.dot(My).real)
    b = abs(Vh) - Ky.dot(xY)
    return Ky, b


def nrelLinK(My, Md, Vh, xY, xD):
    # based on nrel_linearization_K
    Vh_diag = sparse.dia_matrix((Vh.conj(), 0), shape=(len(Vh), len(Vh)))
    Vhai_diag = sparse.dia_matrix(
        (np.ones(len(Vh)) / abs(Vh), 0), shape=(len(Vh), len(Vh))
    )
    Ky = Vhai_diag.dot(Vh_diag.dot(My).real)
    Kd = Vhai_diag.dot(Vh_diag.dot(Md).real)
    b = abs(Vh) - Ky.dot(xY) - Kd.dot(xD)
    if type(Kd) is not np.ndarray:
        Kd = Kd.toarray()
    return Ky, Kd, b


def lineariseMfull(My, Md, Mt, f0, xY, xD, xT):
    # based on nrelLinK
    f0_diag = sparse.dia_matrix((f0.conj(), 0), shape=(len(f0), len(f0)))
    f0ai_diag = sparse.dia_matrix(
        (np.ones(len(f0)) / abs(f0), 0), shape=(len(f0), len(f0))
    )
    Ky = f0ai_diag.dot(f0_diag.dot(My).real)
    Kd = f0ai_diag.dot(f0_diag.dot(Md).real)
    Kt = f0ai_diag.dot(f0_diag.dot(Mt).real)
    b = abs(f0) - Ky.dot(xY) - Kd.dot(xD) - Kt.dot(xT)
    if type(Kd) is not np.ndarray:
        Kd = Kd.toarray()
    return Ky, Kd, Kt, b


def fixed_point_itr(w, Ylli, V, sY, sD, H):
    iTtot_c = sY / V + H.T.dot(sD / (H.dot(V)))
    V = w + Ylli.dot(iTtot_c.conj())
    return V


def fixed_point_solve(
    Ybus, YNodeV, sY, sD, H
):  # seems to give comparable results to opendss.
    v0 = YNodeV[0:3]
    Yl0 = Ybus[3:, 0:3]
    Yll = Ybus[3:, 3:]
    Ylli = spla.inv(Yll)
    w = -Ylli.dot(Yl0.dot(v0))
    dV = 1
    eps = 1e-10
    V0 = w
    while (np.linalg.norm(dV) / np.linalg.norm(w)) > eps:
        V1 = fixed_point_itr(w, Ylli, V0, sY, sD, H[:, 3:])
        dV = V1 - V0
        V0 = V1
    return V0


def cvrLinearization(Ybus, Vh, V0, H, pCvr, qCvr, kvYbase, kvDbase):
    # based on nrel_linearization.
    # Y-bit:
    Yll = Ybus[3:, 3:].tocsc()
    Yl0 = Ybus[3:, 0:3].tocsc()
    H0 = sparse.csc_matrix(H[:, 3:])

    Ylli = spla.inv(Yll)

    Vh_diag = sparse.dia_matrix(
        (Vh.conj(), 0), shape=(len(Vh), len(Vh))
    ).tocsc()  # NB: this looks slow
    Vh_diagi = spla.inv(Vh_diag)

    HVh_diag = sparse.dia_matrix(
        (H0.dot(Vh.conj()), 0), shape=(H0.shape[0], H0.shape[0])
    ).tocsc()  # NB: this looks slow
    try:
        HVh_diagi = spla.inv(HVh_diag)
    except:
        HVh_diagi = H0

    pYcvr_diag = sparse.dia_matrix(
        (abs(Vh / kvYbase) ** pCvr, 0), shape=(len(Vh), len(Vh))
    ).tocsc()
    qYcvr_diag = sparse.dia_matrix(
        (abs(Vh / kvYbase) ** qCvr, 0), shape=(len(Vh), len(Vh))
    ).tocsc()
    pDcvr_diag = sparse.dia_matrix(
        (abs(H0.dot(Vh) / kvDbase) ** pCvr, 0), shape=(H0.shape[0], H0.shape[0])
    ).tocsc()
    qDcvr_diag = sparse.dia_matrix(
        (abs(H0.dot(Vh) / kvDbase) ** qCvr, 0), shape=(H0.shape[0], H0.shape[0])
    ).tocsc()

    My_0 = Ylli.dot(Vh_diagi)
    Md_0 = Ylli.dot(H0.T.dot(HVh_diagi))

    My = sparse.hstack((My_0.dot(pYcvr_diag), -1j * My_0.dot(qYcvr_diag))).toarray()
    try:
        Md = sparse.hstack((Md_0.dot(pDcvr_diag), -1j * Md_0.dot(qDcvr_diag))).toarray()
    except:
        Md = np.zeros((H0.T).shape)
    a = -Ylli.dot(Yl0.dot(V0))

    # D-bit:
    dMy = H0.dot(My)
    dMd = H0.dot(Md)
    da = H0.dot(a)

    return My, Md, a, dMy, dMd, da


def firstOrderTaylor(Ybus, V, V0, xhy, xhd, H):
    # based on the m-file firstOrderTaylor.
    # V is YNodeV[3:]

    jay = np.sqrt(-1 + 0j)

    YLL = Ybus[3:, 3:]
    YL0 = Ybus[3:, :3]

    shy = xhy[0 : len(xhy) // 2] + 1j * xhy[len(xhy) // 2 :]
    shd = xhd[0 : len(xhd) // 2] + 1j * xhd[len(xhd) // 2 :]

    IdeltaConj = np.diag(1 / H.dot(V)).dot(shd)
    sizeV = len(V)
    sizeD = len(xhd) // 2

    M1 = np.diag((H.T).dot(IdeltaConj))
    M2 = np.diag(V).dot(H.T)
    # M3 = np.diag(V).dot(YLL.conj());
    M3 = ((YLL.dot(np.diag(V.conj()))).T).conj()
    M4 = np.diag((YL0.conj()).dot(V0.conj()) + (YLL.conj()).dot(V.conj()))
    M5 = np.diag(H.dot(V))
    M6 = np.diag(IdeltaConj).dot(H)
    Uwye = np.concatenate((np.eye(sizeV), jay * np.eye(sizeV)), axis=1)
    Udelta = np.concatenate((np.eye(sizeD), jay * np.eye(sizeD)), axis=1)

    A1 = np.concatenate(
        ((M1 - M3 - M4).real, (-M1 - M3 + M4).imag, M2.real, M2.imag), axis=1
    )
    A2 = np.concatenate(
        ((M1 - M3 - M4).imag, (M1 + M3 - M4).real, M2.imag, -M2.real), axis=1
    )
    A3 = np.concatenate((M6.real, -M6.imag, M5.real, M5.imag), axis=1)
    A4 = np.concatenate((M6.imag, M6.real, M5.imag, -M5.real), axis=1)

    A = np.concatenate((A1, A2, A3, A4), axis=0)

    Bwye = np.concatenate(
        (
            -Uwye.real,
            -Uwye.imag,
            np.zeros((sizeD, 2 * sizeV)),
            np.zeros((sizeD, 2 * sizeV)),
        ),
        axis=0,
    )
    Bdelta = np.concatenate(
        (
            np.zeros((sizeV, 2 * sizeD)),
            np.zeros((sizeV, 2 * sizeD)),
            Udelta.real,
            Udelta.imag,
        ),
        axis=0,
    )

    # % For each injection i (ordered as [P_1;...;P_N; Q_1;...;Q_N]), we solve A*x = B(:, i) to obtain the derivatives
    # % of voltages and phase-to-phase currents wrt injection i.

    derivVP = np.zeros((sizeV, 0), dtype=complex)
    for i in range(sizeV):
        x = np.linalg.solve(A, Bwye[:, i])
        derivVP = np.c_[derivVP, x[:sizeV] + jay * x[sizeV : 2 * sizeV]]
    derivVQ = np.zeros((sizeV, 0), dtype=complex)
    for i in range(sizeV, 2 * sizeV):
        x = np.linalg.solve(A, Bwye[:, i])
        derivVQ = np.c_[derivVQ, x[:sizeV] + jay * x[sizeV : 2 * sizeV]]
    derivWye = np.c_[derivVP, derivVQ]

    derivVP = np.zeros((sizeV, 0), dtype=complex)
    for i in range(sizeD):
        x = np.linalg.solve(A, Bdelta[:, i])
        derivVP = np.c_[derivVP, x[:sizeV] + jay * x[sizeV : 2 * sizeV]]

    derivVQ = np.zeros((sizeV, 0), dtype=complex)
    for i in range(sizeD, 2 * sizeD):
        x = np.linalg.solve(A, Bdelta[:, i])
        derivVQ = np.c_[derivVQ, x[:sizeV] + jay * x[sizeV : 2 * sizeV]]

    derivVDelta = np.c_[derivVP, derivVQ]

    My = derivWye
    Md = derivVDelta
    a = V - My.dot(xhy) - Md.dot(xhd)

    dMy = H.dot(My)
    dMd = H.dot(Md)
    da = H.dot(a)

    return My, Md, a, dMy, dMd, da


def sparseToBand(sprs):
    # NB! This has not been tested thoroughly and may not work...!
    # based on https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.solve_banded.html
    sprs = sprs.tocoo()
    n0 = sprs.shape[0]  # assume square!
    bands = sprs.col - sprs.row
    l = -min(bands)
    u = max(bands)
    bMtx = np.zeros((1 + u + l, n0))
    for i, j, d in zip(sprs.row, sprs.col, sprs.data):
        band = j - i
        colIdx = u - band
        rowIdx = i + band
        bMtx[colIdx, rowIdx] = d

    return bMtx, l, u


def firstOrderTaylorQuick(Ybus, V, V0, xhy, xhd, H):
    # based on the m-file firstOrderTaylor.
    # V is YNodeV[3:]

    YLL = Ybus[
        3:, 3:
    ]  # NB: this is usually sparse already, hence some odd matrix multiplication orders
    YL0 = Ybus[3:, :3]

    shy = xhy[0 : len(xhy) // 2] + 1j * xhy[len(xhy) // 2 :]
    shd = xhd[0 : len(xhd) // 2] + 1j * xhd[len(xhd) // 2 :]

    # IdeltaConj = np.diag(1/H.dot(V)).dot(shd)
    IdeltaConj = shd / H.dot(V)
    sizeV = len(V)
    sizeD = len(xhd) // 2

    M1 = np.diag((H.T).dot(IdeltaConj))
    M2 = vmM(V, H.T)
    M3 = ((YLL.dot(np.diag(V.conj()))).T).conj()
    M4 = np.diag((YL0.conj()).dot(V0.conj()) + (YLL.conj()).dot(V.conj()))

    M5 = np.diag(H.dot(V))
    M6 = vmM(IdeltaConj, H)

    A1 = np.concatenate(
        ((M1 - M3 - M4).real, (-M1 - M3 + M4).imag, M2.real, M2.imag), axis=1
    )
    A2 = np.concatenate(
        ((M1 - M3 - M4).imag, (M1 + M3 - M4).real, M2.imag, -M2.real), axis=1
    )
    A3 = np.concatenate((M6.real, -M6.imag, M5.real, M5.imag), axis=1)
    A4 = np.concatenate((M6.imag, M6.real, M5.imag, -M5.real), axis=1)

    A = np.concatenate((A1, A2, A3, A4), axis=0)
    del A1
    del A2
    del A3
    del A4
    del M1
    del M2
    del M3
    del M4
    del M5
    del M6

    Bwye = np.concatenate(
        (-np.eye(2 * sizeV), np.zeros((2 * sizeD, 2 * sizeV))), axis=0
    )
    Bdelta = np.concatenate(
        (np.zeros((2 * sizeV, 2 * sizeD)), np.eye(2 * sizeD)), axis=0
    )

    Bwye = sparse.csc_matrix(Bwye)
    Bdelta = sparse.csc_matrix(Bdelta)
    A = sparse.csc_matrix(A)

    # Tried a whole bunch of things, including sparse solves over all of these,
    # solving banded (with scipy.solve_banded using RCM algorithm), bcg methods.
    # None seem to be faster than just calculating the inverse and then multiplying
    # through, at this stage, so sticking with this code.
    Ainv = linalg.inv(A.A)

    derivVP = (Bwye[:, :sizeV].T.dot(Ainv.T)).T[
        : 2 * sizeV
    ]  # Ainv is not sparse hence this is required
    derivVQ = (Bwye[:, sizeV:].T.dot(Ainv.T)).T[: 2 * sizeV]
    My = np.c_[
        derivVP[:sizeV] + 1j * derivVP[sizeV::], derivVQ[:sizeV] + 1j * derivVQ[sizeV::]
    ]
    del derivVP
    del derivVQ

    derivVP = (Bdelta[:, :sizeV].T.dot(Ainv.T)).T[: 2 * sizeV]
    derivVQ = (Bdelta[:, sizeV:].T.dot(Ainv.T)).T[: 2 * sizeV]

    Md = np.c_[
        derivVP[:sizeV] + 1j * derivVP[sizeV::], derivVQ[:sizeV] + 1j * derivVQ[sizeV::]
    ]

    a = V - My.dot(xhy) - Md.dot(xhd)

    dMy = H.dot(My)
    dMd = H.dot(Md)
    da = H.dot(a)

    return My, Md, a, dMy, dMd, da


# # TESTING for schurSolve
# AA = np.random.random((5,5))+np.eye(5)
# BB = np.random.random((5,4))

# idxA = [0,1,2]
# idxB = [3,4]
# A = sparse.csc_matrix(AA[idxA][:,idxA])
# B = sparse.csr_matrix(AA[idxA][:,idxB])
# C = sparse.csc_matrix(AA[idxB][:,idxA])
# D = sparse.csc_matrix(AA[idxB][:,idxB])
# BB1 = sparse.csc_matrix(BB[idxA])
# BB2 = sparse.csc_matrix(BB[idxB])
# Di = sparse.linalg.inv(D)
# BDi = B.dot(sparse.linalg.inv(D))

# X = schurSolve(A,B,C,D,BB1,BB2,Di=Di,BDi=BDi)
# X_ = np.linalg.solve(AA,BB)[:3]
# rerr(X,X_,p=0)


def schurSolve(A, B, C, D, BB1, BB2, Di=None, BDi=None):
    """Calculate a 'schur solve' for Mx = BB, but only for part of x.

    Ie, solve
         [A B][x1] = [BB1]
         [C D][x2] = [BB2]
    for x1, without explicitly finding x2. See e.g.
    https://en.wikipedia.org/wiki/Schur_complement,
    -> Application to solving linear equations

    It is assumed that ALL terms are passed in as sparse matrices.

    INPUTS
    -----
    A, B, C, D: as the main big matrix
    BB1, BB2:   the other matrix
    Di:         the inverse of D, if known (and sparse!)
    BDi:        B.dot(Di), if known

    To avoid complaints from spsolve:
    - B should be csR,
    - C should be csC,
    - D should be csC,

    """
    # First do a little bit of error checking:
    for XX in [A, B, C, D, BB1, BB2]:
        if not sparse.issparse(XX):
            raise Exception("Not all elements are sparse!")

    if Di is None:
        Amod = (A - B.dot(sparse.linalg.spsolve(D, C))).A
    else:
        Amod = (A - (B.dot(Di).dot(C))).A

    if BDi is None:
        if Di is None:
            BDi = sparse.linalg.spsolve(D.T.tocsc(), B.T).T
        else:
            BDi = (Di.T.dot(B.T)).T

    Bmod = (BB1 - BDi.dot(BB2)).A

    x1 = linalg.solve(Amod, Bmod)
    return x1


def schurComp(M, idxOut=None, idxIn=None):
    # https://en.wikipedia.org/wiki/Schur_complement
    if idxIn is None:
        idxIn = np.arange(M.shape[0])
        idxIn = np.delete(idxIn, idxOut)
    elif idxOut is None:
        idxOut = np.arange(M.shape[0])
        idxOut = np.delete(idxOut, idxIn)
    A = M[idxIn][:, idxIn]
    B = M[idxIn][:, idxOut]
    C = M[idxOut][:, idxIn]
    D = M[idxOut][:, idxOut]
    if type(M) is np.ndarray:
        AsD = A - B.dot(linalg.solve(D, C))
    else:
        AsD = A - B.dot(spla.spsolve(D, C))
    return AsD


def getAinv(M, idxOut=None, idxIn=None):
    if idxIn is None:
        idxIn = np.arange(M.shape[0])
        idxIn = np.delete(idxIn, idxOut)
    elif idxOut is None:
        idxOut = np.arange(M.shape[0])
        idxOut = np.delete(idxOut, idxIn)
    Minv = spla.inv(M)
    return Minv[idxIn][:, idxIn]


def spluInv(Asplu):
    perm_c = Asplu.perm_c
    perm_rC = np.argsort(Asplu.perm_r)
    speye = sparse.eye(Asplu.shape[0], dtype=complex, format="csr")
    AinvInt = spla.spsolve_triangular(Asplu.L, speye[perm_rC].toarray())
    return spla.spsolve_triangular(Asplu.U, AinvInt, lower=False)[perm_c]


def sparseSvty(M, Vsrc, idxOut=None, idxIn=None):
    idxSrc = [0, 1, 2]
    if idxIn is None:
        idxIn = np.arange(M.shape[0])
        idxOut = np.delete(idxIn, np.r_[idxSrc, idxOut])
        print("Implement me!")
    elif idxOut is None:
        idxOut = np.arange(M.shape[0])
        idxOut = np.delete(idxOut, np.r_[idxSrc, idxIn])
    # # see e.g. WB 16-10-19
    # Y00 = M[idxSrc][:,idxSrc]
    Y11 = M[idxOut][:, idxOut]
    Y22 = M[idxIn][:, idxIn]
    # Y01 = M[idxSrc][:,idxOut]
    Y10 = M[idxOut][:, idxSrc]
    # Y02 = M[idxSrc][:,idxIn]
    Y20 = M[idxIn][:, idxSrc]
    Y12 = M[idxOut][:, idxIn]
    Y21 = M[idxIn][:, idxOut]
    ZbusIn = np.linalg.inv((Y22 - (Y21.dot(spla.spsolve(Y11, Y12)))).toarray())
    # cIn = - ZbusIn.dot( (Y20 - Y21.dot( spla.spsolve(Y11,Y10 ) ) ).dot(Vsrc) ) # for a checksum if required:
    return ZbusIn


def calcDp1rSqrt(d, e, n):
    """Calculated square root of diagonal-plus-rank 1 matrix.

    IE find the square root of
    X = (d-e)*np.diag(np.ones(n)) + e*np.ones((n,n))

    Originally from 'linSvdCalcs'.

    Calculates the diagonal and off-diagonal elements of a matrix with
    diagonal elements d and off-diagonal elements e, of dimension n x n.

    e.g. A = np.diag(np.ones(n))*(d-e) + np.ones((n,n))*e
    X = la.sqrtm(A)
    a2 = X[0,0]**2
    b2 = X[1,0]**2

    RETURNS
    d,e,n triple which is nice (the function is a bijection of Dp1r matrices
    onto Dp1r matrices! :D)

    Remember: during testing to do X.dot(X) (not X*X!)
    """

    a = 4 * (n - 1) + (n - 2) ** 2
    b = -(2 * (n - 2) * e + 4 * d)
    c = e ** 2

    # this has been tested at some point...!
    b2ii = (-b - np.sqrt(b ** 2 - 4 * a * c)) / (2 * a)
    a2ii = d - (n - 1) * b2ii

    dSqrt = np.sqrt(a2ii)
    eSqrt = -np.sqrt(b2ii)
    return dSqrt, eSqrt, n


def rerr(A, A_, ord=None, p=True):
    """Calculate rerr = norm(A-A_)/norm(A). p input for 'print' value as well.

    NB: the order of A, A_ DOES matter! 'A' is the 'Truth'.

    A, A_ should have the same type (sparse or not), no error checking on this.

    Inputs
    A: the true A
    A_: the approx A
    ord: passed into norm (ignored if one dimensional)
    p: bool, 'print' flag

    Returns
    ---
    rerr - as above.
    """
    if sparse.issparse(A):
        rerr = sparse.linalg.norm(A - A_, ord=ord) / sparse.linalg.norm(A, ord=ord)
    elif type(A) in [float, int, np.float64]:
        rerr = np.abs(A - A_) / np.abs(A)
    else:
        rerr = norm(A - A_, ord=ord) / norm(A, ord=ord)

    if p:
        print(rerr)
    return rerr


def sparse2lowRank(A):
    """Convert a sparse matrix A to the form U_T.dot(V).

    As below: low rank stacked COLUMN vectors are 'transposed'
    """
    if not type(A) in [sparse.csr_matrix, sparse.csc_matrix]:
        raise Exception("A not given as a CSC/CSR matrix.")

    idxs = list(set(A.indices))
    Nr = len(idxs)
    U_T = np.zeros(
        (
            A.shape[0],
            Nr,
        ),
        dtype=complex,
    )
    V = np.zeros(
        (
            Nr,
            A.shape[0],
        ),
        dtype=complex,
    )
    V[np.arange(Nr), idxs] = 1
    for i, idx in enumerate(idxs):
        U_T[:, i] = A[:, idx].toarray().flatten()

    return sparse.csc_matrix(U_T), sparse.csr_matrix(V)


def sparseInvUpdate(Ainv, dA):
    """Update Ainv based on a sparse difference matrix, dA.

    dA should be sparse, in CSC or CSR format.

    Naming convention: low rank stacked COLUMN vectors are 'transposed'
    """
    U_T, V = sparse2lowRank(dA)

    # go through each of these and update.
    return lowRankUpdate(Ainv, U_T.T, V)


def lowRankUpdate(Ainv, U, V):
    """Sequentially update Ainv through the rows of U, V, using oneRankUpdate.

    U, V should both be 'stacked row vectors', of Nr x Nc (Nr << Nc).
    """
    if sparse.issparse(U):
        au = aMulBsp(Ainv, U.T)
    else:
        au = Ainv.dot(U.T)
    va = V.dot(Ainv)
    mid = np.eye(U.shape[0]) + V.dot(au)

    if Ainv.dtype == np.complex_:
        fcalc = linalg.blas.zgemm
    elif Ainv.dtype == np.float_:
        fcalc = linalg.blas.dgemm

    return fcalc(-1, au, linalg.solve(mid, va), 1, Ainv)


def oneRankUpdate(Ainv, u, v):
    """See wikipedia, the 'woodbury matrix identity'.

    NB: u and v are assumed to be dense, as is A.

    Is about 10x faster when n=1000 (0.007s); 25x faster when n=3000 (0.05s);
    80x faster when n=10000 (0.65s).
    Here is implemented in blas, but it is only really the final step which
    is actually any faster using the blas.


    """
    if Ainv.dtype == np.complex_:
        # xx = Ainv.dot(u)
        xx = linalg.blas.zgemv(1, Ainv, u)
        # recip = 1/(1 + v.dot( xx ))
        recip = 1 / (1 + linalg.blas.zdotu(v, xx))
        # yy = v.dot(Ainv)
        yy = linalg.blas.zgemv(1, Ainv, v, trans=1)
        Ainv_ = linalg.blas.zgeru(-recip, xx, yy, 1, 1, Ainv)
    elif Ainv.dtype == np.float_:
        # xx = Ainv.dot(u)
        xx = linalg.blas.dgemv(1, Ainv, u)
        # recip = 1/(1 + v.dot( xx ))
        recip = 1 / (1 + linalg.blas.ddot(v, xx))
        # yy = v.dot(Ainv)
        yy = linalg.blas.dgemv(1, Ainv, v, trans=1)
        Ainv_ = linalg.blas.dger(-recip, xx, yy, 1, 1, Ainv)
    return Ainv_


def wasserLinRegress(X, Y):
    """Run linear regression based on X and Y.

    From theorem 14.4 and 14.8 of wasser, 'All of Statistics'.

    Output slope first, following linregress function:
    output: b1, b0, se_b1, eHat
    """
    muX = np.mean(X)
    muY = np.mean(Y)
    n = len(X)

    b1 = ((X - muX).dot(Y - muY)) / (norm(X - muX) ** 2)  # 14.5
    b0 = muY - b1 * muX  # 14.6

    eHat = Y - (b0 + (b1 * X))  # 14.4
    sgmHat2 = (norm(eHat) ** 2) / (n - 2)  # 14.7

    sX2 = (norm(X - muX) ** 2) / n  # 14.11c
    se_b1 = np.sqrt(sgmHat2) / (np.sqrt(sX2) * np.sqrt(n))  # 14.13

    # output slope first following linregress
    return b1, b0, se_b1, eHat


# CHERNOFF and CHEBYSHEV Proof of concept - only 1-d
def chernoffBnd(a, k, th, cmp=False):
    # start off just considering gamma distributions.
    if cmp:
        t = max((1 / th) - (k / a), 0)
        pBd = np.exp(-a * t) * np.prod((1 - th * t) ** -k)
    else:
        t = max((1 / th) * ((k / a) - 1), 0)
        pBd = np.exp(a * t) * np.prod((1 + th * t) ** -k)
    return pBd


def chebBnds(x, mu, sgm, cmp=False):
    # NB 'n' here is no. sgms.
    n = np.abs(x - mu) / sgm
    sgn = x - mu > 0
    if n < 1:
        pBd = 1
    else:
        pBd = np.nan
        if cmp:
            if sgn:
                pBd = n ** -2
            else:
                pBd = 1
        else:
            if sgn:
                pBd = 1
            else:
                pBd = n ** -2
        # pBd = min(1 - (n**-2)
    return pBd


def logit10(x):
    """Logit function, setting z=-inf for x = 0 z=inf for x=1.

    I think this will only work with 1-D arrays for now.
    """
    z = np.zeros(x.shape)
    z[x == 0] = -np.inf
    z[x == 1] = np.inf
    z[np.isnan(x)] = np.nan

    xCalc = np.where((nangt(x, 0)) * nanlt(x, 1))[0]
    z[xCalc] = np.log10(x[xCalc] / (1 - x[xCalc]))

    return z


def logit(x):
    """Logit function - return np.log(x/(1-x)). Inverse is logistic()."""
    return np.log(x / (1 - x))


def logistic(x):
    """Logistic function - return np.exp(x)/(1 + np.exp(x)). Invs. is logit"""
    return np.exp(x) / (1 + np.exp(x))


def remGaussOutliers(X, cutoff=0.99):
    """Remove outliers that fall outside a normal distr with a cutoff.

    Smaller cutoffs remove more data.
    """
    X = np.sort(X)
    success = False
    nd = stats.norm()
    while not success:
        mu = np.mean(X)
        sg = np.std(X)
        Z = (X - mu) / sg
        eps0 = nd.cdf(-Z[0]) ** len(Z)
        eps1 = nd.cdf(Z[-1]) ** len(Z)
        if (eps0 < cutoff) and (eps1 < cutoff):
            success = True
        if eps0 > cutoff:
            X = X[1:]
        if eps1 > cutoff:
            X = X[:-1]
    return X


def quantilePlot(X, *args, ax=None, **kwargs):
    """Plot a Quantile plot (Q-Q plot) using X on ax (if it exists).

    The Q-Q plot (sometimes called probability plot) is described in, e.g.,
    https://en.wikipedia.org/wiki/Q%E2%80%93Q_plot

    or in 2.6.7 of 'An introduction to statistical modelling of extremes'
    by Coles.
    """
    edf = np.arange(1, len(X) + 1) / (len(X) + 1)
    nd = stats.norm
    prmNd = nd.fit(X)
    nd_fit = nd.ppf(edf, loc=prmNd[0], scale=prmNd[1])
    if ax is None:
        fig, ax = plt.subplots()

    ax.plot(nd_fit, np.sort(X), ".", *args, **kwargs)
    xx = np.linspace(nd_fit[0], nd_fit[-1])
    ax.plot([nd_fit[0], nd_fit[-1]], [nd_fit[0], nd_fit[-1]], "k--")
    ax.set_aspect("equal")
    ax.set_xlabel("Norm approx")
    ax.set_ylabel("Data")
    return ax


def plotEdf(x, *p_args, xlms=None, ax=None, mm="norm", **p_kwargs):
    """Plot the empirical distribution function.

    INPUTS
    ------
    x: the thing to plot the EDF of,
    p_args: normal plot arguments to go into 'step' as *p_args
    p_kwargs: plot keyword arguments to go into 'step' as **p_kwargs
    xlms: x limits to go from/to
    ax: the axis to plot onto
    mm: 'norm' for a normal EDF or '%' for percentage

    RETURNS
    -------
    ax: the axis this was plotted onto,
    [xlo,xhi]: the low/high x limits that the step plot goes to.

    """
    if ax is None:
        fig, ax = plt.subplots()
    x = np.sort(x)
    y = np.arange(0, len(x) + 1) / len(x)
    if xlms is None:
        xhi = x[-1] + (x[-1] - x[0]) * 0.2
        xlo = x[0] - (x[-1] - x[0]) * 0.2
    else:
        xlo, xhi = xlms
    xs = np.r_[xlo, x, xhi]
    ys = np.r_[y, 1]
    if mm == "%":
        ys = ys * 100

    plt.step(xs, ys, where="post", *p_args, **p_kwargs)
    plt.xlim((xlo, xhi))
    return ax, [xlo, xhi]


def sparseBlkDiag(blks):
    """A function to roughly emulate sparse.block_diag.

    sparse.block_diag is not recommended for construction of sparse
    matrices, see
    https://docs.scipy.org/doc/scipy/reference/sparse.html
    So, this has been implemented the method using lil_matrix.

    blks should be a list of dense matrices to put on the diagonal.

    To convert vectors use blk.reshape(-1,1) or blk.reshape(1,-1), but
    OUTSIDE this function! :)

    Returns a lil_matrix - convert to CSR etc outside this function.
    """

    i0 = [0]
    j0 = [0]
    for blk in blks:
        i0.append(i0[-1] + blk.shape[0])
        if blk.ndim == 1:
            raise Exception("Only 2d blocks can be passed in.")
        j0.append(j0[-1] + blk.shape[1])

    A = sparse.lil_matrix((i0[-1], j0[-1]), dtype=complex)
    for i in range(len(i0) - 1):
        A[i0[i] : i0[i + 1], j0[i] : j0[i + 1]] = blks[i]

    return A


def dp1rMv(M, dp1r):
    """Diagonal d plus rank-1 e right multiplication of M.

    A = M.dot(dp1r)
      = M.dot((d-e)*np.eye(n)) + M.dot( e*ones((n,n)) )

    Based on dp1rMv from linSvdCalcs.py

    INPUTS
    ------
    - dp1r, should be of the form d,e,N
    """
    d, e, N = dp1r

    if N != M.shape[1]:
        raise Exception("N, M.shape not the same size!")

    return M * (d - e) + np.outer(e * (np.sum(M, axis=1)), np.ones(N))


def calcVar(X):
    """Calculate diag(X.dot(X.T)), setting zeros to 1e-100.

    Having tested 'dot', 'linalg.blas.get' and 'np.linalg.norm', this
    seems to be the quickest.
    """
    i = 0
    var = np.zeros(len(X))
    for x in X:
        var[i] = x.dot(x)
        if var[i] == 0:
            var[i] = 1e-100
        i += 1
    return var


def magicSlice(
    A,
    B,
    idxX,
    idxY,
):
    """Do matlab-style A[idxX,idxY] = B for B of size len(idxX) x len(idxY).

    Equivalent to:
    for i,ix in enumerate(idxX):
        for j,iy in enumerate(idxY):
            A[ix,iy] = B[i,j]
    """
    if B.shape != (len(idxX), len(idxY)):
        raise Exception("B is not of the correct dimensions.")

    idxXrpt = [idx for idx in idxX for i in range(len(idxY))]

    for b, ix, iy in zip(B.flat, idxXrpt, cycle(idxY)):
        A[ix, iy] = b
    return A


def cdf2qntls(xcdf, fcdf, pvals=np.linspace(0, 1, 5)):
    """Calculate the values of x at the pvals using a CDF function xcdf.

    Inputs
    ---
    xcdf as argument values of the cdf
    fcdf as the corresponding cdf function values
    pvals as the probability values to be calculated at

    Returns
    ---
    xVals, the vales of x at the pvals

    """
    pvals = [pvals] if type(pvals) is float else pvals
    idxs = [np.argmax(fcdf > pval) for pval in pvals]
    return [xcdf[idx] for idx in idxs]


deg2rad = 180 / np.pi


def calcR2(y, yhat, rsdl=None):
    """Calculate the coefficient of determination from y and yhat (or rsdl)

    Equivalent to:
    tss = sum((y - mean(y))**2)
    rss = sum((y - yhat)**2)
        = sum(rsdl**2) # if not None
    R2 = 1 - rss/tss

    https://en.wikipedia.org/wiki/Coefficient_of_determination

    """
    tss = np.sum((y - np.mean(y)) ** 2)
    if rsdl is None:
        rss = np.sum((y - yhat) ** 2)
    else:
        rss = np.sum(rsdl ** 2)

    return 1 - (rss / tss)


def tp2arL(l_tuples):
    """Returns [tp2ar(t) for t in l_tuples]"""
    return [tp2ar(t) for t in l_tuples]
