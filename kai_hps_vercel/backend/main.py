"""API HTTP untuk antarmuka Next.js. Mode Vercel hanya untuk data sintetis."""
from datetime import date, datetime
import json
import logging
import math
from typing import Literal
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, Response
import psycopg
from pydantic import BaseModel, ConfigDict, Field

from components.formatting import today
from database.db import as_json, make_observation, repository
from database.demo import demo_workspace
from engine.cleaning import (
    SOURCE_LABELS, find_candidates, parse_date, prepare_evidence, read_upload,
    validate_indices, validate_prices,
)
from engine.outlier import fences, outlier_reason
from engine.recommendation import analyze
from engine.statistics import summarize
from export.excel_report import analysis_workbook, template

app = FastAPI(title="KAI HPS Price Intelligence", docs_url=None, redoc_url=None)
LOG = logging.getLogger(__name__)
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
Decision = Literal["INCLUDE", "EXCLUDE", "REVIEW"]


class Context(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, allow_inf_nan=False)
    analysis_name: str = Field(min_length=1, max_length=160)
    item_name: str = Field(min_length=1, max_length=180)
    specification: str = Field(min_length=1, max_length=500)
    unit: str = Field(min_length=1, max_length=60)
    quantity: float = Field(gt=0)
    target_date: date
    category: str = Field(default="", max_length=160)
    brand: str = Field(default="", max_length=160)
    location: str = Field(default="", max_length=160)
    region: str = Field(default="", max_length=160)
    notes: str = Field(default="", max_length=2000)
    recent_days: int = Field(default=365, ge=30, le=730)
    minimum_market: int = Field(default=5, ge=2, le=100)
    index_name: str = Field(default="", max_length=200)
    enable_forecast: bool = True


class Choice(BaseModel):
    decision: Decision
    justification: str = Field(default="", max_length=2000)


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    context: Context
    observations: list[dict] = Field(max_length=2000)
    indices: list[dict] = Field(default_factory=list, max_length=300)
    choices: dict[str, Choice] = Field(default_factory=dict, max_length=2000)
    actual_unit_price: float | None = Field(default=None, gt=0)
    save: bool = False


class RowsRequest(BaseModel):
    rows: list[dict] = Field(min_length=1, max_length=250)
    meta: dict | None = None


class SearchRequest(BaseModel):
    item_name: str = Field(min_length=1, max_length=180)
    names: list[str] = Field(max_length=2000)


class Exploration(BaseModel):
    values: list[float | None] = Field(max_length=2000)


@app.exception_handler(ValueError)
def invalid_data(_, exc):
    return JSONResponse({"detail": str(exc)}, status_code=422)


@app.exception_handler(psycopg.Error)
def db_error(_, exc):
    LOG.error("Kesalahan penyimpanan PostgreSQL (%s)", type(exc).__name__)
    return JSONResponse({"detail": "Penyimpanan PostgreSQL tidak dapat diakses."}, status_code=503)


@app.middleware("http")
async def do_not_cache(request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/workspace")
def workspace():
    repo = repository()
    data = repo.workspace() if repo else demo_workspace()
    return {**data, "persistent": repo is not None, "today": today().isoformat(),
            "source_labels": SOURCE_LABELS}


def source_meta(meta):
    if not meta:
        return None
    try:
        source_type = meta["source_type"]
        source_name = str(meta["source_name"]).strip()
        version = str(meta["version"]).strip()
        year = int(meta["effective_year"])
        if source_type not in SOURCE_LABELS or not source_name or not version or not 1900 <= year <= 2200:
            raise ValueError
        return {
            "source_type": source_type, "source_name": source_name, "version": version,
            "effective_year": year, "effective_date": parse_date(meta["effective_date"]),
        }
    except (KeyError, ValueError, TypeError, OverflowError) as exc:
        raise ValueError("Lengkapi jenis, nama, tahun, tanggal efektif, dan versi sumber.") from exc


@app.post("/api/import/{kind}/preview")
def preview(kind: Literal["evidence", "reference", "index"], file: UploadFile = File(...), meta: str = Form("{}")):
    data = file.file.read(3_000_001)
    if len(data) > 3_000_000:
        raise HTTPException(413, "Maksimal 3 MB per unggahan versi web.")
    records, headers = read_upload(data, file.filename or "")
    if kind == "index":
        rows, issues = validate_indices(records, headers)
    else:
        source = source_meta(json.loads(meta)) if kind == "reference" else None
        if kind == "reference" and source is None:
            raise ValueError("Isi informasi edisi referensi.")
        rows, issues = validate_prices(records, source, strict=kind == "reference", columns=headers)
    return as_json({"rows": rows, "issues": issues})


@app.post("/api/import/{kind}")
def save_import(kind: Literal["evidence", "reference", "index"], payload: RowsRequest):
    repo = repository()
    if kind == "index":
        try:
            records = [{**row, "adjustment_rate": float(row["adjustment_rate"]) * 100}
                       for row in payload.rows]
        except (ValueError, TypeError, KeyError) as exc:
            raise ValueError("Laju indeks tidak valid.") from exc
        rows, issues = validate_indices(records)
        rows = [{**row, "is_demo": True} for row in rows]
        return {"rows": repo.import_indices(rows) if repo else rows, "issues": issues}

    source = source_meta(payload.meta) if kind == "reference" else None
    if kind == "reference" and source is None:
        raise ValueError("Isi informasi edisi referensi.")
    raw, issues = validate_prices(payload.rows, source, strict=kind == "reference")
    rows = [make_observation({**row, "is_demo": True}) for row in raw]
    imported = repo.import_prices(rows) if repo else list({r["fingerprint"]: r for r in rows}.values())
    return {"rows": imported, "issues": issues}


@app.post("/api/search")
def search(payload: SearchRequest):
    return find_candidates(payload.names, payload.item_name)


@app.post("/api/analyze")
def run_analysis(payload: AnalysisRequest):
    repo = repository()
    ctx = payload.context.model_dump(mode="json")
    as_of = today()
    if payload.context.target_date < as_of:
        raise ValueError("Tanggal pengadaan harus hari ini atau setelahnya.")
    ctx["analysis_date"] = as_of.isoformat()
    ctx["index_demo"] = bool(ctx["index_name"])
    ctx["rates"] = {
        str(row["year"]): row["adjustment_rate"]
        for row in (repo.indices() if repo else payload.indices)
        if row.get("index_name") == ctx["index_name"] and isinstance(row.get("adjustment_rate"), (int, float))
        and math.isfinite(row["adjustment_rate"]) and -1 < row["adjustment_rate"] <= 1
    }
    if repo:
        keys = [r.get("price_observation_id", "") for r in payload.observations]
        rows = as_json(repo.prices(keys))
    else:
        unique = {}
        for row in payload.observations:
            try:
                price = row["price"]
                if price is not None and (not isinstance(price, (int, float)) or not math.isfinite(price)):
                    raise ValueError
                if row["quantity"] is not None and not isinstance(row["quantity"], (int, float)):
                    raise ValueError
                for field in ("item_name", "unit", "specification", "source_type", "source_name", "vendor",
                              "observation_date", "effective_date", "version", "price_observation_id",
                              "category", "brand", "location", "region", "url_reference", "notes", "created_at"):
                    if not isinstance(row[field], str):
                        raise ValueError
                if not isinstance(row["effective_year"], int):
                    raise ValueError
                unique[row["price_observation_id"]] = {**row, "is_demo": True}
            except (KeyError, ValueError, TypeError) as exc:
                raise ValueError("Bukti demo tidak valid. Cari kembali harga referensi.") from exc
        rows = list(unique.values())
    rows.sort(key=lambda r: (str(r["observation_date"]), r["price_observation_id"]), reverse=True)
    prepared = prepare_evidence(rows, ctx, ctx["recent_days"])
    for row in prepared:
        choice = payload.choices.get(row["price_observation_id"])
        if choice:
            row.update(decision=choice.decision, justification=choice.justification.strip())
    result = analyze(prepared, ctx)
    snapshot = {
        "analysis_id": None, "context": ctx, "result": result, "evidence": prepared,
        "actual_unit_price": payload.actual_unit_price,
    }
    if payload.save:
        if not result["stats"]["n"]:
            raise ValueError("Sertakan minimal satu bukti dengan harga valid.")
        if any(r["decision"] == "INCLUDE" and not r["eligible"] for r in prepared):
            raise ValueError("Tinjau kembali bukti yang tidak memenuhi syarat sebelum menyimpan.")
        if any(r["decision"] == "EXCLUDE" and not r["justification"] for r in prepared):
            raise ValueError("Isi justifikasi untuk semua bukti yang dikeluarkan.")
        snapshot["analysis_id"] = str(uuid4())
        ctx["saved_at"] = datetime.now(ZoneInfo("Asia/Jakarta")).isoformat(timespec="seconds")
        if repo:
            repo.save_analysis(as_json(snapshot))
    return snapshot


@app.post("/api/statistics")
def explore(payload: Exploration):
    stats = summarize(payload.values)
    low, high = fences(stats)
    return {"stats": stats, "flags": [outlier_reason(v, low, high) if v is not None else ""
                                     for v in payload.values]}


def download(content, name):
    return Response(content=content, media_type=XLSX,
                    headers={"Content-Disposition": f'attachment; filename="{name}.xlsx"'})


@app.get("/api/templates/{kind}")
def templates(kind: Literal["evidence", "reference", "index"]):
    names = {"evidence": "Template_Bukti_Harga", "reference": "Template_Referensi_Tahunan", "index": "Template_Indeks"}
    return download(template(kind), names[kind])


@app.get("/api/analyses/{key}")
def saved_analysis(key: str):
    repo = repository()
    snapshot = repo.load_analysis(key) if repo else next(
        (row for row in demo_workspace()["analyses"] if row["analysis_id"] == key), None
    )
    if snapshot is None:
        raise HTTPException(404, "Analisis tidak ditemukan.")
    return snapshot


@app.get("/api/analyses/{key}/report")
def saved_report(key: str):
    return download(analysis_workbook(saved_analysis(key)), "Analisis_HPS")


@app.post("/api/report")
def browser_report(snapshot: dict):
    if repository():
        raise HTTPException(405, "Buka laporan dari riwayat yang tersimpan.")
    try:
        for row in snapshot["evidence"]:
            row["is_demo"] = True
        return download(analysis_workbook(snapshot), "Analisis_HPS_Demo")
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Analisis tidak dapat diekspor. Simpan kembali dan coba lagi.") from exc
