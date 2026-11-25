from math import prod


def normalize_price(price, observed_year, target_year, rates):
    if price is None or price <= 0:
        return None, None, "Harga tidak valid"
    if not rates:
        return None, None, "Indeks tidak dipilih"
    if observed_year >= target_year:
        return None, None, "Di luar periode penyesuaian tahunan"
    years = range(observed_year + 1, target_year + 1)
    missing = [str(year) for year in years if str(year) not in rates]
    if missing:
        return None, None, "Indeks belum tersedia untuk " + ", ".join(missing)
    factor = prod(1 + rates[str(year)] for year in years)
    return price * factor, factor, f"Indeks kumulatif {observed_year + 1}–{target_year}"
