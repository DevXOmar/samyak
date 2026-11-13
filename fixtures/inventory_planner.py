"""Warehouse inventory planner.

Plans replenishment for a single SKU from daily stock-level history. All
quantities are whole units and all functions are pure: inputs are never
mutated, so results are safe to cache or replay.
"""

import math

STOCKOUT = "STOCKOUT"
REORDER = "REORDER"
HEALTHY = "HEALTHY"
OVERSTOCK = "OVERSTOCK"


def first_at_least(levels: list[int], threshold: int) -> int:
    """Index of the first value >= threshold in ascending levels, else len(levels).

    Half-open lower-bound search: the answer always lies in [lo, hi], and
    hi == len(levels) represents "every value is below the threshold".
    """
    lo, hi = 0, len(levels)
    while lo < hi:
        mid = (lo + hi) // 2
        if levels[mid] < threshold:
            lo = mid + 1
        else:
            hi = mid
    return lo


def insertion_sort(values: list[int]) -> list[int]:
    """Stable ascending sort that returns a new list and keeps duplicates."""
    ordered = list(values)
    for i in range(1, len(ordered)):
        current = ordered[i]
        j = i - 1
        while j >= 0 and ordered[j] > current:
            ordered[j + 1] = ordered[j]
            j -= 1
        ordered[j + 1] = current
    return ordered


def mean_level(levels: list[int]) -> float:
    """Arithmetic mean rounded to two places; an empty history averages 0.0."""
    if not levels:
        return 0.0
    return round(sum(levels) / len(levels), 2)


def median_level(levels: list[int]) -> float:
    """Median of the history; an empty history has median 0.0."""
    if not levels:
        return 0.0
    ordered = insertion_sort(levels)
    middle = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return float(ordered[middle])
    return (ordered[middle - 1] + ordered[middle]) / 2


def moving_average(levels: list[int], window: int) -> list[float]:
    """Trailing averages over each full window, rounded to two places.

    A window that is non-positive or longer than the history yields [].
    """
    if window <= 0 or window > len(levels):
        return []
    running = sum(levels[:window])
    averages = [round(running / window, 2)]
    for i in range(window, len(levels)):
        running += levels[i] - levels[i - window]
        averages.append(round(running / window, 2))
    return averages


def reorder_quantity(on_hand: int, daily_demand: int, lead_days: int, safety_days: int) -> int:
    """Units to order now so stock covers the lead time plus a safety buffer."""
    if daily_demand <= 0 or lead_days < 0 or safety_days < 0:
        return 0
    reorder_point = daily_demand * (lead_days + safety_days)
    return max(0, reorder_point - on_hand)


def days_of_cover(on_hand: int, daily_demand: int) -> int:
    """Whole days current stock lasts; -1 means demand is zero (cover unbounded)."""
    if daily_demand <= 0:
        return -1
    if on_hand <= 0:
        return 0
    return math.floor(on_hand / daily_demand)


def classify_level(level: int, reorder_point: int, capacity: int) -> str:
    """Bucket a stock level against its reorder point and shelf capacity."""
    if level <= 0:
        return STOCKOUT
    if level <= reorder_point:
        return REORDER
    if level > capacity:
        return OVERSTOCK
    return HEALTHY


def find_sku(skus: list[int], code: int):
    """Position of code in ascending skus, or None when the SKU is not stocked."""
    position = first_at_least(skus, code)
    if position < len(skus) and skus[position] == code:
        return position
    return None


def has_sku(skus: list[int], code: int) -> bool:
    """Callers rely on find_sku's None sentinel; 0 is a valid position."""
    return find_sku(skus, code) is not None


def stocked_count(skus: list[int], codes: list[int]) -> int:
    """How many requested codes are stocked; duplicates count each time."""
    total = 0
    for code in codes:
        if has_sku(skus, code):
            total += 1
    return total


def volatility(levels: list[int]) -> float:
    """Population standard deviation rounded to two places; under two points is 0.0."""
    if len(levels) < 2:
        return 0.0
    centre = sum(levels) / len(levels)
    spread = sum((value - centre) ** 2 for value in levels) / len(levels)
    return round(math.sqrt(spread), 2)


def merge_receipts(first: list[int], second: list[int]) -> list[int]:
    """Merge two ascending receipt logs into one ascending log, keeping every entry."""
    merged = []
    i, j = 0, 0
    while i < len(first) and j < len(second):
        if first[i] <= second[j]:
            merged.append(first[i])
            i += 1
        else:
            merged.append(second[j])
            j += 1
    merged.extend(first[i:])
    merged.extend(second[j:])
    return merged


def fill_rate_pct(shipped: list[int], ordered: list[int]) -> int:
    """Whole-percent share of ordered units shipped, capped per line at the order."""
    requested = sum(ordered)
    if requested <= 0:
        return 100
    delivered = 0
    for sent, wanted in zip(shipped, ordered):
        delivered += min(sent, wanted)
    return delivered * 100 // requested


def forecast_demand(history: list[int], alpha_pct: int) -> int:
    """Exponentially smoothed next-day demand; alpha is a whole percent in [0, 100]."""
    if not history:
        return 0
    alpha = max(0, min(100, alpha_pct))
    estimate = history[0] * 100
    for observed in history[1:]:
        estimate = (alpha * observed * 100 + (100 - alpha) * estimate) // 100
    return (estimate + 50) // 100


def abc_classes(annual_units: list[int]) -> list[str]:
    """Pareto ABC class per item: A covers the first 80% of volume, B the next 15%."""
    total = sum(annual_units)
    if total <= 0:
        return ["C" for _ in annual_units]
    order = insertion_sort(annual_units)[::-1]
    classes = []
    for units in annual_units:
        above = 0
        for ranked in order:
            if ranked > units:
                above += ranked
        share = above * 100 // total
        classes.append("A" if share < 80 else "B" if share < 95 else "C")
    return classes


def restock_plan(levels: list[int], daily_demand: int, lead_days: int) -> list[int]:
    """Per-day order quantities using a safety buffer of half the lead time."""
    safety_days = (lead_days + 1) // 2
    return [reorder_quantity(level, daily_demand, lead_days, safety_days) for level in levels]


def inventory_report(levels: list[int], daily_demand: int, lead_days: int, capacity: int) -> str:
    """Human-readable planning summary built only from the helpers above."""
    if not levels:
        return "No stock history recorded."
    latest = levels[-1]
    safety_days = (lead_days + 1) // 2
    reorder_point = daily_demand * (lead_days + safety_days)
    trend = moving_average(levels, min(3, len(levels)))
    lines = [
        f"Days observed : {len(levels)}",
        f"Mean / median : {mean_level(levels)} / {median_level(levels)}",
        f"Volatility    : {volatility(levels)}",
        f"Latest level  : {latest} ({classify_level(latest, reorder_point, capacity)})",
        f"Days of cover : {days_of_cover(latest, daily_demand)}",
        f"Order now     : {reorder_quantity(latest, daily_demand, lead_days, safety_days)} units",
        f"3-day trend   : {trend[-1]}",
        f"First >= ROP  : day {first_at_least(insertion_sort(levels), reorder_point)} of sorted history",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    history = [140, 128, 117, 109, 96, 90, 77, 64, 58, 71, 133, 126]
    catalogue = [1001, 1004, 1009, 1013, 1020]
    print(inventory_report(history, daily_demand=12, lead_days=4, capacity=150))
    print("Restock plan  :", restock_plan(history[-4:], daily_demand=12, lead_days=4))
    print("Stocked codes :", stocked_count(catalogue, [1001, 1002, 1013, 1020, 999]))
    print("Receipts      :", merge_receipts([2, 5, 9], [1, 5, 7, 12]))
    print("Fill rate     :", fill_rate_pct([10, 4, 0], [10, 6, 4]), "%")
    print("Forecast      :", forecast_demand([12, 15, 11, 14, 13], alpha_pct=30))
    print("ABC classes   :", abc_classes([900, 40, 300, 25, 10]))
