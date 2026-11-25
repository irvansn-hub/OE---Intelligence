"use client";

import { useEffect, useState } from "react";
import { Search, UploadCloud } from "lucide-react";
import { Bars, Trend, average, distribution, groupBy, monthly } from "./charts";
import { Alert, DataTable, Empty, Field, FilePick, Metric, Panel, Select, Stats, Template,
  Title, api, money, priceColumns, range, unique } from "./kit";

function Filters({ rows, labels, active, set, fields }) {
  return <div className="grid3">{fields.map(([key, title]) =>
    <Select key={key} label={title} value={active[key] || ""} placeholder="Semua"
      options={unique(rows.map(r => r[key])).map(v => [v, key === "source_type" ? labels[v] : v])}
      onChange={value => set(previous => ({ ...previous, [key]: value }))} />)}</div>;
}
const fields = [["effective_year", "Tahun sumber"], ["source_type", "Jenis sumber"], ["region", "Wilayah"]];
function applyFilters(rows, active) {
  return rows.filter(row => Object.entries(active).every(([key, value]) => !value || String(row[key]) === value));
}
function SearchBox({ value, set, placeholder }) {
  return <label className="searchbox"><Search size={19}/><input aria-label={placeholder}
    placeholder={placeholder} value={value} onChange={e => set(e.target.value)} /></label>;
}

export function Reference({ workspace }) {
  const { prices, source_labels: labels } = workspace;
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState({});
  const rows = applyFilters(prices.filter(r => [r.item_name, r.source_name, r.specification]
    .some(v => v.toLowerCase().includes(query.trim().toLowerCase()))), filters);
  return <>
    <Title title="Basis Referensi" subtitle="Telusuri sumber, tahun, tanggal efektif, dan versi bukti." />
    <Panel className="filter-panel"><SearchBox value={query} set={setQuery} placeholder="Cari barang, spesifikasi, atau sumber"/>
      <Filters rows={prices} labels={labels} active={filters} set={setFilters}
        fields={[...fields, ["source_name", "Nama sumber"], ["brand", "Merek"], ["version", "Versi"]]} />
    </Panel>
    <Panel title="Bukti harga" description={rows.length + " observasi sesuai filter"}>
      <DataTable columns={priceColumns(labels)} rows={rows} keyBy={r => r.price_observation_id} />
    </Panel>
  </>;
}

export function Explore({ workspace }) {
  const { prices, source_labels: labels } = workspace;
  const items = unique(prices.map(row => row.item_name));
  const [item, setItem] = useState(items.find(v => v.includes("Laptop")) || items[0]);
  const [query, setQuery] = useState("");
  const [group, setGroup] = useState("");
  const [filters, setFilters] = useState({});
  const [stat, setStat] = useState(null);
  const [view, setView] = useState("source_name");
  const [err, setErr] = useState("");
  const options = items.filter(value => value.toLowerCase().includes(query.toLowerCase()));
  const active = options.includes(item) ? item : options[0] || "";
  const matches = prices.filter(row => row.item_name === active);
  const key = row => row.specification + " · " + row.unit;
  const groups = groupBy(matches, key).sort((a, b) => b.value - a.value).map(row => row.name);
  const selectedGroup = groups.includes(group) ? group : groups[0];
  const same = matches.filter(row => key(row) === selectedGroup);
  const rows = applyFilters(same, filters);
  const valid = rows.filter(row => row.price > 0);
  const values = JSON.stringify(rows.map(row => row.price > 0 ? row.price : null));

  useEffect(() => {
    let current = true;
    api("statistics", { values: JSON.parse(values) })
      .then(data => { if (current) { setStat(data); setErr(""); } })
      .catch(error => { if (current) { setStat(null); setErr(error.message); } });
    return () => { current = false; };
  }, [values]);

  return <>
    <Title title="Eksplorasi Harga" subtitle="Bandingkan harga historis dalam kelompok barang, spesifikasi, dan satuan yang sama." />
    <Panel className="filter-panel">
      <SearchBox value={query} set={v => { setQuery(v); setFilters({}); }} placeholder="Cari laptop, bearing, atau konsultan"/>
      <div className="grid2">
        <Select label="Barang / jasa" value={active} options={options} onChange={v => { setItem(v); setFilters({}); }}
          placeholder={options.length ? undefined : "Barang tidak ditemukan"} />
        <Select label="Spesifikasi dan satuan" value={selectedGroup || ""} options={groups}
          onChange={v => { setGroup(v); setFilters({}); }} />
      </div>
      <Filters rows={same} labels={labels} active={filters} set={setFilters}
        fields={[...fields, ["source_name", "Nama sumber"], ["location", "Lokasi"], ["vendor", "Pemasok"], ["brand", "Merek"]]} />
    </Panel>
    <Alert>{err}</Alert>
    {!rows.length ? <Empty>Tidak ada bukti yang sesuai dengan filter.</Empty> : <>
      <div className="metrics">
        <Metric label="Median teramati" value={money(stat?.stats.median)} />
        <Metric label="P25–P75" value={range(stat?.stats.p25, stat?.stats.p75)} />
        <Metric label="Potensi pencilan" value={stat?.flags.filter(Boolean).length ?? "—"} />
      </div>
      <div className="dashboard-grid">
        <Panel title="Tren median bulanan"><Trend data={monthly(valid)} /></Panel>
        <Panel title="Distribusi harga per satuan"><Bars data={distribution(valid)} horizontal={false} /></Panel>
      </div>
      <Panel title="Harga rata-rata">
        <div className="tabs">{[["source_name", "Menurut sumber"], ["vendor", "Menurut pemasok"], ["region", "Menurut wilayah"]]
          .map(([id, label]) => <button key={id} className={view === id ? "tab active" : "tab"} onClick={() => setView(id)}>{label}</button>)}</div>
        <Bars data={groupBy(valid, r => r[view], average).sort((a, b) => b.value - a.value)} currency name="Harga rata-rata" />
      </Panel>
      <Panel title="Bukti harga"><DataTable rows={rows} keyBy={r => r.price_observation_id}
        columns={[...priceColumns(labels), ["potential", "Penanda IQR", (_, i) => stat?.flags[i] || "—"]]} /></Panel>
      {stat && <Panel title="Statistik lengkap"><Stats data={stat.stats} /></Panel>}
    </>}
  </>;
}

export function ImportBox({ kind, meta, onRows }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const signature = JSON.stringify(meta ?? null);
  const current = preview?.signature === signature ? preview : null;
  async function submit(save) {
    setError(""); setMessage(""); setBusy(true);
    try {
      if (!save) {
        const form = new FormData();
        form.append("file", file);
        if (meta) form.append("meta", JSON.stringify(meta));
        setPreview({ ...await api("import/" + kind + "/preview", form), signature });
      } else {
        const result = await api("import/" + kind, { rows: current.rows, meta });
        if (!result.rows.length) throw new Error("Tidak ada baris valid yang dapat ditambahkan.");
        setMessage(onRows(result.rows) || result.rows.length + " baris diproses.");
        setPreview(null);
      }
    } catch (ex) { setError(ex.message); }
    finally { setBusy(false); }
  }
  return <div className="stack">
    <div className="toolbar"><Template kind={kind}/></div>
    <FilePick value={file} onChange={value => { setFile(value); setPreview(null); setMessage(""); }} />
    <div className="toolbar">
      <button className="button secondary" disabled={!file || busy} onClick={() => submit(false)}>
        <UploadCloud size={17}/> Validasi dan pratinjau</button>
      {current && <button className="button primary" disabled={busy || !current.rows.length}
        onClick={() => submit(true)}>Impor baris yang lolos</button>}
    </div>
    <Alert>{error}</Alert><Alert tone="success">{message}</Alert>
    {current && <>
      <p>{current.rows.length} baris siap diimpor.</p>
      {current.issues.length > 0 && <DataTable rows={current.issues} columns={[
        ["Baris", "Baris"], ["Status", "Status"], ["Rincian", "Rincian"],
      ]} />}
      {current.rows.length > 0 && <DataTable rows={current.rows.slice(0, 20)} columns={kind === "index"
        ? [["year", "Tahun"], ["index_name", "Indeks"], ["adjustment_rate", "Laju", r => (r.adjustment_rate * 100) + "%"]]
        : [["item_name", "Barang / jasa"], ["specification", "Spesifikasi"], ["unit", "Satuan"],
          ["price", "Harga satuan", r => money(r.price)], ["observation_date", "Tanggal"]]} />}
    </>}
  </div>;
}

export function Admin({ workspace, add }) {
  const { today, source_labels: labels, indices, prices } = workspace;
  const [kind, setKind] = useState("reference");
  const [meta, setMeta] = useState({
    source_type: "ASSOCIATION", source_name: "", effective_year: today.slice(0, 4),
    effective_date: today.slice(0, 4) + "-01-01", version: "v1",
  });
  const set = (key, value) => setMeta(previous => ({ ...previous, [key]: value }));
  function addReferences(rows) {
    if (rows.some(row => prices.some(old => old.source_name === row.source_name && old.source_type === row.source_type
      && old.effective_year === row.effective_year && old.version === row.version && old.effective_date !== row.effective_date)))
      throw new Error("Tanggal efektif berbeda pada versi yang sama. Gunakan versi baru.");
    const fresh = rows.filter(row => !prices.some(old => old.price_observation_id === row.price_observation_id));
    add("prices", fresh);
    return fresh.length + " baris baru ditambahkan. " + (rows.length - fresh.length) + " duplikat dilewati.";
  }
  function addIndices(rows) {
    const staged = new Map(indices.map(r => [r.index_name + "|" + r.year, r]));
    for (const row of rows) {
      const key = row.index_name + "|" + row.year;
      if (staged.has(key) && Math.abs(staged.get(key).adjustment_rate - row.adjustment_rate) > 1e-12)
        throw new Error("Tahun dan nama indeks sudah ada. Gunakan nama versi baru untuk revisi.");
      staged.set(key, row);
    }
    add("indices", rows);
  }
  return <>
    <Title title="Admin" subtitle="Impor edisi referensi dan indeks penyesuaian tahunan." />
    <div className="tabs">
      <button className={kind === "reference" ? "tab active" : "tab"} onClick={() => setKind("reference")}>Referensi tahunan</button>
      <button className={kind === "index" ? "tab active" : "tab"} onClick={() => setKind("index")}>Indeks penyesuaian</button>
    </div>
    {kind === "reference" ? <Panel title="Impor referensi tahunan" description="Tahun dan versi baru disimpan sebagai edisi tersendiri.">
      <div className="grid3">
        <Select label="Jenis sumber" value={meta.source_type} options={Object.entries(labels)} onChange={v => set("source_type", v)} />
        <Field label="Nama sumber"><input value={meta.source_name} onChange={e => set("source_name", e.target.value)} /></Field>
        <Field label="Tahun sumber"><input type="number" min="1900" max="2200" value={meta.effective_year}
          onChange={e => { const n = e.target.value; setMeta(prev => ({ ...prev, effective_year: n,
            effective_date: /^\d{4}$/.test(n) ? n + "-01-01" : prev.effective_date })); }} /></Field>
        <Field label="Tanggal efektif"><input type="date" value={meta.effective_date} onChange={e => set("effective_date", e.target.value)} /></Field>
        <Field label="Versi"><input value={meta.version} onChange={e => set("version", e.target.value)} /></Field>
      </div>
      <ImportBox kind="reference" meta={meta} onRows={addReferences} />
    </Panel> : <>
      <Panel title="Impor indeks tahunan" description="Isi angka dalam persen. Contoh 3,2 berarti 3,2%.">
        <ImportBox kind="index" onRows={addIndices} />
      </Panel>
      <Panel title="Indeks tersimpan"><DataTable rows={indices} keyBy={r => r.index_name + "|" + r.year}
        columns={[["index_name", "Nama indeks"], ["year", "Tahun"], ["adjustment_rate", "Laju",
          r => (r.adjustment_rate * 100).toLocaleString("id-ID") + "%"]]} /></Panel>
    </>}
  </>;
}
