# Layer extraction from the two-panel photo (a: pixel layout, b: sensor layout).
# Panel a is classified by hue into colour classes (no layer info in the photo).
# Panel b: teal sensor region, red circular diode, grey hatched guard ring are segmented by colour.
# Scale: panel a width = 45 um (from the "45um" bracket); panel b uses the same um/px (assumption).
# Approximate. Not a foundry layout, not DRC-checked.
import colorsys
import sys
import numpy as np
import gdstk
import ezdxf
from PIL import Image
from scipy import ndimage

SRC = sys.argv[1]
OUT = sys.argv[2]  # output prefix
im = Image.open(SRC).convert("RGB")
arr = np.asarray(im).astype(float) / 255.0
H, W, _ = arr.shape
r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
v = arr.max(axis=2)
mn = arr.min(axis=2)
sat = (v - mn) / (v + 1e-6)
hue = np.zeros((H, W))
d = v - mn + 1e-9
hr = ((g - b) / d) % 6
hg = (b - r) / d + 2
hb = (r - g) / d + 4
hue = np.where(v == r, hr, np.where(v == g, hg, hb)) * 60 % 360

A_BOX = (88, 66, 616, 610)     # x0, y0, x1, y1 of panel a in photo px (panel a incl. its black frame)
B_BOX = (672, 66, 1176, 610)   # panel b
UM_PER_PX = 45.0 / (A_BOX[2] - A_BOX[0])


def crop_mask(mask, box):
    x0, y0, x1, y1 = box
    out = np.zeros_like(mask)
    out[y0:y1, x0:x1] = mask[y0:y1, x0:x1]
    return out


def rects_from(mask, min_px, min_fill):
    lab, _ = ndimage.label(mask)
    res = []
    for i, sl in enumerate(ndimage.find_objects(lab), start=1):
        if sl is None:
            continue
        y0, y1 = sl[0].start, sl[0].stop
        x0, x1 = sl[1].start, sl[1].stop
        box = (y1 - y0) * (x1 - x0)
        n = int((lab[sl] == i).sum())
        if n < min_px or n / box < min_fill:
            continue
        res.append((x0, y0, x1, y1))
    return res


# ---------- panel a: colour classes ----------
def classify_a(h, s, val):
    if val < 0.35:
        return None
    if s < 0.25:
        return "WHITE" if val > 0.6 else None
    if 45 <= h < 70:
        return "YELLOW"
    if 15 <= h < 45:
        return "ORANGE"
    if 70 <= h < 170:
        return "GREEN"
    if 170 <= h < 200:
        return "CYAN"
    if 200 <= h < 260:
        return "BLUE"
    if 260 <= h < 340:
        return "MAGENTA"
    return "RED"

names_a = ["YELLOW", "ORANGE", "GREEN", "CYAN", "BLUE", "MAGENTA", "RED", "WHITE"]
label_a = np.full((H, W), "", dtype=object)
x0a, y0a, x1a, y1a = A_BOX
for y in range(y0a, y1a):
    for x in range(x0a, x1a):
        c = classify_a(hue[y, x], sat[y, x], v[y, x])
        if c:
            label_a[y, x] = c

layers_a = {}
for i, n in enumerate(names_a, start=1):
    m = (label_a == n)
    m = ndimage.binary_closing(m, iterations=1)
    layers_a[n] = (i, rects_from(crop_mask(m, A_BOX), min_px=6, min_fill=0.35))

# ---------- panel b: sensor structures ----------
teal = (hue > 130) & (hue < 190) & (sat > 0.12) & (v > 0.2) & (v < 0.7)
teal = ndimage.binary_closing(crop_mask(teal, B_BOX), iterations=4)
red = (((hue < 30) | (hue > 330)) & (sat > 0.25) & (v > 0.35))
red = crop_mask(red, B_BOX)
lab_r, _ = ndimage.label(red)
diode = []
for i, sl in enumerate(ndimage.find_objects(lab_r), start=1):
    if sl is None:
        continue
    h_, w_ = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
    n = int((lab_r[sl] == i).sum())
    if 20 <= h_ <= 45 and 20 <= w_ <= 45 and 0.45 <= n / (h_ * w_) <= 0.85:  # filled, round-ish blob
        diode.append((sl[1].start, sl[0].start, sl[1].stop, sl[0].stop))
grey = (sat < 0.15) & (v > 0.7)
grey = ndimage.binary_closing(crop_mask(grey, B_BOX), iterations=3)
guard = rects_from(grey, min_px=3000, min_fill=0.15)
topm = rects_from(teal, min_px=2000, min_fill=0.5)

layers_b = {"TOPMETAL": (21, topm), "GUARD_RING": (22, guard)}

def um(p):
    return p * UM_PER_PX


# ---- manual trace of panel b structures the colour rule cannot separate (hatched guard ring, blocks) ----
# coordinates read from the overlay check image, +-10 photo px. Approximate.
def ring(outer, inset):
    o = (outer[0], outer[1], outer[2], outer[3])
    i = (outer[0] + inset, outer[1] + inset, outer[2] - inset, outer[3] - inset)
    return o, i
GUARD_MANUAL = []
MANUAL_LAYER = {}
left_o, left_i = (678, 91, 928, 599), (690, 103, 916, 587)
br_o, br_i = (935, 390, 1169, 599), (947, 402, 1157, 587)
MANUAL_RING = [(left_o, left_i), (br_o, br_i)]
MANUAL_RECT_GUARD = [(928, 148, 1175, 189)]          # top-right horizontal band
MANUAL_PAD = [(798, 326, 814, 343)]                  # small square in topmetal sensor
MANUAL_BLOCK = [(1025, 444, 1139, 558)]              # inner square in bottom-right block

# ---------- GDS ----------
lib = gdstk.Library(name="PHOTO2", unit=1e-6, precision=1e-9)
map_lines = []
Hp = H  # flip y so the picture is upright

def add_rects(cell, layer_no, rects, origin_px):
    ox, oy_bottom = origin_px  # y is flipped about the panel's bottom edge so the picture is upright
    for x0_, y0_, x1_, y1_ in rects:
        p0 = (um(x0_ - ox), um(oy_bottom - y1_))
        p1 = (um(x1_ - ox), um(oy_bottom - y0_))
        cell.add(gdstk.rectangle(p0, p1, layer=layer_no, datatype=0))

cell_a = lib.new_cell("PIXEL_A")
for n, (no, rects) in layers_a.items():
    add_rects(cell_a, no, rects, (A_BOX[0], A_BOX[3]))
    map_lines.append(f"A layer {no}: {n} ({len(rects)} rects)")

cell_b = lib.new_cell("SENSOR_B")
for n, (no, rects) in layers_b.items():
    add_rects(cell_b, no, rects, (B_BOX[0], B_BOX[3]))
    map_lines.append(f"B layer {no}: {n} ({len(rects)} rects)")
# diode circles as 24-gon polygons
for x0_, y0_, x1_, y1_ in diode:
    cx, cy = (x0_ + x1_) / 2, (y0_ + y1_) / 2
    rad = (x1_ - x0_) / 2
    pts = [(um(cx - B_BOX[0] + rad * np.cos(t)), um(B_BOX[3] - (cy + rad * np.sin(t))))
           for t in np.linspace(0, 2 * np.pi, 25)[:-1]]
    cell_b.add(gdstk.Polygon(pts, layer=23, datatype=0))
map_lines.append(f"B layer 23: DIODE ({len(diode)} circles)")

# manual geometry -> GDS (panel b cell)
def rect_poly(x0_, y0_, x1_, y1_):
    return gdstk.rectangle((um(x0_ - B_BOX[0]), um(B_BOX[3] - y1_)),
                           (um(x1_ - B_BOX[0]), um(B_BOX[3] - y0_)))
for o, i_ in MANUAL_RING:
    outer, inner = rect_poly(*o), rect_poly(*i_)
    for piece in gdstk.boolean(outer, inner, "not", layer=22, datatype=0):
        cell_b.add(piece)
for rr, lyr in [(MANUAL_RECT_GUARD, 22), (MANUAL_PAD, 24), (MANUAL_BLOCK, 25)]:
    for x0_, y0_, x1_, y1_ in rr:
        cell_b.add(gdstk.rectangle((um(x0_ - B_BOX[0]), um(B_BOX[3] - y1_)),
                                   (um(x1_ - B_BOX[0]), um(B_BOX[3] - y0_)), layer=lyr, datatype=0))
map_lines += ["B layer 22: GUARD_RING (manual: 2 ring frames + top band)",
              "B layer 24: PAD (manual, small square in topmetal)",
              "B layer 25: BLOCK (manual, inner square of bottom-right block)"]

lib.write_gds(f"{OUT}.gds")
# map file from the written geometry (counts per layer)
spec = {1: "A YELLOW", 2: "A ORANGE", 3: "A GREEN", 4: "A CYAN", 5: "A BLUE", 6: "A MAGENTA",
        7: "A RED", 8: "A WHITE", 21: "B TOPMETAL (sensor region)", 22: "B GUARD_RING (approx.)",
        23: "B DIODE (circle)", 24: "B PAD (small square)", 25: "B BLOCK (inner square)"}
counts = {}
for c in lib.cells:
    for poly in c.polygons:
        counts[poly.layer] = counts.get(poly.layer, 0) + 1
with open(f"{OUT}_gds_map.txt", "w") as f:
    f.write("GDS cells: PIXEL_A = panel a (colour-class rectangles), SENSOR_B = panel b (sensor structure)\n")
    f.write("Units: um. Panel width = 45 um. Panel b uses the same um/px as panel a (assumption).\n")
    f.write("GDS layer numbers (datatype 0) -> names:\n")
    for no in sorted(spec):
        f.write(f"  {no:>2}: {spec[no]}  ({counts.get(no, 0)} shapes)\n")
map_lines = []
print("map written")
print("A size um:", um(A_BOX[2]-A_BOX[0]), um(A_BOX[3]-A_BOX[1]))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
fig, ax = plt.subplots(figsize=(12, 6.7), dpi=110)
ax.imshow(arr)
for no, rects, col in [(21, topm, "cyan"), (22, guard, "lime")]:
    for x0_, y0_, x1_, y1_ in rects:
        ax.add_patch(Rectangle((x0_, y0_), x1_ - x0_, y1_ - y0_, fill=False, ec=col, lw=1.5))
for x0_, y0_, x1_, y1_ in diode:
    ax.add_patch(Circle(((x0_ + x1_) / 2, (y0_ + y1_) / 2), (x1_ - x0_) / 2, fill=False, ec="magenta", lw=1.5))
for box in (A_BOX, B_BOX):
    ax.add_patch(Rectangle((box[0], box[1]), box[2] - box[0], box[3] - box[1], fill=False, ec="yellow", lw=1, ls="--"))
ax.axis("off")
fig.savefig(f"{OUT}_overlay_check.png", bbox_inches="tight")
print("B boxes  topm", topm, "guard", guard, "diode", diode)

# ---------- DXF (same geometry; panel b shifted +60 um so the two panels do not overlap) ----------
import ezdxf
doc = ezdxf.new("R2010", setup=True)
msp = doc.modelspace()
NAMES = {1: "A_YELLOW", 2: "A_ORANGE", 3: "A_GREEN", 4: "A_CYAN", 5: "A_BLUE", 6: "A_MAGENTA",
         7: "A_RED", 8: "A_WHITE", 21: "B_TOPMETAL", 22: "B_GUARD_RING", 23: "B_DIODE",
         24: "B_PAD", 25: "B_BLOCK"}
for nm in NAMES.values():
    doc.layers.add(nm)
for c in lib.cells:
    dx = 60.0 if c.name == "SENSOR_B" else 0.0
    for poly in c.polygons:
        pts = [(x + dx, y) for x, y in poly.points]
        msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": NAMES.get(poly.layer, "OTHER")})
doc.saveas(f"{OUT}.dxf")

import pickle
pickle.dump({"A": layers_a, "B": layers_b, "diode": diode, "A_BOX": A_BOX, "B_BOX": B_BOX}, open(f"{OUT}_geom.pkl", "wb"))
