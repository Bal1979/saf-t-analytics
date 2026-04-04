"""
SAF-T XML Streaming Parser.
Bruger lxml iterparse til hukommelseseffektiv parsing af store SAF-T filer.
Udtrækker alle data nødvendige for de 103 analytics tests.
"""

from lxml import etree
from .models import (
    ParsedSAFTData, Transaction, TransactionLine,
    Account, Supplier, Customer, TaxEntry,
)


def _ns(tag: str, namespace: str) -> str:
    """Tilføj namespace til et tag."""
    if namespace:
        return f"{{{namespace}}}{tag}"
    return tag


def _text(element, tag: str, ns: str) -> str:
    """Hent tekst fra et sub-element."""
    el = element.find(_ns(tag, ns))
    if el is not None and el.text:
        return el.text.strip()
    return ""


def _float(element, tag: str, ns: str) -> float:
    """Hent float fra et sub-element."""
    val = _text(element, tag, ns)
    try:
        return float(val) if val else 0.0
    except ValueError:
        return 0.0


def detect_namespace(file_path: str) -> str:
    """Detektér namespace fra SAF-T fil (læser kun root-elementet)."""
    secure_parser = etree.XMLParser(resolve_entities=False, no_network=True)
    for event, elem in etree.iterparse(file_path, events=("start",), parser=secure_parser):
        tag = elem.tag
        if "}" in tag:
            return tag.split("}")[0].strip("{")
        return ""
    return ""


def parse_saft_file(file_path: str) -> ParsedSAFTData:
    """
    Parser en komplet SAF-T fil og returnerer strukturerede data.
    Bruger iterparse for hukommelseseffektivitet.
    """
    ns = detect_namespace(file_path)
    data = ParsedSAFTData()

    # Parse med lxml (fuld parse for nu — iterparse kommer i Phase 2 for 100MB+ filer)
    secure_parser = etree.XMLParser(resolve_entities=False, no_network=True)
    tree = etree.parse(file_path, secure_parser)
    root = tree.getroot()

    # === Header ===
    header = root.find(_ns("Header", ns))
    if header is not None:
        data.saft_version = _text(header, "AuditFileVersion", ns)
        data.currency = _text(header, "DefaultCurrencyCode", ns) or "DKK"

        company = header.find(_ns("Company", ns))
        if company is not None:
            data.company_name = _text(company, "Name", ns)
            data.cvr_number = _text(company, "RegistrationNumber", ns)

        selection = header.find(_ns("SelectionCriteria", ns))
        if selection is not None:
            data.period_start = _text(selection, "PeriodStart", ns)
            data.period_start_year = _text(selection, "PeriodStartYear", ns)
            data.period_end = _text(selection, "PeriodEnd", ns)
            data.period_end_year = _text(selection, "PeriodEndYear", ns)

    # === MasterFiles ===
    master = root.find(_ns("MasterFiles", ns))
    if master is not None:
        _parse_accounts(master, ns, data)
        _parse_suppliers(master, ns, data)
        _parse_customers(master, ns, data)
        _parse_tax_table(master, ns, data)

    # === GeneralLedgerEntries ===
    gle = root.find(_ns("GeneralLedgerEntries", ns))
    if gle is not None:
        data.total_debit = _float(gle, "TotalDebit", ns)
        data.total_credit = _float(gle, "TotalCredit", ns)
        try:
            data.number_of_entries = int(_text(gle, "NumberOfEntries", ns) or "0")
        except ValueError:
            data.number_of_entries = 0

        _parse_transactions(gle, ns, data)

    return data


def _parse_accounts(master, ns: str, data: ParsedSAFTData):
    """Parse GeneralLedgerAccounts."""
    for gl in master.findall(_ns("GeneralLedgerAccounts", ns)):
        for acc_el in gl.findall(_ns("Account", ns)):
            opening_debit = _float(acc_el, "OpeningDebitBalance", ns)
            opening_credit = _float(acc_el, "OpeningCreditBalance", ns)
            closing_debit = _float(acc_el, "ClosingDebitBalance", ns)
            closing_credit = _float(acc_el, "ClosingCreditBalance", ns)

            is_debit = opening_debit > 0 or closing_debit > 0
            opening = opening_debit if is_debit else opening_credit
            closing = closing_debit if is_debit else closing_credit

            data.accounts.append(Account(
                account_id=_text(acc_el, "AccountID", ns),
                description=_text(acc_el, "AccountDescription", ns),
                standard_account_id=_text(acc_el, "StandardAccountID", ns),
                account_type=_text(acc_el, "AccountType", ns),
                opening_balance=opening,
                closing_balance=closing,
                is_debit=is_debit,
            ))


def _parse_suppliers(master, ns: str, data: ParsedSAFTData):
    """Parse Suppliers."""
    suppliers_el = master.find(_ns("Suppliers", ns))
    if suppliers_el is None:
        return
    for sup_el in suppliers_el.findall(_ns("Supplier", ns)):
        sup_id = _text(sup_el, "SupplierID", ns)
        name = _text(sup_el, "Name", ns)
        account_id = _text(sup_el, "AccountID", ns)

        # Tax registration
        vat_nr = ""
        country = ""
        tax_reg = sup_el.find(_ns("TaxRegistration", ns))
        if tax_reg is not None:
            vat_nr = _text(tax_reg, "TaxRegistrationNumber", ns)
            country = _text(tax_reg, "TaxType", ns)

        data.suppliers.append(Supplier(
            supplier_id=sup_id,
            name=name,
            vat_number=vat_nr,
            country=country,
            account_id=account_id,
        ))


def _parse_customers(master, ns: str, data: ParsedSAFTData):
    """Parse Customers."""
    customers_el = master.find(_ns("Customers", ns))
    if customers_el is None:
        return
    for cust_el in customers_el.findall(_ns("Customer", ns)):
        cust_id = _text(cust_el, "CustomerID", ns)
        name = _text(cust_el, "Name", ns)
        account_id = _text(cust_el, "AccountID", ns)

        vat_nr = ""
        country = ""
        tax_reg = cust_el.find(_ns("TaxRegistration", ns))
        if tax_reg is not None:
            vat_nr = _text(tax_reg, "TaxRegistrationNumber", ns)

        data.customers.append(Customer(
            customer_id=cust_id,
            name=name,
            vat_number=vat_nr,
            country=country,
            account_id=account_id,
        ))


def _parse_tax_table(master, ns: str, data: ParsedSAFTData):
    """Parse TaxTable."""
    tax_table = master.find(_ns("TaxTable", ns))
    if tax_table is None:
        return
    for entry in tax_table.findall(_ns("TaxTableEntry", ns)):
        tax_type = _text(entry, "TaxType", ns)
        desc = _text(entry, "Description", ns)

        for detail in entry.findall(_ns("TaxCodeDetails", ns)):
            data.tax_entries.append(TaxEntry(
                tax_type=tax_type,
                tax_code=_text(detail, "TaxCode", ns),
                description=_text(detail, "Description", ns) or desc,
                percentage=_float(detail, "TaxPercentage", ns),
                country=_text(detail, "Country", ns),
            ))


def _parse_transactions(gle, ns: str, data: ParsedSAFTData):
    """Parse GeneralLedgerEntries → Journal → Transaction → Line."""
    for journal in gle.findall(_ns("Journal", ns)):
        journal_id = _text(journal, "JournalID", ns)

        for txn_el in journal.findall(_ns("Transaction", ns)):
            txn = Transaction(
                transaction_id=_text(txn_el, "TransactionID", ns),
                journal_id=journal_id,
                date=_text(txn_el, "TransactionDate", ns),
                period=_text(txn_el, "Period", ns),
                period_year=_text(txn_el, "PeriodYear", ns),
                description=_text(txn_el, "Description", ns),
            )

            for line_el in txn_el.findall(_ns("Line", ns)):
                # Debit eller Credit
                debit_el = line_el.find(_ns("DebitAmount", ns))
                credit_el = line_el.find(_ns("CreditAmount", ns))

                if debit_el is not None:
                    amount = _float(debit_el, "Amount", ns)
                    is_debit = True
                elif credit_el is not None:
                    amount = _float(credit_el, "Amount", ns)
                    is_debit = False
                else:
                    amount = 0.0
                    is_debit = True

                # Tax info
                tax_code = ""
                tax_info = line_el.find(_ns("TaxInformation", ns))
                if tax_info is not None:
                    tax_code = _text(tax_info, "TaxCode", ns)

                txn.lines.append(TransactionLine(
                    record_id=_text(line_el, "RecordID", ns),
                    account_id=_text(line_el, "AccountID", ns),
                    amount=amount,
                    is_debit=is_debit,
                    tax_code=tax_code,
                    supplier_id=_text(line_el, "SupplierID", ns),
                    customer_id=_text(line_el, "CustomerID", ns),
                    description=_text(line_el, "Description", ns),
                ))

            data.transactions.append(txn)
