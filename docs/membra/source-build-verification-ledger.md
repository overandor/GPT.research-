# Source Build Verification Ledger

This ledger tracks whether the `.py`, `.rs`, and `.cpp` source artifacts are merely attached, locally verified, CI verified, buyer reviewed, or transaction-backed.

## Verification Levels

| Level | Meaning |
|---|---|
| Level 0 | Planned but not attached |
| Level 1 | Attached source file |
| Level 2 | Has build/test instructions |
| Level 3 | Build/test output captured |
| Level 4 | Reviewed by buyer, auditor, or third party |
| Level 5 | Supported an offer, LOI, escrow, or closed transaction |

## Current Source Verification

| Artifact | Language | Build/Test Command | Current Level | Appraised Contribution | Next Evidence Needed |
|---|---|---|---:|---:|---|
| `src/membra/overandor_control_plane.py` | Python | `python src/membra/overandor_control_plane.py` | 2 | $85,000 | captured run output |
| `src/membra/tests/test_overandor_control_plane.py` | Python | `python -m unittest src.membra.tests.test_overandor_control_plane` | 2 | included in Python value | captured test output |
| `src/membra/overandor_invariants.rs` | Rust | `cargo test` from `src/membra` | 2 | $125,000 | captured cargo test output |
| `src/membra/overandor_engine.cpp` | C++ | `cmake -S . -B build && cmake --build build` from `src/membra` | 2 | $110,000 | captured CMake/build output |
| `bundle_senderos.py` | Python | `python bundle_senderos.py --help` | 2 | $65,000 | captured help/dry-run output |
| `app.py` | Python | TBD | 0 | $120,000 | attach source file |
| `mempool_connectoros.py` | Python | TBD | 0 | $85,000 | attach source file |

## Buyer-Diligence Interpretation

A source file at Level 1 or Level 2 supports technical substance but remains unverified. A source file at Level 3 becomes stronger because test/build output exists. Level 4 or Level 5 evidence is needed for institutional confidence.

## Next Capture Targets

```bash
python src/membra/overandor_control_plane.py > docs/membra/evidence/python-control-plane-demo-output.json
python -m unittest src.membra.tests.test_overandor_control_plane > docs/membra/evidence/python-unit-test-output.txt
cd src/membra && cargo test > ../../docs/membra/evidence/rust-cargo-test-output.txt
cd src/membra && cmake -S . -B build && cmake --build build > ../../docs/membra/evidence/cpp-cmake-build-output.txt
```

Do not mark Level 3 until output files are actually captured and attached.
