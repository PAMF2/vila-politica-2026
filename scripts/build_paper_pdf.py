#!/usr/bin/env python3
"""Build NeurIPS-style two-column PDF from PAPER.md.

Goal: match the visual quality of 'Attention is all you need' (Vaswani et al, 2017)
and the official NeurIPS template:
- A4 page, ~1.25in margins
- 10pt Times-like serif
- Single-column title block + abstract + keywords
- Two-column main body
- Section numbers in body ("1 Introduction"), not in headings
- Italic figure/table captions, "Figure 1:" prefix
- Hanging-indent references in 9pt
- Equations centered with proper math rendering via matplotlib SVG

Output: docs/paper/PAPER.pdf
"""
import hashlib
import re
import subprocess
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import markdown

ROOT = Path(__file__).resolve().parent.parent
MD_PATH = ROOT / "docs" / "paper" / "PAPER.md"
HTML_PATH = ROOT / "docs" / "paper" / "PAPER.html"
PDF_PATH = ROOT / "docs" / "paper" / "PAPER.pdf"
SVG_DIR = Path("/tmp/paper_math_svg_v3")
SVG_DIR.mkdir(exist_ok=True)


def render_math(tex, display=False):
    h = hashlib.md5((str(display) + tex).encode()).hexdigest()[:14]
    path = SVG_DIR / f"m_{h}.svg"
    if not path.exists():
        # Match NeurIPS body text size: 10pt; display equations slightly larger.
        fontsize = 13.5 if display else 10.6
        fig = plt.figure(figsize=(0.01, 0.01))
        fig.text(0, 0, f"${tex}$", fontsize=fontsize, color="#0a0a0a")
        try:
            fig.savefig(path, format="svg", bbox_inches="tight",
                        pad_inches=0.04, transparent=True)
        except Exception as e:
            print(f"[math fail] {tex!r}: {e}", file=sys.stderr)
            plt.close(fig)
            return None
        plt.close(fig)
    cls = "math-display" if display else "math-inline"
    return f'<img src="file://{path}" class="{cls}" alt="{tex}">'


with open(MD_PATH) as f:
    md_src = f.read()

# Extract title
title_m = re.match(r"^# (.+?)\n", md_src)
title = title_m.group(1) if title_m else "Vila Politica 2026"
if title_m:
    md_src = md_src[title_m.end():]

# Extract authors
authors_m = re.match(r"\n*## Authors\n+(.+?)(?=\n## )", md_src, flags=re.DOTALL)
authors_html = ""
if authors_m:
    block = authors_m.group(1).strip()
    lines = [l.strip() for l in block.split("\n") if l.strip()]
    # NeurIPS format: name on one line, affiliation on next
    parsed = []
    for ln in lines:
        # "Name (Affiliation, email)"
        m = re.match(r"(.+?)\s*\((.+?)\)", ln)
        if m:
            name = m.group(1).strip()
            aff = m.group(2).strip()
            parsed.append((name, aff))
        else:
            parsed.append((ln, ""))
    if len(parsed) == 2:
        authors_html = (
            f'<div class="author-grid">'
            f'<div><div class="aname">{parsed[0][0]}</div>'
            f'<div class="aaff">{parsed[0][1]}</div></div>'
            f'<div><div class="aname">{parsed[1][0]}</div>'
            f'<div class="aaff">{parsed[1][1]}</div></div>'
            f'</div>'
        )
    else:
        authors_html = " · ".join(f"{n}, {a}" if a else n for n, a in parsed)
    md_src = md_src[:authors_m.start()] + md_src[authors_m.end():]

# Abstract
abstract_m = re.search(r"## Abstract\n+(.+?)(?=\n## )", md_src, flags=re.DOTALL)
abstract_text = ""
if abstract_m:
    abstract_text = abstract_m.group(1).strip()
    md_src = md_src[:abstract_m.start()] + md_src[abstract_m.end():]

# Keywords
kw_m = re.search(r"## Keywords\n+(.+?)(?=\n## )", md_src, flags=re.DOTALL)
keywords_text = ""
if kw_m:
    keywords_text = kw_m.group(1).strip()
    md_src = md_src[:kw_m.start()] + md_src[kw_m.end():]

# Math
md_src = re.sub(
    r"\$\$(.+?)\$\$",
    lambda m: f'<div class="math-block">{render_math(m.group(1).strip(), display=True) or m.group(0)}</div>',
    md_src, flags=re.DOTALL,
)
md_src = re.sub(
    r"(?<!\$)\$([^\$\n]+?)\$(?!\$)",
    lambda m: render_math(m.group(1).strip(), display=False) or m.group(0),
    md_src,
)

# Strip "## N." section number prefix to NeurIPS style "N "
md_src = re.sub(r"^## (\d+)\. ", r"## \1 ", md_src, flags=re.MULTILINE)
md_src = re.sub(r"^### (\d+)\.(\d+) ", r"### \1.\2 ", md_src, flags=re.MULTILINE)

body_html = markdown.markdown(
    md_src,
    extensions=["tables", "fenced_code", "footnotes", "smarty"],
)

# Resolve fig paths
body_html = body_html.replace(
    'src="figs/',
    f'src="file://{ROOT / "docs" / "paper" / "figs"}/',
)

# Wrap figure imgs in <figure> with auto caption number (find <p><img.../></p>)
fig_counter = [0]
def wrap_fig(m):
    fig_counter[0] += 1
    img = m.group(0)
    # find alt or use generic
    alt_m = re.search(r'alt="([^"]*)"', img)
    alt = alt_m.group(1) if alt_m and alt_m.group(1) else ""
    caption = f"Figure {fig_counter[0]}"
    if alt:
        caption += f": {alt}"
    return f'<figure>{img}<figcaption>{caption}.</figcaption></figure>'

body_html = re.sub(
    r'<p><img[^>]+/?></p>',
    wrap_fig,
    body_html,
)

# Wrap tables in figure with caption from preceding text (best effort: just number)
# Skipping auto-table captions to avoid false positives.

# Wrap wide tables (>=5 columns OR >=8 rows) in .wide-table so they
# span both PDF columns instead of getting crushed in narrow column.
def wrap_wide_tables(html):
    def repl(m):
        tbl = m.group(0)
        n_cols = len(re.findall(r'<th', tbl[:tbl.find('</thead>')] if '</thead>' in tbl else tbl))
        n_rows = len(re.findall(r'<tr', tbl))
        if n_cols >= 5 or n_rows >= 8:
            return f'<div class="wide-table">{tbl}</div>'
        return tbl
    return re.sub(r'<table>.*?</table>', repl, html, flags=re.DOTALL)


body_html = wrap_wide_tables(body_html)

# References block hanging indent
body_html = re.sub(
    r"(<h2>References</h2>)",
    r'<div class="references">\1',
    body_html,
)
body_html = re.sub(
    r'(<div class="references">.*?)(<h2>(?!References)|<h1)',
    r"\1</div>\2",
    body_html, flags=re.DOTALL,
)
# If no following h2, close at end
if '<div class="references">' in body_html and '</div>' not in body_html.split('<div class="references">')[1]:
    body_html += "</div>"

# Render abstract markdown
abstract_md = markdown.markdown(abstract_text) if abstract_text else ""

html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
@page {{
  size: A4;
  margin: 2.0cm 1.6cm 2.4cm 1.6cm;
  @bottom-center {{
    content: counter(page);
    font-family: "Times New Roman", "Liberation Serif", serif;
    font-size: 9pt; color: #555;
  }}
}}
@page :first {{
  margin-top: 1.4cm;
  @bottom-center {{
    content: counter(page);
    font-family: "Times New Roman", "Liberation Serif", serif;
    font-size: 9pt; color: #555;
  }}
}}
html, body {{
  font-family: "Times New Roman", "Liberation Serif", "Computer Modern", Georgia, serif;
  font-size: 10pt;
  line-height: 1.36;
  color: #0a0a0a;
  margin: 0;
  text-rendering: optimizeLegibility;
}}

/* Title block - NeurIPS centered */
.title-block {{
  text-align: center;
  margin: 0 0 14pt 0;
}}
.title {{
  font-size: 17pt;
  font-weight: 700;
  line-height: 1.2;
  letter-spacing: -0.005em;
  margin: 0 auto 14pt auto;
  max-width: 95%;
}}
.author-grid {{
  display: flex;
  justify-content: center;
  gap: 30pt;
  margin: 8pt 0 4pt 0;
}}
.author-grid > div {{ text-align: center; }}
.aname {{
  font-size: 11pt;
  font-weight: 600;
  margin: 0;
}}
.aaff {{
  font-size: 9.4pt;
  font-style: italic;
  color: #333;
  margin-top: 1pt;
}}

/* Abstract: NeurIPS small-caps centered, narrow */
.abstract-block {{
  margin: 16pt auto 12pt auto;
  max-width: 80%;
  font-size: 9.6pt;
  line-height: 1.4;
  text-align: justify;
  hyphens: auto;
}}
.abstract-block .label {{
  font-variant: small-caps;
  letter-spacing: 0.06em;
  font-weight: 700;
  font-size: 10pt;
  display: block;
  text-align: center;
  margin: 0 0 4pt 0;
}}
.keywords-block {{
  max-width: 80%;
  margin: 0 auto 18pt auto;
  font-size: 9pt;
  text-align: center;
  color: #333;
}}
.keywords-block .label {{
  font-variant: small-caps;
  letter-spacing: 0.06em;
  font-weight: 700;
  margin-right: 4pt;
}}

/* Two-column main */
main {{
  column-count: 2;
  column-gap: 22pt;
  column-rule: none;
}}
/* (no h3-keep wrapper; rely on widows/orphans + h3 break-after: avoid) */
h1 {{
  font-size: 12.5pt; font-weight: 700; margin: 14pt 0 5pt 0;
  break-after: avoid; page-break-after: avoid;
  break-inside: avoid;
}}
h2 {{
  font-size: 11pt;
  font-weight: 700;
  margin: 11pt 0 3pt 0;
  letter-spacing: 0.005em;
  break-after: avoid; page-break-after: avoid;
  break-inside: avoid;
}}
h3 {{
  font-size: 10pt;
  font-weight: 700;
  margin: 8pt 0 2pt 0;
  font-style: normal;
}}
p {{
  margin: 0 0 5pt 0;
  text-align: justify;
  hyphens: auto;
  text-indent: 0;
  orphans: 4; widows: 4;
}}
p + p {{ text-indent: 12pt; }}
p:first-of-type, h1 + p, h2 + p, h3 + p {{ text-indent: 0; }}
ul, ol {{ margin: 4pt 0 6pt 16pt; padding: 0; }}
li {{ margin: 0 0 1.5pt 0; text-align: justify; }}

/* Tables - NeurIPS booktabs style. Span both columns when wide. */
table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 8.4pt;
  margin: 8pt auto 10pt auto;
  break-inside: avoid;
}}
/* Tables wider than ~5 cols: float across both columns */
.wide-table {{
  column-span: all;
  margin: 10pt 0 12pt 0;
}}
.wide-table table {{
  font-size: 9pt;
  margin: 0 auto;
}}
thead tr {{ border-top: 0.8pt solid #111; border-bottom: 0.5pt solid #111; }}
tbody tr:last-child {{ border-bottom: 0.8pt solid #111; }}
th, td {{
  padding: 2.5pt 5pt;
  text-align: left;
  vertical-align: top;
  border: none;
}}
th {{ font-weight: 700; font-size: 8.6pt; }}
td:nth-child(n+2), th:nth-child(n+2) {{
  text-align: right;
  font-variant-numeric: tabular-nums;
}}

/* Code */
code {{
  font-family: "Liberation Mono", Consolas, "Courier New", monospace;
  font-size: 8.6pt;
  background: #f5f4ee;
  padding: 0.4pt 2pt;
}}
pre {{
  font-family: "Liberation Mono", Consolas, monospace;
  font-size: 8.4pt;
  background: #f5f4ee;
  padding: 5pt 7pt;
  margin: 5pt 0;
  border-left: 1.4pt solid #999;
  break-inside: avoid;
}}

/* Math */
.math-display {{
  display: block;
  margin: 8pt auto;
  max-width: 92%;
}}
.math-inline {{
  display: inline-block;
  vertical-align: -0.16em;
  height: 1em;
}}

/* Figures */
figure {{
  margin: 6pt 0 8pt 0;
  text-align: center;
  break-inside: avoid;
}}
figure img {{
  max-width: 100%;
  height: auto;
}}
figcaption {{
  font-size: 8.4pt;
  font-style: italic;
  color: #222;
  margin-top: 2pt;
  text-align: left;
  hyphens: auto;
}}
img:not(.math-display):not(.math-inline) {{
  max-width: 100%;
  height: auto;
}}

/* Block quotes */
blockquote {{
  border-left: 2pt solid #888;
  margin: 5pt 0;
  padding: 0 9pt;
  color: #333;
  font-style: italic;
  font-size: 9.6pt;
}}

/* References */
.references h2 {{
  margin-top: 14pt;
}}
.references p {{
  padding-left: 14pt;
  text-indent: -14pt !important;
  margin: 0 0 3pt 0;
  text-align: left;
  hyphens: none;
  font-size: 8.4pt;
  line-height: 1.32;
}}

hr {{ border: none; border-top: 0.4pt solid #777; margin: 9pt 0; }}
sup, sub {{ line-height: 0; }}
strong {{ font-weight: 700; }}
em {{ font-style: italic; }}

/* Drop excess space before first H2 inside columns */
main > h2:first-child {{ margin-top: 0; }}
</style>
</head>
<body>
<div class="title-block">
  <div class="title">{title}</div>
  {authors_html}
</div>
<div class="abstract-block">
  <span class="label">Abstract</span>
  {abstract_md.replace('<p>', '').replace('</p>', ' ').strip()}
</div>
<div class="keywords-block">
  <span class="label">Keywords:</span> {keywords_text}
</div>
<main>
{body_html}
</main>
</body>
</html>
"""

HTML_PATH.write_text(html)
print(f"html ok -> {HTML_PATH} ({len(html)} bytes)")

try:
    subprocess.run(
        ["weasyprint", str(HTML_PATH), str(PDF_PATH)],
        check=True, capture_output=True, text=True,
    )
    print(f"pdf size: {PDF_PATH.stat().st_size} bytes")
except subprocess.CalledProcessError as e:
    print(f"weasyprint failed:\n{e.stderr}", file=sys.stderr)
    sys.exit(1)
