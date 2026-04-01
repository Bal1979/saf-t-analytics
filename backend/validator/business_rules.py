"""
Danske forretningsregler for SAF-T 2.0 validering.
Baseret på Erhvervsstyrelsens "Technical Description of SAF-T v2.0 – Draft".
"""

import re
from datetime import datetime
from lxml import etree


# Gyldige ISO 4217 valutakoder (udvalg)
VALID_CURRENCIES = {
    "DKK", "EUR", "USD", "GBP", "SEK", "NOK", "CHF", "JPY", "CAD", "AUD",
    "PLN", "CZK", "HUF", "RON", "BGN", "HRK", "ISK", "TRY", "CNY",
}

# Gyldige ISO 3166-1 alpha-2 landekoder (EU + udvalgte)
VALID_COUNTRIES = {
    "DK", "SE", "NO", "FI", "DE", "FR", "NL", "BE", "AT", "CH", "IT", "ES",
    "PT", "GB", "IE", "PL", "CZ", "HU", "RO", "BG", "HR", "SK", "SI", "LT",
    "LV", "EE", "LU", "MT", "CY", "GR", "US", "CA", "JP", "CN", "AU",
}

# Gyldige kontotyper
VALID_ACCOUNT_TYPES = {"Asset", "Liability", "Sale", "Expense", "Other"}


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


def _findtext(element, path, ns, default=None):
    """Find tekst i et element med namespace."""
    el = _find(element, path, ns)
    if el is not None and el.text:
        return el.text.strip()
    return default


def validate_header(root, ns):
    """Validér Header-sektionen."""
    errors = []
    header = _find(root, "Header", ns)

    if header is None:
        errors.append({
            "level": "FEJL",
            "category": "Header",
            "message": "Obligatorisk 'Header'-element mangler.",
            "line": None,
        })
        return errors

    # AuditFileVersion
    version = _findtext(header, "AuditFileVersion", ns)
    if not version:
        errors.append({
            "level": "FEJL",
            "category": "Header",
            "message": "Obligatorisk felt 'AuditFileVersion' mangler.",
            "line": None,
        })

    # AuditFileCountry
    country = _findtext(header, "AuditFileCountry", ns)
    if not country:
        errors.append({
            "level": "FEJL",
            "category": "Header",
            "message": "Obligatorisk felt 'AuditFileCountry' mangler.",
            "line": None,
        })
    elif country != "DK":
        errors.append({
            "level": "ADVARSEL",
            "category": "Header",
            "message": f"AuditFileCountry er '{country}', forventet 'DK' for dansk SAF-T.",
            "line": None,
        })

    # AuditFileDateCreated
    date_created = _findtext(header, "AuditFileDateCreated", ns)
    if not date_created:
        errors.append({
            "level": "FEJL",
            "category": "Header",
            "message": "Obligatorisk felt 'AuditFileDateCreated' mangler.",
            "line": None,
        })
    else:
        try:
            datetime.strptime(date_created, "%Y-%m-%d")
        except ValueError:
            errors.append({
                "level": "FEJL",
                "category": "Header",
                "message": f"AuditFileDateCreated '{date_created}' er ikke et gyldigt datoformat (YYYY-MM-DD).",
                "line": None,
            })

    # SoftwareCompanyName
    if not _findtext(header, "SoftwareCompanyName", ns):
        errors.append({
            "level": "FEJL",
            "category": "Header",
            "message": "Obligatorisk felt 'SoftwareCompanyName' mangler.",
            "line": None,
        })

    # SoftwareID
    if not _findtext(header, "SoftwareID", ns):
        errors.append({
            "level": "FEJL",
            "category": "Header",
            "message": "Obligatorisk felt 'SoftwareID' mangler.",
            "line": None,
        })

    # SoftwareVersion
    if not _findtext(header, "SoftwareVersion", ns):
        errors.append({
            "level": "FEJL",
            "category": "Header",
            "message": "Obligatorisk felt 'SoftwareVersion' mangler.",
            "line": None,
        })

    # Company
    company = _find(header, "Company", ns)
    if company is None:
        errors.append({
            "level": "FEJL",
            "category": "Header",
            "message": "Obligatorisk 'Company'-element mangler i Header.",
            "line": None,
        })
    else:
        errors.extend(_validate_company(company, ns))

    # DefaultCurrencyCode
    currency = _findtext(header, "DefaultCurrencyCode", ns)
    if not currency:
        errors.append({
            "level": "FEJL",
            "category": "Header",
            "message": "Obligatorisk felt 'DefaultCurrencyCode' mangler.",
            "line": None,
        })
    elif currency not in VALID_CURRENCIES:
        errors.append({
            "level": "ADVARSEL",
            "category": "Header",
            "message": f"DefaultCurrencyCode '{currency}' er ikke en kendt ISO 4217 valutakode.",
            "line": None,
        })

    # SelectionCriteria (M — elementet er obligatorisk, men indholdet er Optional per XSD)
    selection = _find(header, "SelectionCriteria", ns)
    if selection is None:
        errors.append({
            "level": "FEJL",
            "category": "Header",
            "message": "Obligatorisk 'SelectionCriteria'-element mangler i Header.",
            "line": None,
        })
    else:
        errors.extend(_validate_selection_criteria(selection, ns))

    # TaxAccountingBasis (O — minOccurs="0" i både v1.0 og v2.0 XSD)
    if not _findtext(header, "TaxAccountingBasis", ns):
        errors.append({
            "level": "ADVARSEL",
            "category": "Header",
            "message": "TaxAccountingBasis mangler. Det anbefales at angive regnskabsgrundlaget.",
            "line": None,
        })

    return errors


def _validate_company(company, ns):
    """Validér Company-element i Header."""
    errors = []

    # RegistrationNumber (CVR-nummer)
    reg_nr = _findtext(company, "RegistrationNumber", ns)
    if not reg_nr:
        errors.append({
            "level": "FEJL",
            "category": "Header > Company",
            "message": "Obligatorisk felt 'RegistrationNumber' (CVR-nummer) mangler.",
            "line": None,
        })
    else:
        # Dansk CVR-nummer er 8 cifre
        clean_nr = reg_nr.replace(" ", "").replace("-", "")
        if not re.match(r"^\d{8}$", clean_nr):
            errors.append({
                "level": "ADVARSEL",
                "category": "Header > Company",
                "message": f"RegistrationNumber '{reg_nr}' ligner ikke et gyldigt dansk CVR-nummer (8 cifre).",
                "line": None,
            })

    # Name
    if not _findtext(company, "Name", ns):
        errors.append({
            "level": "FEJL",
            "category": "Header > Company",
            "message": "Obligatorisk felt 'Name' mangler i Company.",
            "line": None,
        })

    # Address
    address = _find(company, "Address", ns)
    if address is None:
        errors.append({
            "level": "FEJL",
            "category": "Header > Company",
            "message": "Obligatorisk 'Address'-element mangler i Company.",
            "line": None,
        })
    else:
        if not _findtext(address, "City", ns):
            errors.append({
                "level": "FEJL",
                "category": "Header > Company > Address",
                "message": "Obligatorisk felt 'City' mangler i Address.",
                "line": None,
            })
        if not _findtext(address, "PostalCode", ns):
            errors.append({
                "level": "FEJL",
                "category": "Header > Company > Address",
                "message": "Obligatorisk felt 'PostalCode' mangler i Address.",
                "line": None,
            })
        country = _findtext(address, "Country", ns)
        if not country:
            errors.append({
                "level": "FEJL",
                "category": "Header > Company > Address",
                "message": "Obligatorisk felt 'Country' mangler i Address.",
                "line": None,
            })
        elif country not in VALID_COUNTRIES:
            errors.append({
                "level": "ADVARSEL",
                "category": "Header > Company > Address",
                "message": f"Country '{country}' er ikke en kendt ISO 3166-1 landekode.",
                "line": None,
            })

    return errors


def _validate_selection_criteria(selection, ns):
    """Validér SelectionCriteria. Alle felter er Optional (O) per XSD."""
    errors = []

    # Periodefelter er Optional (minOccurs="0") per XSD-skemaet.
    # Vi giver kun en advarsel hvis de mangler, ikke en fejl.
    missing_fields = []
    for field in ["PeriodStart", "PeriodStartYear", "PeriodEnd", "PeriodEndYear"]:
        if not _findtext(selection, field, ns):
            missing_fields.append(field)

    if missing_fields:
        errors.append({
            "level": "ADVARSEL",
            "category": "Header > SelectionCriteria",
            "message": f"Valgfrie felter mangler: {', '.join(missing_fields)}. "
                       f"Det anbefales at angive perioden for fuldstændighedens skyld.",
            "line": None,
        })

    # Tjek at perioden er logisk
    start_year = _findtext(selection, "PeriodStartYear", ns)
    end_year = _findtext(selection, "PeriodEndYear", ns)
    start_period = _findtext(selection, "PeriodStart", ns)
    end_period = _findtext(selection, "PeriodEnd", ns)

    if all([start_year, end_year, start_period, end_period]):
        try:
            start = int(start_year) * 100 + int(start_period)
            end = int(end_year) * 100 + int(end_period)
            if start > end:
                errors.append({
                    "level": "FEJL",
                    "category": "Header > SelectionCriteria",
                    "message": "Startperioden er efter slutperioden.",
                    "line": None,
                })
        except ValueError:
            errors.append({
                "level": "FEJL",
                "category": "Header > SelectionCriteria",
                "message": "Periode-værdier er ikke gyldige tal.",
                "line": None,
            })

    return errors


def validate_master_files(root, ns, saft_version="2.0"):
    """Validér MasterFiles-sektionen. Obligatorisk i v2.0, valgfri i v1.0."""
    errors = []
    master = _find(root, "MasterFiles", ns)
    is_v2 = saft_version == "2.0"

    if master is None:
        if is_v2:
            errors.append({
                "level": "FEJL",
                "category": "MasterFiles",
                "message": "Obligatorisk 'MasterFiles'-element mangler. "
                           "MasterFiles er påkrævet i SAF-T 2.0.",
                "line": None,
            })
        else:
            errors.append({
                "level": "ADVARSEL",
                "category": "MasterFiles",
                "message": "MasterFiles-element mangler. "
                           "I SAF-T 1.0 er det valgfrit, men anbefales.",
                "line": None,
            })
        return errors, set()

    # GeneralLedgerAccounts (M i v2.0)
    gl_accounts = _findall(master, "GeneralLedgerAccounts", ns)
    account_ids = set()

    if not gl_accounts:
        if is_v2:
            errors.append({
                "level": "FEJL",
                "category": "MasterFiles",
                "message": "Obligatorisk 'GeneralLedgerAccounts'-element mangler. "
                           "Kontoplanen er påkrævet i SAF-T 2.0.",
                "line": None,
            })
        else:
            errors.append({
                "level": "ADVARSEL",
                "category": "MasterFiles",
                "message": "GeneralLedgerAccounts mangler. "
                           "I SAF-T 1.0 er det valgfrit.",
                "line": None,
            })
    else:
        for gl in gl_accounts:
            # NameOfStandardAccount (M i v2.0, O i v1.0)
            name = _findtext(gl, "NameOfStandardAccount", ns)
            if not name:
                errors.append({
                    "level": "FEJL" if is_v2 else "ADVARSEL",
                    "category": "MasterFiles > GeneralLedgerAccounts",
                    "message": "Obligatorisk felt 'NameOfStandardAccount' mangler."
                               if is_v2 else
                               "NameOfStandardAccount mangler. I SAF-T 1.0 er det valgfrit, "
                               "men anbefales for mapping til Standardkontoplanen.",
                    "line": None,
                })
            elif name != "Standardkontoplanen":
                errors.append({
                    "level": "ADVARSEL",
                    "category": "MasterFiles > GeneralLedgerAccounts",
                    "message": f"NameOfStandardAccount er '{name}', "
                               f"forventet 'Standardkontoplanen'.",
                    "line": None,
                })

            # VersionOfStandardAccount (M i v2.0, O i v1.0)
            if not _findtext(gl, "VersionOfStandardAccount", ns):
                errors.append({
                    "level": "FEJL" if is_v2 else "ADVARSEL",
                    "category": "MasterFiles > GeneralLedgerAccounts",
                    "message": "Obligatorisk felt 'VersionOfStandardAccount' mangler."
                               if is_v2 else
                               "VersionOfStandardAccount mangler. I SAF-T 1.0 er det valgfrit.",
                    "line": None,
                })

            # Validér individuelle konti
            accounts = _findall(gl, "Account", ns)
            if not accounts:
                errors.append({
                    "level": "FEJL",
                    "category": "MasterFiles > GeneralLedgerAccounts",
                    "message": "Ingen 'Account'-elementer fundet i GeneralLedgerAccounts.",
                    "line": None,
                })

            for account in accounts:
                acc_id = _findtext(account, "AccountID", ns)
                if not acc_id:
                    errors.append({
                        "level": "FEJL",
                        "category": "MasterFiles > Account",
                        "message": "Obligatorisk felt 'AccountID' mangler i en konto.",
                        "line": None,
                    })
                else:
                    if acc_id in account_ids:
                        errors.append({
                            "level": "FEJL",
                            "category": "MasterFiles > Account",
                            "message": f"Duplikeret AccountID '{acc_id}'. "
                                       f"AccountID skal være unik.",
                            "line": None,
                        })
                    account_ids.add(acc_id)

                if not _findtext(account, "AccountDescription", ns):
                    errors.append({
                        "level": "FEJL",
                        "category": "MasterFiles > Account",
                        "message": f"Obligatorisk felt 'AccountDescription' mangler "
                                   f"for konto '{acc_id or 'ukendt'}'.",
                        "line": None,
                    })

                # AccountType (M i både v1.0 og v2.0)
                acc_type = _findtext(account, "AccountType", ns)
                if not acc_type:
                    errors.append({
                        "level": "FEJL",
                        "category": "MasterFiles > Account",
                        "message": f"Obligatorisk felt 'AccountType' mangler "
                                   f"for konto '{acc_id or 'ukendt'}'. "
                                   f"Gyldige værdier: {', '.join(sorted(VALID_ACCOUNT_TYPES))}.",
                        "line": None,
                    })
                elif acc_type not in VALID_ACCOUNT_TYPES:
                    errors.append({
                        "level": "ADVARSEL",
                        "category": "MasterFiles > Account",
                        "message": f"AccountType '{acc_type}' for konto '{acc_id}' er ikke "
                                   f"en gyldig type. Gyldige: {', '.join(VALID_ACCOUNT_TYPES)}.",
                        "line": None,
                    })

                # Opening/Closing balance — enten Debit eller Credit
                has_opening = (
                    _findtext(account, "OpeningDebitBalance", ns) is not None
                    or _findtext(account, "OpeningCreditBalance", ns) is not None
                )
                has_closing = (
                    _findtext(account, "ClosingDebitBalance", ns) is not None
                    or _findtext(account, "ClosingCreditBalance", ns) is not None
                )

                if not has_opening:
                    errors.append({
                        "level": "FEJL",
                        "category": "MasterFiles > Account",
                        "message": f"Konto '{acc_id or 'ukendt'}' mangler "
                                   f"OpeningDebitBalance eller OpeningCreditBalance.",
                        "line": None,
                    })
                if not has_closing:
                    errors.append({
                        "level": "FEJL",
                        "category": "MasterFiles > Account",
                        "message": f"Konto '{acc_id or 'ukendt'}' mangler "
                                   f"ClosingDebitBalance eller ClosingCreditBalance.",
                        "line": None,
                    })

    # TaxTable (M i v2.0, O i v1.0)
    tax_table = _find(master, "TaxTable", ns)
    if tax_table is None:
        if is_v2:
            errors.append({
                "level": "FEJL",
                "category": "MasterFiles",
                "message": "Obligatorisk 'TaxTable'-element mangler. "
                           "TaxTable er påkrævet i SAF-T 2.0.",
                "line": None,
            })
        else:
            errors.append({
                "level": "ADVARSEL",
                "category": "MasterFiles",
                "message": "TaxTable mangler. I SAF-T 1.0 er det valgfrit, men anbefales.",
                "line": None,
            })

    return errors, account_ids


def validate_general_ledger_entries(root, ns, valid_account_ids, saft_version="2.0"):
    """Validér GeneralLedgerEntries-sektionen. Obligatorisk i v2.0, valgfri i v1.0."""
    errors = []
    is_v2 = saft_version == "2.0"
    gle = _find(root, "GeneralLedgerEntries", ns)

    if gle is None:
        if is_v2:
            errors.append({
                "level": "FEJL",
                "category": "GeneralLedgerEntries",
                "message": "Obligatorisk 'GeneralLedgerEntries'-element mangler. "
                           "Transaktionsdata er påkrævet i SAF-T 2.0.",
                "line": None,
            })
        else:
            errors.append({
                "level": "ADVARSEL",
                "category": "GeneralLedgerEntries",
                "message": "GeneralLedgerEntries mangler. "
                           "I SAF-T 1.0 er det valgfrit.",
                "line": None,
            })
        return errors

    # NumberOfEntries
    num_entries = _findtext(gle, "NumberOfEntries", ns)
    if not num_entries:
        errors.append({
            "level": "FEJL",
            "category": "GeneralLedgerEntries",
            "message": "Obligatorisk felt 'NumberOfEntries' mangler.",
            "line": None,
        })

    # TotalDebit og TotalCredit
    total_debit = _findtext(gle, "TotalDebit", ns)
    total_credit = _findtext(gle, "TotalCredit", ns)

    if not total_debit:
        errors.append({
            "level": "FEJL",
            "category": "GeneralLedgerEntries",
            "message": "Obligatorisk felt 'TotalDebit' mangler.",
            "line": None,
        })
    if not total_credit:
        errors.append({
            "level": "FEJL",
            "category": "GeneralLedgerEntries",
            "message": "Obligatorisk felt 'TotalCredit' mangler.",
            "line": None,
        })

    # Balance-check: TotalDebit == TotalCredit
    if total_debit and total_credit:
        try:
            debit = float(total_debit)
            credit = float(total_credit)
            if abs(debit - credit) > 0.01:
                errors.append({
                    "level": "ADVARSEL",
                    "category": "GeneralLedgerEntries",
                    "message": f"TotalDebit ({debit:.2f}) og TotalCredit ({credit:.2f}) "
                               f"er ikke i balance. Difference: {abs(debit - credit):.2f}.",
                    "line": None,
                })
        except ValueError:
            errors.append({
                "level": "FEJL",
                "category": "GeneralLedgerEntries",
                "message": "TotalDebit eller TotalCredit er ikke gyldige tal.",
                "line": None,
            })

    # Validér Journals og Transaktioner
    journals = _findall(gle, "Journal", ns)
    actual_entry_count = 0
    referenced_accounts = set()

    for journal in journals:
        journal_id = _findtext(journal, "JournalID", ns)
        if not journal_id:
            errors.append({
                "level": "FEJL",
                "category": "GeneralLedgerEntries > Journal",
                "message": "Obligatorisk felt 'JournalID' mangler i en journal.",
                "line": None,
            })

        transactions = _findall(journal, "Transaction", ns)
        actual_entry_count += len(transactions)

        for txn in transactions:
            txn_id = _findtext(txn, "TransactionID", ns)

            # TransactionDate
            txn_date = _findtext(txn, "TransactionDate", ns)
            if not txn_date:
                errors.append({
                    "level": "FEJL",
                    "category": "GeneralLedgerEntries > Transaction",
                    "message": f"Obligatorisk felt 'TransactionDate' mangler "
                               f"i transaktion '{txn_id or 'ukendt'}'.",
                    "line": None,
                })

            # Linjer
            lines = _findall(txn, "Line", ns)
            if not lines:
                # Prøv også TransactionLine (varierer mellem implementeringer)
                lines = _findall(txn, "TransactionLine", ns)

            for line in lines:
                acc_id = _findtext(line, "AccountID", ns)
                if acc_id:
                    referenced_accounts.add(acc_id)

                # Hver linje skal have enten DebitAmount eller CreditAmount
                has_debit = _find(line, "DebitAmount", ns) is not None
                has_credit = _find(line, "CreditAmount", ns) is not None

                if not has_debit and not has_credit:
                    record_id = _findtext(line, "RecordID", ns) or "ukendt"
                    errors.append({
                        "level": "FEJL",
                        "category": "GeneralLedgerEntries > Line",
                        "message": f"Linje '{record_id}' i transaktion '{txn_id or 'ukendt'}' "
                                   f"mangler både DebitAmount og CreditAmount.",
                        "line": None,
                    })

    # Tjek NumberOfEntries matcher faktisk antal
    if num_entries:
        try:
            expected = int(num_entries)
            if expected != actual_entry_count:
                errors.append({
                    "level": "ADVARSEL",
                    "category": "GeneralLedgerEntries",
                    "message": f"NumberOfEntries angiver {expected} transaktioner, "
                               f"men der blev fundet {actual_entry_count}.",
                    "line": None,
                })
        except ValueError:
            pass

    # Referentiel integritet: Alle refererede konti skal findes i MasterFiles
    if valid_account_ids:
        orphan_accounts = referenced_accounts - valid_account_ids
        for acc_id in sorted(orphan_accounts):
            errors.append({
                "level": "FEJL",
                "category": "Referentiel integritet",
                "message": f"AccountID '{acc_id}' bruges i transaktioner, "
                           f"men er ikke defineret i GeneralLedgerAccounts.",
                "line": None,
            })

    return errors


def validate_business_rules(root, ns, saft_version="2.0"):
    """
    Kør alle forretningsregler på SAF-T filen.
    saft_version: "1.0" eller "2.0" — bestemmer hvilke felter der er obligatoriske.
    Returnerer en samlet liste af fejl og advarsler.
    """
    all_errors = []

    # 1. Header
    all_errors.extend(validate_header(root, ns))

    # 2. MasterFiles (strengere krav i v2.0)
    master_errors, account_ids = validate_master_files(root, ns, saft_version)
    all_errors.extend(master_errors)

    # 3. GeneralLedgerEntries (strengere krav i v2.0)
    all_errors.extend(validate_general_ledger_entries(root, ns, account_ids, saft_version))

    return all_errors
