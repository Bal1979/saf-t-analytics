# VAT Analytics - Komplet Testkatalog (103 tests)

Baseret på research af Skattestyrelsens praksis, EU-skattemyndigheders metoder,
Big 4 revisionshusets VAT analytics tools, og kommercielle platforme.

---

## Kategori 1: Transaktionsintegritet & Datakvalitet (10 tests)

| # | Test | Beskrivelse |
|---|------|-------------|
| 1 | Moms-genberegning | Genberegn moms på hver salgs-/købslinje og sammenlign med registreret momsbeløb. Flag linjer med afvigelse. |
| 2 | Momskode-validering | Verificér at hver transaktion har en gyldig, aktiv momskode der mapper til en legitim sats. |
| 3 | Momsafrunding | Tjek at forskellen mellem linjeniveau-moms og dokumentniveau-moms er inden for afrundingstolerance. |
| 4 | Faktura-feltfuldstændighed | Validér at alle lovpligtige felter er udfyldt: sælger/køber, CVR, fakturanr, dato, beskrivelse, beløb, sats. |
| 5 | Fakturadato vs. bogføringsdato | Sammenlign fakturadato med bogføringsdato. Flag transaktioner der bogføres i en anden momsperiode. |
| 6 | Negative linjebeløb | Identificér købs-/salgstransaktioner med negative beløb der ikke er klassificeret som kreditnotaer. |
| 7 | Nul-værdi transaktioner | Flag fakturaer med momsgrundlag = 0 men moms ≠ 0, eller omvendt. |
| 8 | Valutakurs-konsistens | For flervaluta-transaktioner: verificér at anvendt kurs matcher Nationalbankens/ECBs officielle kurs. |
| 9 | Leveringstidspunkt (tax point) | Verificér at momsperioden bestemmes korrekt ud fra leveringstidspunktet. |
| 10 | Dokumenttype-klassificering | Sikr at dokumenter er korrekt klassificeret (faktura, kreditnota, debitnota, proforma). |

## Kategori 2: Dubletdetektion (8 tests)

| # | Test | Beskrivelse |
|---|------|-------------|
| 11 | Eksakt dubletfaktura | Find fakturaer hvor leverandør, fakturanummer, dato og beløb er identiske. |
| 12 | Fuzzy dubletfaktura | Flag fakturapar hvor leverandør og beløb matcher men fakturanumre afviger minimalt (fx "INV-123" vs "INV123"). |
| 13 | Samme beløb, samme leverandør | Find flere fakturaer fra samme leverandør med identisk beløb inden for 30 dage. |
| 14 | Normaliseret fakturanummer | Strip specialtegn, konvertér til uppercase, fjern foranstillede nuller — kør dubletcheck igen. |
| 15 | Dobbelbetalingsdetektion | Krydstjek betalinger mod fakturaer for at finde fakturaer betalt mere end én gang. |
| 16 | Kreditnota-dublet | Tjek for duplikerede kreditnotaer der kan resultere i dobbelt momsrefusion. |
| 17 | Tværgående enhedsdublet | For koncerner: tjek om samme leverandørfaktura er bogført og momsfradraget i flere juridiske enheder. |
| 18 | Sekventielle fakturanumre | Analysér fakturanummersekvenser for huller (slettede fakturaer?) og dubletter. |

## Kategori 3: Momssats-validering (8 tests)

| # | Test | Beskrivelse |
|---|------|-------------|
| 19 | Standard momssats | Verificér at anvendt momssats matcher lovpligtig standardsats (25% i DK). Flag afvigelser. |
| 20 | Reduceret sats berettigelse | For transaktioner med reduceret sats: verificér at varen/ydelsen er berettiget til reduceret sats. |
| 21 | Nulsats berettigelse | Verificér at nulsats-transaktioner opfylder betingelserne (eksportdokumentation, EU-transport). |
| 22 | Momsfri klassificering | Sikr at momsfritagne transaktioner reelt kvalificerer (finans, sundhed, uddannelse, forsikring). |
| 23 | Satsændring-overgang | Ved momssatsændringer: verificér at korrekt sats anvendes baseret på leveringstidspunktet. |
| 24 | Blandet leverance-fordeling | Verificér delvis fradragsret er korrekt beregnet for virksomheder med både momspligtig og momsfri omsætning. |
| 25 | Reverse charge-sats | Verificér at reverse charge beregnes med korrekt indenlandsk sats og at indgående/udgående moms matcher. |
| 26 | Konsistent sats per varekode | Gruppér transaktioner per varekode og verificér at samme momssats anvendes konsistent. |

## Kategori 4: Grænseoverskridende & EU-compliance (12 tests)

| # | Test | Beskrivelse |
|---|------|-------------|
| 27 | VIES momsnummer-validering | Validér alle EU-momsnumre mod VIES-databasen. Flag ugyldige eller afregistrerede numre. |
| 28 | EU-varesalg nulsats-betingelser | For hvert EU-varesalg med nulsats: tjek (a) køber har gyldigt momsnr. i andet EU-land, (b) varer transporteret, (c) indberettet på EU-salg uden moms (listesystemet). |
| 29 | EU-salg afstemning | Afstem EU-varesalg på momsangivelsen med EU-salg uden moms-listen. Flag forskelle. |
| 30 | Intrastat-afstemning | Krydstjek EU-varebevægelser på Intrastat mod momsangivelse og EU-salgsliste. |
| 31 | Reverse charge (ydelser) | For B2B grænseoverskridende ydelser: verificér at reverse charge er korrekt anvendt af modtageren. |
| 32 | Reverse charge (varer) | For EU-varekøb: verificér at køberen har foretaget korrekt reverse charge og indberettet. |
| 33 | Importmoms-genindvinding | Verificér at betalt importmoms er korrekt registreret og fradraget, og at toldværdi matcher faktura. |
| 34 | Eksportdokumentation | For nulstats-eksport uden for EU: verificér at tilstrækkelig dokumentation foreligger (tolddeklarationer, fragtsedler). |
| 35 | Leveringssted-bestemmelse | Verificér korrekt bestemmelse af leveringssted for ydelser (B2B: kundens lokation, B2C: leverandørens). |
| 36 | Trekantshandel | For ABC-triangulering: verificér at forenklingsreglerne er korrekt anvendt. |
| 37 | Ikke-EU leverandør reverse charge | Verificér at køb fra ikke-EU leverandører uden moms er korrekt reverse charged. |
| 38 | Udenlandsk momsrefusion | Verificér at tilbagesøgning af moms i andre EU-lande (8./13. direktiv) er komplet og rettidig. |

## Kategori 5: Timing & Periodetest (8 tests)

| # | Test | Beskrivelse |
|---|------|-------------|
| 39 | Momsperiode-allokering | Verificér at hver transaktion er allokeret til korrekt momsperiode baseret på leveringstidspunkt. |
| 40 | Forsinket fakturabogføring | Identificér leverandørfakturaer bogført >60 dage efter fakturadato. Kan indikere forkert periodeplacering. |
| 41 | Periodeafslutning cut-off | Analysér transaktioner bogført i de sidste/første dage af en momsperiode. Flag potentiel periodemanipulation. |
| 42 | Kreditnota-timing | Verificér at kreditnotaer indberettes i korrekt momsperiode. Flag sene kreditnotaer. |
| 43 | Kontantmetode-compliance | For virksomheder på kontantmetoden: verificér at moms afregnes baseret på betalingsdato, ikke fakturadato. |
| 44 | Rettidig momsindberetning | Tjek at momsangivelser er indsendt rettidigt. Identificér mønstre af for sen indberetning. |
| 45 | Korrigerende angivelser | Identificér og analysér alle rettelsesangivelser. Flag hyppige korrektioner. |
| 46 | Periodisering vs. fakturametode | Verificér at momsafregningsmetoden er konsistent og matcher registrering hos Skattestyrelsen. |

## Kategori 6: Leverandør- & Kundevalidering (8 tests)

| # | Test | Beskrivelse |
|---|------|-------------|
| 47 | Leverandør momsstatus | Verificér at alle leverandører med momsfradrag er gyldigt momsregistrerede. |
| 48 | Sovende leverandør | Identificér leverandører uden aktivitet i >12 måneder der pludselig har nye fakturaer. |
| 49 | Leverandør bankkontoændring | Flag leverandører med nyligt ændrede bankoplysninger kombineret med nye fakturaer (svindelindikator). |
| 50 | Dublet i stamdata | Find potentielle dubletter i leverandør-/kunderegistre (samme adresse, bankkonto, lignende navne). |
| 51 | Nærtstående parter | Flag transaktioner mellem enheder med fælles ejerskab, ledelse eller adresse. |
| 52 | Skuffeselskab-indikatorer | Flag nyregistrerede leverandører uden historik, fast adresse eller medarbejdere. |
| 53 | Momsgruppe-konsistens | Verificér at kunder i en momsgruppe behandles korrekt (ingen moms på interne leverancer). |
| 54 | Leverandørland vs. momsbehandling | Krydstjek leverandørens land mod momsbehandling. Flag dansk moms på udenlandske leverandører. |

## Kategori 7: Beløbs- & Tærskeltests (8 tests)

| # | Test | Beskrivelse |
|---|------|-------------|
| 55 | Registreringsgrænse | Overvåg kumuleret omsætning mod momsregistreringsgrænser i hver jurisdiktion. |
| 56 | De minimis delvis fradrag | For delvist momsfritagne: verificér om total momsfrit input er under bagatelgrænsen. |
| 57 | Store/usædvanlige transaktioner | Flag transaktioner over en væsentlighedsgrænse (top 1% efter værdi). |
| 58 | Runde beløb | Flag fakturaer med mistænkeligt runde beløb (fx præcis 100.000) der kan indikere estimerede fakturaer. |
| 59 | Lige-under-grænsetest | Identificér beløb der klynger sig lige under indberetningsgrænser (indikerer bevidst strukturering). |
| 60 | Negativ moms / overdrevent refusion | Flag perioder hvor indgående moms markant overstiger udgående moms. Skattestyrelsens primære trigger. |
| 61 | Uforholdsmæssig inputmoms-ratio | Sammenlign input/output moms-ratio med historik og branchenormer. Flag væsentlige afvigelser. |
| 62 | Forenklet faktura-grænse | Verificér at forenklede fakturaer kun udstedes under beløbsgrænsen. |

## Kategori 8: Statistisk Anomalidetektion (7 tests)

| # | Test | Beskrivelse |
|---|------|-------------|
| 63 | Benfords lov (1. ciffer) | Anvend Benfords lov på første ciffer af fakturabeløb. Flag datasets med afvigende cifferfordeling. |
| 64 | Benfords lov (2 første cifre) | Udvidet Benford-analyse til de to første cifre for finere anomalidetektion. |
| 65 | Outlier-detektion (Z-score) | Beregn statistiske outliers i transaktionsbeløb. Undersøg transaktioner >3 standardafvigelser. |
| 66 | Sæsonmønster-anomali | Sammenlign momsmønstre med samme perioder i tidligere år. Flag usædvanlige spikes eller fald. |
| 67 | Trendbrud-analyse | Anvend tidsserieanalyse på månedlige momsbeløb for at detektere strukturelle brud. |
| 68 | Stratificering / aldersanalyse | Stratificér transaktioner i størrelsesbånd og sammenlign fordelingen med tidligere perioder. |
| 69 | Peer/branche-sammenligning | Sammenlign virksomhedens momsnøgletal med branchenormer (Skattestyrelsens kerneværktøj). |

## Kategori 9: Reverse Charge & Selvangivelse (6 tests)

| # | Test | Beskrivelse |
|---|------|-------------|
| 70 | Indenlandsk reverse charge sektor | For sektorer med indenlandsk reverse charge (byggeri, elektronik, energi): verificér korrekt anvendelse. |
| 71 | Reverse charge symmetri | Verificér at hver reverse charge-postering har matchende udgående og indgående moms. |
| 72 | Manglende reverse charge | Scan købsfakturaer fra udenlandske leverandører med 0% moms og verificér at reverse charge er foretaget. |
| 73 | Fejlagtig reverse charge | Identificér transaktioner hvor reverse charge fejlagtigt er anvendt på indenlandske leverancer. |
| 74 | Byggebranche reverse charge | Specifik for byggebranchen: verificér at leverandørstatus og ydelsestype er korrekt vurderet. |
| 75 | Reverse charge på importerede ydelser | Verificér at alle importerede ydelser (B2B leveringssted = modtagers land) er korrekt reverse charged. |

## Kategori 10: Indgående/Udgående Moms Afstemning (8 tests)

| # | Test | Beskrivelse |
|---|------|-------------|
| 76 | Finans-til-momsangivelse | Afstem udgående/indgående moms i finansen med beløb på momsangivelsen. Flag forskelle. |
| 77 | Omsætning-til-udgående-moms | Beregn forventet udgående moms fra omsætning × sats. Sammenlign med faktisk indberettet. |
| 78 | Varekøb-til-indgående-moms | Afstem samlede køb med samlet indgående momsfradrag. Verificér effektiv inputmomssats. |
| 79 | Momskontosaldo | Verificér at momskontosaldo ved periodens slutning = skyldigt/tilgodehavende på momsangivelsen. |
| 80 | Tab på debitorer-moms | Verificér at momsregulering for tab på debitorer opfylder betingelser (>6 mdr., afskrevet, debitor notificeret). |
| 81 | Investeringsgode-regulering | For kapitalgoder: verificér at momsreguleringsforpligtelsen (5/10 år) beregnes korrekt årligt. |
| 82 | Repræsentation & ikke-fradrag | Verificér at moms på ikke-fradragsberettigede udgifter (repræsentation, personlige udgifter) er blokeret. |
| 83 | Delvis fradragsret årsregulering | For delvist momsfritagne: verificér at den foreløbige fradragsprocent er reguleret ved årsafslutning. |

## Kategori 11: Svindeldetektion & Karrusel/MTIC (10 tests)

| # | Test | Beskrivelse |
|---|------|-------------|
| 84 | Karruselmønster | Identificér cirkulære handelsmønstre. Skattestyrelsens primære momskarrusel-metode. |
| 85 | Missing trader-profil | Flag nyregistrerede virksomheder med store momstilgodehavender, ingen ansatte, ingen fast adresse. |
| 86 | Hurtig handelscyklus | Flag varer købt og solgt inden for timer/dage med minimal avance — karruselsignal. |
| 87 | Anomal prissætning | Sammenlign transaktionspriser med markedspriser. Flag væsentlige afvigelser. |
| 88 | Fakturaflow vs. vareflow | Sammenlign fakturastrøm med fysisk varestrøm. Flag grænseoverskridende fakturaer uden varebevægelse. |
| 89 | Momsrefusionshastighed | Flag virksomheder der systematisk søger momsrefusion i hver periode med stigende beløb. |
| 90 | Netværksanalyse | Map transaktionsnetværk mellem momsregistrerede enheder for at identificere kunstige kæder. |
| 91 | Kontrahandel | Identificér virksomheder der både er leverandør og kunde til samme modpart. |
| 92 | Marginkompression | Analysér avancer i forsyningskæden. Flag kæder med ubetydelige avancer. |
| 93 | Pludselig brancheskift | Flag virksomheder der pludselig ændrer branche til en sektor forbundet med momssvindel. |

## Kategori 12: E-handel, Digitale Ydelser & Særordninger (7 tests)

| # | Test | Beskrivelse |
|---|------|-------------|
| 94 | OSS/IOSS registreringsgrænse | For e-handel: verificér at EUR 10.000 grænsen overvåges og registrering foretages. |
| 95 | Digitale ydelser leveringssted | For B2C digitale ydelser: verificér at moms beregnes ud fra kundens lokation med lokal sats. |
| 96 | Markedsplads deemed supplier | Hvor online markedsplads er deemed supplier: verificér korrekt momsafregning. |
| 97 | Lavværdi-import (IOSS) | For importerede varer ≤EUR 150: verificér at IOSS er korrekt anvendt. |
| 98 | Udenlandsk e-handel | Verificér at ikke-danske webshops der sælger til danske forbrugere er korrekt momsregistrerede. |
| 99 | Brugtmomsordning | For brugte varer, kunst, antikviteter: verificér at brugtmomsordningen er korrekt anvendt. |
| 100 | Rejsebureauordning (TOMS) | Verificér at rejsebureauer beregner moms korrekt kun på avancen. |

## Bonus: Skattestyrelsen-Specifikke Digitale Kontroller

| # | Test | Beskrivelse |
|---|------|-------------|
| 101 | Digital risikoscore | Machine learning-baseret scoring der kombinerer risikoindikatorer med adfærdsindsigter. |
| 102 | Digitale stopklodser | Automatiske blokering af momsrefusion ved høj risikoscore — udløst næsten 8 mio. gange siden 2020. |
| 103 | Nyregistrering-screening | Automatisk screening af nye momsregistreringer for potentielle svindelvirksomheder. |
