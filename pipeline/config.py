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

# USASpending sub-agency name -> EIS dashboard agency code
AGENCY_CODE_MAP = {
    "Bureau of Land Management": "BLM",
    "Forest Service": "USFS",
    "Bureau of Reclamation": "BR",
    "Department of Energy": "DOE",
    "Department of the Navy": "USN",
    "Department of the Air Force": "USAF",
    "Department of the Army": "USACE",
    "National Park Service": "NPS",
    "Bureau of Ocean Energy Management": "BOEM",
    "National Highway Traffic Safety Administration": "NHTSA",
    "Federal Energy Regulatory Commission": "FERC",
    "National Aeronautics and Space Administration": "NASA",
    "U.S. Fish and Wildlife Service": "USFWS",
    "Nuclear Regulatory Commission": "NRC",
    "Federal Aviation Administration": "FAA",
    "Federal Highway Administration": "FHWA",
    "Federal Railroad Administration": "FRA",
    "Animal and Plant Health Inspection Service": "APHIS",
    "National Oceanic and Atmospheric Administration": "NOAA",
    "U.S. Customs and Border Protection": "CBP",
    "Public Buildings Service": "GSA",
    "Office of Surface Mining, Reclamation and Enforcement": "OSM",
    "Federal Transit Administration": "FTA",
    "Bureau of Indian Affairs": "BIA",
    "Department of Veterans Affairs": "VA",
    "Agency for International Development": "USAID",
    "Bonneville Power Administration": "BPA",
    "Western Area Power Administration": "WAPA",
}
