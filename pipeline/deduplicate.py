"""Deduplication of awards from overlapping queries."""

import logging

logger = logging.getLogger(__name__)


def deduplicate_awards(records: list[dict]) -> list[dict]:
    """
    Deduplicate by 'Award ID'. When duplicates exist (from overlapping
    queries), keep the record with the most populated fields.
    """
    seen: dict[str, dict] = {}

    for record in records:
        award_id = record.get("Award ID")
        if not award_id:
            continue

        if award_id not in seen:
            seen[award_id] = record
        else:
            existing = seen[award_id]
            existing_populated = sum(1 for v in existing.values() if v)
            new_populated = sum(1 for v in record.values() if v)
            if new_populated > existing_populated:
                seen[award_id] = record

    deduped = list(seen.values())
    removed = len(records) - len(deduped)
    if removed:
        logger.info("Deduplicated: %d records -> %d (removed %d duplicates)",
                     len(records), len(deduped), removed)
    return deduped
