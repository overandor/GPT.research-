# overandor Control Gate Map Template

This file maps `overandor` control-plane checks to evidence required for institutional valuation. It is a neutral audit template for documenting safeguards, review points, and operational controls.

| Gate ID | Control Gate | Risk Class Reduced | Source Path | Test Path | Evidence Artifact | Dollar Basis | Verification Status |
|---|---|---|---|---|---|---:|---|
| CG-001 | Exposure Boundary Check | Oversized allocation / scope overrun | TBD | TBD | TBD | notional exposure protected | Pending |
| CG-002 | Price Tolerance Check | Unfavorable execution condition | TBD | TBD | TBD | tolerance breach avoided | Pending |
| CG-003 | Liquidity Sufficiency Check | Insufficient depth / execution quality risk | TBD | TBD | TBD | liquidity-adjusted exposure | Pending |
| CG-004 | Duplicate Action Check | Repeated action / replay condition | TBD | TBD | TBD | duplicate notional avoided | Pending |
| CG-005 | Fee Boundary Check | Excessive operating cost | TBD | TBD | TBD | cost above cap avoided | Pending |
| CG-006 | System Halt / Circuit Control | Cascading operational failure | TBD | TBD | TBD | exposure protected during halt | Pending |
| CG-007 | Authorization Boundary Check | Unauthorized path / control breach | TBD | TBD | TBD | protected wallet or account exposure | Pending |
| CG-008 | Data Freshness Check | Stale signal / stale quote | TBD | TBD | TBD | stale-data exposure avoided | Pending |
| CG-009 | Pre-Execution Review Check | Untested action path | TBD | TBD | TBD | reviewed notional exposure | Pending |
| CG-010 | Audit Log Integrity Check | Missing or unverifiable audit trail | TBD | TBD | TBD | compliance premium basis | Pending |

## Required Evidence Per Gate

For each control gate, attach or reference:

1. source file path;
2. test file path;
3. configuration file, if applicable;
4. log event name;
5. sample event payload;
6. timestamped evidence artifact;
7. estimated value protected;
8. reviewer initials or verification status.

## Valuation Use

The dollar value of each gate should be calculated conservatively:

```text
Gate Value =
  Exposure Protected
× Preventable Failure Probability
× Gate Effectiveness
× Annualization Factor
```

The sum of verified gate values supports the `overandor` capital-preservation and insurance-premium appraisal layer.
