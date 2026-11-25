from engine.cleaning import MARKET_TYPES, canonical
from engine.outlier import fences, outlier_reason
from engine.regression import forecast
from engine.statistics import summarize


def independent_sources(rows):
    return len({canonical(r["vendor"]) or canonical(r["source_name"]) for r in rows})


def analyze(evidence, context):
    selected = []
    for row in evidence:
        row["is_comparable"] = row["decision"] == "INCLUDE" and row["eligible"]
        if row["is_comparable"]:
            selected.append(row)

    # Observed statistics always use original prices. An outlier stays included.
    stats = summarize([r["price"] for r in selected])
    lower, upper = fences(stats)
    for row in evidence:
        row["outlier_reason"] = outlier_reason(row["price"], lower, upper) if row["eligible"] else ""
        row["is_outlier"] = bool(row["outlier_reason"])

    days, minimum = context.get("recent_days", 365), context.get("minimum_market", 5)
    recent = [r for r in selected if 0 <= r["age_days"] <= days]
    market = [r for r in recent if r["source_type"] in MARKET_TYPES]
    adjusted = [r["adjusted_price"] for r in selected if r.get("adjusted_price") is not None
                and r["age_days"] > days]
    market_stats = summarize([r["price"] for r in market])
    normalized = summarize(adjusted)
    sources = independent_sources(selected)
    if len(market) >= minimum and independent_sources(market) >= 2:
        basis = market_stats
        explanation = (f"Median dan P25–P75 dari {len(market)} bukti pasar terkini "
                       f"yang disertakan, dari {independent_sources(market)} sumber independen.")
    elif recent:
        basis = summarize([r["price"] for r in recent])
        explanation = (f"Median dan P25–P75 dari {len(recent)} bukti terkini yang disertakan. "
                       "Ambang bukti pasar terkini belum terpenuhi.")
    elif normalized["n"]:
        basis = normalized
        explanation = (f"Median dan P25–P75 dari {normalized['n']} bukti historis "
                       "yang berhasil disesuaikan dengan indeks.")
    else:
        basis = stats
        explanation = ("Median dan P25–P75 dari bukti asli yang disertakan. "
                       "Tinjau relevansi periode harga.") if selected else "Belum ada bukti yang dapat dihitung."
    if normalized["n"] and recent:
        explanation += f" Median historis terindeks ({normalized['n']} bukti) ditampilkan sebagai pembanding."
    recency = len(recent) / len(selected) if selected else 0
    comparable = len(selected) / len(evidence) if evidence else 0
    cv = stats["cv"]
    high = [len(selected) >= 15, sources >= 4, recency >= .70, comparable >= .70, cv is not None and cv <= .20]
    mid = [len(selected) >= 5, sources >= 2, recency >= .40, comparable >= .50, cv is not None and cv <= .35]
    confidence = "TINGGI" if all(high) else "SEDANG" if all(mid) else "RENDAH"
    model = forecast(selected, context["target_date"]) if context.get("enable_forecast") else {
        "price": None, "n": 0, "note": "Peramalan nonaktif."
    }
    return {
        "stats": stats, "range_low": basis["p25"], "range_high": basis["p75"], "benchmark": basis["median"],
        "market_median": market_stats["median"], "normalized_median": normalized["median"],
        "explanation": explanation, "confidence": confidence, "independent_sources": sources,
        "recent_fraction": recency, "comparable_fraction": comparable, "forecast": model,
        "iqr_lower": lower, "iqr_upper": upper, "outlier_count": sum(r["is_outlier"] for r in evidence),
        "included_outliers": sum(r["is_outlier"] for r in selected),
    }
