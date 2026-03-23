"""Match USASpending EIS contracts to actual EIS projects from the EIS dashboard."""

import csv
import json
import logging
import re
from pathlib import Path

from .config import AGENCY_CODE_MAP

logger = logging.getLogger(__name__)

# Words that appear in almost every NEPA contract description — not useful for matching
STOPWORDS = frozenset({
    "environmental", "impact", "statement", "eis", "draft", "final",
    "supplemental", "programmatic", "preparation", "prepare", "develop",
    "services", "support", "contract", "task", "order", "new", "the",
    "for", "of", "and", "to", "an", "a", "in", "at", "on", "igf",
    "ot", "ct", "cl", "other", "functions", "title", "project",
    "proposed", "national", "federal", "provide", "required",
    "architect", "engineer", "engineering", "review", "analysis",
    "plan", "management", "resource", "resources", "amendment",
})

# High confidence threshold for auto-match
HIGH_CONFIDENCE = 0.5
# Low confidence threshold — below this, no match
LOW_CONFIDENCE = 0.35


def _extract_keywords(text: str) -> set[str]:
    """Extract meaningful keywords from a text, stripping NEPA boilerplate."""
    # Remove IGF prefixes
    text = re.sub(r'IGF::.*?IGF\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'"', '', text)
    # Remove punctuation
    text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text)
    words = {w.lower() for w in text.split() if len(w) > 2 and w.lower() not in STOPWORDS}
    return words


def _score_match(contract_kw: set[str], eis_kw: set[str], same_agency: bool) -> float:
    """Score how well a contract's keywords match an EIS record's keywords."""
    if not contract_kw or not eis_kw:
        return 0.0
    overlap = contract_kw & eis_kw
    if not overlap:
        return 0.0
    # Weight toward contract keywords (which are fewer and more specific)
    score = len(overlap) / len(contract_kw)
    if same_agency:
        score += 0.1
    return score


def load_eis_dashboard(data_path: str | Path) -> list[dict]:
    """Load EIS records from the dashboard JSON export."""
    with open(data_path) as f:
        data = json.load(f)
    records = data.get("completed", []) + data.get("underway", [])
    logger.info("Loaded %d EIS dashboard records.", len(records))
    return records


def match_contracts_to_eis(
    contracts: list[dict],
    eis_records: list[dict],
    overrides_path: str | Path | None = None,
) -> list[dict]:
    """
    Match EIS contracts to actual EIS projects.

    Adds fields to each contract dict:
      - eis_title: matched EIS project name (or empty)
      - eis_agency: dashboard agency code
      - eis_noi_date, eis_feis_date, eis_rod_date: timeline dates
      - eis_duration_years: NOI to FEIS duration
      - eis_match_score: confidence score
      - eis_match_confidence: 'high', 'low', or 'none'
    """
    # Load manual overrides
    manual_overrides = {}
    if overrides_path and Path(overrides_path).exists():
        with open(overrides_path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                confirmed = row.get("confirmed_eis_title", "").strip()
                if confirmed:
                    manual_overrides[row["award_id"]] = confirmed
        if manual_overrides:
            logger.info("Loaded %d manual EIS match overrides.", len(manual_overrides))

    # Pre-compute EIS keywords and index by agency
    eis_by_agency: dict[str, list[tuple[dict, set]]] = {}
    eis_all: list[tuple[dict, set]] = []
    for e in eis_records:
        kw = _extract_keywords(e["n"])
        entry = (e, kw)
        eis_all.append(entry)
        eis_by_agency.setdefault(e["a"], []).append(entry)

    # Build title lookup for manual overrides
    eis_by_title = {e["n"]: e for e in eis_records}

    matched_high = 0
    matched_low = 0
    matched_override = 0
    unmatched = 0
    review_candidates = []

    for contract in contracts:
        if contract.get("document_type") != "EIS":
            _set_no_match(contract)
            continue

        award_id = contract.get("award_id", "")

        # Check manual override first
        if award_id in manual_overrides:
            override_title = manual_overrides[award_id]
            if override_title in eis_by_title:
                _apply_match(contract, eis_by_title[override_title], 1.0, "override")
                matched_override += 1
                continue
            elif override_title.upper() == "NONE":
                _set_no_match(contract)
                unmatched += 1
                continue

        desc = contract.get("description", "")
        c_kw = _extract_keywords(desc)

        if len(c_kw) < 2:
            _set_no_match(contract)
            unmatched += 1
            continue

        # Get agency code
        ag_name = contract.get("awarding_sub_agency") or contract.get("awarding_agency", "")
        ag_code = AGENCY_CODE_MAP.get(ag_name, "")

        # Score against same-agency candidates first, then all
        candidates = eis_by_agency.get(ag_code, []) if ag_code else eis_all

        best_score = 0.0
        best_eis = None
        for eis_rec, eis_kw in candidates:
            score = _score_match(c_kw, eis_kw, same_agency=True)
            if score > best_score:
                best_score = score
                best_eis = eis_rec

        # If no same-agency match, try cross-agency
        if best_score < LOW_CONFIDENCE and ag_code:
            for eis_rec, eis_kw in eis_all:
                score = _score_match(c_kw, eis_kw, same_agency=(eis_rec["a"] == ag_code))
                if score > best_score:
                    best_score = score
                    best_eis = eis_rec

        if best_score >= HIGH_CONFIDENCE and best_eis:
            _apply_match(contract, best_eis, best_score, "high")
            matched_high += 1
        elif best_score >= LOW_CONFIDENCE and best_eis:
            _apply_match(contract, best_eis, best_score, "low")
            matched_low += 1
            review_candidates.append({
                "award_id": award_id,
                "contract_description": desc[:120],
                "auto_match_eis_title": best_eis["n"][:120],
                "auto_match_score": f"{best_score:.2f}",
                "confirmed_eis_title": "",
                "notes": "",
            })
        else:
            _set_no_match(contract)
            unmatched += 1

    logger.info(
        "EIS matching: %d high-confidence, %d low-confidence, %d manual overrides, %d unmatched",
        matched_high, matched_low, matched_override, unmatched,
    )

    # Write review CSV (only new candidates not already in overrides)
    if review_candidates and overrides_path:
        _write_review_csv(review_candidates, overrides_path)

    return contracts


def build_eis_projects(contracts: list[dict]) -> dict:
    """Group matched contracts into EIS project summaries."""
    projects: dict[str, dict] = {}
    unmatched = []

    for c in contracts:
        if c.get("document_type") != "EIS":
            continue

        title = c.get("eis_title", "")
        if not title:
            unmatched.append(_contract_summary(c))
            continue

        if title not in projects:
            projects[title] = {
                "eis_title": title,
                "eis_agency": c.get("eis_agency", ""),
                "eis_noi_date": c.get("eis_noi_date", ""),
                "eis_feis_date": c.get("eis_feis_date", ""),
                "eis_rod_date": c.get("eis_rod_date", ""),
                "eis_duration_years": c.get("eis_duration_years"),
                "total_contractor_cost": 0,
                "contract_count": 0,
                "contracts": [],
            }

        amt = c.get("award_amount")
        try:
            amt = float(amt) if amt else 0
        except (ValueError, TypeError):
            amt = 0

        projects[title]["total_contractor_cost"] += amt
        projects[title]["contract_count"] += 1
        projects[title]["contracts"].append(_contract_summary(c))

    project_list = sorted(projects.values(), key=lambda p: p["total_contractor_cost"], reverse=True)

    return {
        "project_count": len(project_list),
        "unmatched_count": len(unmatched),
        "projects": project_list,
        "unmatched_contracts": unmatched,
    }


def _apply_match(contract: dict, eis: dict, score: float, confidence: str) -> None:
    contract["eis_title"] = eis["n"]
    contract["eis_agency"] = eis["a"]
    contract["eis_noi_date"] = eis.get("noi", "")
    contract["eis_feis_date"] = eis.get("feis", "")
    contract["eis_rod_date"] = eis.get("rod", "")
    contract["eis_duration_years"] = eis.get("df")
    contract["eis_match_score"] = round(score, 2)
    contract["eis_match_confidence"] = confidence


def _set_no_match(contract: dict) -> None:
    contract["eis_title"] = ""
    contract["eis_agency"] = ""
    contract["eis_noi_date"] = ""
    contract["eis_feis_date"] = ""
    contract["eis_rod_date"] = ""
    contract["eis_duration_years"] = None
    contract["eis_match_score"] = 0
    contract["eis_match_confidence"] = "none"


def _contract_summary(c: dict) -> dict:
    amt = c.get("award_amount")
    try:
        amt = float(amt) if amt else 0
    except (ValueError, TypeError):
        amt = 0
    return {
        "award_id": c.get("award_id", ""),
        "generated_internal_id": c.get("generated_internal_id", ""),
        "amount": amt,
        "contractor": c.get("recipient_name", ""),
        "description": c.get("description", ""),
        "start_date": c.get("start_date", ""),
        "end_date": c.get("end_date", ""),
    }


def _write_review_csv(candidates: list[dict], overrides_path: str | Path) -> None:
    """Write borderline matches to review CSV, preserving existing confirmed entries."""
    overrides_path = Path(overrides_path)
    existing_ids = set()

    if overrides_path.exists():
        with open(overrides_path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_ids.add(row.get("award_id", ""))

    new_candidates = [c for c in candidates if c["award_id"] not in existing_ids]
    if not new_candidates:
        return

    write_header = not overrides_path.exists() or overrides_path.stat().st_size == 0
    fields = ["award_id", "contract_description", "auto_match_eis_title",
              "auto_match_score", "confirmed_eis_title", "notes"]

    with open(overrides_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if write_header:
            writer.writeheader()
        writer.writerows(new_candidates)

    logger.info("Wrote %d new candidates to %s for review.", len(new_candidates), overrides_path)
