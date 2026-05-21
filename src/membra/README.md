# MEMBRA / overandor Source Artifacts

This directory contains executable source-code artifacts supporting the MEMBRA / `overandor` appraisal package.

The purpose of this layer is to provide technical substance behind the valuation dossier. Markdown files explain the institutional appraisal; these source files demonstrate deterministic implementation patterns in Python, Rust, and C++.

## Files

| File | Language | Purpose |
|---|---|---|
| `overandor_control_plane.py` | Python | Orchestration layer, review-gate evaluation, and audit-event generation |
| `overandor_invariants.rs` | Rust | Typed invariant/checking core with unit tests |
| `overandor_engine.cpp` | C++ | Low-level deterministic review engine and JSON-style audit output |
| `tests/test_overandor_control_plane.py` | Python | Unit tests for Python control-plane behavior |
| `Cargo.toml` | Rust metadata | Cargo metadata for Rust test/build execution |
| `CMakeLists.txt` | C++ metadata | CMake metadata for C++ build execution |

## Safety Boundary

These artifacts are neutral diligence files. They do not:

- hold private keys;
- submit transactions;
- construct trading strategies;
- target third parties;
- access wallets;
- require external network calls.

They model control-plane review logic and audit events only.

## Run Python Demo

From repository root:

```bash
python src/membra/overandor_control_plane.py
```

## Run Python Tests

```bash
python -m unittest src.membra.tests.test_overandor_control_plane
```

## Run Rust Tests

From `src/membra`:

```bash
cargo test
```

Alternative direct command:

```bash
rustc --test overandor_invariants.rs -o /tmp/overandor_invariants_test
/tmp/overandor_invariants_test
```

## Build C++ Engine

From `src/membra`:

```bash
cmake -S . -B build
cmake --build build
./build/overandor_engine
```

Alternative direct command:

```bash
g++ -std=c++17 overandor_engine.cpp -o /tmp/overandor_engine
/tmp/overandor_engine
```

## Valuation Role

These files support the executable-source portion of the appraisal package.

```text
Executable source code = technical substance
Markdown dossier = valuation narrative
Tests/build files = verification bridge
```

The appraisal becomes stronger when these artifacts are verified by build logs, test output, CI runs, third-party review, or buyer diligence.
