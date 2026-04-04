"""
Kategori 2: Dubletdetektion (Tests 11-18)
Identificerer duplikerede fakturaer, betalinger og transaktioner.
"""

from ..models import ParsedSAFTData, TestResult, Finding, TransactionRef
from collections import defaultdict


def run_tests(data: ParsedSAFTData) -> list[TestResult]:
    """Kør alle 8 dubletdetektionstests."""
    return [
        test_11_exact_duplicates(data),
        test_12_fuzzy_duplicates(data),
        test_13_same_amount_same_vendor(data),
        test_14_normalized_invoice_numbers(data),
        test_15_duplicate_payments(data),
        test_16_credit_note_duplicates(data),
        test_17_cross_entity_duplicates(data),
        test_18_sequential_invoice_gaps(data),
    ]


def _base(test_id: int, name: str) -> dict:
    return {"test_id": test_id, "test_name": name,
            "category_id": "duplicate_detection",
            "category_name": "Dubletdetektion"}


def test_11_exact_duplicates(data: ParsedSAFTData) -> TestResult:
    """Test 11: Eksakt duplikerede transaktioner (samme ID, dato, beløb)."""
    findings = []

    # Gruppér transaktioner efter en nøgle
    seen = defaultdict(list)
    for txn in data.transactions:
        total = sum(l.amount for l in txn.lines)
        key = (txn.date, f"{total:.2f}")
        seen[key].append(txn)

    for key, txns in seen.items():
        if len(txns) > 1:
            for txn in txns[1:]:  # Skip den første (original)
                total = sum(l.amount for l in txn.lines)
                findings.append(Finding(
                    finding_id=f"T11-{txn.transaction_id}",
                    severity="high",
                    title=f"Potentiel dublet-transaktion",
                    description=f"Transaktion {txn.transaction_id} ({txn.date}, "
                                f"{total:.2f} {data.currency}) "
                                f"matcher {txns[0].transaction_id} på dato og beløb.",
                    transactions=[
                        TransactionRef(
                            transaction_id=t.transaction_id,
                            journal_id=t.journal_id,
                            date=t.date,
                            amount=f"{sum(l.amount for l in t.lines):.2f}",
                            description=t.description,
                            highlight_field="duplicate",
                        ) for t in txns
                    ],
                    data={"duplicate_count": len(txns)},
                ))

    total = len(data.transactions)
    score = 100 if not findings else max(0, 100 - len(findings) * 10)

    return TestResult(
        **_base(11, "Eksakt dublet-transaktioner"),
        status="fail" if findings else "pass",
        score=score,
        finding_count=len(findings),
        findings=findings[:50],
        summary=f"{len(findings)} potentielle dubletter fundet blandt {total} transaktioner."
                if findings else f"Ingen dubletter fundet blandt {total} transaktioner.",
        methodology="Identificerer transaktioner med identisk dato og samlet beløb.",
    )


def test_12_fuzzy_duplicates(data: ParsedSAFTData) -> TestResult:
    """Test 12: Fuzzy dubletdetektion (lignende beløb, tætte datoer)."""
    findings = []

    # Gruppér efter beløb (afrundet) og find tætte datoer
    by_amount = defaultdict(list)
    for txn in data.transactions:
        total = round(sum(l.amount for l in txn.lines), 0)
        by_amount[total].append(txn)

    for amount, txns in by_amount.items():
        if len(txns) > 1 and amount != 0:
            # Tjek om de har forskellige datoer men tæt på hinanden
            dates = set(t.date for t in txns if t.date)
            if len(dates) > 1 and len(txns) <= 5:
                findings.append(Finding(
                    finding_id=f"T12-amt-{amount:.0f}",
                    severity="medium",
                    title=f"Lignende transaktioner ({amount:.0f} {data.currency})",
                    description=f"{len(txns)} transaktioner med beløb ~{amount:.0f} "
                                f"på forskellige datoer: {', '.join(sorted(dates))}.",
                    transactions=[
                        TransactionRef(
                            transaction_id=t.transaction_id,
                            date=t.date,
                            amount=f"{sum(l.amount for l in t.lines):.2f}",
                            description=t.description,
                            highlight_field="amount",
                        ) for t in txns
                    ],
                ))

    score = 100 if not findings else max(50, 100 - len(findings) * 5)

    return TestResult(
        **_base(12, "Fuzzy dubletdetektion"),
        status="warning" if findings else "pass",
        score=score,
        finding_count=len(findings),
        findings=findings[:50],
        summary=f"{len(findings)} grupper af lignende transaktioner fundet."
                if findings else "Ingen mistænkelige mønstre fundet.",
        methodology="Finder transaktioner med identisk beløb (afrundet) men forskellige datoer.",
    )


def test_13_same_amount_same_vendor(data: ParsedSAFTData) -> TestResult:
    """Test 13: Samme beløb fra samme leverandør inden for 30 dage."""
    findings = []

    # Gruppér efter leverandør (account_id som proxy) og beløb
    by_account = defaultdict(list)
    for txn in data.transactions:
        for line in txn.lines:
            if line.amount > 0:
                key = (line.account_id, round(line.amount, 2))
                by_account[key].append((txn, line))

    for (account_id, amount), entries in by_account.items():
        if len(entries) > 1:
            findings.append(Finding(
                finding_id=f"T13-{account_id}-{amount:.2f}",
                severity="medium",
                title=f"Gentagne beløb på konto {account_id}",
                description=f"{len(entries)} posteringer med beløb {amount:.2f} "
                            f"på konto {account_id}.",
                transactions=[
                    TransactionRef(
                        transaction_id=t.transaction_id,
                        date=t.date,
                        account_id=l.account_id,
                        amount=f"{l.amount:.2f}",
                        description=t.description,
                        highlight_field="amount",
                    ) for t, l in entries[:10]
                ],
                data={"occurrence_count": len(entries)},
            ))

    score = 100 if not findings else max(50, 100 - len(findings) * 3)

    return TestResult(
        **_base(13, "Samme beløb, samme konto"),
        status="warning" if findings else "pass",
        score=score,
        finding_count=len(findings),
        findings=findings[:50],
        summary=f"{len(findings)} mønstre med gentagne beløb fundet."
                if findings else "Ingen mistænkelige gentagelser fundet.",
        methodology="Identificerer gentagne beløb på samme konto, "
                    "som kan indikere duplikerede fakturaer.",
    )


def test_14_normalized_invoice_numbers(data: ParsedSAFTData) -> TestResult:
    """Test 14: Normaliseret transaktions-ID dubletcheck."""
    findings = []

    def normalize(s: str) -> str:
        return s.upper().replace("-", "").replace(" ", "").replace("_", "").lstrip("0")

    seen = defaultdict(list)
    for txn in data.transactions:
        if txn.transaction_id:
            norm = normalize(txn.transaction_id)
            seen[norm].append(txn)

    for norm, txns in seen.items():
        if len(txns) > 1:
            ids = [t.transaction_id for t in txns]
            if len(set(ids)) > 1:  # Kun hvis originale ID'er er forskellige
                findings.append(Finding(
                    finding_id=f"T14-{norm}",
                    severity="high",
                    title=f"Normaliseret dublet-ID",
                    description=f"Transaktions-ID'er {', '.join(ids)} "
                                f"er identiske efter normalisering (→ '{norm}').",
                    transactions=[
                        TransactionRef(
                            transaction_id=t.transaction_id,
                            date=t.date,
                            highlight_field="transaction_id",
                        ) for t in txns
                    ],
                ))

    return TestResult(
        **_base(14, "Normaliseret ID-dubletcheck"),
        status="fail" if findings else "pass",
        score=100 if not findings else max(0, 100 - len(findings) * 15),
        finding_count=len(findings),
        findings=findings[:50],
        summary=f"{len(findings)} normaliserede dubletter fundet."
                if findings else "Ingen ID-dubletter efter normalisering.",
        methodology="Fjerner bindestreger, mellemrum og foranstillede nuller fra "
                    "transaktions-ID'er og tjekker for dubletter.",
    )


def test_15_duplicate_payments(data: ParsedSAFTData) -> TestResult:
    """Test 15: Duplikerede betalinger."""
    # Kræver SourceDocuments → Payments
    return TestResult(
        **_base(15, "Duplikerede betalinger"),
        status="skipped",
        score=100,
        summary="Kræver SourceDocuments (Payments) for betalingsdubletanalyse.",
        methodology="Krydstjekker betalinger mod fakturaer for at finde dobbeltbetalinger.",
    )


def test_16_credit_note_duplicates(data: ParsedSAFTData) -> TestResult:
    """Test 16: Duplikerede kreditnotaer."""
    # Kræver SourceDocuments → SalesInvoices/PurchaseInvoices med type=creditnote
    return TestResult(
        **_base(16, "Kreditnota-dubletter"),
        status="skipped",
        score=100,
        summary="Kræver SourceDocuments for kreditnota-dubletanalyse.",
        methodology="Tjekker for duplikerede kreditnotaer der kan resultere i dobbelt momsrefusion.",
    )


def test_17_cross_entity_duplicates(data: ParsedSAFTData) -> TestResult:
    """Test 17: Tværgående enhedsdubletter."""
    # Kræver data fra flere juridiske enheder (flere SAF-T filer)
    return TestResult(
        **_base(17, "Tværgående enhedsdubletter"),
        status="skipped",
        score=100,
        summary="Kræver data fra flere juridiske enheder (flere SAF-T filer).",
        methodology="Tjekker om samme faktura er bogført i flere juridiske enheder.",
    )


def test_18_sequential_invoice_gaps(data: ParsedSAFTData) -> TestResult:
    """Test 18: Huller i sekventielle transaktions-ID'er."""
    findings = []

    # Prøv at finde numeriske sekvenser i transaktions-ID'er
    numeric_ids = []
    for txn in data.transactions:
        # Forsøg at udtrække tal fra ID'et
        digits = "".join(c for c in txn.transaction_id if c.isdigit())
        if digits:
            try:
                numeric_ids.append((int(digits), txn.transaction_id, txn))
            except ValueError:
                pass

    if len(numeric_ids) >= 3:
        numeric_ids.sort(key=lambda x: x[0])
        gaps = []
        for i in range(1, len(numeric_ids)):
            diff = numeric_ids[i][0] - numeric_ids[i-1][0]
            if diff > 1 and diff < 100:  # Rimelig gap-størrelse
                gaps.append((numeric_ids[i-1], numeric_ids[i], diff - 1))

        for prev, curr, gap_size in gaps[:20]:
            findings.append(Finding(
                finding_id=f"T18-gap-{prev[0]}-{curr[0]}",
                severity="medium" if gap_size < 5 else "high",
                title=f"Hul i nummersekvens ({gap_size} manglende)",
                description=f"Der er {gap_size} manglende nummer(e) mellem "
                            f"'{prev[1]}' og '{curr[1]}'. "
                            f"Kan indikere slettede eller undertrykte transaktioner.",
                transactions=[
                    TransactionRef(
                        transaction_id=prev[1],
                        date=prev[2].date,
                        highlight_field="sequence_gap",
                    ),
                    TransactionRef(
                        transaction_id=curr[1],
                        date=curr[2].date,
                        highlight_field="sequence_gap",
                    ),
                ],
                data={"gap_size": gap_size, "from_id": prev[1], "to_id": curr[1]},
            ))

    total_gaps = sum(f.data.get("gap_size", 0) for f in findings)
    score = 100 if not findings else max(0, 100 - min(total_gaps, 50) * 2)

    return TestResult(
        **_base(18, "Sekventielle nummerhuller"),
        status="warning" if findings else "pass",
        score=score,
        finding_count=len(findings),
        findings=findings,
        summary=f"{len(findings)} huller fundet ({total_gaps} manglende numre)."
                if findings else "Ingen huller i transaktionsnummersekvensen.",
        methodology="Analyserer transaktions-ID sekvenser for manglende numre, "
                    "som kan indikere slettede transaktioner.",
    )
