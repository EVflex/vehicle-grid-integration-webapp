"""azure_mockup.py

Runs one OpenDSS simulation and renders the result plots.

General approach:
- First, take the 'network_data' parameters which are used to modify the mvlv
  network models and use them to create a new network in _network_mod (given
  network ID 1000). This uses the ft.modify_network class.
- Then, take the 'simulation_data' parameters and run a simulation. This uses
  the turingNet class.

The full options and definitions of the run_dict are given in azureOptsXmpls.

REWRITE NOTES (see CHANGES.md at the repository root for the full list):

- `run_dss_simulation` now returns a *dict* of PNG bytes and numpy arrays
  instead of a 21-element tuple of BytesIO buffers. Two reasons:
  (1) the tuple was error-prone — it listed the same buffer twice and the
      caller had to keep 21 positional slots aligned by hand;
  (2) the simulation now runs in a separate worker process (see main.py) and
      the return value must be picklable — `bytes` are, `BytesIO` handles are
      awkward.
- Every figure is explicitly closed after rendering, and a final
  `plt.close("all")` in a `finally` block guarantees no figures leak even on
  error. Previously ~11 figures stayed open per request until the *next*
  request happened to close them.
- The dead `sf`/`sff` gallery-saving branches were removed. `sff` was never
  imported here, so any call with `sf=1` raised NameError — evidence it was
  never used via the API.
- The three "profile options" plots are all guarded against an empty profile
  selection. Previously the first one called `new_hsl_map(0)`, which divides
  by zero (360 / nn).

THREADING WARNING: this module uses matplotlib's *pyplot* (global-state) API,
which is only safe on the main thread of a process running one job at a time.
That is exactly the environment main.py provides (a dedicated single-worker
subprocess). Do not call run_dss_simulation from a web-server thread.
"""

import io
import logging
import os
import sys
import tempfile

import dss
import matplotlib

# Select the non-interactive Agg backend *before* pyplot is imported: the
# worker has no display, and Agg is the only backend safe for server use.
matplotlib.use("agg")
import matplotlib.pyplot as plt
import numpy as np

from . import azureOptsXmpls as aox
from . import funcsDss_turing
from . import funcsTuring as ft
from .funcsPython_turing import fillplot, new_hsl_map, set_day_label

fn_root = sys.path[0] if __name__ == "__main__" else os.path.dirname(__file__)


def _fig_to_png(**savefig_kwargs) -> bytes:
    """Render the *current* pyplot figure to PNG bytes and close it.

    Closing immediately (rather than relying on a later plt.clf()) keeps the
    worker's memory flat across requests.
    """
    buf = io.BytesIO()
    plt.gcf().savefig(buf, **savefig_kwargs)
    plt.close(plt.gcf())
    return buf.getvalue()


def _placeholder_png(message: str) -> bytes:
    """A small labelled empty plot, returned when a plot has no data to show.

    The frontend renders every plot key in the response, so we return a
    readable placeholder instead of a blank or missing image.
    """
    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    ax.text(
        0.5,
        0.5,
        message,
        ha="center",
        va="center",
        transform=ax.transAxes,
        fontsize="large",
        color="gray",
    )
    ax.set_axis_off()
    return _fig_to_png()


def _shade_failed_steps(failed_hours, ax=None) -> None:
    """Shade the half-hour windows whose power flow did not converge.

    Drawn on daily time-series result plots so the non-converged region is
    visible on the image itself (which users download and screenshot), not
    only in the JSON response. Does nothing when every step converged, so
    result images for converged runs — including the regression baselines —
    are byte-for-byte unchanged.
    """
    if not failed_hours:
        return
    target = ax if ax is not None else plt.gca()
    labelled = False
    for h in failed_hours:
        target.axvspan(
            h - 0.25,
            h + 0.25,
            color="red",
            alpha=0.12,
            zorder=0,
            label="did not converge" if not labelled else None,
        )
        labelled = True


def _plot_profile_selection(simulation, tt, ksel) -> bytes:
    """Shared renderer for the three 'profile options' line plots.

    The three variants only differ by which profile keys are selected, so the
    plotting code lives here once instead of three copy-pasted blocks.
    """
    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    clrs = new_hsl_map(len(ksel), 100, 50)
    mrks = ["--", "-.", ":"] * (1 + (len(ksel) // 3))
    for k, clr, mrk in zip(ksel, clrs, mrks):
        plt.plot(tt, simulation.p[k], mrk, color=clr, label=k)

    set_day_label()
    plt.legend(title="Profile ID", fontsize="small", loc=(1.05, 0.1))
    plt.ylabel("Power, kW")
    plt.tight_layout()
    return _fig_to_png()


def run_dss_simulation(rd=aox.run_dict0):
    """Build the modified network, run a 48-step daily time series, and render
    all result plots.

    Inputs
    ---
    rd - the run dictionary (see azureOptsXmpls.run_dict0)

    Returns
    ---
    A picklable dict with:
    - '<plot>_png': PNG image bytes, for each of the 12 result plots;
    - '<dataset>_header' / '<dataset>_data': column headers (list of str) and
      a 2-D numpy array, for the four downloadable CSV datasets
      (primary_loadings, mv_voltages, trn_powers, lv_comparison).
    """
    try:
        return _run_dss_simulation_inner(rd)
    finally:
        # Belt-and-braces: every plot helper closes its own figure, but if an
        # exception escapes mid-plot this guarantees the worker process does
        # not accumulate open figures across requests.
        plt.close("all")


def _run_dss_simulation_inner(rd):

    # Set up a temporary directory to store network files.
    #
    # DEEP-DIVE: unzip_networks no longer re-extracts the ~3,800-file network
    # zip on every call — it maintains a per-process extracted cache and
    # populates temp_dir with copies of only the handful of small .dss text
    # files that modify_network edits (plus a symlink to the read-only
    # lvNetworks tree). See funcsTuring.unzip_networks.
    #
    # Note the network build (which reads files from temp_dir) happens inside
    # the `with` block; after it exits the OpenDSS model is fully compiled in
    # memory and the files are no longer needed, so the temp dir is removed.
    with tempfile.TemporaryDirectory() as temp_dir:
        ft.unzip_networks(
            dest_dir=os.path.join(temp_dir, "_network_mod"),
            n_id=rd["network_data"]["n_id"],
        )

        d = funcsDss_turing.dssIfc(dss.DSS)
        # Place modified files into _network_mod to match hardcoded value in slesNtwk_turing.py
        ntwk = ft.modify_network(rd, mod_dir=temp_dir, dnout="_network_mod")

        # Simulation modifications
        frid0 = rd["network_data"]["n_id"]
        simulation = ft.turingNet(frId=1000, frId0=frid0, rundict=rd, mod_dir=temp_dir)

    tt = np.arange(0, 24, 24 / 48)  # the half-hourly clock

    # Get the solutions
    lds = simulation.get_lds_kva(48)
    slns, _ = simulation.run_dss_lds(lds)

    # Log (rather than assert) convergence: a non-converged power flow means
    # the results are not trustworthy for engineering decisions.
    #
    # CHANGE(feature): the per-step convergence outcome is now also returned to
    # the caller (see the "convergence" key below), so main.py can pass it into
    # the API response and the frontend can warn the user. Previously this was
    # only logged server-side and was invisible to anyone reading the plots —
    # a user pushing extreme EV/PV penetrations could get confident-looking but
    # physically meaningless results with no indication anything went wrong.
    converged_flags = [bool(s.Cnvg) for s in slns]
    failed_steps = [i for i, ok in enumerate(converged_flags) if not ok]
    n_not_converged = len(failed_steps)
    if n_not_converged:
        logging.warning(
            "%d of %d time steps did NOT converge — results may be invalid",
            n_not_converged,
            len(slns),
        )

    results = {}

    # Convergence summary for the API response. `failed_hours` gives the
    # half-hourly clock time (tt) of each non-converged step so the frontend
    # can name the affected time windows to the user.
    results["convergence"] = {
        "n_steps": len(slns),
        "n_failed": n_not_converged,
        "failed_steps": failed_steps,
        "failed_hours": [round(float(tt[i]), 2) for i in failed_steps],
    }

    # ------------------------------------------------------------------
    # PLOT: mv_highlevel, network plot highlighting LV networks etc
    # ------------------------------------------------------------------
    simulation.fPrm.update(
        {
            "saveFig": 0,
            "showFig": True,
            "pdf": False,
            "figname": "pltNetworks_mvonly_new",
        }
    )
    simulation.plotXvNetwork(
        pType="B",
        pnkw={"txtOpts": "all", "dgFlag": True},
    )
    results["mv_highlevel_png"] = _fig_to_png()

    # PLOT: mv_highlevel_clean, network plot without further highlights
    simulation.fPrm.update(
        {
            "saveFig": 0,
            "showFig": True,
            "pdf": False,
            "figname": "pltNetworks_mvonly_new_clean",
        }
    )
    simulation.plotXvNetwork(
        pType="B",
        pnkw={"txtOpts": None, "dgFlag": False, "figsize": (7, 3.6)},
    )
    results["mv_highlevel_clean_png"] = _fig_to_png()

    # PLOT: mv_powers, power plot (no LV circles)
    simulation.fPrm.update(
        {
            "saveFig": 0,
            "showFig": True,
            "pdf": False,
            "figname": f"{simulation.fdrs[frid0]}",
        }
    )
    # Font size for bus labels per network; .get() with a default so a future
    # network id cannot KeyError here (previously a hard KeyError).
    txtFss = {
        1060: "10",
        1061: "6",
    }
    pnkw = {
        "txtOpts": "all",
        "lvnFlag": False,
        "txtFs": txtFss.get(frid0, "8"),
    }
    simulation.plotXvNetwork(
        pType="p",
        pnkw=pnkw,
    )
    results["mv_powers_png"] = _fig_to_png(facecolor="LightGray")

    # ------------------------------------------------------------------
    # PLOT: lv_voltages, compare two lv voltage timeseries
    # ------------------------------------------------------------------
    # FIX: was a bare `assert`, which (a) produced an unexplained 500 and
    # (b) disappears entirely under `python -O`.
    if len(rd["plot_options"]["lv_voltages"]) > 2:
        raise ValueError("plot_options.lv_voltages: at most 2 networks can be compared")

    fig, ax = plt.subplots()
    lv_idxs = [
        simulation.ckts.ldNo.index(nn) for nn in rd["plot_options"]["lv_voltages"]
    ]

    clrs = [
        "C0",
        "C3",
    ]
    for idx, clr in zip(lv_idxs, clrs):
        # Voltage of every LV load in network `idx`, phase A, in per-unit on a
        # 230 V base. `fillplot` draws the min/max envelope and quantiles.
        Vsec = np.array([s["VlvLds"][idx] for s in slns])[:, :, 0]
        _, dplt = fillplot(
            np.abs(Vsec) / 230,
            tt,
            ax=ax,
            lineClrs=[clr],
            fillKwargs={"color": clr},
        )

    _ = [
        plt.plot(np.nan, np.nan, color=clr, label=lbl)
        for lbl, clr in zip(rd["plot_options"]["lv_voltages"], clrs)
    ]
    plt.legend(
        title="LV Network ID",
        fontsize="small",
    )
    set_day_label()
    plt.ylabel("Voltage, pu (230 V base)")
    xlm = plt.xlim()
    # Statutory UK LV limits: +10% / -6% of nominal.
    plt.hlines(
        [0.94, 1.10],
        *xlm,
        linestyles="dashed",
        color="r",
    )
    plt.xlim(xlm)
    results["lv_voltages_png"] = _fig_to_png()

    # ------------------------------------------------------------------
    # PLOT: lv_comparison — one voltage-envelope panel per simulated network
    # ------------------------------------------------------------------
    fig, axs = plt.subplots(
        figsize=(
            9,
            3.2,
        ),
        nrows=1,
        ncols=simulation.ckts.N,
        sharey=True,
        sharex=True,
    )
    # FIX: with a single LV network plt.subplots returns a bare Axes (not an
    # array), so the original `for ii, ax in enumerate(axs)` raised TypeError.
    # A user is allowed to simulate a single network (lv_list of length 1).
    axs = np.atleast_1d(axs)

    data_out_lv_comparison = np.zeros(
        (
            48,
            0,
        )
    )
    for ii, ax in enumerate(axs):
        Vsec = np.array([s["VlvLds"][ii] for s in slns])[:, :, 0]
        _, dplt = fillplot(
            np.abs(Vsec) / 230,
            tt,
            ax=ax,
            lineClrs=[
                f"C{ii}",
            ],
            fillKwargs={"color": f"C{ii}"},
        )
        xlm = plt.xlim()
        ax.hlines(
            [0.94, 1.10],
            *xlm,
            linestyles="dashed",
            color="r",
        )
        ax.set_title(
            f"LV Network: {simulation.ckts.ldNo[ii]}",
            fontsize="medium",
        )
        set_day_label()

        # dplt columns are the 0/25/50/75/100% quantiles over loads; keep them
        # for the downloadable CSV.
        data_out_lv_comparison = np.c_[data_out_lv_comparison, dplt.T]

    head_lv_comparison = [
        f"{int(q)}% quantile: LV Network: {simulation.ckts.ldNo[ii]}"
        for ii in range(simulation.ckts.N)
        for q in np.linspace(0, 100, 5)
    ]

    # Raw strings so matplotlib mathtext escapes (\;) are not treated as
    # (invalid) Python string escapes.
    axs[0].text(
        0.1,
        1.0905,
        r"$Upper\;limit$",
        fontsize="small",
    )
    axs[0].text(
        0.1,
        0.9425,
        r"$Lower\;limit$",
        fontsize="small",
    )
    axs[0].set_ylabel("Voltage, per unit")

    # Set the x-label on the middle subplot, unless there are not enough
    # panels. Then use the last subplot.
    if len(axs) < 3:
        axs[len(axs) - 1].set_xlabel("Hour of the day")
    else:
        axs[2].set_xlabel("Hour of the day")
        axs[-1].set_xlabel("")

    xlm = plt.xlim()
    plt.xlim(xlm)
    plt.tight_layout()
    results["lv_comparison_png"] = _fig_to_png()
    results["lv_comparison_header"] = head_lv_comparison
    results["lv_comparison_data"] = data_out_lv_comparison

    # ------------------------------------------------------------------
    # PLOT: lv_unbalance — phase unbalance on the LV feeders
    # ------------------------------------------------------------------
    # LV feeders are 3-phase but customers are single-phase, spread across the
    # three phases. OpenDSS already solves this unbalanced; here we surface it.
    # This figure shows the IEC voltage unbalance factor (VUF = |V2|/|V1|) at
    # each LV substation over the day, against the ER P29 (1.3%) and EN 50160
    # (2%) planning levels. The per-phase customer-voltage envelopes are drawn
    # separately, one figure PER selected network (see lv_phase_pngs below), so
    # the frontend can let the user choose which network to inspect.
    vuf = np.array([s.VUF for s in slns])  # (48, n_networks)
    fig, axU = plt.subplots(figsize=(7, 3.4))

    for i in range(simulation.ckts.N):
        axU.plot(tt, vuf[:, i], ".-", color=f"C{i}", label=simulation.ckts.ldNo[i])
    xlmU = axU.get_xlim()
    axU.hlines(1.3, *xlmU, linestyles="dashed", color="orange", lw=1)
    axU.hlines(2.0, *xlmU, linestyles="dashed", color="r", lw=1)
    axU.text(tt[1], 1.33, "ER P29 (1.3%)", fontsize="small", color="orange")
    axU.text(tt[1], 2.03, "EN 50160 (2%)", fontsize="small", color="r")
    axU.set_xlim(xlmU)
    axU.set_ylim(bottom=0)
    axU.set_ylabel("Voltage unbalance factor, %")
    axU.set_title("Phase unbalance at LV substations")
    axU.legend(title="LV Network ID", fontsize="small")
    set_day_label(ax=axU)
    _shade_failed_steps(results["convergence"]["failed_hours"], ax=axU)
    plt.tight_layout()
    results["lv_unbalance_png"] = _fig_to_png()
    results["lv_unbalance_header"] = [
        f"VUF %: LV Network {simulation.ckts.ldNo[i]}" for i in range(simulation.ckts.N)
    ]
    results["lv_unbalance_data"] = vuf

    # PLOTS: lv_phase_pngs — per-phase customer-voltage envelope, one figure for
    # EACH selected LV network (keyed by network id). The data (s.VlvLds) is
    # already in memory, so this adds no extra power-flow solves.
    phase_clrs = {1: "C0", 2: "C1", 3: "C2"}
    lv_phase_pngs = {}
    for p_idx in range(simulation.ckts.N):
        net_id = str(simulation.ckts.ldNo[p_idx])
        phases = simulation._lv_n_phase[list(simulation._lv_n_phase.keys())[p_idx]]
        # |V| of every load in that network over the day, on a 230 V base.
        Vnet = np.abs(np.array([s.VlvLds[p_idx] for s in slns])[:, :, 0]) / 230.0
        plt.figure(figsize=(7, 3.4))
        axP = plt.gca()
        for ph in (1, 2, 3):
            sel = phases == ph
            if not np.any(sel):
                continue
            band = Vnet[:, sel]
            axP.fill_between(
                tt, band.min(axis=1), band.max(axis=1), color=phase_clrs[ph], alpha=0.25
            )
            axP.plot(tt, band.mean(axis=1), color=phase_clrs[ph], label=f"Phase {ph}")
        xlmP = axP.get_xlim()
        axP.hlines([0.94, 1.10], *xlmP, linestyles="dashed", color="r", lw=0.8)
        axP.set_xlim(xlmP)
        axP.set_ylabel("Voltage, pu (230 V base)")
        axP.set_title(f"Per-phase customer voltages — LV Network {net_id}")
        axP.legend(title="Phase", fontsize="small")
        set_day_label(ax=axP)
        _shade_failed_steps(results["convergence"]["failed_hours"], ax=axP)
        plt.tight_layout()
        lv_phase_pngs[net_id] = _fig_to_png()
    results["lv_phase_pngs"] = lv_phase_pngs

    # ------------------------------------------------------------------
    # PLOT: mv_voltages, voltage envelope against time
    # ------------------------------------------------------------------
    smv2pu = lambda s: np.abs(s.Vmv) / simulation.vKvbase[simulation.mvIdx]
    vb = np.array([smv2pu(s) for s in slns])
    _, dplt = fillplot(vb, np.linspace(0, 24, 48))
    set_day_label()
    xlm = plt.xlim()
    # MV statutory limits are +/-6% of nominal.
    plt.hlines([0.94, 1.06], *xlm, linestyle="dashed", color="r", lw=0.8)
    plt.xlim(xlm)
    plt.ylabel("MV Voltage, pu")
    plt.text(
        0.1,
        1.0535,
        r"$Upper\;limit$",
    )
    plt.text(
        0.1,
        0.941,
        r"$Lower\;limit$",
    )
    _shade_failed_steps(results["convergence"]["failed_hours"])
    results["mv_voltages_png"] = _fig_to_png()
    results["mv_voltages_header"] = [
        f"MV voltage: {qq}% quantile" for qq in np.linspace(0, 100, 5)
    ]
    results["mv_voltages_data"] = dplt.T

    # ------------------------------------------------------------------
    # PLOT: trn_powers — primary/secondary substation utilisation
    # ------------------------------------------------------------------
    spri = np.array([np.abs(s.Spri) for s in slns])
    ssec = np.array([np.abs(s.Ssec) for s in slns])

    d = funcsDss_turing.dssIfc(dss.DSS)
    trn_kva = d.getObjAttr(d.TRN, val="kva")
    # The primary substation is two parallel transformers (first two entries);
    # its rating is their sum.
    spri_rating = sum(trn_kva[:2])
    ssec_ratings = np.array([trn_kva[i - 1] for i in simulation.ckts.trnIdx])

    fig, [ax0, ax1] = plt.subplots(
        ncols=2,
        sharey=True,
    )
    ax0.plot(tt, 100 * spri / spri_rating, ".-")
    ax0.hlines(
        100,
        tt[0],
        tt[-1] + 3,
        linestyles="dashed",
        color="r",
    )
    set_day_label(
        ax=ax0,
    )
    ax0.set_ylabel("Substation utilization, %")
    ax0.set_title("Primary Sub. Utilization")
    ax1.plot(tt, 100 * ssec / ssec_ratings, ".-")
    ax1.hlines(
        100,
        tt[0],
        tt[-1] + 3,
        linestyles="dashed",
        color="r",
    )
    set_day_label(
        ax=ax1,
    )
    lgns = [
        simulation.ckts.ldNo[i] + f" ({int(ssec_ratings[i])} kVA)"
        for i in range(simulation.ckts.N)
    ]
    plt.legend(
        lgns,
        fontsize="small",
        title="LV Network (rating)",
    )
    ax1.set_title("Secondary Sub. Utilization")
    ylm = plt.ylim()
    plt.ylim((min([ylm[0], -1]), max([ylm[1], 101])))
    _shade_failed_steps(results["convergence"]["failed_hours"], ax=ax0)
    _shade_failed_steps(results["convergence"]["failed_hours"], ax=ax1)
    results["trn_powers_png"] = _fig_to_png()
    results["trn_powers_header"] = ["Prmy. Sub. Util."] + [
        "Sdry. Sub. Util." + l for l in lgns
    ]
    results["trn_powers_data"] = np.c_[
        np.expand_dims(100 * spri / spri_rating, axis=1), 100 * ssec / ssec_ratings
    ]

    # ------------------------------------------------------------------
    # PLOTS: profile_options / profile_options_dgs / profile_options_fcs
    # ------------------------------------------------------------------
    # Each plots the 1-D profiles in simulation.p, excluding a different set
    # of keys. (Profiles ending in "_" are means of 2-D profile matrices;
    # ic00_ is the built-in commercial profile.) All three are guarded against
    # an empty selection — new_hsl_map(0) divides by zero.
    ksel_all = [k for k, v in simulation.p.items() if v.ndim == 1]

    ksel = [
        k
        for k in ksel_all
        if k not in ("ic00_", "mv_fcs_profile_array_", "mv_solar_profile_array_")
    ]
    results["profile_options_png"] = (
        _plot_profile_selection(simulation, tt, ksel)
        if ksel
        else _placeholder_png("No LV profiles selected")
    )

    # DGs plot: only the MV solar (distributed generation) profile.
    ksel = [k for k in ksel_all if k == "mv_solar_profile_array_"]
    results["profile_options_dgs_png"] = (
        _plot_profile_selection(simulation, tt, ksel)
        if ksel
        else _placeholder_png("No MV solar profile selected")
    )

    # FCS plot: only the MV fast-charging-station profile.
    ksel = [k for k in ksel_all if k == "mv_fcs_profile_array_"]
    results["profile_options_fcs_png"] = (
        _plot_profile_selection(simulation, tt, ksel)
        if ksel
        else _placeholder_png("No MV fast-charging profile selected")
    )

    # ------------------------------------------------------------------
    # PLOTS: pmry_loadings and pmry_powers — per-feeder power flows
    # ------------------------------------------------------------------
    # splt[t, i]: apparent power (kVA) through MV feeder i at time step t.
    splt = np.array([np.abs(np.sum(ss["Sfmv"], axis=1)) for ss in slns])

    # PLOT: pmry_loadings
    yy = 1e2 * 1e-3 * splt / np.array([v for v in simulation.fdr2pwr.values()])  # in %
    _ = [
        plt.plot(tt, yy[:, i], color=matplotlib.cm.tab20(i)) for i in range(yy.shape[1])
    ]
    lgnd = [
        f"F{i+1} (to {b}), {p} MVA"
        for i, (b, p) in enumerate(simulation.fdr2pwr.items())
    ]
    plt.legend(lgnd, loc=(1.03, 0.2), fontsize="small", title="Feeder (to), rating")
    plt.hlines(
        100,
        tt[0],
        tt[-1] + 3,
        linestyles="dashed",
        color="r",
    )
    set_day_label()
    plt.ylabel("Power, % of rated")
    _shade_failed_steps(results["convergence"]["failed_hours"])
    plt.tight_layout()
    results["pmry_loadings_png"] = _fig_to_png()
    results["primary_loadings_header"] = lgnd
    results["primary_loadings_data"] = yy

    # PLOT: pmry_powers
    plt.figure()
    plt.plot(tt, splt / 1e3)
    _ = [
        plt.text(0, splt[0][i] / 1e3, f"{b} (F{i+1}, {p} MVA)")
        for i, (b, p) in enumerate(simulation.fdr2pwr.items())
    ]
    set_day_label()
    plt.ylabel("Power, MVA")
    plt.tight_layout()
    results["pmry_powers_png"] = _fig_to_png()

    return results


if __name__ == "__main__":
    run_dss_simulation(aox.run_dict0)
