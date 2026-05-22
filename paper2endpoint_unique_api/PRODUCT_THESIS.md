# Paper2Endpoint Product Thesis

## Core claim

Paper2Endpoint is not a paper summarizer and not a PDF chatbot.

**Paper2Endpoint turns every research paper into a deployable API surface that computes what the paper specifies.**

Every serious paper contains latent software: formulas, algorithms, assumptions, variables, validation examples, datasets, and decision procedures. Paper2Endpoint extracts that latent software, formalizes it, validates it, and exposes it as endpoints.

## Operating doctrine

```text
Research paper enters
  -> computable specification is extracted
  -> unique paper-scoped endpoints are generated
  -> validation examples are attached
  -> OpenAPI contract is emitted
  -> compute capsule is versioned
  -> DOI/proof can be published
  -> hosted demo can be deployed
  -> Stripe can sell access
  -> official social APIs can distribute the release
```

The system does not claim that every paper is correct. It claims that it computes what the paper specifies, with provenance, assumptions, limitations, and validation tests.

## Unique endpoint rule

Each paper must own a unique endpoint namespace.

```text
One paper -> one deterministic paper_id -> many unique compute endpoints
```

Canonical route pattern:

```text
POST /api/v1/papers/{paper_id}/compute/{endpoint_slug}
```

Two papers may both define a `score` endpoint, but they cannot collide because the paper ID is part of the URL.

```text
/api/v1/papers/bearinglessfull-collateral-a1b2c3d4e5f6/compute/score
/api/v1/papers/another-paper-9031bd4120aa/compute/score
```

The URL itself preserves provenance.

## Endpoint pack

A strong paper endpoint pack should expose:

```text
GET  /api/v1/papers/{paper_id}
GET  /api/v1/papers/{paper_id}/spec
GET  /api/v1/papers/{paper_id}/variables
GET  /api/v1/papers/{paper_id}/formulas
GET  /api/v1/papers/{paper_id}/assumptions
POST /api/v1/papers/{paper_id}/compute/{function_name}
POST /api/v1/papers/{paper_id}/validate
GET  /api/v1/papers/{paper_id}/examples
GET  /api/v1/papers/{paper_id}/openapi.json
GET  /api/v1/papers/{paper_id}/citation
GET  /api/v1/papers/{paper_id}/provenance
POST /api/v1/papers/{paper_id}/benchmark
POST /api/v1/papers/{paper_id}/export
```

## Compute capsule contents

Each paper becomes a versioned compute capsule containing:

- `paper.json` — title, authors, DOI, citation, source hash, version, provenance.
- `schema.json` — typed inputs and outputs.
- `formulas.json` — formulas, algorithms, and variable definitions.
- `assumptions.json` — scope, limitations, units, and constraints.
- `examples.json` — examples from the paper or operator-approved test cases.
- `openapi.json` — machine-readable API contract.
- `app.py` — runnable FastAPI or Streamlit implementation.
- `Dockerfile` — deployable runtime.
- `README.md` — human operator instructions.

## Bearinglessfull Collateral example

The Bearinglessfull Collateral paper can become a compute capsule with endpoints such as:

```text
POST /api/v1/papers/{paper_id}/compute/bearinglessfull-score
POST /api/v1/papers/{paper_id}/compute/liquidation-distance
POST /api/v1/papers/{paper_id}/compute/reserve-buffer-ratio
POST /api/v1/papers/{paper_id}/compute/venue-distribution-risk
POST /api/v1/papers/{paper_id}/compute/rebalance-readiness
POST /api/v1/papers/{paper_id}/compute/access-risk
POST /api/v1/papers/{paper_id}/validate/collateral-topology
GET  /api/v1/papers/{paper_id}/spec
GET  /api/v1/papers/{paper_id}/openapi.json
```

## Why this is valuable

Researchers understand citations and provenance.

Developers understand endpoints and OpenAPI contracts.

Buyers understand hosted APIs.

Investors understand the platform claim: unstructured research becomes executable infrastructure.

## Repo-level product bridge

The existing repo modules now align into one product pipeline:

1. `paper2endpoint_unique_api` — converts paper manifests into unique computable endpoints.
2. `zenodo_submission_dashboard` — publishes the research object and DOI path.
3. `multi_platform_poster_stripe` — sells access through Stripe Checkout and distributes campaigns through official social APIs.
4. `chat_summary_llm_app` — creates productization briefs and investor/operator summaries.

Together, the repo becomes a research-to-endpoint-to-revenue system.

## Appraisal thesis

- Current repo with added modules: **$28k-$65k**.
- With a working Paper2Endpoint MVP: **$75k-$180k**.
- With 10 validated paper endpoint packs and hosted demos: **$150k-$400k**.
- With paying API users or institutional pilots: **$500k+**, depending on revenue, retention, usage, and compliance posture.

These are appraised product-value ranges, not guaranteed sale prices or realized revenue.

## Next production move

Add one canonical compiler app that accepts a paper PDF or Markdown file, proposes a manifest, requires human approval, generates a unique endpoint pack, emits OpenAPI, saves a versioned compute capsule, and optionally deploys it.

The MVP must include a hard approval gate. The LLM may propose formulas and schemas, but a human or trusted reviewer must approve the computable specification before endpoints are published.
