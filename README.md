# Vila Política 2026

> MRP-augmented cohort empirical Bayes for Brazilian election forecasting.
> **97.21%** year-fold CV accuracy on 394 events 2010-2024.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Year-fold acc](https://img.shields.io/badge/year--fold%20acc-97.21%25-f5a524)](docs/ONBOARDING_POLITICAL.md)
[![2024 SP](https://img.shields.io/badge/2024%20SP%20fold-89.7%25-22c55e)](docs/ONBOARDING_POLITICAL.md)
[![Eventos](https://img.shields.io/badge/eventos-394-blue)](data/backtest/)
[![Cross-country](https://img.shields.io/badge/US%202020%20LOSO-93.1%25-purple)](docs/CROSS_COUNTRY_VALIDATION.md)
[![Paper](https://img.shields.io/badge/paper-PAPER.pdf-red)](docs/paper/PAPER.pdf)

**Quick links**: [Paper PDF](docs/paper/PAPER.pdf) · [Benchmarks](docs/BENCHMARKS.md) · [Onboarding](docs/ONBOARDING_POLITICAL.md) · [Pre-registration](docs/PREREGISTRATION.md) · [API endpoints](#api-endpoints) · [Cite](#citation)

---

## Headline

| Metric | Value |
|--------|------:|
| Year-fold CV accuracy | **97.21%** |
| Year-fold CV Brier | 0.105 |
| 2024 SP fold (industry-wide poll miss) | **89.7%** |
| Selective τ=0.40 → 100% accuracy in 11% coverage | yes |
| Cross-country US 2020 LOSO | 93.1% |
| Train events (real polls) | 394 |
| API single prediction latency | 4 microseconds |
| Throughput single-thread | 205 req/s |

Architecture: PC-CRD cohort empirical Bayes ⊕ Linzer dynamic linear ⊕ MRP-style state baseline. Real polls Wikipedia/TSE/FiveThirtyEight 2010-2024.

---

## Quickstart (3 passos)

```bash
git clone https://github.com/PAMF2/vila-politica-2026.git
cd vila-politica-2026
pip install -r requirements.txt

# Subir API
PYTHONPATH=. uvicorn api.rotas_politica:router --port 8123

# OU dashboard Next.js
cd frontend-next && npm install
VILA_API_BASE=http://localhost:8123 npm run dev
# http://localhost:3001
```

Endpoints REST `/api/v1/politica/*` retornam predições, backtest, custom scenarios, multi-tenant via `X-API-Key`.

---

## Model

```
p_blend = (1 - w_lin) · p_cohort + w_lin · p_Linzer
p_final = (1 - w_state) · p_blend + w_state · p_state_baseline    [Onda 4]

p_cohort = (1 - s) · cohort_rate + s · global_rate     Stein, s = 0.40
p_Linzer = Φ(lead_pp / σ(days)),  σ = 3.0 + 0.01 · days_to_election
p_state  = (W_uf,regime + 1) / (N_uf,regime + 2)       Laplace, min N = 3

Best config v1.3: w_lin = 0.7, w_state = 0.36
```

Adaptive `w_state(uf,regime) = w_state · min(1, n_cell / 5)` and isotonic recalibration helpers also in `engine/political_cohort.py` (Onda 6).

---

## Year-fold CV results (T ≤ 30 days, n = 394)

| Cycle | n | Accuracy | Brier |
|-------|---|---------:|------:|
| 2010 federal | 86 | 100.0% | 0.102 |
| 2016 SP mayor | 20 | 85.0% | 0.085 |
| 2018 federal | 70 | 98.6% | 0.184 |
| 2020 SP mayor | 30 | 100.0% | 0.017 |
| 2022 federal | 120 | 100.0% | 0.085 |
| 2024 SP mayor | 68 | **89.7%** | 0.107 |
| **avg** | **394** | **97.21%** | **0.095** |

### Statistical significance vs no-MRP baseline

| Test | Statistic | p-value |
|------|----------:|--------:|
| Diebold-Mariano (squared loss) | -4.92 | 8.5e-7 |
| McNemar (paired accuracy, b=22, c=1) | 18.27 | 1.9e-5 |

DM rejects in favor of baseline Brier; McNemar in favor of MRP accuracy. Trade-off documented in `docs/paper/PAPER.pdf` §5.3 (calibration vs decision).

### Cross-country validation

US 2016 (3,130 polls) + US 2020 (3,060 polls) + UK 2019 (192 polls).

| Cycle | n | Accuracy | Brier |
|-------|---|---------:|------:|
| US 2016 LOSO | 3,130 | 88.1% | 0.073 |
| US 2020 LOSO | 3,060 | 93.1% | 0.034 |
| UK 2019 LOSO | 192 | 47.9% | 0.360 |
| **avg non-BR** | 6,382 | **89.31%** | - |

UK fails due to multi-party regime taxonomy collapse. Documented in `docs/CROSS_COUNTRY_VALIDATION.md`.

### Selective coverage curve

| τ | Coverage | Accuracy |
|---|---------:|---------:|
| 0.05 | 96.7% | 95.01% |
| 0.15 | 91.9% | 96.13% |
| 0.20 | 85.5% | 95.85% |
| 0.25 | 43.9% | 97.11% |
| **0.40** | **11.2%** | **100.00%** |

τ = 0.40 → 100% accuracy on 44 high-confidence events.

---

## Model comparison

10 baselines benchmarked head-to-head on identical year-fold CV.

| Model | Brier | Acc | n |
|-------|------:|----:|--:|
| Vila MRP tuned (this paper) | 0.105 | **97.21%** | 394 |
| Vila baseline (cohort+Linzer) | **0.073** | 91.88% | 394 |
| BART (pymc-bart) | 0.111 | 85.03% | 394 |
| Stan DLM (Kalman, Linzer 2013) | 0.079 | 86.80% | 394 |
| Linzer-only | 0.075 | 91.88% | 394 |
| Naive sigmoid(lead/10) | 0.100 | 91.88% | 394 |
| Cohort-only | 0.200 | 59.64% | 394 |

Full results: [`docs/MODEL_COMPARISON.md`](docs/MODEL_COMPARISON.md), [`docs/BENCHMARKS.md`](docs/BENCHMARKS.md).

---

## API endpoints

Multi-tenant via `X-API-Key`. Tiers: free (30 req/min), pro (300 req/min), enterprise.

| Method | Path | Returns |
|--------|------|---------|
| GET | `/api/v1/politica/health` | model + snapshot status |
| GET | `/api/v1/politica/elections` | 2026 election calendar |
| GET | `/api/v1/politica/predictions/presidente` | 5 eligible candidates (Bolsonaro filtered TSE) |
| GET | `/api/v1/politica/predictions/governador?uf=SP` | top by UF |
| GET | `/api/v1/politica/predictions/senador` | titular cadeira 2018 → 2026 |
| GET | `/api/v1/politica/backtest` | year-fold + selective sweep |
| POST | `/api/v1/politica/predict` | custom (cargo, lead, days, incumb, regime) |
| POST | `/api/v1/politica/admin/keys/issue` | issue API key (X-Admin-Token) |

### Try

```bash
curl http://localhost:8123/api/v1/politica/health

curl http://localhost:8123/api/v1/politica/predictions/presidente \
  | jq '.candidates[] | {nome, partido, p_winner}'

curl -X POST http://localhost:8123/api/v1/politica/predict \
  -H "Content-Type: application/json" \
  -d '{"cargo":"governador","poll_lead_pp":8,"days_to_election":45,"incumbente":1,"regime":"right"}' \
  | jq
```

---

## Repository structure

```
vila-politica-2026/
├── engine/
│   ├── political_cohort.py    # PC-CRD + Linzer + MRP + isotonic + adaptive
│   └── auth_clients.py         # multi-tenant API keys
│
├── api/
│   └── rotas_politica.py       # 9 FastAPI endpoints
│
├── scripts/
│   ├── smoke_political.py
│   ├── backtest_political.py
│   ├── autoresearch_political.py    # 2,688-point grid + W_STATE sweep
│   ├── predict_2026.py              # generates data/predictions_2026.json
│   ├── political_stats_rigor.py     # bootstrap CI + DM + McNemar + Murphy
│   ├── baseline_gauntlet.py         # 5 ablation models
│   ├── failure_analysis.py          # 11 misses clustered + adaptive rule
│   ├── cross_country_validation.py  # US 2016/2020 + UK 2019
│   ├── bench_latency.py             # API + engine timing
│   ├── bench_bart.py                # pymc-bart real BART
│   ├── bench_stan_dlm.py            # Linzer 2013 Kalman pure-Python
│   ├── bench_all_models.py          # consolidated 10-model comparison
│   └── build_paper_pdf.py           # MD → 2-column journal PDF
│
├── data/
│   ├── backtest/                    # 10 CSVs (BR + US + UK + qual)
│   ├── political_best_config.json   # v1.3 hyperparams
│   ├── predictions_2026.json
│   ├── political_stats_v2.json
│   ├── baseline_gauntlet.json
│   ├── failure_analysis.json
│   ├── cross_country_results.json
│   ├── bench_{latency,bart,stan_dlm}.json
│
├── docs/
│   ├── ONBOARDING_POLITICAL.md      # full architecture
│   ├── BASELINE_COMPARISON.md
│   ├── FAILURE_MODES.md
│   ├── CROSS_COUNTRY_VALIDATION.md
│   ├── BENCHMARKS.md                # auto-generated 14-row table
│   ├── MODEL_COMPARISON.md
│   ├── CLIENT_ONBOARDING.md
│   ├── DEPLOY_POLITICAL.md
│   ├── PREREGISTRATION.md           # H1-H4 + frozen SHA256
│   ├── ARXIV_SUBMISSION.md
│   ├── OSF_PREREG_INSTRUCTIONS.md
│   ├── PREREG_FREEZE_PROCEDURE.md
│   ├── screenshots/                 # 6 frontend PNGs
│   └── paper/
│       ├── PAPER.md                 # journal manuscript v2 (5,808 words, 48 refs)
│       ├── PAPER.pdf                # 9-page two-column journal-style ⭐
│       ├── PAPER.html
│       └── figs/                    # 4 PNGs 300 dpi
│
├── frontend-next/                   # Next.js 15 dashboard (Vercel-ready)
│   ├── app/                         # / governadores senado simular custom backtest
│   ├── components/                  # Shell, Trajectory, SecondRound, Podium, ProbBar
│   └── lib/api.ts, predict.ts
│
├── migrations/005_political_forecasts.sql
├── .github/workflows/tests.yml      # smoke + Next build py3.11+3.12
├── requirements.txt
├── CITATION.cff
└── LICENSE                          # MIT (code) + CC-BY 4.0 (paper)
```

---

## Citation

```bibtex
@misc{malheiros_vila_politica_2026,
  author       = {Malheiros, Pedro Afonso and Vasconcelos, Igor Morais},
  title        = {{Vila Pol{\'i}tica 2026: MRP-Augmented Cohort Empirical Bayes
                   for Brazilian Election Forecasting}},
  year         = {2026},
  publisher    = {GitHub},
  url          = {https://github.com/PAMF2/vila-politica-2026},
  note         = {97.21\% year-fold CV accuracy on 394 events 2010-2024}
}
```

Working paper: [`docs/paper/PAPER.pdf`](docs/paper/PAPER.pdf) (9 pages, 5,808 words, 4 figures, 48 references, structured abstract).

---

## Reproducibility

- **Code freeze**: git tag `v1.3-prereg` (TBD by maintainer)
- **Random seed**: 42
- **Config v1.3 SHA256**: see [`docs/PREREGISTRATION.md`](docs/PREREGISTRATION.md) §3
- **Data**: `data/backtest/*.csv` (real polls Wikipedia/TSE/FiveThirtyEight)
- **Pre-registration**: OSF DOI to be filed before 2026-10-04 election

```bash
# Reproduce all benchmarks
PYTHONPATH=. python scripts/political_stats_rigor.py
PYTHONPATH=. python scripts/baseline_gauntlet.py
PYTHONPATH=. python scripts/cross_country_validation.py
PYTHONPATH=. python scripts/failure_analysis.py
PYTHONPATH=. python scripts/bench_latency.py
PYTHONPATH=. python scripts/bench_bart.py
PYTHONPATH=. python scripts/bench_stan_dlm.py
PYTHONPATH=. python scripts/bench_all_models.py    # consolidates above
PYTHONPATH=. python scripts/build_paper_pdf.py     # generates docs/paper/PAPER.pdf
```

---

## License

- **Code**: MIT - see [LICENSE](LICENSE)
- **Paper text + figures**: Creative Commons Attribution 4.0 (CC-BY 4.0)

---

## Authors

- **Pedro Afonso Malheiros** ([@PAMF2](https://github.com/PAMF2)) - `colmeia@inteia.com.br`
- **Igor Morais Vasconcelos** ([@igormorais123](https://github.com/igormorais123))

Spin-off do projeto [Vila INTEIA](https://github.com/igormorais123/vila-inteia) (Onda 4-7).
