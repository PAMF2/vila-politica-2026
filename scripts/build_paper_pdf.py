#!/usr/bin/env python3
"""Build journal-style two-column PDF from PAPER.md via weasyprint + matplotlib SVG math.

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
        fontsize = 12 if display else 9.8
        fig = plt.figure(figsize=(0.01, 0.01))
        fig.text(0, 0, f"${tex}$", fontsize=fontsize)
        try:
            fig.savefig(path, format="svg", bbox_inches="tight",
                        pad_inches=0.02, transparent=True)
        except Exception as e:
            print(f"[math fail] {tex!r}: {e}", file=sys.stderr)
            plt.close(fig)
            return None
        plt.close(fig)
    cls = "math-display" if display else "math-inline"
    return f'<img src="file://{path}" class="{cls}" alt="{tex}">'


with open(MD_PATH) as f:
    md_src = f.read()

# Display math: $$...$$
def repl_display(m):
    tex = m.group(1).strip()
    out = render_math(tex, display=True)
    return f'<div class="math-block">{out}</div>' if out else m.group(0)


md_src = re.sub(r"\$\$(.+?)\$\$", repl_display, md_src, flags=re.DOTALL)

# Inline math: $...$ but not adjacent to $
def repl_inline(m):
    tex = m.group(1).strip()
    if not tex:
        return m.group(0)
    out = render_math(tex, display=False)
    return out if out else m.group(0)


md_src = re.sub(r"(?<!\$)\$([^\$\n]+?)\$(?!\$)", repl_inline, md_src)

# Convert MD to HTML
body_html = markdown.markdown(
    md_src,
    extensions=["tables", "fenced_code", "footnotes", "toc"],
)

# Inject figure paths (resolve relative to PAPER.md)
body_html = body_html.replace(
    'src="figs/',
    f'src="file://{ROOT / "docs" / "paper" / "figs"}/',
)

# Title block: extract first H1
title_m = re.match(r"<h1>(.+?)</h1>", body_html)
title = title_m.group(1) if title_m else "Vila Politica 2026"
if title_m:
    body_html = body_html[title_m.end():]

# Full HTML with academic CSS
html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
@page {{
  size: A4;
  margin: 1.6cm 1.4cm 1.8cm 1.4cm;
  @bottom-center {{ content: counter(page); font-family: serif; font-size: 9pt; }}
  @top-right {{ content: "Vila Politica 2026"; font-family: serif; font-size: 8pt; color: #666; }}
}}
@page :first {{
  @top-right {{ content: ""; }}
}}
html, body {{
  font-family: Georgia, "Times New Roman", serif;
  font-size: 9.8pt;
  line-height: 1.42;
  color: #111;
  margin: 0;
}}
.title-block {{
  column-span: all;
  text-align: center;
  margin: 0 0 18pt 0;
  border-bottom: 0.5pt solid #999;
  padding-bottom: 14pt;
}}
.title {{
  font-size: 18pt;
  font-weight: 700;
  line-height: 1.18;
  margin: 0 0 8pt 0;
  letter-spacing: -0.01em;
}}
.byline {{ font-size: 9.6pt; font-style: italic; }}
.abstract-block {{
  column-span: all;
  margin: 6pt 0 14pt 0;
  padding: 10pt 14pt;
  background: #f8f7f3;
  border-left: 2pt solid #888;
}}
.abstract-block h2 {{
  font-variant: small-caps;
  letter-spacing: 0.06em;
  font-size: 10pt;
  margin: 0 0 6pt 0;
  color: #333;
}}
main {{ column-count: 2; column-gap: 18pt; column-rule: 0.25pt solid #ccc; }}
h1 {{ font-size: 13pt; font-weight: 700; margin: 14pt 0 6pt 0; }}
h2 {{ font-size: 11pt; font-weight: 700; margin: 12pt 0 4pt 0;
      font-variant: small-caps; letter-spacing: 0.04em; }}
h3 {{ font-size: 10pt; font-weight: 700; margin: 8pt 0 3pt 0; font-style: italic; }}
p  {{ margin: 0 0 6pt 0; text-align: justify; hyphens: auto; }}
ul, ol {{ margin: 4pt 0 6pt 18pt; padding: 0; }}
li {{ margin: 0 0 2pt 0; }}
table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 8.6pt;
  margin: 4pt 0 6pt 0;
}}
th, td {{
  border: 0.4pt solid #999;
  padding: 2.5pt 4pt;
  text-align: left;
  vertical-align: top;
}}
th {{ background: #efefe8; font-weight: 700; }}
td:nth-child(n+2) {{ text-align: right; font-variant-numeric: tabular-nums; }}
code {{
  font-family: "JetBrains Mono", "Source Code Pro", monospace;
  font-size: 8.6pt;
  background: #f3f3ee;
  padding: 0.2pt 2pt;
}}
pre {{
  font-family: "JetBrains Mono", "Source Code Pro", monospace;
  font-size: 8.4pt;
  background: #f3f3ee;
  padding: 4pt 6pt;
  margin: 4pt 0;
  border-left: 1.5pt solid #aaa;
  overflow-x: auto;
}}
blockquote {{ border-left: 2pt solid #aaa; margin: 4pt 0; padding: 0 8pt;
              color: #444; font-style: italic; }}
.math-display {{ display: block; margin: 6pt auto; max-width: 95%; }}
.math-inline  {{ display: inline-block; vertical-align: middle; }}
img {{ max-width: 100%; height: auto; }}
figure {{ margin: 6pt 0; text-align: center; }}
figcaption {{ font-size: 8.4pt; font-style: italic; color: #444; }}
hr {{ border: none; border-top: 0.4pt solid #999; margin: 10pt 0; }}
.references p {{ padding-left: 12pt; text-indent: -12pt; font-size: 8.6pt; }}
</style>
</head>
<body>
<div class="title-block">
  <div class="title">{title}</div>
</div>
<main>
{body_html}
</main>
</body>
</html>
"""

HTML_PATH.write_text(html)
print(f"html ok -> {HTML_PATH} ({len(html)} bytes)")

# Compile via weasyprint
try:
    subprocess.run(
        ["weasyprint", str(HTML_PATH), str(PDF_PATH)],
        check=True, capture_output=True, text=True,
    )
    print(f"pdf size: {PDF_PATH.stat().st_size} bytes")
except subprocess.CalledProcessError as e:
    print(f"weasyprint failed:\n{e.stderr}", file=sys.stderr)
    sys.exit(1)
