# Setup Commands — Copy-Paste Blocks

Tested on Debian / Ubuntu / Linux Mint. Adapt `apt-get` to your distro.

## 1. Install LaTeX toolchain (one-time, ~1.2 GB)

```bash
sudo apt-get update
sudo apt-get install -y \
    pandoc \
    texlive-latex-recommended \
    texlive-fonts-recommended \
    texlive-latex-extra \
    texlive-publishers \
    texlive-bibtex-extra \
    texlive-xetex \
    biber \
    poppler-utils
```

Verify:
```bash
pandoc --version | head -1
pdflatex --version | head -1
biber --version | head -1
```

## 2. Build LaTeX manuscript

```bash
cd /home/pedroafonso/vila-politica-2026
make paper-tex
```

Output: `docs/paper/PAPER.tex`. Auto-fetches `cup-journal.cls` and
`cup-logo-new.pdf` from cambridge-medium repo on first run.

## 3. Compile to PDF locally

```bash
cd /home/pedroafonso/vila-politica-2026/docs/paper
pdflatex PAPER.tex
pdflatex PAPER.tex          # second pass for cross-references
biber PAPER                  # if using BibLaTeX bibliography
pdflatex PAPER.tex           # final pass
```

Inspect:
```bash
xdg-open PAPER.pdf            # Linux
open PAPER.pdf                # macOS
start PAPER.pdf               # Windows
```

## 4. Mint arXiv preprint

### Build arXiv tarball

```bash
cd /home/pedroafonso/vila-politica-2026/docs/paper
tar -czvf /tmp/arxiv_submission.tar.gz \
    PAPER.tex \
    cup-journal.cls \
    cup-logo-new.pdf \
    figs/
ls -lh /tmp/arxiv_submission.tar.gz
```

### Upload to arXiv

```bash
xdg-open https://arxiv.org/submit
```

Steps in browser:
1. Login (create account if first time at https://arxiv.org/user/register).
2. **Start new submission** > "Replace files" > upload `/tmp/arxiv_submission.tar.gz`.
3. Primary category: `stat.AP`. Cross-list: `econ.EM`, `stat.ME`.
4. Title, authors, abstract: paste from PAPER.md.
5. Submit. arXiv ID arrives in 12-24h.

## 5. Mint Zenodo DOI for replication archive

### Build replication zip

```bash
cd /home/pedroafonso
git -C vila-politica-2026 archive --format=zip \
    --output=/tmp/vila-politica-2026-v1.3-prereg.zip \
    v1.3-prereg
ls -lh /tmp/vila-politica-2026-v1.3-prereg.zip
```

### Upload to Zenodo

```bash
xdg-open https://zenodo.org/uploads/new
```

Steps in browser:
1. Login (or create account at https://zenodo.org/signup).
2. **New Upload** > drag-drop `/tmp/vila-politica-2026-v1.3-prereg.zip`.
3. Resource type: **Software** (or **Dataset** if you prefer).
4. Title, authors, description: copy from `PAPER.md` abstract.
5. Keywords: copy from `PAPER.md` Keywords block.
6. License: **MIT License**.
7. Related identifiers: link to GitHub (`https://github.com/PAMF2/vila-politica-2026`).
8. **Publish**. DOI minted instantly (e.g. `10.5281/zenodo.XXXXXXX`).

### Insert DOI back into paper

```bash
cd /home/pedroafonso/vila-politica-2026
# Replace XXXXXX with your real Zenodo DOI suffix
sed -i 's|TO BE FILLED Zenodo DOI|10.5281/zenodo.XXXXXXX|g' \
    docs/paper/PAPER.md
make paper          # rebuild PDF with DOI baked in
```

## 6. Get real ORCIDs

```bash
xdg-open https://orcid.org/register
```

Steps in browser:
1. Register (free).
2. Complete profile.
3. Copy 16-digit ORCID iD (format `XXXX-XXXX-XXXX-XXXX`).

Insert into paper:
```bash
cd /home/pedroafonso/vila-politica-2026
# Replace placeholders with your real iDs
sed -i 's|0009-0000-0000-0000|<your-orcid>|' docs/paper/PAPER.md
sed -i 's|0009-0000-0000-0001|<igor-orcid>|' docs/paper/PAPER.md
make paper
```

## 7. Tag submission state

```bash
cd /home/pedroafonso/vila-politica-2026
git tag v1.3-submission -m "PA submission ready - arXiv ID + Zenodo DOI inserted"
git push origin v1.3-submission
```

## 8. Submit to Political Analysis (ScholarOne)

```bash
xdg-open https://mc.manuscriptcentral.com/polanalysis
```

Steps in browser:
1. Login (or create author account).
2. **Author Center** > **Submit a New Manuscript**.
3. Select manuscript type: **Original Article**.
4. Upload files in this order (ScholarOne requires order):
   - **Main Document**: `PAPER.pdf` (the compiled PDF — for review)
   - **Manuscript Source File**: `PAPER.tex`
   - **Class File**: `cup-journal.cls`
   - **Logo**: `cup-logo-new.pdf`
   - **Figures**: each PNG in `docs/paper/figs/` as separate "Image" file
   - **Cover Letter**: paste from `WHERE_TO_PUBLISH.md` template
   - **Replication Materials Archive Link**: paste Zenodo URL
5. Title, abstract, keywords: paste from PAPER.md frontmatter.
6. Suggested reviewers: 5 names from `WHERE_TO_PUBLISH.md` § Suggested
   reviewers.
7. Conflicts of interest: paste from PAPER.md § Competing interests.
8. Funding statement: paste from PAPER.md § Funding statement.
9. **Submit**.

## 9. Submit to International Journal of Forecasting (Editorial Manager)

```bash
xdg-open https://www.editorialmanager.com/forec
```

Convert documentclass first:
```bash
cd /home/pedroafonso/vila-politica-2026/docs/paper
cp PAPER.tex PAPER_IJF.tex
sed -i 's|\\documentclass\[Original Article\]{cup-journal}|\\documentclass[review,3p]{elsarticle}|' PAPER_IJF.tex
# Remove cup-journal-specific macros
sed -i '/\\jname\|\\jvol\|\\jissue\|\\jyear\|\\artid\|\\doi\|\\copyrightline\|\\license\|\\historydates/d' PAPER_IJF.tex
pdflatex PAPER_IJF.tex
pdflatex PAPER_IJF.tex
```

Then upload `PAPER_IJF.tex`, `PAPER_IJF.pdf`, and `figs/` to Editorial Manager.

## 10. Smoke-test before any submission

```bash
cd /home/pedroafonso/vila-politica-2026
make smoke                    # 29/29 contract tests
make reproduce-fast           # full pipeline ~3 min
make verify                   # SHA-256 verify cached JSONs match expected
```

If any of these fails, do not submit. Fix first.

## 11. Backup before any destructive operation

```bash
cd /home/pedroafonso
tar -czf ~/Downloads/vila_politica_$(date +%Y%m%d_%H%M%S).tar.gz \
    --exclude='vila-politica-2026/.git' \
    --exclude='vila-politica-2026/__pycache__' \
    --exclude='vila-politica-2026/node_modules' \
    vila-politica-2026/
ls -lh ~/Downloads/vila_politica_*.tar.gz | tail -1
```

## 12. Rebuild Docker container for binder-equivalent reproduction

```bash
cd /home/pedroafonso/vila-politica-2026
docker build -t vila-politica:v1.3 .
docker run --rm -v $(pwd)/data:/app/data vila-politica:v1.3 make reproduce
docker save vila-politica:v1.3 | gzip > /tmp/vila-politica-v1.3.tar.gz
ls -lh /tmp/vila-politica-v1.3.tar.gz
```

Optional: push to Docker Hub for citable container:
```bash
docker tag vila-politica:v1.3 <your-dockerhub>/vila-politica:v1.3
docker push <your-dockerhub>/vila-politica:v1.3
```

## Order of operations - first submission flow

```bash
# T+0: install toolchain (skip if already done)
sudo apt-get install -y pandoc texlive-latex-recommended \
    texlive-fonts-recommended texlive-latex-extra texlive-publishers biber

# T+5min: get ORCIDs (browser action, ~5 min each)
xdg-open https://orcid.org/register

# T+10min: build LaTeX
cd /home/pedroafonso/vila-politica-2026
make paper-tex
cd docs/paper && pdflatex PAPER.tex && pdflatex PAPER.tex && cd ../..

# T+15min: build replication zip
git archive --format=zip --output=/tmp/replication.zip v1.3-prereg

# T+20min: upload to Zenodo, mint DOI (browser, ~15 min)
xdg-open https://zenodo.org/uploads/new

# T+35min: insert ORCIDs + Zenodo DOI into PAPER.md
$EDITOR docs/paper/PAPER.md   # find/replace placeholders
make paper                     # rebuild PDF

# T+45min: tag submission state
git tag v1.3-submission -m "PA submission ready"
git push origin v1.3-submission

# T+50min: build arXiv tarball
cd docs/paper
tar -czvf /tmp/arxiv.tar.gz PAPER.tex cup-journal.cls cup-logo-new.pdf figs/
cd ../..

# T+55min: arXiv submit (browser, ~30 min)
xdg-open https://arxiv.org/submit

# T+24h: arXiv ID arrives by email
# T+25h: insert arXiv ID footnote into PAPER.md, rebuild, push

# T+26h: PA submit (browser, ~2 h)
xdg-open https://mc.manuscriptcentral.com/polanalysis

# T+8 weeks: PA first decision arrives
```

Total user-facing wallclock: ~3 h active work split across 2 days.
