"""
XSD-validator for SAF-T filer.
Håndterer XML-parsing, well-formedness og XSD-skemavalidering.
Understøtter både SAF-T v1.0 og v2.0.
"""

import os
from lxml import etree


# Kendte SAF-T namespaces
NAMESPACES = {
    "oecd": "urn:OECD:StandardAuditFile-Taxation/2.00",
    "dk": "urn:StandardAuditFile-Taxation-Financial:DK",
}

# Sti til schemas-mappe
SCHEMAS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "schemas")

# XSD-filer per version
XSD_FILES = {
    "1.0": "Danish_SAF-T_Financial_Schema_v_1_0.xsd",
    "2.0": "Danish_SAF-T_Financial_Schema_v_2_0.xsd",
}


def parse_xml(file_path):
    """
    Parser en XML-fil og returnerer root-elementet.
    Returnerer (root, errors) tuple.
    """
    errors = []

    try:
        parser = etree.XMLParser(remove_blank_text=True, huge_tree=True, resolve_entities=False, no_network=True)
        tree = etree.parse(file_path, parser)
        root = tree.getroot()
        return root, errors

    except etree.XMLSyntaxError as e:
        errors.append({
            "level": "FEJL",
            "category": "XML-syntaks",
            "message": f"XML-syntaksfejl: {str(e)}",
            "line": getattr(e, "lineno", None),
        })
        return None, errors

    except Exception as e:
        errors.append({
            "level": "FEJL",
            "category": "XML-parsing",
            "message": f"Kunne ikke parse filen: {str(e)}",
            "line": None,
        })
        return None, errors


def detect_namespace(root):
    """Detektér hvilken SAF-T namespace filen bruger."""
    ns = root.tag.split("}")[0].strip("{") if "}" in root.tag else ""
    return ns


def detect_version_from_file(root, ns):
    """Forsøg at detektere SAF-T version fra filens AuditFileVersion-element."""
    if ns:
        version_el = root.find(f"{{{ns}}}Header/{{{ns}}}AuditFileVersion")
    else:
        version_el = root.find("Header/AuditFileVersion")

    if version_el is not None and version_el.text:
        return version_el.text.strip()
    return None


def validate_against_xsd(file_path, saft_version):
    """
    Validér en XML-fil mod det korrekte XSD-skema baseret på version.
    Returnerer en liste af fejl.
    """
    errors = []

    xsd_filename = XSD_FILES.get(saft_version)
    if not xsd_filename:
        errors.append({
            "level": "ADVARSEL",
            "category": "XSD-skema",
            "message": f"Ukendt SAF-T version '{saft_version}'. "
                       f"Understøttede versioner: {', '.join(XSD_FILES.keys())}.",
            "line": None,
        })
        return errors

    xsd_path = os.path.join(SCHEMAS_DIR, xsd_filename)

    if not os.path.exists(xsd_path):
        errors.append({
            "level": "ADVARSEL",
            "category": "XSD-skema",
            "message": f"XSD-skema '{xsd_filename}' ikke fundet i schemas-mappen. "
                       f"XSD-validering springes over.",
            "line": None,
        })
        return errors

    try:
        secure_parser = etree.XMLParser(resolve_entities=False, no_network=True)
        xsd_doc = etree.parse(xsd_path, secure_parser)
        xsd_schema = etree.XMLSchema(xsd_doc)

        xml_doc = etree.parse(file_path, secure_parser)
        is_valid = xsd_schema.validate(xml_doc)

        if is_valid:
            errors.append({
                "level": "INFO",
                "category": "XSD-validering",
                "message": f"Filen validerer korrekt mod SAF-T v{saft_version} XSD-skema.",
                "line": None,
            })
        else:
            for error in xsd_schema.error_log:
                errors.append({
                    "level": "FEJL",
                    "category": "XSD-validering",
                    "message": str(error.message),
                    "line": error.line,
                })

    except etree.XMLSchemaParseError as e:
        errors.append({
            "level": "FEJL",
            "category": "XSD-skema",
            "message": f"Fejl i XSD-skema: {str(e)}",
            "line": None,
        })

    except Exception as e:
        errors.append({
            "level": "FEJL",
            "category": "XSD-validering",
            "message": f"XSD-valideringsfejl: {str(e)}",
            "line": None,
        })

    return errors


def validate_xml(file_path, saft_version=None):
    """
    Fuld XML-validering: parsing + XSD-skema.
    saft_version: "1.0" eller "2.0". Hvis None, auto-detekteres fra filen.
    Returnerer (root, namespace, detected_version, errors).
    """
    # Trin 1: Parse XML
    root, parse_errors = parse_xml(file_path)
    all_errors = list(parse_errors)

    if root is None:
        return None, None, saft_version, all_errors

    # Trin 2: Detektér namespace
    namespace = detect_namespace(root)

    # Trin 3: Basis XML-checks
    root_tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag
    if root_tag != "AuditFile":
        all_errors.append({
            "level": "FEJL",
            "category": "XML-struktur",
            "message": f"Root-elementet skal være 'AuditFile', men fandt '{root_tag}'.",
            "line": 1,
        })

    # Trin 4: Detektér version fra filen (hvis ikke angivet af brugeren)
    detected_version = detect_version_from_file(root, namespace)

    if saft_version is None:
        if detected_version:
            saft_version = detected_version
        else:
            saft_version = "2.0"  # Default til v2.0
            all_errors.append({
                "level": "ADVARSEL",
                "category": "Version",
                "message": "Kunne ikke detektere SAF-T version fra filen. Bruger v2.0 som standard.",
                "line": None,
            })

    # Tjek om brugerens valg matcher filens version
    if detected_version and saft_version != detected_version:
        all_errors.append({
            "level": "ADVARSEL",
            "category": "Version",
            "message": f"Du valgte SAF-T v{saft_version}, men filen angiver "
                       f"AuditFileVersion '{detected_version}'. "
                       f"Validerer mod v{saft_version} som valgt.",
            "line": None,
        })

    # Trin 5: XSD-validering
    xsd_errors = validate_against_xsd(file_path, saft_version)
    all_errors.extend(xsd_errors)

    return root, namespace, saft_version, all_errors
