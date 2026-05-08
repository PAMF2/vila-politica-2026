#!/usr/bin/env python3
"""Build journal-style two-column PDF from PAPER.md.

Uses weasyprint (HTML/CSS engine) and matplotlib for math rendering as SVG.
Emulates ACM/IEEE single-column-then-two-column academic layout.

Output: docs/paper/PAPER.pdf
"""
import hashlib
import os
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
SVG_DIR = Path("/tmp/paper_math_svg")
SVG_DIR.mkdir(exist_ok=True)


def render_math(tex, display=False):
    h = hashlib.md5((str(display) + tex).encode()).hexdigest()[:14]
    path = SVG_DIR / f"m_{h}.svg"
    if not path.exists():
        fontsize = 13 if display else 10.4
        fig = plt.figure(figsize=(0.01, 0.01))
        fig.text(0, 0, f"${tex}$", fontsize=fontsize)
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

# Preserve Markdown title block (extract first H1) BEFORE math substitution
title_m = re.match(r"^# (.+?)\n", md_src)
title = title_m.group(1) if title_m else "Vila Politica 2026"
if title_m:
    md_src = md_src[title_m.end():]

# Pull authors block
authors_m = re.match(r"\n*## Authors\n+(.+?)(?=\n## )", md_src, flags=re.DOTALL)
authors_html = ""
if authors_m:
    block = authors_m.group(1).strip()
    lines = [l.strip() for l in block.split("\n") if l.strip()]
    authors_html = " · ".join(lines)
    md_src = md_src[:authors_m.start()] + md_src[authors_m.end():]

# Pull abstract block, render small caps style
abstract_m = re.search(r"## Abstract\n+(.+?)(?=\n## )", md_src, flags=re.DOTALL)
abstract_html = ""
if abstract_m:
    abstract_html = abstract_m.group(1).strip()
    md_src = md_src[:abstract_m.start()] + md_src[abstract_m.end():]

# Pull keywords block
kw_m = re.search(r"## Keywords\n+(.+?)(?=\n## )", md_src, flags=re.DOTALL)
keywords_html = ""
if kw_m:
    keywords_html = kw_m.group(1).strip()
    md_src = md_src[:kw_m.start()] + md_src[kw_m.end():]

# Display math: $$...$$
md_src = re.sub(
    r"\$\$(.+?)\$\$",
    lambda m: f'<div class="math-block">{render_math(m.group(1).strip(), display=True) or m.group(0)}</div>',
    md_src, flags=re.DOTALL,
)

# Inline math: $...$
md_src = re.sub(
    r"(?<!\$)\$([^\$\n]+?)\$(?!\$)",
    lambda m: render_math(m.group(1).strip(), display=False) or m.group(0),
    md_src,
)

body_html = markdown.markdown(
    md_src,
    extensions=["tables", "fenced_code", "footnotes", "smarty"],
)

# Resolve fig paths
body_html = body_html.replace(
    'src="figs/',
    f'src="file://{ROOT / "docs" / "paper" / "figs"}/',
)

# References get hanging indent class
body_html = re.sub(
    r"(<h2>References</h2>)",
    r'\1<div class="references">',
    body_html,
)
# Close references div before next h2 or appendix
body_html = re.sub(
    r'(<div class="references">.*?)(<h2>(?!References))',
    r"\1</div>\2",
    body_html, flags=re.DOTALL,
)

# Render abstract MD
abstract_md_html = markdown.markdown(abstract_html) if abstract_html else ""

# Full HTML
html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
@page {{
  size: A4;
  margin: 1.7cm 1.5cm 2cm 1.5cm;
  @bottom-center {{ content: counter(page); font-family: "Times New Roman", serif; font-size: 9pt; color: #555; }}
  @top-right {{ content: "Vila Politica 2026 - Working Paper"; font-family: "Times New Roman", serif; font-size: 8pt; color: #888; }}
}}
@page :first {{
  @top-right {{ content: ""; }}
  @bottom-center {{ content: counter(page); font-family: "Times New Roman", serif; font-size: 9pt; color: #555; }}
}}
html, body {{
  font-family: "Times New Roman", "Liberation Serif", Georgia, serif;
  font-size: 9.6pt;
  line-height: 1.45;
  color: #0a0a0a;
  margin: 0;
  text-rendering: optimizeLegibility;
}}
.title-block {{
  text-align: center;
  margin: 0 0 16pt 0;
  padding-bottom: 12pt;
}}
.title {{
  font-size: 16.5pt;
  font-weight: 700;
  line-height: 1.2;
  letter-spacing: -0.005em;
  margin: 0 0 10pt 0;
  font-family: "Times New Roman", serif;
}}
.byline {{
  font-size: 10pt;
  font-style: italic;
  color: #222;
  margin: 0 0 4pt 0;
}}
.affiliation {{
  font-size: 8.6pt;
  color: #555;
}}
.abstract-block {{
  margin: 0 14pt 18pt 14pt;
  padding: 10pt 16pt;
  border-top: 0.6pt solid #555;
  border-bottom: 0.6pt solid #555;
  font-size: 9.2pt;
  text-align: justify;
}}
.abstract-block .label {{
  font-variant: small-caps;
  letter-spacing: 0.07em;
  font-weight: 700;
  font-size: 8.6pt;
  color: #333;
  margin-right: 6pt;
}}
.keywords-block {{
  margin: 0 14pt 16pt 14pt;
  font-size: 8.8pt;
  color: #333;
}}
.keywords-block .label {{
  font-variant: small-caps;
  letter-spacing: 0.07em;
  font-weight: 700;
  margin-right: 4pt;
}}
main {{
  column-count: 2;
  column-gap: 22pt;
  column-rule: 0.3pt solid #d0d0d0;
}}
h1 {{ font-size: 12.5pt; font-weight: 700; margin: 12pt 0 5pt 0; }}
h2 {{
  font-size: 10.6pt;
  font-weight: 700;
  margin: 12pt 0 4pt 0;
  font-variant: small-caps;
  letter-spacing: 0.045em;
  color: #1a1a1a;
}}
h3 {{
  font-size: 9.8pt;
  font-weight: 700;
  margin: 8pt 0 3pt 0;
  font-style: italic;
  color: #222;
}}
p {{
  margin: 0 0 5pt 0;
  text-align: justify;
  hyphens: auto;
  text-indent: 0;
}}
p + p {{ text-indent: 12pt; }}
ul, ol {{ margin: 4pt 0 6pt 16pt; padding: 0; }}
li {{ margin: 0 0 2pt 0; text-align: justify; }}
table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 8.4pt;
  margin: 5pt 0 7pt 0;
  break-inside: avoid;
}}
thead tr {{ border-top: 0.6pt solid #333; border-bottom: 0.4pt solid #333; }}
tbody tr:last-child {{ border-bottom: 0.6pt solid #333; }}
th, td {{
  padding: 2.6pt 5pt;
  text-align: left;
  vertical-align: top;
}}
th {{ font-weight: 700; font-variant: small-caps; letter-spacing: 0.03em; }}
td:nth-child(n+2), th:nth-child(n+2) {{
  text-align: right;
  font-variant-numeric: tabular-nums;
}}
code {{
  font-family: "Liberation Mono", Consolas, monospace;
  font-size: 8.4pt;
  background: #f4f3ec;
  padding: 0.4pt 2.4pt;
  border-radius: 1pt;
}}
pre {{
  font-family: "Liberation Mono", Consolas, monospace;
  font-size: 8.0pt;
  background: #f4f3ec;
  padding: 5pt 7pt;
  margin: 5pt 0;
  border-left: 1.6pt solid #999;
  overflow-x: auto;
  break-inside: avoid;
}}
blockquote {{
  border-left: 2pt solid #999;
  margin: 5pt 0;
  padding: 0 9pt;
  color: #333;
  font-style: italic;
}}
.math-display {{
  display: block;
  margin: 7pt auto;
  max-width: 92%;
}}
.math-inline {{
  display: inline-block;
  vertical-align: -0.16em;
  height: 1em;
}}
img:not(.math-display):not(.math-inline) {{
  max-width: 100%;
  height: auto;
  display: block;
  margin: 6pt auto 4pt auto;
  break-inside: avoid;
}}
hr {{ border: none; border-top: 0.4pt solid #777; margin: 9pt 0; }}
.references {{ font-size: 8.4pt; }}
.references p {{
  padding-left: 14pt;
  text-indent: -14pt !important;
  margin: 0 0 3pt 0;
  text-align: left;
  hyphens: none;
}}
sup, sub {{ line-height: 0; }}
strong {{ font-weight: 700; }}
em {{ font-style: italic; }}
</style>
</head>
<body>
<div class="title-block">
  <div class="title">{title}</div>
  <div class="byline">{authors_html}</div>
  <div class="affiliation">Vila INTEIA Research</div>
</div>
<div class="abstract-block">
  <span class="label">Abstract.</span> {abstract_md_html.replace('<p>', '').replace('</p>', ' ').strip()}
</div>
<div class="keywords-block">
  <span class="label">Keywords:</span> {keywords_html}
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
