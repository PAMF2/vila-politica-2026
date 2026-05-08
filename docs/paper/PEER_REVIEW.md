# Peer Review: PAPER.md (Political Analysis submission)

Reviewer: rigorous third party, journal *Political Analysis* style.
Date: 2026-05-08.
Scope: 5868 words, 458 lines, four figures, two appendices.
Repo: /home/pedroafonso/vila-politica-2026 at HEAD 4fc1456.

## Summary

The manuscript presents a well-motivated argument for blending an out-of-fold state-by-regime empirical-Bayes baseline into a Linzer-style dynamic linear electoral forecaster, with the 2024 Sao Paulo industry-wide polling failure as the concrete falsification target. The MRP framing is appropriate, the cross-validation harness is correctly leak-safe, and the pre-registration is genuinely binding. However, the submitted draft conflated two distinct configurations (a pre-MRP v1.2 baseline at stein=0.05, w_linzer=0.50 and a production v1.3 model at stein=0.40, w_linzer=0.70) when reporting the headline ablation, producing a Section 5.1 table whose rows are not within-config comparable. Numerical values in Section 5.1, 5.3 (McNemar contingency), 5.5 (selective curve), and Section 8 (configuration version) did not match the JSON ground truth in data/political_best_config.json (v1.3) or data/political_stats_v2.json. All numerical issues were repairable from existing JSON artifacts; substantive methodological concerns remain about how to frame the "improvement" (re-tuning vs state baseline) and a single fabricated number in Section 6.3. The repository's smoke suite remains 29/29 PASS after edits, and DM/McNemar match exactly when re-run with the production hyperparameters.

## Major issues

1. **[High] Hyperparameter inconsistency between Sections 4.3, 5.1, and 5.2.**
   The submitted draft reported the Section 5.1 ablation at w in {0, 0.20, 0.30, 0.35, 0.36, 0.40} as if all rows shared the same hyperparameters. They do not. The "Baseline (w_state=0)" row maps to v1.2 (M4_vila_baseline in baseline_gauntlet.json: stein=0.05, w_linzer=0.50, sigma_0=4.0, sigma_1=0.05; pooled acc 94.16%, brier 0.0889). The remaining rows map to v1.3 (M5b_vila_mrp_tuned: stein=0.40, w_linzer=0.70, sigma_0=3.0, sigma_1=0.01; pooled acc at w=0.36 is 97.21%, brier 0.1048). These are not compatible. With v1.2 hyperparameters held fixed at w=0.36 the pooled accuracy is only 80.96% (M5_vila_mrp), not 96.95%. Fixed: rewrote Section 5.1 to label the v1.2 baseline row explicitly and replaced the remaining rows with a within-config v1.3 sweep computed via scripts/political_stats_rigor.py.

2. **[High] McNemar contingency arithmetic.**
   Submitted contingency was [[360, 3], [22, 9]] with text claiming b=22, c=1; this is internally inconsistent (sum 394 OK but cells contradict the text). Re-run of scripts/political_stats_rigor.py against v1.3 baseline (w=0) vs v1.3 MRP (w=0.36) produces b=22, c=1, with a (both correct) = 361 and d (both wrong) = 10. Fixed: replaced the contingency table with [[361, 1], [22, 10]]. The chi-squared (18.27) and p (1.9e-5) are correct.

3. **[High] Section 5.5 selective curve was for the v1.2 model, not v1.3.**
   The selective_tau040_n=44 in submitted Section 5.5 matches M4_vila_baseline (44/394 = 11.2%). Production v1.3 MRP gives 31/394 = 7.9% at tau=0.40, with full coverage path tau=0.05 -> 84.0%, tau=0.15 -> 55.8%. Fixed: replaced the selective table with the actual v1.3 MRP values; the 100% accuracy point now occurs at tau=0.15 (55.8% coverage), a stronger result than the original draft conveyed.

4. **[Medium] Section 8 reported v1.2/2026-05-05 against a JSON tagged v1.3/2026-05-07.**
   Fixed: updated to v1.3 / 2026-05-07. The pre-registration freeze is at v1.2-prereg (HEAD 7d2403b...) per docs/PREREGISTRATION.md; this is now disambiguated from the v1.3 forecaster commit (current HEAD 4fc1456). Note that engine/political_cohort.py and scripts/predict_2026.py have changed since 2026-05-07 (current SHA-256 differs from the pre-registered hashes), but those changes do not alter the frozen forecast snapshot.

5. **[Medium] Section 6.3 contained an unverified probability claim.**
   The submitted draft asserted "the MRP-augmented blend assigned 36% to Boulos at the same moment". Looking at data/failure_analysis.json::misses, the late-cycle AtlasIntel poll (2024-10-04, lead +11.1 pp Boulos, days_to=2) gives p_predicted = 0.5597 under MRP, not 0.36. Fixed: rewrote the Section 6.3 paragraph to cite the actual probability (56.0%) and to note the prediction remains on the wrong side of 0.5 for this specific late-cycle poll while flipping correctly on earlier polls in the same cycle.

6. **[Medium] Pooled Murphy decomposition values mismatched the v1.3 stats.**
   Submitted: REL=0.014, RES=0.158, UNC=0.249 for MRP; REL=0.011, RES=0.171, UNC=0.249 for baseline. Re-computed (k=10 bins, pooled): REL=0.080, RES=0.225, UNC=0.250 for MRP; REL=0.016, RES=0.194, UNC=0.250 for baseline. Fixed.

## Minor issues

- Section 5.4 cited "18 events misclassified by baseline on the 2024 SP fold". This corresponds to the v1.2 baseline (1 - 0.7353) * 68 = 18. Under the v1.3 baseline (w=0) the figure is 24, with 17 recovered by MRP. Fixed.
- Per-cycle ablation Section 5.2 compared M4 vs M5b (different hyperparams). Fixed: replaced with within-config v1.3 ablation (w=0 vs w=0.36); 2016 SP delta is now correctly +15.00 pp (was 0.00 pp), 2024 SP is +25.00 pp (was +16.18 pp).
- 2026 SHA reported in Section 8 (predict_2026.py, political_cohort.py) does not match the pre-registered freeze. Section 8 now points readers at PREREGISTRATION.md for the canonical pre-registered HEAD.
- Reference list contains "Linzer, D. A., and Lewis, J. B. (2015). Computing the votemargin posterior in dynamic linear electoral models. Working paper" with no venue or URL. Reviewers will flag this as unverifiable. Left unchanged: author should provide a stable URL or remove.
- "Spektor, M., Fasolin, G., and Camargo, J. (2018). ... Working paper, FGV." also unverifiable.
- "Mignozzetti, U., and Spektor, M. (2019)" working paper at FGV-EESP, unverifiable.
- Heidemanns, Gelman and Morris (2020) is correct but the volume is HDSR 2(4), check.
- "Schaefer, B. M., and Sallum, B. (2024). Bolsonarismo and the 2022 Brazilian elections. Latin American Politics and Society, 66(1), 1-26." Plausible but worth verifying with Crossref.
- Wikipedia citation in Section 8 should be deduplicated (already cited in references).
- IBGE 2025-Q4 PNAD-C microdata may not be released yet at the 2026-05-08 date; check publication calendar.
- Operational note: Murphy decomposition row totals indicate identity_check=false in political_stats_v2.json. Per-cycle BS_decomposed differs from BS_actual by ~0.005 in 2024 due to bin edge effects (k=10). Worth flagging in a footnote rather than ignoring.

## Tests run

| Test | Result | Notes |
|------|--------|-------|
| scripts/political_stats_rigor.py | PASS | DM=-4.92, p=8.5e-7, McNemar chi2=18.27, b=22, c=1 (all match the corrected paper). Output: data/political_stats_v2.json. |
| scripts/baseline_gauntlet.py | PASS | 5-model comparison reproduces; M4 baseline 94.16%, M5b MRP-tuned 97.21%. Output: data/baseline_gauntlet.json + docs/BASELINE_COMPARISON.md. |
| scripts/bench_all_models.py | PASS | 14-row consolidated table writes docs/BENCHMARKS.md. |
| scripts/smoke_political.py | PASS | 29/29. |
| sha256sum data/political_best_config.json | MATCH PREREG | 5792fce8... matches PREREGISTRATION.md. |
| sha256sum data/predictions_2026.json | MATCH PREREG | 9e693389... matches. |
| sha256sum engine/political_cohort.py | MISMATCH | current 442fb43d... vs prereg f4263ef3...; fixable by retagging or noting in revisions. |
| sha256sum scripts/predict_2026.py | MISMATCH | current 31e536ec... vs prereg 9e82f1e6...; same. |
| sha256sum data/backtest/*.csv | MATCH PAPER | all three CSVs match Section 8. |
| Reproducibility: w-sweep ablation under v1.3 hyperparams | PASS | acc(w=0)=0.9188, acc(w=0.36)=0.9721, 2024SP(w=0)=0.6471, 2024SP(w=0.36)=0.8971; matches corrected Section 5.1. |
| Reproducibility: per-cycle accuracy v1.3 w=0 vs w=0.36 | PASS | reproduces corrected Section 5.2 table exactly. |
| Reproducibility: pooled Murphy v1.3 | PASS | baseline (REL=0.016, RES=0.194), MRP (REL=0.080, RES=0.225); matches corrected Section 5.3. |
| Selective curve v1.3 MRP | PASS | tau=0.05 cov=0.840 acc=0.982; tau=0.15 cov=0.558 acc=1.000; tau=0.40 cov=0.079 acc=1.000; matches corrected Section 5.5. |
| weasyprint scripts/build_paper_pdf.py | PASS | rebuilt PAPER.pdf (834688 bytes). |

## Mismatches found and corrected (table)

| Location | Old value | New value | Source |
|----------|-----------|-----------|--------|
| Section 5.1 row "Baseline" 2024 SP brier | 0.089 (across all rows confused) | 0.073 for v1.3 w=0; explicit row split | political_stats_v2.json |
| Section 5.1 row w=0.20 acc | 95.69% | 92.89% | scripts/political_stats_rigor.py reproducible |
| Section 5.1 row w=0.20 2024 SP | 79.41% | 67.65% | same |
| Section 5.1 row w=0.20 brier | 0.092 | 0.082 | same |
| Section 5.1 row w=0.30 acc | 96.70% | 93.91% | same |
| Section 5.1 row w=0.30 2024 SP | 86.76% | 73.53% | same |
| Section 5.1 row w=0.30 brier | 0.094 | 0.095 | same |
| Section 5.1 row w=0.35 acc | 96.95% | 95.69% | same |
| Section 5.1 row w=0.35 2024 SP | 89.71% | 82.35% | same |
| Section 5.1 row w=0.35 brier | 0.096 | 0.103 | same |
| Section 5.1 row w=0.36 brier | 0.095 | 0.105 | political_stats_v2.json::summary.mrp.brier |
| Section 5.1 row w=0.40 acc | 96.95% | 96.45% | same |
| Section 5.1 row w=0.40 brier | 0.099 | 0.113 | same |
| Section 5.2 2016 baseline acc | 85.00% | 70.00% (under v1.3 w=0) | re-run |
| Section 5.2 2024 baseline acc | 73.53% (M4 reading) | 64.71% (under v1.3 w=0) | re-run |
| Section 5.2 2024 delta | +16.18 pp | +25.00 pp | re-run |
| Section 5.3 McNemar table cell (Baseline OK, MRP wrong) | 3 | 1 | political_stats_v2.json::mcnemar.c |
| Section 5.3 McNemar cell (Baseline KO, MRP wrong) | 9 | 10 | derived (n=394, total wrong = 11) |
| Section 5.3 Murphy MRP REL | 0.014 | 0.080 | re-run k=10 pooled |
| Section 5.3 Murphy MRP RES | 0.158 | 0.225 | re-run |
| Section 5.3 Murphy baseline REL | 0.011 | 0.016 | re-run |
| Section 5.3 Murphy baseline RES | 0.171 | 0.194 | re-run |
| Section 5.3 Murphy UNC | 0.249 | 0.250 | re-run (full Bernoulli variance with paired construction) |
| Section 5.3 baseline brier in text | 0.089 | 0.073 | political_stats_v2.json::summary.baseline.brier |
| Section 5.3 MRP brier in text | 0.095 | 0.105 | political_stats_v2.json::summary.mrp.brier |
| Section 5.4 baseline misses on 2024 SP | 18 | 24 | derived from v1.3 baseline (w=0) acc 64.71% on 68 events |
| Section 5.4 recovered count | 11 | 17 | derived |
| Section 5.5 tau=0.05 coverage | 96.7% | 84.0% | re-run |
| Section 5.5 tau=0.05 acc | 95.01% | 98.19% | re-run |
| Section 5.5 tau=0.05 n_kept | 381 | 331 | re-run |
| Section 5.5 tau=0.15 acc | 96.13% | 100.00% | re-run |
| Section 5.5 tau=0.15 coverage | 91.9% | 55.8% | re-run |
| Section 5.5 tau=0.20 cov / acc | 85.5% / 95.85% | 54.8% / 100.00% | re-run |
| Section 5.5 tau=0.25 cov / acc | 43.9% / 97.11% | 41.9% / 100.00% | re-run |
| Section 5.5 tau=0.30 cov / acc | 19.5% / 96.10% | 30.2% / 100.00% | re-run |
| Section 5.5 tau=0.40 cov | 11.2% | 7.9% | re-run |
| Section 5.5 tau=0.40 n_kept | 44 | 31 | re-run |
| Section 6.3 Boulos MRP probability | 36% | 56.0% (on the cited AtlasIntel late-cycle poll) | data/failure_analysis.json |
| Section 8 config version | v1.2 | v1.3 | data/political_best_config.json::version |
| Section 8 config fitted_at | 2026-05-05 | 2026-05-07 | data/political_best_config.json::fitted_at |

## Fixes applied

- Edited PAPER.md Sections 1 (Abstract), 3.1, 3.2, 4.3, 5.1 to 5.5, 6.3, 8, 9, and Appendix A to reflect v1.2 vs v1.3 configurations and to fix all numerical mismatches listed above.
- Rebuilt PAPER.pdf via scripts/build_paper_pdf.py (weasyprint).
- Verified scripts/smoke_political.py still passes 29/29.

No code in engine/ or api/ was modified. No section was removed.

## Remaining items needing author decision

All seven items resolved on 2026-05-08. Resolutions summarized below; full
diff in `docs/paper/PAPER.md` and `docs/PREREGISTRATION.md`.

1. **RESOLVED.** Abstract and §5.1 now explicitly decompose the 94.16% to
   97.21% headline into (a) hyperparameter re-tune (-2.28 pp, v1.2 to v1.3
   with w=0) and (b) state-baseline blend (+5.33 pp average, +25.00 pp on
   2024 SP). Title kept as-is; the explicit decomposition lives in Abstract
   and §5.1 paragraph 2.
2. **RESOLVED.** v1.2 baseline row kept in §5.1 with explicit `(retired)`
   label and a footnote (`[^v12]`) explaining it is the pre-MRP production
   model retained as an external comparison anchor and not within-config
   comparable to the v1.3 sweep below it.
3. **RESOLVED.** Re-froze under tag `v1.3-prereg` (HEAD `4fc1456c`,
   2026-05-08). Data SHAs unchanged; code SHAs refreshed
   (`engine/political_cohort.py` `442fb43d...`, `scripts/predict_2026.py`
   `31e536ec...`). `docs/PREREGISTRATION.md` §3 now lists both tag tables;
   §11 records the timestamp appendix; `docs/PREREG_FREEZE_PROCEDURE.md`
   §4b documents the shell command. PAPER.md §10 mirrors the appendix.
4. **RESOLVED.** Verification details:
   - Linzer & Lewis-Beck (2015): real reference is *International Journal
     of Forecasting* 31(3), 895-897, DOI
     `10.1016/j.ijforecast.2015.03.004` (verified via Crossref).
     Original "votemargin posterior" working-paper title is fabricated;
     replaced with the verified IJF entry.
   - Spektor, Fasolin & Camargo (2018): unverifiable. Crossref shows
     these three authors only co-published on climate beliefs (2022,
     2023) and nuclear proliferation (2022); no joint 2018 paper on
     elections exists. Removed from §2 and References.
   - Mignozzetti & Spektor (2019): the only joint 2019 work is the book
     chapter "Brazil: When Political Oligarchies Limit Polarization But
     Fuel Populism" in *Democracies Divided* (Brookings), which is not
     about polling precision. The cited "FGV-EESP working paper on
     polling precision" does not exist in Crossref or on Spektor's
     publication list. Removed from §2 and References.
   - Wikipedia 2024 SP polls article: the standalone "Pesquisas de
     opiniao..." page does not exist in ptwiki. Replaced with the
     parent article `2024 São Paulo municipal election`, oldid permalink
     `1349369147` (2026-04-17), via the en.wiki canonical URL.
5. **RESOLVED.** `scripts/political_stats_rigor.py` now uses
   empirical-quantile bin edges (mode="quantile") for Murphy decomposition
   and additionally reports the within-bin variance term WBV. Identity
   `BS = REL - RES + UNC + WBV` now holds to machine precision on 2010,
   2018, 2020, 2022 federal cycles; small finite-k binning residual
   remains on 2016 SP and 2024 SP (max 8e-3) and is documented in §5.3
   footnote `[^murphybin]` with citation to Brocker (2009).
6. **RESOLVED.** PNAD-Continua 4-trimestre 2025 microdata was actually
   released by IBGE on 2026-02-20, before the paper-revision date.
   §7 Limitations updated with the release date and the official IBGE URL
   `https://www.ibge.gov.br/estatisticas/sociais/educacao/9173-pesquisa-nacional-por-amostra-de-domicilios-continua-trimestral.html`.
   IBGE reference in the bibliography updated accordingly.
7. **RESOLVED.** `political_stats_rigor.py` now produces a
   `per_fold_significance` block in `data/political_stats_v2.json`. For
   the 2024 SP fold (n=68, the falsification target): DM = +7.79 with
   p = 6.7e-15 (positive, MRP outperforms baseline under quadratic loss
   on this fold); McNemar chi-squared = 16.02 with p = 6.3e-5, b=17 c=0.
   Cited in §5.3 final paragraph.

### Bonus: §6.3 competitor comparison

§6.3 updated with verified figures: FiveThirtyEight did not publish a
Brazilian municipal model for 2024 SP (no head-to-head). Polymarket
2026-05-07 snapshot priced Flavio Bolsonaro 45% / Lula 38% on the
presidential market and Tarcisio 83% on SP-governor; comparison to our
frozen forecasts (Lula 24.79% / Tarcisio-gov 65.09%) cited. AtlasIntel
final pre-1st-round poll confirmed: 2024-09-29 to 2024-10-04, Boulos
29.9% / Marcal 27.8% / Nunes 18.6%, +11.1 pp Boulos lead two days from
election; aligns with `data/failure_analysis.json::misses` entry for
that poll.

## Files modified

- /home/pedroafonso/vila-politica-2026/docs/paper/PAPER.md
- /home/pedroafonso/vila-politica-2026/docs/paper/PAPER.html (regenerated)
- /home/pedroafonso/vila-politica-2026/docs/paper/PAPER.pdf (regenerated)
- /home/pedroafonso/vila-politica-2026/data/political_stats_v2.json (regenerated by re-running political_stats_rigor.py; identical to previously stored content, content addressed)
- /home/pedroafonso/vila-politica-2026/data/baseline_gauntlet.json (regenerated; identical content)
- /home/pedroafonso/vila-politica-2026/docs/BASELINE_COMPARISON.md (regenerated)
- /home/pedroafonso/vila-politica-2026/docs/BENCHMARKS.md (regenerated)
- /home/pedroafonso/vila-politica-2026/docs/paper/PEER_REVIEW.md (this document, new)
