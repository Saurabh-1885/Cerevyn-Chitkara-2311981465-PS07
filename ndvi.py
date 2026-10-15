import os

import numpy as np

NOTE = "An index decline does not by itself establish disease, cause or yield loss."


def ndvi(nir, red, valid):
    nir = np.asarray(nir, dtype=float)
    red = np.asarray(red, dtype=float)
    valid = np.asarray(valid, dtype=bool)
    if not nir.shape == red.shape == valid.shape:
        raise ValueError(f"shape mismatch: nir {nir.shape}, red {red.shape}, valid {valid.shape}")
    out = np.full(nir.shape, np.nan)
    with np.errstate(invalid="ignore", over="ignore"):
        den = nir + red
        ok = valid & np.isfinite(nir) & np.isfinite(red) & (np.abs(den) >= 1e-12)
        np.divide(nir - red, den, out=out, where=ok)
    return out


def _pct(a, b):
    return a / b * 100 if b else None


def _mean(a):
    return float(a.mean()) if a.size else None


def compare(d1, d2, farm, threshold=None):
    if threshold is None:
        threshold = float(os.environ.get("NDVI_DECLINE_THRESHOLD") or 0.05)
    farm = np.asarray(farm, dtype=bool)
    n1 = ndvi(d1["nir"], d1["red"], d1["valid"])
    n2 = ndvi(d2["nir"], d2["red"], d2["valid"])
    if not n1.shape == n2.shape == farm.shape:
        raise ValueError(f"shape mismatch: date1 {n1.shape}, date2 {n2.shape}, farm {farm.shape}")
    v1 = farm & np.isfinite(n1)
    v2 = farm & np.isfinite(n2)
    use = v1 & v2
    nf, n = int(farm.sum()), int(use.sum())
    change = n2[use] - n1[use]
    declined = int((change <= -threshold).sum())
    mc = _mean(change)
    result = {
        "status": "ok" if n else "no_usable_pixels",
        "farm_pixels": nf,
        "date1": {"valid_pixels": int(v1.sum()), "coverage_pct": _pct(int(v1.sum()), nf), "mean_ndvi": _mean(n1[v1])},
        "date2": {"valid_pixels": int(v2.sum()), "coverage_pct": _pct(int(v2.sum()), nf), "mean_ndvi": _mean(n2[v2])},
        "usable_pixels": n,
        "usable_pct": _pct(n, nf),
        "mean_ndvi_common_date1": _mean(n1[use]),
        "mean_ndvi_common_date2": _mean(n2[use]),
        "mean_change": mc,
        "threshold": threshold,
        "declined_pixels": declined,
        "declined_pct": _pct(declined, n),
        "decline_flag": bool(mc <= -threshold) if n else None,
        "note": NOTE,
    }
    arrays = {"ndvi1": n1, "ndvi2": n2, "change": np.where(use, n2 - n1, np.nan), "usable": use, "farm": farm}
    return result, arrays
