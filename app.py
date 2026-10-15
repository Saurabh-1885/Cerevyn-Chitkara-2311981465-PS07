from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from report import SAMPLE, run

app = FastAPI(title="NDVI change monitor")
OUT = Path("outputs")
FILES = {"heatmap.png": "image/png", "results.csv": "text/csv", "results.json": "application/json"}


@app.post("/compare")
def compare_dates(
    date1: UploadFile | None = File(None),
    date2: UploadFile | None = File(None),
    farm: UploadFile | None = File(None),
    threshold: float | None = None,
):
    src = [u.file if u else SAMPLE / name for u, name in ((date1, "date1.npz"), (date2, "date2.npz"), (farm, "farm.npz"))]
    try:
        return run(*src, threshold, OUT)
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.get("/{name}")
def get_file(name: str):
    if name not in FILES:
        raise HTTPException(404, f"unknown file, expected one of {sorted(FILES)}")
    p = OUT / name
    if not p.exists():
        raise HTTPException(404, f"{name} not found, run POST /compare first")
    return FileResponse(p, media_type=FILES[name])
