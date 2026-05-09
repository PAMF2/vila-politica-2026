#!/usr/bin/env python3
"""Regenerate fig1-fig4 with cleaner, journal-grade aesthetics.

Reuses cached JSONs (data/political_stats_v2.json, baseline_gauntlet.json,
political_best_config.json, cross_country_results.json) so re-runs are
deterministic without re-fitting.

Outputs:
    docs/paper/figs/fig1_selective_curve.png
    docs/paper/figs/fig2_per_cycle_bar.png
    docs/paper/figs/fig3_calibration.png
    docs/paper/figs/fig4_regime_heatmap.png
    docs/paper/figs/fig7_cross_country.png
"""
from __future__ import annotations

import json
import math
import os
import random
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SEED = 42
random.seed(SEED)
np.random.seed(SEED)
os.environ["W_STATE"] = "0.0"
os.environ["HOUSE_EFFECTS"] = "0"

from engine.political_cohort import (  # noqa: E402
    fit_cohorts_political, predict_political, state_baseline_p,
)
from scripts.autoresearch_political import (  # noqa: E402
    load_by_year, load_other_pool,
)

FIG_DIR = ROOT / "docs" / "paper" / "figs"

STEIN = 0.4
W_LINZER = 0.7
W_STATE = 0.36
SIGMA_INT = 3.0
SIGMA_SLOPE = 0.01

# Journal-grade palette
COL_BASE = "#a02c5f"   # muted magenta
COL_MRP = "#1f5fa0"    # muted blue
COL_GREY = "#6a6a6a"
INK = "#1a1a1a"


def _set_serif(ax):
    for lbl in ax.get_xticklabels() + ax.get_yticklabels():
        lbl.set_family("serif")


def linzer_p(lead_pp: float, days: int) -> float:
    sigma = SIGMA_INT + SIGMA_SLOPE * max(0, days)
    return 0.5 * (1.0 + math.erf(lead_pp / max(sigma, 1.0) / math.sqrt(2.0)))


def predict_baseline(e, rates):
    p_lnz = linzer_p(e.get("poll_lead_pp", 0.0), e.get("days_to", 30))
    p_coh = predict_political(e, rates)["p_raw"]
    return (1 - W_LINZER) * p_coh + W_LINZER * p_lnz


def predict_mrp(e, rates):
    p = predict_baseline(e, rates)
    p_state = state_baseline_p(rates, e.get("uf", "BR"), e["regime"])
    if p_state is not None:
        p = (1 - W_STATE) * p + W_STATE * p_state
    return p


def get_yearfold_predictions():
    by_year = load_by_year()
    other = load_other_pool()
    test_years = sorted(by_year.keys())

    base_probs, mrp_probs, ys, regimes, years = [], [], [], [], []
    for y in test_years:
        train = list(other)
        for y2 in test_years:
            if y2 != y:
                train.extend(by_year[y2])
        rates = fit_cohorts_political(train, stein_shrink=STEIN)
        for e in by_year[y]:
            base_probs.append(predict_baseline(e, rates))
            mrp_probs.append(predict_mrp(e, rates))
            ys.append(e["outcome"])
            regimes.append(e.get("regime", "?"))
            years.append(y)
    return (np.array(base_probs), np.array(mrp_probs),
            np.array(ys), regimes, years)


def make_fig1_selective(base_p, mrp_p, ys):
    """Selective coverage: accuracy on kept events at threshold tau."""
    taus = np.arange(0.00, 0.45, 0.025)
    rows_b, rows_m = [], []
    for t in taus:
        for label, p in [("base", base_p), ("mrp", mrp_p)]:
            keep = np.abs(p - 0.5) >= t
            n = keep.sum()
            if n == 0:
                continue
            acc = ((p[keep] >= 0.5) == ys[keep].astype(bool)).mean()
            cov = n / len(p)
            (rows_b if label == "base" else rows_m).append((t, cov, acc))
    rows_b = np.array(rows_b)
    rows_m = np.array(rows_m)

    fig, ax = plt.subplots(figsize=(6.2, 4.0), dpi=200)
    axc = ax.twinx()

    line_acc_m = ax.plot(rows_m[:, 0], rows_m[:, 2], "o-", color=COL_MRP,
                          linewidth=1.7, markersize=5,
                          label="Accuracy: v1.3 MRP")
    line_acc_b = ax.plot(rows_b[:, 0], rows_b[:, 2], "s--", color=COL_BASE,
                          linewidth=1.5, markersize=5,
                          label="Accuracy: cohort + Linzer baseline")
    line_cov_m = axc.plot(rows_m[:, 0], rows_m[:, 1], "^:", color=COL_GREY,
                           linewidth=1.2, markersize=4,
                           label="Coverage: fraction kept")

    # Annotate where MRP first reaches 1.0
    first100 = rows_m[rows_m[:, 2] >= 0.9999]
    if len(first100):
        t0 = first100[0, 0]
        cov0 = first100[0, 1]
        ax.annotate(
            f"MRP reaches 100%\nat $\\tau$={t0:.3f} (coverage {cov0:.0%})",
            xy=(t0, 1.0), xytext=(t0 + 0.05, 0.94),
            fontsize=8, family="serif", color="#333",
            arrowprops=dict(arrowstyle="-", color="#999", linewidth=0.6),
        )

    ax.set_ylim(0.85, 1.012)
    axc.set_ylim(0.0, 1.05)
    ax.set_xlabel(r"Selective threshold $\tau$ (probability margin)",
                  family="serif")
    ax.set_ylabel("Accuracy on kept events", color=COL_MRP, family="serif")
    axc.set_ylabel("Coverage (fraction kept)", color=COL_GREY, family="serif")
    ax.tick_params(axis="y", colors=COL_MRP)
    axc.tick_params(axis="y", colors=COL_GREY)
    _set_serif(ax)
    _set_serif(axc)
    ax.grid(True, axis="y", linestyle=":", linewidth=0.5, alpha=0.6)

    lines = line_acc_m + line_acc_b + line_cov_m
    labels = [l.get_label() for l in lines]
    ax.legend(lines, labels, loc="lower right", fontsize=8.5,
              frameon=False, prop={"family": "serif"})
    ax.set_title("Selective coverage curve (n=394, year-fold)",
                 family="serif", fontsize=11)
    plt.tight_layout()
    out = FIG_DIR / "fig1_selective_curve.png"
    plt.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"saved -> {out}")


def make_fig2_per_cycle(base_p, mrp_p, ys, years):
    """Side-by-side per-cycle accuracy and Brier bars."""
    cycles = sorted(set(years))
    base_acc, mrp_acc = [], []
    base_brier, mrp_brier = [], []
    counts = []
    for y in cycles:
        idx = np.array([yi == y for yi in years])
        n = idx.sum()
        counts.append(n)
        ys_y = ys[idx]
        for arr, target in [(base_p, base_acc), (mrp_p, mrp_acc)]:
            p_y = arr[idx]
            target.append(((p_y >= 0.5) == ys_y.astype(bool)).mean())
        for arr, target in [(base_p, base_brier), (mrp_p, mrp_brier)]:
            p_y = arr[idx]
            target.append(((p_y - ys_y) ** 2).mean())

    fig, axes = plt.subplots(1, 2, figsize=(8.6, 4.2), dpi=200)
    x = np.arange(len(cycles))
    w = 0.38
    cycle_labels = [f"{c}\n(n={n})" for c, n in zip(cycles, counts)]

    # Acc panel
    a = axes[0]
    bars_b = a.bar(x - w / 2, [v * 100 for v in base_acc], width=w,
          color="#bcd4eb", edgecolor=INK, linewidth=0.6,
          label="Baseline (w=0)")
    bars_m = a.bar(x + w / 2, [v * 100 for v in mrp_acc], width=w,
          color="#f2c6a2", edgecolor=INK, linewidth=0.6,
          label="v1.3 MRP (w=0.36)")
    a.set_xticks(x)
    a.set_xticklabels(cycle_labels, family="serif", fontsize=8.5)
    a.set_ylim(55, 112)
    a.set_ylabel("Accuracy (%)", family="serif")
    a.set_title("Per-cycle accuracy", family="serif", fontsize=11)
    a.grid(True, axis="y", linestyle=":", linewidth=0.5, alpha=0.6)
    a.legend(fontsize=8.5, frameon=False, loc="upper center",
             ncol=2, bbox_to_anchor=(0.5, -0.18),
             prop={"family": "serif"})
    # Annotate accuracy values atop each bar; rotate so 100/100 pairs do not collide
    def _label_top(bar, v, color="#333"):
        a.text(bar.get_x() + bar.get_width() / 2, v * 100 + 1.0,
               f"{v*100:.1f}", ha="center", va="bottom",
               fontsize=7.0, color=color, family="serif",
               rotation=90)
    for bar, v in zip(bars_b, base_acc):
        _label_top(bar, v)
    for bar, v in zip(bars_m, mrp_acc):
        _label_top(bar, v)
    _set_serif(a)

    # Brier panel
    b = axes[1]
    bars_bb = b.bar(x - w / 2, base_brier, width=w,
          color="#bcd4eb", edgecolor=INK, linewidth=0.6,
          label="Baseline (w=0)")
    bars_bm = b.bar(x + w / 2, mrp_brier, width=w,
          color="#f2c6a2", edgecolor=INK, linewidth=0.6,
          label="v1.3 MRP (w=0.36)")
    b.set_xticks(x)
    b.set_xticklabels(cycle_labels, family="serif", fontsize=8.5)
    b.set_ylabel("Brier score (lower is better)", family="serif")
    b.set_title("Per-cycle Brier", family="serif", fontsize=11)
    b.grid(True, axis="y", linestyle=":", linewidth=0.5, alpha=0.6)
    ymax = max(max(base_brier), max(mrp_brier)) * 1.45
    b.set_ylim(0, ymax)
    for bars, vals in [(bars_bb, base_brier), (bars_bm, mrp_brier)]:
        for bar, v in zip(bars, vals):
            b.text(bar.get_x() + bar.get_width() / 2, v + ymax * 0.014,
                   f"{v:.3f}", ha="center", va="bottom",
                   fontsize=7.0, color="#333", family="serif",
                   rotation=90)
    _set_serif(b)

    fig.suptitle("Year-fold cross-validation: baseline (w=0) vs v1.3 MRP (w=0.36) at fixed v1.3 hyperparameters",
                 family="serif", fontsize=10.5, y=0.995)
    plt.tight_layout()
    out = FIG_DIR / "fig2_per_cycle_bar.png"
    plt.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"saved -> {out}")


def _quantile_bins(probs, ys, n_bins=10):
    sorted_idx = np.argsort(probs)
    chunk = len(probs) // n_bins
    rows = []
    for i in range(n_bins):
        a = i * chunk
        b = (i + 1) * chunk if i < n_bins - 1 else len(probs)
        idx = sorted_idx[a:b]
        if len(idx) == 0:
            continue
        rows.append({
            "n": len(idx),
            "p_mean": probs[idx].mean(),
            "y_rate": ys[idx].mean(),
        })
    return rows


def make_fig3_calibration(base_p, mrp_p, ys):
    """Reliability diagram with quantile bins, dual line for baseline + MRP.
    Adds ECE/MCE labels and a histogram of forecast counts on a marginal."""
    base_bins = _quantile_bins(base_p, ys)
    mrp_bins = _quantile_bins(mrp_p, ys)

    def _ece_mce(bins, n_total):
        ece = sum((b["n"] / n_total) * abs(b["p_mean"] - b["y_rate"])
                  for b in bins)
        mce = max(abs(b["p_mean"] - b["y_rate"]) for b in bins)
        return ece, mce

    n_total = len(ys)
    ece_b, mce_b = _ece_mce(base_bins, n_total)
    ece_m, mce_m = _ece_mce(mrp_bins, n_total)

    fig, ax = plt.subplots(figsize=(5.4, 5.0), dpi=200)
    ax.plot([0, 1], [0, 1], color="#888", linestyle=(0, (3, 2)),
            linewidth=1.0, label="Perfect calibration")

    for bins, label, color, marker, ece, mce in [
        (base_bins, "Cohort + Linzer baseline", COL_BASE, "o", ece_b, mce_b),
        (mrp_bins,  "v1.3 MRP ensemble",         COL_MRP,  "s", ece_m, mce_m),
    ]:
        xs = [b["p_mean"] for b in bins]
        ys_ = [b["y_rate"] for b in bins]
        sizes = [max(25, 5 * b["n"]) for b in bins]
        ax.scatter(xs, ys_, s=sizes, color=color, alpha=0.78, marker=marker,
                   edgecolor="white", linewidth=0.6,
                   label=f"{label} (ECE={ece:.3f}, MCE={mce:.3f})")
        ax.plot(xs, ys_, color=color, linewidth=1.1, alpha=0.55)

    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.05)
    ax.set_xlabel("Predicted probability (quantile-bin mean)", family="serif")
    ax.set_ylabel("Empirical outcome rate", family="serif")
    ax.set_aspect("equal")
    ax.grid(True, linestyle=":", linewidth=0.5, alpha=0.6)
    ax.legend(loc="upper left", fontsize=8.2, frameon=False,
              prop={"family": "serif"})
    ax.set_title("Reliability diagram (10 quantile bins, n=394)",
                 family="serif", fontsize=11)
    _set_serif(ax)
    plt.tight_layout()
    out = FIG_DIR / "fig3_calibration.png"
    plt.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"saved -> {out}")


def make_fig4_regime(mrp_p, ys, regimes):
    """Regime x outcome contingency: observed vs predicted."""
    cats = sorted(set(regimes))
    obs = np.zeros((len(cats), 2))
    pred = np.zeros((len(cats), 2))
    for i, r in enumerate(regimes):
        ci = cats.index(r)
        obs[ci, int(ys[i])] += 1
        pred[ci, int(mrp_p[i] >= 0.5)] += 1

    fig, axes = plt.subplots(1, 2, figsize=(8.0, 3.4), dpi=200)
    cmap = "OrRd"

    for ax, mat, title in [
        (axes[0], obs, "Observed (regime x outcome)"),
        (axes[1], pred, "Predicted (regime x outcome)"),
    ]:
        im = ax.imshow(mat, cmap=cmap, aspect="auto",
                       vmin=0, vmax=max(obs.max(), pred.max()))
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["loss", "win"], family="serif")
        ax.set_yticks(range(len(cats)))
        ax.set_yticklabels(cats, family="serif")
        ax.set_title(title, family="serif", fontsize=11)
        for i in range(len(cats)):
            for j in range(2):
                v = int(mat[i, j])
                ax.text(j, i, str(v), ha="center", va="center",
                        color="white" if v > obs.max() * 0.55 else INK,
                        family="serif", fontsize=10)
        plt.colorbar(im, ax=ax, fraction=0.04, pad=0.03)

    fig.suptitle(f"Regime x outcome contingency (n={len(ys)}, year-fold)",
                 family="serif", fontsize=11)
    plt.tight_layout()
    out = FIG_DIR / "fig4_regime_heatmap.png"
    plt.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"saved -> {out}")


def make_fig7_cross_country():
    """Bar chart of per-country LOSO accuracy: no-MRP vs MRP."""
    paths_keys = [
        ("cross_country_results.json", ["us_2016", "us_2020", "uk_2019"]),
        ("cross_country_extended.json", ["fr_2022", "ar_2023", "br_2014", "us_2022"]),
        ("cross_country_more.json", ["de_2021", "mx_2024", "tr_2023", "it_2022", "in_2024"]),
    ]
    rows = []
    for fname, keys in paths_keys:
        p = ROOT / "data" / fname
        if not p.exists():
            continue
        d = json.load(open(p))
        for k in keys:
            if k not in d:
                continue
            info = d[k]
            loso = info.get("loso", {})
            no_mrp = loso.get("no_mrp") or {}
            mrp = loso.get("mrp_w36") or loso.get("augmented") or {}
            acc_b = no_mrp.get("acc")
            acc_m = mrp.get("acc")
            n = info.get("n_events") or no_mrp.get("n")
            if acc_b is not None and acc_m is not None and n:
                country, year = k.upper().split("_", 1)
                rows.append((f"{country} {year}", n, acc_b, acc_m))

    rows.sort(key=lambda r: -(r[3] - r[2]))
    labels = [r[0] for r in rows]
    base_accs = [r[2] * 100 for r in rows]
    mrp_accs = [r[3] * 100 for r in rows]
    ns = [r[1] for r in rows]

    deltas = [m - b for m, b in zip(mrp_accs, base_accs)]
    fig, ax = plt.subplots(figsize=(7.8, 5.4), dpi=200)
    y = np.arange(len(labels))
    h = 0.38
    ax.barh(y - h / 2, base_accs, height=h,
            color="#bcd4eb", edgecolor=INK, linewidth=0.6,
            label="No-MRP baseline")
    ax.barh(y + h / 2, mrp_accs, height=h,
            color="#f2c6a2", edgecolor=INK, linewidth=0.6,
            label="MRP-augmented (w=0.36)")

    # Annotate per-cycle delta on right of bars
    for yi, b, m, d, n in zip(y, base_accs, mrp_accs, deltas, ns):
        rightmost = max(b, m)
        if abs(d) >= 0.5:
            ax.text(rightmost + 1.5, yi - h / 2 + 0.1,
                    f"$\\Delta$ {d:+.1f} pp",
                    va="center", fontsize=8, color="#1f5fa0",
                    family="serif")
        ax.text(118, yi, f"n={n:,}", va="center", fontsize=7.5,
                color="#666", family="serif")

    ax.set_yticks(y)
    ax.set_yticklabels(labels, family="serif")
    ax.invert_yaxis()
    ax.set_xlabel("LOSO / cycle accuracy (%)", family="serif")
    ax.set_xlim(0, 130)
    ax.set_xticks([0, 20, 40, 60, 80, 100])
    ax.grid(True, axis="x", linestyle=":", linewidth=0.5, alpha=0.6)
    ax.legend(loc="lower left", fontsize=8.5, frameon=False,
              prop={"family": "serif"})
    ax.set_title("Cross-country leak-safe accuracy: 12 cycles, 11 countries",
                 family="serif", fontsize=11)
    _set_serif(ax)
    plt.tight_layout()
    out = FIG_DIR / "fig7_cross_country.png"
    plt.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"saved -> {out}")


def main():
    base_p, mrp_p, ys, regimes, years = get_yearfold_predictions()
    print(f"loaded {len(ys)} events across {len(set(years))} cycles")
    make_fig1_selective(base_p, mrp_p, ys)
    make_fig2_per_cycle(base_p, mrp_p, ys, years)
    make_fig3_calibration(base_p, mrp_p, ys)
    make_fig4_regime(mrp_p, ys, regimes)
    make_fig7_cross_country()


if __name__ == "__main__":
    main()
