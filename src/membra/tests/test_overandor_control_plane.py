#!/usr/bin/env python3
"""
Unit tests for overandor_control_plane.py.

These tests are neutral diligence artifacts. They verify deterministic control-plane
status behavior without network calls, private keys, transaction construction, or
market strategy logic.

Run from repository root:
    python -m unittest src.membra.tests.test_overandor_control_plane
"""

from __future__ import annotations

import unittest

from src.membra.overandor_control_plane import (
    GateStatus,
    OverandorControlPlane,
    ReviewRequest,
)


class TestOverandorControlPlane(unittest.TestCase):
    def sample_request(self) -> ReviewRequest:
        return ReviewRequest(
            request_id="test-001",
            asset_name="Language.fi",
            value_usd=25000.0,
            max_value_usd=50000.0,
            tolerance_bps=25.0,
            max_tolerance_bps=50.0,
            data_age_seconds=5.0,
            max_data_age_seconds=30.0,
            duplicate_key_seen=False,
            review_passed=True,
            metadata={"mode": "unit-test"},
        )

    def test_clean_request_passes(self) -> None:
        event = OverandorControlPlane().evaluate(self.sample_request())
        self.assertEqual(event.aggregate_status, GateStatus.PASS)
        self.assertEqual(len(event.results), 5)
        self.assertEqual(event.schema, "membra.overandor.audit_event.v1")
        self.assertTrue(event.event_hash)

    def test_value_boundary_stop(self) -> None:
        req = self.sample_request()
        req = ReviewRequest(**{**req.__dict__, "value_usd": 100000.0})
        event = OverandorControlPlane().evaluate(req)
        self.assertEqual(event.aggregate_status, GateStatus.STOP)

    def test_stale_data_review(self) -> None:
        req = self.sample_request()
        req = ReviewRequest(**{**req.__dict__, "data_age_seconds": 120.0})
        event = OverandorControlPlane().evaluate(req)
        self.assertEqual(event.aggregate_status, GateStatus.REVIEW)

    def test_duplicate_key_stop(self) -> None:
        req = self.sample_request()
        req = ReviewRequest(**{**req.__dict__, "duplicate_key_seen": True})
        event = OverandorControlPlane().evaluate(req)
        self.assertEqual(event.aggregate_status, GateStatus.STOP)

    def test_missing_review_triggers_review(self) -> None:
        req = self.sample_request()
        req = ReviewRequest(**{**req.__dict__, "review_passed": None})
        event = OverandorControlPlane().evaluate(req)
        self.assertEqual(event.aggregate_status, GateStatus.REVIEW)


if __name__ == "__main__":
    unittest.main()
