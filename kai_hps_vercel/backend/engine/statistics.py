from collections import Counter
from math import isfinite
from statistics import fmean, stdev


def summarize(values):
    data = sorted(float(value) for value in values if value is not None and isfinite(value) and value > 0)
    keys = ("min", "max", "mean", "median", "std", "cv", "p10", "p25", "p75", "p90", "iqr")
    if not data:
        return {"n": 0, **dict.fromkeys(keys), "modes": []}

    def percentile(probability):
        position = (len(data) - 1) * probability
        left_index = int(position)
        right_index = min(left_index + 1, len(data) - 1)
        return data[left_index] + (position - left_index) * (data[right_index] - data[left_index])

    p10, p25, median, p75, p90 = (percentile(p) for p in (.1, .25, .5, .75, .9))
    mean = fmean(data)
    std = stdev(data) if len(data) > 1 else None
    counts = Counter(data)
    frequency = max(counts.values())
    modes = sorted(value for value, count in counts.items() if count == frequency)
    if frequency < 2 or (len(modes) == len(counts) and len(modes) > 1):
        modes = []
    return {
        "n": len(data), "min": data[0], "max": data[-1], "mean": mean, "median": median,
        "modes": modes, "std": std, "cv": std / mean if std is not None else None,
        "p10": p10, "p25": p25, "p75": p75, "p90": p90, "iqr": p75 - p25,
    }
