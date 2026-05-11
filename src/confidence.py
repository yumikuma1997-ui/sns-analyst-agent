from __future__ import annotations


LEVELS = ("信頼度A", "信頼度B", "信頼度C", "信頼度D")


def calculate_confidence_level(
    post_count: int,
    has_api_metrics: bool = True,
    qualitative_coverage: float = 0.0,
    manual_coverage: float = 0.0,
) -> str:
    if post_count <= 0 or not has_api_metrics:
        return "信頼度D"
    if post_count >= 30 and qualitative_coverage >= 0.5:
        return "信頼度A"
    if post_count >= 10:
        return "信頼度B"
    return "信頼度C"


def calculate_api_aggregation_confidence(post_count: int, has_view_metrics: bool) -> str:
    if post_count <= 0 or not has_view_metrics:
        return "信頼度D"
    if post_count >= 30:
        return "信頼度A"
    if post_count >= 10:
        return "信頼度B"
    return "信頼度C"


def calculate_strategy_confidence(
    post_count: int,
    manual_count: int,
    creative_count: int,
    trend_count: int,
    competitor_count: int,
    creative_coverage: float = 0.0,
) -> str:
    if post_count <= 0:
        return "信頼度D"
    if creative_count == 0 and trend_count == 0 and competitor_count == 0:
        return "信頼度D"
    if post_count >= 30 and creative_coverage >= 0.5 and trend_count > 0 and competitor_count > 0:
        level = "信頼度A"
    elif post_count >= 10 and creative_count > 0:
        level = "信頼度B"
    else:
        level = "信頼度C"
    if any(count == 0 for count in (manual_count, creative_count, trend_count, competitor_count)):
        return cap_confidence(level, "信頼度C")
    return level


def manual_metric_confidence(has_values: bool, post_count: int) -> str:
    if not has_values:
        return "信頼度D"
    if post_count >= 10:
        return "信頼度B"
    return "信頼度C"


def cap_confidence(level: str, max_level: str) -> str:
    level_index = LEVELS.index(level) if level in LEVELS else LEVELS.index("信頼度D")
    max_index = LEVELS.index(max_level) if max_level in LEVELS else LEVELS.index("信頼度D")
    return LEVELS[max(level_index, max_index)]


def confidence_description(level: str) -> str:
    return {
        "信頼度A": "API数値または手入力データが十分あり、投稿数も十分です。",
        "信頼度B": "数値はありますが、定性情報または一部の手入力が不足しています。",
        "信頼度C": "投稿数または入力項目が不足しており、暫定仮説として扱ってください。",
        "信頼度D": "データ不足です。判断材料として使わず、先に入力データを増やしてください。",
    }.get(level, "信頼度不明")
