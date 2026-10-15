import json
from pathlib import Path

import numpy as np
import pytest

from ndvi import compare, ndvi

SAMPLE = Path(__file__).parent.parent / "sample_data"


def date(nir, red, valid=True):
    nir = np.asarray(nir, dtype=float)
    return {"nir": nir, "red": np.broadcast_to(np.asarray(red, dtype=float), nir.shape), "valid": np.broadcast_to(valid, nir.shape)}


def flat(d, prefix=""):
    for k, v in d.items():
        if isinstance(v, dict):
            yield from flat(v, f"{prefix}{k}.")
        else:
            yield prefix + k, v


def test_known_value():
    assert ndvi([0.6], [0.2], [True])[0] == pytest.approx(0.5)


def test_zero_denominator_is_nan_and_excluded():
    nir = np.array([[0.0, 0.3, 0.6, 0.6]])
    red = np.array([[0.0, -0.3, 0.2, 0.2]])
    out = ndvi(nir, red, np.ones(nir.shape, bool))
    assert np.isnan(out[0, :2]).all()
    assert out[0, 2:] == pytest.approx([0.5, 0.5])
    res, _ = compare(date(nir, red), date(nir, red), np.ones(nir.shape, bool))
    assert res["usable_pixels"] == 2


def test_invalid_pixel_is_nan_not_zero():
    out = ndvi([0.6, 0.6, np.nan, 0.6], [0.2, 0.2, 0.2, np.inf], [True, False, True, True])
    assert out[0] == pytest.approx(0.5)
    assert np.isnan(out[1:]).all()


def test_entirely_masked_area_has_no_usable_pixels():
    nir = np.full((3, 3), 0.6)
    res, arrays = compare(date(nir, 0.2, False), date(nir, 0.2, False), np.ones((3, 3), bool))
    assert res["status"] == "no_usable_pixels"
    assert res["usable_pixels"] == 0
    assert res["mean_change"] is None and res["decline_flag"] is None
    assert res["mean_ndvi_common_date1"] is None and res["mean_ndvi_common_date2"] is None
    assert np.isnan(arrays["change"]).all()
    json.dumps(res)


def test_different_cloud_masks_use_intersection():
    nir = np.full((4, 4), 0.6)
    v1 = np.ones((4, 4), bool)
    v1[:2] = False
    v2 = np.ones((4, 4), bool)
    v2[:, 2:] = False
    farm = np.ones((4, 4), bool)
    res, arrays = compare(date(nir, 0.2, v1), date(nir, 0.2, v2), farm)
    assert res["date1"]["valid_pixels"] == 8 and res["date2"]["valid_pixels"] == 8
    assert res["usable_pixels"] == 4
    assert res["usable_pct"] == pytest.approx(25.0)
    assert (arrays["usable"] == (v1 & v2)).all()


def test_decline_flag_respects_threshold(monkeypatch):
    farm = np.ones((2, 2), bool)
    d1, d2 = date(np.full((2, 2), 0.6), 0.2), date(np.full((2, 2), 0.4), 0.2)
    res, _ = compare(d1, d2, farm)
    assert res["threshold"] == 0.05
    assert res["mean_change"] == pytest.approx(-1 / 6)
    assert res["decline_flag"] is True and res["declined_pixels"] == 4
    res, _ = compare(d1, d2, farm, threshold=0.2)
    assert res["decline_flag"] is False and res["declined_pixels"] == 0
    monkeypatch.setenv("NDVI_DECLINE_THRESHOLD", "0.2")
    res, _ = compare(d1, d2, farm)
    assert res["threshold"] == 0.2 and res["decline_flag"] is False


def test_shape_mismatch_raises():
    with pytest.raises(ValueError, match="shape"):
        compare(date(np.full((3, 3), 0.6), 0.2), date(np.full((3, 3), 0.6), 0.2), np.ones((2, 2), bool))


def test_sample_data_matches_expected():
    d1, d2 = dict(np.load(SAMPLE / "date1.npz")), dict(np.load(SAMPLE / "date2.npz"))
    farm = np.load(SAMPLE / "farm.npz")["farm"]
    expected = json.loads((SAMPLE / "expected.json").read_text())
    res, _ = compare(d1, d2, farm)
    res.pop("note")
    assert dict(flat(res)) == pytest.approx(dict(flat(expected)))


def test_sample_all_cloud_has_no_usable_pixels():
    d1, d2 = dict(np.load(SAMPLE / "date1.npz")), dict(np.load(SAMPLE / "date2_all_cloud.npz"))
    res, _ = compare(d1, d2, np.load(SAMPLE / "farm.npz")["farm"])
    assert res["status"] == "no_usable_pixels"
    assert res["date2"]["coverage_pct"] == 0
