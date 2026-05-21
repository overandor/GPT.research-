// overandor_engine.cpp
//
// Executable C++ artifact for the MEMBRA / overandor appraisal package.
//
// Purpose:
// - Demonstrate low-level deterministic review logic for institutional diligence.
// - Provide a systems-language component complementary to Python orchestration
//   and Rust invariant logic.
// - Avoid private keys, network submission, trading strategy, or execution logic.

#include <chrono>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

namespace membra {
namespace overandor {

enum class GateStatus {
    Pass,
    Review,
    Stop
};

struct ReviewRequest {
    std::string request_id;
    std::string asset_name;
    double value_usd;
    double max_value_usd;
    double tolerance_bps;
    double max_tolerance_bps;
    double data_age_seconds;
    double max_data_age_seconds;
    bool duplicate_key_seen;
    bool review_known;
    bool review_passed;
};

struct GateResult {
    std::string gate_id;
    std::string gate_name;
    GateStatus status;
    std::string reason;
    double value_under_review_usd;
};

std::string status_to_string(GateStatus status) {
    switch (status) {
        case GateStatus::Pass: return "pass";
        case GateStatus::Review: return "review";
        case GateStatus::Stop: return "stop";
    }
    return "unknown";
}

std::string utc_now() {
    const auto now = std::chrono::system_clock::now();
    const auto tt = std::chrono::system_clock::to_time_t(now);
    std::tm tm{};
#if defined(_WIN32)
    gmtime_s(&tm, &tt);
#else
    gmtime_r(&tt, &tm);
#endif
    std::ostringstream out;
    out << std::put_time(&tm, "%Y-%m-%dT%H:%M:%SZ");
    return out.str();
}

GateResult value_boundary_gate(const ReviewRequest& req) {
    if (req.value_usd > req.max_value_usd) {
        return {"CG-001", "Value Boundary Check", GateStatus::Stop,
                "Value exceeds configured boundary.", req.value_usd};
    }
    return {"CG-001", "Value Boundary Check", GateStatus::Pass,
            "Value is inside configured boundary.", 0.0};
}

GateResult tolerance_gate(const ReviewRequest& req) {
    if (req.tolerance_bps > req.max_tolerance_bps) {
        return {"CG-002", "Tolerance Check", GateStatus::Review,
                "Tolerance exceeds configured threshold.", req.value_usd};
    }
    return {"CG-002", "Tolerance Check", GateStatus::Pass,
            "Tolerance is acceptable.", 0.0};
}

GateResult freshness_gate(const ReviewRequest& req) {
    if (req.data_age_seconds > req.max_data_age_seconds) {
        return {"CG-003", "Freshness Check", GateStatus::Review,
                "Input data is stale.", req.value_usd};
    }
    return {"CG-003", "Freshness Check", GateStatus::Pass,
            "Input data is fresh.", 0.0};
}

GateResult duplicate_gate(const ReviewRequest& req) {
    if (req.duplicate_key_seen) {
        return {"CG-004", "Duplicate Check", GateStatus::Stop,
                "Duplicate request key observed.", req.value_usd};
    }
    return {"CG-004", "Duplicate Check", GateStatus::Pass,
            "No duplicate request key observed.", 0.0};
}

GateResult review_gate(const ReviewRequest& req) {
    if (!req.review_known) {
        return {"CG-005", "Review Check", GateStatus::Review,
                "Required review evidence missing.", req.value_usd};
    }
    if (!req.review_passed) {
        return {"CG-005", "Review Check", GateStatus::Stop,
                "Required review failed.", req.value_usd};
    }
    return {"CG-005", "Review Check", GateStatus::Pass,
            "Required review passed.", 0.0};
}

std::vector<GateResult> evaluate_gates(const ReviewRequest& req) {
    return {
        value_boundary_gate(req),
        tolerance_gate(req),
        freshness_gate(req),
        duplicate_gate(req),
        review_gate(req)
    };
}

GateStatus aggregate_status(const std::vector<GateResult>& results) {
    bool has_review = false;
    for (const auto& result : results) {
        if (result.status == GateStatus::Stop) {
            return GateStatus::Stop;
        }
        if (result.status == GateStatus::Review) {
            has_review = true;
        }
    }
    return has_review ? GateStatus::Review : GateStatus::Pass;
}

void print_audit_event(const ReviewRequest& req) {
    const auto results = evaluate_gates(req);
    const auto aggregate = aggregate_status(results);

    std::cout << "{\n";
    std::cout << "  \"schema\": \"membra.overandor.cpp_audit_event.v1\",\n";
    std::cout << "  \"created_at\": \"" << utc_now() << "\",\n";
    std::cout << "  \"request_id\": \"" << req.request_id << "\",\n";
    std::cout << "  \"asset_name\": \"" << req.asset_name << "\",\n";
    std::cout << "  \"aggregate_status\": \"" << status_to_string(aggregate) << "\",\n";
    std::cout << "  \"results\": [\n";

    for (std::size_t i = 0; i < results.size(); ++i) {
        const auto& r = results[i];
        std::cout << "    {\n";
        std::cout << "      \"gate_id\": \"" << r.gate_id << "\",\n";
        std::cout << "      \"gate_name\": \"" << r.gate_name << "\",\n";
        std::cout << "      \"status\": \"" << status_to_string(r.status) << "\",\n";
        std::cout << "      \"reason\": \"" << r.reason << "\",\n";
        std::cout << "      \"value_under_review_usd\": " << r.value_under_review_usd << "\n";
        std::cout << "    }" << (i + 1 < results.size() ? "," : "") << "\n";
    }

    std::cout << "  ]\n";
    std::cout << "}\n";
}

} // namespace overandor
} // namespace membra

int main() {
    membra::overandor::ReviewRequest request{
        "demo-001",
        "Language.fi",
        25000.0,
        50000.0,
        25.0,
        50.0,
        5.0,
        30.0,
        false,
        true,
        true
    };

    membra::overandor::print_audit_event(request);
    return 0;
}
