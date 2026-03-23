"""Query definitions for the three-layered USASpending search strategy."""

from .config import (
    CONTRACT_AWARD_TYPE_CODES,
    PSC_F110_PATH,
    NAICS_541620,
    SEARCH_FIELDS,
    DEFAULT_START_DATE,
)


def build_psc_f110_query(
    start_date: str = DEFAULT_START_DATE, end_date: str | None = None
) -> tuple[dict, list[str]]:
    """
    Query 1: All contracts with PSC code F110.
    Returns (filters_dict, fields_list).
    """
    filters = {
        "award_type_codes": CONTRACT_AWARD_TYPE_CODES,
        "psc_codes": {"require": [PSC_F110_PATH]},
        "time_period": [_time_period(start_date, end_date)],
    }
    return filters, SEARCH_FIELDS


def build_eis_keyword_query(
    start_date: str = DEFAULT_START_DATE, end_date: str | None = None
) -> tuple[dict, list[str]]:
    """
    Query 2: Keyword 'environmental impact statement' across all PSC codes.
    Returns (filters_dict, fields_list).
    """
    filters = {
        "award_type_codes": CONTRACT_AWARD_TYPE_CODES,
        "keywords": ["environmental impact statement"],
        "time_period": [_time_period(start_date, end_date)],
    }
    return filters, SEARCH_FIELDS


def build_ea_keyword_query(
    start_date: str = DEFAULT_START_DATE, end_date: str | None = None
) -> tuple[dict, list[str]]:
    """
    Query 3: Keyword 'environmental assessment' with NAICS 541620.
    Returns (filters_dict, fields_list).
    """
    filters = {
        "award_type_codes": CONTRACT_AWARD_TYPE_CODES,
        "keywords": ["environmental assessment"],
        "naics_codes": {"require": [NAICS_541620]},
        "time_period": [_time_period(start_date, end_date)],
    }
    return filters, SEARCH_FIELDS


def _time_period(start_date: str, end_date: str | None) -> dict:
    from datetime import date

    period = {"start_date": start_date}
    period["end_date"] = end_date or date.today().isoformat()
    return period
