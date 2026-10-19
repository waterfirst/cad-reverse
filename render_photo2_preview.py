import sys
import gdstk
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly

lib = gdstk.read_gds(sys.argv[1])
colors = {1: "#f2e04a", 2: "#f39c3c", 3: "#5cb85c", 4: "#3cc3c3", 5: "#4a7fd8", 6: "#c44fc4",
          7: "#d9534f", 8: "#eeeeee", 21: "#3cc3c3", 22: "#9ad17a", 23: "#e05a5a", 24: "#ffffff", 25: "#b0b0b0"}
fig, axes = plt.subplots(1, 2, figsize=(11, 5.6), dpi=120)
for ax, name, title in [(axes[0], "PIXEL_A", "(a) pixel layout (colour classes)"),
                        (axes[1], "SENSOR_B", "(b) sensor layout (traced)")]:
    c = lib.cells[[x.name for x in lib.cells].index(name)]
    for poly in c.polygons:
        ax.add_patch(MPoly(poly.points, closed=True, fc=colors.get(poly.layer, "#888"),
                           ec="black", lw=0.2, alpha=0.85))
    xs = [p[0] for poly in c.polygons for p in poly.points]
    ys = [p[1] for poly in c.polygons for p in poly.points]
    ax.set_xlim(min(xs) - 2, max(xs) + 2)
    ax.set_ylim(min(ys) - 2, max(ys) + 2)
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("um")
    ax.set_ylabel("um")
fig.suptitle("Layers extracted from photo (approximate, not DRC-checked)", fontsize=10)
fig.tight_layout()
fig.savefig(sys.argv[2])
print("ok")
