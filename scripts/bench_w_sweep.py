#!/usr/bin/env python3
"""State-baseline weight sweep.

Holds the v1.3 production hyperparameters fixed (stein_shrink=0.4,
w_linzer=0.7, sigma_intercept=3.0, sigma_slope=0.01) and sweeps the
state-baseline blend weight w over [0, 0.6] in 0.05 steps. For each w,
runs leak-safe year-fold CV across the 394-event BR core and reports
Brier, accuracy, and the 2024 SP fold accuracy. Saves results to
data/bench_w_sweep.json and the figure to docs/paper/figs/fig5_w_sweep.png.
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
SIGMA_INT = 3.0
SIGMA_SLOPE = 0.01
W_GRID = [round(0.05 * i, 2) for i in range(0, 13)]  # 0.0 ... 0.60


def linzer_p(lead_pp: float, days: int) -> float:
    sigma = SIGMA_INT + SIGMA_SLOPE * max(0, days)
    z = lead_pp / max(sigma, 1.0)
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def predict_at_w(event: dict, rates: dict, w: float) -> float:
    lead = event.get("poll_lead_pp", 0.0)
    days = event.get("days_to", 30)
    p_lnz = linzer_p(lead, days)
    p_coh = predict_political(event, rates)["p_raw"]
    p_blend = (1 - W_LINZER) * p_coh + W_LINZER * p_lnz
    uf = event.get("uf", "BR")
    p_state = state_baseline_p(rates, uf, event["regime"])
    if p_state is not None:
        p_blend = (1 - w) * p_blend + w * p_state
    return p_blend


def run_sweep() -> dict:
    by_year = load_by_year()
    other = load_other_pool()
    test_years = sorted(by_year.keys())

    rates_by_year = {}
    for y in test_years:
        train = list(other)
        for y2 in test_years:
            if y2 != y:
                train.extend(by_year[y2])
        rates_by_year[y] = fit_cohorts_political(train, stein_shrink=STEIN)

    results = []
    for w in W_GRID:
        all_n = 0
        all_brier = 0.0
        all_hits = 0
        sp_n = 0
        sp_hits = 0
        sp_brier = 0.0
        per_year = {}
        for y in test_years:
            rates = rates_by_year[y]
            events = by_year[y]
            n = len(events)
            brier_y = 0.0
            hits_y = 0
            for e in events:
                p = predict_at_w(e, rates, w)
                y_obs = e["outcome"]
                brier_y += (p - y_obs) ** 2
                if (p >= 0.5) == bool(y_obs):
                    hits_y += 1
                if y == 2024 and e.get("uf") == "SP":
                    sp_n += 1
                    sp_brier += (p - y_obs) ** 2
                    if (p >= 0.5) == bool(y_obs):
                        sp_hits += 1
            per_year[str(y)] = {
                "n": n,
                "acc": hits_y / n,
                "brier": brier_y / n,
            }
            all_n += n
            all_brier += brier_y
            all_hits += hits_y
        results.append({
            "w": w,
            "n": all_n,
            "acc": all_hits / all_n,
            "brier": all_brier / all_n,
            "sp2024_n": sp_n,
            "sp2024_acc": (sp_hits / sp_n) if sp_n else None,
            "sp2024_brier": (sp_brier / sp_n) if sp_n else None,
            "per_year": per_year,
        })
    return {
        "config": {
            "stein_shrink": STEIN,
            "w_linzer": W_LINZER,
            "sigma_int": SIGMA_INT,
            "sigma_slope": SIGMA_SLOPE,
            "seed": SEED,
        },
        "w_grid": W_GRID,
        "results": results,
    }


def make_figure(payload: dict, out_path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ws = [r["w"] for r in payload["results"]]
    accs = [r["acc"] for r in payload["results"]]
    briers = [r["brier"] for r in payload["results"]]
    sp_accs = [r["sp2024_acc"] for r in payload["results"]]

    fig, ax1 = plt.subplots(figsize=(6.4, 3.8), dpi=200)
    ax2 = ax1.twinx()

    line_acc = ax1.plot(ws, accs, "o-", color="#1f5fa0",
                        linewidth=1.6, markersize=5,
                        label="Year-fold accuracy (n=394)")
    line_sp = ax1.plot(ws, sp_accs, "s--", color="#a02c5f",
                       linewidth=1.4, markersize=5,
                       label="2024 SP fold accuracy (n=68)")
    line_br = ax2.plot(ws, briers, "^:", color="#666",
                       linewidth=1.2, markersize=4,
                       label="Year-fold mean Brier")

    ax1.axvline(0.36, color="#444", linestyle=(0, (1, 2)), linewidth=0.8)
    ax1.annotate("selected\n$w = 0.36$",
                 xy=(0.36, 0.97), xytext=(0.16, 0.985),
                 fontsize=8.5, family="serif", color="#444",
                 ha="left",
                 arrowprops=dict(arrowstyle="-", color="#888", linewidth=0.6))

    ax1.set_xlabel("State-baseline weight $w$", family="serif")
    ax1.set_ylabel("Accuracy", color="#1f5fa0", family="serif")
    ax2.set_ylabel("Brier", color="#666", family="serif")
    ax1.tick_params(axis="y", colors="#1f5fa0")
    ax2.tick_params(axis="y", colors="#666")
    ax1.grid(True, axis="y", linestyle=":", linewidth=0.5, alpha=0.6)

    lines = line_acc + line_sp + line_br
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc="lower right", fontsize=8,
               frameon=False, prop={"family": "serif"})

    ax1.set_title("MRP weight sweep: accuracy and Brier vs $w$",
                  family="serif", fontsize=11)
    plt.tight_layout()
    plt.savefig(out_path, dpi=200, bbox_inches="tight", facecolor="white")
    print(f"saved figure -> {out_path}")


def main() -> None:
    payload = run_sweep()
    out = ROOT / "data" / "bench_w_sweep.json"
    out.write_text(json.dumps(payload, indent=2))
    print(f"saved results -> {out}")
    fig_out = ROOT / "docs" / "paper" / "figs" / "fig5_w_sweep.png"
    make_figure(payload, fig_out)
    print("\nSummary (w, acc, brier, sp2024_acc):")
    for r in payload["results"]:
        print(f"  w={r['w']:.2f}  acc={r['acc']:.4f}  "
              f"brier={r['brier']:.4f}  sp2024={r['sp2024_acc']:.4f}")


if __name__ == "__main__":
    main()
