from datetime import datetime
from zoneinfo import ZoneInfo

DEMO = "DEMO / SYNTHETIC DATA"


def today():
    return datetime.now(ZoneInfo("Asia/Jakarta")).date()


def rupiah(value):
    return "—" if value is None else "Rp " + f"{value:,.0f}".replace(",", ".")


def price_range(low, high):
    return "—" if low is None else f"{rupiah(low)} – {rupiah(high)}"
