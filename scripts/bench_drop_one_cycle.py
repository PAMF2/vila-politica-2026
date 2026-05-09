#!/usr/bin/env python3
"""Drop-one-cycle ablation.

For each Brazilian cycle y in {2010, 2016, 2018, 2020, 2022, 2024}, drop
all events from year y from the training pool and re-run the standard
year-fold cross-validation on the remaining 5 cycles. Tests whether the
v1.3 ensemble's headline accuracy is dominated by any single cycle in
the training set.

Saves results to data/bench_drop_one_cycle.json.
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


def linzer_p(lead_pp: float, days: int) -> float:
    sigma = SIGMA_INT + SIGMA_SLOPE * max(0, days)
    return 0.5 * (1.0 + math.erf(lead_pp / max(sigma, 1.0) / math.sqrt(2.0)))


def predict_blend(event: dict, rates: dict) -> float:
    lead = event.get("poll_lead_pp", 0.0)
    days = event.get("days_to", 30)
    p_lnz = linzer_p(lead, days)
    p_coh = predict_political(event, rates)["p_raw"]
    p_blend = (1 - W_LINZER) * p_coh + W_LINZER * p_lnz
    uf = event.get("uf", "BR")
    p_state = state_baseline_p(rates, uf, event["regime"])
    if p_state is not None:
        p_blend = (1 - W_STATE) * p_blend + W_STATE * p_state
    return p_blend


def metrics(events: list[dict], probs: list[float]) -> dict:
    n = len(events)
    if n == 0:
        return {"n": 0, "acc": None, "brier": None}
    brier = sum((p - e["outcome"]) ** 2 for p, e in zip(probs, events)) / n
    hits = sum(1 for p, e in zip(probs, events)
               if (p >= 0.5) == bool(e["outcome"]))
    return {"n": n, "acc": hits / n, "brier": brier}


def yearfold_cv_with_drop(by_year: dict, other: list[dict],
                          dropped_cycle: int | None) -> dict:
    """Run year-fold CV on all cycles except `dropped_cycle`. The dropped
    cycle is removed from training AND test."""
    test_years = sorted([y for y in by_year if y != dropped_cycle])
    n_total = 0
    hits_total = 0
    brier_total = 0.0
    per_year = {}
    for y in test_years:
        train = list(other)
        for y2 in test_years:
            if y2 != y:
                train.extend(by_year[y2])
        rates = fit_cohorts_political(train, stein_shrink=STEIN)
        events = by_year[y]
        probs = [predict_blend(e, rates) for e in events]
        m = metrics(events, probs)
        per_year[str(y)] = m
        n_total += m["n"]
        hits_total += int(round(m["acc"] * m["n"]))
        brier_total += m["brier"] * m["n"]
    return {
        "n": n_total,
        "acc": hits_total / max(n_total, 1),
        "brier": brier_total / max(n_total, 1),
        "per_year": per_year,
    }


def run() -> dict:
    by_year = load_by_year()
    other = load_other_pool()
    cycles = sorted(by_year.keys())

    baseline = yearfold_cv_with_drop(by_year, other, dropped_cycle=None)
    drops = {}
    for y in cycles:
        drops[str(y)] = yearfold_cv_with_drop(by_year, other, dropped_cycle=y)

    return {
        "config": {
            "stein_shrink": STEIN,
            "w_linzer": W_LINZER,
            "w_state": W_STATE,
            "sigma_int": SIGMA_INT,
            "sigma_slope": SIGMA_SLOPE,
            "seed": SEED,
        },
        "cycles": cycles,
        "baseline_no_drop": baseline,
        "drop_one": drops,
    }


def main() -> None:
    payload = run()
    out = ROOT / "data" / "bench_drop_one_cycle.json"
    out.write_text(json.dumps(payload, indent=2))
    print(f"saved -> {out}")
    b = payload["baseline_no_drop"]
    print()
    print(f"Baseline (no drop):  n={b['n']}  acc={b['acc']:.4f}  brier={b['brier']:.4f}")
    print()
    print("Drop-one-cycle:")
    for y, r in payload["drop_one"].items():
        delta = r["acc"] - b["acc"]
        print(f"  drop {y:>4}:  n={r['n']:>3}  acc={r['acc']:.4f}  "
              f"brier={r['brier']:.4f}  delta_acc={delta:+.4f}")


if __name__ == "__main__":
    main()
