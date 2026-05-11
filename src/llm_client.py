from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from utils import DATA_INSUFFICIENT, format_number, format_percent, safe_join


@dataclass
class LLMConfig:
    provider: str = "none"
    model: str | None = None
    max_input_chars: int = 12000
    max_output_tokens: int = 1200


def maybe_run_llm_analysis(analysis: dict[str, Any], config: LLMConfig) -> dict[str, str | bool | None]:
    provider = (config.provider or "none").lower()
    if provider == "none":
        return {
            "enabled": False,
            "status": "未実行",
            "provider": "none",
            "model": None,
            "text": "外部LLM分析は未実行です。--llm-provider openai または anthropic と --llm-model を指定すると、ローカル入力データだけを使った定性分析を追加できます。",
            "error": None,
        }
    if provider not in {"openai", "anthropic"}:
        return _llm_error(provider, config.model, f"未対応のLLM providerです: {provider}")
    if not config.model:
        return _llm_error(provider, None, "--llm-model が未指定のため、外部LLM分析をスキップしました。")

    api_key_name = "OPENAI_API_KEY" if provider == "openai" else "ANTHROPIC_API_KEY"
    api_key = os.environ.get(api_key_name)
    if not api_key:
        return _llm_error(provider, config.model, f"{api_key_name} が未設定のため、外部LLM分析をスキップしました。")

    prompt = build_llm_prompt(analysis, config.max_input_chars)
    try:
        if provider == "openai":
            text = _call_openai_responses(api_key, config.model, prompt, config.max_output_tokens)
        else:
            text = _call_anthropic_messages(api_key, config.model, prompt, config.max_output_tokens)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return _llm_error(provider, config.model, f"外部LLM分析に失敗しました: {exc}")

    return {
        "enabled": True,
        "status": "実行済み",
        "provider": provider,
        "model": config.model,
        "text": text.strip() or "LLMから空の応答が返りました。",
        "error": None,
    }


def build_llm_prompt(analysis: dict[str, Any], max_chars: int = 12000) -> str:
    account = analysis["account"]
    summary = analysis["summary"]
    performance = analysis["performance"]
    habits = analysis["habits"]
    trend_analysis = analysis["trend_analysis"]
    competitor_analysis = analysis["competitor_analysis"]
    post_comparison = competitor_analysis.get("post_comparison", {})

    sections = [
        "あなたはショート動画SNSのグロースアナリストです。",
        "以下はユーザーがローカルに入力したTikTok運用データです。TikTokへアクセスしたり、外部サイトを推測したりせず、この入力だけを根拠に分析してください。",
        "断定しすぎず、仮説・追加検証が必要・データ不足を使い分けてください。",
        "",
        "## アカウント",
        f"- ジャンル: {account.get('genre', DATA_INSUFFICIENT)}",
        f"- ターゲット: {account.get('target_audience', DATA_INSUFFICIENT)}",
        f"- 目的: {account.get('operation_goal', DATA_INSUFFICIENT)}",
        "",
        "## KPIサマリー",
        f"- 投稿本数: {summary.get('post_count')}",
        f"- 中央値再生数: {format_number(summary.get('median_views'))}",
        f"- 平均保存率: {format_percent(summary.get('average_save_rate'))}",
        f"- 平均フォロー転換率: {format_percent(summary.get('average_follow_conversion_rate'))}",
        f"- データ品質: {summary.get('data_quality_note', DATA_INSUFFICIENT)}",
        "",
        "## 伸びた投稿の根拠",
        *[f"- {line}" for line in performance.get("top_evidence", [])],
        "",
        "## 伸びなかった投稿の根拠",
        *[f"- {line}" for line in performance.get("weak_evidence", [])],
        "",
        "## 投稿習慣メモ",
        *[f"- {line}" for line in habits.get("notes", [])],
        "",
        "## 手動入力トレンド",
        *[f"- {item.get('name')}: {item.get('applicable_points')}" for item in trend_analysis.get("easy_to_apply", [])],
        "",
        "## 競合・参考アカウント投稿比較",
        f"- 概要: {post_comparison.get('summary', DATA_INSUFFICIENT)}",
        "- 参考投稿から取り入れるべき点:",
        *[f"  - {item}" for item in post_comparison.get("adopt_points", [])],
        "- 取り入れない方がよい点:",
        *[f"  - {item}" for item in post_comparison.get("avoid_points", [])],
        "- 根拠となる参考投稿:",
        *[f"  - {item}" for item in post_comparison.get("top_reference_posts", [])],
        "",
        "## 出力してほしい内容",
        "1. 自アカウントが次の10投稿で取り入れるべき点",
        "2. 競合・参考アカウントから取り入れない方がよい点",
        "3. 冒頭3秒、動画構成、CTA、プロフィール導線の改善案",
        "4. 追加で入力すべきデータ",
    ]
    prompt = "\n".join(sections)
    return prompt[:max_chars]


def _call_openai_responses(api_key: str, model: str, prompt: str, max_output_tokens: int) -> str:
    url = os.environ.get("OPENAI_RESPONSES_URL", "https://api.openai.com/v1/responses")
    payload = {
        "model": model,
        "instructions": "You are a careful SNS analyst. Return concise Japanese markdown bullets grounded only in the provided data.",
        "input": prompt,
        "max_output_tokens": max_output_tokens,
    }
    data = _post_json(
        url,
        payload,
        {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    if isinstance(data.get("output_text"), str):
        return data["output_text"]
    texts = []
    for output in data.get("output", []):
        for content in output.get("content", []):
            text = content.get("text")
            if text:
                texts.append(text)
    return "\n".join(texts)


def _call_anthropic_messages(api_key: str, model: str, prompt: str, max_output_tokens: int) -> str:
    url = os.environ.get("ANTHROPIC_MESSAGES_URL", "https://api.anthropic.com/v1/messages")
    payload = {
        "model": model,
        "max_tokens": max_output_tokens,
        "system": "You are a careful SNS analyst. Return concise Japanese markdown bullets grounded only in the provided data.",
        "messages": [{"role": "user", "content": prompt}],
    }
    data = _post_json(
        url,
        payload,
        {
            "x-api-key": api_key,
            "anthropic-version": os.environ.get("ANTHROPIC_VERSION", "2023-06-01"),
            "Content-Type": "application/json",
        },
    )
    texts = []
    for content in data.get("content", []):
        text = content.get("text")
        if text:
            texts.append(text)
    return "\n".join(texts)


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            response_body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ValueError(f"HTTP {exc.code}: {body[:500]}") from exc
    return json.loads(response_body)


def _llm_error(provider: str, model: str | None, message: str) -> dict[str, str | bool | None]:
    return {
        "enabled": False,
        "status": "スキップ",
        "provider": provider,
        "model": model,
        "text": message,
        "error": message,
    }
