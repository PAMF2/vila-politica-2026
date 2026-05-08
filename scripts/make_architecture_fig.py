#!/usr/bin/env python3
"""Generate the canonical architecture figure for the paper.

Mimics the layered diagram style of 'Attention is all you need' Fig. 1:
clean boxes, labelled arrows, single column rendering, white background.
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.patches import Rectangle

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "paper" / "figs" / "fig0_architecture.png"


def box(ax, xy, w, h, text, fc="#f5f5f0", ec="#222", fontsize=9, weight="normal"):
    x, y = xy
    bb = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.18",
        linewidth=0.9, edgecolor=ec, facecolor=fc,
    )
    ax.add_patch(bb)
    ax.text(x + w / 2, y + h / 2, text,
            ha="center", va="center", fontsize=fontsize,
            family="serif", weight=weight)


def arrow(ax, p1, p2, label=None, style="-", curve=0.0):
    a = FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=12,
                        linewidth=0.9, color="#222",
                        connectionstyle=f"arc3,rad={curve}",
                        linestyle=style)
    ax.add_patch(a)
    if label:
        mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
        ax.text(mx + 0.12, my, label, fontsize=8, family="serif",
                style="italic", color="#444")


fig, ax = plt.subplots(figsize=(7.0, 5.6), dpi=300)
ax.set_xlim(0, 10)
ax.set_ylim(0, 9)
ax.axis("off")

# Top inputs row
box(ax, (0.4, 7.6), 2.0, 0.8, "Polls\n(Wikipedia, TSE, 538)", fc="#eef4ff")
box(ax, (3.0, 7.6), 2.0, 0.8, "State outcomes\n(historical UF wins)", fc="#fef3e6")
box(ax, (5.6, 7.6), 2.0, 0.8, "Candidate metadata\n(party, regime, incumb)", fc="#eaf6ec")
box(ax, (8.0, 7.6), 1.6, 0.8, "Days-to-election\n(integer)", fc="#f4eaf6")

# Middle features
box(ax, (1.0, 5.9), 1.8, 0.7, "lead_pp", fc="#dde7f7")
box(ax, (3.2, 5.9), 1.8, 0.7, "(uf, regime)", fc="#fbe6c7")
box(ax, (5.6, 5.9), 1.8, 0.7, "cohort_key", fc="#cfe9d2")
box(ax, (7.6, 5.9), 1.8, 0.7, "days_bin", fc="#e6d4ed")

# Three computation paths
# Linzer
box(ax, (0.5, 4.0), 2.4, 1.0,
    r"Linzer DLM" "\n" r"$\Phi(\ell / \sigma(d))$",
    fc="#dde7f7", weight="bold")

# Cohort empirical Bayes
box(ax, (3.5, 4.0), 2.4, 1.0,
    "Cohort Empirical Bayes\n" r"$\tilde{p}_k = (1{-}s)\,p_k + s\,p_{\mathrm{glob}}$",
    fc="#cfe9d2", weight="bold")

# State baseline
box(ax, (6.5, 4.0), 2.6, 1.0,
    "State Baseline (MRP)\n" r"$p_{u,r}=\frac{W_{u,r}+1}{N_{u,r}+2}$",
    fc="#fbe6c7", weight="bold")

# Blend
box(ax, (3.0, 2.2), 4.0, 0.9,
    r"Ensemble: $p = (1{-}w)\,[(1{-}w_\ell)\,p_{\mathrm{coh}} + w_\ell\,p_{\mathrm{Linz}}] + w\,p_{u,r}$",
    fc="#fff8d6", weight="bold", fontsize=9.5)

# Output
box(ax, (3.8, 0.5), 2.4, 0.8,
    "P(candidate wins)",
    fc="#f7d1d1", weight="bold")

# Arrows from inputs to features
arrow(ax, (1.4, 7.55), (1.9, 6.65))
arrow(ax, (4.0, 7.55), (4.1, 6.65))
arrow(ax, (6.6, 7.55), (4.1, 6.65), curve=-0.2)
arrow(ax, (6.6, 7.55), (6.5, 6.65))
arrow(ax, (8.8, 7.55), (8.5, 6.65))

# Features to paths
arrow(ax, (1.9, 5.85), (1.7, 5.05))     # lead_pp -> Linzer
arrow(ax, (8.5, 5.85), (1.7, 5.05), curve=-0.3)  # days_bin -> Linzer (sigma)
arrow(ax, (6.5, 5.85), (4.7, 5.05))     # cohort_key -> Cohort
arrow(ax, (1.9, 5.85), (4.7, 5.05), curve=0.25)  # lead_pp -> Cohort
arrow(ax, (4.1, 5.85), (7.8, 5.05), curve=-0.25)  # (uf,regime) -> State

# Paths to blend
arrow(ax, (1.7, 3.95), (4.0, 3.15))
arrow(ax, (4.7, 3.95), (5.0, 3.15))
arrow(ax, (7.8, 3.95), (6.0, 3.15))

# Blend to output
arrow(ax, (5.0, 2.15), (5.0, 1.35))

# Title
ax.text(5.0, 8.7, "Vila Política 2026 - Forecast Pipeline",
        ha="center", fontsize=12, family="serif", weight="bold")

plt.tight_layout()
plt.savefig(OUT, dpi=300, bbox_inches="tight", facecolor="white")
print(f"saved -> {OUT}")
