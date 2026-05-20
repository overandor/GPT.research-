#!/usr/bin/env python3
"""
MEMBRA PriceOS v0.2.1
Dry-Run + Verified-Data Appraisal Console

A single-file Hugging Face / Gradio prototype for appraising digital,
physical, and hybrid assets from KPI evidence.

Doctrine:
Price = verified KPIs + provenance + demand + liquidity + prediction - risk

This tool is not financial, legal, lending, tax, or investment advice.
It does not guarantee sale, profit, transferability, loan approval, or compliance.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import math
import os
import re
import statistics
from typing import Any, Dict, List, Optional

try:
    import gradio as gr
except Exception:  # pragma: no cover
    gr = None

try:
    import requests
except Exception:  # pragma: no cover
    requests = None

APP_NAME = "MEMBRA PriceOS"
APP_VERSION = "0.2.1"
DEFAULT_CURRENCY = "USD"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")

ACCOUNT_LIKE_TYPES = {
    "social_account", "marketplace_store", "amazon_store", "ebay_store",
    "instagram_account", "tiktok_account", "youtube_channel", "x_account",
    "app_store_account", "ad_account",
}

FORMAL_PERSONAS = [
    "Buyer Persona", "Seller Broker Persona", "Investor Persona", "Underwriter Persona",
    "Compliance Officer Persona", "Technical Auditor Persona", "Market Analyst Persona",
    "Brand Strategist Persona", "Risk Officer Persona",
]
BRAND_PERSONAS = FORMAL_PERSONAS + ["Lola Rottweiler Trust Sentinel"]

MULTIPLES = {
    "website": (18, 42, 4, 16),
    "marketplace_store": (12, 36, 3, 12),
    "github_repo": (0, 24, 0, 10),
    "social_account": (6, 24, 1, 8),
    "knowledge_asset": (6, 24, 1, 10),
    "prompt_workflow": (4, 20, 1, 8),
    "dataset": (6, 36, 1, 12),
    "ai_model": (6, 36, 1, 12),
    "real_estate_listing": (0, 0, 0, 0),
    "domain": (0, 0, 0, 0),
    "generic": (6, 24, 1, 8),
}


def now_iso() -> str:
    return _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def clamp(x: Any, low: float = 0.0, high: float = 1.0) -> float:
    try:
        return max(low, min(high, float(x)))
    except Exception:
        return low


def safe_float(x: Any, default: float = 0.0) -> float:
    """Parse $1.2k, 4M, 2.5 billion, 1,200 into floats."""
    if x is None:
        return default
    if isinstance(x, (int, float)):
        return float(x)
    if not isinstance(x, str):
        return default
    s = x.strip().lower().replace(",", "")
    mult = 1.0
    for suffix, value in [(" thousand", 1e3), (" million", 1e6), (" billion", 1e9)]:
        if s.endswith(suffix):
            s = s[: -len(suffix)]
            mult = value
            break
    if s.endswith("k"):
        s, mult = s[:-1], 1e3
    elif s.endswith("m"):
        s, mult = s[:-1], 1e6
    elif s.endswith("b"):
        s, mult = s[:-1], 1e9
    s = re.sub(r"[^0-9.\-]", "", s)
    if s in {"", ".", "-", "-."}:
        return default
    try:
        return float(s) * mult
    except Exception:
        return default


def money(x: Any, currency: str = DEFAULT_CURRENCY) -> str:
    x = safe_float(x)
    sign = "-" if x < 0 else ""
    x = abs(x)
    if x >= 1e9:
        return f"{sign}{currency} {x / 1e9:.2f}B"
    if x >= 1e6:
        return f"{sign}{currency} {x / 1e6:.2f}M"
    if x >= 1e3:
        return f"{sign}{currency} {x:,.0f}"
    return f"{sign}{currency} {x:,.2f}"


def stable_id(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def parse_json_maybe(text: str) -> Dict[str, Any]:
    if not text or not text.strip():
        return {}
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                obj = json.loads(m.group(0))
                return obj if isinstance(obj, dict) else {}
            except Exception:
                return {}
    return {}


def log_score(value: Any, scale: float) -> float:
    value = max(0.0, safe_float(value))
    return clamp(math.log1p(value) / math.log1p(max(scale, 1.0)))


def grade(score: float) -> str:
    score = clamp(score)
    if score >= 0.92:
        return "A++"
    if score >= 0.84:
        return "A"
    if score >= 0.72:
        return "B+"
    if score >= 0.60:
        return "B"
    if score >= 0.45:
        return "C"
    if score >= 0.30:
        return "D"
    return "X"


def detect_asset_type(text: str) -> str:
    t = text.lower()
    if any(x in t for x in ["github", "repo", "repository", "commit"]):
        return "github_repo"
    if any(x in t for x in ["instagram", "tiktok", "youtube channel", "x account", "twitter"]):
        return "social_account"
    if any(x in t for x in ["amazon", "fba", "ebay", "shopify", "storefront", "seller account"]):
        return "marketplace_store"
    if any(x in t for x in ["domain", ".com", ".ai", ".io", ".net", ".org"]):
        return "domain"
    if any(x in t for x in ["pdf", "book", "ebook", "course", "curriculum", "guide"]):
        return "knowledge_asset"
    if any(x in t for x in ["dataset", "data set", "training data", "corpus"]):
        return "dataset"
    if any(x in t for x in ["model", "llm", "agent", "fine-tune", "finetune"]):
        return "ai_model"
    if any(x in t for x in ["house", "property", "real estate", "bedroom", "zillow", "redfin"]):
        return "real_estate_listing"
    if any(x in t for x in ["website", "blog", "seo", "site", "newsletter"]):
        return "website"
    if any(x in t for x in ["prompt", "chatgpt workflow", "workflow"]):
        return "prompt_workflow"
    return "generic"


def find_money_after(text: str, words: List[str]) -> Optional[float]:
    low = text.lower()
    for w in words:
        pattern = rf"{re.escape(w)}[^0-9$]*(\$?\s?[0-9][0-9,]*(?:\.\d+)?\s?(?:k|m|b|thousand|million|billion)?)"
        m = re.search(pattern, low)
        if m:
            return safe_float(m.group(1))
    return None


def llm_extract(text: str) -> Dict[str, Any]:
    """Optional LLM extractor; heuristic fallback keeps the app self-contained."""
    prompt = f"""
Return only valid JSON. Extract explicit asset appraisal fields from this text.
Do not invent verified facts. If unknown use null.
Schema: asset_name, asset_type, category, description_summary, revenue_monthly,
profit_monthly, asking_price, traffic_monthly, followers, engagement_rate,
age_months, offers_count, watchers_count, conversion_rate, refund_rate,
verified_revenue, verified_traffic, verified_ownership, transferability,
legal_risk, platform_risk, fraud_risk, privacy_risk, technical_quality,
documentation_quality, brand_strength, scarcity, utility, buyer_demand,
semantic_density, transformation_potential, monetization_paths, risk_flags,
missing_proof, estimated_fields.

ASSET TEXT:\n{text}
""".strip()
    raw = None
    if OPENAI_API_KEY and requests:
        try:
            r = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={"model": OPENAI_MODEL, "temperature": 0.1, "messages": [{"role": "user", "content": prompt}]},
                timeout=60,
            )
            if r.status_code < 400:
                raw = r.json()["choices"][0]["message"]["content"]
        except Exception:
            raw = None
    if raw is None and OLLAMA_BASE_URL and requests:
        try:
            r = requests.post(
                OLLAMA_BASE_URL.rstrip("/") + "/api/generate",
                json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False, "options": {"temperature": 0.1}},
                timeout=90,
            )
            if r.status_code < 400:
                raw = r.json().get("response")
        except Exception:
            raw = None
    parsed = parse_json_maybe(raw or "")
    return normalize_features(parsed) if parsed else heuristic_extract(text)


def heuristic_extract(text: str) -> Dict[str, Any]:
    low = text.lower()
    asset_type = detect_asset_type(text)
    risk_flags = []
    missing_proof = []
    if any(x in low for x in ["private", "leaked", "credential", "password", "stolen"]):
        risk_flags.append("Possible private, leaked, credential, stolen, or non-transferable material.")
    if any(x in low for x in ["screenshot only", "no proof", "trust me"]):
        risk_flags.append("Weak proof: screenshots or claims alone are not lender-grade evidence.")
    if asset_type in ACCOUNT_LIKE_TYPES:
        risk_flags.append("Platform-transferability warning: account-based assets may be restricted by platform terms.")
        missing_proof.append("Document platform ToS transferability.")
    return normalize_features({
        "asset_name": None,
        "asset_type": asset_type,
        "category": asset_type,
        "description_summary": text[:700],
        "revenue_monthly": find_money_after(text, ["revenue", "sales", "mrr", "monthly revenue"]),
        "profit_monthly": find_money_after(text, ["profit", "net", "cashflow", "cash flow"]),
        "asking_price": find_money_after(text, ["asking", "listed for", "ask price", "price"]),
        "traffic_monthly": _extract_count(text, ["visitors", "visits", "sessions", "pageviews", "page views", "views"]),
        "followers": _extract_count(text, ["followers", "subs", "subscribers"]),
        "engagement_rate": None,
        "age_months": None,
        "offers_count": None,
        "watchers_count": None,
        "conversion_rate": None,
        "refund_rate": None,
        "verified_revenue": "verified revenue" in low or "stripe" in low,
        "verified_traffic": "verified traffic" in low or "ga4" in low or "google analytics" in low,
        "verified_ownership": "verified ownership" in low or "proof of ownership" in low,
        "transferability": 0.45 if asset_type in ACCOUNT_LIKE_TYPES else 0.55,
        "legal_risk": 0.35 if risk_flags else 0.25,
        "platform_risk": 0.55 if asset_type in ACCOUNT_LIKE_TYPES else 0.30,
        "fraud_risk": 0.45 if risk_flags else 0.25,
        "privacy_risk": 0.70 if any(x in low for x in ["private", "leaked", "credential", "password"]) else 0.20,
        "technical_quality": 0.50,
        "documentation_quality": 0.50,
        "brand_strength": 0.50,
        "scarcity": 0.50,
        "utility": 0.50,
        "buyer_demand": 0.50,
        "semantic_density": 0.50,
        "transformation_potential": 0.50,
        "monetization_paths": [],
        "risk_flags": risk_flags,
        "missing_proof": missing_proof,
        "estimated_fields": {},
    })


def _extract_count(text: str, labels: List[str]) -> Optional[float]:
    low = text.lower()
    for label in labels:
        m = re.search(rf"([0-9][0-9,]*(?:\.\d+)?\s?(?:k|m|b|thousand|million|billion)?)\s*{re.escape(label)}", low)
        if m:
            return safe_float(m.group(1))
    return None


def normalize_features(data: Dict[str, Any]) -> Dict[str, Any]:
    defaults = {
        "asset_name": None, "asset_type": "generic", "category": "generic", "description_summary": None,
        "revenue_monthly": None, "profit_monthly": None, "asking_price": None, "traffic_monthly": None,
        "followers": None, "engagement_rate": None, "age_months": None, "offers_count": None,
        "watchers_count": None, "conversion_rate": None, "refund_rate": None,
        "verified_revenue": False, "verified_traffic": False, "verified_ownership": False,
        "transferability": 0.50, "legal_risk": 0.25, "platform_risk": 0.25, "fraud_risk": 0.25, "privacy_risk": 0.25,
        "technical_quality": 0.50, "documentation_quality": 0.50, "brand_strength": 0.50, "scarcity": 0.50,
        "utility": 0.50, "buyer_demand": 0.50, "semantic_density": 0.50, "transformation_potential": 0.50,
        "monetization_paths": [], "risk_flags": [], "missing_proof": [], "estimated_fields": {},
    }
    out = {**defaults, **(data or {})}
    for k in ["revenue_monthly", "profit_monthly", "asking_price", "traffic_monthly", "followers", "engagement_rate", "age_months", "offers_count", "watchers_count", "conversion_rate", "refund_rate"]:
        out[k] = None if out[k] is None else safe_float(out[k])
    for k in ["transferability", "legal_risk", "platform_risk", "fraud_risk", "privacy_risk", "technical_quality", "documentation_quality", "brand_strength", "scarcity", "utility", "buyer_demand", "semantic_density", "transformation_potential"]:
        out[k] = clamp(out[k])
    for k in ["verified_revenue", "verified_traffic", "verified_ownership"]:
        out[k] = bool(out[k])
    for k in ["monetization_paths", "risk_flags", "missing_proof"]:
        out[k] = out[k] if isinstance(out[k], list) else []
    out["estimated_fields"] = out["estimated_fields"] if isinstance(out["estimated_fields"], dict) else {}
    out["asset_type"] = str(out.get("asset_type") or "generic").strip().lower().replace(" ", "_")
    out["category"] = out.get("category") or out["asset_type"]
    return out


def merge_external(features: Dict[str, Any], external: Dict[str, Any]) -> Dict[str, Any]:
    f = dict(features)
    rev = external.get("revenue", {}) if isinstance(external.get("revenue", {}), dict) else {}
    if rev.get("monthly") is not None:
        f["revenue_monthly"] = safe_float(rev.get("monthly"))
    if rev.get("profit") is not None:
        f["profit_monthly"] = safe_float(rev.get("profit"))
    if rev.get("verified") is not None:
        f["verified_revenue"] = bool(rev.get("verified"))
    traffic = external.get("traffic", {}) if isinstance(external.get("traffic", {}), dict) else {}
    if traffic.get("verified_monthly_visitors") is not None:
        f["traffic_monthly"] = safe_float(traffic.get("verified_monthly_visitors")); f["verified_traffic"] = True
    elif traffic.get("monthly_visitors") is not None:
        f["traffic_monthly"] = safe_float(traffic.get("monthly_visitors"))
    market = external.get("market", {}) if isinstance(external.get("market", {}), dict) else {}
    for k in ["offers_count", "watchers_count"]:
        if market.get(k) is not None:
            f[k] = safe_float(market.get(k))
    own = external.get("ownership", {}) if isinstance(external.get("ownership", {}), dict) else {}
    if own.get("verified") is not None:
        f["verified_ownership"] = bool(own.get("verified"))
    return normalize_features(f)


def comp_stats(comps: Any) -> Dict[str, Any]:
    prices = []
    for c in comps if isinstance(comps, list) else []:
        p = safe_float(c.get("price") or c.get("sale_price") or c.get("sold_price")) if isinstance(c, dict) else safe_float(c)
        if p > 0:
            prices.append(p)
    if not prices:
        return {"count": 0, "median": None, "mean": None, "low": None, "high": None, "confidence": 0.0}
    prices.sort()
    return {"count": len(prices), "median": statistics.median(prices), "mean": statistics.mean(prices), "low": prices[0], "high": prices[-1], "confidence": clamp(len(prices) / 10)}


def aggregate_risk(f: Dict[str, Any]) -> float:
    risks = [safe_float(f.get(k), 0.25) for k in ["legal_risk", "platform_risk", "fraud_risk", "privacy_risk"]]
    return clamp(0.70 * statistics.mean(risks) + 0.30 * max(risks))


def trust_score(f: Dict[str, Any]) -> float:
    risk = aggregate_risk(f)
    return clamp(
        (0.25 if f.get("verified_ownership") else 0) +
        (0.25 if f.get("verified_revenue") else 0) +
        (0.20 if f.get("verified_traffic") else 0) +
        0.15 * clamp(f.get("transferability", 0.5)) +
        0.15 * (1 - risk)
    )


def compute_kpis(f: Dict[str, Any], comps: Dict[str, Any]) -> Dict[str, float]:
    risk, trust = aggregate_risk(f), trust_score(f)
    demand = clamp(0.30 * safe_float(f.get("buyer_demand"), 0.5) + 0.20 * log_score(f.get("offers_count"), 20) + 0.20 * log_score(f.get("watchers_count"), 200) + 0.15 * log_score(f.get("traffic_monthly"), 100000) + 0.15 * log_score(f.get("followers"), 100000))
    revenue = clamp(0.65 * log_score(f.get("revenue_monthly"), 100000) + 0.35 * log_score(f.get("profit_monthly"), 50000))
    traffic = clamp(0.70 * log_score(f.get("traffic_monthly"), 500000) + 0.30 * log_score(f.get("followers"), 500000))
    quality = clamp(0.25 * safe_float(f.get("technical_quality"), 0.5) + 0.25 * safe_float(f.get("documentation_quality"), 0.5) + 0.20 * safe_float(f.get("utility"), 0.5) + 0.15 * safe_float(f.get("semantic_density"), 0.5) + 0.15 * safe_float(f.get("brand_strength"), 0.5))
    transfer = clamp(f.get("transferability", 0.5))
    liquidity = clamp(0.28 * demand + 0.22 * trust + 0.16 * transfer + 0.14 * safe_float(comps.get("confidence")) + 0.10 * revenue + 0.10 * (1 - risk))
    return {"revenue_score": revenue, "traffic_score": traffic, "demand_score": demand, "trust_score": trust, "risk_score": risk, "quality_score": quality, "scarcity_score": clamp(f.get("scarcity", 0.5)), "brand_score": clamp(f.get("brand_strength", 0.5)), "transformation_score": clamp(f.get("transformation_potential", 0.5)), "transferability_score": transfer, "comps_confidence": clamp(comps.get("confidence", 0)), "age_score": log_score(f.get("age_months"), 120), "liquidity_score": liquidity}


def price_model(f: Dict[str, Any], k: Dict[str, float], comps: Dict[str, Any]) -> Dict[str, Any]:
    pm_low, pm_high, rm_low, rm_high = MULTIPLES.get(f.get("asset_type", "generic"), MULTIPLES["generic"])
    q = clamp(0.20 + 0.25 * k["quality_score"] + 0.20 * k["trust_score"] + 0.20 * k["demand_score"] + 0.15 * (1 - k["risk_score"]))
    profit_value = safe_float(f.get("profit_monthly")) * (pm_low + q * (pm_high - pm_low))
    revenue_value = safe_float(f.get("revenue_monthly")) * (rm_low + q * (rm_high - rm_low))
    traffic_value = safe_float(f.get("traffic_monthly")) * (0.04 + 0.30 * k["demand_score"] + 0.20 * k["quality_score"])
    engagement = safe_float(f.get("engagement_rate"), 0.02); engagement = engagement / 100 if engagement > 1 else engagement
    audience_value = safe_float(f.get("followers")) * clamp(engagement, 0.005, 0.20) * (1 + 4 * k["brand_score"])
    scarcity_floor = 250 * (1 + 25 * k["scarcity_score"] * k["brand_score"])
    semantic_floor = 200 * (1 + 20 * k["quality_score"] * k["transformation_score"])
    asking = safe_float(f.get("asking_price")); comp_value = safe_float(comps.get("median"))
    if f.get("asset_type") == "real_estate_listing":
        candidates = [x for x in [asking, comp_value] if x > 0]
    else:
        candidates = [x for x in [profit_value, revenue_value, traffic_value, audience_value, scarcity_floor, semantic_floor, comp_value, asking * 0.85 if asking > 0 else 0] if x > 0]
    base = statistics.median(candidates) * 0.70 + max(candidates) * 0.30 if candidates else 500 * (1 + 10 * k["quality_score"] + 8 * k["transformation_score"] + 5 * k["brand_score"])
    price_gap = (asking - base) / max(base, 1) if asking > 0 else 0
    over = clamp(max(0, price_gap) / 2); under = clamp(max(0, -price_gap) / 2)
    p90 = clamp(0.20 + 0.25 * k["liquidity_score"] + 0.18 * k["demand_score"] + 0.18 * k["trust_score"] + 0.10 * k["quality_score"] + 0.08 * under - 0.22 * k["risk_score"] - 0.18 * over)
    latent = base * (0.10 + 0.60 * k["transformation_score"]) * (0.30 + 0.70 * k["quality_score"])
    ts = clamp(0.20 + 0.50 * k["trust_score"] + 0.30 * k["quality_score"])
    fair = base * (1 - 0.55 * k["risk_score"]) * (0.70 + 0.30 * k["trust_score"]) * (0.70 + 0.30 * k["liquidity_score"]) + latent * ts * 0.25
    floor = fair * (0.45 + 0.25 * k["liquidity_score"]) * (1 - 0.35 * k["risk_score"])
    ceiling = fair * (1.20 + 1.20 * k["scarcity_score"] + 0.80 * k["transformation_score"])
    conf = clamp(0.20 + 0.22 * k["trust_score"] + 0.20 * k["comps_confidence"] + 0.18 * (1 - k["risk_score"]) + 0.10 * k["liquidity_score"] + 0.10 * (1 if safe_float(f.get("revenue_monthly")) > 0 else 0))
    collateral = fair * p90 * k["trust_score"] * (1 - k["risk_score"])
    advance = clamp(0.15 + 0.35 * k["trust_score"] + 0.20 * k["liquidity_score"] - 0.30 * k["risk_score"], 0.05, 0.55)
    finance_ready = bool(f.get("verified_ownership")) and k["trust_score"] >= 0.65 and k["risk_score"] <= 0.45 and (bool(f.get("verified_revenue")) or bool(f.get("verified_traffic")) or safe_float(f.get("profit_monthly")) > 0)
    loan = collateral * advance if finance_ready else 0.0
    if not finance_ready:
        collateral *= 0.25; advance = min(advance, 0.05)
    return {
        "base_value": round(base, 2), "fair_value": round(max(0, fair), 2), "floor_value": round(max(0, floor), 2), "ceiling_value": round(max(fair, ceiling), 2),
        "expected_sale_price_90d": round(max(0, fair * (0.90 + 0.20 * p90)), 2), "collateral_value": round(max(0, collateral), 2), "loan_estimate": round(max(0, loan), 2),
        "suggested_advance_rate": round(advance, 3), "latent_transformation_value": round(latent, 2), "transformation_success_probability": round(ts, 3), "confidence": round(conf, 3),
        "finance_ready": finance_ready, "finance_gating_reason": "Eligible for indicative financing analysis." if finance_ready else "Not finance-ready: requires verified ownership, stronger trust score, lower risk, and verified revenue/traffic or profit evidence.",
        "grade": grade(conf * (1 - k["risk_score"]) * (0.5 + 0.5 * k["liquidity_score"])),
        "prediction": {"sale_probability_30d": round(p90 * 0.45, 4), "sale_probability_60d": round(p90 * 0.72, 4), "sale_probability_90d": round(p90, 4), "sale_probability_180d": round(clamp(0.15 + p90 * 0.90), 4), "price_gap_ratio": round(price_gap, 4), "overpricing_penalty": round(over, 4)},
        "base_value_components": {"profit_value": round(profit_value, 2), "revenue_value": round(revenue_value, 2), "traffic_value": round(traffic_value, 2), "audience_value": round(audience_value, 2), "scarcity_floor": round(scarcity_floor, 2), "semantic_floor": round(semantic_floor, 2), "comps_value": round(comp_value, 2), "asking_anchor": round(asking, 2)},
    }


def panelos(f: Dict[str, Any], k: Dict[str, float], p: Dict[str, Any], style: str) -> Dict[str, Any]:
    personas = BRAND_PERSONAS if style == "brand" else FORMAL_PERSONAS
    fair = safe_float(p["fair_value"]); rows = []
    for persona in personas:
        bias = {"Buyer Persona": -0.10, "Seller Broker Persona": 0.12, "Investor Persona": -0.02, "Underwriter Persona": -0.20, "Compliance Officer Persona": -0.25 if k["risk_score"] > 0.45 else -0.05, "Technical Auditor Persona": -0.08 if k["quality_score"] < 0.55 else 0.05, "Market Analyst Persona": 0.00, "Brand Strategist Persona": 0.12 if k["brand_score"] > 0.65 else 0.00, "Risk Officer Persona": -0.25 * k["risk_score"], "Lola Rottweiler Trust Sentinel": -0.30 if k["trust_score"] < 0.45 else 0.03}.get(persona, 0)
        pfair = fair * (1 + bias)
        objections = []
        if k["trust_score"] < 0.55: objections.append("Needs stronger proof.")
        if k["risk_score"] > 0.45: objections.append("Risk justifies discount or compliance review.")
        if k["liquidity_score"] < 0.50: objections.append("Liquidity is weak; improve buyer targeting.")
        if f.get("asset_type") in ACCOUNT_LIKE_TYPES: objections.append("Verify platform transferability.")
        rows.append({"persona": persona, "low_price": round(pfair * 0.75, 2), "fair_price": round(pfair, 2), "high_price": round(pfair * 1.35, 2), "confidence": round(clamp(0.35 + 0.35 * k["trust_score"] + 0.20 * k["liquidity_score"] - 0.20 * k["risk_score"]), 3), "objections": objections or ["No fatal objection if evidence remains verifiable."]})
    consensus = sum(r["fair_price"] * r["confidence"] for r in rows) / max(sum(r["confidence"] for r in rows), 1e-9)
    return {"panel_style": style, "personas": rows, "consensus_price": round(consensus, 2), "disagreement_ratio": round(statistics.pstdev([r["fair_price"] for r in rows]) / max(consensus, 1), 3)}


def bullet(items: List[str], fallback: str) -> str:
    return "\n".join(f"- {x}" for x in (items or [fallback]))


def appraise_asset(asset_text: str, external_json: str = "", panel_style: str = "brand") -> Dict[str, Any]:
    if not asset_text.strip():
        return {"error": "No asset description provided."}
    external = parse_json_maybe(external_json)
    mode = "verified_connector_mode" if external else "manual_dry_run_mode"
    mode_notice = "Verified Connector Mode: structured external data was supplied. Final confidence still depends on source authenticity." if external else "Manual / Dry-Run Mode: based on user-supplied text and model extraction. Use verified API connectors for lender-grade pricing."
    features = merge_external(llm_extract(asset_text), external)
    if features["asset_type"] in ACCOUNT_LIKE_TYPES and "Document platform ToS transferability." not in features["missing_proof"]:
        features["missing_proof"].append("Document platform ToS transferability.")
        features["platform_risk"] = max(features["platform_risk"], 0.55)
        features["transferability"] = min(features["transferability"], 0.45)
    comps = comp_stats(external.get("comps", []))
    kpis = compute_kpis(features, comps)
    price = price_model(features, kpis, comps)
    panel = panelos(features, kpis, price, panel_style)
    toxic_text = (" ".join(features.get("risk_flags", [])) + " " + asset_text).lower()
    toxic = kpis["risk_score"] >= 0.85 or any(x in toxic_text for x in ["stolen", "credential", "leaked private", "password"])
    if toxic:
        price["grade"] = "X"; price["loan_estimate"] = 0.0; price["finance_ready"] = False; price["finance_gating_reason"] = "Blocked or toxic-risk asset. Do not list, finance, or trade without compliance review."
    positives, objections, actions = [], [], []
    (positives if kpis["trust_score"] >= 0.65 else objections).append("Strong proof layer increases appraisal confidence." if kpis["trust_score"] >= 0.65 else "Proof layer is incomplete; stronger attestations would raise confidence.")
    (positives if kpis["demand_score"] >= 0.60 else objections).append("Demand signals support liquidity." if kpis["demand_score"] >= 0.60 else "Demand signals are moderate or weak.")
    if safe_float(features.get("profit_monthly")) > 0: positives.append("Monthly profit supports income-based valuation.")
    elif safe_float(features.get("revenue_monthly")) > 0: positives.append("Monthly revenue supports revenue-based valuation.")
    else: objections.append("No verified revenue was provided; valuation relies on utility, traffic, comps, brand, and latent value.")
    (objections if kpis["risk_score"] >= 0.45 else positives).append("Risk score creates a material valuation discount." if kpis["risk_score"] >= 0.45 else "Risk level does not dominate the appraisal.")
    if not features.get("verified_ownership"): actions.append("Add ownership attestation.")
    if safe_float(features.get("revenue_monthly")) > 0 and not features.get("verified_revenue"): actions.append("Connect revenue proof such as Stripe, Shopify, Amazon SP-API, eBay reports, or accounting export.")
    if safe_float(features.get("traffic_monthly")) > 0 and not features.get("verified_traffic"): actions.append("Connect traffic proof such as GA4, Search Console, Cloudflare, Plausible, Fathom, or server logs.")
    if features.get("asset_type") in ACCOUNT_LIKE_TYPES: actions.append("Document platform ToS transferability before sale or financing.")
    justification = f"""
MEMBRA Price Justification

Mode:\n{mode_notice}

Asset type:\n{features.get('asset_type')}

Grade:\n{price['grade']}

Fair value:\n{money(price['fair_value'])}

Expected 90-day sale price:\n{money(price['expected_sale_price_90d'])}

90-day sale probability:\n{price['prediction']['sale_probability_90d']:.1%}

Collateral value estimate:\n{money(price['collateral_value'])}

Indicative loan estimate:\n{money(price['loan_estimate'])}

Finance status:\n{price['finance_gating_reason']}

Why this price is supported:\n{bullet(positives, 'Value is present but requires stronger proof.')}

Price discounts / objections:\n{bullet(objections, 'No major discount driver detected from supplied data.')}

PanelOS consensus:\n- Consensus price: {money(panel['consensus_price'])}\n- Disagreement ratio: {panel['disagreement_ratio']:.1%}

Recommended next actions:\n{bullet(actions, 'List with verified proof package and monitor offers.')}
""".strip()
    if toxic:
        justification += "\n\nBLOCK NOTICE: Asset may be toxic, stolen, credential-related, private, or non-transferable. Do not list, finance, or trade without compliance review."
    return {
        "membra_report_id": stable_id({"asset_text": asset_text, "external": external}),
        "generated_at": now_iso(), "app_name": APP_NAME, "app_version": APP_VERSION,
        "mode": mode, "mode_notice": mode_notice, "asset_features": features, "comps_summary": comps,
        "kpis": {x: round(y, 4) for x, y in kpis.items()}, "base_value_components": price.pop("base_value_components"),
        "prediction": price.pop("prediction"), "price": price, "panelos": panel, "justification": justification,
        "connector_schema_example": {"revenue": {"monthly": 1200, "profit": 800, "verified": True, "source": "stripe", "period": "trailing_30_days"}, "traffic": {"verified_monthly_visitors": 8000, "source": "ga4", "bot_ratio": 0.08}, "ownership": {"verified": True, "method": "oauth_or_dns_or_repo_token"}, "comps": [{"price": 22000, "sold": True, "source": "marketplace_or_manual", "date": "2026-05-01"}]},
        "disclaimer": "Model-based appraisal only. Not financial, legal, tax, lending, investment, or trading advice. No profit is guaranteed.",
    }


def appraise_to_json(asset_text: str, external_json: str = "", panel_style: str = "brand") -> str:
    return json.dumps(appraise_asset(asset_text, external_json, panel_style), indent=2, ensure_ascii=False)


def appraise_to_markdown(asset_text: str, external_json: str = "", panel_style: str = "brand") -> str:
    r = appraise_asset(asset_text, external_json, panel_style)
    if "error" in r: return r["error"]
    p, pred, k = r["price"], r["prediction"], r["kpis"]
    md = f"""
# MEMBRA Appraisal Report

**Report ID:** `{r['membra_report_id']}`  
**Generated:** {r['generated_at']}  
**Mode:** `{r['mode']}`  
**Asset Type:** `{r['asset_features'].get('asset_type')}`  
**Grade:** **{p['grade']}**

> {r['mode_notice']}

## PriceOS

| Metric | Value |
|---|---:|
| Fair Value | {money(p['fair_value'])} |
| Floor Value | {money(p['floor_value'])} |
| Ceiling Value | {money(p['ceiling_value'])} |
| Expected 90-Day Sale Price | {money(p['expected_sale_price_90d'])} |
| Collateral Value | {money(p['collateral_value'])} |
| Indicative Loan Estimate | {money(p['loan_estimate'])} |
| Finance Ready | {p['finance_ready']} |
| Confidence | {p['confidence']:.1%} |

## PredictionOS

| Metric | Value |
|---|---:|
| Sale Probability 30d | {pred['sale_probability_30d']:.1%} |
| Sale Probability 60d | {pred['sale_probability_60d']:.1%} |
| Sale Probability 90d | {pred['sale_probability_90d']:.1%} |
| Sale Probability 180d | {pred['sale_probability_180d']:.1%} |

## KPI Scores

| KPI | Score |
|---|---:|
| Revenue | {k['revenue_score']:.2f} |
| Traffic | {k['traffic_score']:.2f} |
| Demand | {k['demand_score']:.2f} |
| Trust | {k['trust_score']:.2f} |
| Risk | {k['risk_score']:.2f} |
| Quality | {k['quality_score']:.2f} |
| Liquidity | {k['liquidity_score']:.2f} |
| Transformation | {k['transformation_score']:.2f} |

## Justification

{r['justification']}

## PanelOS Personas
""".strip()
    for row in r["panelos"]["personas"]:
        md += f"\n\n### {row['persona']}\n- Low: {money(row['low_price'])}\n- Fair: {money(row['fair_price'])}\n- High: {money(row['high_price'])}\n- Confidence: {row['confidence']:.1%}\n- Objections: {' '.join(row['objections'])}"
    md += f"\n\n## Disclaimer\n\n{r['disclaimer']}\n"
    return md


EXAMPLE_ASSET = """
Asset: AI workflow GitHub repo that turns PDFs into structured research briefs.
Current revenue: $1.2k/month from consulting clients.
Profit: $800/month.
Traffic: 8k monthly visitors from SEO.
Asking price: $24k.
Has documentation, demo video, MIT license, and verified ownership.
Revenue is verified through Stripe. Traffic is verified through GA4.
Risks: depends on OpenAI API, needs better onboarding, no enterprise contracts yet.
"""

EXAMPLE_EXTERNAL = json.dumps({
    "comps": [{"price": 18000, "sold": True}, {"price": 22000, "sold": True}, {"price": 27500, "sold": True}],
    "revenue": {"monthly": 1200, "profit": 800, "verified": True, "source": "stripe", "period": "trailing_30_days"},
    "traffic": {"verified_monthly_visitors": 8000, "source": "ga4", "bot_ratio": 0.08},
    "market": {"offers_count": 2, "watchers_count": 18},
    "ownership": {"verified": True, "method": "repo_token"},
}, indent=2)


def launch_gradio() -> None:
    if gr is None:
        raise RuntimeError("Install Gradio with: pip install gradio")
    with gr.Blocks(title=f"{APP_NAME} v{APP_VERSION}") as demo:
        gr.Markdown(f"# {APP_NAME} v{APP_VERSION}\n\n**Dry-Run + Verified-Data Appraisal Console**\n\nThis is not a guarantee of sale, profit, loan approval, or transferability.")
        with gr.Row():
            asset_text = gr.Textbox(label="Asset Description", value=EXAMPLE_ASSET, lines=15)
            external_json = gr.Textbox(label="Optional Verified Data / Comps JSON", value=EXAMPLE_EXTERNAL, lines=15)
        panel_style = gr.Dropdown(choices=["institutional", "brand"], value="brand", label="Panel Style")
        with gr.Row():
            run_md = gr.Button("Generate MEMBRA Report")
            run_json = gr.Button("Generate Raw JSON")
        out_md = gr.Markdown(label="Report")
        out_json = gr.Code(label="JSON", language="json")
        run_md.click(appraise_to_markdown, inputs=[asset_text, external_json, panel_style], outputs=out_md)
        run_json.click(appraise_to_json, inputs=[asset_text, external_json, panel_style], outputs=out_json)
        gr.Markdown("""
## ConnectorOS Roadmap
Connect → Sync → Reconcile → Extract KPI → Benchmark → Price → Predict → Justify

Recommended connector targets: Stripe, GA4, Search Console, Cloudflare, GitHub, RDAP, YouTube, Instagram, TikTok, X, Shopify, Amazon SP-API, eBay, Solana, Etherscan, CoinGecko, The Graph.
""")
    demo.launch()


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="MEMBRA PriceOS appraisal engine")
    parser.add_argument("--asset", default="")
    parser.add_argument("--asset-file", default="")
    parser.add_argument("--external-json", default="")
    parser.add_argument("--external-file", default="")
    parser.add_argument("--panel-style", choices=["brand", "institutional"], default="brand")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--serve", action="store_true")
    args = parser.parse_args()
    if args.serve:
        launch_gradio(); return
    asset = args.asset or (open(args.asset_file, encoding="utf-8").read() if args.asset_file else EXAMPLE_ASSET)
    external = args.external_json or (open(args.external_file, encoding="utf-8").read() if args.external_file else EXAMPLE_EXTERNAL)
    print(appraise_to_json(asset, external, args.panel_style) if args.json else appraise_to_markdown(asset, external, args.panel_style))


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 1 and gr is not None:
        launch_gradio()
    else:
        main()
