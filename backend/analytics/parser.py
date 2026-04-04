"""
SAF-T Data Parser
Udtrækker struktureret data fra SAF-T XML-filer til brug for analytics.
Konverterer XML til Python datastrukturer (dicts/lists) der er nemme at analysere.
"""

from lxml import etree
from typing import Optional


def _find(element, path, ns):
    """Find et element med namespace."""
    if ns:
        parts = path.split("/")
        ns_path = "/".join(f"{{{ns}}}{p}" for p in parts)
        return element.find(ns_path)
    return element.find(path)


def _findall(element, path, ns):
    """Find alle elementer med namespace."""
    if ns:
        parts = path.split("/")
        ns_path = "/".join(f"{{{ns}}}{p}" for p in parts)
        return element.findall(ns_path)
    return element.findall(path)


def _text(element, path, ns, default=None):
    """Find tekst i et element med namespace."""
    el = _find(element, path, ns)
    if el is not None and el.text:
        return el.text.strip()
    return default


def _decimal(element, path, ns, default=0.0):
    """Find decimal-værdi."""
    val = _text(element, path, ns)
    if val:
        try:
            return float(val)
        except ValueError:
            return default
    return default


def parse_saft_file(file_path: str) -> Optional[dict]:
    """
    Parser en SAF-T XML-fil og returnerer struktureret data.

    Returnerer et dict med:
    - header: Firmadata, periode, version
    - accounts: Kontoplan med saldi
    - tax_table: Momssatser
    - suppliers: Leverandører
    - customers: Kunder
    - transactions: Alle transaktioner med linjer
    - journals: Journaloversigt
    - summary: Opsummering (totaler, antal)
    """
    try:
        parser = etree.XMLParser(remove_blank_text=True, huge_tree=True, resolve_entities=False, no_network=True)
        tree = etree.parse(file_path, parser)
        root = tree.getroot()
    except Exception:
        return None

    # Detektér namespace
    ns = root.tag.split("}")[0].strip("{") if "}" in root.tag else ""

    data = {
        "header": _parse_header(root, ns),
        "accounts": _parse_accounts(root, ns),
        "tax_table": _parse_tax_table(root, ns),
        "suppliers": _parse_suppliers(root, ns),
        "customers": _parse_customers(root, ns),
        "transactions": [],
        "journals": [],
        "summary": {},
    }

    # Parse transaktioner
    transactions, journals = _parse_transactions(root, ns)
    data["transactions"] = transactions
    data["journals"] = journals

    # Beregn opsummering
    data["summary"] = _compute_summary(data)

    return data


def _parse_header(root, ns) -> dict:
    """Udtræk header-information."""
    header = _find(root, "Header", ns)
    if header is None:
        return {}

    company = _find(header, "Company", ns)
    address = _find(company, "Address", ns) if company is not None else None
    selection = _find(header, "SelectionCriteria", ns)

    return {
        "version": _text(header, "AuditFileVersion", ns, ""),
        "country": _text(header, "AuditFileCountry", ns, ""),
        "date_created": _text(header, "AuditFileDateCreated", ns, ""),
        "software_company": _text(header, "SoftwareCompanyName", ns, ""),
        "software_id": _text(header, "SoftwareID", ns, ""),
        "software_version": _text(header, "SoftwareVersion", ns, ""),
        "currency": _text(header, "DefaultCurrencyCode", ns, "DKK"),
        "tax_accounting_basis": _text(header, "TaxAccountingBasis", ns, ""),
        "company": {
            "registration_number": _text(company, "RegistrationNumber", ns, "") if company is not None else "",
            "name": _text(company, "Name", ns, "") if company is not None else "",
            "city": _text(address, "City", ns, "") if address is not None else "",
            "postal_code": _text(address, "PostalCode", ns, "") if address is not None else "",
            "country": _text(address, "Country", ns, "") if address is not None else "",
        },
        "period": {
            "start": _text(selection, "PeriodStart", ns, "") if selection is not None else "",
            "start_year": _text(selection, "PeriodStartYear", ns, "") if selection is not None else "",
            "end": _text(selection, "PeriodEnd", ns, "") if selection is not None else "",
            "end_year": _text(selection, "PeriodEndYear", ns, "") if selection is not None else "",
        },
    }


def _parse_accounts(root, ns) -> list:
    """Udtræk kontoplanen."""
    accounts = []
    master = _find(root, "MasterFiles", ns)
    if master is None:
        return accounts

    for gl in _findall(master, "GeneralLedgerAccounts", ns):
        standard_name = _text(gl, "NameOfStandardAccount", ns, "")
        standard_version = _text(gl, "VersionOfStandardAccount", ns, "")

        for acc in _findall(gl, "Account", ns):
            accounts.append({
                "account_id": _text(acc, "AccountID", ns, ""),
                "description": _text(acc, "AccountDescription", ns, ""),
                "standard_account_id": _text(acc, "StandardAccountID", ns, ""),
                "account_type": _text(acc, "AccountType", ns, ""),
                "opening_debit": _decimal(acc, "OpeningDebitBalance", ns),
                "opening_credit": _decimal(acc, "OpeningCreditBalance", ns),
                "closing_debit": _decimal(acc, "ClosingDebitBalance", ns),
                "closing_credit": _decimal(acc, "ClosingCreditBalance", ns),
                "standard_name": standard_name,
                "standard_version": standard_version,
            })

    return accounts


def _parse_tax_table(root, ns) -> list:
    """Udtræk momstabel."""
    tax_entries = []
    master = _find(root, "MasterFiles", ns)
    if master is None:
        return tax_entries

    tax_table = _find(master, "TaxTable", ns)
    if tax_table is None:
        return tax_entries

    for entry in _findall(tax_table, "TaxTableEntry", ns):
        tax_type = _text(entry, "TaxType", ns, "")
        description = _text(entry, "Description", ns, "")

        for detail in _findall(entry, "TaxCodeDetails", ns):
            tax_entries.append({
                "tax_type": tax_type,
                "description": description,
                "tax_code": _text(detail, "TaxCode", ns, ""),
                "detail_description": _text(detail, "Description", ns, ""),
                "tax_percentage": _decimal(detail, "TaxPercentage", ns),
                "country": _text(detail, "Country", ns, ""),
            })

    return tax_entries


def _parse_suppliers(root, ns) -> list:
    """Udtræk leverandører."""
    suppliers = []
    master = _find(root, "MasterFiles", ns)
    if master is None:
        return suppliers

    for supplier in _findall(master, "Suppliers/Supplier", ns):
        address = _find(supplier, "Address", ns)
        suppliers.append({
            "supplier_id": _text(supplier, "SupplierID", ns, ""),
            "registration_number": _text(supplier, "RegistrationNumber", ns, ""),
            "name": _text(supplier, "Name", ns, ""),
            "city": _text(address, "City", ns, "") if address is not None else "",
            "country": _text(address, "Country", ns, "") if address is not None else "",
            "tax_registration": _text(supplier, "TaxRegistration/TaxRegistrationNumber", ns, ""),
        })

    return suppliers


def _parse_customers(root, ns) -> list:
    """Udtræk kunder."""
    customers = []
    master = _find(root, "MasterFiles", ns)
    if master is None:
        return customers

    for customer in _findall(master, "Customers/Customer", ns):
        address = _find(customer, "Address", ns)
        customers.append({
            "customer_id": _text(customer, "CustomerID", ns, ""),
            "registration_number": _text(customer, "RegistrationNumber", ns, ""),
            "name": _text(customer, "Name", ns, ""),
            "city": _text(address, "City", ns, "") if address is not None else "",
            "country": _text(address, "Country", ns, "") if address is not None else "",
            "tax_registration": _text(customer, "TaxRegistration/TaxRegistrationNumber", ns, ""),
        })

    return customers


def _parse_transactions(root, ns) -> tuple:
    """Udtræk alle transaktioner med linjer. Returnerer (transactions, journals)."""
    transactions = []
    journals = []

    gle = _find(root, "GeneralLedgerEntries", ns)
    if gle is None:
        return transactions, journals

    total_debit_declared = _decimal(gle, "TotalDebit", ns)
    total_credit_declared = _decimal(gle, "TotalCredit", ns)
    num_entries_declared = _text(gle, "NumberOfEntries", ns, "0")

    for journal in _findall(gle, "Journal", ns):
        journal_id = _text(journal, "JournalID", ns, "")
        journal_desc = _text(journal, "Description", ns, "")
        journal_type = _text(journal, "Type", ns, "")

        journal_info = {
            "journal_id": journal_id,
            "description": journal_desc,
            "type": journal_type,
            "transaction_count": 0,
        }

        for txn in _findall(journal, "Transaction", ns):
            txn_id = _text(txn, "TransactionID", ns, "")
            txn_date = _text(txn, "TransactionDate", ns, "")
            txn_desc = _text(txn, "Description", ns, "")
            txn_period = _text(txn, "Period", ns, "")
            txn_period_year = _text(txn, "PeriodYear", ns, "")

            lines = []
            for line in _findall(txn, "Line", ns):
                record_id = _text(line, "RecordID", ns, "")
                account_id = _text(line, "AccountID", ns, "")
                description = _text(line, "Description", ns, "")

                # Debit eller Credit amount
                debit_el = _find(line, "DebitAmount", ns)
                credit_el = _find(line, "CreditAmount", ns)

                debit_amount = 0.0
                credit_amount = 0.0
                currency = ""

                if debit_el is not None:
                    debit_amount = _decimal(debit_el, "Amount", ns)
                    currency = _text(debit_el, "CurrencyCode", ns, "")
                if credit_el is not None:
                    credit_amount = _decimal(credit_el, "Amount", ns)
                    currency = _text(credit_el, "CurrencyCode", ns, "")

                # Tax information
                tax_info = _find(line, "TaxInformation", ns)
                tax_code = ""
                tax_percentage = 0.0
                tax_amount = 0.0
                tax_base = 0.0

                if tax_info is not None:
                    tax_code = _text(tax_info, "TaxCode", ns, "")
                    tax_percentage = _decimal(tax_info, "TaxPercentage", ns)
                    tax_amount = _decimal(tax_info, "TaxAmount/Amount", ns)
                    tax_base = _decimal(tax_info, "TaxBase", ns)

                # Supplier/Customer reference
                supplier_id = _text(line, "SupplierID", ns, "")
                customer_id = _text(line, "CustomerID", ns, "")

                # Source document reference
                source_doc_id = _text(line, "SourceDocumentID", ns, "")

                lines.append({
                    "record_id": record_id,
                    "account_id": account_id,
                    "description": description,
                    "debit_amount": debit_amount,
                    "credit_amount": credit_amount,
                    "currency": currency,
                    "tax_code": tax_code,
                    "tax_percentage": tax_percentage,
                    "tax_amount": tax_amount,
                    "tax_base": tax_base,
                    "supplier_id": supplier_id,
                    "customer_id": customer_id,
                    "source_document_id": source_doc_id,
                })

            transaction = {
                "transaction_id": txn_id,
                "journal_id": journal_id,
                "date": txn_date,
                "description": txn_desc,
                "period": txn_period,
                "period_year": txn_period_year,
                "lines": lines,
                "total_debit": sum(l["debit_amount"] for l in lines),
                "total_credit": sum(l["credit_amount"] for l in lines),
            }

            transactions.append(transaction)
            journal_info["transaction_count"] += 1

        journals.append(journal_info)

    return transactions, journals


def _compute_summary(data: dict) -> dict:
    """Beregn opsummering af parsed data."""
    transactions = data["transactions"]
    accounts = data["accounts"]

    total_debit = sum(t["total_debit"] for t in transactions)
    total_credit = sum(t["total_credit"] for t in transactions)
    total_lines = sum(len(t["lines"]) for t in transactions)

    # Unikke konti brugt i transaktioner
    used_accounts = set()
    for t in transactions:
        for l in t["lines"]:
            if l["account_id"]:
                used_accounts.add(l["account_id"])

    # Unikke leverandører og kunder i transaktioner
    used_suppliers = set()
    used_customers = set()
    for t in transactions:
        for l in t["lines"]:
            if l["supplier_id"]:
                used_suppliers.add(l["supplier_id"])
            if l["customer_id"]:
                used_customers.add(l["customer_id"])

    return {
        "total_transactions": len(transactions),
        "total_lines": total_lines,
        "total_debit": round(total_debit, 2),
        "total_credit": round(total_credit, 2),
        "balance_difference": round(abs(total_debit - total_credit), 2),
        "total_accounts_defined": len(accounts),
        "total_accounts_used": len(used_accounts),
        "total_suppliers_defined": len(data["suppliers"]),
        "total_suppliers_used": len(used_suppliers),
        "total_customers_defined": len(data["customers"]),
        "total_customers_used": len(used_customers),
        "total_tax_codes": len(data["tax_table"]),
        "total_journals": len(data["journals"]),
        "currency": data["header"].get("currency", "DKK"),
        "company_name": data["header"].get("company", {}).get("name", ""),
        "company_cvr": data["header"].get("company", {}).get("registration_number", ""),
        "period": data["header"].get("period", {}),
    }
