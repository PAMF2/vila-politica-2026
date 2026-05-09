#!/usr/bin/env python3
"""Permutation test for the MRP gain.

Null hypothesis: the +5.33 pp accuracy gain from adding the state
baseline is consistent with random outcome assignment under the same
cohort+Linzer features.

Procedure:
  1. Compute observed gain = acc(MRP) - acc(baseline) on the BR core.
  2. Generate B = 1000 permuted outcome vectors (paired flip-preserving:
     each (winner, runner-up) pair keeps its complementary structure but
     gets randomly relabeled).
  3. For each permutation, recompute acc(MRP) and acc(baseline) on the
     permuted outcomes (predictions stay fixed - we only relabel y).
  4. Report two-sided p-value = fraction of permuted gains that are
     larger in absolute value than the observed gain.

Saves results to data/bench_permutation_test.json.
"""
from __future__ import annotations

import json
import math
import os
import random
import sys
from collections import defaultdict
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
N_PERM = 1000


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


def acc(probs, outcomes):
    n = len(probs)
    if n == 0:
        return 0.0
    return sum(1 for p, y in zip(probs, outcomes) if (p >= 0.5) == bool(y)) / n


def event_pair_key(event: dict) -> str:
    """Two paired rows (winner / runner-up) share an evento_id stem;
    distinguish the suffix '_w' (winner) vs '_l' (loser)."""
    eid = event.get("evento_id", "")
    if eid.endswith("_w"):
        return eid[:-2]
    if eid.endswith("_l"):
        return eid[:-2]
    return eid


def run() -> dict:
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

    all_events = []
    base_probs = []
    mrp_probs = []
    outcomes = []
    for y in test_years:
        rates = rates_by_year[y]
        for e in by_year[y]:
            all_events.append(e)
            base_probs.append(predict_baseline(e, rates))
            mrp_probs.append(predict_mrp(e, rates))
            outcomes.append(e["outcome"])

    n = len(outcomes)
    obs_acc_base = acc(base_probs, outcomes)
    obs_acc_mrp = acc(mrp_probs, outcomes)
    obs_gain = obs_acc_mrp - obs_acc_base

    # Build pair index: each pair key maps to (idx_w, idx_l)
    pairs = defaultdict(lambda: {"w": None, "l": None})
    for i, e in enumerate(all_events):
        key = event_pair_key(e)
        eid = e.get("evento_id", "")
        if eid.endswith("_w"):
            pairs[key]["w"] = i
        elif eid.endswith("_l"):
            pairs[key]["l"] = i
        else:
            # singleton (rare): treat as its own pair w/ no flip
            pairs[key]["w"] = i

    pair_keys = list(pairs.keys())

    rng = random.Random(SEED)
    perm_gains = []
    for _ in range(N_PERM):
        permuted = list(outcomes)
        for k in pair_keys:
            p = pairs[k]
            iw, il = p["w"], p["l"]
            if iw is None or il is None:
                continue
            # Coin flip per pair: keep or swap winner/loser labels
            if rng.random() < 0.5:
                permuted[iw], permuted[il] = permuted[il], permuted[iw]
        gain = acc(mrp_probs, permuted) - acc(base_probs, permuted)
        perm_gains.append(gain)

    n_more_extreme = sum(1 for g in perm_gains if abs(g) >= abs(obs_gain))
    p_value = (n_more_extreme + 1) / (N_PERM + 1)
    perm_mean = sum(perm_gains) / N_PERM
    perm_var = sum((g - perm_mean) ** 2 for g in perm_gains) / N_PERM
    perm_sd = perm_var ** 0.5
    z = (obs_gain - perm_mean) / perm_sd if perm_sd > 0 else float("nan")

    return {
        "config": {
            "stein_shrink": STEIN,
            "w_linzer": W_LINZER,
            "w_state": W_STATE,
            "sigma_int": SIGMA_INT,
            "sigma_slope": SIGMA_SLOPE,
            "n_perm": N_PERM,
            "seed": SEED,
        },
        "n_events": n,
        "n_pairs": sum(1 for k, p in pairs.items()
                       if p["w"] is not None and p["l"] is not None),
        "observed": {
            "acc_baseline": obs_acc_base,
            "acc_mrp": obs_acc_mrp,
            "gain": obs_gain,
        },
        "permutation_null": {
            "mean_gain": perm_mean,
            "sd_gain": perm_sd,
            "z_score": z,
            "p_value_two_sided": p_value,
            "n_more_extreme": n_more_extreme,
            "n_perm": N_PERM,
        },
    }


def main() -> None:
    payload = run()
    out = ROOT / "data" / "bench_permutation_test.json"
    out.write_text(json.dumps(payload, indent=2))
    print(f"saved -> {out}")
    o = payload["observed"]
    p = payload["permutation_null"]
    print()
    print(f"n events:     {payload['n_events']}")
    print(f"n pairs:      {payload['n_pairs']}")
    print(f"obs acc base: {o['acc_baseline']:.4f}")
    print(f"obs acc mrp:  {o['acc_mrp']:.4f}")
    print(f"obs gain:     {o['gain']:+.4f}")
    print()
    print(f"perm null mean gain: {p['mean_gain']:+.4f}")
    print(f"perm null sd gain:   {p['sd_gain']:.4f}")
    print(f"z-score:             {p['z_score']:.3f}")
    print(f"two-sided p-value:   {p['p_value_two_sided']:.4f}")
    print(f"({p['n_more_extreme']}/{p['n_perm']} permuted gains as extreme)")


if __name__ == "__main__":
    main()
