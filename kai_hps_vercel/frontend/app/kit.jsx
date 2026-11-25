"use client";

import { ArrowDownToLine, FileSpreadsheet, Info } from "lucide-react";

export const money = value => Number.isFinite(value)
  ? "Rp " + new Intl.NumberFormat("id-ID", { maximumFractionDigits: 0 }).format(value) : "—";
export const decimal = value => Number.isFinite(value)
  ? new Intl.NumberFormat("id-ID", { maximumFractionDigits: 2 }).format(value) : "—";
export const range = (low, high) => low == null ? "—" : money(low) + " – " + money(high);
export const pct = (n, digits = 0) => n == null ? "—"
  : new Intl.NumberFormat("id-ID", { style: "percent", maximumFractionDigits: digits }).format(n);
export const choiceLabels = { INCLUDE: "Sertakan", EXCLUDE: "Keluarkan", REVIEW: "Tinjau" };
export const unique = rows => [...new Set(rows.filter(value => value !== "" && value != null))]
  .sort((a, b) => String(a).localeCompare(String(b), "id", { numeric: true }));

export async function api(path, body) {
  const isForm = body instanceof FormData;
  const response = await fetch("/api/" + path, {
    cache: "no-store",
    ...(body === undefined ? {} : {
      method: "POST", body: isForm ? body : JSON.stringify(body),
      ...(isForm ? {} : { headers: { "Content-Type": "application/json" } }),
    }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(typeof error.detail === "string" ? error.detail
      : response.status === 413 ? "Ukuran berkas atau bukti terlalu besar."
      : response.status === 422 ? "Periksa kelengkapan dan format data yang diisi."
      : "Layanan belum tersedia. Coba lagi.");
  }
  const content = response.headers.get("content-type") || "";
  return content.includes("application/json") ? response.json() : response.blob();
}

export async function report(snapshot, persistent) {
  const file = persistent ? await api("analyses/" + snapshot.analysis_id + "/report")
    : await api("report", snapshot);
  const address = URL.createObjectURL(file);
  const a = document.createElement("a");
  a.href = address;
  a.download = "Analisis_HPS_" + snapshot.analysis_id.slice(0, 12) + ".xlsx";
  a.click();
  setTimeout(() => URL.revokeObjectURL(address), 1000);
}

export function Empty({ children }) {
  return <div className="empty"><Info size={18} /><span>{children}</span></div>;
}
export function Alert({ children, tone = "error" }) {
  return children ? <div className={"alert " + tone} role={tone === "error" ? "alert" : "status"}>{children}</div> : null;
}
export function Metric({ label, value, icon: Icon, note }) {
  return <article className="metric"><div className="metric-head">{label}{Icon && <Icon size={18} />}</div>
    <strong>{value}</strong>{note && <small>{note}</small>}</article>;
}
export function Panel({ title, description, children, className = "" }) {
  return <section className={"panel " + className}>
    {title && <div className="panel-title"><h2>{title}</h2>{description && <p>{description}</p>}</div>}
    {children}
  </section>;
}
export function Title({ title, subtitle, children }) {
  return <div className="view-heading"><div><h1>{title}</h1><p>{subtitle}</p></div>{children}</div>;
}
export function Field({ label, children, wide }) {
  return <label className={"field" + (wide ? " wide" : "")}><span>{label}</span>{children}</label>;
}
export function Select({ label, value, onChange, options, placeholder, wide }) {
  return <Field label={label} wide={wide}><select value={value} onChange={e => onChange(e.target.value)}>
    {placeholder && <option value="">{placeholder}</option>}
    {options.map(option => Array.isArray(option)
      ? <option key={option[0]} value={option[0]}>{option[1]}</option>
      : <option key={option} value={option}>{option}</option>)}
  </select></Field>;
}
export function DataTable({ columns, rows, keyBy, empty = "Belum ada data untuk ditampilkan." }) {
  if (!rows.length) return <Empty>{empty}</Empty>;
  return <div className="table-wrap" tabIndex={0} aria-label="Tabel data">
    <table><thead><tr>{columns.map(([key, label]) => <th key={key}>{label}</th>)}</tr></thead>
      <tbody>{rows.map((row, i) => <tr key={keyBy ? keyBy(row) : i}>
        {columns.map(([key, , display]) => <td key={key}>{display ? display(row, i) : row[key] || "—"}</td>)}
      </tr>)}</tbody></table></div>;
}
export function Template({ kind }) {
  return <a className="button secondary" href={"/api/templates/" + kind} download>
    <ArrowDownToLine size={16} /> Unduh template Excel
  </a>;
}
export function FilePick({ value, onChange }) {
  return <label className="file-box"><FileSpreadsheet size={24} /><span>{value?.name || "Pilih file Excel atau CSV"}<small>Maksimum 3 MB dan 250 baris per impor</small></span>
    <input aria-label="Pilih file Excel atau CSV" type="file" accept=".xlsx,.csv"
      onChange={e => onChange(e.target.files?.[0] || null)} /></label>;
}
export function Stats({ data }) {
  const fields = [
    ["n", "Jumlah (N)", decimal], ["min", "Minimum", money], ["max", "Maksimum", money],
    ["mean", "Rata-rata", money], ["median", "Median", money], ["std", "Simpangan baku", money],
    ["p10", "P10", money], ["p25", "P25", money], ["p75", "P75", money],
    ["p90", "P90", money], ["iqr", "IQR", money], ["cv", "Koefisien variasi", value => pct(value, 1)],
  ];
  return <dl className="stats">{fields.map(([key, label, format]) =>
    <div key={key}><dt>{label}</dt><dd>{format(data[key])}</dd></div>)}
    <div><dt>Modus</dt><dd>{data.modes?.map(money).join(", ") || "Tidak bermakna"}</dd></div></dl>;
}

export const priceColumns = labels => [
  ["item_name", "Barang / jasa"], ["specification", "Spesifikasi"], ["region", "Wilayah"],
  ["price", "Harga asli", row => <span className="tabular">{money(row.price)}</span>],
  ["unit", "Satuan"], ["source_name", "Sumber"], ["source_type", "Jenis sumber", row => labels[row.source_type]],
  ["vendor", "Pemasok"], ["observation_date", "Tanggal", row => row.observation_date?.slice(0, 10)],
  ["effective_year", "Tahun"], ["effective_date", "Berlaku", row => row.effective_date?.slice(0, 10)],
  ["version", "Versi"], ["url_reference", "Referensi"],
];
