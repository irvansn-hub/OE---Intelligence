def fences(stats):
    if stats["n"] < 4:
        return None, None
    margin = 1.5 * stats["iqr"]
    return stats["p25"] - margin, stats["p75"] + margin


def outlier_reason(price, lower, upper):
    if price is None or lower is None:
        return ""
    if price < lower:
        return f"Di bawah pagar IQR ({lower:,.0f} IDR)"
    if price > upper:
        return f"Di atas pagar IQR ({upper:,.0f} IDR)"
    return ""
