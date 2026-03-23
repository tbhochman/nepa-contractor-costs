"""CLI entrypoint: orchestrates the full NEPA contractor cost data pipeline."""

import argparse
import csv
import json
import logging
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from .api_client import search_awards
from .classify import apply_exclusions, apply_manual_overrides, classify_document_type
from .deduplicate import deduplicate_awards
from .enrich import enrich_missing_details
from .queries import (
    build_ea_keyword_query,
    build_eis_keyword_query,
    build_psc_f110_query,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pull NEPA contractor cost data from USASpending.gov"
    )
    parser.add_argument(
        "--start-date",
        default="2007-10-01",
        help="Start date for query range (YYYY-MM-DD). Default: 2007-10-01 (API minimum)",
    )
    parser.add_argument(
        "--end-date",
        default=None,
        help="End date for query range (YYYY-MM-DD). Default: today",
    )
    parser.add_argument(
        "--skip-enrich",
        action="store_true",
        help="Skip individual award detail fetch (faster, but may miss PSC/NAICS codes)",
    )
    parser.add_argument(
        "--output-dir",
        default="data",
        help="Output directory for CSV/JSON files. Default: data/",
    )
    parser.add_argument(
        "--overrides-dir",
        default="overrides",
        help="Directory for manual overrides/exclusions. Default: overrides/",
    )
    return parser.parse_args()


def load_existing_data(output_dir: Path) -> dict[str, dict]:
    """Load existing CSV data for cache-based enrichment."""
    csv_path = output_dir / "nepa_contracts.csv"
    if not csv_path.exists():
        return {}

    lookup = {}
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            award_id = row.get("award_id", "")
            if award_id:
                lookup[award_id] = row
    logger.info("Loaded %d existing records for enrichment cache.", len(lookup))
    return lookup


def normalize_record(raw: dict) -> dict:
    """Normalize a raw API result into our standard field names."""
    # Records from the PSC F110 query are known to be F110 even without
    # the individual award detail fetch.
    source_query = raw.get("_source_query", "")
    psc_code = raw.get("psc_code", "")
    if not psc_code and source_query == "psc_f110":
        psc_code = "F110"

    return {
        "award_id": raw.get("Award ID", ""),
        "description": raw.get("Description", ""),
        "award_amount": raw.get("Award Amount"),
        "awarding_agency": raw.get("Awarding Agency", ""),
        "awarding_sub_agency": raw.get("Awarding Sub Agency", ""),
        "recipient_name": raw.get("Recipient Name", ""),
        "start_date": raw.get("Start Date", ""),
        "end_date": raw.get("End Date", ""),
        "contract_award_type": raw.get("Contract Award Type", ""),
        "generated_internal_id": raw.get("generated_internal_id", ""),
        "psc_code": psc_code,
        "naics_code": raw.get("naics_code", ""),
    }


def compute_derived_fields(records: list[dict]) -> list[dict]:
    """Add fiscal_year and duration_days."""
    for record in records:
        # Fiscal year from start date
        start = record.get("start_date", "")
        if start:
            try:
                start_dt = datetime.strptime(start, "%Y-%m-%d")
                # Federal fiscal year: Oct 1 starts the next FY
                fy = start_dt.year + 1 if start_dt.month >= 10 else start_dt.year
                record["fiscal_year"] = fy
            except ValueError:
                record["fiscal_year"] = None
        else:
            record["fiscal_year"] = None

        # Duration
        end = record.get("end_date", "")
        if start and end:
            try:
                start_dt = datetime.strptime(start, "%Y-%m-%d")
                end_dt = datetime.strptime(end, "%Y-%m-%d")
                record["duration_days"] = (end_dt - start_dt).days
            except ValueError:
                record["duration_days"] = None
        else:
            record["duration_days"] = None

    return records


def write_outputs(records: list[dict], output_dir: Path) -> None:
    """Write CSV, JSON, and metadata files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # CSV
    csv_path = output_dir / "nepa_contracts.csv"
    output_fields = [
        "award_id", "generated_internal_id", "description", "award_amount",
        "awarding_agency", "awarding_sub_agency", "recipient_name",
        "start_date", "end_date", "duration_days", "contract_award_type",
        "psc_code", "naics_code", "document_type", "fiscal_year",
    ]
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=output_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)
    logger.info("Wrote %d records to %s", len(records), csv_path)

    # JSON for dashboard
    json_path = output_dir / "nepa_contracts.json"
    json_records = []
    for r in records:
        out = {k: r.get(k) for k in output_fields}
        # Ensure award_amount is numeric
        if out["award_amount"] is not None:
            try:
                out["award_amount"] = float(out["award_amount"])
            except (ValueError, TypeError):
                out["award_amount"] = None
        json_records.append(out)

    json_data = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "record_count": len(json_records),
        "records": json_records,
    }
    with open(json_path, "w") as f:
        json.dump(json_data, f, indent=2)
    logger.info("Wrote %d records to %s", len(json_records), json_path)

    # Metadata
    meta_path = output_dir / "metadata.json"
    doc_type_counts = {}
    for r in records:
        dt = r.get("document_type", "UNKNOWN")
        doc_type_counts[dt] = doc_type_counts.get(dt, 0) + 1

    agency_counts = {}
    for r in records:
        ag = r.get("awarding_agency", "Unknown")
        agency_counts[ag] = agency_counts.get(ag, 0) + 1

    metadata = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "record_count": len(records),
        "document_type_counts": doc_type_counts,
        "top_agencies": dict(
            sorted(agency_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        ),
    }
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
    logger.info("Wrote metadata to %s", meta_path)


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    overrides_dir = Path(args.overrides_dir)

    logger.info("Starting NEPA contractor cost data pipeline...")
    logger.info("Date range: %s to %s", args.start_date, args.end_date or "today")

    # Step 1: Run three layered queries
    all_records = []

    logger.info("Query 1/3: PSC F110 contracts...")
    filters, fields = build_psc_f110_query(args.start_date, args.end_date)
    for record in search_awards(filters, fields):
        record["_source_query"] = "psc_f110"
        all_records.append(record)
    logger.info("Query 1 returned %d records.", len([r for r in all_records if r["_source_query"] == "psc_f110"]))

    logger.info("Query 2/3: Keyword 'environmental impact statement'...")
    filters, fields = build_eis_keyword_query(args.start_date, args.end_date)
    for record in search_awards(filters, fields):
        record["_source_query"] = "eis_keyword"
        all_records.append(record)
    logger.info("Query 2 returned %d records.", len([r for r in all_records if r["_source_query"] == "eis_keyword"]))

    logger.info("Query 3/3: Keyword 'environmental assessment' + NAICS 541620...")
    filters, fields = build_ea_keyword_query(args.start_date, args.end_date)
    for record in search_awards(filters, fields):
        record["_source_query"] = "ea_keyword"
        all_records.append(record)
    logger.info("Query 3 returned %d records.", len([r for r in all_records if r["_source_query"] == "ea_keyword"]))

    logger.info("Total raw records: %d", len(all_records))

    # Step 2: Deduplicate
    deduped = deduplicate_awards(all_records)

    # Step 3: Normalize field names
    normalized = [normalize_record(r) for r in deduped]

    # Step 4: Enrich missing PSC/NAICS (optional)
    if not args.skip_enrich:
        existing = load_existing_data(output_dir)
        # Remap existing data keys to match raw field names for enrichment
        existing_mapped = {}
        for k, v in existing.items():
            existing_mapped[k] = v
        normalized = enrich_missing_details(normalized, existing_mapped)
    else:
        logger.info("Skipping enrichment (--skip-enrich).")

    # Step 5: Classify document type
    for record in normalized:
        record["document_type"] = classify_document_type(
            record.get("description"), record.get("psc_code")
        )

    # Step 6: Apply manual overrides and exclusions
    # Remap Award ID key for override functions
    for record in normalized:
        record["Award ID"] = record["award_id"]

    normalized = apply_manual_overrides(
        normalized, overrides_dir / "manual_classifications.csv"
    )
    normalized = apply_exclusions(
        normalized, overrides_dir / "excluded_awards.csv"
    )

    # Step 7: Filter to EIS and EA only
    before_filter = len(normalized)
    normalized = [r for r in normalized if r.get("document_type") in ("EIS", "EA")]
    logger.info("Filtered to EIS/EA: %d -> %d records", before_filter, len(normalized))

    # Step 8: Compute derived fields
    normalized = compute_derived_fields(normalized)

    # Step 9: Write outputs
    write_outputs(normalized, output_dir)

    # Summary
    doc_types = {}
    for r in normalized:
        dt = r.get("document_type", "UNKNOWN")
        doc_types[dt] = doc_types.get(dt, 0) + 1
    logger.info("Final dataset: %d records", len(normalized))
    for dt, count in sorted(doc_types.items()):
        logger.info("  %s: %d", dt, count)


if __name__ == "__main__":
    main()
