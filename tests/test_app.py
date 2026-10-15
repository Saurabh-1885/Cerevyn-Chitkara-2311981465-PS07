import io
import json
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

import app as app_module

SAMPLE = Path(__file__).parent.parent / "sample_data"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "OUT", tmp_path / "outputs")
    return TestClient(app_module.app)


def npz(**arrays):
    buf = io.BytesIO()
    np.savez(buf, **arrays)
    buf.seek(0)
    return buf


def test_default_compare_matches_expected(client):
    r = client.post("/compare")
    assert r.status_code == 200
    expected = json.loads((SAMPLE / "expected.json").read_text())
    body = r.json()
    for k, v in expected.items():
        assert body[k] == pytest.approx(v)
    assert "disease" in body["note"]


def test_heatmap_and_csv_served_after_run(client):
    client.post("/compare")
    png = client.get("/heatmap.png")
    assert png.status_code == 200 and png.content[:8] == b"\x89PNG\r\n\x1a\n"
    lines = client.get("/results.csv").text.splitlines()
    assert lines[0] == "row,col,ndvi_date1,ndvi_date2,change,usable"
    assert len(lines) == 101
    assert client.get("/results.json").json()["usable_pixels"] == 78


def test_threshold_query_changes_flag(client):
    r = client.post("/compare", params={"threshold": 0.01})
    assert r.json()["threshold"] == 0.01 and r.json()["decline_flag"] is True


def test_negative_threshold_is_422(client):
    assert client.post("/compare", params={"threshold": -1}).status_code == 422


def test_mismatched_shapes_is_422(client):
    bad = npz(red=np.ones((3, 3)), nir=np.ones((3, 3)), valid=np.ones((3, 3), bool))
    r = client.post("/compare", files={"date2": ("date2.npz", bad)})
    assert r.status_code == 422 and "shape mismatch" in r.json()["detail"]


def test_missing_key_and_garbage_are_422(client):
    r = client.post("/compare", files={"date1": ("d.npz", npz(red=np.ones((12, 12))))})
    assert r.status_code == 422 and "missing key" in r.json()["detail"]
    r = client.post("/compare", files={"date1": ("d.npz", io.BytesIO(b"not an npz"))})
    assert r.status_code == 422


def test_all_cloud_date2_has_no_usable_pixels(client):
    with open(SAMPLE / "date2_all_cloud.npz", "rb") as f:
        r = client.post("/compare", files={"date2": ("date2.npz", f)})
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "no_usable_pixels" and body["usable_pixels"] == 0
    assert body["mean_change"] is None and body["decline_flag"] is None
    assert client.get("/heatmap.png").status_code == 200


def test_get_before_any_run_is_404(client):
    for name in ("heatmap.png", "results.csv", "results.json"):
        r = client.get(f"/{name}")
        assert r.status_code == 404 and "POST /compare" in r.json()["detail"]
