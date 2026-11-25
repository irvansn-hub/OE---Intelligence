from datetime import date, timedelta

from components.formatting import DEMO, today

LAPTOP = {
    "item_name": "Laptop Bisnis 14 inci", "category": "Teknologi Informasi",
    "specification": "Core i5, RAM 16 GB, SSD 512 GB, layar 14 inci",
    "brand": "", "unit": "unit", "region": "DKI Jakarta", "location": "Jakarta",
}


def demo_prices(as_of=None):
    as_of = as_of or today()
    rows = []

    def add(item, days, price, source_type, source_name, vendor, quantity, edition=None, **changes):
        observation_date = as_of - timedelta(days=days)
        year = observation_date.year
        rows.append({
            **item, "quantity": float(quantity), "price": float(price), "source_type": source_type,
            "source_name": source_name, "vendor": vendor, "observation_date": observation_date,
            "effective_year": year, "effective_date": date(year, 1, 1), "version": edition or "Demo v1",
            "url_reference": f"DEMO/KAI-HPS/{len(rows) + 1:03d}", "notes": DEMO, "is_demo": True,
            **changes,
        })

    channels = [
        ("MARKET_SURVEY", "Survei Toko Jakarta (Demo)", "Toko Cakra (Demo)"),
        ("SUPPLIER_QUOTATION", "Penawaran Sagara (Demo)", "PT Sagara (Demo)"),
        ("MARKETPLACE", "Survei Marketplace (Demo)", "Toko Lintas (Demo)"),
        ("SUPPLIER_QUOTATION", "Penawaran Nusa (Demo)", "PT Nusa (Demo)"),
        ("MANUFACTURER", "Daftar Pabrikan (Demo)", "Pabrikan Cendana (Demo)"),
        ("KAI_HISTORICAL_CONTRACT", "Kontrak KAI (Demo)", "PT Arunika (Demo)"),
        ("GOVERNMENT", "Referensi Harga Pemerintah (Demo)", ""),
        ("KAI_HISTORICAL_HPS", "Rekap HPS KAI (Demo)", ""),
    ]
    for i in range(40):
        days = 8 + i * 17
        price = 10_900_000 - 25_000 * i + (0, 100_000, -80_000, 30_000)[i % 4]
        add(LAPTOP, days, price, *channels[i % len(channels)], 20)
    add(LAPTOP, 12, 27_500_000, *channels[2], 20)
    add(LAPTOP, 22, 8_100_000, *channels[1], 20, specification="Core i3, RAM 8 GB, SSD 256 GB")
    add(LAPTOP, 49, 10_600_000, *channels[3], 5, region="Jawa Barat", location="Bandung")
    bearing = {
        "item_name": "Bearing 6205-2RS", "category": "Suku Cadang",
        "specification": "Bantalan 25 × 52 × 15 mm, seal karet ganda",
        "brand": "", "unit": "buah", "region": "Jawa Barat", "location": "Bandung",
    }
    consulting = {
        "item_name": "Konsultan Ahli Transportasi", "category": "Jasa Konsultansi",
        "specification": "Ahli transportasi S2, pengalaman 8 tahun",
        "brand": "", "unit": "orang-bulan", "region": "DKI Jakarta", "location": "Jakarta",
    }
    for i in range(12):
        add(bearing, 10 + i * 31, 205_000 - 1_250 * i + (i % 3) * 4_000, *channels[i % 5], 100)
        add(consulting, 22 + i * 41, 32_500_000 - i * 240_000,
            "ASSOCIATION", "INKINDO (Demo)", "", 3)
    return rows


def demo_indices(as_of):
    return {str(as_of.year - offset): .025 + offset * .003 for offset in range(4)}

