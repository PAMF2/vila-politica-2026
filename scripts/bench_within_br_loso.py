#!/usr/bin/env python3
"""Within-Brazil leave-one-state-out cross-validation.

Holds out each Brazilian UF's 2022 gubernatorial events one at a time,
refits cohort + state baseline on the remaining 25 UFs (plus all
federal and SP municipal training events from non-test years), and
evaluates accuracy + Brier on the held-out UF. Tests whether the
within-BR (uf, regime) prior generalizes spatially across the 26
non-SP states even when the UF cell is undefined for the held-out
state.

Saves results to data/bench_within_br_loso.json.
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


def linzer_p(lead_pp: float, days: int) -> float:
    sigma = SIGMA_INT + SIGMA_SLOPE * max(0, days)
    return 0.5 * (1.0 + math.erf(lead_pp / max(sigma, 1.0) / math.sqrt(2.0)))


def predict_blend(event: dict, rates: dict) -> tuple[float, bool]:
    """Returns (p_blend, used_state). used_state=False if (uf,regime) cell
    was undefined for this event (model collapses to no-MRP)."""
    lead = event.get("poll_lead_pp", 0.0)
    days = event.get("days_to", 30)
    p_lnz = linzer_p(lead, days)
    p_coh = predict_political(event, rates)["p_raw"]
    p_blend = (1 - W_LINZER) * p_coh + W_LINZER * p_lnz
    uf = event.get("uf", "BR")
    p_state = state_baseline_p(rates, uf, event["regime"])
    used_state = p_state is not None
    if used_state:
        p_blend = (1 - W_STATE) * p_blend + W_STATE * p_state
    return p_blend, used_state


def metrics(events: list[dict], probs: list[float]) -> dict:
    n = len(events)
    if n == 0:
        return {"n": 0, "acc": None, "brier": None}
    brier = sum((p - e["outcome"]) ** 2 for p, e in zip(probs, events)) / n
    hits = sum(1 for p, e in zip(probs, events)
               if (p >= 0.5) == bool(e["outcome"]))
    return {"n": n, "acc": hits / n, "brier": brier}


def run() -> dict:
    by_year = load_by_year()
    other = load_other_pool()

    events_2022_by_uf: dict[str, list[dict]] = defaultdict(list)
    for e in by_year.get(2022, []):
        uf = e.get("uf", "BR")
        if uf in {"BR", "SP"}:
            continue
        events_2022_by_uf[uf].append(e)

    ufs = sorted(events_2022_by_uf.keys())

    # Fixed training pool (everything except 2022 governor events) used for
    # both fixed-train cohort fit and the LOSO refit (LOSO drops ONE UF's
    # 2 events from the 2022-governor portion).
    train_other = list(other)
    for y, evs in by_year.items():
        if y == 2022:
            continue
        train_other.extend(evs)
    # All 2022 events except governor (just the federal events from 2022).
    train_2022_non_gov = [e for e in by_year.get(2022, [])
                          if e.get("uf", "BR") in {"BR", "SP"}]

    # Baseline: train on everything (no UF held out from 2022 governor pool),
    # evaluate on each UF separately for reference.
    rates_full = fit_cohorts_political(
        train_other + train_2022_non_gov +
        sum(events_2022_by_uf.values(), []),
        stein_shrink=STEIN,
    )

    per_uf = {}
    loso_total_n = 0
    loso_total_hits = 0
    loso_total_brier = 0.0
    full_total_n = 0
    full_total_hits = 0
    full_total_brier = 0.0
    state_used_count = 0
    state_undefined_count = 0

    for uf in ufs:
        # LOSO: drop this UF's 2022 governor events from training.
        train_loso = list(train_other) + list(train_2022_non_gov)
        for u2 in ufs:
            if u2 != uf:
                train_loso.extend(events_2022_by_uf[u2])
        rates_loso = fit_cohorts_political(train_loso, stein_shrink=STEIN)

        test_events = events_2022_by_uf[uf]
        probs_loso = []
        used_state_loso = []
        for e in test_events:
            p, used = predict_blend(e, rates_loso)
            probs_loso.append(p)
            used_state_loso.append(used)
        m_loso = metrics(test_events, probs_loso)

        probs_full = [predict_blend(e, rates_full)[0] for e in test_events]
        m_full = metrics(test_events, probs_full)

        per_uf[uf] = {
            "n": len(test_events),
            "loso": m_loso,
            "full": m_full,
            "state_baseline_used_loso": sum(used_state_loso),
        }
        loso_total_n += m_loso["n"]
        loso_total_hits += m_loso["acc"] * m_loso["n"]
        loso_total_brier += m_loso["brier"] * m_loso["n"]
        full_total_n += m_full["n"]
        full_total_hits += m_full["acc"] * m_full["n"]
        full_total_brier += m_full["brier"] * m_full["n"]
        state_used_count += sum(used_state_loso)
        state_undefined_count += len(used_state_loso) - sum(used_state_loso)

    summary = {
        "config": {
            "stein_shrink": STEIN,
            "w_linzer": W_LINZER,
            "w_state": W_STATE,
            "sigma_int": SIGMA_INT,
            "sigma_slope": SIGMA_SLOPE,
            "seed": SEED,
        },
        "ufs": ufs,
        "per_uf": per_uf,
        "totals": {
            "n": loso_total_n,
            "loso": {
                "acc": loso_total_hits / loso_total_n,
                "brier": loso_total_brier / loso_total_n,
            },
            "full_train": {
                "acc": full_total_hits / full_total_n,
                "brier": full_total_brier / full_total_n,
            },
            "state_baseline_used": state_used_count,
            "state_baseline_undefined_loso": state_undefined_count,
        },
    }
    return summary


def main() -> None:
    payload = run()
    out = ROOT / "data" / "bench_within_br_loso.json"
    out.write_text(json.dumps(payload, indent=2))
    print(f"saved -> {out}")
    t = payload["totals"]
    print()
    print(f"n events (26 UFs x 2 paired):  {t['n']}")
    print(f"LOSO     (held-out UF dropped): "
          f"acc={t['loso']['acc']:.4f}  brier={t['loso']['brier']:.4f}")
    print(f"Full-tr  (no UF held out):     "
          f"acc={t['full_train']['acc']:.4f}  brier={t['full_train']['brier']:.4f}")
    print(f"State baseline available LOSO: {t['state_baseline_used']}/{t['n']}")
    print(f"  ({t['state_baseline_undefined_loso']} events fall back to no-MRP "
          f"because the UF cell is undefined when the UF is held out)")


if __name__ == "__main__":
    main()
