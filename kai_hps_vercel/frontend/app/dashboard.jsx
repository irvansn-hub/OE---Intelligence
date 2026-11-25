"use client";

import { useState } from "react";
import { ClipboardList, Database, Layers3, ScanLine, TrendingUp, TriangleAlert } from "lucide-react";
import { Bars, Compare, Trend, average, groupBy, monthly } from "./charts";
import { Metric, Panel, Select, Title, decimal, pct, unique } from "./kit";

export function Dashboard({ workspace, go }) {
  const { prices, analyses, source_labels: labels } = workspace;
  const items = unique(prices.map(row => row.item_name));
  const [item, setItem] = useState(items.find(name => name.includes("Laptop")) || items[0] || "");
  const [group, setGroup] = useState("");
  const byItem = prices.filter(r => r.item_name === item);
  const groups = groupBy(byItem, r => r.specification + " · " + r.unit)
    .sort((a, b) => b.value - a.value).map(r => r.name);
  const selectedGroup = groups.includes(group) ? group : groups[0] || "";
  const comparable = byItem.filter(r => r.specification + " · " + r.unit === selectedGroup && r.price > 0);
  const paired = analyses.filter(r => r.actual_unit_price > 0 && r.result.benchmark != null);
  const counts = analyses.map(row => row.result.stats.n);
  const deviation = paired.length
    ? paired.reduce((sum, row) => sum + row.result.benchmark / row.actual_unit_price - 1, 0) / paired.length
    : null;
  const outliers = analyses.reduce((sum, row) => sum + row.result.outlier_count, 0);
  return <>
    <Title title="Dasbor" subtitle="Ringkasan bukti harga dan analisis HPS tersimpan.">
      <button className="button primary" onClick={() => go("analisis")}>Analisis baru</button>
    </Title>
    <div className="metrics">
      <Metric label="Analisis tersimpan" value={analyses.length} icon={ClipboardList} />
      <Metric label="Barang / jasa" value={items.length} icon={Layers3} />
      <Metric label="Bukti harga" value={prices.length} icon={Database} />
      <Metric label="Bukti per analisis" value={counts.length ? decimal(counts.reduce((a, b) => a + b, 0) / counts.length) : "—"} icon={ScanLine} />
      <Metric label="Selisih vs. kontrak" value={pct(deviation, 1)} icon={TrendingUp} />
      <Metric label="Penanda pencilan" value={outliers} icon={TriangleAlert} />
    </div>
    <Panel className="filter-panel"><div className="grid2">
      <Select label="Barang / jasa" options={items} value={item} onChange={setItem}/>
      <Select label="Spesifikasi dan satuan" options={groups} value={selectedGroup} onChange={setGroup}/>
    </div></Panel>
    <div className="dashboard-grid">
      <Panel title="Tren harga historis" description="Median bulanan per satuan">
        <Trend data={monthly(comparable)}/>
      </Panel>
      <Panel title="Rata-rata menurut sumber" description="Untuk spesifikasi dan satuan yang dipilih">
        <Bars data={groupBy(comparable, r => labels[r.source_type], average).sort((a, b) => b.value - a.value)} currency name="Harga rata-rata" />
      </Panel>
      <Panel title="Komposisi sumber" description="Jumlah observasi pada seluruh basis harga">
        <Bars data={groupBy(prices, r => labels[r.source_type]).sort((a, b) => b.value - a.value)} />
      </Panel>
      <Panel title="Benchmark dan kontrak aktual" description="Harga satuan dari analisis yang memiliki pembanding">
        <Compare data={paired.map(row => ({
          name: row.context.analysis_name, benchmark: row.result.benchmark, actual: row.actual_unit_price,
        }))} />
      </Panel>
    </div>
  </>;
}
