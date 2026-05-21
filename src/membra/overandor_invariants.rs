// overandor_invariants.rs
//
// Executable Rust artifact for the MEMBRA / overandor appraisal package.
//
// Purpose:
// - Provide a typed invariant/checking core for buyer and auditor diligence.
// - Demonstrate deterministic control logic in a systems language.
// - Avoid private keys, network submission, trading strategy, or execution logic.

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum GateStatus {
    Pass,
    Review,
    Stop,
}

#[derive(Debug, Clone)]
pub struct ReviewRequest {
    pub request_id: String,
    pub asset_name: String,
    pub value_usd: f64,
    pub max_value_usd: f64,
    pub tolerance_bps: f64,
    pub max_tolerance_bps: f64,
    pub data_age_seconds: f64,
    pub max_data_age_seconds: f64,
    pub duplicate_key_seen: bool,
    pub review_passed: Option<bool>,
}

#[derive(Debug, Clone)]
pub struct GateResult {
    pub gate_id: &'static str,
    pub gate_name: &'static str,
    pub status: GateStatus,
    pub reason: &'static str,
    pub value_under_review_usd: f64,
}

pub fn value_boundary_gate(req: &ReviewRequest) -> GateResult {
    if req.value_usd > req.max_value_usd {
        return GateResult {
            gate_id: "CG-001",
            gate_name: "Value Boundary Check",
            status: GateStatus::Stop,
            reason: "Value exceeds configured boundary.",
            value_under_review_usd: req.value_usd,
        };
    }

    GateResult {
        gate_id: "CG-001",
        gate_name: "Value Boundary Check",
        status: GateStatus::Pass,
        reason: "Value is inside configured boundary.",
        value_under_review_usd: 0.0,
    }
}

pub fn tolerance_gate(req: &ReviewRequest) -> GateResult {
    if req.tolerance_bps > req.max_tolerance_bps {
        return GateResult {
            gate_id: "CG-002",
            gate_name: "Tolerance Check",
            status: GateStatus::Review,
            reason: "Tolerance exceeds configured threshold.",
            value_under_review_usd: req.value_usd,
        };
    }

    GateResult {
        gate_id: "CG-002",
        gate_name: "Tolerance Check",
        status: GateStatus::Pass,
        reason: "Tolerance is acceptable.",
        value_under_review_usd: 0.0,
    }
}

pub fn freshness_gate(req: &ReviewRequest) -> GateResult {
    if req.data_age_seconds > req.max_data_age_seconds {
        return GateResult {
            gate_id: "CG-003",
            gate_name: "Freshness Check",
            status: GateStatus::Review,
            reason: "Input data is stale.",
            value_under_review_usd: req.value_usd,
        };
    }

    GateResult {
        gate_id: "CG-003",
        gate_name: "Freshness Check",
        status: GateStatus::Pass,
        reason: "Input data is fresh.",
        value_under_review_usd: 0.0,
    }
}

pub fn duplicate_gate(req: &ReviewRequest) -> GateResult {
    if req.duplicate_key_seen {
        return GateResult {
            gate_id: "CG-004",
            gate_name: "Duplicate Check",
            status: GateStatus::Stop,
            reason: "Duplicate request key observed.",
            value_under_review_usd: req.value_usd,
        };
    }

    GateResult {
        gate_id: "CG-004",
        gate_name: "Duplicate Check",
        status: GateStatus::Pass,
        reason: "No duplicate request key observed.",
        value_under_review_usd: 0.0,
    }
}

pub fn review_gate(req: &ReviewRequest) -> GateResult {
    match req.review_passed {
        Some(true) => GateResult {
            gate_id: "CG-005",
            gate_name: "Review Check",
            status: GateStatus::Pass,
            reason: "Required review passed.",
            value_under_review_usd: 0.0,
        },
        Some(false) => GateResult {
            gate_id: "CG-005",
            gate_name: "Review Check",
            status: GateStatus::Stop,
            reason: "Required review failed.",
            value_under_review_usd: req.value_usd,
        },
        None => GateResult {
            gate_id: "CG-005",
            gate_name: "Review Check",
            status: GateStatus::Review,
            reason: "Required review evidence missing.",
            value_under_review_usd: req.value_usd,
        },
    }
}

pub fn evaluate(req: &ReviewRequest) -> (GateStatus, Vec<GateResult>) {
    let results = vec![
        value_boundary_gate(req),
        tolerance_gate(req),
        freshness_gate(req),
        duplicate_gate(req),
        review_gate(req),
    ];

    let aggregate = if results.iter().any(|r| r.status == GateStatus::Stop) {
        GateStatus::Stop
    } else if results.iter().any(|r| r.status == GateStatus::Review) {
        GateStatus::Review
    } else {
        GateStatus::Pass
    };

    (aggregate, results)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_request() -> ReviewRequest {
        ReviewRequest {
            request_id: "demo-001".to_string(),
            asset_name: "Language.fi".to_string(),
            value_usd: 25_000.0,
            max_value_usd: 50_000.0,
            tolerance_bps: 25.0,
            max_tolerance_bps: 50.0,
            data_age_seconds: 5.0,
            max_data_age_seconds: 30.0,
            duplicate_key_seen: false,
            review_passed: Some(true),
        }
    }

    #[test]
    fn clean_request_passes() {
        let req = sample_request();
        let (status, results) = evaluate(&req);
        assert_eq!(status, GateStatus::Pass);
        assert_eq!(results.len(), 5);
    }

    #[test]
    fn duplicate_request_stops() {
        let mut req = sample_request();
        req.duplicate_key_seen = true;
        let (status, _) = evaluate(&req);
        assert_eq!(status, GateStatus::Stop);
    }
}
