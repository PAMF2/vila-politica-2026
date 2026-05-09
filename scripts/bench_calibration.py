#!/usr/bin/env python3
"""Reliability diagram + Expected Calibration Error.

Bins the v1.3 ensemble's predictions into deciles and plots empirical
outcome rate vs predicted probability. Computes Expected Calibration
Error (ECE) and Maximum Calibration Error (MCE) for both baseline and
MRP-augmented predictions.

Saves data/bench_calibration.json + docs/paper/figs/fig6_calibration_curves.png.
"""
from __future__ import annotations

import json
import math
import os
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SEED = 42
random.seed(SEED)
os.environ["W_STATE"] = "0.0"
os.environ["HOUSE_EFFECTS"] = "0"

from engine.political_cohort import (  # noqa: E402
    fit_cohorts_political,
    predict_political,
    state_baseline_p,
)
from scripts.autoresearch_political import (  # noqa: E402
    load_by_year,
    load_other_pool,
)

STEIN = 0.4
W_LINZER = 0.7
W_STATE = 0.36
SIGMA_INT = 3.0
SIGMA_SLOPE = 0.01
N_BINS = 10


def linzer_p(lead_pp: float, days: int) -> float:
    sigma = SIGMA_INT + SIGMA_SLOPE * max(0, days)
    return 0.5 * (1.0 + math.erf(lead_pp / max(sigma, 1.0) / math.sqrt(2.0)))


def predict_baseline(event: dict, rates: dict) -> float:
    lead = event.get("poll_lead_pp", 0.0)
    days = event.get("days_to", 30)
    p_lnz = linzer_p(lead, days)
    p_coh = predict_political(event, rates)["p_raw"]
    return (1 - W_LINZER) * p_coh + W_LINZER * p_lnz


def predict_mrp(event: dict, rates: dict) -> float:
    p = predict_baseline(event, rates)
    uf = event.get("uf", "BR")
    p_state = state_baseline_p(rates, uf, event["regime"])
    if p_state is not None:
        p = (1 - W_STATE) * p + W_STATE * p_state
    return p


def reliability_curve(probs: list[float], outcomes: list[int],
                      n_bins: int = N_BINS) -> dict:
    """Equal-width binning [0, 1] in n_bins. Returns per-bin stats + ECE/MCE."""
    bins = [{"lo": i / n_bins, "hi": (i + 1) / n_bins,
             "n": 0, "p_sum": 0.0, "y_sum": 0}
            for i in range(n_bins)]
    for p, y in zip(probs, outcomes):
        idx = min(int(p * n_bins), n_bins - 1)
        bins[idx]["n"] += 1
        bins[idx]["p_sum"] += p
        bins[idx]["y_sum"] += y
    n_total = sum(b["n"] for b in bins)
    rows = []
    ece = 0.0
    mce = 0.0
    for b in bins:
        if b["n"] == 0:
            rows.append({**b, "p_mean": None, "y_rate": None,
                         "abs_gap": None, "weight": 0.0})
            continue
        p_mean = b["p_sum"] / b["n"]
        y_rate = b["y_sum"] / b["n"]
        gap = abs(p_mean - y_rate)
        ece += (b["n"] / n_total) * gap
        mce = max(mce, gap)
        rows.append({"lo": b["lo"], "hi": b["hi"], "n": b["n"],
                     "p_mean": p_mean, "y_rate": y_rate,
                     "abs_gap": gap, "weight": b["n"] / n_total})
    return {"bins": rows, "ECE": ece, "MCE": mce, "n": n_total}


def run() -> dict:
    by_year = load_by_year()
    other = load_other_pool()
    test_years = sorted(by_year.keys())

    base_probs, mrp_probs, outcomes = [], [], []
    for y in test_years:
        train = list(other)
        for y2 in test_years:
            if y2 != y:
                train.extend(by_year[y2])
        rates = fit_cohorts_political(train, stein_shrink=STEIN)
        for e in by_year[y]:
            base_probs.append(predict_baseline(e, rates))
            mrp_probs.append(predict_mrp(e, rates))
            outcomes.append(e["outcome"])

    baseline_curve = reliability_curve(base_probs, outcomes)
    mrp_curve = reliability_curve(mrp_probs, outcomes)
    return {
        "config": {
            "stein_shrink": STEIN,
            "w_linzer": W_LINZER,
            "w_state": W_STATE,
            "sigma_int": SIGMA_INT,
            "sigma_slope": SIGMA_SLOPE,
            "n_bins": N_BINS,
            "seed": SEED,
        },
        "baseline_no_mrp": baseline_curve,
        "mrp_v13": mrp_curve,
    }


def make_figure(payload: dict, out_path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(4.4, 4.2), dpi=200)
    ax.plot([0, 1], [0, 1], color="#999", linestyle=(0, (3, 2)),
            linewidth=1.0, label="Perfect calibration")

    for label, key, color, marker in [
        ("Cohort+Linzer baseline", "baseline_no_mrp", "#a02c5f", "o"),
        ("v1.3 MRP ensemble",       "mrp_v13",         "#1f5fa0", "s"),
    ]:
        c = payload[key]
        xs, ys, sizes = [], [], []
        for b in c["bins"]:
            if b["p_mean"] is None:
                continue
            xs.append(b["p_mean"])
            ys.append(b["y_rate"])
            sizes.append(max(15, 6 * b["n"]))
        ax.scatter(xs, ys, s=sizes, color=color, alpha=0.75, marker=marker,
                   edgecolor="white", linewidth=0.5,
                   label=f"{label} (ECE = {c['ECE']:.3f}, MCE = {c['MCE']:.3f})")
        ax.plot(xs, ys, color=color, linewidth=1.0, alpha=0.5)

    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)
    ax.set_xlabel("Mean predicted probability (per bin)", family="serif")
    ax.set_ylabel("Empirical outcome rate (per bin)", family="serif")
    ax.set_aspect("equal")
    ax.grid(True, linestyle=":", linewidth=0.5, alpha=0.6)
    ax.legend(loc="upper left", fontsize=8, frameon=False,
              prop={"family": "serif"})
    ax.set_title("Reliability diagram: 10 equal-width bins, n=394",
                 family="serif", fontsize=11)
    plt.tight_layout()
    plt.savefig(out_path, dpi=200, bbox_inches="tight", facecolor="white")
    print(f"saved figure -> {out_path}")


def main() -> None:
    payload = run()
    out = ROOT / "data" / "bench_calibration.json"
    out.write_text(json.dumps(payload, indent=2))
    print(f"saved data -> {out}")
    fig_out = ROOT / "docs" / "paper" / "figs" / "fig6_calibration_curves.png"
    make_figure(payload, fig_out)
    print()
    print(f"Cohort+Linzer baseline:  ECE = {payload['baseline_no_mrp']['ECE']:.4f}  "
          f"MCE = {payload['baseline_no_mrp']['MCE']:.4f}")
    print(f"v1.3 MRP ensemble:       ECE = {payload['mrp_v13']['ECE']:.4f}  "
          f"MCE = {payload['mrp_v13']['MCE']:.4f}")


if __name__ == "__main__":
    main()
