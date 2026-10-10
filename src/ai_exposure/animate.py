"""MP4 animation of a bubble chart, for social posts (LinkedIn plays native video, not HTML).

The video shows the same information as the PNG. It is written to output/private/ and is
never committed.

Sequence (30 fps, about 12 s): empty axes -> gray metros grow in, left to right ->
highlighted metros grow in with labels -> fit line draws -> r appears -> hold.
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FFMpegWriter, FuncAnimation
from matplotlib.colors import to_rgba

FPS = 30


def _ease(t):
    t = np.clip(t, 0, 1)
    return 1 - (1 - t) ** 3


def animate(kw, out, seconds=12.0):
    from .plot import bubble

    fig, ax, art = bubble(**kw, keep_open=True)
    fig.set_size_inches(10, 7.5)  # 1920 x 1440 at dpi 192
    (g_sc, g_x, g_s), (h_sc, h_x, h_s) = art["groups"]
    base_fc = {id(g_sc): to_rgba(g_sc.get_facecolor()[0]), id(h_sc): to_rgba(h_sc.get_facecolor()[0])}

    def stagger(x, t0, t1, spread=0.6):
        """Per-point progress: points start in x order across (t0, t1)."""
        lo, span = x.min(), max(np.ptp(x), 1e-9)
        dur = (t1 - t0) * (1 - spread)

        def prog(t, xs=x):
            start = t0 + np.clip((xs - lo) / span, 0, 1) * (t1 - t0) * spread
            return _ease((t - start) / dur)
        return prog

    g_prog = stagger(g_x, 0.8, 3.6)
    h_prog = stagger(h_x, 3.6, 6.0)
    fit_xy = art.get("fit_xy")
    n = int(seconds * FPS)

    def frame(i):
        t = i / FPS
        for sc, prog, s in [(g_sc, g_prog, g_s), (h_sc, h_prog, h_s)]:
            p = prog(t)
            sc.set_sizes(s * p)
            fc = np.tile(base_fc[id(sc)], (len(s), 1))
            fc[:, 3] *= p
            sc.set_facecolor(fc)
            sc.set_edgecolor([(1, 1, 1, a) for a in p])
        for lab in art["labels"]:
            la = _ease((h_prog(t, np.array([lab.xy[0]]))[0] - 0.7) / 0.3)
            lab.set_alpha(la)
            if getattr(lab, "arrow_patch", None) is not None:
                lab.arrow_patch.set_alpha(la * 0.9)
        if art["fit_line"] is not None:
            fp = _ease((t - 6.2) / 1.8)
            k = max(int(len(fit_xy[0]) * fp), 1 if fp > 0 else 0)
            art["fit_line"].set_data(fit_xy[0][:k], fit_xy[1][:k])
            ta = _ease((t - 8.0) / 0.6)
            art["fit_text"].set_alpha(ta)
            art["fit_text"].get_bbox_patch().set_alpha(ta)
        return []

    anim = FuncAnimation(fig, frame, frames=n, blit=False)
    writer = FFMpegWriter(fps=FPS, codec="libx264", bitrate=6000,
                          extra_args=["-pix_fmt", "yuv420p", "-movflags", "+faststart"])
    anim.save(out, writer=writer, dpi=192, savefig_kwargs={"facecolor": "white"})
    plt.close(fig)
    print(f"Wrote {out}")
