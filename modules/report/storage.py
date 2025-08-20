
from __future__ import annotations
from pathlib import Path
import json
import datetime as dt
from .utils import fs_safe

REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

def report_path(rid: str) -> Path:
    return REPORTS_DIR / f"{fs_safe(rid)}.json"

def attachments_dir(rid: str) -> Path:
    d = REPORTS_DIR / fs_safe(rid)
    d.mkdir(parents=True, exist_ok=True)
    return d

def read_json(p: Path) -> dict:
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception: return {}

def write_json(p: Path, data: dict) -> None:
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    tmp.replace(p)

def list_reports_for(oec: str | None) -> list[dict]:
    out = []
    for p in sorted(REPORTS_DIR.glob("*.json")):
        d = read_json(p)
        rid = d.get("meta", {}).get("id") or p.stem
        out.append({
            "id": rid,
            "title": d.get("meta", {}).get("title", rid),
            "oec": d.get("meta", {}).get("oec"),
            "created": d.get("meta", {}).get("created", ""),
        })
    if oec:
        out = [r for r in out if r.get("oec") == oec]
    out.sort(key=lambda r: r.get("created", ""), reverse=True)
    return out

def gen_report_id(oec: str) -> str:
    now = dt.datetime.now()
    return f"{now:%H:%M}_{now:%d.%m.%Y}_{oec}"

def ensure_skeleton(rid: str, oec: str) -> dict:
    now = dt.datetime.now().isoformat(timespec="seconds")
    return {
        "meta": {"id": rid, "oec": oec, "created": now, "title": rid, "version": 3},
        "event": {
            "datum_vzniku": dt.date.today().isoformat(),
            "cas_vzniku": dt.time(0,0,0).strftime("%H:%M:%S"),
            "datum_zpozorovani": dt.date.today().isoformat(),
            "cas_zpozorovani": dt.time(0,0,0).strftime("%H:%M:%S"),
            "datum_ohlaseni": dt.date.today().isoformat(),
            "cas_ohlaseni": dt.time(0,0,0).strftime("%H:%M:%S"),
            "adresa": {"kraj":"", "obec":"", "ulice":"", "cp":"", "co":"", "parcelni":"", "psc":""},
            "gps": {"lat": None, "lon": None, "pozn": ""},
        },
        "conditions": {"weather": "", "temperature_c": 0, "visibility": ""},
        "participants": {"owners": [], "users": []},
        "witnesses": "",
        "sketch": "",
        "attachments": [],
        "notes": "",
    }
