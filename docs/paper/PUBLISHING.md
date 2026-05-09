# Publishing Guide

This document explains how to convert `PAPER.md` into a journal-ready LaTeX submission and walk it through the publication pipeline.

## Quick path: Overleaf (recommended, no local install)

1. Create a free account at https://overleaf.com.
2. Open the Cambridge Medium template:
   https://www.overleaf.com/latex/templates/template-for-submission-to-political-analysis/csxqmspqzntv
   (this is the official Cambridge `cup-journal.cls` template Political Analysis accepts).
3. Click **Open as Template** to get a fresh project.
4. Replace the template's `main.tex` content with the body of `PAPER.tex` produced by `scripts/build_paper_tex.py` (see local path below).
5. Drag-and-drop the entire `figs/` folder into the Overleaf project.
6. Click **Recompile**. The PDF preview matches Political Analysis copy-edited style.

If you prefer to bypass `build_paper_tex.py`, you can paste the markdown directly into Overleaf and use Overleaf's built-in Pandoc filter, but the script result is more robust because it pre-resolves the structured abstract and the author block.

## Local path: pandoc + texlive

### Install dependencies (Debian/Ubuntu)

```bash
sudo apt-get update
sudo apt-get install -y pandoc \
    texlive-latex-recommended \
    texlive-fonts-recommended \
    texlive-latex-extra \
    texlive-publishers \
    texlive-bibtex-extra \
    biber
```

This pulls about 1.2 GB but produces a self-contained LaTeX toolchain.

### Convert PAPER.md to PAPER.tex

```bash
python3 scripts/build_paper_tex.py
```

The script:

- Fetches `cup-journal.cls` and `cup-logo-new.pdf` from
  https://github.com/christopherkenny/cambridge-medium on first run.
- Parses the markdown frontmatter (`# title`, `## Authors`, `## Abstract`,
  `## Keywords`).
- Calls pandoc to convert the body to LaTeX.
- Wraps everything in a Cambridge cup-journal.cls preamble with title,
  author block, ORCID, corresponding-author marker, abstract, keywords,
  and journal-required statements (funding, competing interests, data
  availability, replication, ethics).

Output: `docs/paper/PAPER.tex`.

### Compile

```bash
cd docs/paper
pdflatex PAPER.tex
pdflatex PAPER.tex   # second pass for cross-references
```

The second pass resolves Figure / Table cross-references and the table-of-references hanging-indent layout.

## Publishing pipeline

### Option A: Political Analysis (Cambridge)

1. Read the author guidelines:
   https://www.cambridge.org/core/journals/political-analysis/information/instructions-contributors
2. Submit at https://mc.manuscriptcentral.com/polanalysis (ScholarOne
   submission portal).
3. Required uploads:
   - **Manuscript** (`PAPER.tex` + `figs/` + `cup-journal.cls` + `cup-logo-new.pdf`).
     Either tar.gz the whole `docs/paper/` folder, or zip it. Submit the PDF
     as a separate review-PDF file.
   - **Cover letter**. One paragraph: novelty (closed-form MRP-style
     state-regime prior, leak-safe protocol, BR + 11-country replication),
     why Political Analysis is the right venue, prior contact with the
     editor (if any), conflicts of interest disclosure.
   - **Replication materials**. Political Analysis requires a
     publicly-archived replication archive. Two options:
     - **Dataverse** (Harvard, free): https://dataverse.harvard.edu/.
       Upload the entire repository, get a DOI.
     - **Zenodo** (CERN, free): https://zenodo.org/. Same idea.
     Both produce a citable DOI that goes in the data-availability
     statement of the paper.
4. Suggested reviewers: list 3-5 names whose work is cited in §2 / §6.10 /
   §6.9 (e.g. authors of MRP / Linzer / cross-country forecasting papers).
5. Review timeline: typical first decision in 8-12 weeks; major revision
   round common; final acceptance to print 3-6 months after acceptance.

### Option B: International Journal of Forecasting (Elsevier)

1. Author guidelines:
   https://www.sciencedirect.com/journal/international-journal-of-forecasting/publish/guide-for-authors
2. Submit at https://www.editorialmanager.com/forec.
3. IJF accepts LaTeX in `elsarticle.cls`. Convert the cup-journal preamble
   to elsarticle:

```bash
# After running build_paper_tex.py, swap the documentclass line:
sed -i 's/\\documentclass\[Original Article\]{cup-journal}/\\documentclass[review,3p]{elsarticle}/' \
    docs/paper/PAPER.tex
```

   Most macros (\title, \author, \abstract) work identically. The
   `\jname`, `\jvol`, `\jissue`, `\jyear`, `\artid`, `\doi`,
   `\copyrightline`, `\license`, `\historydates`, `\corremail`,
   `\affil`, `\orcid` macros are CUP-specific and will need to be
   removed or adapted.

### Option C: arXiv preprint (any time, any version)

1. Account at https://arxiv.org/.
2. Submit under category `stat.AP` (statistics applications) cross-listed
   to `econ.EM` (econometrics) or `cs.LG` (machine learning).
3. Upload `PAPER.tex` plus `figs/`, `cup-journal.cls`, `cup-logo-new.pdf`
   as a tar.gz. arXiv compiles the PDF on its servers; check the result
   in the preview.
4. Add the arXiv ID to the GitHub README within 24 hours so the
   replication archive points back to the preprint.

### Option D: OSF pre-registration anchor (already done)

The frozen pre-registration document at v1.2-prereg / v1.3-prereg git
tags is the analytical pre-registration. To make it citable from a third
party:

1. Account at https://osf.io/.
2. New registration -> Open-Ended Registration template.
3. Upload `PRE-REGISTRATION.md`, `PAPER.md` snapshot at
   `v1.2-prereg`, the cached JSON manifest, and the SHA-256 manifest
   that ships with the supplementary archive.
4. OSF mints a DOI on registration; cite it in the data-availability
   statement.

## Checklist before submission

- [ ] All figure cross-references (`Figure N`) match auto-numbered captions.
- [ ] All bibliographic entries have DOIs or stable URLs where available.
- [ ] No local file paths in body prose (only in §8 SHA tables, if any).
- [ ] PDF compiles without warnings with weasyprint AND with pdflatex.
- [ ] Smoke test passes: `make smoke` (29/29).
- [ ] Numerical claims trace to JSON ground truth: spot-check `make
      stats`, `make wsweep`, `make hetero`, `make loso`, `make dropone`,
      `make houseeffects`, `make calibration`, `make permutation`.
- [ ] Replication archive uploaded to Dataverse or Zenodo with DOI.
- [ ] Pre-registration tag (`v1.2-prereg` or `v1.3-prereg`) referenced
      in §8.5.
- [ ] Cover letter drafted.
- [ ] Suggested reviewers listed.
- [ ] Conflicts of interest disclosed (Vila INTEIA co-founder
      relationship is in §Competing Interests).
- [ ] Funding statement in §Funding (no external funding).
- [ ] Ethics statement in §Ethics (public aggregate data only).

## Common rejection reasons and pre-emptive responses

1. **"Reviewer questions cycle-specific overfitting"**. Counter:
   §6.5 (w-sweep), §6.6 (heteroscedastic null), §6.8 (drop-one-cycle
   robustness in [0.9396, 0.9785] range).
2. **"Reviewer questions whether the result is BR-specific"**. Counter:
   §6.4 cross-country replication on 11 additional countries with 6,954
   events; AR 2023 result; §6.7 within-BR LOSO.
3. **"Reviewer asks about house effects"**. Counter: §5.4 per-institute
   table; AtlasIntel and Instituto Verita handled by the prior pull
   without per-firm calibration.
4. **"Reviewer asks why not Stan / full Bayesian"**. Counter: §5.6
   benchmark - Stan DLM 0.8680 vs ours 0.9721; closed form is intentional
   and §6.6 shows extra parameters degrade the ensemble.
5. **"Reviewer questions calibration"**. Counter: §5.3 reliability
   diagram + Murphy decomposition + ECE/MCE; the architecture trades
   Brier for accuracy and §5.5 selective coverage curve quantifies the
   trade.

## Frequently asked questions

**Q. Can I publish without LaTeX?**
A. Political Analysis accepts MS Word submissions, but the structured
abstract, the author block, and the reference formatting will need
manual reproduction. The LaTeX path is shorter.

**Q. Can I submit the markdown directly?**
A. No. All major political-science journals require either LaTeX or
Word for typesetting. The markdown serves as the source of truth; it
is not a submission format.

**Q. Should I use double-spacing?**
A. PA submission guidelines request double-spacing for review. Add
`\linespread{1.6}` to the preamble before submission, then remove for
the camera-ready version.

**Q. What about line numbers?**
A. ScholarOne adds line numbers automatically during review; do not
add them manually.

**Q. How long does first decision take?**
A. PA: 8-12 weeks typical. IJF: 6-10 weeks. Major revision common.

**Q. Can the architecture be deployed before publication?**
A. Yes. The MIT-licensed code at the v1.3-prereg tag is functional and
can be operated by third parties; the article documents and validates
it.
