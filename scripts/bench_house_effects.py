#!/usr/bin/env python3
"""Per-institute house effects on the 2024 SP fold.

For each polling firm appearing in the BR core dataset, computes:
  (1) the mean signed bias (predicted_p - outcome) on the v1.3 ensemble,
  (2) the mean signed bias on the cohort+Linzer no-MRP baseline,
  (3) the bias reduction from MRP,
  (4) the count of polls per institute.

Identifies which institutes systematically favored Boulos in 2024 SP and
quantifies how much the state baseline absorbs that bias per pollster.

Saves results to data/bench_house_effects.json.
"""
from __future__ import annotations

import json
import math
import os
import random
import re
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

# Map raw evento_id pollster string to canonical institute name
INSTITUTES = [
    ("AtlasIntel",      ["AtlasIntel", "Atlas"]),
    ("Datafolha",       ["Datafolha"]),
    ("Quaest",          ["Quaest", "GenialQuaest"]),
    ("Ipec",            ["Ipec", "IBOPE", "Ibope"]),
    ("Paraná Pesquisas", ["ParanaPesquisas", "Parana"]),
    ("RealTimeBigData", ["RealTimeBigData", "RTBD"]),
    ("Instituto Verita", ["InstitutoVerit", "Verita"]),
    ("Vox Populi",      ["VoxPopuli", "Vox"]),
    ("CNT/MDA",         ["CNT", "MDA"]),
    ("Other",           []),
]


def linzer_p(lead_pp: float, days: int) -> float:
    sigma = SIGMA_INT + SIGMA_SLOPE * max(0, days)
    return 0.5 * (1.0 + math.erf(lead_pp / max(sigma, 1.0) / math.sqrt(2.0)))


def predict_baseline(event: dict, rates: dict) -> float:
    """Cohort + Linzer (no state baseline)."""
    lead = event.get("poll_lead_pp", 0.0)
    days = event.get("days_to", 30)
    p_lnz = linzer_p(lead, days)
    p_coh = predict_political(event, rates)["p_raw"]
    return (1 - W_LINZER) * p_coh + W_LINZER * p_lnz


def predict_mrp(event: dict, rates: dict) -> float:
    """Full v1.3 ensemble with state baseline."""
    p = predict_baseline(event, rates)
    uf = event.get("uf", "BR")
    p_state = state_baseline_p(rates, uf, event["regime"])
    if p_state is not None:
        p = (1 - W_STATE) * p + W_STATE * p_state
    return p


def institute_of(evento_id: str) -> str:
    s = evento_id or ""
    for canonical, aliases in INSTITUTES:
        if canonical == "Other":
            continue
        for alias in aliases:
            if alias.lower() in s.lower():
                return canonical
    return "Other"


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

    by_inst: dict[str, list[dict]] = defaultdict(list)
    for y, events in by_year.items():
        rates = rates_by_year[y]
        for e in events:
            inst = institute_of(e.get("evento_id", ""))
            p_base = predict_baseline(e, rates)
            p_mrp = predict_mrp(e, rates)
            y_obs = e["outcome"]
            row = {
                "year": y,
                "uf": e.get("uf", "BR"),
                "regime": e.get("regime"),
                "lead_pp": e.get("poll_lead_pp", 0.0),
                "outcome": y_obs,
                "p_baseline": p_base,
                "p_mrp": p_mrp,
                "bias_baseline": p_base - y_obs,
                "bias_mrp": p_mrp - y_obs,
                "loss_baseline": (p_base - y_obs) ** 2,
                "loss_mrp": (p_mrp - y_obs) ** 2,
                "correct_baseline": (p_base >= 0.5) == bool(y_obs),
                "correct_mrp": (p_mrp >= 0.5) == bool(y_obs),
            }
            by_inst[inst].append(row)

    summary = {}
    for inst, rows in sorted(by_inst.items(), key=lambda kv: -len(kv[1])):
        n = len(rows)
        n2024_sp = sum(1 for r in rows if r["year"] == 2024 and r["uf"] == "SP")
        mean_bias_b = sum(r["bias_baseline"] for r in rows) / n
        mean_bias_m = sum(r["bias_mrp"] for r in rows) / n
        brier_b = sum(r["loss_baseline"] for r in rows) / n
        brier_m = sum(r["loss_mrp"] for r in rows) / n
        acc_b = sum(r["correct_baseline"] for r in rows) / n
        acc_m = sum(r["correct_mrp"] for r in rows) / n
        # 2024 SP slice
        rows_sp = [r for r in rows if r["year"] == 2024 and r["uf"] == "SP"]
        if rows_sp:
            n_sp = len(rows_sp)
            bias_b_sp = sum(r["bias_baseline"] for r in rows_sp) / n_sp
            bias_m_sp = sum(r["bias_mrp"] for r in rows_sp) / n_sp
            acc_b_sp = sum(r["correct_baseline"] for r in rows_sp) / n_sp
            acc_m_sp = sum(r["correct_mrp"] for r in rows_sp) / n_sp
        else:
            n_sp = bias_b_sp = bias_m_sp = acc_b_sp = acc_m_sp = None
        summary[inst] = {
            "n_total": n,
            "n_2024_sp": n2024_sp,
            "all_data": {
                "mean_bias_baseline": mean_bias_b,
                "mean_bias_mrp": mean_bias_m,
                "bias_reduction": abs(mean_bias_b) - abs(mean_bias_m),
                "brier_baseline": brier_b,
                "brier_mrp": brier_m,
                "acc_baseline": acc_b,
                "acc_mrp": acc_m,
            },
            "sp_2024_slice": {
                "n": n_sp,
                "mean_bias_baseline": bias_b_sp,
                "mean_bias_mrp": bias_m_sp,
                "acc_baseline": acc_b_sp,
                "acc_mrp": acc_m_sp,
            },
        }

    return {
        "config": {
            "stein_shrink": STEIN,
            "w_linzer": W_LINZER,
            "w_state": W_STATE,
            "sigma_int": SIGMA_INT,
            "sigma_slope": SIGMA_SLOPE,
            "seed": SEED,
        },
        "per_institute": summary,
    }


def main() -> None:
    payload = run()
    out = ROOT / "data" / "bench_house_effects.json"
    out.write_text(json.dumps(payload, indent=2))
    print(f"saved -> {out}")
    print()
    print(f"{'Institute':<22} {'n':>4} {'n_SP24':>7} "
          f"{'bias_base':>10} {'bias_mrp':>10} "
          f"{'acc_base':>9} {'acc_mrp':>9}")
    print("-" * 80)
    for inst, s in payload["per_institute"].items():
        a = s["all_data"]
        print(f"{inst:<22} {s['n_total']:>4} {s['n_2024_sp']:>7} "
              f"{a['mean_bias_baseline']:>+10.4f} {a['mean_bias_mrp']:>+10.4f} "
              f"{a['acc_baseline']:>9.4f} {a['acc_mrp']:>9.4f}")
    print()
    print("2024 SP slice (where polls were systematically wrong):")
    print(f"{'Institute':<22} {'n':>4} {'bias_b_SP':>11} {'bias_m_SP':>11} "
          f"{'acc_b_SP':>9} {'acc_m_SP':>9}")
    print("-" * 80)
    for inst, s in payload["per_institute"].items():
        sp = s["sp_2024_slice"]
        if sp["n"] is None:
            continue
        print(f"{inst:<22} {sp['n']:>4} "
              f"{sp['mean_bias_baseline']:>+11.4f} {sp['mean_bias_mrp']:>+11.4f} "
              f"{sp['acc_baseline']:>9.4f} {sp['acc_mrp']:>9.4f}")


if __name__ == "__main__":
    main()
