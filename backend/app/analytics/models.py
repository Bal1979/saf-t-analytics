"""
Pydantic-modeller for SAF-T Analytics resultater.
Strukturerer data til PowerBI-stil drill-down dashboard.
"""

from __future__ import annotations
from pydantic import BaseModel
from typing import Literal, Optional, List, Dict
from decimal import Decimal
from datetime import date


# === Parsed SAF-T Data ===

class TransactionLine(BaseModel):
    record_id: str
    account_id: str
    amount: float
    is_debit: bool
    tax_code: Optional[str] = None
    supplier_id: Optional[str] = None
    customer_id: Optional[str] = None
    description: str = ""

class Transaction(BaseModel):
    transaction_id: str
    journal_id: str
    date: str
    period: str = ""
    period_year: str = ""
    description: str = ""
    lines: list[TransactionLine] = []

class Account(BaseModel):
    account_id: str
    description: str
    standard_account_id: str = ""
    account_type: str = ""
    opening_balance: float = 0.0
    closing_balance: float = 0.0
    is_debit: bool = True

class Supplier(BaseModel):
    supplier_id: str
    name: str = ""
    vat_number: str = ""
    country: str = ""
    account_id: str = ""

class Customer(BaseModel):
    customer_id: str
    name: str = ""
    vat_number: str = ""
    country: str = ""
    account_id: str = ""

class TaxEntry(BaseModel):
    tax_type: str
    tax_code: str
    description: str = ""
    percentage: float = 0.0
    country: str = ""

class ParsedSAFTData(BaseModel):
    """Komplet parsed SAF-T data til brug for analytics."""
    # Header
    company_name: str = ""
    cvr_number: str = ""
    currency: str = "DKK"
    period_start: str = ""
    period_end: str = ""
    period_start_year: str = ""
    period_end_year: str = ""
    saft_version: str = ""

    # MasterFiles
    accounts: list[Account] = []
    suppliers: list[Supplier] = []
    customers: list[Customer] = []
    tax_entries: list[TaxEntry] = []

    # GeneralLedgerEntries
    total_debit: float = 0.0
    total_credit: float = 0.0
    number_of_entries: int = 0
    transactions: list[Transaction] = []


# === Analytics Results (Drill-Down Levels) ===

class TransactionRef(BaseModel):
    """Level 4: Reference til en specifik transaktion."""
    transaction_id: str
    journal_id: str = ""
    date: str = ""
    account_id: str = ""
    amount: str = ""
    description: str = ""
    highlight_field: str = ""  # Feltet der udløste fundet

class Finding(BaseModel):
    """Level 3: Et enkelt fund fra en test."""
    finding_id: str
    severity: Literal["high", "medium", "low"]
    title: str
    description: str
    transactions: list[TransactionRef] = []
    data: dict = {}  # Fleksibel data til visning

class TestResult(BaseModel):
    """Level 2-3: Resultat af én specifik test."""
    test_id: int
    test_name: str
    category_id: str
    category_name: str
    status: Literal["pass", "fail", "warning", "skipped", "error"]
    score: int  # 0-100
    finding_count: int = 0
    findings: list[Finding] = []
    summary: str = ""
    methodology: str = ""

class CategoryResult(BaseModel):
    """Level 2: Aggregeret resultat for en hel kategori."""
    category_id: str
    name: str
    description: str = ""
    score: int  # 0-100
    tests_passed: int = 0
    tests_failed: int = 0
    tests_warning: int = 0
    tests_skipped: int = 0
    tests_total: int = 0
    top_findings: list[Finding] = []

class AnalyticsReport(BaseModel):
    """Level 1: Den samlede analytics-rapport."""
    overall_score: int  # 0-100
    total_tests: int
    tests_passed: int
    tests_failed: int
    tests_warning: int
    tests_skipped: int
    total_findings: int
    categories: list[CategoryResult] = []
    test_results: list[TestResult] = []
    top_findings: list[Finding] = []
    metadata: dict = {}
