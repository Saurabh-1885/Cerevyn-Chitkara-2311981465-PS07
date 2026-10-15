import json
from pathlib import Path

import numpy as np

N = 12
out = Path(__file__).parent / "sample_data"
out.mkdir(exist_ok=True)

farm = np.zeros((N, N), bool)
farm[1:-1, 1:-1] = True

red1 = np.full((N, N), 0.2)
nir1 = np.full((N, N), 0.6)
red1[3, 2:5] = nir1[3, 2:5] = 0.0
valid1 = np.ones((N, N), bool)
valid1[:2] = False

red2 = np.full((N, N), 0.2)
nir2 = np.full((N, N), 0.6)
nir2[6:10, 3:7] = 0.4
valid2 = np.ones((N, N), bool)
valid2[:, -2:] = False

np.savez(out / "farm.npz", farm=farm)
np.savez(out / "date1.npz", red=red1, nir=nir1, valid=valid1)
np.savez(out / "date2.npz", red=red2, nir=nir2, valid=valid2)
np.savez(out / "date2_all_cloud.npz", red=red2, nir=nir2, valid=np.zeros((N, N), bool))

# 100 farm pixels; date1 loses 10 cloud + 3 zero-denominator, date2 loses 10 cloud, 1 pixel overlaps
farm_px, v1, v2, usable, patch = 100, 100 - 10 - 3, 100 - 10, 100 - 22, 16
drop = 0.5 - 1 / 3
common2 = ((usable - patch) * 0.5 + patch / 3) / usable
expected = {
    "status": "ok",
    "farm_pixels": farm_px,
    "date1": {"valid_pixels": v1, "coverage_pct": v1 / farm_px * 100, "mean_ndvi": 0.5},
    "date2": {"valid_pixels": v2, "coverage_pct": v2 / farm_px * 100, "mean_ndvi": ((v2 - patch) * 0.5 + patch / 3) / v2},
    "usable_pixels": usable,
    "usable_pct": usable / farm_px * 100,
    "mean_ndvi_common_date1": 0.5,
    "mean_ndvi_common_date2": common2,
    "mean_change": -patch * drop / usable,
    "threshold": 0.05,
    "declined_pixels": patch,
    "declined_pct": patch / usable * 100,
    "decline_flag": False,
}
(out / "expected.json").write_text(json.dumps(expected, indent=2) + "\n")
