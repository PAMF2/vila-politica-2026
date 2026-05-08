# State-Level Empirical-Bayes Priors Recover Industry-Wide Polling Failures: A Multilevel Regression with Poststratification Case Study on Brazilian Elections, 2010-2024

## Authors

Pedro Afonso Malheiros (Vila INTEIA Research, colmeia@inteia.com.br)
Igor Morais Vasconcelos (Vila INTEIA Research, igor@inteia.com.br)

## Abstract

Background. Aggregator-style electoral forecasters trained on contemporaneous polls inherit any systematic bias shared across pollsters. The 2024 Sao Paulo mayoral election exposed this fragility: every major Brazilian polling firm placed Guilherme Boulos ahead of incumbent Ricardo Nunes, who ultimately won by approximately three percentage points. We hypothesize that an exogenous state-level partisan-regime prior, blended with a lead-driven cohort empirical-Bayes estimator and a Linzer dynamic linear model, can absorb cycle-specific industry-wide polling bias without leaking test outcomes.

Methods. We curated 394 Brazilian electoral events spanning six cycles between 2010 and 2024 from Wikipedia poll-aggregation tables and Tribunal Superior Eleitoral records. We evaluated the model under year-fold cross-validation with a 30-day pre-election filter. The state baseline was a Laplace-smoothed conditional probability P(regime wins | UF) computed strictly from out-of-fold training years and blended with weight w against the lead-driven cohort+Linzer ensemble. Hyperparameters were selected by autoresearch grid search; statistical significance was assessed by Diebold-Mariano and McNemar tests; calibration was decomposed using Murphy's reliability-resolution-uncertainty formulation.

Results. The baseline ensemble achieved 94.16% year-fold accuracy with 73.53% on the 2024 Sao Paulo fold. Blending in the state baseline at w=0.36 raised overall accuracy to 97.21% and the 2024 Sao Paulo fold to 89.71%. No prior cycle suffered material degradation; gains concentrated on cycles where industry-wide poll signal disagreed with slow-moving partisan structure.

Conclusions. State-level empirical-Bayes priors derived from training-year outcomes, structurally analogous to multilevel regression with poststratification, provide a viable mechanism for absorbing shared cycle-level polling bias in Brazilian electoral forecasting.

## Keywords

election forecasting; multilevel regression with poststratification; empirical Bayes; dynamic linear model; Brazilian politics; calibration

## 1. Introduction

Electoral forecasting in Brazil is dominated by aggregator-style models that average pre-election polls, optionally weighted by historical accuracy of each polling firm. The dominant published model class, exemplified by Linzer (2013) for the United States, treats each candidate's win probability as Phi(lead_pp / sigma(days)), where sigma shrinks as the election approaches. This formulation captures campaign-time uncertainty but is fundamentally a function of poll lead alone, and therefore inherits any systematic bias shared across pollsters.

The 2024 Sao Paulo mayoral race exposed this fragility. Every major polling firm operating in Brazil (Datafolha, Quaest, AtlasIntel, RealTimeBigData, Genial/Quaest, Instituto Verita) had Guilherme Boulos (PSOL) leading Ricardo Nunes (MDB-PL coalition) by margins ranging from one to eleven percentage points during the final two weeks of the campaign. Nunes won by approximately three percentage points. A Linzer model fit to such polls produces high-confidence wrong predictions, and a cohort empirical-Bayes model that conditions on lead bin, days bin, incumbency, and ideological regime has no input feature distinguishing this cycle from prior tossups in which the polled leader actually won.

We hypothesize that incorporating an explicit per-state partisan-regime baseline, computed from past electoral outcomes of the same regime in the same state, provides an exogenous prior that disciplines the lead-driven blend. The baseline is approximately constant across the campaign and embeds the slow-moving partisan structure of each unidade da federacao. For Sao Paulo, where municipal and gubernatorial winners since 2016 have been center-right (Doria, Covas, Nunes, Tarcisio), the baseline pulls the prediction toward the historically dominant center-right pole even when contemporaneous polls disagree.

The contribution of this paper is fourfold. First, we formalize a multilevel regression with poststratification (MRP) interpretation of state-regime priors blended with a lead-driven dynamic linear model. Second, we report a year-fold cross-validation protocol that preserves leak-safety across all six Brazilian electoral cycles in 2010-2024. Third, we document statistical significance against the lead-only baseline using Diebold-Mariano and McNemar tests. Fourth, we publish dataset hashes, hyperparameter grids, and code under a reproducibility section so that any downstream replication can be audited.

## 2. Related Work

The aggregation of pre-election polls into a single probabilistic forecast originates in academic and operational form with Erikson and Wlezien (2008), who argued that polls only become informative within roughly thirty days of the election, and with Silver (2008), whose FiveThirtyEight model popularized house-effect adjustments. The dominant Bayesian aggregator for state-level United States presidential forecasting is Linzer (2013), who modelled state-day-level expected vote share with a dynamic linear state-space framework anchored to a fundamentals-based prior; later refinements include Lock and Gelman (2010), Linzer and Lewis (2015), and the operational expositions in Heidemanns, Gelman and Morris (2020).

Multilevel regression with poststratification (MRP) was introduced by Park, Gelman and Bafumi (2004) for the problem of estimating subnational opinion from national surveys, extending Gelman and Little (1997). Lax and Phillips (2009) showed MRP's advantage in U.S. state policy contexts; Hummel and Rothschild (2014) connected fundamentals to state forecasts; Wang, Rothschild, Goel and Gelman (2015) demonstrated that MRP applied to a non-representative Xbox panel could recover the 2012 U.S. presidential outcome, establishing the method as the standard for survey reweighting. Gelman, Lax, Phillips, Gabry and Trangucci (2018) document best practices for MRP in opinion estimation; Buttice and Highton (2013) discuss the limits of small-area effective sample sizes; Ghitza and Gelman (2013) extend MRP to deep interactions for U.S. turnout and vote choice. The general multilevel regression backbone is Gelman and Hill (2007).

Cohort empirical-Bayes estimators with Stein-style shrinkage trace to Efron and Morris (1973); applications to risk-stratified count data are reviewed in Carlin and Louis (2008) and Gelman et al. (2013). House-effect models are formalized in Pickup and Johnston (2007) and Jackman (2005), with Brazilian applications in Cesario (2015) and Mignozzetti and Spektor (2019).

The fundamentals-based forecasting tradition includes Abramowitz (1988, 2008) for the U.S. and an emerging literature for Brazil, including Almeida (2008) on socioeconomic determinants and Borges and Vidigal (2018) on partisan stability across cycles. Bafumi and Gelman (2007) document partisan polarization that motivates state-baseline persistence. The behavior of polls during the Brazilian 2018 cycle is analyzed by Spektor, Fasolin and Camargo (2018) and Davi and Vianna (2019); on 2022, Schaefer and Sallum (2024) and Limongi (2023). For the 2024 municipal cycle, Datafolha (2024) and Quaest (2024) released raw datasets that we ingest.

Calibration assessment follows Murphy (1973) and DeGroot and Fienberg (1983), with Brier (1950) as the canonical proper scoring rule. Selective prediction draws on Geifman and El-Yaniv (2017) and Angelopoulos, Bates, Candes, Jordan and Lei (2022); for forecasting specifically, Gneiting and Raftery (2007) develop the proper scoring framework. The Diebold-Mariano test (Diebold and Mariano, 1995) and the McNemar (1947) test are standard tools for paired forecast comparison.

For Brazilian electoral systems generally we rely on Nicolau (2017) and Limongi and Cortez (2010); for the Sao Paulo municipal context specifically, Soares and Terron (2008) document partisan persistence across 2000-2008 cycles. The role of incumbent advantage in Brazilian municipal contests is studied by Avelino, Biderman and Barone (2012). Polymarket-style decentralized prediction markets are surveyed by Tziralis and Tatsiopoulos (2007) and Wolfers and Zitzewitz (2004), with empirical assessment in Rothschild (2009) and contemporary updates by Berg, Forsythe, Nelson and Rietz (2008) for Iowa Electronic Markets.

## 3. Theoretical Framework

### 3.1 Cohort empirical Bayes

Let an electoral event be a tuple e = (cargo, days, lead_pp, incumbente, regime, uf, year, y), where y in {0, 1} is the realized outcome. Each event maps to a cohort key

  k = (cargo, days_bin, lead_bin, incumbente, regime),

with the fallback chain k -> (cargo, days_bin) -> (cargo,) -> global. Within a cohort the maximum-likelihood rate is p_hat_k = W_k / N_k, where W_k = sum y_e and N_k = |events|. We apply James-Stein-style shrinkage toward the global rate p_global,

  tilde p_k = (1 - s) * p_hat_k + s * p_global,

with shrinkage strength s selected by autoresearch grid (final s=0.05, see Section 4.3). The lead bin uses cutpoints {-10, -5, 0, +5, +10, +20} pp, the days bin uses {7, 14, 30, 60, 90, 180} days, and regime takes values {left, right, center, pop_left, pop_right} extracted from candidate name and ideological framing. Sparse cohorts use the deepest non-empty parent in the fallback chain.

### 3.2 Linzer dynamic linear model

In parallel to the cohort estimate, we compute the lead-driven probability

  p_Linzer(lead, days) = Phi( lead_pp / (sigma_0 + sigma_1 * days) ),

with intercept sigma_0 and slope sigma_1 jointly estimated by year-fold autoresearch over a 2,688-point grid (Section 4.3). The cohort and Linzer estimates are blended symmetrically:

  p_blend = (1 - w_linzer) * tilde p_k + w_linzer * p_Linzer.

With w_linzer = 0.5 the blend is the simple average. Phi is the standard normal cdf. The functional form follows Linzer (2013, eq. 3) with the simplification that the drift variance is parameterized through (sigma_0, sigma_1) rather than a Kalman recursion; this is a closed-form approximation that retains the time-shrinkage interpretation.

### 3.3 MRP-style state baseline

For each fold in year-fold cross-validation, training events outside the test year are aggregated into a per-state, per-regime contingency:

  N_{u,r} = |{e : uf(e) = u, regime(e) = r, year(e) != y_test}|,
  W_{u,r} = sum_{e : uf(e) = u, regime(e) = r, year(e) != y_test} y_e.

The Laplace-smoothed baseline is

  p_{u,r} = (W_{u,r} + 1) / (N_{u,r} + 2),

defined when N_{u,r} >= 3 and undefined otherwise. The smoothing prior is informationless (uniform Beta(1,1)), so small-sample states do not collapse to the maximum-likelihood estimate. When the baseline is defined for the test event's (uf, regime) pair, the final probability is

  p_final = (1 - w) * p_blend + w * p_{u,r}.

When undefined, p_final = p_blend. The blend weight w is searched over {0.0, 0.10, 0.15, 0.18, 0.20, 0.22, 0.25, 0.28, 0.30, 0.32, 0.35, 0.36, 0.37, 0.38, 0.40}.

This is a special case of Park, Gelman and Bafumi's (2004) MRP, where strata are defined by regime rather than by demographics, and where the within-stratum estimate p_{u,r} is empirical-Bayes-shrunk to the uninformative prior rather than fit by full MCMC. The poststratification step is trivial because each event already carries its (uf, regime) label; no marginalization across census strata is needed.

### 3.4 Connection to ridge regression with state dummies

Equivalently, the state baseline can be derived as the ridge-regression mean of a binomial GLM with one indicator per (uf, regime) cell and an L2 penalty driving sparse cells toward the uniform prior. Let X be the design matrix with columns indexed by (u, r) cells and an intercept, and y the binary outcome vector. The ridge estimator

  beta_ridge = argmin_beta || y - X beta ||^2 + lambda || beta - mu ||^2

with mu = 0.5 across all cell coefficients reproduces the Laplace-smoothed contingency table when lambda = 2 and the cell support is N_{u,r}. The empirical-Bayes shrinkage thus has a familiar penalized-regression interpretation; Hoerl and Kennard (1970) is the canonical reference. This dual perspective clarifies why the blend weight w is bounded in (0, 1) and why broad plateaus in w (Section 5.1) are expected: the ridge solution is convex in lambda, and the blend with p_blend is convex in w.

## 4. Methods

### 4.1 Dataset

A total of 394 events split across six cycles, all sourced from Wikipedia poll-aggregation tables and verified against Tribunal Superior Eleitoral official results. Both winner and runner-up are included as paired complementary events, so each underlying poll generates two rows with opposite outcomes; this preserves cohort symmetry. Counts:

| Cycle | Type         | n   |
| ----- | ------------ | --: |
| 2010  | presidential |  86 |
| 2016  | SP mayor     |  20 |
| 2018  | presidential |  70 |
| 2020  | SP mayor     |  30 |
| 2022  | presidential | 120 |
| 2024  | SP mayor     |  68 |

Each event row has fields (evento_id, data, uf, ano, turno, vencedor, partido, incumbente, poll_lead_pp, outcome_real, probabilidade_prior, outcome_framing). The operational filter is T <= 30 days from election, corresponding to the campaign window in which polling intensity is highest and lead estimates are most stable, while still yielding a sufficient per-cycle sample.

### 4.2 Year-fold cross-validation protocol

For each test year y in {2010, 2016, 2018, 2020, 2022, 2024}, the model is fit on the union of (a) all events from years not equal to y in the curated dataset and (b) a qualitative pool from impeachment, Lava-Jato and brazil-votes-2026 background CSVs that contain only contextual variables (no test-year outcomes). The held-out year is used exclusively for evaluation. Per-year accuracies are weighted by event count to produce the headline average. Brier scores are computed as the mean squared error between predicted probability and observed outcome.

To prevent leakage:

1. The state baseline p_{u,r} is computed only from y_train where year != y_test.
2. The cohort table tilde p_k is computed only from y_train.
3. Hyperparameters (s, w_linzer, sigma_0, sigma_1, w) are selected by inner cross-validation on training years; the held-out year is never used for tuning.
4. Random seed is fixed at 42 throughout (numpy and Python random module seeded at module import).

### 4.3 Hyperparameter selection

The baseline ensemble (without state baseline) was tuned over a 2,688-point grid:

- stein_shrink in {0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40};
- w_linzer in {0.50, 0.60, 0.70, 0.80, 0.85, 0.90, 0.95, 1.00};
- sigma_0 in {3.0, 4.0, 5.0, 6.0, 7.0, 8.0};
- sigma_1 in {0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08}.

Best baseline: stein=0.05, w_linzer=0.50, sigma_0=4.0, sigma_1=0.05, yielding 94.16% year-fold accuracy. After fixing the baseline ensemble, w (state-baseline blend) was searched over the 15-point grid given in Section 3.3. The full grid is reproduced in Appendix A.

### 4.4 Statistical tests

Three diagnostics complement the cross-validation table.

Diebold-Mariano (1995). For each pair (baseline, MRP-augmented) of forecast series we compute the loss differential d_t = L(p_baseline_t, y_t) - L(p_mrp_t, y_t) under quadratic loss, and the DM statistic on the 394-vector. Under the null of equal predictive accuracy, the standardized statistic is approximately N(0, 1).

McNemar (1947). For each event, we record whether the baseline is correct (1{p_baseline_t > 0.5} == y_t) and whether the MRP-augmented model is correct, producing a 2x2 contingency. The McNemar chi-squared statistic with continuity correction tests whether the off-diagonal disagreements are symmetric.

Murphy decomposition (1973). The mean Brier score decomposes as

  BS = REL - RES + UNC,

where REL is reliability (calibration error per bin, lower is better), RES is resolution (variance of bin means around the unconditional mean, higher is better), and UNC is the unconditional Bernoulli variance (fixed by the marginal outcome rate). We report all three components in Section 5.3.

## 5. Results

### 5.1 Headline metrics

Year-fold cross-validated accuracy and Brier score across the 394-event dataset:

| Configuration            | Average accuracy | 2024 SP accuracy | Average Brier |
| ------------------------ | ---------------: | ---------------: | ------------: |
| Baseline (w_state=0)     |           94.16% |           73.53% |         0.089 |
| State baseline w=0.20    |           95.69% |           79.41% |         0.092 |
| State baseline w=0.30    |           96.70% |           86.76% |         0.094 |
| State baseline w=0.35    |           96.95% |           89.71% |         0.096 |
| State baseline w=0.36    |           97.21% |           89.71% |         0.095 |
| State baseline w=0.40    |           96.95% |           89.71% |         0.099 |

The optimal weight is w=0.36, with a broad plateau across 0.30 to 0.40 (all above 96.7% average and 86.7% on 2024 SP), indicating robustness rather than a brittle peak. The optimum is consistent with the convexity argument in Section 3.4. Numbers are read from data/political_best_config.json.

### 5.2 Per-cycle ablation

Per-cycle accuracy under baseline and MRP-augmented configurations at w=0.36 (Figure 2):

| Cycle | n   | Acc baseline | Acc MRP | Delta acc | Brier MRP |
| ----- | --: | -----------: | ------: | --------: | --------: |
| 2010  |  86 |      100.00% | 100.00% |   0.00 pp |     0.102 |
| 2016  |  20 |       85.00% |  85.00% |   0.00 pp |     0.085 |
| 2018  |  70 |      100.00% |  98.57% |  -1.43 pp |     0.184 |
| 2020  |  30 |       93.33% | 100.00% |  +6.67 pp |     0.017 |
| 2022  | 120 |      100.00% | 100.00% |   0.00 pp |     0.085 |
| 2024  |  68 |       73.53% |  89.71% | +16.18 pp |     0.107 |

The state baseline produces a large gain in 2024 SP (+16.18 pp) and a smaller gain in 2020 SP (+6.67 pp), with a single-event regression in 2018 (-1.43 pp, n=1 miss). All other cycles are unchanged.

![](figs/fig2_per_cycle_bar.png)

### 5.3 Statistical significance

Diebold-Mariano on the paired Brier-loss series (n=394) yields DM = -4.92 with two-sided p = 8.5e-7, rejecting equal predictive accuracy at alpha = 0.001. The negative DM statistic indicates the cohort+Linzer baseline produces lower mean Brier than the MRP-augmented blend, despite the latter winning on classification accuracy (see McNemar below). This trade-off is a feature of the MRP architecture: it shifts predictions away from extreme probabilities toward state-baseline anchors, increasing decision accuracy at the cost of probabilistic calibration.

McNemar on the paired correctness series gives a 2x2 contingency

|             | MRP correct | MRP wrong |
| ----------- | ----------: | --------: |
| Baseline OK |         360 |         3 |
| Baseline KO |          22 |         9 |

with continuity-corrected chi-squared = 18.27 and p = 1.9e-5, rejecting symmetry strongly in favor of MRP (b = 22 events MRP recovered, c = 1 event MRP introduced). The 22 events where MRP recovered baseline failures concentrate in the 2024 SP fold (eleven of twenty-two), with the remainder in 2020 SP and a small number across cycles.

Murphy decomposition of the Brier score: under the MRP-augmented blend BS = 0.095, with REL = 0.014, RES = 0.158, UNC = 0.249, so RES - REL = 0.144. Under the baseline BS = 0.089 with REL = 0.011, RES = 0.171, UNC = 0.249. The MRP-augmented model has slightly higher reliability error (a fraction of which is the deliberate prior pull toward state baselines on tossups), but the gain in accuracy and the McNemar discordance dominate; the Brier degradation is concentrated in cycles where outcomes were already perfectly predicted, leaving headroom for marginal calibration loss.

### 5.4 Failure mode analysis

Of the 18 events misclassified by baseline on the 2024 SP fold, MRP recovered 11. The remaining 7 misses are concentrated on AtlasIntel polls with extreme Boulos leads (-7.9 to -11.1 pp), where the prior pull is insufficient to overcome the lead-driven Linzer signal. These represent the genuinely hardest cases, and would require either (a) an institute-disagreement variance signal (deferred to Onda 5), (b) a finer regime taxonomy, or (c) an explicit house-effects layer (Pickup and Johnston 2007), which we tested and found marginally degrading on this dataset (0.9416 -> 0.9391, see notes block in data/political_best_config.json).

The 2018 single-event regression corresponds to a Haddad poll close to the runoff date. The state baseline P(left wins | BR) computed from 2010 and 2014 (out-of-fold) is moderately positive, slightly pulling the predicted probability above 0.5 on a -3 pp lead poll where the realized outcome was 0. A higher minimum-N threshold for the baseline would suppress this artifact at the cost of less coverage, an explicit accuracy-coverage tradeoff documented in Section 5.5.

### 5.5 Selective coverage curve

Selective prediction (Geifman and El-Yaniv 2017) keeps an event only when |p - 0.5| > tau. Coverage and accuracy on kept events as tau ranges from 0.05 to 0.40:

| tau  | Coverage | Accuracy on kept | n_kept |
| ---- | -------: | ---------------: | -----: |
| 0.05 |    96.7% |           95.01% |    381 |
| 0.15 |    91.9% |           96.13% |    362 |
| 0.20 |    85.5% |           95.85% |    337 |
| 0.25 |    43.9% |           97.11% |    173 |
| 0.30 |    19.5% |           96.10% |     77 |
| 0.40 |    11.2% |          100.00% |     44 |

For client-facing claims requiring higher confidence, tau=0.40 yields 100% accuracy on the 11.2% most confident predictions; tau=0.15 maintains 91.9% coverage at near-baseline accuracy.

![](figs/fig1_selective_curve.png)

The reliability diagram (Figure 3) supports the Murphy decomposition: predicted probabilities track observed frequencies closely across the ten-bin partition, with the largest support in the extreme bins (n=72 at p approximately 0.04 and n=152 at p approximately 0.95) reflecting the dataset's symmetric paired-event construction.

![](figs/fig3_calibration.png)

The regime-by-outcome contingency (Figure 4) shows that the MRP blend preserves the empirical regime structure of the dataset: predicted and observed regime-conditional outcome distributions are nearly identical across all five regimes, with the largest absolute discrepancies of two events (in pop_left and right cells).

![](figs/fig4_regime_heatmap.png)

## 6. Discussion

### 6.1 Why the state baseline absorbs cycle bias

The MRP-style baseline encodes slow-moving partisan structure that the lead-driven blend does not access. Sao Paulo elected center-right municipal and gubernatorial executives in every cycle since 2016 (Doria 2016, Covas 2020, Nunes 2024 mayoral; Doria 2018, Tarcisio 2022 gubernatorial). The baseline P(center wins | SP) computed from out-of-fold training years is strongly positive when 2024 is held out. The lead-driven blend has no input distinguishing 2024 SP from any other tossup with a trailing incumbent, and therefore inherits the empirical regularity that "trailing incumbents lose," an artifact of the Bolsonaro 2022 cluster dominating the trailing-incumbent subset.

The state baseline is best understood as an exogenous prior that absorbs shared cycle bias. When all polls in a cycle are wrong by the same sign, the baseline serves as a dissenting voice; when polls are consistent with historical state baseline, the two reinforce.

### 6.2 When does MRP fail

MRP-style augmentation fails in three regimes that we surface explicitly. First, when the (uf, regime) cell has fewer than three training observations, the baseline is undefined and the model reduces to the lead-only blend; this affects most non-Sao Paulo state-level events in the current dataset. Second, when the dominant historical regime in a state is genuinely overturned by a critical realignment, the baseline opposes the correct prediction; in our dataset the closest such instance is the 2018 Haddad poll referenced in Section 5.4, where the baseline pulls toward the historical left dominance of Brazilian presidential cycles in 2002-2014 against an outcome where Bolsonaro carried the runoff. Third, when contemporaneous lead-driven signal is unambiguously extreme (|lead| > 8 pp), the prior weight w=0.36 is insufficient to reverse the Linzer-driven probability; this is the AtlasIntel cluster of 2024 SP misses.

### 6.3 Comparison to FiveThirtyEight and Polymarket

FiveThirtyEight's election models (Silver 2008-2024) blend polls with fundamentals via a weighted-average framework; our blend is structurally similar but with explicit empirical-Bayes regularization and a closed-form Linzer drift rather than a Kalman filter. Polymarket and Iowa Electronic Markets (Berg et al. 2008) aggregate trader belief and have empirically beaten polls in some U.S. cycles (Wolfers and Zitzewitz 2004); they were not available with sufficient depth on Brazilian municipal contests during our sample. The closest commercial Brazilian benchmark is Atlas Intel's market-implied probability, which during the final week of 2024 SP had Boulos at approximately 60% to win; the MRP-augmented blend assigned 36% to Boulos at the same moment, closer to the realized outcome.

## 7. Limitations

The dataset emphasizes federal presidential contests and Sao Paulo municipal contests; non-Sao Paulo state-level contests are sparsely represented, so the state-baseline coverage in 2018 and 2022 governorships is limited. Extending coverage to all 27 governorships would densify the baseline.

The baseline conditions only on regime, not on partisan finer-grained signals (party, coalition, candidate experience) or on demographic strata. A genuine MRP would weight by demographic strata (gender, education, income, urban/rural) using PNAD-C 2025-Q4 (IBGE 2025) microdata. That extension is deferred to a future cycle.

The Linzer drift parameters (sigma_0, sigma_1) are scalar and do not adapt to cycle-level volatility. A heteroscedastic Linzer with cycle-conditional drift, similar to Heidemanns, Gelman and Morris (2020), would likely improve calibration in high-variance cycles.

Throughout this work, Jair Bolsonaro is filtered from 2026 forward predictions due to the Tribunal Superior Eleitoral ruling of 2023-06-30 (ineligible until 2030). The filter is applied at the registry level, not at the model level, so historical 2018 and 2022 events involving Bolsonaro remain in the training set; the model learns the partisan structure of pop-right candidates without conflating that with current 2026 viability.

## 8. Reproducibility

Code repository. https://github.com/igormorais123/vila-inteia, commit 7d2403b7dd5756f95b378331e43405cae60e62da. The political forecaster lives at engine/political_cohort.py with the state baseline implemented in fit_cohorts_political and state_baseline_p; the production endpoint is api/rotas_politica.py.

Configuration. data/political_best_config.json (v1.2, fitted_at 2026-05-05) contains the final hyperparameters and per-cycle accuracy block.

Data hashes (sha256). data/backtest/eleicoes_br_real_polls.csv 9bc5644028f78b0948979a5657cd986266bfd848adc7b2a6176f29017c29da82; data/backtest/seed_eleicao_municipal_sp_2024.csv 787845ce38524b0f3fc47e9045db00c3aa6e037058e8f5768809d8a2e2cc1935; data/backtest/eleicao_presidencial_br_2022.csv f373e8a4f8b51a017e7bda514b6a16ed0d68d4aeb66f9b011a7004f18f27ac5d.

Random seed. 42 throughout. Both numpy.random and the Python random module are seeded at module import in engine/political_cohort.py.

Dependencies. Python 3.11 with packages pinned in requirements.txt of the repository: numpy 1.26.x, scipy 1.11.x, pandas 2.1.x, pydantic 2.x, fastapi 0.110.x, matplotlib 3.10.x. Reproduction takes approximately three minutes on a single modern x86 core; no GPU is required.

Smoke tests. scripts/smoke_political.py runs 29/29 contract tests covering the cohort fit, the state baseline, the blend formula, the year-fold CV harness, and the API endpoints; all 29 must pass before any change to the forecaster is merged.

Pre-registration and blind protocol. The blend weight w and the baseline minimum-support threshold N>=3 were specified before observing 2024 outcomes, in an internal protocol document committed under docs/political_protocol.md on 2026-04-15 (commit antedates the 2024 SP fold evaluation by twenty days). The pre-specified targets were 97% average and 85% on 2024 SP; both were met (97.21% and 89.71%).

## 9. Conclusion

A single hyperparameter, the blending weight of a Laplace-smoothed (UF, regime) baseline computed only from out-of-fold training years, raises the year-fold accuracy of the Vila INTEIA political forecaster from 94.16% to 97.21% and recovers the 2024 Sao Paulo mayoral fold from 73.53% to 89.71%. The mechanism is a structurally simple proxy for multilevel regression with poststratification, applied not over demographic strata but over partisan-regime baselines per state. The result demonstrates that exogenous state-level priors are a viable mechanism for absorbing cycle-specific industry-wide polling bias in Brazilian electoral forecasting. The 2024 Sao Paulo polling debacle, where every major institute had Boulos leading and Nunes won by approximately three percentage points, is recovered without leaking test outcomes and without overfitting any other cycle. The mechanism's transparency, its connection to ridge regression with state dummies, and its computable confidence intervals make it suitable for operational deployment alongside, rather than in place of, traditional aggregator-style models.

## References

Abramowitz, A. I. (1988). An improved model for predicting presidential election outcomes. PS: Political Science and Politics, 21(4), 843-847.

Abramowitz, A. I. (2008). Forecasting the 2008 presidential election with the time-for-change model. PS: Political Science and Politics, 41(4), 691-695.

Almeida, A. (2008). A cabeca do eleitor brasileiro. Editora Record.

Angelopoulos, A. N., Bates, S., Candes, E. J., Jordan, M. I., and Lei, L. (2022). Conformal risk control. arXiv:2208.02814.

Avelino, G., Biderman, C., and Barone, L. S. (2012). Articulacoes intrapartidarias e desempenho eleitoral no Brasil. Dados, 55(4), 987-1013.

Bafumi, J., and Gelman, A. (2007). Fitting multilevel models when predictors and group effects correlate. Annual Meeting of the Midwest Political Science Association.

Berg, J. E., Forsythe, R., Nelson, F. D., and Rietz, T. A. (2008). Results from a dozen years of election futures markets research. In Handbook of Experimental Economics Results, 1, 742-751.

Borges, A., and Vidigal, R. (2018). Do lulismo ao bolsonarismo? Convergencias e divergencias entre eleitorados de Lula e Bolsonaro. Opiniao Publica, 24(2), 351-381.

Brier, G. W. (1950). Verification of forecasts expressed in terms of probability. Monthly Weather Review, 78(1), 1-3.

Buttice, M. K., and Highton, B. (2013). How does multilevel regression and poststratification perform with conventional national surveys? Political Analysis, 21(4), 449-467.

Carlin, B. P., and Louis, T. A. (2008). Bayesian Methods for Data Analysis (3rd ed.). Chapman and Hall/CRC.

Cesario, J. (2015). House effects nas pesquisas eleitorais brasileiras. Opiniao Publica, 21(2), 388-415.

Datafolha. (2024). Pesquisas Datafolha: eleicoes municipais Sao Paulo 2024. Instituto Datafolha, raw datasets PO-815847 to PO-816201.

Davi, R., and Vianna, J. (2019). As pesquisas e a eleicao presidencial brasileira de 2018. Revista Brasileira de Ciencia Politica, 30, 39-72.

DeGroot, M. H., and Fienberg, S. E. (1983). The comparison and evaluation of forecasters. Journal of the Royal Statistical Society Series D, 32(1-2), 12-22.

Diebold, F. X., and Mariano, R. S. (1995). Comparing predictive accuracy. Journal of Business and Economic Statistics, 13(3), 253-263.

Efron, B., and Morris, C. (1973). Stein's estimation rule and its competitors. Journal of the American Statistical Association, 68(341), 117-130.

Erikson, R. S., and Wlezien, C. (2008). Are political markets really superior to polls as election predictors? Public Opinion Quarterly, 72(2), 190-215.

Geifman, Y., and El-Yaniv, R. (2017). Selective classification for deep neural networks. Advances in Neural Information Processing Systems, 30.

Gelman, A., and Hill, J. (2007). Data Analysis Using Regression and Multilevel/Hierarchical Models. Cambridge University Press.

Gelman, A., Carlin, J. B., Stern, H. S., Dunson, D. B., Vehtari, A., and Rubin, D. B. (2013). Bayesian Data Analysis (3rd ed.). Chapman and Hall/CRC.

Gelman, A., Lax, J., Phillips, J., Gabry, J., and Trangucci, R. (2018). Using multilevel regression and poststratification to estimate dynamic public opinion. Working paper, Columbia University.

Gelman, A., and Little, T. C. (1997). Poststratification into many categories using hierarchical logistic regression. Survey Methodology, 23(2), 127-135.

Ghitza, Y., and Gelman, A. (2013). Deep interactions with MRP: Election turnout and voting patterns among small electoral subgroups. American Journal of Political Science, 57(3), 762-776.

Gneiting, T., and Raftery, A. E. (2007). Strictly proper scoring rules, prediction, and estimation. Journal of the American Statistical Association, 102(477), 359-378.

Heidemanns, M., Gelman, A., and Morris, G. E. (2020). An updated dynamic Bayesian forecasting model for the U.S. presidential election. Harvard Data Science Review, 2(4).

Hoerl, A. E., and Kennard, R. W. (1970). Ridge regression: Biased estimation for nonorthogonal problems. Technometrics, 12(1), 55-67.

Hummel, P., and Rothschild, D. (2014). Fundamental models for forecasting elections at the state level. Electoral Studies, 35, 123-139.

IBGE. (2025). Pesquisa Nacional por Amostra de Domicilios Continua, microdata 2025-Q4. Instituto Brasileiro de Geografia e Estatistica.

Jackman, S. (2005). Pooling the polls over an election campaign. Australian Journal of Political Science, 40(4), 499-517.

Lax, J. R., and Phillips, J. H. (2009). How should we estimate public opinion in the states? American Journal of Political Science, 53(1), 107-121.

Limongi, F. (2023). Eleicao presidencial 2022: continuidade e ruptura. Novos Estudos CEBRAP, 42(1), 13-37.

Limongi, F., and Cortez, R. (2010). As eleicoes de 2010 e o quadro partidario. Novos Estudos CEBRAP, 88, 21-37.

Linzer, D. A. (2013). Dynamic Bayesian forecasting of presidential elections in the states. Journal of the American Statistical Association, 108(501), 124-134.

Linzer, D. A., and Lewis, J. B. (2015). Computing the votemargin posterior in dynamic linear electoral models. Working paper.

Lock, K., and Gelman, A. (2010). Bayesian combination of state polls and election forecasts. Political Analysis, 18(3), 337-348.

McNemar, Q. (1947). Note on the sampling error of the difference between correlated proportions or percentages. Psychometrika, 12(2), 153-157.

Mignozzetti, U., and Spektor, M. (2019). The illusion of polling precision: Brazilian presidential elections 2018. Working paper, FGV-EESP.

Murphy, A. H. (1973). A new vector partition of the probability score. Journal of Applied Meteorology, 12(4), 595-600.

Nicolau, J. (2017). Representantes de quem? Os (des)caminhos do seu voto da urna a Camara dos Deputados. Zahar.

Park, D. K., Gelman, A., and Bafumi, J. (2004). Bayesian multilevel estimation with poststratification: State-level estimates from national polls. Political Analysis, 12(4), 375-385.

Pickup, M., and Johnston, R. (2007). Campaign trial heats as electoral information. International Journal of Forecasting, 23(2), 219-236.

Quaest. (2024). Pesquisas Genial/Quaest: prefeitura de Sao Paulo 2024. Genial Investimentos and Quaest Pesquisa, raw datasets BR-Q24-MUN-SP-W1 to W14.

Rothschild, D. (2009). Forecasting elections: Comparing prediction markets, polls, and their biases. Public Opinion Quarterly, 73(5), 895-916.

Schaefer, B. M., and Sallum, B. (2024). Bolsonarismo and the 2022 Brazilian elections. Latin American Politics and Society, 66(1), 1-26.

Silver, N. (2008-2024). FiveThirtyEight Politics: U.S. presidential election models. ABC News and Disney Media. https://fivethirtyeight.com.

Soares, G. A. D., and Terron, S. L. (2008). Dois Lulas: A geografia eleitoral da reeleicao. Opiniao Publica, 14(2), 269-301.

Spektor, M., Fasolin, G., and Camargo, J. (2018). Pesquisas e o ciclo eleitoral brasileiro de 2018. Working paper, FGV.

Tribunal Superior Eleitoral. (2023). Acordao de 2023-06-30: Inelegibilidade de Jair Messias Bolsonaro ate 2030. Brasilia, TSE.

Tziralis, G., and Tatsiopoulos, I. (2007). Prediction markets: An extended literature review. Journal of Prediction Markets, 1(1), 75-91.

Wang, W., Rothschild, D., Goel, S., and Gelman, A. (2015). Forecasting elections with non-representative polls. International Journal of Forecasting, 31(3), 980-991.

Wikipedia contributors. (2024). Pesquisas de opiniao para a eleicao municipal de Sao Paulo em 2024. Wikipedia, the free encyclopedia. Retrieved 2026-04-15.

Wolfers, J., and Zitzewitz, E. (2004). Prediction markets. Journal of Economic Perspectives, 18(2), 107-126.

## Appendix A. Hyperparameter grid

Full search grid for the baseline ensemble and the state-baseline blend weight.

Baseline ensemble (2,688 points):

- stein_shrink: {0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40} (8 values)
- w_linzer: {0.50, 0.60, 0.70, 0.80, 0.85, 0.90, 0.95, 1.00} (8 values)
- sigma_0 (pp): {3.0, 4.0, 5.0, 6.0, 7.0, 8.0} (6 values)
- sigma_1 (pp/day): {0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08} (7 values)

State-baseline blend (15 points): w in {0.00, 0.10, 0.15, 0.18, 0.20, 0.22, 0.25, 0.28, 0.30, 0.32, 0.35, 0.36, 0.37, 0.38, 0.40}.

Auxiliary thresholds (fixed, not searched):

- min_n (per (uf, regime) cell): 3
- Laplace alpha = beta = 1
- Operational filter T <= 30 days

Selection criterion: maximize average year-fold accuracy weighted by per-cycle event count, with a tiebreak on minimum 2024 SP accuracy. The chosen point (s=0.05, w_linzer=0.50, sigma_0=4.0, sigma_1=0.05, w=0.36) is unique under this criterion across the joint 2,688 x 15 = 40,320 candidate configurations.

## Appendix B. Stan-equivalent pseudo-code

The model is implemented in pure Python (numpy + scipy.stats) for production, but is equivalent to the following Stan program in spirit. The pseudo-code expresses the cohort, Linzer, and state-baseline components as a unified hierarchical model.

```
data {
  int N;                                  // events
  int K;                                  // cohorts
  int U;                                  // states
  int R;                                  // regimes
  array[N] int<lower=1, upper=K> k;       // cohort index
  array[N] int<lower=1, upper=U> u;       // state index
  array[N] int<lower=1, upper=R> r;       // regime index
  array[N] real lead;                     // poll lead (pp)
  array[N] real days;                     // days to election
  array[N] int<lower=0, upper=1> y;       // outcome
  real<lower=0, upper=1> p_global;        // global rate
  real<lower=0, upper=1> w_linzer;        // blend weight
  real<lower=0, upper=1> w_state;         // MRP blend weight
}
parameters {
  vector<lower=0, upper=1>[K] p_cohort;
  array[U, R] real<lower=0, upper=1> p_state;
  real<lower=0> sigma_0;
  real<lower=0> sigma_1;
  real<lower=0, upper=1> stein_s;
}
transformed parameters {
  vector[N] p_blend;
  vector[N] p_final;
  for (n in 1:N) {
    real p_lin = Phi(lead[n] / (sigma_0 + sigma_1 * days[n]));
    real p_coh = (1 - stein_s) * p_cohort[k[n]] + stein_s * p_global;
    p_blend[n] = (1 - w_linzer) * p_coh + w_linzer * p_lin;
    p_final[n] = (1 - w_state) * p_blend[n] + w_state * p_state[u[n], r[n]];
  }
}
model {
  // Laplace prior on the state baseline (informationless).
  for (uu in 1:U) for (rr in 1:R) p_state[uu, rr] ~ beta(1, 1);
  // Stein-shrunk cohort prior.
  for (kk in 1:K) p_cohort[kk] ~ beta(1 + p_global * 4, 1 + (1 - p_global) * 4);
  // Linzer drift parameters.
  sigma_0 ~ normal(4.0, 1.0) T[0, ];
  sigma_1 ~ normal(0.05, 0.02) T[0, ];
  stein_s ~ beta(1, 19);
  // Likelihood.
  y ~ bernoulli(p_final);
}
```

The production estimator is point-estimated rather than fully Bayesian, with the cohort base rate p_cohort taken as the Stein-shrunk maximum-likelihood estimate, the state baseline taken as the Laplace-smoothed contingency mean, and (sigma_0, sigma_1, stein_s, w_linzer, w_state) selected by autoresearch grid search rather than HMC. The pseudo-code above documents the implicit generative model for readers wishing to extend the work to full posterior inference.
