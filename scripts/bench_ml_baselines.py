#!/usr/bin/env python3
"""ML baselines: 5 classical / off-the-shelf classifiers on the same year-fold
CV the rest of the gauntlet uses. Honest comparison vs Vila MRP / BART / Stan
DLM ensemble.

Models:
  L1 LogisticRegression (sklearn)
  L2 RandomForest (sklearn, n_estimators=200)
  L3 XGBoost (xgboost; falls back HONESTLY to sklearn GradientBoostingClassifier
       labelled 'XGB proxy' if xgboost not installed)
  L4 MLP (sklearn, hidden=(32,16))
  L5 GaussianNB (sklearn)

Protocol (mirrors scripts/bench_bart.py):
  - Year-fold CV: hold out one cycle, train on every other cycle + non-political
    'other_pool' qualitative events with binary outcome. Test year never in
    train (leak-safe).
  - T<=30 day filter from autoresearch_political.load_by_year().
  - Features: poll_lead_pp, days_to, incumbente, regime (one-hot 5 cols), uf
    (one-hot, full vocab from train+test).
  - Continuous features standardized via StandardScaler fit on train only.
  - Seed=42 throughout.

Output: data/bench_ml_baselines.json with per-cycle brier/acc/log_loss +
weighted pooled avg + fit_time + predict_time_ms_per_event.
"""
from __future__ import annotations
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.autoresearch_political import (  # type: ignore  # noqa: E402
    load_by_year,
    load_other_pool,
)

SEED = 42
np.random.seed(SEED)

OUT_PATH = ROOT / "data" / "bench_ml_baselines.json"

# Regime vocabulary covers every value seen across the dataset. We pull from
# data at runtime to be safe, but seed with a known superset so the vector
# has a stable width even in folds that miss a regime.
REGIMES_DEFAULT = ["left", "center", "right", "centro", "centro-esquerda"]


def detect_xgboost():
    """Return (backend_name, module_or_None, note)."""
    try:
        import xgboost as xgb  # noqa: F401
        return "xgboost", xgb, f"xgboost {xgb.__version__} available"
    except Exception as exc:
        return "xgb_proxy", None, (
            f"xgboost unavailable ({type(exc).__name__}: {exc}); using sklearn "
            "GradientBoostingClassifier as honest XGB proxy"
        )


# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------

def _build_vocabs(events) -> tuple[list[str], list[str]]:
    regimes = sorted({(e.get("regime") or "center") for e in events}
                     | set(REGIMES_DEFAULT))
    ufs = sorted({e.get("uf", "BR") for e in events})
    return regimes, ufs


def event_to_features(events, regimes, ufs) -> np.ndarray:
    rows = []
    for e in events:
        lead = float(e.get("poll_lead_pp", 0.0))
        days = float(e.get("days_to", 30))
        inc = float(e.get("incumbente", 0))
        reg = e.get("regime") or "center"
        reg_oh = [1.0 if reg == r else 0.0 for r in regimes]
        uf = e.get("uf", "BR")
        uf_oh = [1.0 if uf == u else 0.0 for u in ufs]
        rows.append([lead, days, inc, *reg_oh, *uf_oh])
    return np.asarray(rows, dtype=float)


def feature_names(regimes, ufs) -> list[str]:
    return ["poll_lead_pp", "days_to", "incumbente",
            *[f"regime_{r}" for r in regimes],
            *[f"uf_{u}" for u in ufs]]


# ---------------------------------------------------------------------------
# Model factories
# ---------------------------------------------------------------------------

def make_logistic():
    from sklearn.linear_model import LogisticRegression
    return LogisticRegression(
        max_iter=5000,
        random_state=SEED,
        solver="lbfgs",
        C=1.0,
    )


def make_random_forest():
    from sklearn.ensemble import RandomForestClassifier
    return RandomForestClassifier(
        n_estimators=200,
        random_state=SEED,
        n_jobs=1,
    )


def make_xgboost(xgb_mod):
    return xgb_mod.XGBClassifier(
        n_estimators=200,
        random_state=SEED,
        eval_metric="logloss",
        tree_method="hist",
        n_jobs=1,
        verbosity=0,
    )


def make_xgb_proxy():
    from sklearn.ensemble import GradientBoostingClassifier
    return GradientBoostingClassifier(
        n_estimators=200,
        random_state=SEED,
        learning_rate=0.05,
        max_depth=3,
    )


def make_mlp():
    from sklearn.neural_network import MLPClassifier
    return MLPClassifier(
        hidden_layer_sizes=(32, 16),
        random_state=SEED,
        max_iter=2000,
        early_stopping=False,
    )


def make_naive_bayes():
    from sklearn.naive_bayes import GaussianNB
    return GaussianNB()


# ---------------------------------------------------------------------------
# Eval
# ---------------------------------------------------------------------------

def eval_metrics(y_true, p):
    y = np.asarray(y_true, dtype=int)
    p = np.asarray(p, dtype=float)
    n = len(y)
    if n == 0:
        return {"n": 0, "brier": 0.0, "acc": 0.0, "log_loss": 0.0}
    p_clip = np.clip(p, 1e-9, 1 - 1e-9)
    brier = float(np.mean((p_clip - y) ** 2))
    acc = float(np.mean((p_clip >= 0.5).astype(int) == y))
    log_loss = float(np.mean(-(y * np.log(p_clip) + (1 - y) * np.log(1 - p_clip))))
    return {"n": n, "brier": brier, "acc": acc, "log_loss": log_loss}


# ---------------------------------------------------------------------------
# Per-fold runner
# ---------------------------------------------------------------------------

def fit_predict(model_id, builder, X_tr, y_tr, X_te):
    """Fit a fresh model, time fit, time predict_proba, return (p, fit_s,
    predict_ms_per_event)."""
    clf = builder()
    t0 = time.time()
    clf.fit(X_tr, y_tr)
    t_fit = time.time() - t0
    t1 = time.time()
    p = clf.predict_proba(X_te)
    t_pred_ms_per = (time.time() - t1) * 1000.0 / max(len(X_te), 1)
    # GaussianNB / RF / etc. all return shape (n, 2). XGB too.
    if p.ndim == 2 and p.shape[1] >= 2:
        p1 = p[:, 1]
    else:
        p1 = np.asarray(p).ravel()
    p1 = np.clip(p1, 1e-4, 1 - 1e-4)
    return p1, t_fit, t_pred_ms_per


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"[bench_ml] seed={SEED}")
    backend, xgb_mod, note = detect_xgboost()
    print(f"[bench_ml] xgboost backend={backend} ({note})")

    by_year = load_by_year()
    other = load_other_pool()
    years = sorted(by_year.keys())
    print(f"[bench_ml] years={years}  n_per_year=" +
          str({y: len(by_year[y]) for y in years}))
    print(f"[bench_ml] other_pool={len(other)}")

    all_events = list(other) + [e for y in years for e in by_year[y]]
    regimes, ufs = _build_vocabs(all_events)
    feat_names = feature_names(regimes, ufs)
    print(f"[bench_ml] features={len(feat_names)}  regimes={regimes}  ufs={ufs}")

    other_with_y = [e for e in other if "outcome" in e and e["outcome"] in (0, 1)]
    print(f"[bench_ml] other_with_outcome={len(other_with_y)}")

    # Continuous columns are the first three: poll_lead_pp, days_to, incumbente.
    # We standardize lead+days; leave incumbente alone (binary).
    from sklearn.preprocessing import StandardScaler

    # Model registry. XGB swapped for GBM proxy when xgboost missing.
    if backend == "xgboost":
        def build_xgb():
            return make_xgboost(xgb_mod)
        models = {
            "L1_logreg":      ("LogReg",        make_logistic),
            "L2_random_forest": ("RandomForest", make_random_forest),
            "L3_xgboost":     ("XGBoost",       build_xgb),
            "L4_mlp":         ("MLP_32_16",     make_mlp),
            "L5_naive_bayes": ("GaussianNB",    make_naive_bayes),
        }
    else:
        models = {
            "L1_logreg":      ("LogReg",        make_logistic),
            "L2_random_forest": ("RandomForest", make_random_forest),
            "L3_xgboost":     ("XGB proxy (GBM)", make_xgb_proxy),
            "L4_mlp":         ("MLP_32_16",     make_mlp),
            "L5_naive_bayes": ("GaussianNB",    make_naive_bayes),
        }

    results: dict = {mid: {"per_year": {}, "fit_times": [], "pred_times": []}
                     for mid in models}

    # We fit a FRESH StandardScaler per fold, on training rows only.
    for y in years:
        train_events = list(other_with_y)
        for y2 in years:
            if y2 != y:
                train_events.extend(by_year[y2])
        test_events = by_year[y]

        X_tr = event_to_features(train_events, regimes, ufs)
        y_tr = np.asarray([int(e["outcome"]) for e in train_events], dtype=int)
        X_te = event_to_features(test_events, regimes, ufs)
        y_te = np.asarray([int(e["outcome"]) for e in test_events], dtype=int)

        # Standardize first two columns (lead, days). Leave the rest untouched.
        scaler = StandardScaler()
        cont_idx = [0, 1]
        X_tr_scaled = X_tr.copy()
        X_te_scaled = X_te.copy()
        scaler.fit(X_tr[:, cont_idx])
        X_tr_scaled[:, cont_idx] = scaler.transform(X_tr[:, cont_idx])
        X_te_scaled[:, cont_idx] = scaler.transform(X_te[:, cont_idx])

        print(f"[bench_ml] fold y={y}  train={X_tr_scaled.shape}  test={X_te_scaled.shape}  "
              f"pos_rate_tr={y_tr.mean():.3f}  pos_rate_te={y_te.mean():.3f}")

        for mid, (label, builder) in models.items():
            try:
                p, t_fit, t_pred = fit_predict(mid, builder, X_tr_scaled, y_tr, X_te_scaled)
                m = eval_metrics(y_te, p)
            except Exception as exc:
                print(f"[bench_ml]   {mid} FAILED on fold y={y}: {exc!r}")
                m = {"n": int(len(y_te)), "brier": None, "acc": None,
                     "log_loss": None, "error": repr(exc)}
                t_fit = 0.0
                t_pred = 0.0
            m["fit_time_s"] = round(t_fit, 4)
            m["predict_time_ms_per_event"] = round(t_pred, 4)
            results[mid]["per_year"][y] = m
            results[mid]["fit_times"].append(t_fit)
            results[mid]["pred_times"].append(t_pred)
            if m.get("brier") is not None:
                print(f"[bench_ml]   {mid:<18} {label:<18} "
                      f"brier={m['brier']:.4f} acc={m['acc']:.4f} "
                      f"ll={m['log_loss']:.4f} fit={m['fit_time_s']}s "
                      f"pred={m['predict_time_ms_per_event']}ms/ev")

    # Pool weighted by n.
    summary: dict = {}
    for mid in models:
        per_year = results[mid]["per_year"]
        n_total = sum(per_year[y]["n"] for y in years)
        def wmean(field):
            num = 0.0
            den = 0
            for y in years:
                v = per_year[y].get(field)
                if v is None:
                    continue
                num += v * per_year[y]["n"]
                den += per_year[y]["n"]
            return num / den if den > 0 else None
        summary[mid] = {
            "label": models[mid][0],
            "n": n_total,
            "brier_avg": (round(wmean("brier"), 6) if wmean("brier") is not None else None),
            "acc_avg":   (round(wmean("acc"), 6)   if wmean("acc")   is not None else None),
            "log_loss_avg": (round(wmean("log_loss"), 6) if wmean("log_loss") is not None else None),
            "fit_time_s_total": round(sum(results[mid]["fit_times"]), 4),
            "predict_time_ms_per_event_avg": round(
                float(np.mean(results[mid]["pred_times"])) if results[mid]["pred_times"] else 0.0,
                4,
            ),
        }

    out = {
        "model_family": "ML baselines (sklearn / xgboost)",
        "backend_xgboost": backend,
        "backend_note": note,
        "honest_proxy": backend == "xgb_proxy",
        "honest_note": (
            note if backend == "xgb_proxy"
            else "xgboost installed; XGBClassifier used directly (no proxy)."
        ),
        "seed": SEED,
        "features": feat_names,
        "n_features": len(feat_names),
        "regimes": regimes,
        "ufs": ufs,
        "years": years,
        "n_per_cycle": {y: len(by_year[y]) for y in years},
        "models": {
            mid: {
                "label": models[mid][0],
                "per_year": {
                    y: {
                        k: v for k, v in results[mid]["per_year"][y].items()
                    }
                    for y in years
                },
                "summary": summary[mid],
            }
            for mid in models
        },
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, indent=2))
    print(f"[bench_ml] wrote {OUT_PATH}")

    # Console summary
    print("\n=== POOLED RESULTS (weighted by n per cycle) ===")
    print(f"{'Model':<22} {'Label':<20} {'n':>4} {'Brier':>8} {'Acc':>8} "
          f"{'LogLoss':>8} {'Fit(s)':>8} {'Pred(ms)':>9}")
    for mid in models:
        s = summary[mid]
        b = f"{s['brier_avg']:.4f}" if s['brier_avg'] is not None else "  -  "
        a = f"{s['acc_avg']:.4f}"   if s['acc_avg']   is not None else "  -  "
        l = f"{s['log_loss_avg']:.4f}" if s['log_loss_avg'] is not None else "  -  "
        print(f"{mid:<22} {s['label']:<20} {s['n']:>4} "
              f"{b:>8} {a:>8} {l:>8} "
              f"{s['fit_time_s_total']:>8.2f} {s['predict_time_ms_per_event_avg']:>9.4f}")


if __name__ == "__main__":
    main()
