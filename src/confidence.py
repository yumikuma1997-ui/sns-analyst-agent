from __future__ import annotations


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
        return "信頼度B" if qualitative_coverage < 0.5 else "信頼度A"
    return "信頼度C"


def manual_metric_confidence(has_values: bool, post_count: int) -> str:
    if not has_values:
        return "信頼度D"
    if post_count >= 10:
        return "信頼度B"
    return "信頼度C"


def confidence_description(level: str) -> str:
    return {
        "信頼度A": "API数値または手入力データが十分あり、投稿数も十分です。",
        "信頼度B": "数値はありますが、定性情報または一部入力が不足しています。",
        "信頼度C": "投稿数または入力項目が不足しており、暫定仮説です。",
        "信頼度D": "データ不足です。判断材料として使わず、先に入力を増やしてください。",
    }.get(level, "信頼度不明")
