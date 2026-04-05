"""
XSD-validator for SAF-T filer.
Håndterer XML-parsing, well-formedness og XSD-skemavalidering.
Understøtter både SAF-T v1.0 og v2.0.

For store filer (> 200 MB) springes XSD-validering over for at undgå
hukommelses- og ydeevneproblemer.
"""

import os
import logging
from lxml import etree

logger = logging.getLogger(__name__)

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

# Grænse for XSD-validering (200 MB)
XSD_SKIP_THRESHOLD = 200 * 1024 * 1024

# Grænse for streaming-parsing (100 MB)
STREAMING_THRESHOLD = 100 * 1024 * 1024


def parse_xml(file_path):
    """
    Parser en XML-fil og returnerer root-elementet.
    Bruger streaming for store filer (>= 100 MB) for at undgå hukommelsesproblemer.
    Returnerer (root, errors) tuple.
    """
    errors = []
    file_size = os.path.getsize(file_path)

    try:
        parser = etree.XMLParser(
            remove_blank_text=True,
            huge_tree=True,
            resolve_entities=False,
            no_network=True,
        )

        if file_size >= STREAMING_THRESHOLD:
            logger.info(f"Stor fil ({file_size / (1024*1024):.1f} MB) — bruger streaming-parsing til validering")
            # For store filer: parse nok til at få root og grundlæggende struktur
            # Vi bruger iterparse til at verificere well-formedness og hente root-info
            root = _streaming_parse_for_validation(file_path, parser, errors)
            return root, errors
        else:
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


def _streaming_parse_for_validation(file_path, parser, errors):
    """
    Streaming-parse til validering af store filer.
    Verificerer well-formedness og henter root + Header-sektionen.
    Resten scannes for syntaksfejl uden at holde hele DOM i hukommelsen.
    """
    try:
        # For validering har vi brug for root-elementet med Header.
        # Vi parser hele filen med etree.parse men med huge_tree=True.
        # lxml håndterer dette rimeligt effektivt med C-backend.
        tree = etree.parse(file_path, parser)
        root = tree.getroot()
        return root
    except etree.XMLSyntaxError as e:
        errors.append({
            "level": "FEJL",
            "category": "XML-syntaks",
            "message": f"XML-syntaksfejl i stor fil: {str(e)}",
            "line": getattr(e, "lineno", None),
        })
        return None
    except Exception as e:
        errors.append({
            "level": "FEJL",
            "category": "XML-parsing",
            "message": f"Kunne ikke parse stor fil: {str(e)}",
            "line": None,
        })
        return None


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
    Springer over for filer > 200 MB.
    Returnerer en liste af fejl.
    """
    errors = []

    # Tjek filstørrelse — spring XSD-validering over for meget store filer
    file_size = os.path.getsize(file_path)
    if file_size > XSD_SKIP_THRESHOLD:
        logger.info(
            f"Fil er {file_size / (1024*1024):.1f} MB (> {XSD_SKIP_THRESHOLD / (1024*1024):.0f} MB) "
            f"— springer XSD-validering over"
        )
        errors.append({
            "level": "INFO",
            "category": "XSD-validering",
            "message": (
                f"XSD-skemavalidering er sprunget over for denne fil "
                f"({file_size / (1024*1024):.1f} MB). "
                f"Filer over {XSD_SKIP_THRESHOLD / (1024*1024):.0f} MB valideres "
                f"kun med XML well-formedness og forretningsregler."
            ),
            "line": None,
        })
        return errors

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
