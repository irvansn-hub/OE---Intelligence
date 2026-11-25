"""Shared import and evidence validation for local files and future adapters."""
import csv
from datetime import date
from difflib import SequenceMatcher
from io import BytesIO, StringIO
import math
import re

from xml.etree.ElementTree import ParseError
from zipfile import BadZipFile, ZipFile

from openpyxl import load_workbook

from components.formatting import today

SOURCE_LABELS = {
    "GOVERNMENT": "Pemerintah", "ASSOCIATION": "Asosiasi / INKINDO",
    "KAI_HISTORICAL_CONTRACT": "Kontrak historis KAI", "KAI_HISTORICAL_HPS": "HPS historis KAI",
    "MANUFACTURER": "Pabrikan", "SUPPLIER_QUOTATION": "Penawaran pemasok",
    "MARKET_SURVEY": "Survei pasar", "MARKETPLACE": "Marketplace", "OTHER": "Lainnya",
}
PRICE_FIELDS = (
    "item_name", "category", "specification", "brand", "unit", "quantity", "price",
    "location", "region", "source_type", "source_name", "vendor", "observation_date",
    "url_reference", "notes",
)
FIELD_LABELS = dict(zip(PRICE_FIELDS, (
    "Barang / jasa", "Kategori", "Spesifikasi", "Merek", "Satuan", "Jumlah", "Harga asli per satuan",
    "Lokasi", "Wilayah", "Jenis sumber", "Nama sumber", "Pemasok", "Tanggal observasi",
    "URL / referensi", "Catatan",
)))
MARKET_TYPES = {"MANUFACTURER", "SUPPLIER_QUOTATION", "MARKET_SURVEY", "MARKETPLACE"}


def clean_text(value):
    empty = value is None or (isinstance(value, float) and math.isnan(value))
    return "" if empty else " ".join(str(value).split())


def canonical(value):
    return " ".join(re.findall(r"\w+", clean_text(value).casefold()))


def number(value):
    if not clean_text(value):
        return None
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError("Angka harus berhingga.")
    return parsed


def parse_date(value):
    if not clean_text(value) or isinstance(value, (int, float)):
        raise ValueError("Tanggal harus berupa tanggal Excel atau teks YYYY-MM-DD.")
    if isinstance(value, date):
        return value.date() if hasattr(value, "date") else value
    return date.fromisoformat(str(value).strip())


def read_upload(data, filename):
    ext = filename.lower().rsplit(".", 1)[-1]
    workbook = None
    try:
        if ext == "xlsx":
            with ZipFile(BytesIO(data)) as parts:
                if sum(part.file_size for part in parts.infolist()) > 25_000_000:
                    raise ValueError("Isi Excel terlalu besar setelah dibuka.")
            workbook = load_workbook(BytesIO(data), read_only=True, data_only=True)
            rows = workbook.worksheets[0].iter_rows(values_only=True)
        elif ext == "csv":
            contents = data.decode("utf-8-sig")
            try:
                dialect = csv.Sniffer().sniff(contents[:8192], delimiters=",;\t")
            except csv.Error:
                dialect = "excel"
            rows = csv.reader(StringIO(contents), dialect)
        else:
            raise ValueError("Gunakan file .xlsx atau .csv.")
        headers = [clean_text(value).lower() for value in next(rows, ())]
        named = [header for header in headers if header]
        if len(named) != len(set(named)):
            raise ValueError("Nama kolom harus unik.")
        records = []
        for values in rows:
            if not any(value is not None and value != "" for value in values):
                continue
            records.append({key: value for key, value in zip(headers, values) if key})
            if len(records) > 250:
                raise ValueError("Maksimal 250 baris sekali impor. Bagi file menjadi beberapa bagian.")
        return records, set(named)
    except (OSError, UnicodeError, IndexError, BadZipFile, csv.Error, ParseError) as exc:
        raise ValueError("File rusak atau tidak didukung. Gunakan template yang tersedia.") from exc
    finally:
        if workbook is not None:
            workbook.close()


def column_names(rows, columns):
    return set(columns) if columns is not None else {key for row in rows for key in row}


def validate_prices(rows, source=None, strict=False, columns=None):
    """Keep price defects as reviewable evidence. Annual references require valid prices."""
    from database.db import evidence_key

    required = {"item_name", "specification", "unit", "price", "observation_date"}
    if source is None:
        required |= {"source_type", "source_name"}
    missing = sorted(required - column_names(rows, columns))
    if missing:
        raise ValueError(f"Kolom wajib belum ada: {', '.join(missing)}.")
    valid, issues, seen = [], [], set()
    for line, raw in enumerate(rows, start=2):
        row = {k: clean_text(raw.get(k)) for k in PRICE_FIELDS}
        if source:
            row.update(source)
        row["source_type"] = row["source_type"].upper()
        row["is_demo"] = False
        errors, warnings = [], []
        for key in ("item_name", "specification", "unit", "source_name"):
            if not row[key]:
                errors.append(f"{key} wajib diisi")
        if row["source_type"] not in SOURCE_LABELS:
            errors.append("source_type tidak dikenal")
        for key, label in (("price", "harga"), ("quantity", "jumlah")):
            try:
                row[key] = number(raw.get(key))
            except (ValueError, TypeError, OverflowError):
                row[key] = None
                errors.append(f"{label} harus berupa angka tanpa simbol Rp")
        if row["price"] is None or row["price"] <= 0:
            (errors if strict else warnings).append("harga kosong, nol, atau negatif")
        if row["quantity"] is not None and row["quantity"] <= 0:
            warnings.append("jumlah nol atau negatif")
        try:
            row["observation_date"] = parse_date(raw.get("observation_date"))
            row.setdefault("effective_year", row["observation_date"].year)
            row.setdefault("effective_date", date(row["effective_year"], 1, 1))
            row.setdefault("version", "Bukti pasar")
        except (ValueError, TypeError, OverflowError):
            errors.append("observation_date harus berupa tanggal Excel atau YYYY-MM-DD")
        if not errors:
            key = evidence_key(row)
            if key in seen:
                warnings.append("duplikat identik dalam file; basis data menyimpan satu salinan")
            seen.add(key)
            valid.append(row)
        if errors or warnings:
            issues.append({"Baris": line, "Status": "Ditolak" if errors else "Tinjau",
                           "Rincian": "; ".join(errors + warnings)})
    return valid, issues


def validate_indices(rows, columns=None):
    required = {"year", "index_name", "adjustment_rate"}
    if not required.issubset(column_names(rows, columns)):
        raise ValueError("Kolom wajib: year, index_name, adjustment_rate.")
    valid, issues = [], []
    for line, row in enumerate(rows, start=2):
        try:
            year, rate = number(row["year"]), number(row["adjustment_rate"])
            name = clean_text(row["index_name"])
            if not name or year is None or not year.is_integer() or not 1900 <= year <= 2200:
                raise ValueError
            if rate is None or not -100 < rate <= 100:
                raise ValueError
            valid.append({"year": int(year), "index_name": name, "adjustment_rate": rate / 100})
        except (ValueError, TypeError, OverflowError):
            issues.append({"Baris": line, "Status": "Ditolak",
                           "Rincian": "Nama wajib, tahun 1900–2200, dan laju > −100 sampai 100 (persen)."})
    return valid, issues


def find_candidates(names, item_name):
    query = canonical(item_name)
    if not query:
        return []

    def matches(name):
        normalized = canonical(name)
        return bool(normalized) and (
            query in normalized or normalized in query or SequenceMatcher(None, query, normalized).ratio() >= .74
        )

    return [name for name in names if matches(name)]


def prepare_evidence(rows, context, recent_days=365):
    from engine.normalization import normalize_price

    rows = [{**row} for row in rows]
    as_of = parse_date(context.get("analysis_date", today()))
    seen = set()
    for row in rows:
        flags = []
        observed = parse_date(row["observation_date"])
        row["observation_date"] = observed.isoformat()
        row["age_days"] = (as_of - observed).days
        price = row["price"]
        invalid = price is None or not math.isfinite(price) or price <= 0
        if invalid:
            flags.append("Harga kosong, nol, atau negatif")
        unit_mismatch = canonical(context["unit"]) != canonical(row["unit"])
        if unit_mismatch:
            flags.append("Satuan berbeda")
        for key, message in (
            ("item_name", "Nama barang mirip; verifikasi kecocokan"),
            ("specification", "Kemungkinan spesifikasi berbeda"),
            ("brand", "Merek berbeda atau belum diketahui"),
            ("region", "Wilayah berbeda atau belum diketahui"),
        ):
            if canonical(context.get(key)) and canonical(context[key]) != canonical(row.get(key)):
                flags.append(message)
        if row.get("quantity") is None:
            flags.append("Jumlah referensi belum diketahui")
        elif row["quantity"] != context["quantity"]:
            flags.append("Jumlah pembelian berbeda")
        if row["age_days"] > recent_days:
            flags.append(f"Observasi berumur lebih dari {recent_days} hari")
        future = row["age_days"] < 0 or parse_date(row["effective_date"]) > as_of
        if future:
            flags.append("Observasi atau sumber belum berlaku pada tanggal analisis")
        duplicate_key = tuple(canonical(row.get(k)) for k in (
            "item_name", "specification", "brand", "unit", "vendor", "source_name", "region",
            "price", "quantity", "observation_date",
        ))
        duplicate = duplicate_key in seen
        if duplicate:
            flags.append("Kemungkinan duplikat")
        seen.add(duplicate_key)
        row["eligible"] = not (invalid or unit_mismatch or future)
        row["flags"] = flags
        row["decision"] = "REVIEW" if flags else "INCLUDE"
        row["justification"] = ""
        row["is_outlier"] = False
        row["adjusted_price"], row["index_factor"], row["index_note"] = normalize_price(
            price, observed.year, parse_date(context["target_date"]).year, context.get("rates", {})
        )
    return rows
