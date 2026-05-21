#!/usr/bin/env python3
"""
overandor_control_plane.py

Executable MEMBRA / overandor control-plane artifact.

This module provides deterministic review gates and audit events for appraisal,
buyer diligence, and internal testing. It is intentionally neutral: it does not
hold private keys, submit network messages, or perform market strategy logic.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
from typing import Any, Callable, Dict, List, Optional
import json


class GateStatus(str, Enum):
    PASS = "pass"
    REVIEW = "review"
    STOP = "stop"


@dataclass(frozen=True)
class ReviewRequest:
    request_id: str
    asset_name: str
    value_usd: float
    max_value_usd: float
    tolerance_bps: float
    max_tolerance_bps: float
    data_age_seconds: float
    max_data_age_seconds: float
    duplicate_key_seen: bool = False
    review_passed: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class GateResult:
    gate_id: str
    gate_name: str
    status: GateStatus
    reason: str
    value_under_review_usd: float = 0.0


@dataclass(frozen=True)
class AuditEvent:
    schema: str
    created_at: str
    request_id: str
    asset_name: str
    aggregate_status: GateStatus
    results: List[Dict[str, Any]]
    event_hash: str


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def stable_hash(payload: Dict[str, Any]) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(body.encode("utf-8")).hexdigest()


def value_boundary_gate(req: ReviewRequest) -> GateResult:
    if req.value_usd > req.max_value_usd:
        return GateResult("CG-001", "Value Boundary Check", GateStatus.STOP, "Value exceeds configured boundary.", req.value_usd)
    return GateResult("CG-001", "Value Boundary Check", GateStatus.PASS, "Value is inside configured boundary.")


def tolerance_gate(req: ReviewRequest) -> GateResult:
    if req.tolerance_bps > req.max_tolerance_bps:
        return GateResult("CG-002", "Tolerance Check", GateStatus.REVIEW, "Tolerance exceeds configured threshold.", req.value_usd)
    return GateResult("CG-002", "Tolerance Check", GateStatus.PASS, "Tolerance is acceptable.")


def freshness_gate(req: ReviewRequest) -> GateResult:
    if req.data_age_seconds > req.max_data_age_seconds:
        return GateResult("CG-003", "Freshness Check", GateStatus.REVIEW, "Input data is stale.", req.value_usd)
    return GateResult("CG-003", "Freshness Check", GateStatus.PASS, "Input data is fresh.")


def duplicate_gate(req: ReviewRequest) -> GateResult:
    if req.duplicate_key_seen:
        return GateResult("CG-004", "Duplicate Check", GateStatus.STOP, "Duplicate request key observed.", req.value_usd)
    return GateResult("CG-004", "Duplicate Check", GateStatus.PASS, "No duplicate request key observed.")


def review_gate(req: ReviewRequest) -> GateResult:
    if req.review_passed is False:
        return GateResult("CG-005", "Review Check", GateStatus.STOP, "Required review failed.", req.value_usd)
    if req.review_passed is None:
        return GateResult("CG-005", "Review Check", GateStatus.REVIEW, "Required review evidence missing.", req.value_usd)
    return GateResult("CG-005", "Review Check", GateStatus.PASS, "Required review passed.")


class OverandorControlPlane:
    def __init__(self) -> None:
        self.gates: List[Callable[[ReviewRequest], GateResult]] = [
            value_boundary_gate,
            tolerance_gate,
            freshness_gate,
            duplicate_gate,
            review_gate,
        ]

    def evaluate(self, req: ReviewRequest) -> AuditEvent:
        results = [gate(req) for gate in self.gates]
        statuses = [result.status for result in results]
        if GateStatus.STOP in statuses:
            aggregate = GateStatus.STOP
        elif GateStatus.REVIEW in statuses:
            aggregate = GateStatus.REVIEW
        else:
            aggregate = GateStatus.PASS

        event_payload: Dict[str, Any] = {
            "schema": "membra.overandor.audit_event.v1",
            "created_at": utc_now(),
            "request_id": req.request_id,
            "asset_name": req.asset_name,
            "aggregate_status": aggregate.value,
            "results": [asdict(result) for result in results],
        }
        return AuditEvent(event_hash=stable_hash(event_payload), **event_payload)  # type: ignore[arg-type]


def demo() -> None:
    request = ReviewRequest(
        request_id="demo-001",
        asset_name="Language.fi",
        value_usd=25000.0,
        max_value_usd=50000.0,
        tolerance_bps=25.0,
        max_tolerance_bps=50.0,
        data_age_seconds=5.0,
        max_data_age_seconds=30.0,
        duplicate_key_seen=False,
        review_passed=True,
        metadata={"mode": "demo"},
    )
    event = OverandorControlPlane().evaluate(request)
    print(json.dumps(asdict(event), indent=2, default=str))


if __name__ == "__main__":
    demo()
