# PS07 Satellite Vegetation Change Monitor

[![ci](https://github.com/Saurabh-1885/Cerevyn-Chitkara-2311981465-PS07/actions/workflows/ci.yml/badge.svg)](https://github.com/Saurabh-1885/Cerevyn-Chitkara-2311981465-PS07/actions/workflows/ci.yml)

| | |
|---|---|
| Problem ID | PS07 |
| Candidate | Saurabh Gupta |
| Roll No | 2311981465 |
| Branch | BE CSE |
| University | Chitkara University, HP |

## Problem

Compare a vegetation index (NDVI) for a farm area across two dates. NDVI must be computed correctly, invalid and cloud pixels must be excluded, and the comparison must be reproducible.

## Approach

- NDVI = (NIR - Red) / (NIR + Red), computed per pixel in `ndvi.py`.
- A pixel gets NaN, never 0, when it is flagged invalid (`valid` False), when `|NIR + Red| < 1e-12`, or when NIR or Red is not finite.
- Per date, coverage is valid farm pixels / farm pixels, and the date mean uses that date's own valid farm pixels.
- The comparison area is the farm pixels with a finite NDVI on both dates. Mean change (date 2 - date 1) and per-pixel change are computed only there, so different cloud masks on the two dates cannot bias the result.
- A pixel declines when its change is <= -threshold. The date level flag `decline_flag` is set when the mean change is <= -threshold. The threshold is an absolute NDVI drop, default 0.05.
- Configure the threshold with the `NDVI_DECLINE_THRESHOLD` environment variable (see `.env.example`), the `--threshold` CLI option, or the `threshold` query parameter on the API. Order of precedence: explicit value, then env var, then 0.05.
- If no pixel is usable the result has `status: "no_usable_pixels"` and null means, change and flag. No exception is raised.
- **An index decline does not by itself establish disease, cause or yield loss.** This text is included in every result as `note` and printed on the heatmap.

## Input schema

Each file is a NumPy `.npz`. All arrays must be 2D with the same shape.

| File | Keys |
|---|---|
| date file (one per date) | `red` float, `nir` float, `valid` bool (True = clear pixel) |
| farm file | `farm` bool (True = farm pixel) |

A missing key, an unreadable file or a shape mismatch raises `ValueError` with a message (CLI exits with `error: ...`, API returns 422).

## Setup (Windows)

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Python 3.11 or newer. CI runs 3.11; local development used 3.14.3.

Dependency versions (from `requirements.txt`):

| Package | Version |
|---|---|
| numpy | 2.4.6 |
| matplotlib | 3.11.2 |
| fastapi | 0.143.1 |
| uvicorn | 0.54.0 |
| python-multipart | 0.0.32 |
| httpx | 0.28.1 |
| pytest | 9.1.1 |

## Run

CLI on the bundled sample data (writes `outputs/results.json`, `outputs/results.csv`, `outputs/heatmap.png`):

```
.venv\Scripts\python report.py
.venv\Scripts\python report.py --date1 a.npz --date2 b.npz --farm farm.npz --threshold 0.1 --out outputs
```

API:

```
.venv\Scripts\python -m uvicorn app:app
```

- `POST /compare` with optional multipart files `date1`, `date2`, `farm` (the bundled sample is used for any file not sent) and optional `threshold` query parameter. Returns the result JSON and writes the output files.
- `GET /results.json`, `GET /results.csv`, `GET /heatmap.png` download the outputs of the last run.
- Interactive docs at `http://127.0.0.1:8000/docs`.

Tests:

```
.venv\Scripts\python -m pytest
```

## Sample data and output

`sample_data/` holds synthetic 12x12 grids built by `make_sample.py` (no randomness). Healthy pixels have NIR 0.6 and Red 0.2 (NDVI 0.5). The farm is every pixel except the 1-pixel border (100 pixels).

- Date 1: cloud on the top 2 rows and three farm pixels with Red = NIR = 0 (zero denominator).
- Date 2: cloud on the right 2 columns and a 4x4 patch where NIR drops to 0.4 (NDVI 0.333).
- `sample_data/expected.json` holds the hand derived expected values; `sample_data/README.md` shows the derivation.

Output of `python report.py` (`outputs/results.json`):

```json
{
  "status": "ok",
  "farm_pixels": 100,
  "date1": {
    "valid_pixels": 87,
    "coverage_pct": 87.0,
    "mean_ndvi": 0.49999999999999994
  },
  "date2": {
    "valid_pixels": 90,
    "coverage_pct": 90.0,
    "mean_ndvi": 0.4703703703703703
  },
  "usable_pixels": 78,
  "usable_pct": 78.0,
  "mean_ndvi_common_date1": 0.4999999999999999,
  "mean_ndvi_common_date2": 0.46581196581196577,
  "mean_change": -0.03418803418803418,
  "threshold": 0.05,
  "declined_pixels": 16,
  "declined_pct": 20.51282051282051,
  "decline_flag": false,
  "note": "An index decline does not by itself establish disease, cause or yield loss."
}
```

The 16 patch pixels each drop by 1/6, so 20.5% of usable pixels decline by at least the threshold, but the mean change (-0.034) is smaller than 0.05, so the date level flag is false. Lower the threshold (for example `--threshold 0.03`) to see it set.

Heatmap (NDVI date 1, NDVI date 2, change; gray = cloud, invalid or outside the farm):

![heatmap](outputs/heatmap.png)

## Required checks and tests

| Required check | Test |
|---|---|
| NIR 0.6, Red 0.2 gives NDVI 0.5 | `test_known_value` |
| Zero denominators are never given a value | `test_zero_denominator_is_nan_and_excluded` |
| Invalid pixels are NaN, not 0 | `test_invalid_pixel_is_nan_not_zero` |
| Entirely masked area | `test_entirely_masked_area_has_no_usable_pixels`, `test_sample_all_cloud_has_no_usable_pixels`, `test_all_cloud_date2_has_no_usable_pixels` |
| Different cloud masks between dates | `test_different_cloud_masks_use_intersection` |
| Threshold is configurable | `test_decline_flag_respects_threshold`, `test_threshold_query_changes_flag` |
| Shape mismatch, missing key, bad file | `test_shape_mismatch_raises`, `test_mismatched_shapes_is_422`, `test_missing_key_and_garbage_are_422` |
| Sample data matches expected outputs | `test_sample_data_matches_expected`, `test_default_compare_matches_expected` |
| API outputs and negative threshold | `test_heatmap_and_csv_served_after_run`, `test_negative_threshold_is_422`, `test_get_before_any_run_is_404` |

## Azure

Deployment is planned, not done. See [docs/azure-plan.md](docs/azure-plan.md).

## Demo

Demo video: https://github.com/Saurabh-1885/Cerevyn-Chitkara-2311981465-PS07/blob/main/docs/demo.mp4

## Limitations

- Synthetic data only; no real satellite imagery was used or tested.
- NDVI only; no other indices.
- No georeferencing or reprojection. Inputs must already be aligned grids of the same shape.
- Every pixel has equal weight; pixel area and partial pixels are ignored.
- Single user, local `outputs/` folder. Each run overwrites the previous outputs.
- Cloud masks are supplied in the `valid` array; clouds are not detected.

## Contributions

AI tools were used for scaffolding; I reviewed and can explain all code.
