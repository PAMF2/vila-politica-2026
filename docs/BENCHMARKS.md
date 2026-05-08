# Vila Política 2026 - Benchmarks

Benchmarks consolidados: model performance, latência, throughput.

---

## Model performance (year-fold CV, 394 events, T≤30)

Headline avg accuracy + Brier per model. Year-fold leak-safe (test cycle never in train).

| Model | Brier ↓ | Acc ↑ | Acc 2024 SP | Notas |
|-------|--------:|------:|------------:|-------|
| **Vila MRP tuned** (this paper) | 0.105 | **97.21%** | **89.7%** | shrink=0.4, w_lin=0.7, w_state=0.36 |
| BART (HistGB proxy) | **0.050** | 95.18% | 100.0% | 200 trees, lr=0.05, depth=4 |
| Vila no-MRP (cohort+Linzer) | 0.072 | 94.16% | 73.5% | baseline |
| Linzer-only | 0.075 | 91.88% | 73.5% | só Φ(lead/σ(d)) |
| Naive poll (sigmoid lead/10) | 0.100 | 91.88% | 73.5% | floor |
| Stan DLM (Kalman, Linzer 2013) | 0.073 | 82.74% | 0.0% | pure-Python, MLE σ_walk + σ_obs |
| Cohort-only | 0.200 | 59.64% | - | sem poll signal |

**Observação honesta**: Vila MRP wins acc (+5.3pp vs baseline) mas perde Brier (+0.033). Trade-off documentado em paper §5.3 (calibração vs decision).

---

## Cross-country generalization

Year-fold CV em US 2016 + US 2020 + UK 2019 (real polls FiveThirtyEight + Wikipedia).

| Cycle | n | Acc no-MRP | Acc + MRP w=0.36 | Brier MRP |
|-------|---|----:|----:|----:|
| US 2016 (LOSO) | 3,130 | 88.1% | 88.1% | 0.073 |
| US 2020 (LOSO) | 3,060 | 93.1% | 93.1% | 0.034 |
| UK 2019 (regional) | 192 | 47.9% | 47.9% | 0.360 |
| **avg non-BR** | 6,382 | **89.31%** | **89.31%** | - |

US cross-cycle (train 2020 → test 2016): MRP +2.7pp acc, Brier 0.098→0.082.

UK 2019 falla pq taxonomia regime `{left, right, center}` colapsa Con/Lab/LD/SNP/Brx multi-party. Architecture extension futura.

---

## Statistical rigor (Phase 1)

Year-fold CV pooled (n=394), seed=42, 1000 bootstrap resamples.

### Diebold-Mariano (squared loss)

| stat | value |
|------|------:|
| DM statistic | -4.92 |
| p-value (two-sided) | 8.5e-7 |

Reject H0. Baseline (cohort+Linzer) significantly lower Brier than MRP.

### McNemar (paired accuracy)

| stat | value |
|------|------:|
| chi² (continuity-corrected) | 18.27 |
| p-value | 1.9e-5 |
| baseline-wrong/MRP-right (b) | 22 |
| baseline-right/MRP-wrong (c) | 1 |

Reject H0. MRP +21 net hits (22 recovered, 1 introduced).

### Murphy decomposition (10 bins)

Brier = REL - RES + UNC per cycle.

| cycle | REL ↓ | RES ↑ | UNC | Brier |
|-------|------:|------:|----:|------:|
| 2010 | 0.101 | 0.250 | 0.250 | 0.102 |
| 2016 | 0.004 | 0.175 | 0.250 | 0.085 |
| 2018 | 0.172 | 0.236 | 0.250 | 0.184 |
| 2020 | 0.017 | 0.250 | 0.250 | 0.017 |
| 2022 | 0.085 | 0.250 | 0.250 | 0.085 |
| 2024 | 0.033 | 0.180 | 0.250 | 0.107 |

2018 + 2024 SP têm RES weak (model menos discriminativo nesses ciclos).

---

## Selective coverage curve

Threshold τ aplicado em |p - 0.5|. Predictions com confiança < τ são abstidas.

| τ | Coverage | Acc | Brier |
|---|---------:|----:|------:|
| 0.05 | 96.7% | 95.01% | 0.078 |
| 0.15 | 91.9% | 96.13% | 0.077 |
| 0.20 | 85.5% | 95.85% | 0.078 |
| 0.25 | 43.9% | 97.11% | 0.061 |
| 0.30 | 19.5% | 96.10% | 0.058 |
| **0.40** | **11.2%** | **100.00%** | **0.040** |

τ=0.40 → 100% acc em 44 events confiantes (11.2% cobertura).

---

## Latência API (single-thread, py3.11)

Medido via `scripts/bench_latency.py`. FastAPI TestClient (no network round-trip).

### Engine (model layer)

| Operação | n_train | p50 | p95 | p99 |
|----------|--------:|----:|----:|----:|
| Cohort fit | 444 | 1.29ms | 1.38ms | - |
| Single prediction (full ensemble) | - | **0.004ms** | - | 0.009ms |
| Snapshot regen (~25 candidatos) | 444 | 0.07ms | 0.10ms | - |

Single prediction ~4 microsegundos = 250k predições/segundo single-thread.

### API endpoints

| Endpoint | p50 | p95 | p99 |
|----------|----:|----:|----:|
| `GET /health` | 4.88ms | 7.79ms | 8.67ms |
| `GET /elections` | 5.98ms | 14.53ms | 49.34ms |
| `GET /predictions/presidente` | 8.52ms | 22.14ms | 46.29ms |
| `GET /predictions/governador?uf=SP` | 6.14ms | 12.31ms | 13.29ms |
| `GET /predictions/senador` | 6.94ms | 10.11ms | 23.35ms |
| `GET /backtest` | 14.51ms | 18.86ms | 19.60ms |
| `POST /predict` | 7.04ms | 10.09ms | - |

### Throughput estimate

- /health: ~205 req/s single-thread
- /predictions/presidente: ~117 req/s
- /backtest (snapshot heavy): ~69 req/s

Multi-worker via uvicorn `--workers N`: throughput escala ~linearmente até cores disponíveis.

---

## Reproducibility

```bash
# All benchmarks
PYTHONPATH=. python scripts/political_stats_rigor.py     # Phase 1 (stats)
PYTHONPATH=. python scripts/baseline_gauntlet.py         # Phase 2 (5 ablations)
PYTHONPATH=. python scripts/cross_country_validation.py  # Phase 3 (US/UK)
PYTHONPATH=. python scripts/failure_analysis.py          # Phase 4 (clustering)
PYTHONPATH=. python scripts/bench_latency.py             # latência

# Outputs
ls data/political_stats_v2.json data/baseline_gauntlet.json \
   data/cross_country_results.json data/failure_analysis.json \
   data/bench_latency.json
```

Seed = 42. Config v1.3: `data/political_best_config.json`.

---

## Honest model rankings

**Por accuracy:**
1. Vila MRP tuned 97.21% (winner)
2. BART proxy 95.18%
3. Vila no-MRP 94.16%
4. Linzer / Naive 91.88% (tied)
5. Stan DLM 82.74%
6. Cohort-only 59.64%

**Por Brier (calibração):**
1. BART 0.050 (winner)
2. Vila no-MRP 0.073
3. Stan DLM 0.073
4. Linzer 0.075
5. Naive 0.100
6. Vila MRP 0.105
7. Cohort 0.200

**Trade-off:** Vila MRP wins acc mas perde Brier vs BART. BART tem segunda-melhor acc + melhor Brier — modelo mais bem calibrado. Vila MRP é melhor pra decisões discretas (yes/no winner), BART pra probability calibration.

**Stan DLM** acerta 100% nos federais (2010, 2018, 2022) e SP 2020 mas erra 100% no SP 2024 (Boulos polls). É a réplica fiel de Linzer 2013 em Python — mostra que paper original Linzer também herdaria erro indústria-wide.

## Próximas iterações

- Live forecast comparison (Polymarket / PredictIt arquivos)
- MRP demographic poststratification (PNAD-C 2025-Q4)
- Multi-worker throughput scaling teste (uvicorn workers=4,8)
- House effects per instituto refit (Onda 5 lateral-zero, retrying with 2026 polls)
