"""
Løsningsforslag for SAF-T valideringsfejl.
Tilføjer konkrete, handlingsrettede forbedringsforslag med XML-eksempler.
"""

import re

# Mapping: (category-pattern, message-pattern) -> fix suggestion
# Hvert forslag har: "fix" (tekst), "example" (XML-kode), "reference" (standard-reference)
FIX_RULES = [
    # ===== HEADER =====
    {
        "match": lambda c, m: "Header" in c and "AuditFileVersion" in m and "mangler" in m,
        "fix": "Tilføj elementet <AuditFileVersion> i <Header>. For SAF-T 2.0 skal værdien være '2.0'.",
        "example": "<AuditFileVersion>2.0</AuditFileVersion>",
        "reference": "SAF-T v2.0, sektion 3 (Header), felt AuditFileVersion (M)",
    },
    {
        "match": lambda c, m: "Header" in c and "AuditFileCountry" in m and "mangler" in m,
        "fix": "Tilføj elementet <AuditFileCountry> med værdien 'DK' (ISO 3166-1 alpha-2 landekode for Danmark).",
        "example": "<AuditFileCountry>DK</AuditFileCountry>",
        "reference": "SAF-T v2.0, sektion 3 (Header), felt AuditFileCountry (M)",
    },
    {
        "match": lambda c, m: "AuditFileCountry" in m and "forventet 'DK'" in m,
        "fix": "Ret AuditFileCountry til 'DK'. Den danske SAF-T standard kræver landekoden for Danmark.",
        "example": "<AuditFileCountry>DK</AuditFileCountry>",
        "reference": "SAF-T v2.0, sektion 3 (Header), felt AuditFileCountry (M)",
    },
    {
        "match": lambda c, m: "AuditFileDateCreated" in m and "mangler" in m,
        "fix": "Tilføj elementet <AuditFileDateCreated> med datoen for hvornår filen blev genereret i formatet YYYY-MM-DD.",
        "example": "<AuditFileDateCreated>2026-03-30</AuditFileDateCreated>",
        "reference": "SAF-T v2.0, sektion 3 (Header), felt AuditFileDateCreated (M)",
    },
    {
        "match": lambda c, m: "AuditFileDateCreated" in m and "datoformat" in m,
        "fix": "Ret datoen til ISO 8601-format: YYYY-MM-DD. Eksempel: '2026-01-15' for 15. januar 2026.",
        "example": "<AuditFileDateCreated>2026-01-15</AuditFileDateCreated>",
        "reference": "SAF-T v2.0, sektion 3 (Header), xs:date format",
    },
    {
        "match": lambda c, m: "SoftwareCompanyName" in m and "mangler" in m,
        "fix": "Tilføj elementet <SoftwareCompanyName> med navnet på firmaet bag bogføringssystemet. "
               "Kontakt din systemleverandør hvis du er i tvivl om det præcise navn.",
        "example": "<SoftwareCompanyName>Microsoft Corporation</SoftwareCompanyName>",
        "reference": "SAF-T v2.0, sektion 3 (Header), felt SoftwareCompanyName (M)",
    },
    {
        "match": lambda c, m: "SoftwareID" in m and "mangler" in m,
        "fix": "Tilføj elementet <SoftwareID> med navnet på det bogføringssystem der genererede filen.",
        "example": "<SoftwareID>Dynamics 365 Business Central</SoftwareID>",
        "reference": "SAF-T v2.0, sektion 3 (Header), felt SoftwareID (M)",
    },
    {
        "match": lambda c, m: "SoftwareVersion" in m and "mangler" in m,
        "fix": "Tilføj elementet <SoftwareVersion> med versionsnummeret for bogføringssystemet.",
        "example": "<SoftwareVersion>22.5.0</SoftwareVersion>",
        "reference": "SAF-T v2.0, sektion 3 (Header), felt SoftwareVersion (M)",
    },
    {
        "match": lambda c, m: "Company" in c and "Company'-element mangler" in m,
        "fix": "Tilføj et <Company>-element i <Header> med virksomhedens stamdata: "
               "CVR-nummer, navn og adresse. Disse oplysninger skal matche CVR-registret.",
        "example": "<Company>\n"
                   "  <RegistrationNumber>12345678</RegistrationNumber>\n"
                   "  <Name>Firmanavn ApS</Name>\n"
                   "  <Address>\n"
                   "    <StreetName>Vestergade</StreetName>\n"
                   "    <Number>42</Number>\n"
                   "    <City>København</City>\n"
                   "    <PostalCode>1456</PostalCode>\n"
                   "    <Country>DK</Country>\n"
                   "  </Address>\n"
                   "</Company>",
        "reference": "SAF-T v2.0, sektion 3.1 (CompanyHeaderStructure)",
    },
    {
        "match": lambda c, m: "RegistrationNumber" in m and "mangler" in m,
        "fix": "Tilføj virksomhedens CVR-nummer (8 cifre) i elementet <RegistrationNumber>. "
               "CVR-nummeret kan findes på virk.dk.",
        "example": "<RegistrationNumber>12345678</RegistrationNumber>",
        "reference": "SAF-T v2.0, sektion 3.1 (CompanyHeaderStructure), DanishCvrNumber type",
    },
    {
        "match": lambda c, m: "RegistrationNumber" in m and "CVR-nummer" in m and "8 cifre" in m,
        "fix": "CVR-nummeret skal være præcis 8 cifre uden bindestreger eller mellemrum. "
               "Slå det korrekte CVR-nummer op på cvr.dk eller virk.dk.",
        "example": "<RegistrationNumber>12345678</RegistrationNumber>",
        "reference": "SAF-T v2.0, sektion 3.1, DanishCvrNumber (8 cifre)",
    },
    {
        "match": lambda c, m: "'Name' mangler" in m and "Company" in c,
        "fix": "Tilføj virksomhedens officielle navn som det fremgår af CVR-registret.",
        "example": "<Name>Firmanavn ApS</Name>",
        "reference": "SAF-T v2.0, sektion 3.1 (CompanyHeaderStructure), felt Name (M)",
    },
    {
        "match": lambda c, m: "Address" in c and "Address'-element mangler" in m,
        "fix": "Tilføj et <Address>-element med virksomhedens adresse inkl. by, postnummer og land.",
        "example": "<Address>\n"
                   "  <StreetName>Vestergade</StreetName>\n"
                   "  <Number>42</Number>\n"
                   "  <City>København</City>\n"
                   "  <PostalCode>1456</PostalCode>\n"
                   "  <Country>DK</Country>\n"
                   "</Address>",
        "reference": "SAF-T v2.0, sektion 7.1 (AddressStructure)",
    },
    {
        "match": lambda c, m: "'City' mangler" in m,
        "fix": "Tilføj elementet <City> med bynavnet i virksomhedens adresse.",
        "example": "<City>København</City>",
        "reference": "SAF-T v2.0, sektion 7.1 (AddressStructure), felt City (M)",
    },
    {
        "match": lambda c, m: "'PostalCode' mangler" in m,
        "fix": "Tilføj elementet <PostalCode> med postnummeret. For danske adresser: 4-cifret postnummer.",
        "example": "<PostalCode>1456</PostalCode>",
        "reference": "SAF-T v2.0, sektion 7.1 (AddressStructure), felt PostalCode (M)",
    },
    {
        "match": lambda c, m: "'Country' mangler" in m and "Address" in c,
        "fix": "Tilføj elementet <Country> med ISO 3166-1 alpha-2 landekoden. Brug 'DK' for Danmark.",
        "example": "<Country>DK</Country>",
        "reference": "SAF-T v2.0, sektion 7.1 (AddressStructure), felt Country (M)",
    },
    {
        "match": lambda c, m: "Country" in m and "landekode" in m,
        "fix": "Brug en gyldig ISO 3166-1 alpha-2 landekode (2 bogstaver). Eksempler: DK, SE, DE, NO.",
        "example": "<Country>DK</Country>",
        "reference": "ISO 3166-1 alpha-2",
    },
    {
        "match": lambda c, m: "DefaultCurrencyCode" in m and "mangler" in m,
        "fix": "Tilføj elementet <DefaultCurrencyCode> med den primære valutakode (ISO 4217). "
               "For danske virksomheder er det typisk 'DKK'.",
        "example": "<DefaultCurrencyCode>DKK</DefaultCurrencyCode>",
        "reference": "SAF-T v2.0, sektion 3 (Header), felt DefaultCurrencyCode (M)",
    },
    {
        "match": lambda c, m: "DefaultCurrencyCode" in m and "valutakode" in m,
        "fix": "Brug en gyldig ISO 4217 valutakode (3 bogstaver). Eksempler: DKK, EUR, USD, GBP, SEK, NOK.",
        "example": "<DefaultCurrencyCode>DKK</DefaultCurrencyCode>",
        "reference": "ISO 4217 valutakoder",
    },
    {
        "match": lambda c, m: "SelectionCriteria" in m and "mangler i Header" in m,
        "fix": "Tilføj et <SelectionCriteria>-element der angiver den valgte regnskabsperiode. "
               "Denne sektion fortæller hvilken periode SAF-T filen dækker.",
        "example": "<SelectionCriteria>\n"
                   "  <PeriodStart>01</PeriodStart>\n"
                   "  <PeriodStartYear>2026</PeriodStartYear>\n"
                   "  <PeriodEnd>12</PeriodEnd>\n"
                   "  <PeriodEndYear>2026</PeriodEndYear>\n"
                   "</SelectionCriteria>",
        "reference": "SAF-T v2.0, sektion 3 (Header) + 7.11 (SelectionCriteriaStructure)",
    },
    {
        "match": lambda c, m: "SelectionCriteria" in c and "mangler" in m and ("PeriodStart" in m or "PeriodEnd" in m),
        "fix": "Tilføj de manglende periodefelter. PeriodStart/PeriodEnd er måned (01-12), "
               "PeriodStartYear/PeriodEndYear er årstal (fx 2026).",
        "example": "<PeriodStart>01</PeriodStart>\n"
                   "<PeriodStartYear>2026</PeriodStartYear>",
        "reference": "SAF-T v2.0, sektion 7.11 (SelectionCriteriaStructure)",
    },
    {
        "match": lambda c, m: "Startperioden er efter slutperioden" in m,
        "fix": "Ret perioden så startdatoen ligger før slutdatoen. "
               "Eksempel: Start = januar 2026, Slut = december 2026.",
        "example": "<PeriodStart>01</PeriodStart>\n"
                   "<PeriodStartYear>2026</PeriodStartYear>\n"
                   "<PeriodEnd>12</PeriodEnd>\n"
                   "<PeriodEndYear>2026</PeriodEndYear>",
        "reference": "SAF-T v2.0, sektion 7.11 (SelectionCriteriaStructure)",
    },
    {
        "match": lambda c, m: "TaxAccountingBasis" in m and "mangler" in m,
        "fix": "Tilføj elementet <TaxAccountingBasis>. For et normalt årsregnskab bruges typisk 'Regnskab'.",
        "example": "<TaxAccountingBasis>Regnskab</TaxAccountingBasis>",
        "reference": "SAF-T v2.0, sektion 3 (Header), felt TaxAccountingBasis (M)",
    },

    # ===== MASTERFILES =====
    {
        "match": lambda c, m: "MasterFiles" in c and "MasterFiles'-element mangler" in m,
        "fix": "Tilføj et <MasterFiles>-element som barn af <AuditFile>. I SAF-T 2.0 er MasterFiles "
               "obligatorisk og skal indeholde mindst GeneralLedgerAccounts og TaxTable. "
               "Kontakt din systemleverandør for at sikre at eksporten inkluderer stamdata.",
        "example": "<MasterFiles>\n"
                   "  <GeneralLedgerAccounts>\n"
                   "    <!-- Kontoplan her -->\n"
                   "  </GeneralLedgerAccounts>\n"
                   "  <TaxTable>\n"
                   "    <!-- Momstabel her -->\n"
                   "  </TaxTable>\n"
                   "</MasterFiles>",
        "reference": "SAF-T v2.0, sektion 4 (MasterFiles) — ændret fra Optional til Mandatory i v2.0",
    },
    {
        "match": lambda c, m: "GeneralLedgerAccounts'-element mangler" in m,
        "fix": "Tilføj et <GeneralLedgerAccounts>-element med virksomhedens kontoplan. "
               "Hver konto skal mappes til Erhvervsstyrelsens Standardkontoplan via StandardAccountID. "
               "Kontakt din systemleverandør for at aktivere SAF-T eksport af kontoplanen.",
        "example": "<GeneralLedgerAccounts>\n"
                   "  <NameOfStandardAccount>Standardkontoplanen</NameOfStandardAccount>\n"
                   "  <VersionOfStandardAccount>2.0</VersionOfStandardAccount>\n"
                   "  <Account>\n"
                   "    <AccountID>1000</AccountID>\n"
                   "    <AccountDescription>Bank</AccountDescription>\n"
                   "    <StandardAccountID>5000</StandardAccountID>\n"
                   "    <AccountType>Asset</AccountType>\n"
                   "    <OpeningDebitBalance>0.00</OpeningDebitBalance>\n"
                   "    <ClosingDebitBalance>50000.00</ClosingDebitBalance>\n"
                   "  </Account>\n"
                   "</GeneralLedgerAccounts>",
        "reference": "SAF-T v2.0, sektion 4.1 (GeneralLedgerAccounts) — Mandatory i v2.0",
    },
    {
        "match": lambda c, m: "NameOfStandardAccount" in m and "mangler" in m,
        "fix": "Tilføj elementet <NameOfStandardAccount> med værdien 'Standardkontoplanen'. "
               "Dette er den danske standardkontoplan som Erhvervsstyrelsen administrerer.",
        "example": "<NameOfStandardAccount>Standardkontoplanen</NameOfStandardAccount>",
        "reference": "SAF-T v2.0, sektion 4.1, felt NameOfStandardAccount (M)",
    },
    {
        "match": lambda c, m: "NameOfStandardAccount" in m and "forventet 'Standardkontoplanen'" in m,
        "fix": "Ret værdien til præcis 'Standardkontoplanen' (med stort S). "
               "Dette er den eneste tilladte værdi for danske SAF-T filer.",
        "example": "<NameOfStandardAccount>Standardkontoplanen</NameOfStandardAccount>",
        "reference": "SAF-T v2.0, sektion 4.1, enumeration: Standardkontoplanen",
    },
    {
        "match": lambda c, m: "VersionOfStandardAccount" in m and "mangler" in m,
        "fix": "Tilføj elementet <VersionOfStandardAccount> med versionen af Standardkontoplanen. "
               "Tjek den gældende version på erhvervsstyrelsen.dk/standardkontoplan-saf-t.",
        "example": "<VersionOfStandardAccount>2.0</VersionOfStandardAccount>",
        "reference": "SAF-T v2.0, sektion 4.1, felt VersionOfStandardAccount (M)",
    },
    {
        "match": lambda c, m: "'AccountID' mangler" in m,
        "fix": "Tilføj et unikt <AccountID> for hver konto. AccountID er kontonummeret fra dit bogføringssystem.",
        "example": "<AccountID>1000</AccountID>",
        "reference": "SAF-T v2.0, sektion 4.1.1 (Account), felt AccountID (M) + Key",
    },
    {
        "match": lambda c, m: "Duplikeret AccountID" in m,
        "fix": lambda c, m: f"Fjern den duplikerede konto eller giv den et unikt AccountID. "
                            f"Hver konto skal have et entydigt ID (Key-constraint i XSD). "
                            f"Tjek om der er sammenfald mellem konti fra forskellige afdelinger.",
        "example": "<!-- Hver AccountID skal være unik -->\n"
                   "<Account><AccountID>1000</AccountID>...</Account>\n"
                   "<Account><AccountID>1001</AccountID>...</Account>",
        "reference": "SAF-T v2.0, sektion 4.1.1 (Account), KeyGeneralLedgerAccount",
    },
    {
        "match": lambda c, m: "'AccountDescription' mangler" in m,
        "fix": "Tilføj en beskrivelse af kontoen i <AccountDescription>. "
               "Brug kontoens navn fra dit bogføringssystem.",
        "example": "<AccountDescription>Bankkonto - Danske Bank</AccountDescription>",
        "reference": "SAF-T v2.0, sektion 4.1.1 (Account), felt AccountDescription (M)",
    },
    {
        "match": lambda c, m: "AccountType" in m and "gyldig type" in m,
        "fix": "Ret AccountType til en af de tilladte værdier: Asset (aktiv), Liability (passiv), "
               "Sale (omsætning), Expense (omkostning) eller Other (andet).",
        "example": "<AccountType>Asset</AccountType>",
        "reference": "SAF-T v2.0, sektion 4.1.1 (Account), enumeration",
    },
    {
        "match": lambda c, m: "OpeningDebitBalance" in m or "OpeningCreditBalance" in m,
        "fix": "Tilføj enten <OpeningDebitBalance> eller <OpeningCreditBalance> med saldoen "
               "ved periodens start. Brug Debit for aktiver og udgifter, Credit for passiver og indtægter. "
               "Værdien skal være i standardvalutaen (typisk DKK).",
        "example": "<OpeningDebitBalance>50000.00</OpeningDebitBalance>\n"
                   "<!-- ELLER -->\n"
                   "<OpeningCreditBalance>50000.00</OpeningCreditBalance>",
        "reference": "SAF-T v2.0, sektion 4.1.1 (Account), OpeningDebitBalance/OpeningCreditBalance (M)",
    },
    {
        "match": lambda c, m: "ClosingDebitBalance" in m or "ClosingCreditBalance" in m,
        "fix": "Tilføj enten <ClosingDebitBalance> eller <ClosingCreditBalance> med saldoen "
               "ved periodens slutning. Brug samme side (Debit/Credit) som åbningsbalancen med "
               "mindre saldoen har skiftet fortegn.",
        "example": "<ClosingDebitBalance>75000.00</ClosingDebitBalance>\n"
                   "<!-- ELLER -->\n"
                   "<ClosingCreditBalance>75000.00</ClosingCreditBalance>",
        "reference": "SAF-T v2.0, sektion 4.1.1 (Account), ClosingDebitBalance/ClosingCreditBalance (M)",
    },
    {
        "match": lambda c, m: "TaxTable'-element mangler" in m,
        "fix": "Tilføj et <TaxTable>-element med virksomhedens momssatser. "
               "For de fleste danske virksomheder skal mindst standardmomsen (25%) medtages. "
               "Kontakt din systemleverandør for at inkludere TaxTable i SAF-T eksporten.",
        "example": "<TaxTable>\n"
                   "  <TaxTableEntry>\n"
                   "    <TaxType>VAT</TaxType>\n"
                   "    <Description>Dansk moms</Description>\n"
                   "    <TaxCodeDetails>\n"
                   "      <TaxCode>S25</TaxCode>\n"
                   "      <Description>Standardmoms 25%</Description>\n"
                   "      <TaxPercentage>25.00</TaxPercentage>\n"
                   "      <Country>DK</Country>\n"
                   "    </TaxCodeDetails>\n"
                   "  </TaxTableEntry>\n"
                   "</TaxTable>",
        "reference": "SAF-T v2.0, sektion 4.5 (TaxTable) — Mandatory i v2.0",
    },

    # ===== GENERAL LEDGER ENTRIES =====
    {
        "match": lambda c, m: "GeneralLedgerEntries'-element mangler" in m,
        "fix": "Tilføj et <GeneralLedgerEntries>-element med transaktionsdata. "
               "I SAF-T 2.0 er dette obligatorisk og skal indeholde alle bogførte transaktioner "
               "for den valgte periode. Kontakt din systemleverandør for at aktivere transaktionseksport.",
        "example": "<GeneralLedgerEntries>\n"
                   "  <NumberOfEntries>1</NumberOfEntries>\n"
                   "  <TotalDebit>1000.00</TotalDebit>\n"
                   "  <TotalCredit>1000.00</TotalCredit>\n"
                   "  <Journal>\n"
                   "    <JournalID>GL</JournalID>\n"
                   "    <Description>Hovedjournal</Description>\n"
                   "    <Type>GL</Type>\n"
                   "    <Transaction>...</Transaction>\n"
                   "  </Journal>\n"
                   "</GeneralLedgerEntries>",
        "reference": "SAF-T v2.0, sektion 5 (GeneralLedgerEntries) — Mandatory i v2.0",
    },
    {
        "match": lambda c, m: "'NumberOfEntries' mangler" in m,
        "fix": "Tilføj elementet <NumberOfEntries> med det totale antal transaktioner i filen. "
               "Tallet skal matche det faktiske antal <Transaction>-elementer.",
        "example": "<NumberOfEntries>42</NumberOfEntries>",
        "reference": "SAF-T v2.0, sektion 5 (GeneralLedgerEntries), felt NumberOfEntries (M)",
    },
    {
        "match": lambda c, m: "'TotalDebit' mangler" in m,
        "fix": "Tilføj elementet <TotalDebit> med summen af alle debetposteringer i filen.",
        "example": "<TotalDebit>1250000.00</TotalDebit>",
        "reference": "SAF-T v2.0, sektion 5 (GeneralLedgerEntries), felt TotalDebit (M)",
    },
    {
        "match": lambda c, m: "'TotalCredit' mangler" in m,
        "fix": "Tilføj elementet <TotalCredit> med summen af alle kreditposteringer i filen.",
        "example": "<TotalCredit>1250000.00</TotalCredit>",
        "reference": "SAF-T v2.0, sektion 5 (GeneralLedgerEntries), felt TotalCredit (M)",
    },
    {
        "match": lambda c, m: "TotalDebit" in m and "ikke i balance" in m,
        "fix": "TotalDebit og TotalCredit skal være ens (dobbelt bogholderi). "
               "Genberegn summerne fra alle transaktionslinjer. Hvis de stadig ikke stemmer, "
               "er der sandsynligvis en manglende modpostering i bogføringen. "
               "Kontakt din bogholder eller revisor.",
        "example": "<TotalDebit>1250000.00</TotalDebit>\n"
                   "<TotalCredit>1250000.00</TotalCredit>",
        "reference": "SAF-T v2.0, sektion 5 — dobbelt bogholderi princippet",
    },
    {
        "match": lambda c, m: "NumberOfEntries angiver" in m and "blev fundet" in m,
        "fix": "Ret værdien i <NumberOfEntries> så den matcher det faktiske antal transaktioner. "
               "Tæl alle <Transaction>-elementer på tværs af alle journals.",
        "example": "<!-- Hvis der er 42 transaktioner i filen: -->\n"
                   "<NumberOfEntries>42</NumberOfEntries>",
        "reference": "SAF-T v2.0, sektion 5, NumberOfEntries skal matche antal Transaction",
    },
    {
        "match": lambda c, m: "'JournalID' mangler" in m,
        "fix": "Tilføj et unikt <JournalID> for hver journal. Brug journalnavn/-kode fra dit system.",
        "example": "<JournalID>GL</JournalID>",
        "reference": "SAF-T v2.0, sektion 5.1 (Journal), felt JournalID (M)",
    },
    {
        "match": lambda c, m: "'TransactionDate' mangler" in m,
        "fix": "Tilføj elementet <TransactionDate> med bogføringsdatoen i formatet YYYY-MM-DD. "
               "Datoen skal ligge inden for den valgte periode i SelectionCriteria.",
        "example": "<TransactionDate>2026-03-15</TransactionDate>",
        "reference": "SAF-T v2.0, sektion 5.1.1 (Transaction), felt TransactionDate (M)",
    },
    {
        "match": lambda c, m: "mangler både DebitAmount og CreditAmount" in m,
        "fix": "Tilføj enten <DebitAmount> eller <CreditAmount> til linjen. "
               "Hver transaktionslinje skal have præcis én af delene. "
               "Beløbet angives med <Amount>-underelementet.",
        "example": "<DebitAmount>\n"
                   "  <Amount>1000.00</Amount>\n"
                   "</DebitAmount>\n"
                   "<!-- ELLER -->\n"
                   "<CreditAmount>\n"
                   "  <Amount>1000.00</Amount>\n"
                   "</CreditAmount>",
        "reference": "SAF-T v2.0, sektion 5.1.1.1 (Line), DebitAmount/CreditAmount",
    },

    # ===== REFERENTIEL INTEGRITET =====
    {
        "match": lambda c, m: "Referentiel integritet" in c,
        "fix": lambda c, m: _ref_integrity_fix(m),
        "example": "<!-- Tilføj kontoen i MasterFiles: -->\n"
                   "<Account>\n"
                   "  <AccountID>[kontonummer]</AccountID>\n"
                   "  <AccountDescription>[beskrivelse]</AccountDescription>\n"
                   "  <OpeningDebitBalance>0.00</OpeningDebitBalance>\n"
                   "  <ClosingDebitBalance>0.00</ClosingDebitBalance>\n"
                   "</Account>",
        "reference": "SAF-T v2.0, KeyRef-constraint: transaktionslinjer skal referere gyldige konti",
    },

    # ===== XML / XSD =====
    {
        "match": lambda c, m: "XML-syntaks" in c,
        "fix": "Filen indeholder XML-syntaksfejl og kan ikke parses. "
               "Tjek at filen er korrekt UTF-8 encoded og at alle XML-tags er korrekt lukket. "
               "Prøv at regenerere filen fra bogføringssystemet.",
        "example": "<!-- Tjek for manglende lukning af tags, fx: -->\n"
                   "<Header>...</Header>  <!-- korrekt -->\n"
                   "<Header>...           <!-- forkert: mangler </Header> -->",
        "reference": "XML 1.0 specifikation — well-formedness",
    },
    {
        "match": lambda c, m: "Root-elementet" in m and "AuditFile" in m,
        "fix": "Filens root-element skal være <AuditFile>. Tjek at filen er en SAF-T fil og "
               "ikke et andet XML-format. Prøv at regenerere filen med den korrekte SAF-T eksport.",
        "example": '<?xml version="1.0" encoding="UTF-8"?>\n'
                   '<AuditFile xmlns="urn:StandardAuditFile-Taxation-Financial:DK">\n'
                   "  <Header>...</Header>\n"
                   "  <MasterFiles>...</MasterFiles>\n"
                   "  <GeneralLedgerEntries>...</GeneralLedgerEntries>\n"
                   "</AuditFile>",
        "reference": "SAF-T v2.0, sektion 2 (AuditFile)",
    },
    {
        "match": lambda c, m: "XSD-skema" in c and "Intet XSD-skema" in m,
        "fix": "XSD-skemavalidering er ikke aktiv da skemafilen mangler. "
               "Når Erhvervsstyrelsen publicerer det danske SAF-T 2.0 XSD-skema, "
               "kan det placeres i 'schemas/'-mappen for fuld skemavalidering. "
               "Forretningsreglerne valideres stadig korrekt.",
        "example": "",
        "reference": "Erhvervsstyrelsen GitLab (publiceres efter høringen)",
    },
]


def _ref_integrity_fix(message):
    """Generér fix-forslag for referentiel integritet."""
    # Prøv at finde AccountID fra beskeden
    match = re.search(r"AccountID '([^']+)'", message)
    acc_id = match.group(1) if match else "[kontonummer]"
    return (
        f"Kontoen '{acc_id}' bruges i transaktioner men er ikke defineret i kontoplanen. "
        f"Enten: (1) Tilføj kontoen i GeneralLedgerAccounts med AccountID '{acc_id}', "
        f"eller (2) Ret transaktionslinjerne til at bruge en eksisterende konto. "
        f"Tjek om det er en tastefejl i kontonummeret."
    )


def enrich_with_suggestions(issues):
    """
    Berig en liste af fejl/advarsler med løsningsforslag.
    Tilføjer 'fix', 'example' og 'reference' felter.
    """
    for issue in issues:
        category = issue.get("category", "")
        message = issue.get("message", "")

        matched = False
        for rule in FIX_RULES:
            try:
                if rule["match"](category, message):
                    # Fix kan være en streng eller en funktion
                    fix = rule["fix"]
                    if callable(fix):
                        issue["fix"] = fix(category, message)
                    else:
                        issue["fix"] = fix
                    issue["example"] = rule.get("example", "")
                    issue["reference"] = rule.get("reference", "")
                    matched = True
                    break
            except Exception:
                continue

        if not matched:
            # Generisk fallback
            issue["fix"] = (
                "Tjek den tekniske beskrivelse for SAF-T 2.0 fra Erhvervsstyrelsen "
                "for krav til dette felt. Kontakt evt. din systemleverandør for hjælp."
            )
            issue["example"] = ""
            issue["reference"] = "SAF-T v2.0 Technical Description"

    return issues
