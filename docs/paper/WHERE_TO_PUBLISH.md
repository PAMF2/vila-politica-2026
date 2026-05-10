# Where to Publish — Venue Decision Guide

This document ranks publication venues for the manuscript "State-Level
Empirical-Bayes Priors Recover Industry-Wide Polling Failures: Cross-Country
Evidence from Twelve Cycles" and recommends a submission sequence.

## TL;DR

**Primary target:** Political Analysis (Cambridge).
**Secondary target if rejected:** International Journal of Forecasting (Elsevier) → AOAS (IMS).
**Pre-print first:** arXiv stat.AP cross-listed to econ.EM and stat.ME.

Total expected timeline from submission to acceptance: 3-9 months.

## Paper character — what we are submitting

- **Method type:** ensemble blend of cohort empirical Bayes + closed-form
  Linzer DLM + Laplace-smoothed (state, regime) MRP-style prior.
- **Theoretical novelty:** moderate. The state-baseline component is a
  ridge-regression dual; Stein shrinkage is textbook. The novelty is the
  blend formula plus the leak-safe protocol.
- **Empirical contribution:** strong. 394-event Brazilian core, 12 cycles
  / 11 additional countries / 6,954 cross-country events. 12-model
  benchmark on identical year-fold protocol. 8 robustness experiments.
  Statistical significance via DM + McNemar + 1,000-sample permutation.
- **Substantive domain:** Brazilian electoral forecasting; cross-country
  generalization to US, UK, FR, DE, MX, TR, IT, IN, AR.
- **Reproducibility:** MIT-licensed code, two pre-registration tags
  (v1.2-prereg, v1.3-prereg), Docker container, Makefile end-to-end in
  three minutes.

## Venue ranking

| Rank | Venue                                  | Match | IF   | Time to first decision | Reviewer pool                  | Risk profile |
|-----:|:---------------------------------------|:-----:|-----:|:-----------------------|:--------------------------------|:-------------|
| 1    | Political Analysis (Cambridge)         | ★★★★★ | 4.8  | 8-12 weeks             | PolMeth + MRP literature        | Low          |
| 2    | International Journal of Forecasting   | ★★★★  | 7.9  | 6-10 weeks             | Forecasting methodology         | Med          |
| 3    | Annals of Applied Statistics (IMS)     | ★★★★  | 1.8  | 12-16 weeks            | Applied stats with substantive  | Med-high     |
| 4    | JRSS Series A (Statistics in Society)  | ★★★★  | 1.9  | 12-20 weeks            | Stats with societal application | Med-high     |
| 5    | Public Opinion Quarterly (Oxford)      | ★★★★  | 3.4  | 8-12 weeks             | Survey methodology              | Med          |
| 6    | JASA Applications and Case Studies     | ★★★   | 4.4  | 16-24 weeks            | Statistical theory + apps       | High         |
| 7    | Electoral Studies (Elsevier)           | ★★★   | 2.5  | 6 weeks                | Electoral behavior              | Low          |
| 8    | PS: Political Science and Politics     | ★★★   | 2.0  | 8-12 weeks             | PolMeth forecasting symposiums  | Low (if cut) |

Match score reflects fit between the paper's character and the venue's
typical content. Risk reflects probability of rejection on first round.

## Why Political Analysis first

1. **Direct precedent**. The MRP literature this paper extends is
   primarily published in PA: Park, Gelman and Bafumi (2004); Lax and
   Phillips (2009); Buttice and Highton (2013); Lock and Gelman (2010).
   PA's editorial board recognizes the methodological frame immediately.

2. **Reviewer pool overlap**. The paper's §2.2 cites at least seven
   PA-published works; the journal's pool of MRP-trained reviewers is
   the most concentrated.

3. **Replication archive policy**. PA requires public replication
   archives with DOI. Our Zenodo + GitHub plan is compatible with no
   modification.

4. **Format compatibility**. Cambridge Medium template
   (`cup-journal.cls`) is already applied in `build_paper_pdf.py` CSS;
   `build_paper_tex.py` produces a PA-ready LaTeX manuscript.

5. **Citation reach**. Methodological forecasting work in PA is cited
   by every subsequent state-level model (Silver via FiveThirtyEight,
   Heidemanns / Gelman / Morris via The Economist, YouGov MRP).

## Why International Journal of Forecasting second

1. **Higher impact factor** (7.9 vs PA's 4.8) and faster decision cycle
   (6-10 weeks vs 8-12).

2. **Forecasting methodology focus**. Linzer (2013) is published in
   JASA but Linzer and Lewis-Beck (2015), Hummel and Rothschild
   (2014), Wang et al. (2015), and Graefe (2014) are all in IJF
   or its sibling Public Opinion Quarterly.

3. **Cross-country replication welcomed**. IJF actively publishes
   cross-national forecasting studies; the 12-cycle / 11-country
   appendix is a positive signal there.

4. **Drawback**. IJF reviewers may push for continuous vote-share
   prediction in addition to binary win-probability output. The
   architecture supports this (Linzer component is continuous already)
   but the paper does not currently report MAE on vote-share. Adding
   §5.7 with vote-share MAE would be the natural revision response.

## Why Annals of Applied Statistics third

1. **Statistics venue with substantive applied work**. Hummel and
   Rothschild (2014) published in Electoral Studies, but methodologically
   similar empirical-Bayes work goes to AOAS (e.g. Brown 2008 on
   season-trajectory baseball forecasting; Liu, Gelman and Zheng 2014
   on multilevel poll modeling).

2. **Drawback**. AOAS reviewers tend to ask for theoretical contribution
   (e.g. asymptotic properties of state-baseline shrinkage, finite-sample
   bounds on the blend weight $w$). Our closed-form is intentionally
   simple and the theoretical contribution is moderate. A first-round
   "minor revisions" with a request for one theorem is plausible.

## Why JRSS-A fourth

JRSS-A "Statistics in Society" is the canonical Royal Statistical
Society venue for societal-application stats. Electoral forecasting
across 12 cycles in 11 countries with industry failure-mode analysis
fits its mission. Same theoretical-contribution risk as AOAS, but with
slightly better tolerance for applied empirical work without theorems.

## Pre-print: always arXiv first

**Submit arXiv before any journal submission.** Reasons:

1. Stake the claim publicly with a citable preprint identifier.
2. arXiv submission does not count as prior publication for any
   target journal.
3. PA, IJF, AOAS, JRSS-A all explicitly allow arXiv preprints.
4. arXiv ID can be inserted into the paper's title-page footnote
   before journal submission, signalling the work is already in the
   public record.

**arXiv categories:**
- Primary: `stat.AP` (statistics applications)
- Cross-list: `econ.EM` (econometrics), `stat.ME` (statistical
  methodology), `cs.LG` (machine learning, optional - benchmark
  has ML baselines)

## Decision tree

```
Day 1:    Mint Zenodo DOI for replication archive.
Day 2:    Submit to arXiv. Wait 24h for moderation.
Day 3:    Add arXiv ID to PAPER.md title footnote, rebuild PDF.
Day 4-7:  Submit to Political Analysis via ScholarOne.
            └─ Decision in 8-12 weeks.
              ├─ Accept / minor revisions: revise, accept, publish.
              └─ Reject:
                  ├─ Reason "wrong venue" → submit to IJF (1 week prep).
                  ├─ Reason "needs more theory" → submit to AOAS or JRSS-A
                  │   after adding one theoretical extension (e.g.
                  │   asymptotic distribution of state-baseline estimator).
                  └─ Reason "rigor insufficient" → triage reviewer
                      comments, revise, resubmit to IJF.
```

## Cover-letter template (Political Analysis)

```
Dear Editor,

I am pleased to submit "State-Level Empirical-Bayes Priors Recover
Industry-Wide Polling Failures: Cross-Country Evidence from Twelve
Cycles" for consideration in Political Analysis.

The paper documents a closed-form ensemble that absorbs cycle-specific
industry-wide polling bias by blending a partisan-regime-conditional
state baseline with a Linzer dynamic linear model and a cohort
empirical-Bayes estimator. On the 2024 Sao Paulo mayoral race - where
every major Brazilian polling firm placed Boulos ahead of incumbent
Nunes, who won by approximately three points - the architecture
recovers fold accuracy from 73.53% to 89.71% under leak-safe year-fold
cross-validation. The aggregate Brazilian core gain (97.21% vs 91.88%
within-config baseline) is significant under Diebold-Mariano, McNemar,
and a 1,000-sample pair-preserving permutation test. We replicate the
leak-safe protocol on twelve cross-country cycles spanning eleven
additional countries (n=6,954); Argentina 2023 corroborates the
Brazilian finding on a cycle that polls and prediction markets jointly
missed.

The contribution sits squarely within the Political Analysis MRP
tradition (Park, Gelman, Bafumi 2004; Buttice, Highton 2013; Lock,
Gelman 2010). The architecture is closed-form and reproducible end to
end in three minutes on commodity hardware; replication materials are
archived on Zenodo at DOI [TO BE FILLED].

This work has not been submitted elsewhere and is not under
consideration at any other journal. A preprint is available at arXiv
[TO BE FILLED].

The authors have a competing-interests disclosure: we are co-founders
of Vila INTEIA, which operates a non-commercial public-facing
forecasting product based on the v1.3 architecture. The product is
released under MIT license alongside the paper.

Suggested reviewers (none of whom are co-authors or close collaborators):
- [Name 1, affiliation, expertise]
- [Name 2, affiliation, expertise]
- [Name 3, affiliation, expertise]
- [Name 4, affiliation, expertise]
- [Name 5, affiliation, expertise]

Sincerely,
Pedro Afonso Malheiros and Igor Morais Vasconcelos
```

## Suggested reviewers — concrete names by venue

For Political Analysis:
- **Andrew Gelman** (Columbia, Statistics + Political Science) - MRP
  inventor, would recognize the framing immediately.
- **Drew Linzer** (Civis Analytics, formerly Emory) - Linzer 2013 is
  cited as the lead-driven baseline.
- **Christopher Wlezien** (UT Austin, Government) - timeline-of-elections
  expert; cited in §2.1.
- **Andreas Graefe** (Macromedia University Munich) - PollyVote
  ensemble combiner; cited in §6.9.
- **Patrick Hummel** (Google) - state-level forecasting;
  Hummel/Rothschild 2014 cited.

For IJF:
- Add **Justin Wolfers** (Michigan) - prediction-markets economics;
  cited in §6.9.
- Add **Andre Murr** (Manchester) - citizen-forecasting empirics;
  cited in §6.9.

For AOAS / JRSS-A:
- Substitute Gelman with **Persi Diaconis** or **Jasper Snoek**
  (Bayesian methodology generalists).
- Add **Susan Murphy** (Harvard) - if pivoting toward methodological
  generalization.

## Avoid these venues

- **Nature / Science / PNAS** - top-tier general-science venues require
  broader societal claims and crisper single-finding framing than this
  multi-experiment methodology paper.
- **NeurIPS / ICML** - ML venues expect deep-learning baselines or
  theoretical guarantees; closed-form ensemble would read as
  insufficiently novel.
- **Econometrica / JoE** - too theoretical for our applied focus.
- **AJPS / APSR** - too political-substantive; methodology depth would
  be cut as a side issue.

## Pre-submission gate (do not submit before these are TRUE)

- [ ] arXiv ID minted and embedded in PAPER.md title footnote.
- [ ] Zenodo DOI minted for replication archive.
- [ ] Real ORCIDs (not the placeholder zeros) in the author block.
- [ ] All `[TO BE FILLED]` cover-letter placeholders resolved.
- [ ] PDF compiles via both `weasyprint` and `pdflatex`.
- [ ] `make smoke` returns 29/29.
- [ ] `make reproduce-fast` runs end-to-end without errors.
- [ ] Repository tagged `v1.3-submission` to anchor the as-submitted state.
- [ ] All 5 suggested reviewers contacted off-record (optional but
      reduces risk of editor assigning a known critic).

## What to do if all venues reject

Unlikely given the paper's empirical strength, but a fallback chain:

1. Re-target: **Political Behavior** (Springer) or **Electoral Studies**
   for a more applied framing.
2. Re-target: **Journal of the Royal Statistical Society Series C
   (Applied Statistics)** for an applied-stats framing.
3. Permanently archive: **Open Forum for Election Forecasting** (an
   open-access OSF venue) - low impact but stable DOI and citable.
4. Re-frame as a software-tool paper for **Journal of Statistical
   Software** focusing on the MIT-licensed pipeline.

The probability of all four primary venues rejecting on rigor grounds
is low given the experimental scope; most rejections at this scope are
"wrong venue" rather than "wrong work."

## Last word

Pick one venue, submit, wait. Do not multi-submit. PA first because
match is best; IJF second because timeline is shorter and IF is higher;
stats venues third only if both PolSci venues reject for reason that
suggests stats audience would receive better.
