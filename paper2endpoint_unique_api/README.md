# Paper2Endpoint Unique API

Research papers must not share generic compute URLs. Every paper gets a deterministic `paper_id`, and every computable formula or algorithm becomes a unique paper-scoped endpoint.

## Core rule

```text
One paper → one deterministic paper_id → many unique compute endpoints
```

Endpoint pattern:

```text
POST /api/v1/papers/{paper_id}/compute/{endpoint_slug}
```

Because `paper_id` is derived from the paper slug plus manifest hash, two different papers cannot accidentally own the same compute URL. Even if two papers define an endpoint named `score`, their paths remain unique.

## Why this matters

Generic endpoints such as `/compute/score` destroy provenance. Paper2Endpoint preserves provenance at the URL level:

```text
/api/v1/papers/bearinglessfull-collateral-a1b2c3d4e5f6/compute/bearinglessfull-score
/api/v1/papers/another-paper-9031bd4120aa/compute/score
```

Both can compute a score, but the URL itself declares which paper specification owns the computation.

## Run

```bash
cd paper2endpoint_unique_api
pip install fastapi uvicorn
PAPER_MANIFEST_DIR=paper_manifests uvicorn app:app --host 0.0.0.0 --port 7860
```

Open:

```text
http://localhost:7860/docs
```

## List papers

```bash
curl http://localhost:7860/api/v1/papers
```

## Inspect one paper's spec

```bash
curl http://localhost:7860/api/v1/papers/{paper_id}/spec
```

## Compute a paper endpoint

```bash
curl -X POST http://localhost:7860/api/v1/papers/{paper_id}/compute/bearinglessfull-score \
  -H 'Content-Type: application/json' \
  -d '{
    "venue_distribution": 0.80,
    "liquidation_distance": 0.70,
    "reserve_buffer": 0.90,
    "rebalance_readiness": 0.60,
    "access_resilience": 0.75
  }'
```

## Manifest format

Each paper is one JSON manifest in `paper_manifests/*.json`.

```json
{
  "title": "Paper Title",
  "paper_slug": "paper-title",
  "version": "0.1",
  "doi": null,
  "citation": "Author. Paper Title. Working paper.",
  "source_hash": "sha256_of_pdf_or_manuscript",
  "endpoints": [
    {
      "slug": "my-formula",
      "name": "My Formula",
      "description": "What the endpoint computes.",
      "formula": "x + y",
      "output_unit": "number",
      "citation": "Section 2, Equation 1",
      "assumptions": ["Inputs are numeric."],
      "variables": [
        {"name": "x", "type": "number", "description": "First input."},
        {"name": "y", "type": "number", "description": "Second input."}
      ]
    }
  ]
}
```

## Safety boundary

This runtime computes only the formulas supplied in the manifest. It does not claim the paper is correct, profitable, safe, peer-reviewed, or validated. It computes what the operator says the paper specifies, preserves provenance, and exposes assumptions and citations in the response.

## Supported formulas

The formula runtime supports numeric arithmetic and allowlisted math functions only. It intentionally rejects arbitrary Python execution.

Allowed functions:

```text
abs, min, max, round, sqrt, log, log10, exp, sin, cos, tan, floor, ceil
```

## Production upgrades

- Add a PDF/Markdown extractor that proposes manifests but requires human approval.
- Add tests per endpoint from paper examples.
- Add manifest signing and source PDF hashing.
- Add persistent registry storage instead of local JSON files.
- Add auth and per-paper API keys.
- Add a billing layer that maps paper endpoint packs to Stripe products.
- Add Zenodo DOI linkage after endpoint pack validation.
