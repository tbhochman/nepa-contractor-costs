"""EIS vs EA classification based on contract description text."""

import csv
import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Patterns checked in priority order: EIS first, then EA.
# If both match, EIS wins (an EIS contract may reference prior EAs).
EIS_PATTERNS = [
    re.compile(r"\benvironmental impact statement\b", re.IGNORECASE),
    re.compile(r"\bprogrammatic EIS\b", re.IGNORECASE),
    re.compile(r"\bsupplemental EIS\b", re.IGNORECASE),
    re.compile(r"\bdraft EIS\b", re.IGNORECASE),
    re.compile(r"\bfinal EIS\b", re.IGNORECASE),
    re.compile(r"\bDEIS\b"),
    re.compile(r"\bFEIS\b"),
    re.compile(r"\bPEIS\b"),
    re.compile(r"\bSEIS\b"),
    # Standalone "EIS" — case-sensitive, word boundary to avoid matching
    # words like "thEIS" or "EISenhower"
    re.compile(r"(?<![A-Za-z])EIS(?![A-Za-z])"),
]

EA_PATTERNS = [
    re.compile(r"\benvironmental assessment\b", re.IGNORECASE),
    # Standalone "EA" is risky (matches too many things), so only match
    # when preceded by NEPA-related context words
    re.compile(r"\b(?:draft|final|supplemental|programmatic)\s+EA\b", re.IGNORECASE),
]

# Phrases that contain "environmental assessment" but refer to non-NEPA work
# (e.g., health risk assessment, chemical assessment, scientific assessment).
EA_FALSE_POSITIVE_PATTERNS = [
    re.compile(r"\bhealth and environmental assessment\b", re.IGNORECASE),
    re.compile(r"\bhealth.{0,20}environmental assessment\b", re.IGNORECASE),
    re.compile(r"\bscientific.{0,20}environmental assessment\b", re.IGNORECASE),
    re.compile(r"\brisk.{0,20}environmental assessment\b", re.IGNORECASE),
    re.compile(r"\benvironmental assessment.{0,20}documentation support\b", re.IGNORECASE),
    re.compile(r"\benvironmental assessment.{0,20}risk\b", re.IGNORECASE),
]


def classify_document_type(description: str | None, psc_code: str | None = None) -> str:
    """
    Classify a contract as EIS, EA, NEPA_SUPPORT, or UNKNOWN.

    Priority: EIS > EA > NEPA_SUPPORT (if PSC F110 but no keyword match).
    """
    if not description:
        if psc_code == "F110":
            return "NEPA_SUPPORT"
        return "UNKNOWN"

    # Check EIS patterns
    for pattern in EIS_PATTERNS:
        if pattern.search(description):
            return "EIS"

    # Check EA patterns — but filter out false positives first
    ea_match = any(p.search(description) for p in EA_PATTERNS)
    if ea_match:
        is_false_positive = any(p.search(description) for p in EA_FALSE_POSITIVE_PATTERNS)
        if not is_false_positive:
            return "EA"

    # PSC F110 but no specific document type matched
    if psc_code == "F110":
        return "NEPA_SUPPORT"

    return "UNKNOWN"


def apply_manual_overrides(
    records: list[dict], overrides_path: str | Path
) -> list[dict]:
    """
    Apply manual classification overrides from a CSV file.

    Override file format: award_id,classification,notes
    """
    overrides_path = Path(overrides_path)
    if not overrides_path.exists():
        return records

    overrides = {}
    with open(overrides_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            overrides[row["award_id"]] = row["classification"]

    if not overrides:
        return records

    applied = 0
    for record in records:
        award_id = record.get("Award ID", "")
        if award_id in overrides:
            record["document_type"] = overrides[award_id]
            applied += 1

    logger.info("Applied %d manual classification overrides.", applied)
    return records


def apply_exclusions(
    records: list[dict], exclusions_path: str | Path
) -> list[dict]:
    """
    Remove false-positive awards listed in the exclusions CSV.

    Exclusion file format: award_id,reason
    """
    exclusions_path = Path(exclusions_path)
    if not exclusions_path.exists():
        return records

    excluded_ids = set()
    with open(exclusions_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            excluded_ids.add(row["award_id"])

    if not excluded_ids:
        return records

    before = len(records)
    records = [r for r in records if r.get("Award ID", "") not in excluded_ids]
    logger.info("Excluded %d false-positive awards.", before - len(records))
    return records
