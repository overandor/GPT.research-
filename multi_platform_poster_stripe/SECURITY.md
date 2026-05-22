# Security Model

This package touches public posting APIs and Stripe Checkout Session creation. Treat it as a production-adjacent revenue workflow, not a toy script.

## Hard boundaries

- The script does not collect or process card data.
- Stripe payments must use hosted Checkout Sessions.
- Access fulfillment must be triggered only after a verified Stripe webhook event.
- Generated LLM drafts must remain `approved=false` until human review.
- Live execution requires `--live`; otherwise the poster runs as a dry run.
- API credentials must stay in environment variables, local secret stores, CI secrets, or platform secrets.

## Secret handling

Never commit these values:

- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `TELEGRAM_BOT_TOKEN`
- `X_BEARER_TOKEN`
- `REDDIT_CLIENT_SECRET`
- `REDDIT_PASSWORD`
- `PINTEREST_ACCESS_TOKEN`
- `TIKTOK_ACCESS_TOKEN`

If a secret is exposed in chat, GitHub, logs, screenshots, or a public paste, revoke and rotate it immediately.

## Stripe safety

Use test mode first. A Stripe Checkout Session proves that the payment page was created, not that money settled or access should be granted. Grant access only after receiving and verifying a webhook event such as `checkout.session.completed` with acceptable `payment_status`, `mode`, customer identity, metadata, and product/price policy.

The provided `stripe_webhook.py` verifies Stripe's signature and logs verified events. It deliberately does not grant access automatically.

## Posting safety

Use platform-specific official APIs only. Do not add scraping, credential stuffing, browser automation, CAPTCHA bypassing, or unauthorized account actions.

Before enabling `--live`:

1. Review every JSONL queue line.
2. Confirm `approved=true` only appears on approved content.
3. Run a dry run without `--live`.
4. Confirm the selected `--platforms` filter.
5. Confirm `--min-interval-seconds` is not below the platform's acceptable cadence.

## Marketing compliance

Avoid claims that imply guaranteed profit, investment advice, fake scarcity, medical/legal/financial certainty, impersonation, or platform endorsement. The Ollama prompt already asks for compliant copy, but human review is the real control.

## Audit logs

The script writes `poster_audit_log.jsonl` by default. Keep this file if you need an operational audit trail. Consider redacting API response previews before sharing logs externally.

## Recommended production upgrades

- Replace local JSON state with a transactional database if multiple runners will operate at once.
- Add a hosted dashboard for queue review and approval.
- Add CI tests for queue validation, Stripe form building, and webhook signature verification.
- Add structured logging and alerting for failed post attempts.
- Add webhook idempotency storage so duplicate Stripe webhook deliveries do not double-grant access.
