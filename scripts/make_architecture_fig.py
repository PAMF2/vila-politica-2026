#!/usr/bin/env python3
"""Architecture figure for the paper.

Single-column orthogonal diagram in the spirit of Vaswani et al. (2017)
Fig. 1: muted academic palette, right-angle arrows, weight labels on
the ensemble blend. Each input has one primary feature directly below
it. Features fan into three compute paths via clean L-shaped arrows.
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "paper" / "figs" / "fig0_architecture.png"

INK = "#1a1a1a"
SOFT = "#5a5a5a"

PALETTE = {
    "input":   "#f6f4ef",
    "feature": "#eef2f7",
    "linzer":  "#dfe7f2",
    "cohort":  "#e2ede2",
    "state":   "#f3eadc",
    "blend":   "#fbf3d2",
    "output":  "#f1d9d9",
}


def box(ax, xy, w, h, text, fc, fontsize=9, weight="normal"):
    x, y = xy
    bb = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.10",
        linewidth=0.8, edgecolor=INK, facecolor=fc,
    )
    ax.add_patch(bb)
    ax.text(x + w / 2, y + h / 2, text,
            ha="center", va="center", fontsize=fontsize,
            family="serif", weight=weight, color=INK)


def varrow(ax, p1, p2, label=None, lx=0.10, ly=0.0, fs=8.5, dashed=False):
    style = (0, (3, 2)) if dashed else "-"
    a = FancyArrowPatch(
        p1, p2, arrowstyle="-|>", mutation_scale=10,
        linewidth=0.85, color=INK, linestyle=style,
    )
    ax.add_patch(a)
    if label:
        ax.text((p1[0] + p2[0]) / 2 + lx,
                (p1[1] + p2[1]) / 2 + ly,
                label, fontsize=fs, family="serif",
                style="italic", color=SOFT)


def lshape(ax, p1, p2, dashed=False):
    """Down-then-horizontal-then-down arrow: drops from p1 to a midline,
    runs horizontally to p2.x, drops to p2."""
    x1, y1 = p1
    x2, y2 = p2
    style = (0, (3, 2)) if dashed else "-"
    midy = (y1 + y2) / 2
    ax.plot([x1, x1], [y1, midy], color=INK, linewidth=0.85, linestyle=style)
    ax.plot([x1, x2], [midy, midy], color=INK, linewidth=0.85, linestyle=style)
    a = FancyArrowPatch(
        (x2, midy), (x2, y2), arrowstyle="-|>",
        mutation_scale=10, linewidth=0.85, color=INK, linestyle=style,
    )
    ax.add_patch(a)


# ---- canvas ----
fig, ax = plt.subplots(figsize=(7.6, 6.6), dpi=300)
ax.set_xlim(0, 10)
ax.set_ylim(0, 10)
ax.axis("off")

LABEL_GREY = "#6a6a6a"
for y, name in [(9.55, "INPUTS"), (7.85, "FEATURES"),
                (6.05, "COMPUTE"), (3.40, "BLEND"),
                (1.30, "OUTPUT")]:
    ax.text(0.05, y, name, fontsize=8, color=LABEL_GREY,
            family="serif", weight="bold", ha="left")

# Column centers (x) for each input/feature pair
INPUT_COL = [1.50, 4.00, 6.50, 9.00]
COMPUTE_COL = {"linzer": 1.80, "cohort": 5.00, "state": 8.20}

# ---- INPUTS row ----
inputs = [
    "Polls\n(Wikipedia, TSE, 538)",
    "State outcomes\n(historical UF wins)",
    "Candidate metadata\n(party, regime, incumb)",
    "Days-to-election\n(integer)",
]
for x, txt in zip(INPUT_COL, inputs):
    box(ax, (x - 0.95, 8.7), 1.9, 0.75, txt,
        fc=PALETTE["input"], fontsize=8.5)

# ---- FEATURES row (one per input column) ----
features = ["lead_pp", "(uf, regime)", "cohort_key", "days_bin"]
for x, name in zip(INPUT_COL, features):
    box(ax, (x - 0.6, 7.05), 1.2, 0.55, name,
        fc=PALETTE["feature"], fontsize=9)

# ---- COMPUTE row ----
box(ax, (COMPUTE_COL["linzer"] - 1.2, 4.8), 2.4, 1.0,
    r"Linzer DLM" "\n" r"$p_{\mathrm{Linz}} = \Phi(\ell\,/\,\sigma(d))$",
    fc=PALETTE["linzer"], weight="bold", fontsize=9.5)
box(ax, (COMPUTE_COL["cohort"] - 1.3, 4.8), 2.6, 1.0,
    r"Cohort Empirical Bayes" "\n"
    r"$p_{\mathrm{coh}} = (1{-}s)\,p_k + s\,p_{\mathrm{glob}}$",
    fc=PALETTE["cohort"], weight="bold", fontsize=9.5)
box(ax, (COMPUTE_COL["state"] - 1.3, 4.8), 2.6, 1.0,
    r"State Baseline (MRP)" "\n"
    r"$p_{u,r} = \dfrac{W_{u,r}+1}{N_{u,r}+2}$",
    fc=PALETTE["state"], weight="bold", fontsize=9.5)

# ---- BLEND row ----
box(ax, (1.4, 2.4), 7.2, 0.9,
    r"$p \,=\, (1{-}w)\,[(1{-}w_\ell)\,p_{\mathrm{coh}} + w_\ell\,p_{\mathrm{Linz}}] \,+\, w\,p_{u,r}$",
    fc=PALETTE["blend"], weight="bold", fontsize=10.5)

# ---- OUTPUT row ----
box(ax, (3.8, 0.6), 2.4, 0.8, r"$P(\text{candidate wins})$",
    fc=PALETTE["output"], weight="bold", fontsize=10)

# ---- ARROWS ----

# 1) Inputs -> features (straight vertical, primary)
for x in INPUT_COL:
    varrow(ax, (x, 8.70), (x, 7.60))

# 2) Features -> compute paths (L-shapes from feature.bottom to compute.top)
#    Map: lead_pp -> Linzer (primary)
#         cohort_key -> Cohort (primary)
#         (uf,regime) -> State (primary)
#         days_bin -> Linzer (secondary, dashed; sigma scale)
lshape(ax, (INPUT_COL[0], 7.05), (COMPUTE_COL["linzer"] - 0.4, 5.80))  # lead_pp -> Linzer
lshape(ax, (INPUT_COL[2], 7.05), (COMPUTE_COL["cohort"], 5.80))         # cohort_key -> Cohort
lshape(ax, (INPUT_COL[1], 7.05), (COMPUTE_COL["state"], 5.80))          # (uf,regime) -> State
lshape(ax, (INPUT_COL[3], 7.05), (COMPUTE_COL["linzer"] + 0.4, 5.80),
       dashed=True)                                                     # days_bin -> Linzer (sigma)

# 3) Compute -> blend (with weight labels)
varrow(ax, (COMPUTE_COL["linzer"], 4.80), (3.30, 3.30),
       label=r"$w_\ell$", lx=-0.20, ly=0.05, fs=9)
varrow(ax, (COMPUTE_COL["cohort"], 4.80), (5.00, 3.30),
       label=r"$1{-}w_\ell$", lx=0.15, ly=0.05, fs=9)
varrow(ax, (COMPUTE_COL["state"], 4.80), (6.70, 3.30),
       label=r"$w$", lx=0.20, ly=0.05, fs=9)

# 4) Blend -> output
varrow(ax, (5.0, 2.4), (5.0, 1.4))

# Title
ax.text(5.0, 9.85, "Vila Politica 2026: forecast pipeline",
        ha="center", fontsize=12.5, family="serif",
        weight="bold", color=INK)

plt.tight_layout()
plt.savefig(OUT, dpi=300, bbox_inches="tight", facecolor="white")
print(f"saved -> {OUT}")
