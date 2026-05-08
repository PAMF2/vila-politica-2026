# Vila Política 2026

> Sistema de predição eleitoral multi-tenant para Brasil 2026 baseado em PC-CRD cohort empirical Bayes + Linzer dynamic linear + MRP-style state baseline. **97.21% acurácia** em year-fold CV de 394 eventos políticos brasileiros 2010-2024.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Year-fold acc](https://img.shields.io/badge/year--fold%20acc-97.21%25-f5a524)](docs/ONBOARDING_POLITICAL.md)
[![2024 SP](https://img.shields.io/badge/2024%20SP%20fold-89.7%25-22c55e)](docs/ONBOARDING_POLITICAL.md)
[![Eventos](https://img.shields.io/badge/eventos-394-blue)](data/backtest/)

Repositório standalone para publicação acadêmica e deploy comercial. Spin-off do projeto [Vila INTEIA](https://github.com/igormorais123/vila-inteia) (Onda 4 - 6).

---

## Quickstart (3 passos)

```bash
git clone https://github.com/igormorais123/vila-politica-2026.git
cd vila-politica-2026
pip install -r requirements.txt

# Subir API
PYTHONPATH=. python api/rotas_politica.py

# OU ver dashboard Next.js
cd frontend-next && npm install
VILA_API_BASE=http://localhost:8123 npm run dev
# http://localhost:3001
```

Endpoints REST `/api/v1/politica/*` retornam predições, backtest, custom scenarios, multi-tenant via `X-API-Key`.

---

## Modelo

```
p_blend  = 0.3 · p_cohort + 0.7 · p_Linzer
p_final  = 0.64 · p_blend + 0.36 · p_state_baseline    (Onda 4)

p_cohort = (1-s) · cohort_rate + s · global_rate       Stein shrink, s=0.4
p_Linzer = Φ(lead_pp / σ(days)),  σ = 3.0 + 0.01·days
p_state  = (W_uf,regime + 1) / (N_uf,regime + 2)       Laplace, min N=3
```

Adaptive w_state per cell + isotonic recalibration helpers (Onda 6) também disponíveis em `engine/political_cohort.py`.

---

## Resultados year-fold CV

| Ciclo | n | Acc | Brier |
|-------|---|----:|------:|
| 2010 federal | 86 | 100.0% | 0.102 |
| 2016 SP | 20 | 85.0% | 0.085 |
| 2018 federal | 70 | 98.6% | 0.184 |
| 2020 SP | 30 | 100.0% | 0.017 |
| 2022 federal | 120 | 100.0% | 0.085 |
| 2024 SP | 68 | 89.7% | 0.107 |
| **avg** | **394** | **97.21%** | **0.095** |

Selective τ=0.40 → **100% acc / 11% cobertura**.

Cross-country (US 2016/2020 + UK 2019, 6,382 events):
- US 2020 LOSO: 93.1% (beats BR 2024 89.7%)
- US 2016 LOSO: 88.1% (Vila herda erro indústria swing states)
- UK 2019: 47.9% (regime taxonomy precisa estender pra multi-party)

Stats rigor (Phase 1):
- DM = -4.92, p = 8.5e-7 (baseline lower Brier, sig)
- McNemar χ² = 18.27, p = 1.9e-5 (MRP +21 hits net, sig)
- Murphy decomposition per cycle (10 bins) — 2018 e 2024 SP weak resolution

---

## Estrutura

```
vila-politica-2026/
├── engine/
│   ├── political_cohort.py    # PC-CRD + Linzer + MRP + isotonic
│   └── auth_clients.py        # multi-tenant API keys
│
├── api/
│   └── rotas_politica.py      # 9 endpoints FastAPI
│
├── scripts/
│   ├── smoke_political.py        # 29/29 tests
│   ├── backtest_political.py     # year-fold + selective
│   ├── autoresearch_political.py # grid 2,688 + W_STATE
│   ├── predict_2026.py           # gera predictions_2026.json
│   ├── political_stats_rigor.py  # bootstrap CI + DM + McNemar + Murphy
│   ├── baseline_gauntlet.py      # 5 ablation models
│   ├── failure_analysis.py       # 11 misses clustered
│   └── cross_country_validation.py  # US 2016/2020 + UK 2019
│
├── data/
│   ├── backtest/             # 10 CSVs (BR + cross-country + qual pool)
│   ├── political_best_config.json    # v1.3 hyperparams
│   ├── predictions_2026.json         # snapshot atual
│   ├── political_stats_v2.json
│   ├── baseline_gauntlet.json
│   ├── failure_analysis.json
│   └── cross_country_results.json
│
├── docs/
│   ├── ONBOARDING_POLITICAL.md       # arquitetura completa
│   ├── CLIENT_ONBOARDING.md          # quickstart cliente
│   ├── DEPLOY_POLITICAL.md           # Render + Vercel
│   ├── BASELINE_COMPARISON.md        # 5 ablation models
│   ├── FAILURE_MODES.md              # 11 misses + adaptive rule
│   ├── CROSS_COUNTRY_VALIDATION.md   # US 2016/2020 + UK 2019
│   ├── PREREGISTRATION.md            # H1-H4 + SHA frozen artifacts
│   ├── ARXIV_SUBMISSION.md           # arXiv stat.AP submission prep
│   ├── OSF_PREREG_INSTRUCTIONS.md    # OSF preprint guide
│   ├── PREREG_FREEZE_PROCEDURE.md    # git tag freeze
│   ├── screenshots/                  # 6 PNGs frontend
│   └── paper/
│       ├── PAPER.md                  # journal manuscript v2 (40KB, 5808w)
│       ├── figs/                     # 4 PNGs 300dpi
│       └── vila_mrp_artigo.pdf
│
├── frontend-next/                    # Next.js 15 dashboard (Vercel-ready)
│   ├── app/                          # / governadores senado simular custom backtest
│   ├── components/
│   └── lib/api.ts, predict.ts
│
├── migrations/
│   └── 005_political_forecasts.sql
│
└── tests/
    └── (TODO consolidate from scripts/smoke + integration)
```

---

## Cite

```bibtex
@misc{malheiros_vila_politica_2026,
  author       = {Pedro Afonso Malheiros and Igor Morais Vasconcelos},
  title        = {{Vila Pol{\'i}tica 2026: MRP-Augmented Cohort Empirical Bayes for Brazilian Election Forecasting}},
  year         = {2026},
  publisher    = {GitHub},
  howpublished = {\url{https://github.com/igormorais123/vila-politica-2026}}
}
```

Working paper: `docs/paper/PAPER.md` (5808 words, 4 figs, 48 refs, structured abstract).

---

## Endpoints

| Path | Retorna |
|------|---------|
| `GET /api/v1/politica/health` | status + n_train_events |
| `GET /api/v1/politica/elections` | calendário 2026 |
| `GET /api/v1/politica/predictions/presidente` | 5 candidatos elegíveis |
| `GET /api/v1/politica/predictions/governador?uf=SP` | top por UF |
| `GET /api/v1/politica/predictions/senador` | titulares cadeira 2026 |
| `GET /api/v1/politica/backtest` | métricas + selective |
| `POST /api/v1/politica/predict` | predição custom |

Multi-tenant via `X-API-Key`. Tiers: free (30/min), pro (300/min), enterprise.

---

## Reproducibility

- **Code freeze**: git tag `v1.3-prereg`
- **Random seed**: 42
- **Config SHA256**: see `docs/PREREGISTRATION.md` §3
- **Data**: `data/backtest/*.csv` (real polls Wikipedia/TSE/FiveThirtyEight)
- **Pre-registration**: OSF DOI (TBD post-submission)

---

## License

MIT. See [LICENSE](LICENSE).

Paper texto: CC-BY 4.0.

---

**Authors**:
- Pedro Afonso Malheiros (`colmeia@inteia.com.br`)
- Igor Morais Vasconcelos ([@igormorais123](https://github.com/igormorais123))
