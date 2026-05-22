# Multi-Platform Poster + Stripe Checkout

Official-API-only marketing and monetization runner. It can generate draft posts with a local Ollama model, require human approval, post through official platform APIs, and create hosted Stripe Checkout Sessions from the same JSONL queue.

## Value proposition

This folder turns a single script into a deployable campaign engine:

- Social distribution: Telegram, X, Reddit, Pinterest, and TikTok through official APIs.
- Monetization: Stripe Checkout Session generation without handling card data.
- Human control: drafts are not live until `approved=true` and `--live` is provided.
- Risk control: dry-run behavior is the default.
- Auditability: every dry run and live attempt writes to JSONL audit logs.
- Dedupe: per-platform content hashes prevent accidental reposting.
- Local AI: Ollama can generate drafts without sending prompts to a hosted LLM.

## Files

| File | Purpose |
| --- | --- |
| `app.py` | Main CLI runner for draft generation, posting, and Stripe Checkout Session creation. |
| `stripe_webhook.py` | Minimal Stripe webhook verifier and event logger for fulfillment handoff. |
| `posts.example.jsonl` | Safe queue examples for Stripe and social posting. |
| `.env.example` | Required environment variable template. |
| `SECURITY.md` | Operational safety model for secrets, posting, and payment handling. |

## Install

The main poster uses only the Python standard library.

```bash
python --version
python multi_platform_poster_stripe/app.py --help
```

Ollama draft generation requires a running Ollama server. Live posting requires each platform's own official API credentials.

## Stripe quick start

Create a Stripe Price in your Stripe dashboard, then export credentials:

```bash
export STRIPE_SECRET_KEY="sk_test_..."
export STRIPE_PRICE_ID="price_..."
export STRIPE_MODE="payment"
export STRIPE_SUCCESS_URL="https://yourdomain.com/success?session_id={CHECKOUT_SESSION_ID}"
export STRIPE_CANCEL_URL="https://yourdomain.com/cancel"
```

Dry run first:

```bash
python multi_platform_poster_stripe/app.py \
  --queue multi_platform_poster_stripe/posts.example.jsonl \
  --platforms stripe \
  --once
```

Create a real Checkout Session:

```bash
python multi_platform_poster_stripe/app.py \
  --queue multi_platform_poster_stripe/posts.example.jsonl \
  --platforms stripe \
  --once \
  --live
```

The live command prints the Stripe Checkout URL and records the Checkout Session ID in `.poster_state.json`.

## Queue format

Each line in the queue is one JSON object. Set `approved=true` only after review.

```json
{"title":"MEMBRA Access","text":"Support the research release and unlock access.","url":"","media_url":"","platforms":["stripe"],"campaign":"membra","approved":true}
```

Optional Stripe-specific fields may be set per queue item:

```json
{"title":"MEMBRA Monthly","text":"Subscribe for monthly access.","platforms":["stripe"],"campaign":"membra","approved":true,"stripe_mode":"subscription","stripe_price_id":"price_...","stripe_quantity":1,"customer_email":"buyer@example.com"}
```

If `stripe_price_id` is omitted, the script can create ad hoc `price_data` using `stripe_unit_amount`, `stripe_currency`, and `stripe_product_name`.

## Ollama draft generation

```bash
python multi_platform_poster_stripe/app.py \
  --generate \
  --topic "MEMBRA research dashboard launch" \
  --campaign membra \
  --platforms telegram,x,stripe \
  --drafts drafts.jsonl
```

The generated line is written with `approved=false`. Review the text, then manually set `approved=true` before live use.

## Webhook handoff

Checkout Session creation is not fulfillment. Use `stripe_webhook.py` to verify Stripe signatures and log events before granting access.

```bash
export STRIPE_WEBHOOK_SECRET="whsec_..."
python multi_platform_poster_stripe/stripe_webhook.py
```

Default endpoint:

```text
POST http://0.0.0.0:8080/webhook
```

The webhook server writes verified events to `stripe_webhook_events.jsonl`. Use that log or extend the handler to grant access, send emails, or unlock subscriptions.

## Production checklist

1. Use Stripe test mode until the full queue, payment, webhook, and fulfillment path is verified.
2. Store API keys in environment variables or a secret manager, never in JSONL queue files.
3. Keep `approved=false` for generated drafts until a human review is complete.
4. Run without `--live` before every new campaign.
5. Use a dedicated webhook endpoint with `STRIPE_WEBHOOK_SECRET` before granting access.
6. Keep `.poster_state.json` and audit logs backed up if they are part of your compliance record.
7. Do not make guaranteed income, investment, or profit claims in generated campaign copy.
