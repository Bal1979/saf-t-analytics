"""
Rapportgenerering for SAF-T validering.
Samler alle valideringsresultater i en struktureret rapport.
Understøtter SAF-T v1.0 og v2.0.
"""

from validator.xsd_validator import validate_xml
from validator.business_rules import validate_business_rules
from validator.fix_suggestions import enrich_with_suggestions


def generate_report(file_path, saft_version=None):
    """
    Kør fuld validering og generer en rapport.
    saft_version: "1.0" eller "2.0". Hvis None, auto-detekteres fra filen.
    Returnerer et dict med alle resultater.
    """
    report = {
        "file": file_path,
        "sections": {},
        "errors": [],
        "warnings": [],
        "info": [],
        "summary": {},
    }

    # Trin 1: XML-validering + XSD-skemavalidering
    root, namespace, detected_version, xml_errors = validate_xml(file_path, saft_version)
    report["saft_version"] = detected_version or saft_version or "ukendt"
    report["errors"].extend([e for e in xml_errors if e["level"] == "FEJL"])
    report["warnings"].extend([e for e in xml_errors if e["level"] == "ADVARSEL"])
    report["info"].extend([e for e in xml_errors if e["level"] == "INFO"])

    # Hvis XML ikke kunne parses, stop her
    if root is None:
        report["summary"] = _summarize(report)
        return report

    # Gem metadata
    report["namespace"] = namespace or "Ingen namespace fundet"

    # Trin 2: Forretningsregler (versionsafhængige)
    effective_version = detected_version or saft_version or "2.0"
    business_errors = validate_business_rules(root, namespace, effective_version)
    report["errors"].extend([e for e in business_errors if e["level"] == "FEJL"])
    report["warnings"].extend([e for e in business_errors if e["level"] == "ADVARSEL"])

    # Trin 3: Berig med løsningsforslag
    enrich_with_suggestions(report["errors"])
    enrich_with_suggestions(report["warnings"])

    # Gruppér per sektion
    all_issues = report["errors"] + report["warnings"]
    sections = {}
    for issue in all_issues:
        cat = issue["category"].split(" > ")[0]
        if cat not in sections:
            sections[cat] = {"errors": 0, "warnings": 0, "issues": []}
        if issue["level"] == "FEJL":
            sections[cat]["errors"] += 1
        else:
            sections[cat]["warnings"] += 1
        sections[cat]["issues"].append(issue)

    report["sections"] = sections
    report["summary"] = _summarize(report)

    return report


def _summarize(report):
    """Opsummér rapporten."""
    total_errors = len(report["errors"])
    total_warnings = len(report["warnings"])
    version = report.get("saft_version", "ukendt")

    if total_errors == 0 and total_warnings == 0:
        status = "GYLDIG"
        message = f"SAF-T filen er gyldig (v{version}). Ingen fejl eller advarsler fundet."
    elif total_errors == 0:
        status = "GYLDIG MED ADVARSLER"
        message = f"SAF-T filen (v{version}) er strukturelt gyldig, men har {total_warnings} advarsel(er)."
    else:
        status = "UGYLDIG"
        message = f"SAF-T filen (v{version}) har {total_errors} fejl og {total_warnings} advarsel(er)."

    return {
        "status": status,
        "message": message,
        "saft_version": version,
        "total_errors": total_errors,
        "total_warnings": total_warnings,
        "total_issues": total_errors + total_warnings,
    }
