"""USASpending.gov API client with pagination and retry logic."""

import time
import logging
from typing import Iterator

import requests

from .config import (
    SPENDING_BY_AWARD_URL,
    AWARD_DETAIL_URL,
    PAGE_SIZE,
    DETAIL_FETCH_DELAY_SECONDS,
)

logger = logging.getLogger(__name__)

SESSION = requests.Session()
SESSION.headers.update({"Content-Type": "application/json"})

MAX_RETRIES = 3
RETRY_BACKOFF = 2  # seconds, doubles each retry


def _post_with_retry(url: str, payload: dict) -> dict:
    """POST with exponential backoff retry."""
    for attempt in range(MAX_RETRIES):
        try:
            resp = SESSION.post(url, json=payload, timeout=60)
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError) as e:
            wait = RETRY_BACKOFF * (2 ** attempt)
            if attempt < MAX_RETRIES - 1:
                logger.warning(
                    "Request failed (attempt %d/%d): %s. Retrying in %ds...",
                    attempt + 1, MAX_RETRIES, e, wait,
                )
                time.sleep(wait)
            else:
                logger.error("Request failed after %d attempts: %s", MAX_RETRIES, e)
                raise


def _get_with_retry(url: str) -> dict:
    """GET with exponential backoff retry."""
    for attempt in range(MAX_RETRIES):
        try:
            resp = SESSION.get(url, timeout=60)
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError) as e:
            wait = RETRY_BACKOFF * (2 ** attempt)
            if attempt < MAX_RETRIES - 1:
                logger.warning(
                    "Request failed (attempt %d/%d): %s. Retrying in %ds...",
                    attempt + 1, MAX_RETRIES, e, wait,
                )
                time.sleep(wait)
            else:
                logger.error("Request failed after %d attempts: %s", MAX_RETRIES, e)
                raise


def search_awards(filters: dict, fields: list[str]) -> Iterator[dict]:
    """
    Search awards via POST /search/spending_by_award/ with automatic pagination.

    Yields individual award result dicts.
    """
    page = 1
    total_fetched = 0

    while True:
        payload = {
            "filters": filters,
            "fields": fields,
            "limit": PAGE_SIZE,
            "page": page,
            "subawards": False,
            "order": "desc",
            "sort": "Award Amount",
        }

        data = _post_with_retry(SPENDING_BY_AWARD_URL, payload)
        results = data.get("results", [])

        if not results:
            break

        for record in results:
            yield record
            total_fetched += 1

        page_metadata = data.get("page_metadata", {})
        has_next = page_metadata.get("hasNext", False)

        if total_fetched % 500 == 0 or not has_next:
            logger.info(
                "Fetched %d records so far (page %d)...", total_fetched, page
            )

        if not has_next:
            break

        page += 1

    logger.info("Search complete: %d total records.", total_fetched)


def fetch_award_detail(internal_id: str) -> dict | None:
    """
    Fetch full award detail via GET /awards/{generated_internal_id}/.

    Returns the award data dict, or None on error.
    Caller is responsible for rate limiting between calls.
    """
    url = f"{AWARD_DETAIL_URL}{internal_id}/"
    try:
        data = _get_with_retry(url)
        time.sleep(DETAIL_FETCH_DELAY_SECONDS)
        return data
    except Exception as e:
        logger.warning("Failed to fetch detail for %s: %s", internal_id, e)
        return None
