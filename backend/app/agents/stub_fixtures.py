"""Canonical valid artifacts for the six stages.

Used by the StubRunner (offline/deterministic mission execution) and
re-exported by tests/fixtures.py for contract tests. Keeping them in the
backend keeps the stub runner self-contained (no test-package imports).
"""
from __future__ import annotations

USER_REQUEST = "Our Q2 sales dropped and we need to understand why and fix it."

VALID_PD = {
    "problem_statement": (
        "Q2 revenue declined 14% YoY; determine the drivers and recommend "
        "corrective actions to recover within two quarters."
    ),
    "objectives": [
        "Identify the drivers of the Q2 decline",
        "Recommend corrective actions",
    ],
    "success_criteria": [
        "Recover at least 5% revenue growth within two quarters",
        "Deliver prioritized recommendations within 3 weeks",
    ],
    "scope": {
        "included": ["domestic sales", "Q2 FY2026"],
        "excluded": ["international", "M&A"],
    },
    "stakeholders": [{"role": "CFO", "interest": "revenue recovery"}],
    "constraints": ["No new hires before Q4"],
    "assumptions": ["Pricing unchanged during Q2"],
    "key_questions": [
        "Which product categories drove the decline?",
        "Which regions were most affected?",
    ],
}

VALID_MANIFEST = {
    "sources": [
        {
            "source_id": "src_sales",
            "source_type": "file",
            "location": "data/q2_sales.csv",
            "acquired_at": "2026-08-01T10:00:00Z",
            "provenance_notes": "Export from ERP, finance team",
            "ingestion": {
                "format": "csv",
                "status": "success",
                "records_extracted": 1240,
                "parse_errors": [],
                "schema_extracted": [
                    {"field": "region", "inferred_type": "string"},
                    {"field": "category", "inferred_type": "string"},
                    {"field": "revenue", "inferred_type": "float"},
                ],
            },
        }
    ],
    "coverage": [
        {
            "key_question_ref": "Which product categories drove the decline?",
            "covered_by": ["src_sales"],
            "gaps": [],
        },
        {
            "key_question_ref": "Which regions were most affected?",
            "covered_by": ["src_sales"],
            "gaps": [],
        },
    ],
    "missing_data": [],
    "access_issues": [],
    "overall_status": "complete",
}

VALID_PREPARED = {
    "dataset": {
        "location": "artifacts/q2_sales_clean.parquet",
        "row_count": 1218,
        "column_count": 5,
        "primary_key": "transaction_id",
        "granularity": "monthly per product",
        "time_range": {"start": "2025-01-01", "end": "2026-06-30"},
    },
    "data_contract": {
        "version": "1.0",
        "fields": [
            {
                "name": "region",
                "semantic_meaning": "Sales region of the transaction",
                "data_type": "string",
                "nullability": False,
                "source_ref": "src_sales.region",
            },
            {
                "name": "category",
                "semantic_meaning": "Product category",
                "data_type": "string",
                "nullability": False,
                "source_ref": "src_sales.category",
            },
            {
                "name": "revenue",
                "semantic_meaning": "Transaction revenue in USD",
                "data_type": "float",
                "allowed_values_or_range": ">= 0",
                "nullability": False,
                "source_ref": "src_sales.revenue",
            },
        ],
    },
    "quality_metrics": {"missingness_percent": 1.2, "duplicate_rate": 0.0, "validation_errors": []},
    "cleaning_log": ["Removed 22 rows with NULL region", "Standardized revenue to USD"],
    "limitations": [],
}

VALID_REPORT = {
    "methodology": [
        {
            "step": "Trend computation",
            "method": "Monthly revenue aggregation + YoY comparison",
            "justification": "Directly answers the category question",
        }
    ],
    "findings": [
        {
            "finding_id": "F1",
            "statement": "Category A drove 62% of the Q2 decline",
            "evidence": {
                "computed_output_ref": "e2b://engagements/1/analysis/trend.json",
                "key_numbers": {"metric": "share_of_decline", "value": 0.62, "unit": "ratio"},
                "statistical_test": {"test": "t-test", "statistic": 4.1, "p_value": 0.002, "significant": True},
            },
            "answers_question": "Which product categories drove the decline?",
            "confidence": "high",
        }
    ],
    "open_questions": ["Which regions were most affected?"],
    "artifacts": [{"name": "trend", "type": "chart", "location": "e2b://engagements/1/analysis/trend.json"}],
}

VALID_INTERPRETATION = {
    "business_meaning": [
        {
            "finding_ref": "F1",
            "so_what": "Category A's decline is the primary revenue risk",
            "magnitude_of_impact": "62% of the 14% drop, ~8.7% of revenue",
            "affected": ["Sales", "Product"],
        }
    ],
    "causal_hypotheses": [
        {
            "hypothesis": "Category A lost shelf space to competitors",
            "status": "plausible",
            "supporting_evidence_refs": ["F1"],
            "rival_explanations": ["Pricing change in Category A"],
            "testability": "Compare distribution metrics",
        }
    ],
    "risks": [
        {"risk": "Recovery slower than expected", "likelihood": "medium", "impact": "high"}
    ],
    "implications": ["Focus recovery on Category A"],
    "what_would_change_conclusions": [],
}

VALID_RECOMMENDATION = {
    "recommendations": [
        {
            "recommendation_id": "R1",
            "action": "Shift 20% of Q3 marketing budget to Category A",
            "rationale": "F1 shows Category A drove 62% of the decline",
            "expected_impact": {
                "metric": "revenue growth",
                "estimate": "+5-8% within two quarters",
                "basis": ["F1"],
            },
            "effort": {"level": "low", "estimate": "2 weeks"},
            "cost_estimate": "$150k reallocation",
            "risks": ["Competitor response"],
            "priority": "critical",
            "success_criteria_ref": "SC1",
        }
    ],
    "alternatives_considered": [
        {"alternative": "Cut prices across all categories", "rejected_because": "High margin risk"}
    ],
    "deferred_criteria": [
        {"criterion_ref": "SC2", "reason": "Depends on Q3 results"}
    ],
    "final_summary": "Focus recovery on Category A with a budget shift.",
    "next_steps": ["Approve budget shift", "Monitor weekly"],
    "overall_confidence": "high",
}

STUB_OUTPUTS = {
    1: VALID_PD,
    2: VALID_MANIFEST,
    3: VALID_PREPARED,
    4: VALID_REPORT,
    5: VALID_INTERPRETATION,
    6: VALID_RECOMMENDATION,
}
