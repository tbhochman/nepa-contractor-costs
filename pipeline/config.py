"""Configuration constants for the NEPA contractor costs pipeline."""

API_BASE = "https://api.usaspending.gov/api/v2"
SPENDING_BY_AWARD_URL = f"{API_BASE}/search/spending_by_award/"
AWARD_DETAIL_URL = f"{API_BASE}/awards/"  # + {generated_unique_award_id}/

# Contract type codes
# A = BPA Call, B = Purchase Order, C = Delivery Order, D = Definitive Contract
CONTRACT_AWARD_TYPE_CODES = ["A", "B", "C", "D"]

# PSC code for NEPA services
PSC_F110_PATH = ["Service", "F", "F1", "F110"]

# NAICS code for Environmental Consulting Services
NAICS_541620 = "541620"

# Fields to request from spending_by_award
SEARCH_FIELDS = [
    "Award ID",
    "Description",
    "Award Amount",
    "Awarding Agency",
    "Awarding Sub Agency",
    "Recipient Name",
    "Start Date",
    "End Date",
    "Contract Award Type",
    "generated_internal_id",
]

# Default time range (FY2008 onward — API search minimum is 2007-10-01)
DEFAULT_START_DATE = "2007-10-01"

# API pagination
PAGE_SIZE = 100

# Rate limiting for individual award detail fetches
DETAIL_FETCH_DELAY_SECONDS = 0.25
