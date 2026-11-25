"use client";

import { useState } from "react";
import { Calculator, Download, Plus, Search } from "lucide-react";
import { Alert, DataTable, Empty, Field, Metric, Panel, Select, Stats, Title, api,
  choiceLabels, money, pct, range, report, unique } from "./kit";
import { ImportBox } from "./reference";

const profile = [["item_name", "Nama barang / jasa"], ["category", "Kategori"], ["brand", "Merek"],
  ["unit", "Satuan"], ["location", "Lokasi"], ["region", "Wilayah"], ["specification", "Spesifikasi"]];
const preset = row => Object.fromEntries([...profile.map(([key]) => key), "quantity"]
  .map(key => [key, row?.[key] ?? (key === "quantity" ? 1 : "")]));

function Inputs({ fields, set, definitions }) {
  return definitions.map(([key, label, type = "text"]) => <Field key={key} label={label}
    wide={key === "specification" || key === "notes"}>
    <input type={type} step={type === "number" ? "any" : undefined} value={fields[key] ?? ""}
      onChange={e => set(key, e.target.value)} required={["item_name", "unit", "specification", "source_name",
        "observation_date", "analysis_name", "target_date"].includes(key)} />
  </Field>);
}

function Manual({ context, labels, onAdd }) {
  const [fields, setFields] = useState({
    ...preset(context), price: "", source_type: "SUPPLIER_QUOTATION", source_name: "", vendor: "",
    observation_date: context.analysis_date, url_reference: "", notes: "",
  });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [message, setMessage] = useState("");
  const set = (key, value) => setFields(p => ({ ...p, [key]: value }));
  async function submit(e) {
    e.preventDefault();
    setErr(""); setMessage(""); setBusy(true);
    try {
      const rows = [{ ...fields, price: fields.price === "" ? null : Number(fields.price),
        quantity: fields.quantity === "" ? null : Number(fields.quantity) }];
      const response = await api("import/evidence", { rows });
      if (!response.rows.length) throw new Error(response.issues[0]?.Rincian || "Bukti belum valid.");
      setMessage(onAdd(response.rows));
      setFields(p => ({ ...p, price: "", source_name: "", vendor: "", url_reference: "", notes: "" }));
    } catch (ex) { setErr(ex.message); }
    finally { setBusy(false); }
  }
  return <form className="stack" onSubmit={submit}>
    <div className="grid3">
      <Inputs fields={fields} set={set} definitions={[...profile,
        ["price", "Harga satuan (Rp)", "number"], ["quantity", "Jumlah", "number"],
        ["observation_date", "Tanggal observasi", "date"]]} />
      <Select label="Jenis sumber" value={fields.source_type} options={Object.entries(labels)} onChange={v => set("source_type", v)} />
      <Inputs fields={fields} set={set} definitions={[["source_name", "Nama sumber"], ["vendor", "Pemasok"],
        ["url_reference", "URL / nomor dokumen"], ["notes", "Catatan bukti"]]} />
    </div>
    <div className="toolbar"><button className="button secondary" disabled={busy}><Plus size={17} /> Tambahkan bukti</button></div>
    <Alert>{err}</Alert><Alert tone="success">{message}</Alert>
  </form>;
}

function Results({ snapshot }) {
  const { result, evidence } = snapshot;
  const { stats, forecast } = result;
  const outliers = evidence?.filter(r => r.is_outlier) || [];
  return <>
    <div className="metrics">
      <Metric label="Median teramati" value={money(stats.median)}/>
      <Metric label="Rentang teramati P25–P75" value={range(stats.p25, stats.p75)}/>
      <Metric label="Keyakinan data" value={result.confidence}/>
    </div>
    <Panel title="Rentang benchmark indikatif" className="benchmark">
      <div className="benchmark-number">{range(result.range_low, result.range_high)}</div>
      <p>Benchmark analitis <strong>{money(result.benchmark)}</strong></p>
      <p>{result.explanation}</p>
      <small>HPS final memerlukan tinjauan dan persetujuan sesuai proses PT KAI.</small>
    </Panel>
    <div className="metrics">
      <Metric label="Median pasar terkini" value={money(result.market_median)}/>
      <Metric label="Median historis terindeks" value={money(result.normalized_median)}/>
      <Metric label="Prakiraan tren" value={money(forecast.price)}
        note={forecast.price == null ? forecast.note : "R² " + forecast.r2.toFixed(2) + " · N = " + forecast.n + " · " + forecast.quality}/>
    </div>
    {forecast.price != null && <Alert tone="info">{forecast.note}</Alert>}
    {!!outliers.length && <Panel title="Potensi pencilan">
      <DataTable rows={outliers} keyBy={r => r.price_observation_id} columns={[
        ["source_name", "Sumber"], ["price", "Harga", r => money(r.price)],
        ["outlier_reason", "Dasar penanda"], ["decision", "Keputusan", r => choiceLabels[r.decision]],
      ]}/>
    </Panel>}
    <Panel title="Statistik lengkap dan keyakinan data">
      <Stats data={stats}/>
      <p className="muted">{stats.n} bukti disertakan · {result.independent_sources} sumber independen · {pct(result.recent_fraction)}
        {" "}terkini · {pct(result.comparable_fraction)} sebanding.</p>
      <details><summary>Ambang keyakinan</summary>
        <p>Tinggi jika N ≥ 15, sumber ≥ 4, terkini ≥ 70%, sebanding ≥ 70% dan CV ≤ 20%.
          Sedang jika N ≥ 5, sumber ≥ 2, terkini ≥ 40%, sebanding ≥ 50% dan CV ≤ 35%. Selebihnya rendah.</p>
      </details>
    </Panel>
  </>;
}

function History({ workspace, selected, setSelected }) {
  const rows = [...workspace.analyses].reverse();
  const [loaded, setLoaded] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const active = rows.find(row => row.analysis_id === selected);
  const record = active?.evidence ? active : loaded?.analysis_id === selected ? loaded : active;
  async function action(type, id) {
    setError(""); setBusy(true);
    try {
      if (type === "open") {
        setSelected(id);
        if (id && !rows.find(r => r.analysis_id === id)?.evidence) setLoaded(await api("analyses/" + id));
      } else {
        await report(record, workspace.persistent);
      }
    } catch (ex) { setError(ex.message); }
    finally { setBusy(false); }
  }
  return <>
    <Panel title="Pilih analisis tersimpan">
      <Select label="Analisis" value={selected} placeholder="Pilih analisis" onChange={id => action("open", id)}
        options={rows.map(r => [r.analysis_id, r.context.analysis_name + " · " + r.context.analysis_date])}/>
      <div className="toolbar"><button disabled={!record || busy} className="button primary" onClick={() => action("download")}>
        <Download size={17} /> Unduh laporan Excel</button></div>
      <Alert>{error}</Alert>
    </Panel>
    {record ? <Results snapshot={record}/> : <Empty>Pilih analisis untuk melihat hasilnya.</Empty>}
  </>;
}

export function Analysis({ workspace, add }) {
  const { prices, today, indices, source_labels: labels } = workspace;
  const laptop = prices.find(r => r.item_name.includes("Laptop") && r.specification.includes("16 GB")
    && r.region === "DKI Jakarta" && r.quantity === 20);
  const [input, setInput] = useState({
    ...preset(laptop), target_date: today, analysis_name: "", notes: "",
    recent_days: 365, minimum_market: 5, index_name: "", enable_forecast: true,
  });
  const [tab, setTab] = useState("new");
  const [draft, setDraft] = useState(null);
  const [choices, setChoices] = useState({});
  const [actual, setActual] = useState("");
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [busy, setBusy] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [selected, setSelected] = useState("");
  const [addMode, setAddMode] = useState("manual");
  const [version, bump] = useState(0);
  const set = (key, value) => setInput(old => ({ ...old, [key]: value }));
  const options = new Map();
  for (const row of prices) {
    const label = row.item_name + " · " + row.specification + " · " + row.unit + (row.region ? " · " + row.region : "");
    if (!options.has(label)) options.set(label, row);
  }
  const payload = (context, rows, choiceMap, save, actualPrice) => ({
    context, observations: workspace.persistent ? rows.map(r => ({ price_observation_id: r.price_observation_id })) : rows,
    choices: choiceMap, indices, actual_unit_price: actualPrice, save,
  });

  async function run(e, step) {
    e?.preventDefault();
    setBusy(true); setError(""); setInfo("");
    try {
      if (step === "find") {
        const names = await api("search", { item_name: input.item_name, names: unique(prices.map(r => r.item_name)) });
        const observations = prices.filter(r => names.includes(r.item_name));
        const context = { ...input, quantity: Number(input.quantity) };
        const snapshot = await api("analyze", payload(context, observations, {}, false, null));
        setDraft({ context, observations, snapshot }); setChoices({}); setActual(""); bump(v => v + 1);
        if (!observations.length) setInfo("Belum ada referensi yang cocok. Tambahkan bukti atau unggah file.");
      } else {
        const save = step === "save";
        const snapshot = await api("analyze", payload(draft.context, draft.observations, choices, save, actual ? Number(actual) : null));
        setDraft(previous => ({ ...previous, snapshot }));
        if (save) {
          add("analyses", [snapshot]); setSelected(snapshot.analysis_id); setTab("history");
          setInfo("Analisis disimpan. Laporan Excel siap diunduh.");
        }
      }
      setDirty(false);
    } catch (ex) { setError(ex.message); }
    finally { setBusy(false); }
  }

  function addRows(rows) {
    const observations = [...new Map([...draft.observations, ...rows].map(r => [r.price_observation_id, r])).values()];
    const fresh = observations.length - draft.observations.length;
    add("prices", rows);
    setDraft(previous => ({ ...previous, observations }));
    setDirty(true);
    return fresh + " bukti baru ditautkan. Klik Hitung benchmark untuk memperbarui hasil.";
  }
  function choose(key, row, value) {
    setChoices(previous => ({ ...previous, [row.price_observation_id]: {
      decision: row.decision, justification: row.justification, ...previous[row.price_observation_id], [key]: value,
    } }));
    setDirty(true);
  }

  return <>
    <Title title="Analisis HPS" subtitle="Cari bukti yang sebanding, tinjau hasil, dan simpan benchmark indikatif." />
    <div className="tabs">
      <button className={tab === "new" ? "tab active" : "tab"} onClick={() => setTab("new")}>Analisis baru</button>
      <button className={tab === "history" ? "tab active" : "tab"} onClick={() => setTab("history")}>Riwayat dan ekspor</button>
    </div>
    <Alert>{error}</Alert><Alert tone="info">{info}</Alert>
    {tab === "history" ? <History workspace={workspace} selected={selected} setSelected={setSelected} /> : <>
      <Panel title="Konteks pengadaan">
        <form onSubmit={e => run(e, "find")} className="stack">
          <Select label="Isi cepat dari basis harga" value="" placeholder="Pilih barang untuk mengisi formulir"
            options={[...options.keys()]} onChange={label => { if (options.has(label)) setInput(old => ({ ...old, ...preset(options.get(label)) })); }} />
          <div className="grid3"><Inputs fields={input} set={set} definitions={[
            ["analysis_name", "Nama analisis / HPS ID"], ...profile.slice(0, -1),
            ["quantity", "Jumlah", "number"], ["target_date", "Tanggal pengadaan", "date"],
            profile.at(-1), ["notes", "Catatan"],
          ]}/></div>
          <details><summary>Pengaturan benchmark</summary><div className="grid3">
            <Field label="Batas bukti terkini (hari)"><input type="number" min="30" max="730" value={input.recent_days}
              onChange={e => set("recent_days", Number(e.target.value))}/></Field>
            <Field label="Minimum bukti pasar terkini"><input type="number" min="2" max="100" value={input.minimum_market}
              onChange={e => set("minimum_market", Number(e.target.value))}/></Field>
            <Select label="Indeks tahunan" placeholder="Tanpa indeks" value={input.index_name}
              options={unique(indices.map(r => r.index_name))} onChange={v => set("index_name", v)}/>
            <label className="check"><input type="checkbox" checked={input.enable_forecast}
              onChange={e => set("enable_forecast", e.target.checked)}/> Aktifkan prakiraan tren</label>
          </div></details>
          <div className="toolbar"><button className="button primary" disabled={busy}><Search size={17}/> Cari harga referensi</button></div>
        </form>
      </Panel>
      {draft && <>
        <Panel title="Bukti dan keputusan analis" description={draft.context.analysis_name + " · Harga per " + draft.context.unit}>
          {dirty && <Alert tone="info">Bukti atau keputusan berubah. Hitung kembali untuk memperbarui hasil.</Alert>}
          <DataTable rows={draft.snapshot.evidence} keyBy={r => r.price_observation_id} columns={[
            ["decision", "Keputusan", r => <select aria-label={"Keputusan " + r.source_name}
              value={choices[r.price_observation_id]?.decision ?? r.decision} onChange={e => choose("decision", r, e.target.value)}>
              {Object.entries(choiceLabels).map(([v, label]) => <option value={v} key={v}>{label}</option>)}</select>],
            ["price", "Harga asli", r => money(r.price)],
            ["adjusted_price", "Harga terindeks", r => <span title={r.index_note}>{money(r.adjusted_price)}</span>],
            ["source_name", "Sumber"], ["observation_date", "Tanggal"], ["unit", "Satuan"], ["region", "Wilayah"],
            ["flags", "Penanda", r => [...r.flags, r.outlier_reason].filter(Boolean).join(" · ") || "—"],
            ["specification", "Spesifikasi"], ["url_reference", "Referensi"],
            ["justification", "Justifikasi jika dikeluarkan", r => <input aria-label={"Justifikasi " + r.source_name}
              value={choices[r.price_observation_id]?.justification ?? r.justification}
              onChange={e => choose("justification", r, e.target.value)} placeholder="Alasan pengecualian" />],
          ]}/>
          <div className="toolbar"><button className="button secondary" disabled={busy || !draft.observations.length}
            onClick={() => run(null, "calculate")}><Calculator size={17}/> Hitung benchmark</button></div>
        </Panel>
        <Panel title="Tambahkan bukti harga">
          <div className="tabs">
            <button className={addMode === "manual" ? "tab active" : "tab"} onClick={() => setAddMode("manual")}>Input manual</button>
            <button className={addMode === "file" ? "tab active" : "tab"} onClick={() => setAddMode("file")}>Unggah Excel / CSV</button>
          </div>
          {addMode === "manual" ? <Manual key={version} context={draft.snapshot.context} labels={labels} onAdd={addRows}/>
            : <ImportBox key={version} kind="evidence" onRows={addRows}/>}
        </Panel>
        {draft.snapshot.result.stats.n > 0 && <Results snapshot={draft.snapshot}/>}
        <Panel title="Simpan hasil analisis">
          <div className="grid2">
            <Field label="Harga kontrak aktual per satuan (opsional, Rp)"><input type="number" min="1" step="any"
              value={actual} onChange={e => setActual(e.target.value)}/></Field>
          </div>
          <div className="toolbar"><button className="button primary" onClick={() => run(null, "save")}
            disabled={busy || !draft.observations.length}>Simpan analisis</button></div>
        </Panel>
      </>}
    </>}
  </>;
}
