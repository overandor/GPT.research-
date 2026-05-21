# MEMBRA Executable Source Code Price Ledger

**Purpose:** Separate executable software artifacts from Markdown dossier artifacts. The appraisal package should include `.py`, `.rs`, and `.cpp` files because code, tests, demos, and runtime behavior carry more technical value than narrative documentation alone.

**Important:** These are appraised contribution values, not guaranteed cash prices. A buyer or auditor should verify that each source file builds, runs, and maps to the stated control-plane or product function.

---

## Source Artifact Summary

| File | Language | Status | Role | Appraised Contribution |
|---|---|---|---|---:|
| `src/membra/overandor_control_plane.py` | Python | Attached | Orchestration layer, deterministic review gates, audit-event generation | $85,000 |
| `src/membra/overandor_invariants.rs` | Rust | Attached | Typed invariant core and unit-testable control logic | $125,000 |
| `src/membra/overandor_engine.cpp` | C++ | Attached | Low-level deterministic control engine / systems proof artifact | $110,000 |
| `bundle_senderos.py` | Python | Attached | Safe pre-signed bundle relay harness for Jito / Flashbots workflows | $65,000 |
| `mempool_connectoros.py` | Python | Pending | Read-only endpoint registry and pending-observation collector | $85,000 |
| `app.py` | Python | Pending / external | Main PriceOS / Language.fi / Gradio app surface | $120,000 |

**Executable source subtotal:** **$590,000**

---

## Why Executable Files Matter

Markdown files explain the valuation, but executable files prove implementation depth.

The source-code layer supports the valuation through:

1. deterministic control logic;
2. audit-event generation;
3. typed invariant checks;
4. cross-language implementation depth;
5. buyer diligence artifacts;
6. future test and CI integration;
7. transferability into a real software package.

---

## Language Allocation

| Language | Files | Valuation Role | Appraised Subtotal |
|---|---:|---|---:|
| Python | 3 attached/pending | App orchestration, buyer-facing tools, connector workflows | $355,000 |
| Rust | 1 attached | Typed safety / invariant kernel | $125,000 |
| C++ | 1 attached | Low-level deterministic systems component | $110,000 |

---

## Attached Source Files

### 1. `src/membra/overandor_control_plane.py` — $85,000

Role:

- Python orchestration artifact;
- deterministic review-gate evaluation;
- audit-event generation;
- JSON-ready data structures;
- buyer/auditor demo surface.

Verification needed:

```bash
python src/membra/overandor_control_plane.py
```

---

### 2. `src/membra/overandor_invariants.rs` — $125,000

Role:

- Rust invariant artifact;
- strong typed structures;
- gate evaluation functions;
- unit tests for pass/stop behavior;
- institutional-grade systems-language evidence.

Verification needed:

```bash
rustc --test src/membra/overandor_invariants.rs -o /tmp/overandor_invariants_test
/tmp/overandor_invariants_test
```

---

### 3. `src/membra/overandor_engine.cpp` — $110,000

Role:

- C++ systems artifact;
- deterministic review engine;
- audit-event JSON output;
- low-level implementation evidence;
- portable buyer diligence artifact.

Verification needed:

```bash
g++ -std=c++17 src/membra/overandor_engine.cpp -o /tmp/overandor_engine
/tmp/overandor_engine
```

---

### 4. `bundle_senderos.py` — $65,000

Role:

- safe pre-signed bundle submission harness;
- dry-run default;
- Jito and Flashbots relay compatibility;
- no private-key generation, no trade construction, no strategy automation.

Verification needed:

```bash
python bundle_senderos.py --help
```

---

## Pending High-Value Source Files

### `app.py` — $120,000

Needed as the main deployed app surface.

Expected role:

- Language.fi / MEMBRA public demo;
- PriceOS / appraisal UI;
- buyer-facing proof surface;
- Gradio or web UI deployment target.

### `mempool_connectoros.py` — $85,000

Needed as read-only monitoring and endpoint registry.

Expected role:

- public endpoint catalog;
- REST probe layer;
- WebSocket subscription layer;
- normalized observation output;
- proof-ledger integration.

---

## Revised $1,000,000 Appraisal Split

| Category | Appraised Contribution |
|---|---:|
| Executable source code artifacts | $590,000 |
| Institutional Markdown dossier | $250,000 |
| Evidence / repo metrics / security / transfer files | $120,000 |
| Market listing / buyer validation files | $40,000 |

**Total target valuation:** **$1,000,000**

---

## Current Source Evidence Status

| File | Status | Verification Level |
|---|---|---|
| `src/membra/overandor_control_plane.py` | Attached | Level 2: source artifact |
| `src/membra/overandor_invariants.rs` | Attached | Level 2: source artifact |
| `src/membra/overandor_engine.cpp` | Attached | Level 2: source artifact |
| `bundle_senderos.py` | Attached | Level 2: source artifact |
| `app.py` | Pending | Level 0: not attached in this branch |
| `mempool_connectoros.py` | Pending | Level 0: not attached in this branch |

To reach stronger valuation support, each attached source file should be advanced to Level 3 by adding test results, build logs, and CI output.

---

## Next Files Required

```text
src/membra/tests/test_overandor_control_plane.py
src/membra/Cargo.toml
src/membra/CMakeLists.txt
src/membra/README.md
app.py
mempool_connectoros.py
```

These files would make the code layer feel more like a real software package rather than isolated artifacts.

---

## Diligence Rule

A buyer should be shown both layers:

```text
Executable source code = technical substance
Markdown dossier = valuation narrative and institutional framing
Evidence logs/tests = verification bridge
```

The $1,000,000 target becomes more defensible when all three layers are present.
