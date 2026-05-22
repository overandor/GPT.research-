#!/usr/bin/env python3
"""
multi_platform_poster_stripe/app.py

Official-API-only multi-platform poster with:
- LLM draft generation via Ollama
- Human approval gate
- Optimal-time posting windows
- Dry-run default
- JSONL queue
- Per-platform dedupe
- Audit logs
- Stripe Checkout Session creation

Production boundary:
- This script never handles card data.
- Stripe uses hosted Checkout Sessions.
- Real fulfillment should be performed by a separate webhook server that verifies Stripe signatures.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


SUPPORTED_PLATFORMS = {"telegram", "x", "reddit", "pinterest", "tiktok", "stripe"}

OPTIMAL_WINDOWS = {
    "telegram": [9, 12, 18],
    "x": [8, 11, 17, 20],
    "reddit": [10, 14, 19],
    "pinterest": [12, 20, 21],
    "tiktok": [18, 19, 20, 21],
    "stripe": list(range(24)),
}


@dataclass(frozen=True)
class PostItem:
    line_number: int
    title: str
    text: str
    url: str | None
    media_url: str | None
    platforms: list[str]
    raw: dict[str, Any]
    content_hash: str


def now_ts() -> int:
    return int(time.time())


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def env_bool(name: str, default: bool = False) -> bool:
    value = env(name, "true" if default else "false").lower()
    return value in {"1", "true", "yes", "y", "on"}


def canonical_hash(parts: list[str]) -> str:
    normalized = " ".join(" ".join(parts).strip().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")


def append_jsonl(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, sort_keys=True) + "\n")


def http_request(method: str, url: str, *, headers=None, json_body=None, form_body=None, timeout=30):
    headers = headers or {}
    body = None

    if json_body is not None:
        body = json.dumps(json_body).encode("utf-8")
        headers = {"Content-Type": "application/json", **headers}
    elif form_body is not None:
        body = urllib.parse.urlencode(form_body).encode("utf-8")
        headers = {"Content-Type": "application/x-www-form-urlencoded", **headers}

    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return int(resp.status), resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return int(exc.code), exc.read().decode("utf-8", errors="replace")


def validate_platforms(platforms: list[str]) -> list[str]:
    clean = []
    for p in platforms:
        p = str(p).strip().lower()
        if not p:
            continue
        if p not in SUPPORTED_PLATFORMS:
            raise SystemExit(f"Unsupported platform: {p}")
        clean.append(p)
    return list(dict.fromkeys(clean))


def platform_optimal_now(platform: str) -> bool:
    return datetime.now().hour in OPTIMAL_WINDOWS.get(platform, [])


def compose_text(post: PostItem, max_len: int | None = None) -> str:
    text = post.text.strip()
    if post.url:
        text = f"{text}\n\n{post.url}"
    if max_len and len(text) > max_len:
        text = text[: max_len - 1].rstrip() + "…"
    return text


def load_queue(path: Path, max_chars: int, require_approval: bool) -> list[PostItem]:
    if not path.exists():
        raise SystemExit(f"Queue file not found: {path}")

    posts = []

    for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue

        raw = json.loads(line)

        if require_approval and not bool(raw.get("approved", False)):
            continue

        title = str(raw.get("title", "")).strip()
        text = str(raw.get("text", "")).strip()
        url = str(raw.get("url", "")).strip() or None
        media_url = str(raw.get("media_url", "")).strip() or None

        if not text:
            raise SystemExit(f"Missing text on line {idx}")
        if len(text) > max_chars:
            raise SystemExit(f"Line {idx} exceeds max chars")

        platforms = validate_platforms(raw.get("platforms", ["telegram"]))
        content_hash = canonical_hash([title, text, url or "", media_url or ""])

        posts.append(PostItem(idx, title, text, url, media_url, platforms, raw, content_hash))

    return posts


def platform_state_key(platform: str, post: PostItem) -> str:
    return f"{platform}:{post.content_hash}"


def already_posted(state: dict[str, Any], platform: str, post: PostItem) -> bool:
    return platform_state_key(platform, post) in set(state.get("posted_platform_hashes", []))


def platform_allowed(state: dict[str, Any], platform: str, min_interval: int) -> bool:
    last = int(state.get("last_post_ts_by_platform", {}).get(platform, 0) or 0)
    return now_ts() - last >= min_interval


def mark_posted(state: dict[str, Any], platform: str, post: PostItem, response_id: str | None = None):
    state.setdefault("posted_platform_hashes", [])
    state.setdefault("last_post_ts_by_platform", {})
    state.setdefault("posted_count_by_platform", {})
    state.setdefault("response_ids", {})

    key = platform_state_key(platform, post)

    if key not in state["posted_platform_hashes"]:
        state["posted_platform_hashes"].append(key)

    state["last_post_ts_by_platform"][platform] = now_ts()
    state["posted_count_by_platform"][platform] = int(state["posted_count_by_platform"].get(platform, 0)) + 1

    if response_id:
        state["response_ids"][key] = response_id

    return state


def next_pending(posts, state, platform_filter, min_interval, use_optimal_times):
    for post in posts:
        for platform in post.platforms:
            if platform_filter and platform not in platform_filter:
                continue
            if already_posted(state, platform, post):
                continue
            if not platform_allowed(state, platform, min_interval):
                continue
            if use_optimal_times and not platform_optimal_now(platform):
                continue
            return post, platform
    return None


def build_generation_prompt(topic: str, campaign: str, platforms: list[str]) -> str:
    return f"""
Create one compliant marketing draft for official API posting.

Rules:
- No fake scarcity.
- No guaranteed income claims.
- No impersonation.
- No engagement bait.
- No financial advice.
- No hashtag spam.
- Useful, concise, direct.
- Return strict JSON only.

Topic: {topic}
Campaign: {campaign}
Platforms: {platforms}

Return:
{{
  "title": "...",
  "text": "...",
  "url": "",
  "media_url": "",
  "platforms": {json.dumps(platforms)},
  "tags": [],
  "campaign": "{campaign}",
  "approved": false
}}
"""


def generate_with_ollama(prompt: str, args: argparse.Namespace) -> str:
    payload = {
        "model": args.ollama_model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": args.temperature,
            "num_predict": args.num_predict,
        },
    }

    status, body = http_request("POST", args.ollama_url, json_body=payload, timeout=args.timeout_seconds)

    if not (200 <= status < 300):
        raise RuntimeError(f"Ollama failed HTTP {status}: {body[:500]}")

    return str(json.loads(body).get("response", "")).strip()


def generate_draft(args: argparse.Namespace) -> int:
    if not args.topic.strip():
        raise SystemExit("--topic is required with --generate")

    platforms = validate_platforms(args.platforms.split(",") if args.platforms else ["telegram"])
    prompt = build_generation_prompt(args.topic, args.campaign, platforms)

    raw = generate_with_ollama(prompt, args)

    try:
        draft = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"LLM did not return valid JSON:\n{raw}") from exc

    draft["approved"] = False
    draft["campaign"] = draft.get("campaign") or args.campaign
    draft["platforms"] = validate_platforms(draft.get("platforms", platforms))

    append_jsonl(Path(args.drafts), draft)
    print(f"Draft written to {args.drafts}. Review it and set approved=true before live posting.")
    return 0


def post_telegram(post: PostItem, timeout: int):
    token = env("TELEGRAM_BOT_TOKEN")
    chat_id = env("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required")

    status, body = http_request(
        "POST",
        f"https://api.telegram.org/bot{token}/sendMessage",
        json_body={
            "chat_id": chat_id,
            "text": compose_text(post, 4096),
            "disable_web_page_preview": False,
        },
        timeout=timeout,
    )

    response_id = None
    try:
        response_id = str(json.loads(body).get("result", {}).get("message_id", "")) or None
    except json.JSONDecodeError:
        pass

    return status, body, response_id


def post_x(post: PostItem, timeout: int):
    token = env("X_BEARER_TOKEN")

    if not token:
        raise RuntimeError("X_BEARER_TOKEN is required")

    base = env("X_API_BASE", "https://api.x.com").rstrip("/")

    status, body = http_request(
        "POST",
        f"{base}/2/tweets",
        headers={"Authorization": f"Bearer {token}"},
        json_body={"text": compose_text(post, 280)},
        timeout=timeout,
    )

    response_id = None
    try:
        response_id = str(json.loads(body).get("data", {}).get("id", "")) or None
    except json.JSONDecodeError:
        pass

    return status, body, response_id


def reddit_access_token(timeout: int) -> str:
    client_id = env("REDDIT_CLIENT_ID")
    client_secret = env("REDDIT_CLIENT_SECRET")
    username = env("REDDIT_USERNAME")
    password = env("REDDIT_PASSWORD")
    user_agent = env("REDDIT_USER_AGENT", "multi-platform-poster/1.0")

    if not all([client_id, client_secret, username, password, user_agent]):
        raise RuntimeError("Missing Reddit credentials")

    auth_raw = f"{client_id}:{client_secret}".encode("utf-8")

    status, body = http_request(
        "POST",
        "https://www.reddit.com/api/v1/access_token",
        headers={
            "Authorization": "Basic " + base64.b64encode(auth_raw).decode("ascii"),
            "User-Agent": user_agent,
        },
        form_body={
            "grant_type": "password",
            "username": username,
            "password": password,
        },
        timeout=timeout,
    )

    if not (200 <= status < 300):
        raise RuntimeError(f"Reddit OAuth failed HTTP {status}: {body[:500]}")

    return str(json.loads(body)["access_token"])


def post_reddit(post: PostItem, timeout: int):
    subreddit = env("REDDIT_SUBREDDIT")
    user_agent = env("REDDIT_USER_AGENT", "multi-platform-poster/1.0")

    if not subreddit:
        raise RuntimeError("REDDIT_SUBREDDIT is required")

    token = reddit_access_token(timeout)
    title = post.title or post.text[:280]

    if post.url and env("REDDIT_KIND", "self").lower() == "link":
        form = {
            "api_type": "json",
            "kind": "link",
            "sr": subreddit,
            "title": title,
            "url": post.url,
            "sendreplies": "true",
        }
    else:
        form = {
            "api_type": "json",
            "kind": "self",
            "sr": subreddit,
            "title": title,
            "text": compose_text(post),
            "sendreplies": "true",
        }

    status, body = http_request(
        "POST",
        "https://oauth.reddit.com/api/submit",
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": user_agent,
        },
        form_body=form,
        timeout=timeout,
    )

    response_id = None
    try:
        response_id = str(json.loads(body).get("json", {}).get("data", {}).get("id", "")) or None
    except json.JSONDecodeError:
        pass

    return status, body, response_id


def post_pinterest(post: PostItem, timeout: int):
    token = env("PINTEREST_ACCESS_TOKEN")
    board_id = env("PINTEREST_BOARD_ID")

    if not token or not board_id:
        raise RuntimeError("PINTEREST_ACCESS_TOKEN and PINTEREST_BOARD_ID are required")
    if not post.media_url:
        raise RuntimeError("Pinterest requires media_url")

    status, body = http_request(
        "POST",
        "https://api.pinterest.com/v5/pins",
        headers={"Authorization": f"Bearer {token}"},
        json_body={
            "board_id": board_id,
            "title": post.title or post.text[:90],
            "description": post.text[:500],
            "link": post.url or "",
            "media_source": {
                "source_type": "image_url",
                "url": post.media_url,
            },
        },
        timeout=timeout,
    )

    response_id = None
    try:
        response_id = str(json.loads(body).get("id", "")) or None
    except json.JSONDecodeError:
        pass

    return status, body, response_id


def post_tiktok(post: PostItem, timeout: int):
    token = env("TIKTOK_ACCESS_TOKEN")

    if not token:
        raise RuntimeError("TIKTOK_ACCESS_TOKEN is required")
    if not post.media_url:
        raise RuntimeError("TikTok requires public video media_url")

    status, body = http_request(
        "POST",
        "https://open.tiktokapis.com/v2/post/publish/video/init/",
        headers={"Authorization": f"Bearer {token}"},
        json_body={
            "post_info": {
                "title": compose_text(post, 2200),
                "privacy_level": env("TIKTOK_PRIVACY_LEVEL", "SELF_ONLY"),
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
                "brand_content_toggle": False,
                "brand_organic_toggle": False,
                "is_aigc": env("TIKTOK_IS_AIGC", "true").lower() in {"1", "true", "yes", "y"},
            },
            "source_info": {
                "source": "PULL_FROM_URL",
                "video_url": post.media_url,
            },
        },
        timeout=timeout,
    )

    response_id = None
    try:
        response_id = str(json.loads(body).get("data", {}).get("publish_id", "")) or None
    except json.JSONDecodeError:
        pass

    return status, body, response_id


def post_stripe(post: PostItem, timeout: int):
    secret_key = env("STRIPE_SECRET_KEY")
    if not secret_key:
        raise RuntimeError("STRIPE_SECRET_KEY is required")

    mode = str(post.raw.get("stripe_mode") or env("STRIPE_MODE", "payment")).strip().lower()
    if mode not in {"payment", "subscription"}:
        raise RuntimeError("STRIPE_MODE must be payment or subscription")

    success_url = str(post.raw.get("stripe_success_url") or env("STRIPE_SUCCESS_URL")).strip()
    cancel_url = str(post.raw.get("stripe_cancel_url") or env("STRIPE_CANCEL_URL")).strip()

    if not success_url or not cancel_url:
        raise RuntimeError("STRIPE_SUCCESS_URL and STRIPE_CANCEL_URL are required")

    price_id = str(post.raw.get("stripe_price_id") or env("STRIPE_PRICE_ID")).strip()
    quantity = int(post.raw.get("stripe_quantity") or env("STRIPE_QUANTITY", "1"))

    if quantity < 1:
        raise RuntimeError("Stripe quantity must be >= 1")

    form = {
        "mode": mode,
        "success_url": success_url,
        "cancel_url": cancel_url,
        "client_reference_id": f"{env('STRIPE_CLIENT_REFERENCE_PREFIX', 'poster')}:{post.content_hash[:32]}",
        "metadata[source]": "multi_platform_poster",
        "metadata[campaign]": str(post.raw.get("campaign", ""))[:500],
        "metadata[line_number]": str(post.line_number),
        "metadata[content_hash]": post.content_hash,
        "metadata[title]": (post.title or "")[:500],
        "line_items[0][quantity]": str(quantity),
    }

    if price_id:
        form["line_items[0][price]"] = price_id
    else:
        unit_amount = int(post.raw.get("stripe_unit_amount") or env("STRIPE_UNIT_AMOUNT", "0"))
        currency = str(post.raw.get("stripe_currency") or env("STRIPE_CURRENCY", "usd")).strip().lower()
        product_name = str(
            post.raw.get("stripe_product_name")
            or env("STRIPE_PRODUCT_NAME", post.title or "Campaign checkout")
        ).strip()

        if unit_amount <= 0:
            raise RuntimeError("Set STRIPE_PRICE_ID or provide STRIPE_UNIT_AMOUNT in cents")
        if not currency:
            raise RuntimeError("STRIPE_CURRENCY is required when using STRIPE_UNIT_AMOUNT")

        form["line_items[0][price_data][currency]"] = currency
        form["line_items[0][price_data][unit_amount]"] = str(unit_amount)
        form["line_items[0][price_data][product_data][name]"] = product_name[:250]

    customer_email = str(post.raw.get("customer_email") or env("STRIPE_CUSTOMER_EMAIL")).strip()
    if customer_email:
        form["customer_email"] = customer_email

    if env_bool("STRIPE_ALLOW_PROMOTION_CODES", False):
        form["allow_promotion_codes"] = "true"

    billing_address_collection = env("STRIPE_BILLING_ADDRESS_COLLECTION", "")
    if billing_address_collection in {"auto", "required"}:
        form["billing_address_collection"] = billing_address_collection

    auth_raw = f"{secret_key}:".encode("utf-8")
    status, body = http_request(
        "POST",
        "https://api.stripe.com/v1/checkout/sessions",
        headers={
            "Authorization": "Basic " + base64.b64encode(auth_raw).decode("ascii"),
        },
        form_body=form,
        timeout=timeout,
    )

    response_id = None
    try:
        response_id = str(json.loads(body).get("id", "")) or None
    except json.JSONDecodeError:
        pass

    return status, body, response_id


POSTERS = {
    "telegram": post_telegram,
    "x": post_x,
    "reddit": post_reddit,
    "pinterest": post_pinterest,
    "tiktok": post_tiktok,
    "stripe": post_stripe,
}


def run_one(args: argparse.Namespace) -> int:
    posts = load_queue(Path(args.queue), args.max_chars, args.require_approval)

    if not posts:
        print("No approved queue items found.")
        return 0

    state_path = Path(args.state)
    log_path = Path(args.log)

    state = load_json(state_path, {
        "posted_platform_hashes": [],
        "last_post_ts_by_platform": {},
        "posted_count_by_platform": {},
        "response_ids": {},
    })

    platform_filter = set(validate_platforms(args.platforms.split(","))) if args.platforms else None

    pending = next_pending(
        posts,
        state,
        platform_filter,
        args.min_interval_seconds,
        args.optimal_times,
    )

    if pending is None:
        print("No eligible post/platform pair is ready.")
        append_jsonl(log_path, {"ts": now_ts(), "event": "no_eligible_post"})
        return 0

    post, platform = pending

    if args.dry_run or not args.live:
        print(f"DRY RUN: would post line {post.line_number} to {platform}")
        print(compose_text(post))
        append_jsonl(log_path, {
            "ts": now_ts(),
            "event": "dry_run",
            "platform": platform,
            "line_number": post.line_number,
            "hash": post.content_hash,
        })
        return 0

    try:
        status, body, response_id = POSTERS[platform](post, args.timeout_seconds)
        success = 200 <= status < 300
    except Exception as exc:
        status, body, response_id, success = 0, repr(exc), None, False

    append_jsonl(log_path, {
        "ts": now_ts(),
        "event": "post_attempt",
        "platform": platform,
        "success": success,
        "status_code": status,
        "line_number": post.line_number,
        "hash": post.content_hash,
        "response_id": response_id,
        "response_preview": body[:1000],
    })

    if not success:
        print(f"Post failed for {platform}: HTTP {status}: {body[:1000]}", file=sys.stderr)
        return 1

    save_json(state_path, mark_posted(state, platform, post, response_id))

    if platform == "stripe":
        try:
            checkout_url = json.loads(body).get("url")
        except json.JSONDecodeError:
            checkout_url = None

        print(f"Created Stripe Checkout Session for line {post.line_number}. HTTP {status}. id={response_id or 'n/a'}")
        if checkout_url:
            print(f"Stripe Checkout URL: {checkout_url}")
    else:
        print(f"Posted line {post.line_number} to {platform}. HTTP {status}. id={response_id or 'n/a'}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Official-API-only multi-platform poster with LLM drafts and Stripe Checkout.")

    parser.add_argument("--queue", default="posts.jsonl")
    parser.add_argument("--drafts", default="drafts.jsonl")
    parser.add_argument("--state", default=".poster_state.json")
    parser.add_argument("--log", default="poster_audit_log.jsonl")
    parser.add_argument("--platforms", default="")
    parser.add_argument("--min-interval-seconds", type=int, default=3600)
    parser.add_argument("--max-chars", type=int, default=2200)
    parser.add_argument("--timeout-seconds", type=int, default=30)
    parser.add_argument("--sleep-seconds", type=int, default=60)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--optimal-times", action="store_true")
    parser.add_argument("--require-approval", action="store_true", default=True)

    parser.add_argument("--generate", action="store_true")
    parser.add_argument("--topic", default="")
    parser.add_argument("--campaign", default="default")
    parser.add_argument("--ollama-url", default="http://localhost:11434/api/generate")
    parser.add_argument("--ollama-model", default="llama3.1")
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--num-predict", type=int, default=500)

    args = parser.parse_args()

    if args.generate:
        return generate_draft(args)

    if args.min_interval_seconds < 300:
        raise SystemExit("Refusing to run with interval below 300 seconds.")

    if args.once:
        return run_one(args)

    while True:
        code = run_one(args)
        if code != 0:
            return code
        time.sleep(args.sleep_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
