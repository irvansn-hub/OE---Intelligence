"use client";

import { useEffect, useState } from "react";
import { BarChart3, BookOpen, ClipboardList, Database, Gauge, Menu, ShieldCheck, X } from "lucide-react";
import { Analysis } from "./analysis";
import { Dashboard } from "./dashboard";
import { Admin, Explore, Reference } from "./reference";
import { Alert, Empty, api } from "./kit";

const sections = [
  ["dasbor", "Dasbor", Gauge], ["analisis", "Analisis HPS", ClipboardList],
  ["eksplorasi", "Eksplorasi Harga", BarChart3], ["referensi", "Basis Referensi", BookOpen],
  ["admin", "Admin", Database],
];
const STORAGE = "kai-hps-vercel-demo-v1";

function merge(rows, added, key) {
  return [...new Map([...rows, ...added].map(row => [key(row), row])).values()];
}

export default function Home() {
  const [page, setPage] = useState("dasbor");
  const [menuOpen, setMenu] = useState(false);
  const [workspace, setWorkspace] = useState(null);
  const [fallback, setFallback] = useState({});
  const [error, setError] = useState("");
  const [cacheWarning, setCacheWarning] = useState("");
  const [analysisOpened, setAnalysisOpened] = useState(false);
  const [readVersion, setReadVersion] = useState(0);

  useEffect(() => {
    function navigate() {
      const view = window.location.hash.slice(1);
      setPage(sections.some(([part]) => part === view) ? view : "dasbor");
      setMenu(false);
      if (view === "analisis") setAnalysisOpened(true);
    }
    navigate();
    window.addEventListener("hashchange", navigate);
    return () => window.removeEventListener("hashchange", navigate);
  }, []);
  useEffect(() => {
    let current = true;
    api("workspace").then(data => {
      if (!current) return;
      setWorkspace(data);
      setError("");
      if (!data.persistent) {
        try { setFallback(JSON.parse(localStorage.getItem(STORAGE) || "{}")); }
        catch { setCacheWarning("Penyimpanan browser belum dapat dibaca. Data demo awal tetap tersedia."); }
      }
    }).catch(err => { if (current) setError(err.message); });
    return () => { current = false; };
  }, [readVersion]);

  const go = name => {
    if (name === "analisis") setAnalysisOpened(true);
    setPage(name);
    setMenu(false);
    window.location.hash = name;
    window.scrollTo({ top: 0 });
  };

  function add(type, rows) {
    if (workspace.persistent) {
      setWorkspace(previous => ({ ...previous, [type]: merge(previous[type], rows, identity[type]) }));
      return;
    }
    const all = merge(fallback[type] || [], rows, identity[type]);
    const next = { ...fallback, [type]: all };
    setFallback(next);
    try { localStorage.setItem(STORAGE, JSON.stringify(next)); }
    catch { setCacheWarning("Penyimpanan browser penuh atau dibatasi. Unduh laporan sebelum menutup tab."); }
  }

  const identity = {
    prices: row => row.price_observation_id,
    indices: row => row.index_name + "|" + row.year,
    analyses: row => row.analysis_id,
  };
  const visible = workspace && {
    ...workspace,
    ...Object.fromEntries(Object.entries(identity).map(([key, id]) => [
      key, merge(workspace[key], workspace.persistent ? [] : fallback[key] || [], id),
    ])),
  };

  return <div className="shell">
    <aside className={menuOpen ? "sidebar sidebar-open" : "sidebar"}>
      <div className="brand"><div className="brand-logo">KAI</div>
        <div><strong>HPS Price Intelligence</strong><small>Supply Policy &amp; Planning</small></div></div>
      <nav aria-label="Navigasi utama">
        {sections.map(([id, label, Icon]) =>
          <a key={id} href={"#" + id} aria-current={page === id ? "page" : undefined}
            onClick={e => { e.preventDefault(); go(id); }} className={page === id ? "nav-active" : ""}>
            <Icon size={19}/>{label}
          </a>
        )}
      </nav>
      <div className="sidebar-note"><ShieldCheck size={19} /><span>Dukungan keputusan HPS</span></div>
    </aside>
    {menuOpen && <button className="overlay" onClick={() => setMenu(false)} aria-label="Tutup navigasi" />}
    <div className="main-area">
      <header className="topbar">
        <button className="menu-button" onClick={() => setMenu(!menuOpen)} aria-label="Buka navigasi" aria-expanded={menuOpen}>
          {menuOpen ? <X size={23}/> : <Menu size={23}/>}
        </button>
        <span className="top-name">KAI HPS Price Intelligence</span>
        <span className="demo-marker">DEMO / DATA SINTETIS</span>
      </header>
      <main className="content">
        <Alert tone="info">{workspace && (workspace.persistent
          ? "Mode demo dengan PostgreSQL bersama. Gunakan data sintetis."
          : "Gunakan data sintetis. Impor dan analisis baru tersimpan di browser ini.")}</Alert>
        <Alert tone="info">{workspace?.truncated && "Dasbor memuat hingga 2.000 observasi terbaru."}</Alert>
        <Alert tone="info">{cacheWarning}</Alert>
        {error && <div className="panel"><Alert>{error}</Alert><button className="button secondary"
          onClick={() => setReadVersion(v => v + 1)}>Muat ulang</button></div>}
        {!visible && !error && <Empty>Sedang memuat bukti harga demo…</Empty>}
        {visible && page === "dasbor" && <Dashboard workspace={visible} go={go}/>}
        {visible && analysisOpened && <div hidden={page !== "analisis"}>
          <Analysis workspace={visible} add={add} />
        </div>}
        {visible && page === "eksplorasi" && <Explore workspace={visible}/>}
        {visible && page === "referensi" && <Reference workspace={visible}/>}
        {visible && page === "admin" && <Admin workspace={visible} add={add}/>}
      </main>
    </div>
  </div>;
}
