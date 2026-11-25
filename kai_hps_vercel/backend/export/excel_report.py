"""Laporan XLSX yang dapat dibuka tanpa menjalankan ulang analisis."""
from datetime import date
import json
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from components.formatting import DEMO
from engine.cleaning import FIELD_LABELS, PRICE_FIELDS, SOURCE_LABELS

CURRENCY = '"Rp" #,##0;[Red]("Rp" #,##0)'
DECISION = {"INCLUDE": "Sertakan", "EXCLUDE": "Keluarkan", "REVIEW": "Tinjau"}
STAT_LABELS = {
    "n": "Jumlah (N)", "min": "Minimum", "max": "Maksimum", "mean": "Rata-rata",
    "median": "Median", "std": "Simpangan baku sampel", "cv": "Koefisien variasi",
    "p10": "P10", "p25": "P25", "p75": "P75", "p90": "P90", "iqr": "IQR",
}


def _content(ws, headers, records, widths=None, currency=()):
    ws.append(headers)
    for row in records:
        ws.append(list(row))
    ws.freeze_panes = "A2"
    ws.sheet_view.showGridLines = False
    ws.auto_filter.ref = ws.dimensions
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_title_rows = "1:1"
    ws.page_setup.orientation = "landscape" if len(headers) > 4 else "portrait"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.row_dimensions[1].height = 32
    for cell in ws[1]:
        cell.fill = PatternFill("solid", fgColor="172C50")
        cell.font = Font(name="Calibri", bold=True, color="FFFFFF")
        cell.alignment = Alignment(vertical="center", wrap_text=True)
        ws.column_dimensions[cell.column_letter].width = (widths or {}).get(cell.column, 21)
    for row in list(ws.rows)[1:]:
        height = 24
        for cell in row:
            if cell.data_type == "f" or cell.data_type == "e":
                cell.data_type = "s"
            if cell.row % 2 == 0:
                cell.fill = PatternFill("solid", fgColor="EEF3F9")
            cell.font = Font(name="Calibri", color="172C50", size=11)
            cell.alignment = Alignment(vertical="center", wrap_text=True)
            if cell.column in currency and isinstance(cell.value, (int, float)):
                cell.number_format = CURRENCY
            if isinstance(cell.value, str):
                width = int(ws.column_dimensions[get_column_letter(cell.column)].width) - 2
                height = max(height, 15 * (1 + len(cell.value) // max(1, width)))
        ws.row_dimensions[row[0].row].height = min(height, 180)


def _bytes(wb):
    out = BytesIO()
    wb.save(out)
    return out.getvalue()


def template(kind):
    columns = {
        "evidence": PRICE_FIELDS, "reference": tuple(k for k in PRICE_FIELDS
                                                    if k not in {"source_name", "source_type"}),
        "index": ("year", "index_name", "adjustment_rate"),
    }[kind]
    wb = Workbook()
    ws = wb.active
    ws.title = "Data"
    _content(ws, list(columns), [], {n: 22 for n in range(1, len(columns) + 1)})
    field_help = {
        "item_name": "Wajib. Gunakan nama yang konsisten.", "specification": "Wajib. Tulis spesifikasi pembanding.",
        "unit": "Wajib. Contoh unit, buah, orang-bulan.", "quantity": "Jumlah yang tercakup dalam bukti.",
        "price": "Harga per satuan dalam Rupiah. Masukkan angka. Untuk referensi tahunan, wajib positif.",
        "source_type": "Wajib untuk bukti. Pilih satu kode dari daftar di bawah.",
        "source_name": "Wajib untuk bukti. Nama dokumen, survei, atau penawaran.",
        "observation_date": "Wajib. Tanggal Excel atau YYYY-MM-DD.",
        "adjustment_rate": "Isi persen sebagai angka. Contoh 3,2 (Excel lokal) berarti 3,2%.",
        "year": "Wajib. Tahun penerapan indeks.", "index_name": "Wajib. Nama seri indeks.",
    }
    instructions = [(col, field_help.get(col, FIELD_LABELS.get(col, col) + " jika tersedia.")) for col in columns]
    if kind == "evidence":
        instructions += [(key, label) for key, label in SOURCE_LABELS.items()]
    _content(wb.create_sheet("Petunjuk"), ["Kolom / kode", "Cara mengisi"], instructions, {1: 33, 2: 80})
    return _bytes(wb)


def analysis_workbook(snapshot):
    context, result, evidence = (snapshot[key] for key in ("context", "result", "evidence"))
    stats = result["stats"]
    wb = Workbook()
    summary = wb.active
    summary.title = "Ringkasan Eksekutif"
    demo = any(r["is_demo"] for r in evidence) or context.get("index_demo", False)
    rows = [
        ("Status data", DEMO if demo else "Data yang dimasukkan pengguna"),
        ("Nama analisis / HPS ID", context["analysis_name"]), ("Barang / jasa", context["item_name"]),
        ("Kategori", context.get("category")), ("Spesifikasi", context["specification"]),
        ("Merek", context.get("brand")), ("Jumlah", context["quantity"]), ("Satuan", context["unit"]),
        ("Lokasi", context.get("location")), ("Wilayah", context.get("region")),
        ("Tanggal analisis", date.fromisoformat(context["analysis_date"])),
        ("Tanggal pengadaan", date.fromisoformat(context["target_date"])),
        ("Jumlah bukti disertakan", stats["n"]), ("Median teramati", stats["median"]),
        ("Rata-rata teramati", stats["mean"]), ("Minimum teramati", stats["min"]),
        ("Maksimum teramati", stats["max"]), ("Rentang indikatif · batas bawah", result["range_low"]),
        ("Rentang indikatif · batas atas", result["range_high"]),
        ("Benchmark analitis yang disarankan", result["benchmark"]),
        ("Tingkat keyakinan data", result["confidence"]),
        ("Harga kontrak aktual per satuan", snapshot.get("actual_unit_price")),
        ("Dasar benchmark", result["explanation"]), ("Catatan analis", context.get("notes")),
        ("Penggunaan", "Pendukung keputusan. HPS final membutuhkan tinjauan dan persetujuan analis."),
    ]
    _content(summary, ["Indikator", "Hasil dan konteks"], rows, {1: 44, 2: 83})
    for i in (*range(15, 22), 23):
        summary.cell(i, 2).number_format = CURRENCY
    for i in (12, 13):
        summary.cell(i, 2).number_format = "dd/mm/yyyy"
    for i in (15, 21, 22):
        for cell in summary[i]:
            cell.fill = PatternFill("solid", fgColor="FFEBD9")
            cell.font = Font(name="Calibri", bold=True, color="172C50")

    headers = ["ID observasi", *[FIELD_LABELS[k] for k in PRICE_FIELDS], "Tahun sumber",
               "Tanggal efektif", "Versi sumber", "Harga terindeks", "Faktor indeks", "Status indeks",
               "Keputusan", "Sebanding", "Potensi pencilan", "Penjelasan pencilan", "Penanda validasi",
               "Justifikasi analis", "Waktu data masuk", "Status data"]
    def evidence_row(r):
        fields = [SOURCE_LABELS.get(r[k], r[k]) if k == "source_type" else
                  date.fromisoformat(r[k]) if k == "observation_date" else r[k] for k in PRICE_FIELDS]
        return [
            r["price_observation_id"], *fields, r["effective_year"], str(r["effective_date"])[:10],
            r["version"], r["adjusted_price"], r["index_factor"], r["index_note"], DECISION[r["decision"]],
            r["is_comparable"], r["is_outlier"], r["outlier_reason"], " · ".join(r["flags"]),
            r["justification"], r["created_at"], DEMO if r["is_demo"] else "",
        ]
    _content(wb.create_sheet("Bukti Harga"), headers, map(evidence_row, evidence),
             {1: 39, 2: 31, 4: 46, 16: 30, 28: 55, 29: 48}, currency=(8, 20))
    model = result["forecast"]
    stat_rows = [(name, stats[k]) for k, name in STAT_LABELS.items()]
    stat_rows += [
        ("Modus", ", ".join(f"Rp {val:,.0f}".replace(",", ".") for val in stats["modes"]) or "Tidak bermakna"),
        ("Pagar IQR bawah", result["iqr_lower"]), ("Pagar IQR atas", result["iqr_upper"]),
        ("Potensi pencilan seluruh bukti", result["outlier_count"]),
        ("Potensi pencilan disertakan", result["included_outliers"]),
        ("Median pasar terkini", result["market_median"]),
        ("Median historis terindeks", result["normalized_median"]),
        ("Perkiraan regresi", model["price"]), ("R² pelatihan", model.get("r2")),
        ("Jumlah bukti regresi", model["n"]), ("Kualitas regresi", model.get("quality")),
        ("Catatan regresi", model["note"]),
    ]
    stat_sheet = wb.create_sheet("Analisis Statistik")
    _content(stat_sheet, ["Statistik", "Nilai"], stat_rows, {1: 45, 2: 76})
    for i in (3, 4, 5, 6, 7, 9, 10, 11, 12, 13, 15, 16, 19, 20, 21):
        stat_sheet.cell(i, 2).number_format = CURRENCY
    stat_sheet["B8"].number_format = "0.0%"
    stat_sheet["B22"].number_format = "0.00"
    exclusions = [(r["price_observation_id"], r["source_name"], r["price"],
                   " · ".join([*r["flags"], r["outlier_reason"]]).strip(" ·") or "Keputusan analis",
                   r["justification"]) for r in evidence if r["decision"] == "EXCLUDE"]
    _content(wb.create_sheet("Data Dikeluarkan"),
             ["ID observasi", "Sumber", "Harga asli", "Penanda / alasan", "Justifikasi analis"],
             exclusions, {1: 40, 2: 32, 4: 52, 5: 62}, currency=(3,))
    audit = [
        ("ID internal", snapshot.get("analysis_id")), ("Tanggal analisis (WIB)", context["analysis_date"]),
        ("Waktu pencatatan (WIB)", context.get("saved_at")),
        ("Satuan harga", context["unit"]), ("Dasar statistik", "Harga asli per satuan berstatus INCLUDE dan valid."),
        ("Persentil", "Interpolasi linear. Simpangan baku menggunakan pembagi N−1."),
        ("Pencilan", "P25 − 1,5 × IQR atau P75 + 1,5 × IQR. Minimum 4 bukti disertakan."),
        ("Rentang teramati", "P25–P75 dari harga asli yang disertakan."),
        ("Rumus benchmark", result["explanation"]),
        ("Usia maksimum bukti terkini (hari)", context.get("recent_days", 365)),
        ("Ambang bukti pasar terkini", context.get("minimum_market", 5)),
        ("Indeks", context.get("index_name")), ("Laju indeks (fraksi)", json.dumps(context.get("rates", {}))),
        ("Normalisasi", "Harga asli × hasil kali (1 + laju tahunan) dari tahun observasi+1 hingga tahun sasaran."),
        ("Sumber independen", result["independent_sources"]),
        ("Proporsi bukti terkini", result["recent_fraction"]),
        ("Proporsi bukti sebanding", result["comparable_fraction"]),
        ("Ambang keyakinan tinggi", "N ≥ 15, sumber ≥ 4, terkini ≥ 70%, sebanding ≥ 70%, CV ≤ 20%."),
        ("Ambang keyakinan sedang", "N ≥ 5, sumber ≥ 2, terkini ≥ 40%, sebanding ≥ 50%, CV ≤ 35%."),
        ("Regresi", "OLS tanggal → harga asli. Kecualikan dari model pencilan serta mismatch atau duplikat tertentu."),
        ("Syarat regresi", "Min 12 observasi, 6 tanggal, rentang 180 hari. Maks 365 hari ke depan."),
        ("Bukti berstatus Tinjau", sum(r["decision"] == "REVIEW" for r in evidence)),
    ]
    ws = wb.create_sheet("Metodologi dan Audit")
    _content(ws, ["Parameter", "Nilai / aturan"], audit, {1: 45, 2: 92})
    ws["B16"].number_format = ws["B17"].number_format = "0.0%"
    return _bytes(wb)


if __name__ == "__main__":
    from pathlib import Path

    out = Path(__file__).resolve().parents[1] / "data" / "templates"
    out.mkdir(parents=True, exist_ok=True)
    for key, filename in (("evidence", "Template_Bukti_Harga.xlsx"),
                          ("reference", "Template_Referensi_Tahunan.xlsx"), ("index", "Template_Indeks.xlsx")):
        (out / filename).write_bytes(template(key))
