import argparse
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from ndvi import compare

SAMPLE = Path(__file__).parent / "sample_data"


def _load(src, keys, label):
    try:
        z = np.load(src, allow_pickle=False)
        return {k: np.asarray(z[k]) for k in keys}
    except KeyError as e:
        raise ValueError(f"{label}: missing key {e}") from None
    except Exception as e:
        raise ValueError(f"{label}: cannot read as .npz ({e})") from None


def load_inputs(date1, date2, farm):
    d1 = _load(date1, ("red", "nir", "valid"), "date1")
    d2 = _load(date2, ("red", "nir", "valid"), "date2")
    f = _load(farm, ("farm",), "farm")["farm"]
    shapes = {f"date1.{k}": v.shape for k, v in d1.items()} | {f"date2.{k}": v.shape for k, v in d2.items()} | {"farm": f.shape}
    if len(set(shapes.values())) != 1:
        raise ValueError(f"shape mismatch: {shapes}")
    if f.ndim != 2:
        raise ValueError(f"expected 2D arrays, got shape {f.shape}")
    return d1, d2, f


def _heatmap(arrays, path, result):
    farm = arrays["farm"]
    change = arrays["change"]
    lim = float(np.nanmax(np.abs(change))) if np.isfinite(change).any() else 1.0
    panels = [
        ("NDVI date 1", np.where(farm, arrays["ndvi1"], np.nan), "RdYlGn", -1, 1),
        ("NDVI date 2", np.where(farm, arrays["ndvi2"], np.nan), "RdYlGn", -1, 1),
        ("Change (date 2 - date 1)", change, "RdBu", -lim or -1, lim or 1),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.5))
    for ax, (title, data, cmap, lo, hi) in zip(axes, panels):
        cm = plt.get_cmap(cmap).with_extremes(bad="gray")
        im = ax.imshow(np.ma.masked_invalid(data), cmap=cm, vmin=lo, vmax=hi)
        ax.set_title(title)
        ax.set_xticks([])
        ax.set_yticks([])
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.suptitle(
        f"Index change only, not evidence of disease, cause or yield loss. Gray = cloud, invalid or outside farm.\n"
        f"usable {result['usable_pixels']}/{result['farm_pixels']} farm pixels, threshold {result['threshold']}"
    )
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def _csv(arrays, path):
    rows, cols = np.nonzero(arrays["farm"])
    fmt = lambda v: "" if np.isnan(v) else repr(float(v))
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["row", "col", "ndvi_date1", "ndvi_date2", "change", "usable"])
        for r, c in zip(rows, cols):
            w.writerow([r, c, fmt(arrays["ndvi1"][r, c]), fmt(arrays["ndvi2"][r, c]), fmt(arrays["change"][r, c]), int(arrays["usable"][r, c])])


def run(date1, date2, farm, threshold=None, out_dir="outputs"):
    if threshold is not None and threshold < 0:
        raise ValueError(f"threshold must be >= 0, got {threshold}")
    d1, d2, f = load_inputs(date1, date2, farm)
    result, arrays = compare(d1, d2, f, threshold)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(result, indent=2))
    _csv(arrays, out / "results.csv")
    _heatmap(arrays, out / "heatmap.png", result)
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Compare NDVI between two dates on a farm mask")
    p.add_argument("--date1", default=SAMPLE / "date1.npz")
    p.add_argument("--date2", default=SAMPLE / "date2.npz")
    p.add_argument("--farm", default=SAMPLE / "farm.npz")
    p.add_argument("--threshold", type=float)
    p.add_argument("--out", default="outputs")
    a = p.parse_args()
    try:
        print(json.dumps(run(a.date1, a.date2, a.farm, a.threshold, a.out), indent=2))
    except ValueError as e:
        raise SystemExit(f"error: {e}")
