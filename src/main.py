from __future__ import annotations

import argparse
import sys
from pathlib import Path

from analyzer import analyze
from llm_client import LLMConfig, maybe_run_llm_analysis
from loaders import (
    load_account_profile,
    load_api_posts,
    load_competitor_posts,
    load_creative_notes,
    load_manual_insights,
    load_trend_research,
)
from report_generator import write_markdown_report
from tiktok_api import (
    DEFAULT_SCOPES,
    DEFAULT_USER_FIELDS,
    DEFAULT_VIDEO_FIELDS,
    OAuthConfig,
    build_authorization_url,
    create_pkce_pair,
    exchange_code_for_token,
    fetch_user_info,
    fetch_video_list,
    load_pkce_file,
    load_token_file,
    normalize_video_list_file,
    parse_fields,
    refresh_access_token,
    save_pkce_file,
    save_token_file,
    write_json,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a local TikTok account analysis report.")
    _add_report_args(parser)

    subparsers = parser.add_subparsers(dest="command")
    report_parser = subparsers.add_parser("report", help="Generate Markdown report from local CSV/JSON files.")
    _add_report_args(report_parser)

    tiktok_parser = subparsers.add_parser("tiktok", help="Official TikTok API PoC commands.")
    tiktok_subparsers = tiktok_parser.add_subparsers(dest="tiktok_command", required=True)
    _add_tiktok_parsers(tiktok_subparsers)
    return parser


def _add_report_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--account", default="data/account_profile.local.json", help="Path to account profile JSON.")
    parser.add_argument("--api-posts", "--posts", dest="api_posts", default="data/tiktok_videos.local.csv", help="Path to official API posts CSV/JSON.")
    parser.add_argument("--manual-insights", default="data/manual_insights.local.csv", help="Path to manually entered TikTok Studio insight CSV/JSON.")
    parser.add_argument("--creative-notes", default="data/creative_notes.local.csv", help="Path to manually entered creative notes CSV/JSON.")
    parser.add_argument("--trend-research", "--trends", dest="trend_research", default="data/trend_research.local.csv", help="Path to manually researched trend CSV/JSON.")
    parser.add_argument("--competitor-posts", default="data/competitor_posts.local.csv", help="Path to competitor/reference post pattern CSV/JSON.")
    parser.add_argument("--competitors", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--llm-provider", default="none", choices=["none", "openai", "anthropic"], help="Optional external LLM provider.")
    parser.add_argument("--llm-model", default=None, help="Model ID for the selected LLM provider.")
    parser.add_argument("--llm-max-input-chars", type=int, default=12000, help="Maximum characters sent to the LLM.")
    parser.add_argument("--llm-max-output-tokens", type=int, default=1200, help="Maximum output tokens requested from the LLM.")
    parser.add_argument("--output", default="reports/tiktok_api_report.local.md", help="Output Markdown report path.")


def _add_tiktok_parsers(subparsers: argparse._SubParsersAction) -> None:
    auth_url = subparsers.add_parser("auth-url", help="Build a TikTok OAuth authorization URL.")
    auth_url.add_argument("--client-key", required=True)
    auth_url.add_argument("--redirect-uri", required=True)
    auth_url.add_argument("--scopes", default=",".join(DEFAULT_SCOPES))
    auth_url.add_argument("--state", default=None)
    auth_url.add_argument("--code-challenge", default=None)
    auth_url.add_argument("--code-challenge-method", default="S256")
    auth_url.add_argument("--pkce-file", default=None, help="Read or create a PKCE verifier/challenge JSON file.")

    pkce = subparsers.add_parser("create-pkce", help="Create a local PKCE verifier/challenge file.")
    pkce.add_argument("--output", default="data/tiktok_pkce.local.json")

    exchange = subparsers.add_parser("exchange-token", help="Exchange authorization code for access/refresh tokens.")
    exchange.add_argument("--client-key", required=True)
    exchange.add_argument("--client-secret", required=True)
    exchange.add_argument("--code", required=True)
    exchange.add_argument("--redirect-uri", required=True)
    exchange.add_argument("--code-verifier", default=None)
    exchange.add_argument("--pkce-file", default=None, help="Read code_verifier from a PKCE JSON file.")
    exchange.add_argument("--token-file", default="data/tiktok_tokens.local.json")

    refresh = subparsers.add_parser("refresh-token", help="Refresh a saved TikTok access token.")
    refresh.add_argument("--client-key", required=True)
    refresh.add_argument("--client-secret", required=True)
    refresh.add_argument("--token-file", default="data/tiktok_tokens.local.json")

    user = subparsers.add_parser("fetch-user", help="Fetch authorized user's profile/stat fields.")
    user.add_argument("--token-file", default="data/tiktok_tokens.local.json")
    user.add_argument("--fields", default=",".join(DEFAULT_USER_FIELDS))
    user.add_argument("--output", default="data/tiktok_user.raw.json")

    videos = subparsers.add_parser("fetch-videos", help="Fetch authorized user's public videos with Video List API.")
    videos.add_argument("--token-file", default="data/tiktok_tokens.local.json")
    videos.add_argument("--fields", default=",".join(DEFAULT_VIDEO_FIELDS))
    videos.add_argument("--max-count", type=int, default=20)
    videos.add_argument("--max-pages", type=int, default=None)
    videos.add_argument("--cursor", type=int, default=None)
    videos.add_argument("--output", default="data/tiktok_videos.raw.json")

    normalize = subparsers.add_parser("normalize-videos", help="Normalize TikTok raw JSON into analysis-compatible CSV.")
    normalize.add_argument("--input", default="data/tiktok_videos.raw.json")
    normalize.add_argument("--output", default="data/tiktok_videos.normalized.csv")


def run_report(args: argparse.Namespace) -> int:
    account = load_account_profile(args.account)
    api_posts = load_api_posts(args.api_posts)
    manual_insights = load_manual_insights(args.manual_insights)
    creative_notes = load_creative_notes(args.creative_notes)
    trend_research = load_trend_research(args.trend_research)
    competitor_posts = load_competitor_posts(args.competitor_posts)
    analysis = analyze(account, api_posts, manual_insights, creative_notes, trend_research, competitor_posts)
    analysis["input_files"] = {
        "account": args.account,
        "api_posts": args.api_posts,
        "manual_insights": args.manual_insights,
        "creative_notes": args.creative_notes,
        "trend_research": args.trend_research,
        "competitor_posts": args.competitor_posts,
    }
    analysis["llm_analysis"] = maybe_run_llm_analysis(
        analysis,
        LLMConfig(
            provider=args.llm_provider,
            model=args.llm_model,
            max_input_chars=args.llm_max_input_chars,
            max_output_tokens=args.llm_max_output_tokens,
        ),
    )
    write_markdown_report(analysis, args.output)
    print(f"Report generated: {Path(args.output).resolve()}")
    return 0


def run_tiktok(args: argparse.Namespace) -> int:
    if args.tiktok_command == "create-pkce":
        pkce_data = create_pkce_pair()
        save_pkce_file(args.output, pkce_data)
        print(f"PKCE saved: {Path(args.output).resolve()}")
        print(f"code_challenge: {pkce_data['code_challenge']}")
        return 0

    if args.tiktok_command == "auth-url":
        code_challenge = args.code_challenge
        code_challenge_method = args.code_challenge_method
        if args.pkce_file:
            pkce_path = Path(args.pkce_file)
            if pkce_path.exists():
                pkce_data = load_pkce_file(pkce_path)
            else:
                pkce_data = create_pkce_pair()
                save_pkce_file(pkce_path, pkce_data)
            code_challenge = pkce_data["code_challenge"]
            code_challenge_method = pkce_data.get("code_challenge_method", "S256")
        url = build_authorization_url(
            OAuthConfig(
                client_key=args.client_key,
                redirect_uri=args.redirect_uri,
                scopes=parse_fields(args.scopes, DEFAULT_SCOPES),
                state=args.state,
                code_challenge=code_challenge,
                code_challenge_method=code_challenge_method,
            )
        )
        print(url)
        return 0

    if args.tiktok_command == "exchange-token":
        code_verifier = args.code_verifier
        if args.pkce_file:
            code_verifier = load_pkce_file(args.pkce_file)["code_verifier"]
        token_data = exchange_code_for_token(
            client_key=args.client_key,
            client_secret=args.client_secret,
            code=args.code,
            redirect_uri=args.redirect_uri,
            code_verifier=code_verifier,
        )
        if not _has_access_token(token_data):
            _print_token_error("Token exchange failed", token_data)
            return 1
        save_token_file(args.token_file, token_data)
        print(f"Token saved: {Path(args.token_file).resolve()}")
        return 0

    if args.tiktok_command == "refresh-token":
        current_token = load_token_file(args.token_file)
        token_data = refresh_access_token(
            client_key=args.client_key,
            client_secret=args.client_secret,
            refresh_token=current_token["refresh_token"],
        )
        if not _has_access_token(token_data):
            _print_token_error("Token refresh failed", token_data)
            return 1
        save_token_file(args.token_file, token_data)
        print(f"Token refreshed: {Path(args.token_file).resolve()}")
        return 0

    if args.tiktok_command == "fetch-user":
        token_data = load_token_file(args.token_file)
        access_token = _access_token_or_none(token_data)
        if not access_token:
            return 1
        user_data = fetch_user_info(access_token, parse_fields(args.fields, DEFAULT_USER_FIELDS))
        write_json(args.output, user_data)
        print(f"User info saved: {Path(args.output).resolve()}")
        return 0

    if args.tiktok_command == "fetch-videos":
        token_data = load_token_file(args.token_file)
        access_token = _access_token_or_none(token_data)
        if not access_token:
            return 1
        video_data = fetch_video_list(
            access_token=access_token,
            fields=parse_fields(args.fields, DEFAULT_VIDEO_FIELDS),
            max_count=args.max_count,
            max_pages=args.max_pages,
            cursor=args.cursor,
        )
        write_json(args.output, video_data)
        print(f"Videos saved: {Path(args.output).resolve()}")
        return 0

    if args.tiktok_command == "normalize-videos":
        rows = normalize_video_list_file(args.input, args.output)
        print(f"Normalized videos saved: {Path(args.output).resolve()} ({len(rows)} rows)")
        return 0

    raise ValueError(f"Unknown tiktok command: {args.tiktok_command}")


def _has_access_token(token_data: dict[str, object]) -> bool:
    return isinstance(token_data.get("access_token"), str) and bool(token_data["access_token"])


def _access_token_or_none(token_data: dict[str, object]) -> str | None:
    access_token = token_data.get("access_token")
    if isinstance(access_token, str) and access_token:
        return access_token
    _print_token_error("Token file does not contain access_token", token_data)
    return None


def _print_token_error(prefix: str, token_data: dict[str, object]) -> None:
    error = token_data.get("error") or "unknown_error"
    description = token_data.get("error_description") or "No error_description returned."
    print(f"{prefix}: {error} - {description}", file=sys.stderr)


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "tiktok":
        return run_tiktok(args)
    return run_report(args)


if __name__ == "__main__":
    raise SystemExit(main())
