from __future__ import annotations

import argparse
from pathlib import Path

from analyzer import analyze
from llm_client import LLMConfig, maybe_run_llm_analysis
from loaders import load_account_profile, load_competitors, load_posts_csv, load_reference_posts_csv, load_trends
from report_generator import write_markdown_report
from tiktok_api import (
    DEFAULT_SCOPES,
    DEFAULT_USER_FIELDS,
    DEFAULT_VIDEO_FIELDS,
    OAuthConfig,
    build_authorization_url,
    exchange_code_for_token,
    fetch_user_info,
    fetch_video_list,
    load_token_file,
    normalize_video_list_file,
    parse_fields,
    refresh_access_token,
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
    parser.add_argument("--account", default="data/account_profile.sample.json", help="Path to account profile JSON.")
    parser.add_argument("--posts", default="data/posts.sample.csv", help="Path to posts CSV.")
    parser.add_argument("--trends", default="data/trends.sample.json", help="Path to trends JSON.")
    parser.add_argument("--competitors", default="data/competitors.sample.json", help="Path to competitors JSON.")
    parser.add_argument("--competitor-posts", default="data/competitor_posts.sample.csv", help="Path to competitor/reference posts CSV.")
    parser.add_argument("--llm-provider", default="none", choices=["none", "openai", "anthropic"], help="Optional external LLM provider.")
    parser.add_argument("--llm-model", default=None, help="Model ID for the selected LLM provider.")
    parser.add_argument("--llm-max-input-chars", type=int, default=12000, help="Maximum characters sent to the LLM.")
    parser.add_argument("--llm-max-output-tokens", type=int, default=1200, help="Maximum output tokens requested from the LLM.")
    parser.add_argument("--output", default="reports/sample_report.md", help="Output Markdown report path.")


def _add_tiktok_parsers(subparsers: argparse._SubParsersAction) -> None:
    auth_url = subparsers.add_parser("auth-url", help="Build a TikTok OAuth authorization URL.")
    auth_url.add_argument("--client-key", required=True)
    auth_url.add_argument("--redirect-uri", required=True)
    auth_url.add_argument("--scopes", default=",".join(DEFAULT_SCOPES))
    auth_url.add_argument("--state", default=None)
    auth_url.add_argument("--code-challenge", default=None)
    auth_url.add_argument("--code-challenge-method", default="S256")

    exchange = subparsers.add_parser("exchange-token", help="Exchange authorization code for access/refresh tokens.")
    exchange.add_argument("--client-key", required=True)
    exchange.add_argument("--client-secret", required=True)
    exchange.add_argument("--code", required=True)
    exchange.add_argument("--redirect-uri", required=True)
    exchange.add_argument("--code-verifier", default=None)
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
    posts = load_posts_csv(args.posts)
    trends = load_trends(args.trends)
    competitors = load_competitors(args.competitors)
    competitor_posts = load_reference_posts_csv(args.competitor_posts)
    analysis = analyze(account, posts, trends, competitors, competitor_posts)
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
    if args.tiktok_command == "auth-url":
        url = build_authorization_url(
            OAuthConfig(
                client_key=args.client_key,
                redirect_uri=args.redirect_uri,
                scopes=parse_fields(args.scopes, DEFAULT_SCOPES),
                state=args.state,
                code_challenge=args.code_challenge,
                code_challenge_method=args.code_challenge_method,
            )
        )
        print(url)
        return 0

    if args.tiktok_command == "exchange-token":
        token_data = exchange_code_for_token(
            client_key=args.client_key,
            client_secret=args.client_secret,
            code=args.code,
            redirect_uri=args.redirect_uri,
            code_verifier=args.code_verifier,
        )
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
        save_token_file(args.token_file, token_data)
        print(f"Token refreshed: {Path(args.token_file).resolve()}")
        return 0

    if args.tiktok_command == "fetch-user":
        token_data = load_token_file(args.token_file)
        user_data = fetch_user_info(token_data["access_token"], parse_fields(args.fields, DEFAULT_USER_FIELDS))
        write_json(args.output, user_data)
        print(f"User info saved: {Path(args.output).resolve()}")
        return 0

    if args.tiktok_command == "fetch-videos":
        token_data = load_token_file(args.token_file)
        video_data = fetch_video_list(
            access_token=token_data["access_token"],
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


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "tiktok":
        return run_tiktok(args)
    return run_report(args)


if __name__ == "__main__":
    raise SystemExit(main())
