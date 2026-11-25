from datetime import date
from statistics import fmean

MIN_OBSERVATIONS = 12
MIN_DATES = 6
MIN_SPAN_DAYS = 180
MAX_HORIZON_DAYS = 365


def forecast(rows, target_date):
    usable = [r for r in rows if not r["is_outlier"] and not any(
        ("spesifikasi" in flag or "Merek" in flag or "Nama barang" in flag or "duplikat" in flag)
        for flag in r.get("flags", [])
    )]
    dates = [date.fromisoformat(r["observation_date"]).toordinal() for r in usable]
    n = len(dates)
    if n < MIN_OBSERVATIONS or len(set(dates)) < MIN_DATES or max(dates) - min(dates) < MIN_SPAN_DAYS:
        return {"price": None, "n": n, "note": "Perlu 12 bukti, 6 tanggal unik, dan rentang 180 hari."}
    target = date.fromisoformat(str(target_date)).toordinal()
    if target < min(dates) or target - max(dates) > MAX_HORIZON_DAYS:
        return {"price": None, "n": n, "note": "Tanggal sasaran berada di luar cakupan model."}

    prices = [r["price"] for r in usable]
    if min(prices) == max(prices):
        return {"price": None, "n": n, "note": "Seluruh harga model sama; tren tidak diestimasi."}

    mean_date, mean_price = fmean(dates), fmean(prices)
    date_dev = [value - mean_date for value in dates]
    price_dev = [value - mean_price for value in prices]
    slope = sum(x * y for x, y in zip(date_dev, price_dev)) / sum(x * x for x in date_dev)
    estimate = mean_price + slope * (target - mean_date)
    residual_ss = sum((y - slope * x) ** 2 for x, y in zip(date_dev, price_dev))
    score = 1 - residual_ss / sum(y * y for y in price_dev)
    if estimate <= 0:
        return {"price": None, "n": n, "note": "Prediksi tidak valid."}
    quality = "Rendah" if score < .4 else "Moderat" if score < .75 else "Baik"
    return {
        "price": estimate, "r2": score, "n": n, "quality": quality,
        "note": "Kecocokan model lemah; gunakan dengan hati-hati." if score < .4
                else "R² dihitung pada data pelatihan. Perkiraan bersifat pendukung.",
    }
