"""Figures.

Public figures (committed to figures/):
    exposure_ranking.png        50-metro exposure index, Eloundou with Anthropic overlay
    method_validation.png       Eloundou vs Anthropic exposure across the 50 metros

Private figures (written to output/private/, gitignored):
    python -m ai_exposure.plot --metric postings
    python -m ai_exposure.plot --metric investment

Style: teal highlight for the 10 largest metros by employment plus the extreme
metros on each axis, gray for the rest, log y-axis, Source and Note lines below.
"""

import argparse
import textwrap

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches  # noqa: E402
import matplotlib.transforms  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.ticker import FuncFormatter, LogLocator, NullFormatter  # noqa: E402

from . import opportunity  # noqa: E402
from .sources import ROOT  # noqa: E402

FIG = ROOT / "figures"
PRIVATE_OUT = ROOT / "output" / "private"
PROCESSED = ROOT / "data" / "processed"

TEAL = "#0E6E73"
GRAY = "#B8BEC4"
INK = "#1F2328"
MUTED = "#5B636B"
GRID = "#E6E8EB"

EXPOSURE_SOURCE = (
    "Exposure: BLS OEWS May 2024; Eloundou et al. (2024), GPT-4 beta rating; "
    "Anthropic Economic Index (2026)."
)
EXPOSURE_NOTE = (
    "AI Exposure Index = employment-weighted mean of occupation-level AI exposure "
    "(Eloundou et al. 2024, task-count weighted) over occupations scored by both sources."
)

plt.rcParams.update(
    {
        "font.family": ["Inter", "DejaVu Sans"],
        "font.size": 10,
        "axes.edgecolor": MUTED,
        "axes.labelcolor": INK,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)


def _footer(fig, source, note):
    lines = textwrap.wrap("Source: " + source, 150) + textwrap.wrap("Note: " + note, 150)
    fig.text(0.06, 0.015, "\n".join(lines), fontsize=7.5, color=MUTED, va="bottom", ha="left", linespacing=1.4)
    return len(lines)


def _label(ax, rows, xcol, ycol, radius_pt=None, all_points=None):
    """Direct labels placed greedily (biggest marks first). Each label takes the candidate spot with
    the lowest cost: overlap with other labels, overlap with other bubbles, distance. Spots away from
    the mark get a thin leader line."""
    from matplotlib.transforms import Bbox

    fig = ax.figure
    renderer = fig.canvas.get_renderer()
    pt = fig.dpi / 72.0
    axbb = ax.get_window_extent(renderer)
    pts = all_points if all_points is not None else rows
    rad = (lambda i: radius_pt[i]) if radius_pt is not None else (lambda i: 4)
    bubbles = {}
    for idx, r in pts.iterrows():
        cx, cy = ax.transData.transform((r[xcol], r[ycol]))
        rr = rad(idx) * pt
        bubbles[idx] = Bbox.from_extents(cx - rr, cy - rr, cx + rr, cy + rr)

    def area(a, b):
        w = min(a.x1, b.x1) - max(a.x0, b.x0)
        h = min(a.y1, b.y1) - max(a.y0, b.y0)
        return w * h if w > 0 and h > 0 else 0.0

    placed = []
    order = sorted(rows.index, key=lambda i: -rad(i))
    for idx in order:
        r = rows.loc[idx]
        rp = rad(idx)
        best = None
        for dist in (3, 12, 24, 38):
            d = rp + dist
            for off, ha, va in [((d, 0), "left", "center"), ((-d, 0), "right", "center"),
                                ((0, d), "center", "bottom"), ((0, -d), "center", "top"),
                                ((d * .7, d * .7), "left", "bottom"), ((-d * .7, d * .7), "right", "bottom"),
                                ((d * .7, -d * .7), "left", "top"), ((-d * .7, -d * .7), "right", "top")]:
                t = ax.text(0, 0, r.label, fontsize=8.5, ha=ha, va=va)
                t.set_transform(ax.transData + matplotlib.transforms.ScaledTranslation(off[0] / 72, off[1] / 72,
                                                                                       fig.dpi_scale_trans))
                t.set_position((r[xcol], r[ycol]))
                bb = t.get_window_extent(renderer).expanded(1.04, 1.25)
                t.remove()
                cost = dist * 2
                if not (axbb.contains(bb.x0, bb.y0) and axbb.contains(bb.x1, bb.y1)):
                    cost += 1e6
                cost += sum(area(bb, p) for p in placed) * 50
                cost += sum(area(bb, b) for i, b in bubbles.items() if i != idx) * 3
                if best is None or cost < best[0]:
                    best = (cost, off, ha, va, dist, bb)
            if best[0] < 24 * 2 + 1 and best[4] == dist:
                break
        _, off, ha, va, dist, bb = best
        ax.annotate(r.label, (r[xcol], r[ycol]), xytext=off, textcoords="offset points", ha=ha, va=va,
                    fontsize=8.5, color=INK, zorder=6,
                    arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6, shrinkA=1, shrinkB=rp + 1)
                    if dist > 3 else None)
        placed.append(bb)


def _study():
    return pd.read_csv(PROCESSED / "msa_exposure_study.csv", dtype={"msa_code": str})


def _money(v, _=None):
    if v >= 1e9:
        return f"${v / 1e9:,.0f}B" if v >= 1e10 else f"${v / 1e9:g}B"
    if v >= 1e6:
        return f"${v / 1e6:,.0f}M"
    return f"${v:,.0f}"


def bubble(df, ycol, ylabel, title, source, note, out, synthetic=False, money=False, fit=False, keep_open=False):
    """Exposure (x) vs opportunity (y, log), bubble = total employment. Flourish-like layout."""
    df = df.copy().reset_index(drop=True)
    top10 = set(df.nlargest(10, "total_employment").msa_code)
    extremes = set(df.nlargest(2, "exposure_eloundou").msa_code) | set(df.nsmallest(1, "exposure_eloundou").msa_code) \
        | set(df.nlargest(2, ycol).msa_code) | set(df.nsmallest(1, ycol).msa_code)
    df["hl"] = df.msa_code.isin(top10 | extremes)
    smax = df.total_employment.max()
    size = lambda e: 1400 * e / smax + 30  # noqa: E731

    fig, ax = plt.subplots(figsize=(10, 7.4))
    fig.subplots_adjust(left=0.1, right=0.97, top=0.81, bottom=0.215)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(which="both", length=0, labelsize=9, colors=MUTED)
    art = {"groups": [], "fit_line": None, "fit_text": None, "labels": []}
    for hl, color, alpha, z in [(False, GRAY, 0.7, 2), (True, TEAL, 0.82, 3)]:
        d = df[df.hl == hl]
        sc = ax.scatter(d.exposure_eloundou, d[ycol], s=size(d.total_employment), c=color, alpha=alpha,
                        edgecolors="white", linewidths=1.2, zorder=z)
        art["groups"].append((sc, d.exposure_eloundou.to_numpy(), size(d.total_employment).to_numpy()))
    ax.set_yscale("log")
    ax.yaxis.set_major_locator(LogLocator(base=10, subs=(1, 2, 5)))
    ax.yaxis.set_minor_formatter(NullFormatter())
    ax.yaxis.set_major_formatter(FuncFormatter(_money) if money else
                                 FuncFormatter(lambda v, _: f"{v:,.0f}" if v >= 10 else f"{v:g}"))
    lo, hi = df[ycol].min(), df[ycol].max()
    ax.set_ylim(lo / 1.6, hi * 1.8)
    pad = (df.exposure_eloundou.max() - df.exposure_eloundou.min()) * 0.06
    ax.set_xlim(df.exposure_eloundou.min() - pad, df.exposure_eloundou.max() + pad * 1.8)
    ax.grid(True, which="major", color=GRID, linewidth=0.8, zorder=0)
    if fit:
        from scipy.stats import pearsonr
        x, ly = df.exposure_eloundou, np.log10(df[ycol])
        b, a = np.polyfit(x, ly, 1)
        r = pearsonr(x, ly)[0]
        xs = np.linspace(*ax.get_xlim(), 100)
        (art["fit_line"],) = ax.plot(xs, 10 ** (a + b * xs), color=INK, lw=1.4, ls=(0, (5, 4)), alpha=0.7, zorder=1)
        art["fit_xy"] = (xs, 10 ** (a + b * xs))
        art["fit_text"] = ax.text(0.985, 0.04, f"Fit: log-linear OLS, r = {r:.2f} (semi-log)", transform=ax.transAxes,
                ha="right", va="bottom", fontsize=9, color=INK,
                bbox=dict(boxstyle="round,pad=0.35", fc="white", ec=GRID))
    fig.canvas.draw()
    df["r_pt"] = np.sqrt(size(df.total_employment) / np.pi)
    before = set(ax.texts)
    _label(ax, df[df.hl], "exposure_eloundou", ycol, radius_pt=df["r_pt"], all_points=df)
    art["labels"] = [t for t in ax.texts if t not in before]
    ax.set_xlabel("AI Exposure Index", fontsize=9.5, color=MUTED, labelpad=8)
    ax.set_ylabel(ylabel, fontsize=9.5, color=MUTED, labelpad=8)

    fig.text(0.06, 0.95, title, fontsize=16, color=INK, weight="bold")
    fig.text(0.06, 0.912, f"{len(df)} U.S. metros. Each bubble is a metro, sized by total employment.",
             fontsize=10, color=MUTED)
    # legend chips
    lx, ly = 0.06, 0.865
    for color, text in [(TEAL, "10 largest metros + top and bottom on each axis"), (GRAY, "Other metros")]:
        fig.patches.append(matplotlib.patches.Circle((lx + 0.006, ly + 0.006), 0.0065, transform=fig.transFigure,
                                                     color=color, alpha=0.85, figure=fig))
        t = fig.text(lx + 0.018, ly, text, fontsize=9, color=INK)
        fig.canvas.draw()
        lx = t.get_window_extent().transformed(fig.transFigure.inverted()).x1 + 0.03
    fig.text(lx, ly, "Bubble size: total employment (BLS OEWS May 2024)", fontsize=9, color=MUTED)

    if synthetic:
        ax.text(0.5, 0.5, "SYNTHETIC DATA\nNOT REAL", transform=ax.transAxes, fontsize=48, color="#C0392B",
                alpha=0.18, ha="center", va="center", rotation=20, weight="bold", zorder=10)
    _footer(fig, source, note)
    if keep_open:
        return fig, ax, art
    fig.savefig(out, dpi=200, facecolor="white")
    plt.close(fig)
    print(f"Wrote {out}")


def exposure_ranking(df):
    df = df.sort_values("exposure_eloundou")
    fig, ax = plt.subplots(figsize=(8, 11))
    fig.subplots_adjust(left=0.2, right=0.95, top=0.94, bottom=0.1)
    y = np.arange(len(df))
    ax.barh(y, df.exposure_eloundou, color=TEAL, height=0.62, label="Eloundou (primary)")
    ax.scatter(df.exposure_anthropic, y, color=INK, s=14, zorder=3, label="Anthropic (cross-check)")
    ax.set_yticks(y, df.label, fontsize=8)
    ax.tick_params(axis="y", length=0)
    ax.grid(True, axis="x", color=GRID, zorder=0)
    ax.set_axisbelow(True)
    ax.set_xlabel("AI Exposure Index")
    ax.legend(loc="lower right", frameon=False, fontsize=8.5)
    fig.text(0.04, 0.965, "AI Exposure Index, 50 U.S. metros", fontsize=14, color=INK, weight="semibold")
    _footer(fig, EXPOSURE_SOURCE, "Anthropic observed exposure runs about 2.6x lower in level; rankings agree "
            "(see method_validation.png).")
    out = FIG / "exposure_ranking.png"
    fig.savefig(out, dpi=200)
    plt.close(fig)
    print(f"Wrote {out}")


def method_validation(df, spearman):
    fig, ax = plt.subplots(figsize=(8, 7))
    fig.subplots_adjust(left=0.11, right=0.96, top=0.88, bottom=0.17)
    ax.scatter(df.exposure_eloundou, df.exposure_anthropic, s=46, c=TEAL, edgecolors="white", linewidths=1.2, zorder=3)
    b, a = np.polyfit(df.exposure_eloundou, df.exposure_anthropic, 1)
    xs = np.linspace(df.exposure_eloundou.min(), df.exposure_eloundou.max(), 50)
    ax.plot(xs, a + b * xs, color=MUTED, linewidth=1.2, linestyle="--", zorder=2)
    resid = df.exposure_anthropic - (a + b * df.exposure_eloundou)
    lab = set(df.nlargest(4, "exposure_eloundou").msa_code) | set(df.nsmallest(3, "exposure_eloundou").msa_code) \
        | set(df.loc[resid.abs().nlargest(4).index, "msa_code"])
    fig.canvas.draw()
    _label(ax, df[df.msa_code.isin(lab)], "exposure_eloundou", "exposure_anthropic",
           radius_pt=pd.Series(np.sqrt(46 / np.pi), index=df.index), all_points=df)
    ax.grid(True, color=GRID, zorder=0)
    ax.set_xlabel("Eloundou et al. (2024): capability-based exposure")
    ax.set_ylabel("Anthropic Economic Index (2026): observed exposure")
    fig.text(0.05, 0.95, "Two exposure measures, one ranking", fontsize=14, color=INK, weight="semibold")
    fig.text(0.05, 0.915, f"50 U.S. metros. Spearman rank correlation = {spearman:.2f}. Dashed line = OLS fit.",
             fontsize=9, color=MUTED)
    _footer(fig, EXPOSURE_SOURCE, "Both indexes use identical BLS employment weights over a common set of "
            "756 SOC occupations.")
    out = FIG / "method_validation.png"
    fig.savefig(out, dpi=200)
    plt.close(fig)
    print(f"Wrote {out}")


def main():
    import json

    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--metric", choices=list(opportunity.METRICS), help="build a private figure from licensed data")
    p.add_argument("--input", help="path to licensed CSV (default: data/private/<file>)")
    p.add_argument("--per-worker", action="store_true",
                   help="divide the metric by total employment and show it per 10,000 workers")
    p.add_argument("--animate", action="store_true", help="write an MP4 animation instead of a PNG")
    p.add_argument("--no-fit", action="store_true", help="omit the fit line and r label")
    p.add_argument("--sample", choices=["d3", "all50"], default="d3",
                   help="d3 = 48 metros (Hartford, Louisville excluded); all50 = full study universe")
    args = p.parse_args()

    study = _study()
    sample = study[study.in_d3_sample == 1] if args.sample == "d3" else study
    excl = "" if args.sample == "all50" else " Hartford and Louisville excluded."

    if args.metric:
        m = opportunity.METRICS[args.metric]
        y = opportunity.load(args.metric, args.input)
        df = sample.merge(y, on="msa_code", how="inner").reset_index(drop=True)
        if len(df) < len(sample):
            print(f"Warning: {len(sample) - len(df)} metros have no {m.column} value and are dropped.")
        PRIVATE_OUT.mkdir(parents=True, exist_ok=True)
        ycol, ylabel, suffix, extra = m.column, m.axis_label, "", ""
        if args.per_worker:
            ycol = m.column + "_per_10k"
            df[ycol] = df[m.column] / df.total_employment * 1e4
            ylabel = m.axis_label.replace(" (log scale)", " per 10,000 workers (log scale)")
            suffix, extra = "_per_worker", " Divided by total employment (BLS OEWS May 2024)."
        kw = dict(df=df, ycol=ycol, ylabel=ylabel, title=m.title + (" per Worker" if args.per_worker else ""),
                  source=f"{EXPOSURE_SOURCE} {m.source_line}.",
                  note=f"{EXPOSURE_NOTE} {m.window}{extra} n = {len(df)} metros.{excl}",
                  out=PRIVATE_OUT / f"exposure_vs_{args.metric}{suffix}.png",
                  money=(args.metric == "investment"), fit=not args.no_fit)
        if getattr(args, "animate", False):
            from .animate import animate
            animate(kw, PRIVATE_OUT / f"exposure_vs_{args.metric}{suffix}.mp4")
        else:
            bubble(**kw)
        return

    FIG.mkdir(parents=True, exist_ok=True)
    val = json.loads((PROCESSED / "validation.json").read_text())
    exposure_ranking(study)
    method_validation(study, val["study_50"]["spearman"])
    opportunity.make_synthetic(study)  # refresh data/sample/ for pipeline tests


if __name__ == "__main__":
    main()
