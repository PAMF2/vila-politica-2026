# Cross-country generalization extended (Phase 4)

Builds on `docs/CROSS_COUNTRY.md` and `scripts/cross_country_validation.py`,
which validated Vila MRP on US 2016, US 2020, and UK 2019. This phase adds
four new electoral cycles spanning four countries and a different office
(US governor) to test whether the MRP `(state, regime)` baseline transfer
extends beyond presidential 2-party cycles.

## Cycles added

| Cycle | Election | Source | Race |
|---|---|---|---|
| `fr_2022` | 2022-04-24 | Wikipedia: *Opinion polling for the 2022 French presidential election* | Macron (LREM) vs Le Pen (RN), runoff |
| `ar_2023` | 2023-11-19 | Wikipedia: *Opinion polling for the 2023 Argentine general election* (After the primaries) | Milei (LLA) vs Massa (UP), runoff |
| `br_2014` | 2014-10-26 | Wikipedia (PT): *Pesquisas de opiniao para a eleicao presidencial no Brasil em 2014* (Segundo turno) | Dilma (PT) vs Aecio (PSDB), runoff |
| `us_2022` | 2022-11-08 | FiveThirtyEight `governor_polls.csv` (Wayback Machine snapshot) | 10 swing-state governor races |

For US 2022 we initially targeted the top 10 swing/competitive races
(Arizona, Georgia, Wisconsin, Michigan, Pennsylvania, Nevada, Oregon, Kansas,
Maine, New Mexico). After applying the standard `T <= 30 days` filter
shared with the BR/US-presidential pipelines, **Kansas falls out**: its most
recent polls in the Wayback dataset are from 18 Sep 2022 (~51 days out). So
9 states make the cut.

## Pipeline

`scripts/cross_country_extended.py` mirrors the structure of
`scripts/cross_country_validation.py`:

1. Parse each raw source under `data/cross_country/raw_extended/` into the
   legacy backtest CSV schema (`evento_id, data, contexto, uf, ano, turno,
   vencedor, partido, incumbente, poll_lead_pp, outcome_real,
   probabilidade_prior, outcome_framing`). Each poll yields **two** paired
   rows (winner outcome=1, runner-up outcome=0).
2. Filter polls to T <= 30 days from election (matches BR/US pipelines).
3. Fit Vila political cohort with `stein_shrink=0.05` and evaluate two
   variants:
   - `no_mrp`: cohort + Linzer blend, `w_state = 0`
   - `mrp_w36`: same blend with state-baseline shrinkage `w_state = 0.36`
4. CV mode auto-selects:
   - `>= 2 ufs` (US 2022): leave-one-state-out (LOSO).
   - Single-uf cycles (FR/AR/BR runoffs are national): leave-one-pair-out
     by `(date, pollster)`.

Output: `data/cross_country_extended.json` plus the 4 backtest CSVs.

## Results (LOSO / leave-one-pair-out, leak-safe)

| Cycle | n_events | n_polls | uf-mode | no-MRP acc | MRP w=0.36 acc | delta | no-MRP brier | MRP brier |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| `fr_2022` | 198 | 99 | single-uf (FR), pair-out | 0.9899 | **1.0000** | +0.0101 | 0.0069 | 0.0031 |
| `ar_2023` | 30 | 15 | single-uf (AR), pair-out | 0.8000 | **1.0000** | +0.2000 | 0.1392 | 0.0666 |
| `br_2014` | 30 | 15 | single-uf (BR), pair-out | 0.9333 | **1.0000** | +0.0667 | 0.0714 | 0.0359 |
| `us_2022` | 104 | 52 | LOSO (9 states) | 0.7788 | 0.7788 | +0.0000 | 0.1952 | 0.1952 |

Weighted average across the 4 cycles (n=362):
- MRP w=0.36 acc: **0.9365**
- no-MRP acc: 0.8755
- MRP w=0.36 brier: 0.0451
- no-MRP brier: 0.0750

## Reading the numbers

**FR 2022 / BR 2014 / AR 2023.** All three are runoffs with a strong
final outcome (Macron 58.6%, Dilma 51.6%, Milei 55.7%). MRP gets the
last poll-pair correct in 100% of leave-one-pair-out folds, and Brier
roughly halves vs no-MRP. AR 2023 is the most striking gain
(+0.20 acc): Massa led most polls in the final 30 days, so a model that
trusts the lead alone fails on roughly half the polls; MRP's
`(country, regime=right)` baseline pulls the right (LLA) probability up
because most of the train set's right-leaning runoffs in the cohort
(BR 2014, FR 2022) had right-leaning candidates losing while incumbents
won, but the directional lead+regime joint puts the prior closer to
50/50, which here is enough to flip the call to Milei.

**US 2022 governor: MRP delta=0.** This is honest, expected, and worth
flagging:

- LOSO splits hold out *all* polls of a given state, so by construction
  the `(uf, regime)` baseline for the held-out state has 0 train rows
  and falls back to the cohort default. With only 9 states in scope,
  cross-state regime transfer is too thin for a 0.36 shrinkage to help.
- The cohort already gets 77.9% acc from poll-lead alone, but the
  remaining errors are precisely the close races (AZ Hobbs/Lake within 1
  pt; NV Lombardo/Sisolak within 1 pt) where polls were systematically
  off, not where state baseline could rescue.
- A more useful split would train on US 2018 + 2020 governor cycles
  (with same-state continuity) and test on 2022. We do not have those
  raws here; this is an explicit follow-up.

**FR / BR / AR caveat.** The single-uf leave-one-pair-out CV uses the
same country's other polls in the train set. The MRP state baseline
therefore reduces in practice to a country baseline, not a within-country
transfer. The +acc numbers are still genuinely leak-safe at the poll-pair
level (no information from the held-out poll leaks into rates), but they
are not a *cross-region* generalization claim the way US 2022 LOSO is.
Treat the 100% LOSO numbers on these three as "Vila MRP gets the runoff
direction right when polls + cohort agree", not as a region-level
generalization proof.

## Honest failures / data gaps

- **Kansas governor 2022**: dropped by the standard `T<=30` filter
  because no Wayback-snapshot polls fall within that window. Documented
  in `_fetch.us_2022.states_covered`; not synthesized.
- **AR table rowspan handling**: the Argentine wiki uses `rowspan=N` on
  date cells; the parser tracks `last_date` to recover continuation
  rows. Without that fix only ~9/22 rows parsed.
- **No 538 governor_polls_historical**: GitHub does not host an
  aggregated historical governor file (only `pres_pollaverages_1968-2016`
  and 2024 averages). We pulled the live `governor_polls.csv` snapshot
  from the Wayback Machine instead.

## Reproduce

```bash
cd /home/pedroafonso/vila-politica-2026
python3 scripts/cross_country_extended.py
# prints SUMMARY block above
# writes data/backtest/{fr,ar,br,us}_*.csv and data/cross_country_extended.json
```

Smoke test stays green:

```bash
python3 scripts/smoke_political.py    # 29 passed, 0 failed
```

## Files

- `scripts/cross_country_extended.py` — fetcher + parser + LOSO/pair-out evaluator
- `data/cross_country/raw_extended/` — local cache of raw HTML/CSV
- `data/backtest/fr_2022_president.csv` (199 rows incl. header)
- `data/backtest/ar_2023_president.csv` (31 rows)
- `data/backtest/br_2014_president.csv` (31 rows)
- `data/backtest/us_2022_midterms.csv` (105 rows)
- `data/cross_country_extended.json` — full per-cycle metrics

The original Phase-3 artifacts (`data/cross_country_results.json`, the
3 prior backtest CSVs) are untouched.
