#!/usr/bin/env python3
"""Heteroscedastic Linzer drift experiment.

Tests whether allowing the Linzer drift parameters $(\\sigma_0, \\sigma_1)$
to vary by cycle improves calibration over the scalar baseline used in
v1.3 production.

Protocol (leak-safe):
    For each test year y in {2010, 2016, 2018, 2020, 2022, 2024}:
        1. Train pool = events from years != y (plus qualitative pool).
        2. Grid-search (sigma_int, sigma_slope) on training events to
           minimize TRAINING Brier of the Linzer-only model.
        3. Apply selected per-cycle drift to test year y inside the v1.3
           ensemble (cohort + Linzer + state baseline at w=0.36).
        4. Record per-year accuracy and Brier.

Compare to fixed scalar baseline (sigma_int=3.0, sigma_slope=0.01).

Saves results to data/bench_hetero_linzer.json.
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

# Scalar baseline (production v1.3)
SIGMA_INT_FIXED = 3.0
SIGMA_SLOPE_FIXED = 0.01

# Grid for per-cycle adaptation
SIGMA_INT_GRID = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 8.0]
SIGMA_SLOPE_GRID = [0.0, 0.005, 0.01, 0.02, 0.05, 0.10]


def linzer_p(lead_pp: float, days: int, s_int: float, s_slope: float) -> float:
    sigma = s_int + s_slope * max(0, days)
    z = lead_pp / max(sigma, 1.0)
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def predict_blend(event: dict, rates: dict, s_int: float, s_slope: float) -> float:
    lead = event.get("poll_lead_pp", 0.0)
    days = event.get("days_to", 30)
    p_lnz = linzer_p(lead, days, s_int, s_slope)
    p_coh = predict_political(event, rates)["p_raw"]
    p_blend = (1 - W_LINZER) * p_coh + W_LINZER * p_lnz
    uf = event.get("uf", "BR")
    p_state = state_baseline_p(rates, uf, event["regime"])
    if p_state is not None:
        p_blend = (1 - W_STATE) * p_blend + W_STATE * p_state
    return p_blend


def linzer_only_brier(events: list[dict], s_int: float, s_slope: float) -> float:
    """Plain Linzer Brier on a set of events (used for per-cycle fit)."""
    n = len(events)
    if n == 0:
        return 1.0
    s = 0.0
    for e in events:
        p = linzer_p(e.get("poll_lead_pp", 0.0),
                     e.get("days_to", 30), s_int, s_slope)
        s += (p - e["outcome"]) ** 2
    return s / n


def metrics(events: list[dict], probs: list[float]) -> dict:
    n = len(events)
    if n == 0:
        return {"n": 0}
    brier = sum((p - e["outcome"]) ** 2 for p, e in zip(probs, events)) / n
    hits = sum(1 for p, e in zip(probs, events)
               if (p >= 0.5) == bool(e["outcome"]))
    return {"n": n, "acc": hits / n, "brier": brier}


def fit_per_cycle_drift(train_events: list[dict]) -> tuple[float, float, float]:
    """Grid-search (sigma_int, sigma_slope) minimizing Linzer-only training
    Brier. Returns (sigma_int, sigma_slope, brier_train)."""
    best = (SIGMA_INT_FIXED, SIGMA_SLOPE_FIXED,
            linzer_only_brier(train_events, SIGMA_INT_FIXED, SIGMA_SLOPE_FIXED))
    for s_int in SIGMA_INT_GRID:
        for s_slope in SIGMA_SLOPE_GRID:
            b = linzer_only_brier(train_events, s_int, s_slope)
            if b < best[2]:
                best = (s_int, s_slope, b)
    return best


def run() -> dict:
    by_year = load_by_year()
    other = load_other_pool()
    test_years = sorted(by_year.keys())

    summary = {
        "config": {
            "stein_shrink": STEIN,
            "w_linzer": W_LINZER,
            "w_state": W_STATE,
            "sigma_int_fixed": SIGMA_INT_FIXED,
            "sigma_slope_fixed": SIGMA_SLOPE_FIXED,
            "sigma_int_grid": SIGMA_INT_GRID,
            "sigma_slope_grid": SIGMA_SLOPE_GRID,
            "seed": SEED,
        },
        "per_year": {},
        "totals": {},
    }

    fixed_total_n = 0
    fixed_total_brier = 0.0
    fixed_total_hits = 0
    hetero_total_brier = 0.0
    hetero_total_hits = 0

    for y in test_years:
        train = list(other)
        for y2 in test_years:
            if y2 != y:
                train.extend(by_year[y2])
        rates = fit_cohorts_political(train, stein_shrink=STEIN)
        events = by_year[y]

        # Fixed scalar baseline
        probs_fixed = [predict_blend(e, rates, SIGMA_INT_FIXED, SIGMA_SLOPE_FIXED)
                       for e in events]
        m_fixed = metrics(events, probs_fixed)

        # Per-cycle adapted: fit on train, apply to test
        s_int_y, s_slope_y, b_train = fit_per_cycle_drift(train)
        probs_hetero = [predict_blend(e, rates, s_int_y, s_slope_y)
                        for e in events]
        m_hetero = metrics(events, probs_hetero)

        summary["per_year"][str(y)] = {
            "n": len(events),
            "fixed": m_fixed,
            "hetero": m_hetero,
            "fitted_sigma_int": s_int_y,
            "fitted_sigma_slope": s_slope_y,
            "train_brier_at_fit": b_train,
        }

        fixed_total_n += m_fixed["n"]
        fixed_total_brier += m_fixed["brier"] * m_fixed["n"]
        fixed_total_hits += m_fixed["acc"] * m_fixed["n"]
        hetero_total_brier += m_hetero["brier"] * m_hetero["n"]
        hetero_total_hits += m_hetero["acc"] * m_hetero["n"]

    summary["totals"] = {
        "n": fixed_total_n,
        "fixed": {
            "acc": fixed_total_hits / fixed_total_n,
            "brier": fixed_total_brier / fixed_total_n,
        },
        "hetero": {
            "acc": hetero_total_hits / fixed_total_n,
            "brier": hetero_total_brier / fixed_total_n,
        },
    }
    return summary


def main() -> None:
    payload = run()
    out = ROOT / "data" / "bench_hetero_linzer.json"
    out.write_text(json.dumps(payload, indent=2))
    print(f"saved -> {out}")
    t = payload["totals"]
    print()
    print(f"Fixed   sigma=({SIGMA_INT_FIXED}, {SIGMA_SLOPE_FIXED}):"
          f"  acc={t['fixed']['acc']:.4f}  brier={t['fixed']['brier']:.4f}")
    print(f"Hetero  per-cycle              :"
          f"  acc={t['hetero']['acc']:.4f}  brier={t['hetero']['brier']:.4f}")
    print()
    print("Per-year (n, fixed_acc, hetero_acc, fixed_brier, hetero_brier, "
          "fitted_sigma_int, fitted_sigma_slope):")
    for y, r in payload["per_year"].items():
        print(f"  {y}  n={r['n']:>3}  "
              f"fixed_acc={r['fixed']['acc']:.4f}  "
              f"hetero_acc={r['hetero']['acc']:.4f}  "
              f"fixed_brier={r['fixed']['brier']:.4f}  "
              f"hetero_brier={r['hetero']['brier']:.4f}  "
              f"sigma=({r['fitted_sigma_int']}, {r['fitted_sigma_slope']})")


if __name__ == "__main__":
    main()
