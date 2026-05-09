#!/usr/bin/env python3
"""Convert PAPER.md to a Cambridge cup-journal.cls LaTeX manuscript.

Pipeline:
  1. Pandoc converts PAPER.md to LaTeX body fragment.
  2. We wrap it in a cup-journal.cls preamble with title, author, abstract,
     keywords, ORCID, corresponding-author, and journal statements.
  3. Output goes to docs/paper/PAPER.tex.
  4. The cup-journal.cls + cup-logo-new.pdf must be co-located in
     docs/paper/ before pdflatex runs (the helper downloads them on first
     run if absent).

Requirements:
  - pandoc >= 2.x  (sudo apt install pandoc)
  - pdflatex from texlive  (sudo apt install texlive-latex-recommended
                            texlive-fonts-recommended texlive-latex-extra
                            texlive-publishers)
  - urllib for first-run cup-journal.cls fetch

Usage:
  python3 scripts/build_paper_tex.py
  cd docs/paper && pdflatex PAPER.tex && pdflatex PAPER.tex
"""
from __future__ import annotations

import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MD = ROOT / "docs" / "paper" / "PAPER.md"
TEX = ROOT / "docs" / "paper" / "PAPER.tex"
CLS = ROOT / "docs" / "paper" / "cup-journal.cls"
LOGO = ROOT / "docs" / "paper" / "cup-logo-new.pdf"

CLS_URL = ("https://raw.githubusercontent.com/christopherkenny/"
           "cambridge-medium/main/_extensions/cambridge-medium/cup-journal.cls")
LOGO_URL = ("https://raw.githubusercontent.com/christopherkenny/"
            "cambridge-medium/main/_extensions/cambridge-medium/"
            "cup-logo-new.pdf")


def fetch_template_files() -> None:
    if not CLS.exists():
        print(f"fetching {CLS_URL}")
        urllib.request.urlretrieve(CLS_URL, CLS)
    if not LOGO.exists():
        print(f"fetching {LOGO_URL}")
        urllib.request.urlretrieve(LOGO_URL, LOGO)


def parse_md(md_src: str) -> dict:
    """Extract title, authors, abstract, keywords, body."""
    title_m = re.match(r"^# (.+?)\n", md_src)
    title = title_m.group(1) if title_m else "Untitled"
    rest = md_src[title_m.end():] if title_m else md_src

    authors_m = re.search(r"\n## Authors\n+(.+?)(?=\n## )", rest, re.DOTALL)
    authors_block = authors_m.group(1).strip() if authors_m else ""
    if authors_m:
        rest = rest[:authors_m.start()] + rest[authors_m.end():]

    abstract_m = re.search(r"\n## Abstract\n+(.+?)(?=\n## )", rest, re.DOTALL)
    abstract = abstract_m.group(1).strip() if abstract_m else ""
    if abstract_m:
        rest = rest[:abstract_m.start()] + rest[abstract_m.end():]

    kw_m = re.search(r"\n## Keywords\n+(.+?)(?=\n## )", rest, re.DOTALL)
    keywords = kw_m.group(1).strip() if kw_m else ""
    if kw_m:
        rest = rest[:kw_m.start()] + rest[kw_m.end():]

    return {
        "title": title,
        "authors": authors_block,
        "abstract": abstract,
        "keywords": keywords,
        "body": rest.strip(),
    }


def authors_to_tex(block: str) -> tuple[str, str, str]:
    """Returns (author_tex, address_tex, corresponding_email)."""
    lines = [l.strip() for l in block.split("\n") if l.strip()]
    parsed = []
    for ln in lines:
        m = re.match(r"(.+?)\s*\((.+?)\)\s*$", ln)
        if not m:
            continue
        name = m.group(1).strip()
        parts = [p.strip() for p in m.group(2).split(";")]
        aff = parts[0] if parts else ""
        orcid, email = "", ""
        for p in parts[1:]:
            if "@" in p:
                email = p
            elif p.lower().startswith("orcid"):
                orcid = p.split(None, 1)[1].strip() if " " in p else ""
            else:
                aff = (aff + "; " + p) if aff else p
        parsed.append((name, aff, orcid, email))

    author_lines = []
    addresses = []
    for i, (n, a, o, e) in enumerate(parsed):
        rank = i + 1
        marker = "1,*" if i == 0 else str(rank)
        orcid_tex = f"\\orcid{{{o}}}" if o else ""
        author_lines.append(f"\\author[{marker}]{{{n} {orcid_tex}}}".strip())
        addresses.append(f"\\affil[{rank}]{{{a}}}")

    author_tex = "\n".join(author_lines)
    address_tex = "\n".join(addresses)
    corresponding = parsed[0][3] if parsed else ""
    return author_tex, address_tex, corresponding


def md_body_to_tex(body: str) -> str:
    """Run pandoc to convert markdown body to LaTeX."""
    tmp_md = ROOT / "docs" / "paper" / "_body_tmp.md"
    tmp_tex = ROOT / "docs" / "paper" / "_body_tmp.tex"
    tmp_md.write_text(body)
    subprocess.run(
        ["pandoc", str(tmp_md), "-f", "markdown", "-t", "latex",
         "--wrap=preserve", "-o", str(tmp_tex)],
        check=True,
    )
    out = tmp_tex.read_text()
    tmp_md.unlink()
    tmp_tex.unlink()
    return out


PREAMBLE = r"""\documentclass[Original Article]{cup-journal}

\usepackage{lipsum}
\usepackage{booktabs}
\usepackage{hyperref}
\usepackage{graphicx}
\usepackage{xcolor}
\usepackage{amsmath}
\usepackage{amssymb}

% Journal-specific configuration
\jname{Political Analysis}
\jvol{XX}
\jissue{X}
\jyear{2026}
\artid{XXXXXX}
\doi{10.1017/pan.XXXX.XX}
\copyrightline{\textcopyright{} The Authors, 2026. Published by Cambridge
    University Press on behalf of the Society for Political Methodology.}
\license{This is an Open Access article, distributed under the terms of
    the Creative Commons Attribution licence (CC BY).}
\historydates{Received: \today; Revised: \today; Accepted: \today;
    First published online: \today}

\title{__TITLE__}
__AUTHORS__
__ADDRESSES__
\corremail{__CORRESPONDING__}

\begin{document}

\maketitle

\begin{abstract}
__ABSTRACT__
\end{abstract}

\begin{keywords}
__KEYWORDS__
\end{keywords}

__BODY__

\end{document}
"""


def main() -> None:
    fetch_template_files()
    src = MD.read_text()
    parts = parse_md(src)
    a_tex, addr_tex, corresp = authors_to_tex(parts["authors"])
    body_tex = md_body_to_tex(parts["body"])

    abstract_tex = parts["abstract"].replace("\n\n", "\n\n").strip()
    # Strip the ## Abstract structured-bold labels into LaTeX equivalents
    abstract_tex = re.sub(r"\*\*([^*]+)\.\*\*", r"\\textbf{\1.}", abstract_tex)

    tex = (
        PREAMBLE
        .replace("__TITLE__", parts["title"])
        .replace("__AUTHORS__", a_tex)
        .replace("__ADDRESSES__", addr_tex)
        .replace("__CORRESPONDING__", corresp)
        .replace("__ABSTRACT__", abstract_tex)
        .replace("__KEYWORDS__", parts["keywords"])
        .replace("__BODY__", body_tex)
    )
    TEX.write_text(tex)
    print(f"saved -> {TEX} ({len(tex)} chars)")
    print()
    print("Next steps:")
    print(f"  cd {TEX.parent}")
    print("  pdflatex PAPER.tex")
    print("  pdflatex PAPER.tex   # second pass for cross-references")
    print()
    print("Or upload PAPER.tex + figs/ + cup-journal.cls + cup-logo-new.pdf to Overleaf.")


if __name__ == "__main__":
    main()
