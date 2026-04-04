"""
SAF-T Analytics Engine.
Kører alle testkategorier og aggregerer resultater.
"""

from .models import ParsedSAFTData, AnalyticsReport, CategoryResult, TestResult, Finding
from .parser import parse_saft_file
from .categories import transaction_integrity, duplicate_detection


# Registrer alle testkategorier
CATEGORIES = [
    {
        "id": "transaction_integrity",
        "name": "Transaktionsintegritet",
        "description": "Fundamentale checks der verificerer datakvaliteten.",
        "module": transaction_integrity,
    },
    {
        "id": "duplicate_detection",
        "name": "Dubletdetektion",
        "description": "Identificerer duplikerede fakturaer, betalinger og transaktioner.",
        "module": duplicate_detection,
    },
    # Flere kategorier tilføjes her efterhånden...
]


def run_analytics(file_path: str) -> AnalyticsReport:
    """
    Kør alle analytics tests på en SAF-T fil.
    Returnerer en komplet AnalyticsReport med drill-down data.
    """
    # 1. Parse SAF-T data
    data = parse_saft_file(file_path)

    # 2. Kør alle testkategorier
    all_results: list[TestResult] = []
    categories: list[CategoryResult] = []

    for cat_def in CATEGORIES:
        module = cat_def["module"]
        test_results = module.run_tests(data)
        all_results.extend(test_results)

        # Aggregér kategori-statistik
        passed = sum(1 for t in test_results if t.status == "pass")
        failed = sum(1 for t in test_results if t.status == "fail")
        warning = sum(1 for t in test_results if t.status == "warning")
        skipped = sum(1 for t in test_results if t.status == "skipped")
        active_tests = passed + failed + warning
        score = int(
            (passed * 100 + warning * 50) / active_tests
        ) if active_tests > 0 else 100

        # Top findings for kategorien
        cat_findings = []
        for t in test_results:
            cat_findings.extend(t.findings[:3])
        cat_findings.sort(key=lambda f: {"high": 0, "medium": 1, "low": 2}[f.severity])

        categories.append(CategoryResult(
            category_id=cat_def["id"],
            name=cat_def["name"],
            description=cat_def["description"],
            score=score,
            tests_passed=passed,
            tests_failed=failed,
            tests_warning=warning,
            tests_skipped=skipped,
            tests_total=len(test_results),
            top_findings=cat_findings[:5],
        ))

    # 3. Beregn overordnet score
    active_categories = [c for c in categories if c.tests_passed + c.tests_failed + c.tests_warning > 0]
    overall_score = int(
        sum(c.score for c in active_categories) / len(active_categories)
    ) if active_categories else 100

    # 4. Top findings på tværs af alt
    all_findings: list[Finding] = []
    for t in all_results:
        all_findings.extend(t.findings)
    all_findings.sort(key=lambda f: {"high": 0, "medium": 1, "low": 2}[f.severity])

    total_passed = sum(c.tests_passed for c in categories)
    total_failed = sum(c.tests_failed for c in categories)
    total_warning = sum(c.tests_warning for c in categories)
    total_skipped = sum(c.tests_skipped for c in categories)

    return AnalyticsReport(
        overall_score=overall_score,
        total_tests=sum(c.tests_total for c in categories),
        tests_passed=total_passed,
        tests_failed=total_failed,
        tests_warning=total_warning,
        tests_skipped=total_skipped,
        total_findings=len(all_findings),
        categories=categories,
        test_results=all_results,
        top_findings=all_findings[:10],
        metadata={
            "company": data.company_name,
            "cvr": data.cvr_number,
            "period": f"{data.period_start}/{data.period_start_year} - "
                      f"{data.period_end}/{data.period_end_year}",
            "currency": data.currency,
            "saft_version": data.saft_version,
            "total_transactions": len(data.transactions),
            "total_accounts": len(data.accounts),
            "total_suppliers": len(data.suppliers),
            "total_customers": len(data.customers),
        },
    )
