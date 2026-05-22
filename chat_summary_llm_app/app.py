#!/usr/bin/env python3
"""
chat_summary_llm_app/app.py

One-file LLM app that summarizes the working chat into a production/readiness brief.

Default backend: local Ollama
Optional backend: OpenAI-compatible chat completions endpoint

Run:
  streamlit run app.py

Environment:
  LLM_BACKEND=ollama | openai_compatible
  OLLAMA_URL=http://localhost:11434/api/generate
  OLLAMA_MODEL=llama3.1
  OPENAI_COMPATIBLE_URL=https://api.openai.com/v1/chat/completions
  OPENAI_COMPATIBLE_API_KEY=...
  OPENAI_COMPATIBLE_MODEL=gpt-4o-mini
"""

from __future__ import annotations

import json
import os
import textwrap
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

try:
    import streamlit as st
except Exception as exc:  # pragma: no cover
    raise SystemExit("Install streamlit first: pip install streamlit") from exc


CHAT_FACTS = """
1. The user shared a deployed Replit URL: https://stripe-checkout-gateway--antichrist062.replit.app.
2. Public inspection showed a web app title: Membra. Initial text extraction was sparse.
3. Screenshots later revealed the app is MEMBRA — Perpetual Futures Engine.
4. Visible modules included Dashboard, Scanner, History, Memory, Diagnostics, Settings, and Pricing.
5. The app appeared to scan Gate.io perpetual futures, run LLM directional analysis, store predictions, evaluate outcomes, and run a machine-memory/reflection cycle.
6. The visible app explicitly presented itself as research-only and not as live trade execution.
7. Visible metrics included weak current prediction performance: roughly 38.7% global hit rate, 27.3% high-confidence hit rate, and about -0.07% average return.
8. The app was appraised as a working prototype/research dashboard with an estimated as-is midpoint around $18,000, but not guaranteed market value.
9. The ROI discussion clarified that with a zero-dollar cash cost, ROI percentage is mathematically undefined because ROI divides by cost basis; the accurate framing is high unrealized ROI.
10. A GitHub repository search found relevant repositories under overandor, including overandor/membra, overandor/membramoney, and overandor/GPT.research-.
11. overandor/membra was identified as a broader MEMBRA proof-of-job / Solana / validator protocol repository.
12. overandor/membramoney contained a Hugging Face style README for an LLM 15-Minute Signal Hunter using Gate.io futures, Jupiter DEX, Solana data, and LLM predictions.
13. The user pasted a Streamlit Zenodo Research Submission Dashboard for creating Zenodo drafts, uploading PDFs, saving metadata, and publishing DOI records.
14. A production-ready Zenodo dashboard was committed into overandor/GPT.research- under zenodo_submission_dashboard/app.py.
15. Additional Zenodo dashboard files were committed: requirements.txt, Dockerfile, README.md, and .streamlit/config.toml.
16. The user then pasted a Python multi_platform_poster.py script for official-API-only posting across Telegram, X, Reddit, Pinterest, and TikTok with Ollama draft generation, human approval, dry-run default, JSONL queues, dedupe, and audit logs.
17. Stripe Checkout support was designed and added as a new platform named stripe.
18. A Stripe-enabled one-file app was committed into overandor/GPT.research- under multi_platform_poster_stripe/app.py.
19. The Stripe integration creates hosted Checkout Sessions and does not handle card data.
20. The Stripe extension uses STRIPE_SECRET_KEY, STRIPE_PRICE_ID or price_data, success/cancel URLs, metadata, client_reference_id, optional customer email, promotion codes, and billing address settings.
21. The repo was further productized with multi_platform_poster_stripe/README.md, .env.example, posts.example.jsonl, stripe_webhook.py, and SECURITY.md.
22. The Stripe webhook verifier uses standard-library HMAC verification for Stripe-Signature and logs verified events to JSONL without automatically granting access.
23. The final product direction emerging from the chat is a MEMBRA-aligned research, monetization, publishing, and distribution toolkit: research dashboard, Zenodo DOI submission, Stripe checkout, and multi-platform campaign distribution.
""".strip()


DEFAULT_EXECUTIVE_SUMMARY = """
This chat transformed MEMBRA from a visible Replit prototype into a more defensible product asset. The original app was identified as a research-only perpetual futures engine with scanner, prediction history, diagnostics, memory/reflection loops, and pricing surface. Its visible performance metrics were not strong enough to justify valuation as a proven trading edge, but the workflow, UI, data loop, and commercialization shell supported an as-is prototype appraisal around the low-to-mid five figures, with $18,000 used as a fair midpoint under assumptions of working code and clean implementation.

The build work then moved into GitHub. A production-ready Zenodo submission dashboard was added to overandor/GPT.research-, giving the repo a research-publication pathway for manuscripts and DOI creation. A multi-platform poster was extended into a monetization/distribution engine by adding Stripe Checkout as a new platform. The Stripe implementation creates hosted Checkout Sessions rather than handling card data. The package was then hardened with documentation, environment templates, JSONL queue examples, a webhook verifier, and a security model.

The repo's value is now broader than one app. It has three productizable lanes: MEMBRA research/analytics, research publishing via Zenodo, and monetized campaign distribution through Stripe plus official social APIs. The strongest next step is to connect these into a single operator dashboard with authentication, queue review, webhook-based fulfillment, audit trails, and a clear research-only compliance boundary.
""".strip()


PROMPT_TEMPLATE = """
You are a strict productization analyst. Summarize the chat facts into a concise but high-value production brief.

Output format:
1. Executive Summary
2. What Was Built
3. Repository Value Added
4. Monetization Path
5. Risk Boundaries
6. Next Production Steps
7. One-Sentence Appraisal

Rules:
- Be concrete.
- Do not claim proven trading profitability.
- Do not claim realized ROI unless money was actually received.
- Mention Stripe hosted Checkout and webhook verification.
- Mention Zenodo DOI workflow.
- Mention MEMBRA research dashboard and machine-memory loop.
- Keep it useful for an investor, buyer, or technical operator.

Chat facts:
{chat_facts}
""".strip()


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def http_json(method: str, url: str, payload: dict[str, Any], headers: dict[str, str] | None = None, timeout: int = 120) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body[:1000]}") from exc


def summarize_with_ollama(prompt: str, model: str, url: str, temperature: float) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": 1400,
        },
    }
    result = http_json("POST", url, payload)
    return str(result.get("response", "")).strip()


def summarize_with_openai_compatible(prompt: str, model: str, url: str, api_key: str, temperature: float) -> str:
    if not api_key:
        raise RuntimeError("OPENAI_COMPATIBLE_API_KEY is required for openai_compatible backend")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You produce concise, accurate production briefs."},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
    }
    result = http_json(
        "POST",
        url,
        payload,
        headers={"Authorization": f"Bearer {api_key}"},
    )
    return str(result.get("choices", [{}])[0].get("message", {}).get("content", "")).strip()


def run_llm_summary(chat_facts: str, backend: str, temperature: float) -> str:
    prompt = PROMPT_TEMPLATE.format(chat_facts=chat_facts)
    if backend == "ollama":
        return summarize_with_ollama(
            prompt,
            model=env("OLLAMA_MODEL", "llama3.1"),
            url=env("OLLAMA_URL", "http://localhost:11434/api/generate"),
            temperature=temperature,
        )
    if backend == "openai_compatible":
        return summarize_with_openai_compatible(
            prompt,
            model=env("OPENAI_COMPATIBLE_MODEL", "gpt-4o-mini"),
            url=env("OPENAI_COMPATIBLE_URL", "https://api.openai.com/v1/chat/completions"),
            api_key=env("OPENAI_COMPATIBLE_API_KEY"),
            temperature=temperature,
        )
    raise RuntimeError(f"Unsupported backend: {backend}")


def build_artifact(summary: str, facts: str) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "app": "MEMBRA Chat Summary LLM App",
        "summary": summary,
        "facts": [line.strip() for line in facts.splitlines() if line.strip()],
        "production_boundary": {
            "trading_profit_proven": False,
            "roi_realized": False,
            "stripe_handles_card_data": False,
            "requires_webhook_for_fulfillment": True,
            "research_only_boundary": True,
        },
    }


def main() -> None:
    st.set_page_config(
        page_title="MEMBRA Chat Summary LLM",
        page_icon="🧠",
        layout="wide",
    )

    st.title("MEMBRA Chat Summary LLM")
    st.caption("One-file app.py that turns this chat into a productization, appraisal, and production-readiness brief.")

    with st.sidebar:
        st.header("LLM Backend")
        backend = st.selectbox(
            "Backend",
            ["ollama", "openai_compatible"],
            index=0 if env("LLM_BACKEND", "ollama") == "ollama" else 1,
        )
        temperature = st.slider("Temperature", min_value=0.0, max_value=1.0, value=0.2, step=0.05)
        st.divider()
        st.write("Ollama")
        st.code(f"{env('OLLAMA_MODEL', 'llama3.1')} @ {env('OLLAMA_URL', 'http://localhost:11434/api/generate')}")
        st.write("OpenAI-compatible")
        st.code(f"{env('OPENAI_COMPATIBLE_MODEL', 'gpt-4o-mini')} @ {env('OPENAI_COMPATIBLE_URL', 'https://api.openai.com/v1/chat/completions')}")

    tab_summary, tab_facts, tab_json, tab_prompt = st.tabs(["Summary", "Chat Facts", "Export JSON", "Prompt"])

    with tab_summary:
        st.subheader("Default deterministic summary")
        st.write(DEFAULT_EXECUTIVE_SUMMARY)

        st.subheader("LLM-generated production brief")
        if st.button("Generate with LLM", use_container_width=True):
            with st.spinner("Generating production brief..."):
                try:
                    llm_summary = run_llm_summary(CHAT_FACTS, backend, temperature)
                    st.session_state["llm_summary"] = llm_summary
                except Exception as exc:
                    st.error(f"LLM generation failed: {exc}")

        if "llm_summary" in st.session_state:
            st.markdown(st.session_state["llm_summary"])
        else:
            st.info("Click Generate with LLM to create the formatted production brief. The deterministic summary above is always available.")

    with tab_facts:
        st.subheader("Grounded chat facts")
        st.text_area("Facts used by the LLM", value=CHAT_FACTS, height=520)

    with tab_json:
        active_summary = st.session_state.get("llm_summary", DEFAULT_EXECUTIVE_SUMMARY)
        artifact = build_artifact(active_summary, CHAT_FACTS)
        st.json(artifact)
        st.download_button(
            "Download summary JSON",
            data=json.dumps(artifact, indent=2),
            file_name="membra_chat_summary.json",
            mime="application/json",
            use_container_width=True,
        )

    with tab_prompt:
        st.subheader("LLM prompt")
        st.text_area(
            "Prompt template",
            value=PROMPT_TEMPLATE.format(chat_facts=CHAT_FACTS),
            height=520,
        )

    st.divider()
    st.caption(
        "Boundary: this app summarizes product work. It does not prove trading profitability, realized ROI, or payment settlement. "
        "Stripe fulfillment should depend on verified webhook events, not Checkout Session creation alone."
    )


if __name__ == "__main__":
    main()
