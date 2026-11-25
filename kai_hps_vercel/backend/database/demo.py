from datetime import date, datetime, timedelta
from functools import lru_cache

from components.formatting import DEMO, today
from database.db import as_json, make_observation
from database.sample import LAPTOP, demo_indices, demo_prices
from engine.cleaning import prepare_evidence
from engine.recommendation import analyze


@lru_cache(maxsize=1)
def demo_workspace():
    as_of = today()
    prices = sorted((make_observation(row) for row in demo_prices(as_of)),
                    key=lambda row: row["observation_date"], reverse=True)
    rates = demo_indices(as_of)
    indices = [{"index_name": "Indeks contoh (Demo)", "year": int(year), "adjustment_rate": rate,
                "is_demo": True} for year, rate in rates.items()]
    ctx = {
        **LAPTOP, "analysis_name": "DEMO-HPS-001 · Laptop operasional", "quantity": 20.0,
        "analysis_date": as_of.isoformat(), "target_date": min(as_of + timedelta(days=20),
        date(as_of.year, 12, 31)).isoformat(), "notes": DEMO,
        "recent_days": 365, "minimum_market": 5, "enable_forecast": True,
        "index_name": "Indeks contoh (Demo)", "index_demo": True, "rates": rates,
        "saved_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    rows = prepare_evidence([row for row in prices if row["item_name"] == LAPTOP["item_name"]], ctx)
    for row in rows:
        if row["price"] > 20_000_000:
            row.update(decision="EXCLUDE", justification="Harga ekstrem. Cakupan paket belum dikonfirmasi.")
        elif any("spesifikasi" in flag for flag in row["flags"]):
            row.update(decision="EXCLUDE", justification="Spesifikasi CPU, RAM dan SSD lebih rendah.")
        elif row["eligible"] and all("berumur" in flag for flag in row["flags"]):
            row["decision"] = "INCLUDE"
    snapshot = {
        "analysis_id": "demo-hps-laptop", "context": ctx, "actual_unit_price": 10_720_000,
        "result": analyze(rows, ctx), "evidence": rows,
    }
    return as_json({"prices": prices, "indices": indices, "analyses": [snapshot]})
