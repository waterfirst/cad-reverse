# Per-layer preview: one panel per GDS layer, shape of that layer in colour, others as faint grey.
import sys
import gdstk
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly

GDS, OUT = sys.argv[1], sys.argv[2]
NAMES = {1: "A YELLOW", 2: "A ORANGE", 3: "A GREEN", 4: "A CYAN", 5: "A BLUE", 6: "A MAGENTA",
         7: "A RED", 8: "A WHITE", 21: "B TOPMETAL", 22: "B GUARD_RING", 23: "B DIODE",
         24: "B PAD", 25: "B BLOCK"}
COLORS = {1: "#f2e04a", 2: "#f39c3c", 3: "#5cb85c", 4: "#3cc3c3", 5: "#4a7fd8", 6: "#c44fc4",
          7: "#d9534f", 8: "#eeeeee", 21: "#3cc3c3", 22: "#9ad17a", 23: "#e05a5a", 24: "#ffffff", 25: "#b0b0b0"}

lib = gdstk.read_gds(GDS)
cells = {c.name: c for c in lib.cells}
layers = sorted(NAMES)
ncol = 5
nrow = -(-len(layers) // ncol)
fig, axes = plt.subplots(nrow, ncol, figsize=(3.3 * ncol, 3.3 * nrow), dpi=110)
axes = axes.ravel()
for ax, L in zip(axes, layers):
    cell = cells["PIXEL_A"] if L < 20 else cells["SENSOR_B"]
    for poly in cell.polygons:
        if poly.layer != L:
            ax.add_patch(MPoly(poly.points, closed=True, fc="#dddddd", ec="none", alpha=0.5))
    n = 0
    for poly in cell.polygons:
        if poly.layer == L:
            n += 1
            ax.add_patch(MPoly(poly.points, closed=True, fc=COLORS[L], ec="black", lw=0.3, alpha=0.9))
    xs = [p[0] for poly in cell.polygons for p in poly.points]
    ys = [p[1] for poly in cell.polygons for p in poly.points]
    ax.set_xlim(min(xs) - 2, max(xs) + 2)
    ax.set_ylim(min(ys) - 2, max(ys) + 2)
    ax.set_aspect("equal")
    ax.set_title(f"L{L} {NAMES[L]} ({n})", fontsize=9)
    ax.tick_params(labelsize=6)
for ax in axes[len(layers):]:
    ax.axis("off")
fig.suptitle("Per-layer view (grey = other layers, same cell). Approximate, not DRC-checked", fontsize=10)
fig.tight_layout()
fig.savefig(OUT)
print("ok", OUT)
