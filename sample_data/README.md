# Sample data

All files here are **synthetic**. They were built by `make_sample.py` (no randomness, re-running reproduces them exactly). No real satellite data is used.

Each grid is 12x12. Healthy pixels have NIR 0.6 and Red 0.2 (NDVI 0.5).

| File | Contents |
|------|----------|
| `farm.npz` | `farm`: bool mask, True everywhere except the 1-pixel border (100 farm pixels) |
| `date1.npz` | `red`, `nir`, `valid`. Cloud (`valid` False) on the top 2 rows. Three farm pixels at row 3, cols 2-4 have red = nir = 0 (zero denominator) |
| `date2.npz` | `red`, `nir`, `valid`. Cloud on the right 2 columns. A 4x4 patch (rows 6-9, cols 3-6) drops to NIR 0.4, Red 0.2 (NDVI 0.333) |
| `date2_all_cloud.npz` | date2 with every pixel invalid, for the no usable pixels case |
| `expected.json` | Hand derived results of comparing date1 and date2 inside the farm at threshold 0.05 |

## How the expected numbers follow

- Date1 loses 10 farm pixels to cloud and 3 to zero denominators: 87 valid (87.0%).
- Date2 loses 10 farm pixels to cloud: 90 valid (90.0%).
- One farm pixel (row 1, col 10) is cloudy in both, so 22 distinct farm pixels are unusable and 78 are usable (78.0%).
- The 16 patch pixels are all usable and each changes by 1/3 - 1/2 = -1/6, so mean change is -16/6/78 = -0.0342 and 16 pixels (20.5% of usable) decline by at least 0.05.
- The mean change is smaller than the 0.05 threshold, so the date level decline flag is false even though 16 pixels declined.
