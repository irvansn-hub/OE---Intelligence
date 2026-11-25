"use client";

import {
  Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from "recharts";
import { Empty, money } from "./kit";

const NAVY = "#224b7c";
const ORANGE = "#da6526";
const GRID = "#e4ebf2";
const AXIS = { fontSize: 11, fill: "#53677d" };
const num = new Intl.NumberFormat("id-ID", { notation: "compact", maximumFractionDigits: 1 });
const moneyAxis = value => num.format(value);

export function groupBy(rows, key, fn = group => group.length) {
  const groups = new Map();
  for (const row of rows) {
    const name = key(row);
    if (!name) continue;
    const list = groups.get(name) || [];
    list.push(row);
    groups.set(name, list);
  }
  return [...groups].map(([name, group]) => ({ name, value: fn(group) }));
}
export function median(group) {
  const ordered = group.map(r => r.price).sort((a, b) => a - b);
  const center = Math.floor(ordered.length / 2);
  return ordered.length % 2 ? ordered[center] : (ordered[center - 1] + ordered[center]) / 2;
}
export function average(group) {
  return group.reduce((sum, row) => sum + row.price, 0) / group.length;
}
export function monthly(rows) {
  return groupBy(rows, r => r.observation_date?.slice(0, 7), median)
    .sort((a, b) => a.name.localeCompare(b.name));
}
export function Trend({ data }) {
  if (!data.length) return <Empty>Belum ada data tren untuk kelompok ini.</Empty>;
  return <div className="chart" role="img" aria-label="Grafik tren median harga bulanan">
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data} margin={{ top: 12, right: 18, left: 0, bottom: 4 }}>
        <CartesianGrid vertical={false} stroke={GRID} />
        <XAxis dataKey="name" minTickGap={20} axisLine={false} tickLine={false} tick={AXIS}
          tickFormatter={value => new Date(value + "-15T12:00:00").toLocaleDateString("id-ID", { month: "short", year: "2-digit" })} />
        <YAxis tickFormatter={moneyAxis} tickLine={false} axisLine={false} tick={AXIS} domain={["auto", "auto"]} width={54} />
        <Tooltip formatter={money} labelFormatter={value => "Bulan " + value} />
        <Line name="Median" type="monotone" dataKey="value" stroke={NAVY} strokeWidth={3}
          dot={{ r: 3, fill: NAVY, stroke: "white" }} activeDot={{ r: 6 }} isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer></div>;
}
export function Bars({ data, currency = false, name = "Jumlah", horizontal = true }) {
  if (!data.length) return <Empty>Belum ada data untuk grafik ini.</Empty>;
  const view = data.slice(0, 12);
  return <div className="chart" role="img" aria-label={name}>
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={view} layout={horizontal ? "vertical" : "horizontal"}
        margin={{ top: 8, right: 20, left: 0, bottom: 4 }}>
        <CartesianGrid vertical={!horizontal} horizontal={!horizontal} stroke={GRID} />
        {horizontal ? <>
          <XAxis type="number" tickFormatter={currency ? moneyAxis : undefined} tick={AXIS} axisLine={false} tickLine={false} allowDecimals={currency} />
          <YAxis type="category" dataKey="name" tick={AXIS} width={124} axisLine={false} tickLine={false}
            tickFormatter={v => v.length > 19 ? v.slice(0, 18) + "…" : v} />
        </> : <>
          <XAxis dataKey="name" tick={AXIS} axisLine={false} tickLine={false} />
          <YAxis tick={AXIS} tickLine={false} axisLine={false} allowDecimals={false} width={40} />
        </>}
        <Tooltip formatter={currency ? money : undefined} />
        <Bar name={name} dataKey="value" fill={horizontal ? NAVY : ORANGE} radius={horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0]} maxBarSize={27} isAnimationActive={false} />
      </BarChart>
    </ResponsiveContainer></div>;
}
export function Compare({ data }) {
  if (!data.length) return <Empty>Harga kontrak aktual belum ada.</Empty>;
  return <div className="chart" role="img" aria-label="Perbandingan benchmark dan harga kontrak aktual">
    <ResponsiveContainer width="100%" height="100%"><BarChart data={data.slice(0, 6)} margin={{ top: 8, right: 16, left: 0, bottom: 4 }}>
      <CartesianGrid vertical={false} stroke={GRID}/>
      <XAxis dataKey="name" hide /><YAxis tickFormatter={moneyAxis} width={54} tick={AXIS} axisLine={false} tickLine={false}/>
      <Tooltip formatter={money} /><Legend iconSize={9} />
      <Bar name="Benchmark" dataKey="benchmark" fill={NAVY} radius={[4, 4, 0, 0]} maxBarSize={54} isAnimationActive={false} />
      <Bar name="Kontrak aktual" dataKey="actual" fill={ORANGE} radius={[4, 4, 0, 0]} maxBarSize={54} isAnimationActive={false} />
    </BarChart></ResponsiveContainer></div>;
}
export function distribution(rows) {
  if (!rows.length) return [];
  const prices = rows.map(r => r.price);
  const min = Math.min(...prices), max = Math.max(...prices);
  if (min === max) return [{ name: moneyAxis(min), value: prices.length }];
  const step = (max - min) / 6;
  const bins = Array.from({ length: 6 }, (_, i) => ({
    name: moneyAxis(min + i * step) + "–" + moneyAxis(min + (i + 1) * step), value: 0,
  }));
  for (const price of prices) bins[Math.min(5, Math.floor((price - min) / step))].value++;
  return bins;
}
