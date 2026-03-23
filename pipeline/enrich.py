"""Enrich records with PSC/NAICS codes from individual award detail endpoint."""

import logging
from .api_client import fetch_award_detail

logger = logging.getLogger(__name__)


def enrich_missing_details(
    records: list[dict],
    existing_lookup: dict[str, dict] | None = None,
) -> list[dict]:
    """
    For records missing PSC or NAICS codes, fetch individual award detail.

    If existing_lookup is provided (keyed by Award ID), skip awards that
    already have codes populated from a prior run.
    """
    enriched = 0
    skipped = 0
    failed = 0

    for i, record in enumerate(records):
        award_id = record.get("Award ID", "")
        internal_id = record.get("generated_internal_id", "")

        # Already has codes
        if record.get("psc_code") and record.get("naics_code"):
            continue

        # Check existing data from prior run
        if existing_lookup and award_id in existing_lookup:
            existing = existing_lookup[award_id]
            if existing.get("psc_code"):
                record["psc_code"] = existing["psc_code"]
            if existing.get("naics_code"):
                record["naics_code"] = existing["naics_code"]
            skipped += 1
            continue

        if not internal_id:
            continue

        detail = fetch_award_detail(internal_id)
        if not detail:
            failed += 1
            continue

        # Extract PSC and NAICS from the detail response
        tx = detail.get("latest_transaction_contract_data") or {}
        psc = tx.get("product_or_service_code")
        naics = tx.get("naics")

        if psc:
            record["psc_code"] = psc
        if naics:
            record["naics_code"] = naics

        enriched += 1

        if (enriched + skipped + failed) % 50 == 0:
            logger.info(
                "Enrichment progress: %d enriched, %d from cache, %d failed (of %d total)",
                enriched, skipped, failed, len(records),
            )

    logger.info(
        "Enrichment complete: %d enriched, %d from cache, %d failed.",
        enriched, skipped, failed,
    )
    return records
