"""
Tests for SAF-T Analytics: parser, engine, and models.
"""

import os
import pytest

# Ensure backend is on the path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from analytics.parser import parse_saft_file
from analytics.engine import run_all_tests, build_report
from analytics.models import make_finding


TEST_VALID_XML = os.path.join(os.path.dirname(__file__), "..", "test_valid.xml")


# === parse_saft_file tests ===

class TestParseSaftFile:
    def test_returns_dict_with_expected_keys(self):
        data = parse_saft_file(TEST_VALID_XML)
        assert data is not None
        expected_keys = {
            "header", "accounts", "tax_table", "suppliers",
            "customers", "transactions", "journals", "summary",
        }
        assert expected_keys.issubset(data.keys())

    def test_header_contains_company_info(self):
        data = parse_saft_file(TEST_VALID_XML)
        header = data["header"]
        assert header["version"] == "2.0"
        assert header["country"] == "DK"
        assert header["company"]["name"] == "Eksempel ApS"
        assert header["company"]["registration_number"] == "12345678"

    def test_accounts_parsed(self):
        data = parse_saft_file(TEST_VALID_XML)
        assert len(data["accounts"]) == 3
        account_ids = [a["account_id"] for a in data["accounts"]]
        assert "1000" in account_ids
        assert "2000" in account_ids
        assert "3000" in account_ids

    def test_transactions_parsed(self):
        data = parse_saft_file(TEST_VALID_XML)
        assert len(data["transactions"]) == 2
        assert data["transactions"][0]["transaction_id"] == "TXN-001"

    def test_summary_computed(self):
        data = parse_saft_file(TEST_VALID_XML)
        summary = data["summary"]
        assert summary["total_transactions"] == 2
        assert summary["total_accounts_defined"] == 3

    def test_returns_none_for_invalid_file(self):
        result = parse_saft_file("/nonexistent/file.xml")
        assert result is None


# === run_all_tests tests ===

class TestRunAllTests:
    def test_returns_report_with_expected_structure(self):
        data = parse_saft_file(TEST_VALID_XML)
        report = run_all_tests(data)
        assert "overall_score" in report
        assert "categories" in report
        assert "all_findings" in report
        assert "total_findings" in report
        assert "severity_summary" in report
        assert "impact_summary" in report
        assert "summary" in report

    def test_overall_score_in_range(self):
        data = parse_saft_file(TEST_VALID_XML)
        report = run_all_tests(data)
        assert 0 <= report["overall_score"] <= 100

    def test_severity_summary_keys(self):
        data = parse_saft_file(TEST_VALID_XML)
        report = run_all_tests(data)
        for key in ("critical", "high", "medium", "low"):
            assert key in report["severity_summary"]


# === build_report tests ===

class TestBuildReport:
    def test_score_100_with_no_findings(self):
        data = parse_saft_file(TEST_VALID_XML)
        report = build_report(data, [])
        assert report["overall_score"] == 100
        assert report["total_findings"] == 0

    def test_score_decreases_with_findings(self):
        data = parse_saft_file(TEST_VALID_XML)
        findings = [
            make_finding(
                test_id=1,
                test_name="Test",
                impact_type="economic",
                direction="negative",
                severity="critical",
                description="A critical issue",
                estimated_amount=1000.0,
            ),
        ]
        report = build_report(data, findings)
        assert report["overall_score"] < 100
        assert report["total_findings"] == 1

    def test_impact_summary_amounts(self):
        data = parse_saft_file(TEST_VALID_XML)
        findings = [
            make_finding(
                test_id=1,
                test_name="Negative",
                impact_type="economic",
                direction="negative",
                severity="high",
                description="Negative finding",
                estimated_amount=500.0,
            ),
            make_finding(
                test_id=2,
                test_name="Positive",
                impact_type="economic",
                direction="positive",
                severity="low",
                description="Positive finding",
                estimated_amount=200.0,
            ),
        ]
        report = build_report(data, findings)
        econ = report["impact_summary"]["economic"]
        assert econ["negative_amount"] == 500.0
        assert econ["positive_amount"] == 200.0
        assert econ["net_amount"] == -300.0


# === make_finding tests ===

class TestMakeFinding:
    def test_creates_finding_with_all_required_fields(self):
        finding = make_finding(
            test_id=42,
            test_name="Test Name",
            impact_type="compliance",
            direction="neutral",
            severity="medium",
            description="Some description",
        )
        required_fields = {
            "test_id", "test_name", "impact_type", "direction",
            "severity", "description", "fix_suggestion",
            "estimated_amount", "currency", "transactions",
        }
        assert required_fields.issubset(finding.keys())

    def test_default_values(self):
        finding = make_finding(
            test_id=1,
            test_name="Test",
            impact_type="economic",
            direction="negative",
            severity="low",
            description="Desc",
        )
        assert finding["fix_suggestion"] == ""
        assert finding["estimated_amount"] == 0.0
        assert finding["currency"] == "DKK"
        assert finding["transactions"] == []

    def test_custom_values(self):
        finding = make_finding(
            test_id=99,
            test_name="Custom Test",
            impact_type="interest_risk",
            direction="positive",
            severity="critical",
            description="Custom desc",
            fix_suggestion="Fix it",
            estimated_amount=1234.56,
            currency="EUR",
            transactions=[{"id": "TXN-001"}],
        )
        assert finding["test_id"] == 99
        assert finding["fix_suggestion"] == "Fix it"
        assert finding["estimated_amount"] == 1234.56
        assert finding["currency"] == "EUR"
        assert len(finding["transactions"]) == 1
