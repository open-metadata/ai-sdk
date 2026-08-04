"""Deterministic seed-data generator for the banking demo.

Emits 38 CSV files under ``dbt/seeds/raw_*/`` that the dbt project + Redshift
``COPY`` pipeline consumes. Uses a fixed seed (42) so re-running produces
identical output (essential for stable dbt tests + reproducible demo runs).

Realism features:
  - Hour-of-day / day-of-week / monthly seasonality on transactions and auths
  - Triangular DOB distribution (peak age ~42)
  - ISO 13616 IBAN with mod-97 checksum + country-specific length
  - 8/11-char BIC/SWIFT codes
  - BIN-correct masked PAN per card product
  - Consumer-style email mix (gmail/yahoo/outlook/icloud/...)
  - IFRS 9 staging (1/2/3) + PD/LGD/EAD/ECL on loans
  - FICO ↔ DTI ↔ approval correlation in loan applications
  - Templated AML narratives by alert_type
  - Engineered fraud cluster + chargeback storm
  - atm_withdrawals / wire_transfers / ach_transfers linked to parent transactions
  - mobile_app_events.session_id constrained to same-customer web sessions

Usage:
    python scripts/generate_seed_data.py
"""

from __future__ import annotations

import argparse
import csv
import logging
import random
import string
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

from faker import Faker

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# noqa: E402 throughout — the sys.path setup above must precede this import.
from schema.registry import Column, Table, find_table  # noqa: E402

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------

SEED = 42
random.seed(SEED)
fake = Faker("en_US")
Faker.seed(SEED)


# ---------------------------------------------------------------------------
# Output paths
# ---------------------------------------------------------------------------

SEEDS_DIR = Path(__file__).resolve().parent.parent / "dbt" / "seeds"

RAW_SCHEMAS = {
    "raw_core_banking": [
        "customers", "customer_addresses", "customer_contacts",
        "branches", "employees", "accounts", "account_holders",
    ],
    "raw_transactions": [
        "transactions", "transaction_categories", "atm_withdrawals",
        "wire_transfers", "ach_transfers",
    ],
    "raw_cards": [
        "card_products", "cards", "card_authorizations",
        "card_disputes", "merchants",
    ],
    "raw_lending": [
        "loan_products", "loan_applications", "loans",
        "loan_payments", "collateral",
    ],
    "raw_risk": [
        "credit_scores", "kyc_checks", "aml_alerts",
        "sanctions_screening", "suspicious_activity_reports",
    ],
    "raw_wealth": [
        "investment_accounts", "securities", "holdings", "trades",
    ],
    "raw_digital": [
        "web_sessions", "mobile_app_events", "login_attempts",
    ],
    "raw_marketing": [
        "campaigns", "customer_segments", "customer_interactions",
    ],
}


# ---------------------------------------------------------------------------
# Time window: 12 months ending 2026-05-22 (today, per demo context)
# ---------------------------------------------------------------------------

END_DATE = date(2026, 5, 22)
START_DATE = END_DATE - timedelta(days=365)
RUN_TIMESTAMP = datetime(2026, 5, 22, 12, 0, 0)


# ---------------------------------------------------------------------------
# Scale dials
# ---------------------------------------------------------------------------

N_CUSTOMERS = 5_000
N_BRANCHES = 75
N_EMPLOYEES = 400
N_ACCOUNTS = 8_500
N_CARDS = 6_500
N_LOANS = 3_000
N_LOAN_APPS = 6_500
N_TXNS = 250_000
N_CARD_AUTHS = 120_000
N_ATM = 25_000
N_WIRES = 5_000
N_ACH = 35_000
N_AML = 2_000
N_SAR = 150
N_CREDIT_PULLS = 12_000
N_KYC = 6_500
N_SECURITIES = 150
N_HOLDINGS = 6_000
N_TRADES = 25_000
N_WEB_SESSIONS = 150_000
N_MOBILE_EVENTS = 250_000
N_LOGIN_ATTEMPTS = 400_000
N_CAMPAIGNS = 40
N_CUSTOMER_INTERACTIONS = 40_000
N_MERCHANTS = 600
# Fraud + chargeback engineered patterns
N_FRAUD_BURST_CUSTOMERS = 10        # customers with rapid card-auth burst
N_FRAUD_AUTHS_PER_BURST = 80        # auths within a 24h window
N_CHARGEBACK_STORM_MERCHANTS = 2    # merchants with disputed authorizations
N_CHARGEBACK_STORM_SIZE = 40        # disputes per storm merchant


# ---------------------------------------------------------------------------
# Lookup data (deterministic, small)
# ---------------------------------------------------------------------------

ACCOUNT_TYPES = [
    # (code, name, product_category)
    ("CHECKING",          "Personal Checking",         "deposit"),
    ("SAVINGS",           "Personal Savings",          "deposit"),
    ("MMA",               "Money Market Account",      "deposit"),
    ("CD",                "Certificate of Deposit",    "deposit"),
    ("BUSINESS_CHECKING", "Business Checking",         "deposit"),
    ("HELOC",             "Home Equity Line of Credit","credit"),
    ("AUTO_LOAN",         "Auto Loan",                 "credit"),
    ("MORTGAGE",          "Mortgage",                  "credit"),
]

TRANSACTION_CATEGORIES = [
    # (code, name, group, sign_hint)
    ("DEPOSIT",      "Deposit",         "income",   1),
    ("WITHDRAWAL",   "Withdrawal",      "outflow", -1),
    ("TRANSFER_IN",  "Transfer In",     "income",   1),
    ("TRANSFER_OUT", "Transfer Out",    "outflow", -1),
    ("PURCHASE",     "Purchase",        "outflow", -1),
    ("FEE",          "Fee",             "fee",     -1),
    ("INTEREST",     "Interest",        "income",   1),
    ("ATM",          "ATM Withdrawal",  "outflow", -1),
    ("WIRE",         "Wire",            "outflow", -1),
    ("ACH",          "ACH",             "outflow", -1),
    ("REVERSAL",     "Reversal",        "adjustment", 1),
    ("ADJUSTMENT",   "Adjustment",      "adjustment", 0),
]

LOAN_PRODUCTS = [
    # (code, name, product_class, term_months, base_rate_apr)
    ("MORTGAGE_30Y", "30-Year Fixed Mortgage",  "mortgage",     360, 0.0699),
    ("MORTGAGE_15Y", "15-Year Fixed Mortgage",  "mortgage",     180, 0.0625),
    ("AUTO_LOAN",    "Auto Loan",               "auto",          60, 0.0849),
    ("PERSONAL_LOAN","Personal Loan",           "personal",      48, 0.1199),
    ("HELOC",        "Home Equity LOC",         "heloc",        120, 0.0799),
    ("BUSINESS_LOAN","Business Loan",           "business",      84, 0.0899),
]

CARD_PRODUCTS = [
    # (code, name, product_class, annual_fee, credit_limit_band)
    ("DEBIT",            "Personal Debit Card",    "debit",   Decimal("0"),    None),
    ("CREDIT_BASIC",     "Cashback Credit",        "credit",  Decimal("0"),    "low"),
    ("CREDIT_REWARDS",   "Rewards Credit",         "credit",  Decimal("95"),   "mid"),
    ("CREDIT_PLATINUM",  "Platinum Credit",        "credit",  Decimal("495"),  "high"),
    ("BUSINESS_DEBIT",   "Business Debit",         "debit",   Decimal("0"),    None),
    ("PREPAID",          "Prepaid Card",           "prepaid", Decimal("0"),    None),
]

CUSTOMER_SEGMENTS = [
    # (code, name, description)
    ("MASS",            "Mass Market",          "Standard retail customers."),
    ("AFFLUENT",        "Mass Affluent",        "Affluent retail customers (~$100k+ liquid)."),
    ("HIGH_VALUE",      "High Value",           "High-value customers ($250k+ deposits)."),
    ("PRIVATE_BANKING", "Private Banking",      "Ultra HNW private banking clients."),
    ("BUSINESS_SMB",    "Small Business",       "Small-business banking clients."),
    ("BUSINESS_COMM",   "Commercial",           "Mid-market commercial clients."),
    ("STUDENT",         "Student",              "Student banking customers."),
    ("SENIOR",          "Senior",               "Senior customers (65+)."),
]

REGIONS = ["Northeast", "Southeast", "Midwest", "Southwest", "West"]

MCC_CODES = [
    # Retail / consumer
    ("5411", "Grocery Stores"),
    ("5812", "Eating Places, Restaurants"),
    ("5814", "Fast Food Restaurants"),
    ("5541", "Service Stations (Gas)"),
    ("5311", "Department Stores"),
    ("5310", "Discount Stores"),
    ("5651", "Family Clothing Stores"),
    ("5732", "Electronics Stores"),
    ("5912", "Drug Stores, Pharmacies"),
    ("5942", "Book Stores"),
    ("5921", "Package Stores - Beer, Wine, Liquor"),
    ("5999", "Misc Retail"),
    # Utilities / telecom
    ("4900", "Utilities"),
    ("4814", "Telecom Services"),
    ("4812", "Mobile / Cellular Service"),
    # Travel / transport
    ("7011", "Hotels, Motels, Resorts"),
    ("4111", "Local/Suburban Commuter Transport"),
    ("4789", "Transportation Services"),
    ("4511", "Airlines, Air Carriers"),
    ("3000", "Airline-Specific (UA)"),
    ("3001", "Airline-Specific (AA)"),
    # Health / personal
    ("8011", "Doctors / Physicians"),
    ("8021", "Dentists"),
    ("8062", "Hospitals"),
    # Online / digital
    ("5734", "Computer Software Stores"),
    ("5968", "Subscription Merchants"),
    ("5969", "Direct-Marketing - Other"),
    # Fraud-typology codes
    ("6011", "ATM / Cash Disbursement (financial inst.)"),
    ("6051", "Quasi-Cash / Crypto / Money Orders"),
    ("4829", "Money Transfer / Wire"),
    ("7995", "Gambling / Betting / Casino"),
    ("5967", "Inbound Telemarketing"),
    ("5966", "Outbound Telemarketing"),
    ("5993", "Cigar Stores, Stands"),
    # Financial services
    ("6010", "Manual Cash Disbursement"),
    ("6300", "Insurance Sales / Underwriting"),
    ("6536", "MoneySend (Funding)"),
    # Education / nonprofit
    ("8220", "Colleges, Universities"),
    ("8398", "Charitable / Social Service Orgs"),
]

# Card BIN ranges by product class (real-world prefixes)
CARD_BIN_RANGES: dict[str, list[str]] = {
    "DEBIT":           ["411111", "445566", "433333"],          # Visa
    "BUSINESS_DEBIT":  ["445566", "411223"],                    # Visa Business
    "CREDIT_BASIC":    ["411111", "414720", "510510", "520000"],  # Visa / MC
    "CREDIT_REWARDS":  ["520082", "545454", "512345"],          # Mastercard
    "CREDIT_PLATINUM": ["377777", "342233", "601100"],          # Amex / Discover
    "PREPAID":         ["411111", "510510"],                    # Visa / MC prepaid BIN ranges
}

# Email domain distribution (US consumer mix)
EMAIL_DOMAINS = [
    ("gmail.com", 0.50),
    ("yahoo.com", 0.18),
    ("outlook.com", 0.10),
    ("hotmail.com", 0.07),
    ("icloud.com", 0.07),
    ("aol.com", 0.03),
    ("protonmail.com", 0.02),
    ("comcast.net", 0.02),
    ("example.com", 0.01),
]

ASSET_CLASSES = ["equity", "bond", "mutual_fund", "etf", "money_market"]
SECTORS = [
    "Technology", "Financials", "Health Care", "Consumer Discretionary",
    "Industrials", "Energy", "Utilities", "Materials", "Real Estate",
    "Communication Services", "Consumer Staples",
]

# Risk bands match the glossary
RISK_BANDS = ["low", "medium", "high", "critical"]


# ---------------------------------------------------------------------------
# Dataset container
# ---------------------------------------------------------------------------

@dataclass
class Dataset:
    """In-memory store of all generated rows. Functions append here so later
    generators can pick referential keys deterministically."""

    branches: list[dict[str, Any]] = field(default_factory=list)
    employees: list[dict[str, Any]] = field(default_factory=list)
    customers: list[dict[str, Any]] = field(default_factory=list)
    customer_addresses: list[dict[str, Any]] = field(default_factory=list)
    customer_contacts: list[dict[str, Any]] = field(default_factory=list)
    accounts: list[dict[str, Any]] = field(default_factory=list)
    account_holders: list[dict[str, Any]] = field(default_factory=list)
    transactions: list[dict[str, Any]] = field(default_factory=list)
    transaction_categories: list[dict[str, Any]] = field(default_factory=list)
    atm_withdrawals: list[dict[str, Any]] = field(default_factory=list)
    wire_transfers: list[dict[str, Any]] = field(default_factory=list)
    ach_transfers: list[dict[str, Any]] = field(default_factory=list)
    card_products: list[dict[str, Any]] = field(default_factory=list)
    cards: list[dict[str, Any]] = field(default_factory=list)
    card_authorizations: list[dict[str, Any]] = field(default_factory=list)
    card_disputes: list[dict[str, Any]] = field(default_factory=list)
    merchants: list[dict[str, Any]] = field(default_factory=list)
    loan_products: list[dict[str, Any]] = field(default_factory=list)
    loan_applications: list[dict[str, Any]] = field(default_factory=list)
    loans: list[dict[str, Any]] = field(default_factory=list)
    loan_payments: list[dict[str, Any]] = field(default_factory=list)
    collateral: list[dict[str, Any]] = field(default_factory=list)
    credit_scores: list[dict[str, Any]] = field(default_factory=list)
    kyc_checks: list[dict[str, Any]] = field(default_factory=list)
    aml_alerts: list[dict[str, Any]] = field(default_factory=list)
    sanctions_screening: list[dict[str, Any]] = field(default_factory=list)
    suspicious_activity_reports: list[dict[str, Any]] = field(default_factory=list)
    investment_accounts: list[dict[str, Any]] = field(default_factory=list)
    securities: list[dict[str, Any]] = field(default_factory=list)
    holdings: list[dict[str, Any]] = field(default_factory=list)
    trades: list[dict[str, Any]] = field(default_factory=list)
    web_sessions: list[dict[str, Any]] = field(default_factory=list)
    mobile_app_events: list[dict[str, Any]] = field(default_factory=list)
    login_attempts: list[dict[str, Any]] = field(default_factory=list)
    campaigns: list[dict[str, Any]] = field(default_factory=list)
    customer_segments: list[dict[str, Any]] = field(default_factory=list)
    customer_interactions: list[dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _id(prefix: str, n: int, width: int = 6) -> str:
    """Stable identifier like ``CUST_000001``."""
    return f"{prefix}_{str(n).zfill(width)}"


def _random_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def _random_datetime(start: date, end: date) -> datetime:
    d = _random_date(start, end)
    return datetime.combine(d, datetime.min.time()) + timedelta(
        seconds=random.randint(0, 86_399)
    )


def _money(low: float, high: float, decimals: int = 2) -> Decimal:
    return Decimal(str(round(random.uniform(low, high), decimals)))


def _q2(value: Decimal | float) -> Decimal:
    """Quantize money / rate values to 2 decimal places."""
    return Decimal(str(value)).quantize(Decimal("0.01"))


def _q4(value: Decimal | float) -> Decimal:
    """Quantize to 4 decimal places (rates, ratios)."""
    return Decimal(str(value)).quantize(Decimal("0.0001"))


# Hour-of-day weights for retail card / transaction activity:
# 03:00 trough, 12:00 + 18:00 peaks. Reproducible.
_HOUR_WEIGHTS = [
    0.4, 0.3, 0.2, 0.2, 0.3, 0.5, 1.0, 1.8, 2.6, 3.4, 4.0, 4.5,   # 00..11
    5.0, 5.0, 4.6, 4.4, 4.5, 5.0, 4.8, 4.2, 3.4, 2.4, 1.6, 0.9,    # 12..23
]


# Day-of-week weights for transactions/auths. Sat (5) + Sun (6) elevated retail.
_DOW_WEIGHTS = [1.0, 1.0, 1.0, 1.0, 1.2, 1.3, 1.1]                # Mon..Sun


# Wires + ACH: weekday-skewed (most business banking settles M-F).
_DOW_WEIGHTS_BUSINESS = [1.4, 1.4, 1.4, 1.4, 1.3, 0.2, 0.1]


# Month-of-year seasonal multipliers (Jan..Dec). Nov-Dec holiday spike,
# Feb-Mar tax refund deposit bump, summer travel uptick.
_MONTH_WEIGHTS = [
    0.92, 1.05, 1.08, 0.95, 0.97, 1.00, 1.06, 1.08, 0.98, 1.00, 1.18, 1.30,
]


def _weighted_datetime(
    start: date,
    end: date,
    dow_weights: list[float] | None = None,
    business_hours: bool = False,
) -> datetime:
    """Sample a datetime with realistic hour-of-day + day-of-week + monthly weights.

    Args:
        start, end:     inclusive date window
        dow_weights:    optional 7-element list (Mon..Sun). Defaults to retail mix.
        business_hours: if True, restrict hour to 06-19 with peak 09-12 + 13-17.
    """
    days = (end - start).days
    # Build daily weight = month_weight * dow_weight, sampled per-call without
    # pre-materialising the full vector (memory) — rejection sampling instead.
    dow_w = dow_weights or _DOW_WEIGHTS
    max_dw = max(_MONTH_WEIGHTS) * max(dow_w)
    while True:
        offset = random.randint(0, days)
        cand = start + timedelta(days=offset)
        w = _MONTH_WEIGHTS[cand.month - 1] * dow_w[cand.weekday()]
        if random.random() * max_dw <= w:
            break
    if business_hours:
        # 06..19 with peak at 09-12 + 13-17
        peak_hours = [6, 7, 8, 9, 9, 10, 10, 11, 11, 12, 13, 14, 15, 16, 17, 18, 19]
        h = random.choice(peak_hours)
    else:
        # Sample hour using HOUR_WEIGHTS
        h = random.choices(range(24), weights=_HOUR_WEIGHTS, k=1)[0]
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    return datetime.combine(cand, datetime.min.time()).replace(
        hour=h, minute=minute, second=second
    )


def _triangular_dob(youngest: int = 18, oldest: int = 95, peak: int = 42) -> date:
    """DOB sampled by triangular distribution of customer age (peak ~42)."""
    age = int(random.triangular(youngest, oldest, peak))
    today = END_DATE
    birth_year = today.year - age
    # Random month + day within the year
    return date(birth_year, random.randint(1, 12), random.randint(1, 28))


def _consumer_email(first: str, last: str, idx: int) -> str:
    """Realistic consumer-email mix: weighted domains + plausible local parts."""
    pattern = random.choices(
        [
            f"{first.lower()}.{last.lower()}",
            f"{first.lower()}{last.lower()}",
            f"{first[0].lower()}{last.lower()}",
            f"{first.lower()}{random.randint(1, 999)}",
            f"{first.lower()}_{last.lower()}",
        ],
        weights=[0.30, 0.20, 0.20, 0.20, 0.10],
        k=1,
    )[0]
    # Strip non-alphanum-dot-underscore
    pattern = "".join(c for c in pattern if c.isalnum() or c in "._")
    domains, weights = zip(*EMAIL_DOMAINS, strict=False)
    domain = random.choices(domains, weights=weights, k=1)[0]
    # Tiny collision-avoid suffix in <5% of rows
    if random.random() < 0.04:
        pattern = f"{pattern}{idx}"
    return f"{pattern}@{domain}"


def _ein() -> str:
    """US Employer Identification Number ##-#######."""
    return f"{random.randint(10, 99)}-{random.randint(1_000_000, 9_999_999)}"


def _drivers_license(state: str = "CA") -> str:
    """Plausible US driver's license (state-prefixed)."""
    return f"{state}{random.randint(100000, 99999999)}"


def _passport() -> str:
    """US passport-style 9 char identifier."""
    return random.choice(string.ascii_uppercase) + "".join(
        random.choices(string.digits, k=8)
    )


def _ssn() -> str:
    a = random.randint(100, 899)
    b = random.randint(10, 99)
    c = random.randint(1000, 9999)
    return f"{a}-{b}-{c}"


def _phone() -> str:
    area = random.randint(200, 999)
    mid = random.randint(200, 999)
    last = random.randint(1000, 9999)
    return f"({area}) {mid}-{last}"


def _mask_pan(product_code: str | None = None) -> str:
    """Masked card PAN ``BIN(6) + XXXXXX + last4`` using a real BIN per product."""
    bin_prefixes = CARD_BIN_RANGES.get(product_code or "", ["411111"])
    first6 = random.choice(bin_prefixes)
    last4 = "".join(random.choices(string.digits, k=4))
    return f"{first6}XXXXXX{last4}"


# IBAN country length matrix (subset). Real-world spec.
_IBAN_COUNTRY_SPECS: dict[str, int] = {
    "GB": 22, "DE": 22, "FR": 27, "ES": 24, "IT": 27, "NL": 18,
    "BE": 16, "PT": 25, "IE": 22, "CH": 21, "AT": 20, "PL": 28,
}


def _iban_checksum(country: str, bban: str) -> str:
    """Compute ISO 13616 IBAN check digits via mod-97."""
    rearranged = bban + country + "00"
    digits = ""
    for ch in rearranged:
        if ch.isdigit():
            digits += ch
        else:
            digits += str(ord(ch.upper()) - ord("A") + 10)
    checksum = 98 - (int(digits) % 97)
    return f"{checksum:02d}"


def _iban() -> str:
    """ISO 13616 IBAN with correct length per country + valid mod-97 checksum."""
    country = random.choice(list(_IBAN_COUNTRY_SPECS.keys()))
    length = _IBAN_COUNTRY_SPECS[country]
    bban_len = length - 4
    # Use alphanumerics for BBAN (some countries allow letters in the bank-id)
    bban = "".join(random.choices(string.digits, k=bban_len))
    check = _iban_checksum(country, bban)
    return f"{country}{check}{bban}"


def _swift(country_hint: str | None = None) -> str:
    """Valid-shaped BIC/SWIFT 8 or 11 chars: BBBB CC LL [XXX]."""
    bank = "".join(random.choices(string.ascii_uppercase, k=4))
    country = country_hint or random.choice(
        ["US", "GB", "DE", "FR", "JP", "IT", "ES", "NL", "CH", "AT"]
    )
    loc = "".join(random.choices(string.ascii_uppercase + string.digits, k=2))
    if random.random() < 0.6:
        return f"{bank}{country}{loc}"
    branch = "".join(random.choices(string.ascii_uppercase + string.digits, k=3))
    return f"{bank}{country}{loc}{branch}"


def _ip() -> str:
    return ".".join(str(random.randint(1, 254)) for _ in range(4))


def _mac() -> str:
    return ":".join(f"{random.randint(0, 255):02x}" for _ in range(6))


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

def gen_branches(d: Dataset) -> None:
    for i in range(1, N_BRANCHES + 1):
        opened = _random_date(date(2005, 1, 1), date(2022, 12, 31))
        d.branches.append({
            "branch_id": _id("BR", i, 4),
            "branch_name": f"{fake.city()} Branch",
            "address_line_1": fake.street_address(),
            "city": fake.city(),
            "state": fake.state_abbr(),
            "postal_code": fake.zipcode(),
            "country": "USA",
            "region": random.choice(REGIONS),
            "phone": _phone(),
            "manager_employee_id": None,  # backfilled after employees
            "opened_date": opened,
            "closed_date": None,
            "is_active": True,
        })
    # Close one for realism
    d.branches[7]["is_active"] = False
    d.branches[7]["closed_date"] = date(2024, 3, 15)


def gen_employees(d: Dataset) -> None:
    roles = [
        "teller", "personal_banker", "branch_manager", "loan_officer",
        "wealth_advisor", "fraud_analyst", "aml_investigator", "compliance_officer",
        "credit_analyst", "data_engineer", "data_steward", "executive",
    ]
    salary_bands = ["B1", "B2", "B3", "B4", "B5", "B6"]
    # First 10 are executives / managers without manager_id
    for i in range(1, N_EMPLOYEES + 1):
        hire = _random_date(date(2008, 1, 1), date(2025, 12, 31))
        role = "branch_manager" if i <= 10 else random.choice(roles)
        d.employees.append({
            "employee_id": _id("EMP", i, 5),
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": f"{fake.user_name()}@bank.demo",
            "phone": _phone(),
            "hire_date": hire,
            "termination_date": None,
            "role": role,
            "branch_id": d.branches[(i - 1) % len(d.branches)]["branch_id"],
            "manager_id": None if i <= 10 else d.employees[(i - 1) % 10]["employee_id"],
            "salary_band": random.choice(salary_bands),
            "is_active": True if i % 25 != 0 else False,
        })
    # Backfill branch.manager_employee_id from the first 10 employees
    for branch_idx, branch in enumerate(d.branches[:10]):
        branch["manager_employee_id"] = d.employees[branch_idx]["employee_id"]
    for branch in d.branches[10:]:
        # Other branches share managers
        branch["manager_employee_id"] = d.employees[branch_idx % 10]["employee_id"]


def gen_customers(d: Dataset) -> None:
    types = ["retail", "business", "private_banking"]
    type_weights = [0.83, 0.12, 0.05]

    for i in range(1, N_CUSTOMERS + 1):
        customer_type = random.choices(types, weights=type_weights, k=1)[0]
        if customer_type == "private_banking":
            segment = "PRIVATE_BANKING"
        elif customer_type == "business":
            segment = random.choice(["BUSINESS_SMB", "BUSINESS_COMM"])
        else:
            # SENIOR segment driven by age below; for now distribute the rest
            segment = random.choices(
                ["MASS", "AFFLUENT", "HIGH_VALUE", "STUDENT"],
                weights=[0.62, 0.22, 0.10, 0.06],
                k=1,
            )[0]

        created = _weighted_datetime(date(2015, 1, 1), END_DATE)

        if customer_type == "business":
            # Use full faker company name (already includes Inc/LLC/Corp/Group)
            biz_name = fake.company()
            first_name = biz_name
            last_name = ""
        else:
            first_name = fake.first_name()
            last_name = fake.last_name()

        dob = _triangular_dob(youngest=18, oldest=92, peak=42)
        # SENIOR override: customers born <= 1960
        if customer_type == "retail" and dob.year <= 1960 and segment in ("MASS", "AFFLUENT"):
            segment = "SENIOR"

        # Tax identifier: SSN for retail, EIN for businesses
        tax_id = _ein() if customer_type == "business" else _ssn()

        email = (
            _consumer_email(first_name.split()[0], last_name or "biz", i)
            if customer_type != "business"
            else f"contact@{fake.domain_name()}"
        )

        d.customers.append({
            "customer_id": _id("CUST", i, 6),
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": _phone(),
            "ssn": _ssn() if customer_type != "business" else None,
            "tax_id": tax_id,
            "date_of_birth": dob,
            "customer_segment": segment,
            "customer_type": customer_type,
            "branch_id": random.choice(d.branches)["branch_id"],
            "primary_employee_id": random.choice(d.employees[:50])["employee_id"],
            "kyc_status": random.choices(
                ["passed", "pending", "failed", "expired"],
                weights=[0.86, 0.05, 0.04, 0.05],
                k=1,
            )[0],
            "risk_band": random.choices(
                RISK_BANDS, weights=[0.65, 0.25, 0.08, 0.02], k=1,
            )[0],
            "created_at": created,
            "updated_at": RUN_TIMESTAMP,
        })

    # --- Intentional DQ defects (stable indices) -------------------------
    d.customers[10]["ssn"] = None                     # NULL SSN
    d.customers[25]["ssn"] = None                     # NULL SSN
    d.customers[11]["email"] = "not-an-email"         # Invalid email
    d.customers[12]["date_of_birth"] = date(2050, 1, 1)   # Future DOB
    # Duplicate-ish customer (different id but same name + DOB as CUST_000014)
    dup = dict(d.customers[13])
    dup["customer_id"] = _id("CUST", N_CUSTOMERS + 1, 6)
    d.customers.append(dup)


def gen_customer_addresses(d: Dataset) -> None:
    address_types = ["mailing", "residential", "work"]
    addr_id = 1
    for cust in d.customers:
        # 1–2 addresses per customer
        n = random.choices([1, 2], weights=[0.7, 0.3], k=1)[0]
        chosen_types = random.sample(address_types, k=n)
        for at in chosen_types:
            d.customer_addresses.append({
                "address_id": _id("ADDR", addr_id, 7),
                "customer_id": cust["customer_id"],
                "address_type": at,
                "address_line_1": fake.street_address(),
                "address_line_2": fake.secondary_address() if random.random() < 0.2 else None,
                "city": fake.city(),
                "state": fake.state_abbr(),
                "postal_code": fake.zipcode(),
                "country": "USA",
                "is_primary": at == "mailing",
                "effective_from": _random_date(date(2015, 1, 1), END_DATE),
                "effective_to": None,
            })
            addr_id += 1

    # DQ: empty city on one row
    d.customer_addresses[20]["city"] = ""


def gen_customer_contacts(d: Dataset) -> None:
    contact_id = 1
    for cust in d.customers:
        # email contact
        d.customer_contacts.append({
            "contact_id": _id("CT", contact_id, 7),
            "customer_id": cust["customer_id"],
            "contact_type": "email",
            "contact_value": cust["email"],
            "is_primary": True,
            "is_verified": random.random() < 0.93,
            "opt_out": random.random() < 0.05,
            "added_at": cust["created_at"],
        })
        contact_id += 1
        # mobile phone contact
        d.customer_contacts.append({
            "contact_id": _id("CT", contact_id, 7),
            "customer_id": cust["customer_id"],
            "contact_type": "mobile_phone",
            "contact_value": cust["phone"],
            "is_primary": True,
            "is_verified": random.random() < 0.85,
            "opt_out": False,
            "added_at": cust["created_at"],
        })
        contact_id += 1
        # ~30% have a home phone
        if random.random() < 0.3:
            d.customer_contacts.append({
                "contact_id": _id("CT", contact_id, 7),
                "customer_id": cust["customer_id"],
                "contact_type": "home_phone",
                "contact_value": _phone(),
                "is_primary": False,
                "is_verified": False,
                "opt_out": random.random() < 0.20,
                "added_at": cust["created_at"],
            })
            contact_id += 1


def gen_accounts(d: Dataset) -> None:
    # Distribute accounts across customers (some have 1, some 2-3)
    customer_pool = [c["customer_id"] for c in d.customers]
    type_codes = [t[0] for t in ACCOUNT_TYPES]
    deposit_types = [t[0] for t in ACCOUNT_TYPES if t[2] == "deposit"]
    credit_types = [t[0] for t in ACCOUNT_TYPES if t[2] == "credit"]

    for i in range(1, N_ACCOUNTS + 1):
        cust_id = random.choice(customer_pool)
        # Bias toward deposit accounts (typical bank mix)
        atype = random.choices(
            type_codes,
            weights=[0.30, 0.20, 0.08, 0.05, 0.05, 0.07, 0.10, 0.15],
            k=1,
        )[0]
        opened = _random_date(date(2015, 1, 1), END_DATE - timedelta(days=30))
        status = random.choices(
            ["active", "dormant", "closed", "frozen"],
            weights=[0.85, 0.08, 0.05, 0.02],
            k=1,
        )[0]
        closed = None
        if status == "closed":
            closed = _random_date(opened + timedelta(days=30), END_DATE)
        # Balance buckets by account type
        if atype in deposit_types:
            balance = _money(0, 250_000)
            if atype == "CD":
                balance = _money(1_000, 100_000)
            if atype == "BUSINESS_CHECKING":
                balance = _money(5_000, 1_500_000)
        else:
            balance = -_money(0, 250_000)  # negative for credit/loan
        d.accounts.append({
            "account_id": _id("ACC", i, 8),
            "customer_id": cust_id,
            "account_type": atype,
            "product_code": atype,
            "opened_date": opened,
            "closed_date": closed,
            "status": status,
            "balance": balance,
            "currency": "USD",
            "branch_id": random.choice(d.branches)["branch_id"],
            "interest_rate": Decimal("0.0010") if atype in deposit_types else None,
            "credit_limit": _money(1_000, 50_000) if atype in credit_types else None,
            "is_joint": False,  # set below
            "created_at": opened,
            "updated_at": RUN_TIMESTAMP,
        })

    # DQ: negative balance on a "closed" deposit account
    d.accounts[55]["status"] = "closed"
    d.accounts[55]["balance"] = Decimal("-150.00")
    d.accounts[55]["account_type"] = "CHECKING"
    d.accounts[55]["closed_date"] = date(2025, 11, 15)


def gen_account_holders(d: Dataset) -> None:
    holder_id = 1
    for acc in d.accounts:
        # Primary holder
        d.account_holders.append({
            "holder_id": _id("AH", holder_id, 7),
            "account_id": acc["account_id"],
            "customer_id": acc["customer_id"],
            "holder_order": 1,
            "relationship": "primary",
            "added_at": acc["opened_date"],
            "removed_at": None,
        })
        holder_id += 1
        # ~10% are joint accounts
        if random.random() < 0.10:
            joint_cust = random.choice(d.customers)["customer_id"]
            if joint_cust == acc["customer_id"]:
                continue
            d.account_holders.append({
                "holder_id": _id("AH", holder_id, 7),
                "account_id": acc["account_id"],
                "customer_id": joint_cust,
                "holder_order": 2,
                "relationship": "joint",
                "added_at": acc["opened_date"],
                "removed_at": None,
            })
            acc["is_joint"] = True
            holder_id += 1


def gen_transaction_categories(d: Dataset) -> None:
    for code, name, group, sign_hint in TRANSACTION_CATEGORIES:
        d.transaction_categories.append({
            "category_code": code,
            "category_name": name,
            "category_group": group,
            "sign_hint": sign_hint,
        })


def gen_merchants(d: Dataset) -> None:
    for i in range(1, N_MERCHANTS + 1):
        mcc, mcc_desc = random.choice(MCC_CODES)
        d.merchants.append({
            "merchant_id": _id("MERCH", i, 6),
            "merchant_name": fake.company(),
            "mcc_code": mcc,
            "mcc_description": mcc_desc,
            "city": fake.city(),
            "state": fake.state_abbr(),
            "country": "USA",
            "created_at": _random_date(date(2018, 1, 1), END_DATE),
        })


def gen_card_products(d: Dataset) -> None:
    for code, name, klass, fee, limit_band in CARD_PRODUCTS:
        d.card_products.append({
            "product_code": code,
            "product_name": name,
            "product_class": klass,
            "annual_fee": fee,
            "credit_limit_band": limit_band,
            "is_active": True,
        })


def gen_cards(d: Dataset) -> None:
    product_codes = [p["product_code"] for p in d.card_products]
    product_weights = [0.42, 0.22, 0.15, 0.06, 0.10, 0.05]  # debit-heavy mix
    for i in range(1, N_CARDS + 1):
        cust = random.choice(d.customers)
        issued = _random_date(date(2018, 1, 1), END_DATE - timedelta(days=30))
        expires = issued.replace(year=issued.year + 4)
        product = random.choices(product_codes, weights=product_weights, k=1)[0]
        # Link to a customer-owned account when possible
        owned = [a for a in d.accounts if a["customer_id"] == cust["customer_id"]]
        linked = random.choice(owned)["account_id"] if owned else random.choice(d.accounts)["account_id"]
        d.cards.append({
            "card_id": _id("CARD", i, 6),
            "customer_id": cust["customer_id"],
            "card_number_masked": _mask_pan(product),
            "product_code": product,
            "issued_date": issued,
            "expires_date": expires,
            "status": random.choices(
                ["active", "blocked", "expired", "lost"],
                weights=[0.87, 0.04, 0.06, 0.03],
                k=1,
            )[0],
            "credit_limit": _money(1_000, 50_000) if product.startswith("CREDIT") else None,
            "linked_account_id": linked,
        })


def gen_card_authorizations(d: Dataset) -> None:
    decline_reasons = [
        "insufficient_funds", "card_blocked", "expired_card", "fraud_suspected",
        "exceeds_limit", "invalid_cvv", "do_not_honor",
    ]
    for i in range(1, N_CARD_AUTHS + 1):
        card = random.choice(d.cards)
        merchant = random.choice(d.merchants)
        auth_ts = _weighted_datetime(START_DATE, END_DATE)
        # Amount distribution: lognormal-ish; rare large outliers
        if random.random() < 0.85:
            amount = _money(1, 250)
        elif random.random() < 0.97:
            amount = _money(250, 1_500)
        else:
            amount = _money(1_500, 9_500)
        status = random.choices(
            ["approved", "declined", "reversed"],
            weights=[0.93, 0.06, 0.01],
            k=1,
        )[0]
        d.card_authorizations.append({
            "authorization_id": _id("AUTH", i, 8),
            "card_id": card["card_id"],
            "merchant_id": merchant["merchant_id"],
            "amount": amount,
            "currency": "USD",
            "auth_status": status,
            "decline_reason": random.choice(decline_reasons) if status == "declined" else None,
            "auth_timestamp": auth_ts,
            "is_card_present": random.random() < 0.55,
            "ip_address": _ip() if random.random() < 0.92 else None,
        })


def gen_card_disputes(d: Dataset) -> None:
    """Card disputes sampled from card_authorizations.

    Real-world chargeback rates are ~0.5–1% of authorizations. We sample
    ~0.7% so the dispute table grows with auth volume."""
    n_disputes = max(80, int(len(d.card_authorizations) * 0.007))
    sample = random.sample(d.card_authorizations, k=min(n_disputes, len(d.card_authorizations)))
    for i, auth in enumerate(sample, start=1):
        opened = auth["auth_timestamp"].date() + timedelta(days=random.randint(0, 30))
        resolved = opened + timedelta(days=random.randint(20, 90))
        d.card_disputes.append({
            "dispute_id": _id("DSP", i, 6),
            "authorization_id": auth["authorization_id"],
            "card_id": auth["card_id"],
            "dispute_reason": random.choice([
                "fraud_unrecognized", "duplicate_charge", "service_not_received",
                "merchant_dispute", "atm_error", "subscription_cancel",
                "incorrect_amount", "credit_not_processed",
            ]),
            "dispute_amount": auth["amount"],
            "opened_date": opened,
            "resolved_date": resolved if random.random() < 0.85 else None,
            "status": random.choices(
                ["resolved_chargeback", "resolved_no_chargeback", "pending"],
                weights=[0.50, 0.40, 0.10],
                k=1,
            )[0],
            "chargeback_amount": auth["amount"] if random.random() < 0.50 else Decimal("0"),
        })


def gen_fraud_burst(d: Dataset) -> None:
    """Engineered fraud cluster: 10 customers with concentrated card-auth bursts.

    Generates additional card_authorizations rows for fraud-detection demos:
    each "victim" customer sees ~80 authorizations within a 24-hour window
    across mixed-geography IPs and an unusual mix of merchants/MCCs.
    """
    if not d.cards or not d.merchants:
        return
    # Pick 10 distinct customers that hold cards
    cards_by_cust: dict[str, list[dict[str, Any]]] = {}
    for c in d.cards:
        cards_by_cust.setdefault(c["customer_id"], []).append(c)
    candidates = [c for c in cards_by_cust if cards_by_cust[c]]
    targets = random.sample(candidates, k=min(N_FRAUD_BURST_CUSTOMERS, len(candidates)))

    next_idx = len(d.card_authorizations) + 1
    for victim_cust_id in targets:
        victim_card = random.choice(cards_by_cust[victim_cust_id])
        burst_anchor = _random_datetime(
            START_DATE + timedelta(days=30), END_DATE - timedelta(days=2)
        )
        for j in range(N_FRAUD_AUTHS_PER_BURST):
            ts = burst_anchor + timedelta(seconds=random.randint(0, 86_400))
            merchant = random.choice(d.merchants)
            # Fraud-typical: many declines, small + spikes
            status = random.choices(
                ["approved", "declined"], weights=[0.35, 0.65], k=1,
            )[0]
            amount = _money(1, 50) if random.random() < 0.7 else _money(500, 3_500)
            d.card_authorizations.append({
                "authorization_id": _id("AUTH", next_idx, 8),
                "card_id": victim_card["card_id"],
                "merchant_id": merchant["merchant_id"],
                "amount": amount,
                "currency": "USD",
                "auth_status": status,
                "decline_reason": random.choice([
                    "fraud_suspected", "invalid_cvv", "exceeds_limit",
                    "do_not_honor", "card_blocked",
                ]) if status == "declined" else None,
                "auth_timestamp": ts,
                "is_card_present": random.random() < 0.10,  # mostly card-not-present
                # Mixed geography IPs to look suspicious
                "ip_address": _ip(),
            })
            next_idx += 1


def gen_chargeback_storm(d: Dataset) -> None:
    """Engineered chargeback storm: N merchants take a spike of disputes
    within a 30-day window. Drives merchant-risk demos.
    """
    if not d.merchants or not d.card_authorizations:
        return
    target_merchants = random.sample(d.merchants, k=N_CHARGEBACK_STORM_MERCHANTS)
    storm_anchor = _random_datetime(
        START_DATE + timedelta(days=60), END_DATE - timedelta(days=60)
    )
    next_idx = len(d.card_disputes) + 1
    for merchant in target_merchants:
        merchant_auths = [
            a for a in d.card_authorizations
            if a["merchant_id"] == merchant["merchant_id"]
        ]
        if not merchant_auths:
            continue
        chosen = random.sample(
            merchant_auths, k=min(N_CHARGEBACK_STORM_SIZE, len(merchant_auths))
        )
        for auth in chosen:
            opened = storm_anchor.date() + timedelta(days=random.randint(0, 30))
            d.card_disputes.append({
                "dispute_id": _id("DSP", next_idx, 6),
                "authorization_id": auth["authorization_id"],
                "card_id": auth["card_id"],
                "dispute_reason": random.choice([
                    "service_not_received", "merchant_dispute", "credit_not_processed",
                ]),
                "dispute_amount": auth["amount"],
                "opened_date": opened,
                "resolved_date": opened + timedelta(days=random.randint(30, 75)),
                "status": random.choices(
                    ["resolved_chargeback", "resolved_no_chargeback", "pending"],
                    weights=[0.75, 0.15, 0.10],
                    k=1,
                )[0],
                "chargeback_amount": auth["amount"] if random.random() < 0.75 else Decimal("0"),
            })
            next_idx += 1


def gen_transactions(d: Dataset) -> None:
    cat_codes = [c["category_code"] for c in d.transaction_categories]
    cat_weights = [0.20, 0.18, 0.05, 0.05, 0.30, 0.05, 0.03, 0.05, 0.02, 0.05, 0.01, 0.01]
    active_accounts = [a for a in d.accounts if a["status"] in ("active", "dormant")]
    channel_per_cat = {
        "ATM": "atm",
        "WIRE": "wire",
        "ACH": "ach",
        "PURCHASE": "card",
    }
    # Pre-build per-category description templates so text is on-topic instead
    # of Faker random sentences. Improves OM glossary/PII demos.
    desc_templates = {
        "DEPOSIT":     ["Direct deposit payroll", "Mobile check deposit", "Branch cash deposit", "Refund from {merchant}"],
        "WITHDRAWAL":  ["Counter withdrawal", "Cash back at POS", "Branch withdrawal slip"],
        "PURCHASE":    ["POS purchase at {merchant}", "Online purchase {merchant}", "Card-present purchase {merchant}"],
        "TRANSFER_IN": ["Internal transfer in", "Zelle credit from contact"],
        "TRANSFER_OUT":["Internal transfer out", "Zelle payment to contact"],
        "FEE":         ["Monthly maintenance fee", "Overdraft fee", "ATM out-of-network fee", "Wire transfer fee"],
        "INTEREST":    ["Interest credit", "CD interest payment"],
        "ATM":         ["ATM withdrawal {merchant}", "Foreign ATM withdrawal"],
        "WIRE":        ["Wire transfer outbound", "Wire transfer inbound"],
        "ACH":         ["ACH debit batch", "ACH credit batch"],
        "REVERSAL":    ["Transaction reversal"],
        "ADJUSTMENT":  ["Account adjustment", "Goodwill credit"],
    }

    for i in range(1, N_TXNS + 1):
        acc = random.choice(active_accounts)
        cat = random.choices(cat_codes, weights=cat_weights, k=1)[0]
        sign_hint = next(c[3] for c in TRANSACTION_CATEGORIES if c[0] == cat)
        # Lognormal-ish amount distribution by category
        if cat == "WIRE":
            base = random.uniform(500, 100_000)
        elif cat in ("ACH", "TRANSFER_IN", "TRANSFER_OUT"):
            base = random.uniform(50, 25_000)
        elif cat == "DEPOSIT":
            base = random.uniform(20, 8_000)
        elif cat == "FEE":
            base = random.choice([5, 12, 25, 35])
        elif cat == "INTEREST":
            base = random.uniform(0.5, 250)
        elif cat == "PURCHASE":
            base = random.uniform(1, 800)
        else:
            base = random.uniform(1, 1_500)
        amount = _q2(base)
        signed = amount if sign_hint >= 0 else -amount
        # Business / corporate channels get weekday-biased timing
        if cat in ("WIRE", "ACH"):
            posted_at = _weighted_datetime(
                START_DATE, END_DATE, dow_weights=_DOW_WEIGHTS_BUSINESS, business_hours=True,
            )
        else:
            posted_at = _weighted_datetime(START_DATE, END_DATE)
        merchant = random.choice(d.merchants) if cat in ("PURCHASE", "ATM") else None
        descs = desc_templates.get(cat, ["Transaction"])
        desc_tmpl = random.choice(descs)
        description = (
            desc_tmpl.format(merchant=merchant["merchant_name"]) if merchant else desc_tmpl
        )
        channel = channel_per_cat.get(
            cat, random.choice(["branch", "web", "mobile", "card"])
        )
        d.transactions.append({
            "transaction_id": _id("TXN", i, 10),
            "account_id": acc["account_id"],
            "posted_at": posted_at,
            "amount": signed,
            "currency": "USD",
            "transaction_type": cat,
            "merchant_id": merchant["merchant_id"] if merchant else None,
            "description": description,
            "is_reversal": cat == "REVERSAL",
            "channel": channel,
            "running_balance": None,  # computed downstream
            "created_at": posted_at,
        })

    # --- DQ defects ----------------------------------------------------
    # 30 orphan transactions referencing a non-existent account
    for i in range(30):
        d.transactions[i]["account_id"] = "ACC_99999999"


def gen_atm_withdrawals(d: Dataset) -> None:
    """ATM-specific ledger. Each row links back to a parent transaction row
    in raw_transactions.transactions (transaction_type='ATM') for lineage demos.
    """
    atm_locations = [(fake.city(), fake.state_abbr()) for _ in range(220)]
    # Use ATM-category transactions as the parent set
    atm_txns = [t for t in d.transactions if t["transaction_type"] == "ATM"]
    if not atm_txns:
        atm_txns = d.transactions[: N_ATM]
    # Sample with replacement (some txns may not map) up to N_ATM
    chosen = random.choices(atm_txns, k=min(N_ATM, len(atm_txns) * 5))[: N_ATM]
    for i, parent in enumerate(chosen, start=1):
        city, state = random.choice(atm_locations)
        ts = parent["posted_at"]
        amount = abs(parent["amount"]) if abs(parent["amount"]) > 0 else _money(20, 500)
        # Round withdrawal amounts to nearest $20 (real ATMs dispense $20 multiples)
        amount = Decimal(int(amount / 20) * 20 or 20)
        d.atm_withdrawals.append({
            "atm_withdrawal_id": _id("ATM", i, 7),
            "account_id": parent["account_id"],
            "atm_terminal_id": f"ATM-{random.randint(1000, 9999)}",
            "atm_city": city,
            "atm_state": state,
            "amount": amount,
            "fee_amount": Decimal("3.00") if random.random() < 0.30 else Decimal("0"),
            "withdrawn_at": ts,
            "is_foreign": random.random() < 0.05,
            "network": random.choice(["STAR", "PLUS", "Cirrus", "NYCE", "Pulse"]),
            "parent_transaction_id": parent["transaction_id"],
        })


def gen_wire_transfers(d: Dataset) -> None:
    """Wire-specific ledger with proper IBAN/BIC. Links back to a parent
    transaction in raw_transactions.transactions for lineage demos.
    """
    wire_txns = [t for t in d.transactions if t["transaction_type"] == "WIRE"]
    if not wire_txns:
        wire_txns = d.transactions[: N_WIRES]
    chosen = random.choices(wire_txns, k=min(N_WIRES, len(wire_txns) * 5))[: N_WIRES]
    for i, parent in enumerate(chosen, start=1):
        direction = random.choice(["incoming", "outgoing"])
        amount = abs(parent["amount"])
        if amount < 250:
            amount = _money(500, 250_000)
        d.wire_transfers.append({
            "wire_id": _id("WIRE", i, 6),
            "account_id": parent["account_id"],
            "direction": direction,
            "amount": amount,
            "currency": random.choices(
                ["USD", "EUR", "GBP", "JPY", "CHF"],
                weights=[0.78, 0.10, 0.06, 0.04, 0.02],
                k=1,
            )[0],
            "from_iban": _iban() if direction == "incoming" else None,
            "to_iban": _iban() if direction == "outgoing" else None,
            "swift_code": _swift(),
            "fee_amount": Decimal(str(random.choice([15, 25, 35, 45, 50]))),
            "originator_name": fake.name() if direction == "incoming" else None,
            "beneficiary_name": fake.name() if direction == "outgoing" else None,
            "wire_purpose": random.choice([
                "salary", "loan_payment", "invoice", "real_estate",
                "investment", "remittance", "M&A", "vendor_payment", "other",
            ]),
            "sent_at": parent["posted_at"],
            "status": random.choices(
                ["completed", "pending", "failed", "rejected"],
                weights=[0.92, 0.04, 0.02, 0.02],
                k=1,
            )[0],
            "parent_transaction_id": parent["transaction_id"],
        })


def gen_ach_transfers(d: Dataset) -> None:
    """ACH ledger. Links to parent transactions in raw_transactions for lineage.
    Uses real-world SEC codes (PPD, CCD, WEB, TEL, IAT) with realistic distribution.
    """
    ach_txns = [t for t in d.transactions if t["transaction_type"] == "ACH"]
    if not ach_txns:
        ach_txns = d.transactions[: N_ACH]
    chosen = random.choices(ach_txns, k=min(N_ACH, len(ach_txns) * 5))[: N_ACH]
    sec_weights = [0.55, 0.20, 0.18, 0.05, 0.02]
    for i, parent in enumerate(chosen, start=1):
        direction = random.choice(["credit", "debit"])
        amount = abs(parent["amount"])
        if amount < 5:
            amount = _money(10, 5_000)
        ts = parent["posted_at"]
        d.ach_transfers.append({
            "ach_id": _id("ACH", i, 7),
            "account_id": parent["account_id"],
            "direction": direction,
            "amount": amount,
            "ach_type": random.choice(["PPD", "CCD", "WEB", "TEL"]),
            "counterparty_routing": f"{random.randint(10_000_000, 99_999_999)}",
            "counterparty_account_masked": "XXXXXX" + str(random.randint(1000, 9999)),
            "counterparty_name": fake.company() if direction == "credit" else fake.name(),
            "settled_date": ts.date() + timedelta(days=random.choice([0, 1, 1, 2, 3])),
            "originated_at": ts,
            "status": random.choices(
                ["settled", "returned", "pending"],
                weights=[0.94, 0.04, 0.02],
                k=1,
            )[0],
            "sec_code": random.choices(
                ["PPD", "CCD", "WEB", "TEL", "IAT"], weights=sec_weights, k=1,
            )[0],
            "return_reason_code": random.choice(
                ["R01", "R02", "R03", "R04", "R07", "R08", "R10"]
            ) if random.random() < 0.04 else None,
            "parent_transaction_id": parent["transaction_id"],
        })


def gen_loan_products(d: Dataset) -> None:
    for code, name, klass, term, rate in LOAN_PRODUCTS:
        d.loan_products.append({
            "product_code": code,
            "product_name": name,
            "product_class": klass,
            "default_term_months": term,
            "base_apr": Decimal(str(rate)),
            "min_amount": Decimal("5000") if klass != "mortgage" else Decimal("50000"),
            "max_amount": Decimal("750000") if klass == "mortgage" else Decimal("100000"),
            "is_secured": klass in ("mortgage", "auto", "heloc"),
            "is_active": True,
        })


def gen_loan_applications(d: Dataset) -> None:
    """Loan applications with FICO/DTI/approval correlation.

    Higher FICO + lower DTI → higher approval probability. Mimics real lending
    decision distributions; supports risk analytics demos.
    """
    purposes = [
        "home_purchase", "refinance", "auto_purchase",
        "debt_consolidation", "home_improvement", "education",
        "business_expansion", "medical", "other",
    ]
    denial_reasons = [
        "low_credit_score", "high_dti", "insufficient_income",
        "incomplete_documentation", "policy_exclusion",
    ]
    loan_officers = [
        e["employee_id"] for e in d.employees if e["role"] == "loan_officer"
    ] or [d.employees[0]["employee_id"]]

    for i in range(1, N_LOAN_APPS + 1):
        cust = random.choice(d.customers)
        product = random.choice(d.loan_products)
        applied = _weighted_datetime(START_DATE, END_DATE).date()

        # FICO band by customer segment (bimodal-ish)
        if cust["customer_segment"] in ("PRIVATE_BANKING", "HIGH_VALUE"):
            fico = int(random.triangular(680, 850, 780))
        elif cust["customer_segment"] in ("AFFLUENT", "BUSINESS_COMM"):
            fico = int(random.triangular(620, 820, 720))
        elif cust["customer_segment"] in ("STUDENT", "MASS"):
            fico = int(random.triangular(500, 800, 680))
        else:
            fico = int(random.triangular(540, 820, 700))

        # DTI inversely correlated with FICO
        dti_base = max(0.08, min(0.55, 0.62 - (fico - 540) / 800))
        dti = _q4(random.uniform(dti_base * 0.7, dti_base * 1.3))

        income = _money(35_000, 350_000)
        amount = _money(float(product["min_amount"]), float(product["max_amount"]))

        # Approval probability driven by FICO and DTI
        approve_p = 0.40
        if fico >= 740: approve_p += 0.35
        elif fico >= 670: approve_p += 0.20
        elif fico < 580: approve_p -= 0.25
        if dti < Decimal("0.30"): approve_p += 0.10
        elif dti > Decimal("0.45"): approve_p -= 0.15
        approve_p = max(0.05, min(0.92, approve_p))
        roll = random.random()
        if roll < approve_p:
            status = "approved"
        elif roll < approve_p + 0.45 * (1 - approve_p):
            status = "denied"
        elif roll < approve_p + 0.70 * (1 - approve_p):
            status = "withdrawn"
        else:
            status = "pending"
        decision_date = applied + timedelta(days=random.randint(2, 21)) if status != "pending" else None

        denial = None
        if status == "denied":
            if fico < 620:
                denial = "low_credit_score"
            elif dti > Decimal("0.45"):
                denial = "high_dti"
            elif income < Decimal("50000"):
                denial = "insufficient_income"
            else:
                denial = random.choice(denial_reasons)

        d.loan_applications.append({
            "application_id": _id("APP", i, 7),
            "customer_id": cust["customer_id"],
            "product_code": product["product_code"],
            "applied_date": applied,
            "requested_amount": amount,
            "fico_at_application": fico,
            "annual_income": income,
            "dti_ratio": dti,
            "purpose": random.choice(purposes),
            "status": status,
            "decision_date": decision_date,
            "denial_reason": denial,
            "loan_officer_id": random.choice(loan_officers),
            "branch_id": cust["branch_id"],
        })


def gen_loans(d: Dataset) -> None:
    """Loans booked from approved applications, with IFRS 9 staging.

    Adds days_past_due, ifrs9_stage (1/2/3), PD_12m, LGD, EAD, ECL — the
    standard impairment fields required for Risk Officer / IFRS9 dashboards.
    Monetary amounts quantised to 2 decimal places.
    """
    approved_apps = [a for a in d.loan_applications if a["status"] == "approved"]
    chosen = random.sample(approved_apps, k=min(N_LOANS, len(approved_apps)))
    product_lookup = {p["product_code"]: p for p in d.loan_products}

    # LGD calibration by product class
    lgd_map = {
        "MORTGAGE_30Y":  Decimal("0.30"),
        "MORTGAGE_15Y":  Decimal("0.25"),
        "AUTO_LOAN":     Decimal("0.45"),
        "HELOC":         Decimal("0.55"),
        "PERSONAL_LOAN": Decimal("0.65"),
        "BUSINESS_LOAN": Decimal("0.55"),
    }

    for i, app in enumerate(chosen, start=1):
        product = product_lookup[app["product_code"]]
        principal = app["requested_amount"]
        rate = _q4(product["base_apr"] + Decimal(str(round(random.uniform(-0.005, 0.030), 4))))
        term = product["default_term_months"]
        origination = app["decision_date"] + timedelta(days=random.randint(7, 30))
        maturity = origination + timedelta(days=30 * term)

        status = random.choices(
            ["current", "delinquent", "paid_off", "charged_off"],
            weights=[0.78, 0.11, 0.08, 0.03],
            k=1,
        )[0]

        # Balance + days-past-due driven by status
        if status == "paid_off":
            balance = Decimal("0")
            dpd = 0
        elif status == "charged_off":
            balance = _q2(principal * Decimal("0.45"))
            dpd = random.randint(180, 540)
        elif status == "delinquent":
            balance = _q2(principal * Decimal(str(round(random.uniform(0.30, 0.99), 4))))
            dpd = random.choice([30, 31, 45, 60, 75, 90, 120, 150])
        else:
            balance = _q2(principal * Decimal(str(round(random.uniform(0.30, 0.99), 4))))
            dpd = 0

        next_due = None if status == "paid_off" else END_DATE - timedelta(days=random.randint(0, 90))

        # IFRS 9 staging based on DPD
        if status == "charged_off" or dpd >= 90:
            ifrs9_stage = 3
        elif dpd >= 30:
            ifrs9_stage = 2
        else:
            ifrs9_stage = 1

        # PD (12-month for stage 1; lifetime for stage 2/3 proxy)
        fico = app["fico_at_application"]
        base_pd = max(0.002, min(0.50, 0.02 + (740 - fico) * 0.0008))
        if ifrs9_stage == 1:
            pd_12m = _q4(base_pd)
        elif ifrs9_stage == 2:
            pd_12m = _q4(min(0.85, base_pd * 5))
        else:
            pd_12m = Decimal("1.0000")

        lgd = lgd_map.get(product["product_code"], Decimal("0.50"))
        ead = balance
        ecl = _q2(pd_12m * lgd * ead)
        monthly_payment = _q2((principal / term) + (principal * rate / Decimal("12")))

        d.loans.append({
            "loan_id": _id("LOAN", i, 6),
            "application_id": app["application_id"],
            "customer_id": app["customer_id"],
            "product_code": product["product_code"],
            "principal": _q2(principal),
            "interest_rate": rate,
            "term_months": term,
            "origination_date": origination,
            "maturity_date": maturity,
            "first_payment_date": origination + timedelta(days=30),
            "next_due_date": next_due,
            "status": status,
            "balance": balance,
            "monthly_payment": monthly_payment,
            "branch_id": app["branch_id"],
            # IFRS9 impairment fields
            "days_past_due": dpd,
            "ifrs9_stage": ifrs9_stage,
            "pd_12m": pd_12m,
            "lgd": lgd,
            "ead": ead,
            "ecl_amount": ecl,
        })


def gen_loan_payments(d: Dataset) -> None:
    pay_id = 1
    for loan in d.loans:
        if loan["status"] == "paid_off":
            n_payments = loan["term_months"]
        elif loan["status"] == "charged_off":
            n_payments = random.randint(3, 24)
        else:
            # Months between origination and today
            months_elapsed = (END_DATE.year - loan["origination_date"].year) * 12 + \
                             (END_DATE.month - loan["origination_date"].month)
            n_payments = max(0, months_elapsed - random.randint(0, 3))

        for k in range(n_payments):
            pay_date = loan["first_payment_date"] + timedelta(days=30 * k)
            if pay_date > END_DATE:
                break
            interest_portion = loan["balance"] * loan["interest_rate"] / Decimal("12")
            principal_portion = loan["monthly_payment"] - interest_portion
            d.loan_payments.append({
                "payment_id": _id("LP", pay_id, 8),
                "loan_id": loan["loan_id"],
                "payment_date": pay_date,
                "amount": loan["monthly_payment"],
                "principal_portion": principal_portion,
                "interest_portion": interest_portion,
                "payment_type": "scheduled",
                "status": random.choices(
                    ["posted", "returned"],
                    weights=[0.97, 0.03],
                    k=1,
                )[0],
                "channel": random.choice(["ach", "branch", "online", "check"]),
                "created_at": datetime.combine(pay_date, datetime.min.time()),
            })
            pay_id += 1


def gen_collateral(d: Dataset) -> None:
    secured_loans = [l for l in d.loans if l["product_code"] in ("MORTGAGE_30Y", "MORTGAGE_15Y", "AUTO_LOAN", "HELOC")]
    for i, loan in enumerate(secured_loans, start=1):
        if loan["product_code"].startswith("MORTGAGE") or loan["product_code"] == "HELOC":
            ctype = "real_estate"
            value = loan["principal"] * Decimal(str(round(random.uniform(1.10, 1.50), 4)))
            desc = f"{fake.street_address()}, {fake.city()}, {fake.state_abbr()}"
        else:
            ctype = "auto"
            value = loan["principal"] * Decimal(str(round(random.uniform(1.05, 1.40), 4)))
            desc = f"{random.choice(['Toyota', 'Honda', 'Ford', 'Tesla', 'Chevrolet'])} {random.choice(['Camry','Civic','F-150','Model 3','Equinox'])} {random.randint(2018, 2025)}"
        d.collateral.append({
            "collateral_id": _id("COL", i, 6),
            "loan_id": loan["loan_id"],
            "collateral_type": ctype,
            "description": desc,
            "appraised_value": value,
            "appraisal_date": loan["origination_date"] - timedelta(days=random.randint(0, 60)),
            "ltv_ratio": loan["principal"] / value,
            "lien_position": 1,
        })


def gen_credit_scores(d: Dataset) -> None:
    for i in range(1, N_CREDIT_PULLS + 1):
        cust = random.choice(d.customers)
        score_date = _random_date(date(2023, 1, 1), END_DATE)
        d.credit_scores.append({
            "score_id": _id("CS", i, 7),
            "customer_id": cust["customer_id"],
            "score_type": random.choice(["FICO", "VANTAGE"]),
            "score_value": random.randint(450, 820),
            "score_date": score_date,
            "bureau": random.choice(["EXPERIAN", "EQUIFAX", "TRANSUNION"]),
            "pull_reason": random.choice([
                "loan_application", "credit_card_application",
                "periodic_refresh", "consumer_request",
            ]),
            "created_at": datetime.combine(score_date, datetime.min.time()),
        })


def gen_kyc_checks(d: Dataset) -> None:
    for i in range(1, N_KYC + 1):
        cust = random.choice(d.customers)
        check_date = _random_date(cust["created_at"].date(), END_DATE)
        check_type = random.choice(["initial", "refresh", "edd"])
        d.kyc_checks.append({
            "kyc_id": _id("KYC", i, 7),
            "customer_id": cust["customer_id"],
            "check_type": check_type,
            "check_date": check_date,
            "check_status": random.choices(
                ["passed", "failed", "pending", "review"],
                weights=[0.85, 0.05, 0.05, 0.05],
                k=1,
            )[0],
            "verification_method": random.choice([
                "in_person", "video_call", "document_upload", "third_party_idv",
            ]),
            "documents_provided": random.choice([
                "passport,proof_of_address",
                "drivers_license,proof_of_address",
                "national_id,utility_bill",
                "passport",
            ]),
            "performed_by_employee_id": random.choice([
                e["employee_id"] for e in d.employees
                if e["role"] in ("aml_investigator", "compliance_officer", "personal_banker")
            ] or [d.employees[0]["employee_id"]]),
            "next_review_date": check_date + timedelta(days=365),
            "risk_assessment_band": random.choices(
                RISK_BANDS, weights=[0.70, 0.20, 0.08, 0.02], k=1,
            )[0],
            "created_at": datetime.combine(check_date, datetime.min.time()),
        })


def gen_aml_alerts(d: Dataset) -> None:
    """AML alerts with realistic type distribution and templated narratives.

    Industry rough mix: structuring ~30%, unusual_pattern ~25%, rapid_movement
    ~15%, high_value_cash ~10%, geographic_risk ~10%, pep_match ~5%,
    sanctions_hit ~5%. Narratives are templated per alert_type so analysts
    see plausible justifications (drives AI demos that explain alerts).
    """
    alert_types = [
        "structuring", "unusual_pattern", "rapid_movement",
        "high_value_cash", "geographic_risk", "pep_match", "sanctions_hit",
    ]
    alert_weights = [0.30, 0.25, 0.15, 0.10, 0.10, 0.05, 0.05]
    severities = ["low", "medium", "high", "critical"]
    statuses = ["new", "triaging", "escalated", "closed_no_action", "closed_sar_filed"]

    narrative_templates = {
        "structuring": [
            "Customer made {n} cash deposits totaling ${total:,} over {days} days, each under the $10,000 CTR threshold.",
            "Pattern of {n} structured cash transactions across {days} days indicating possible smurfing.",
            "Customer broke a large deposit into {n} smaller transactions to avoid CTR reporting.",
        ],
        "unusual_pattern": [
            "Customer's activity deviates significantly from {months}-month baseline: {delta}x normal volume.",
            "Unusual transaction pattern detected: {n} wires in {days} days vs. {baseline} per month baseline.",
            "Material change in transaction profile vs. customer's onboarding KYC information.",
        ],
        "rapid_movement": [
            "Funds in/out within {hours}h: ${amount:,} credited and ${out:,} wired within same business day.",
            "Pass-through activity: ${amount:,} deposited and withdrawn within {days} days.",
            "Velocity exceeds limits: {n} large transactions in {days} days, characteristic of layering.",
        ],
        "high_value_cash": [
            "Single cash deposit of ${amount:,} on {date} exceeds high-value threshold.",
            "Aggregate cash transactions of ${amount:,} over {days} days from {n} branches.",
        ],
        "geographic_risk": [
            "Transaction with counterparty in {country} (FATF high-risk jurisdiction).",
            "IP address geolocation conflicts with stated address: detected in {country}.",
            "Wire to/from {country} exceeds geographic risk threshold.",
        ],
        "pep_match": [
            "Customer name matched PEP database entry (score {score}%): possible match flagged for EDD.",
            "Family-member relationship to a foreign PEP identified during periodic refresh.",
        ],
        "sanctions_hit": [
            "Counterparty name matched OFAC SDN list (score {score}%): transaction blocked pending review.",
            "Beneficiary in wire transfer matched EU sanctions designation.",
        ],
    }

    aml_investigators = [
        e["employee_id"] for e in d.employees if e["role"] == "aml_investigator"
    ] or [d.employees[0]["employee_id"]]

    closed_account_ids = [a["account_id"] for a in d.accounts if a["status"] == "closed"]

    high_risk_countries = ["Iran", "North Korea", "Syria", "Cuba", "Yemen", "Myanmar"]

    for i in range(1, N_AML + 1):
        cust = random.choice(d.customers)
        acc_id = random.choice(d.accounts)["account_id"]
        # DQ: every 50th alert references a closed account
        if i % 50 == 0 and closed_account_ids:
            acc_id = random.choice(closed_account_ids)
        # Most alerts attach to a specific suspect transaction
        txn_id = random.choice(d.transactions)["transaction_id"] if random.random() < 0.70 else None
        alert_type = random.choices(alert_types, weights=alert_weights, k=1)[0]
        # Structuring alerts cluster on weekends (smurfing pattern)
        if alert_type == "structuring":
            alert_date = _weighted_datetime(
                START_DATE, END_DATE,
                dow_weights=[0.6, 0.6, 0.6, 0.7, 0.9, 1.6, 1.6],
            ).date()
        else:
            alert_date = _random_date(START_DATE, END_DATE)
        status = random.choices(statuses, weights=[0.18, 0.22, 0.18, 0.32, 0.10], k=1)[0]
        severity = random.choices(severities, weights=[0.35, 0.32, 0.22, 0.11], k=1)[0]

        # Build narrative
        tmpl = random.choice(narrative_templates[alert_type])
        narrative = tmpl.format(
            n=random.randint(3, 14),
            total=random.randint(45_000, 290_000),
            days=random.randint(2, 21),
            hours=random.choice([2, 4, 8, 24]),
            months=random.choice([3, 6, 12]),
            delta=random.choice(["2.5", "3.8", "5.2", "8.1"]),
            baseline=random.randint(1, 8),
            amount=random.randint(15_000, 480_000),
            out=random.randint(8_000, 410_000),
            date=alert_date.isoformat(),
            country=random.choice(high_risk_countries),
            score=random.randint(82, 99),
        )

        d.aml_alerts.append({
            "alert_id": _id("AML", i, 6),
            "customer_id": cust["customer_id"],
            "account_id": acc_id,
            "transaction_id": txn_id,
            "alert_type": alert_type,
            "severity": severity,
            "status": status,
            "alert_date": alert_date,
            "triaged_date": alert_date + timedelta(days=random.randint(1, 7)) if status != "new" else None,
            "closed_date": alert_date + timedelta(days=random.randint(7, 45)) if status.startswith("closed") else None,
            "assigned_to_employee_id": random.choice(aml_investigators),
            "narrative": narrative,
            "scenario_code": f"SCN-{random.randint(100, 199)}",
            "created_at": datetime.combine(alert_date, datetime.min.time()),
        })


def gen_sanctions_screening(d: Dataset) -> None:
    lists = ["OFAC_SDN", "OFAC_CONS", "EU_SANCTIONS", "UN_SANCTIONS", "UK_HMT"]
    for i in range(1, 401):
        cust = random.choice(d.customers)
        screen_date = _random_date(cust["created_at"].date(), END_DATE)
        is_hit = random.random() < 0.02
        d.sanctions_screening.append({
            "screening_id": _id("SAN", i, 6),
            "customer_id": cust["customer_id"],
            "screening_date": screen_date,
            "list_name": random.choice(lists),
            "screen_result": "hit" if is_hit else "no_hit",
            "match_score": Decimal(str(round(random.uniform(0.85, 0.99), 4))) if is_hit else None,
            "matched_name": cust["last_name"] if is_hit else None,
            "disposition": random.choice(["true_match", "false_positive"]) if is_hit else None,
            "screened_by_system": random.choice(["WorldCheck", "Dow Jones RiskCenter", "LexisNexis"]),
            "created_at": datetime.combine(screen_date, datetime.min.time()),
        })


def gen_suspicious_activity_reports(d: Dataset) -> None:
    escalated_alerts = [a for a in d.aml_alerts if a["status"] == "closed_sar_filed"]
    chosen = random.sample(escalated_alerts, k=min(N_SAR, len(escalated_alerts)))
    for i, alert in enumerate(chosen, start=1):
        filed = alert["closed_date"] + timedelta(days=random.randint(1, 30))
        d.suspicious_activity_reports.append({
            "sar_id": _id("SAR", i, 5),
            "alert_id": alert["alert_id"],
            "customer_id": alert["customer_id"],
            "filing_date": filed,
            "filing_institution": "First Demo Bank",
            "regulator": "FinCEN",
            "filing_reference": f"FC-{filed.year}-{random.randint(10000, 99999)}",
            "suspicious_activity_type": alert["alert_type"],
            "total_amount_involved": _money(5_000, 500_000),
            "narrative": fake.paragraph(nb_sentences=3),
            "filed_by_employee_id": random.choice([
                e["employee_id"] for e in d.employees if e["role"] == "compliance_officer"
            ] or [d.employees[0]["employee_id"]]),
            "status": random.choice(["filed", "amended", "under_review"]),
            "created_at": datetime.combine(filed, datetime.min.time()),
        })


def gen_investment_accounts(d: Dataset) -> None:
    investment_customers = random.sample(d.customers, k=200)
    for i, cust in enumerate(investment_customers, start=1):
        opened = _random_date(date(2018, 1, 1), END_DATE - timedelta(days=30))
        d.investment_accounts.append({
            "investment_account_id": _id("INV", i, 6),
            "customer_id": cust["customer_id"],
            "account_type": random.choice(["brokerage", "IRA_traditional", "IRA_roth", "401k", "529_plan"]),
            "opened_date": opened,
            "status": random.choices(["active", "closed"], weights=[0.95, 0.05], k=1)[0],
            "risk_tolerance": random.choice(["conservative", "moderate", "aggressive"]),
            "investment_objective": random.choice([
                "income", "growth", "balanced", "capital_preservation", "speculative",
            ]),
            "advisor_employee_id": random.choice([
                e["employee_id"] for e in d.employees if e["role"] == "wealth_advisor"
            ] or [d.employees[0]["employee_id"]]),
            "created_at": opened,
        })


def gen_securities(d: Dataset) -> None:
    for i in range(1, N_SECURITIES + 1):
        ac = random.choice(ASSET_CLASSES)
        ticker = "".join(random.choices(string.ascii_uppercase, k=random.randint(3, 5)))
        d.securities.append({
            "security_id": _id("SEC", i, 5),
            "ticker": ticker,
            "isin": "US" + "".join(random.choices(string.digits + string.ascii_uppercase, k=10)),
            "name": f"{fake.company()} {random.choice(['Inc', 'Corp', 'Holdings', 'Trust', 'Fund'])}",
            "asset_class": ac,
            "sector": random.choice(SECTORS),
            "exchange": random.choice(["NYSE", "NASDAQ", "BATS", "ARCA"]),
            "currency": "USD",
            "current_price": _money(5, 850),
            "price_as_of": END_DATE,
        })


def gen_holdings(d: Dataset) -> None:
    for i in range(1, N_HOLDINGS + 1):
        inv_acc = random.choice(d.investment_accounts)
        sec = random.choice(d.securities)
        qty = Decimal(str(round(random.uniform(1, 5_000), 4)))
        d.holdings.append({
            "holding_id": _id("HLD", i, 7),
            "investment_account_id": inv_acc["investment_account_id"],
            "security_id": sec["security_id"],
            "quantity": qty,
            "cost_basis": qty * sec["current_price"] * Decimal(str(round(random.uniform(0.5, 1.2), 4))),
            "as_of_date": END_DATE,
            "acquired_date": _random_date(inv_acc["opened_date"], END_DATE),
        })


def gen_trades(d: Dataset) -> None:
    for i in range(1, N_TRADES + 1):
        inv_acc = random.choice(d.investment_accounts)
        sec = random.choice(d.securities)
        qty = Decimal(str(round(random.uniform(1, 1_000), 4)))
        ts = _random_datetime(START_DATE, END_DATE)
        side = random.choice(["buy", "sell"])
        d.trades.append({
            "trade_id": _id("TRD", i, 8),
            "investment_account_id": inv_acc["investment_account_id"],
            "security_id": sec["security_id"],
            "side": side,
            "quantity": qty,
            "trade_price": sec["current_price"] * Decimal(str(round(random.uniform(0.85, 1.15), 4))),
            "commission": _money(0, 25),
            "trade_timestamp": ts,
            "settle_date": ts.date() + timedelta(days=2),
            "status": random.choices(
                ["executed", "cancelled", "partially_filled"],
                weights=[0.93, 0.04, 0.03],
                k=1,
            )[0],
            "venue": random.choice(["NYSE", "NASDAQ", "DARK_POOL", "OTC"]),
        })


def gen_web_sessions(d: Dataset) -> None:
    devices = ["desktop", "mobile_web", "tablet"]
    browsers = ["Chrome", "Safari", "Firefox", "Edge"]
    for i in range(1, N_WEB_SESSIONS + 1):
        cust = random.choice(d.customers)
        start_ts = _random_datetime(START_DATE, END_DATE)
        duration = random.randint(15, 1_800)
        d.web_sessions.append({
            "session_id": _id("SESS", i, 9),
            "customer_id": cust["customer_id"],
            "started_at": start_ts,
            "ended_at": start_ts + timedelta(seconds=duration),
            "duration_seconds": duration,
            "device_type": random.choice(devices),
            "browser": random.choice(browsers),
            "os": random.choice(["Windows 10", "Windows 11", "macOS", "Linux", "iOS", "Android"]),
            "ip_address": _ip(),
            "user_agent": fake.user_agent(),
            "referrer": random.choice([
                "google.com", "facebook.com", "direct", "linkedin.com",
                "youtube.com", "email_campaign", "twitter.com",
            ]),
            "landing_page": random.choice([
                "/", "/personal", "/business", "/loans", "/credit-cards",
                "/wealth", "/locations", "/about",
            ]),
            "pages_viewed": random.randint(1, 25),
        })


def gen_mobile_app_events(d: Dataset) -> None:
    """Mobile-app event stream. session_id is constrained to a web_session
    owned by the same customer so customer↔session reconciliation works."""
    event_types = [
        "login", "view_balance", "transfer", "bill_pay", "deposit_check",
        "view_statements", "card_lock", "logout", "open_dispute", "search_atm",
    ]
    os_versions = [
        "iOS 17.5", "iOS 17.4", "iOS 16.7", "Android 14",
        "Android 13", "Android 12", "iOS 18.0",
    ]
    app_versions = ["8.4.1", "8.4.2", "8.5.0", "8.5.1", "9.0.0"]

    # Pre-compute customer → web session_ids index
    sessions_by_customer: dict[str, list[str]] = {}
    for s in d.web_sessions:
        sessions_by_customer.setdefault(s["customer_id"], []).append(s["session_id"])

    for i in range(1, N_MOBILE_EVENTS + 1):
        cust = random.choice(d.customers)
        ts = _weighted_datetime(START_DATE, END_DATE)
        cust_sessions = sessions_by_customer.get(cust["customer_id"])
        if cust_sessions:
            session_id = random.choice(cust_sessions)
        else:
            session_id = None
        d.mobile_app_events.append({
            "event_id": _id("EVT", i, 9),
            "customer_id": cust["customer_id"],
            "event_type": random.choice(event_types),
            "event_timestamp": ts,
            "device_os": random.choice(os_versions),
            "device_model": random.choice([
                "iPhone 15 Pro", "iPhone 14", "iPhone 13", "iPhone 12",
                "Samsung Galaxy S24", "Samsung Galaxy S23",
                "Google Pixel 8", "Google Pixel 7", "OnePlus 12",
            ]),
            "app_version": random.choice(app_versions),
            "geo_latitude": Decimal(str(round(random.uniform(25.0, 49.0), 6))),
            "geo_longitude": Decimal(str(round(random.uniform(-125.0, -70.0), 6))),
            "session_id": session_id,
            "screen_name": random.choice([
                "Home", "Accounts", "Transfer", "BillPay",
                "DepositCheck", "Statements", "CardControls", "Settings",
                "Disputes", "ATM_Finder",
            ]),
        })


def gen_login_attempts(d: Dataset) -> None:
    for i in range(1, N_LOGIN_ATTEMPTS + 1):
        cust = random.choice(d.customers)
        ts = _random_datetime(START_DATE, END_DATE)
        success = random.random() < 0.95
        d.login_attempts.append({
            "login_id": _id("LOG", i, 10),
            "customer_id": cust["customer_id"],
            "attempted_at": ts,
            "success": success,
            "failure_reason": None if success else random.choice([
                "bad_password", "mfa_failed", "account_locked",
                "expired_token", "rate_limited",
            ]),
            "channel": random.choice(["web", "mobile_app", "api"]),
            "ip_address": _ip(),
            "user_agent": fake.user_agent(),
            "mfa_method": random.choice(["sms_otp", "totp", "push", "none"]),
            "device_fingerprint": _mac(),
        })


def gen_campaigns(d: Dataset) -> None:
    types = ["email", "direct_mail", "sms", "social", "branch_referral", "in_app"]
    objectives = [
        "deposit_growth", "card_acquisition", "loan_cross_sell",
        "wealth_expansion", "retention", "reactivation",
    ]
    for i in range(1, N_CAMPAIGNS + 1):
        start = _random_date(START_DATE, END_DATE - timedelta(days=30))
        end = start + timedelta(days=random.randint(14, 90))
        d.campaigns.append({
            "campaign_id": _id("CAMP", i, 5),
            "campaign_name": f"{fake.bs().title()} {start.year}Q{(start.month - 1) // 3 + 1}",
            "channel": random.choice(types),
            "objective": random.choice(objectives),
            "start_date": start,
            "end_date": end,
            "budget": _money(5_000, 250_000),
            "target_segment": random.choice([s[0] for s in CUSTOMER_SEGMENTS]),
            "owner_employee_id": random.choice([
                e["employee_id"] for e in d.employees[:50]
            ]),
            "status": random.choice(["active", "completed", "paused"]),
        })


def gen_customer_segments_lookup(d: Dataset) -> None:
    for code, name, desc in CUSTOMER_SEGMENTS:
        d.customer_segments.append({
            "segment_code": code,
            "segment_name": name,
            "description": desc,
        })


def gen_customer_interactions(d: Dataset) -> None:
    channels = ["branch_visit", "phone_call", "chat", "email", "video_meeting", "in_app_message"]
    outcomes = ["resolved", "follow_up", "escalated", "no_action", "sale"]
    for i in range(1, N_CUSTOMER_INTERACTIONS + 1):
        cust = random.choice(d.customers)
        camp = random.choice(d.campaigns) if random.random() < 0.30 else None
        ts = _random_datetime(START_DATE, END_DATE)
        d.customer_interactions.append({
            "interaction_id": _id("INT", i, 7),
            "customer_id": cust["customer_id"],
            "campaign_id": camp["campaign_id"] if camp else None,
            "channel": random.choice(channels),
            "topic": random.choice([
                "account_inquiry", "loan_question", "card_dispute",
                "product_recommendation", "complaint", "address_change",
                "payment_assistance",
            ]),
            "employee_id": random.choice(d.employees)["employee_id"],
            "interaction_timestamp": ts,
            "duration_minutes": random.randint(1, 45),
            "outcome": random.choice(outcomes),
            "satisfaction_score": random.randint(1, 5) if random.random() < 0.7 else None,
            "notes": fake.sentence(nb_words=8),
        })


# ---------------------------------------------------------------------------
# Account-types lookup needs to write somewhere — but it's referenced by
# accounts.account_type. We emit it as part of raw_core_banking schema
# alongside customers etc. via a tuple of (schema, table, data).
# ---------------------------------------------------------------------------

def gen_account_types_lookup() -> list[dict[str, Any]]:
    return [
        {"account_type_code": code, "account_type_name": name, "product_category": cat}
        for code, name, cat in ACCOUNT_TYPES
    ]


# ---------------------------------------------------------------------------
# CSV writer
# ---------------------------------------------------------------------------

# Missing values are written as this literal rather than as an empty field so
# that both warehouses agree on what NULL means. Redshift's COPY reads it via
# `NULL AS '\\N'` and BigQuery's load via `--null_marker='\N'`. An empty field
# would not work: Redshift's EMPTYASNULL turns it into NULL, but BigQuery loads
# an unquoted empty field into a STRING column as '', which would silently
# diverge every `coalesce()` and `is null` branch in the dbt models between the
# two targets.
#
# The `dbt seed` fallback is the exception: it reads the CSVs itself and has no
# null-marker setting, so it needs the empty-field form. `--null-marker ''`
# produces it — see the `dbt-seed` Makefile target.
DEFAULT_NULL_MARKER = "\\N"

# Set from the CLI in main(); write_csv is called from ~40 places and threading
# the value through all of them would be pure noise.
_null_marker = DEFAULT_NULL_MARKER


def resolve_table(path: Path, fieldnames: list[str]) -> Table:
    """Return the registry entry for a CSV, or fail if the columns diverge.

    The registry drives both warehouses' DDL and the bq load schemas. A column
    added here but not there would load into the wrong column, or be dropped,
    with no error from either loader.
    """
    table = find_table(path.parent.name, path.stem)
    if table is None:
        raise ValueError(f"{path.parent.name}.{path.stem} is not declared in schema/registry.py")

    declared = [column.name for column in table.columns]
    if fieldnames != declared:
        raise ValueError(
            f"{path.parent.name}.{path.stem} columns do not match schema/registry.py.\n"
            f"  generated: {fieldnames}\n"
            f"  registry:  {declared}"
        )
    return table


def coerce_to_declared_type(value: Any, column: Column, table: Table) -> Any:
    """Render one value exactly as its declared column type requires.

    Redshift's COPY papers over two mismatches that BigQuery rejects outright,
    so both are normalised here rather than at each of the ~40 call sites:

    * A ``date`` in a TIMESTAMP column. ``TIMEFORMAT 'auto'`` reads a bare
      ``YYYY-MM-DD`` as midnight; BigQuery requires the time part and fails the
      whole load job without it.
    * An unquantised ``Decimal``. Division leaves values like
      ``0.6673340006673340006673340007`` (28 decimal places). COPY silently
      rounds to the column's declared scale; BigQuery rejects anything past
      NUMERIC's 9-digit scale limit, and anything past the scale declared in
      the bq load schema.

    Both coercions reproduce what Redshift was already doing implicitly, so
    neither changes that target's loaded data.
    """
    if column.type.kind == "timestamp":
        if isinstance(value, datetime):
            return value
        if isinstance(value, date):
            return datetime.combine(value, datetime.min.time())
        return value

    if column.type.kind == "date" and isinstance(value, datetime):
        return value.date()

    if column.type.kind == "decimal":
        if not isinstance(value, (Decimal, int, float)):
            return value
        quantised = Decimal(str(value)).quantize(
            Decimal(1).scaleb(-column.type.scale), rounding=ROUND_HALF_UP
        )
        digits = len(quantised.as_tuple().digits)
        if digits > column.type.precision:
            raise ValueError(
                f"{table.schema}.{table.name}.{column.name}: {quantised} needs {digits} "
                f"digits but the column is decimal({column.type.precision}, {column.type.scale})"
            )
        return quantised

    return value


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        logger.warning("No rows for %s — skipping", path)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    table = resolve_table(path, fieldnames)
    columns = {column.name: column for column in table.columns}
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    name: (
                        _null_marker
                        if value is None
                        else coerce_to_declared_type(value, columns[name], table)
                    )
                    for name, value in row.items()
                }
            )
    logger.info("Wrote %d rows → %s", len(rows), path.relative_to(SEEDS_DIR.parent))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate the banking demo's 38 raw seed CSVs (deterministic, seed=42)."
    )
    parser.add_argument(
        "--null-marker",
        default=DEFAULT_NULL_MARKER,
        help=(
            "String written for missing values. The default is what the Redshift COPY "
            "and bq load commands are configured to read. Pass an empty string for the "
            "`dbt seed` fallback, which has no null-marker setting of its own."
        ),
    )
    args = parser.parse_args()

    global _null_marker
    _null_marker = args.null_marker

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    logger.info(
        "Generating banking demo seed data (seed=%d, null marker=%r)", SEED, _null_marker
    )

    d = Dataset()

    # Generation order matters: FKs depend on earlier datasets
    logger.info("--- raw_core_banking ---")
    gen_branches(d)
    gen_employees(d)
    gen_customers(d)
    gen_customer_addresses(d)
    gen_customer_contacts(d)
    gen_accounts(d)
    gen_account_holders(d)

    logger.info("--- raw_cards (merchants + products first; cards used by transactions) ---")
    gen_merchants(d)
    gen_card_products(d)
    gen_cards(d)

    logger.info("--- raw_transactions ---")
    gen_transaction_categories(d)
    gen_transactions(d)
    gen_atm_withdrawals(d)
    gen_wire_transfers(d)
    gen_ach_transfers(d)

    logger.info("--- raw_cards: authorizations + disputes ---")
    gen_card_authorizations(d)
    gen_card_disputes(d)
    logger.info("--- raw_cards: engineered fraud + chargeback patterns ---")
    gen_fraud_burst(d)
    gen_chargeback_storm(d)

    logger.info("--- raw_lending ---")
    gen_loan_products(d)
    gen_loan_applications(d)
    gen_loans(d)
    gen_loan_payments(d)
    gen_collateral(d)

    logger.info("--- raw_risk ---")
    gen_credit_scores(d)
    gen_kyc_checks(d)
    gen_aml_alerts(d)
    gen_sanctions_screening(d)
    gen_suspicious_activity_reports(d)

    logger.info("--- raw_wealth ---")
    gen_investment_accounts(d)
    gen_securities(d)
    gen_holdings(d)
    gen_trades(d)

    logger.info("--- raw_digital ---")
    gen_web_sessions(d)
    gen_mobile_app_events(d)
    gen_login_attempts(d)

    logger.info("--- raw_marketing ---")
    gen_campaigns(d)
    gen_customer_segments_lookup(d)
    gen_customer_interactions(d)

    # ----------------------------------------------------------------------
    # Write all CSVs
    # ----------------------------------------------------------------------
    logger.info("Writing CSVs to %s", SEEDS_DIR)

    write_csv(SEEDS_DIR / "raw_core_banking" / "customers.csv",          d.customers)
    write_csv(SEEDS_DIR / "raw_core_banking" / "customer_addresses.csv", d.customer_addresses)
    write_csv(SEEDS_DIR / "raw_core_banking" / "customer_contacts.csv",  d.customer_contacts)
    write_csv(SEEDS_DIR / "raw_core_banking" / "branches.csv",           d.branches)
    write_csv(SEEDS_DIR / "raw_core_banking" / "employees.csv",          d.employees)
    write_csv(SEEDS_DIR / "raw_core_banking" / "accounts.csv",           d.accounts)
    write_csv(SEEDS_DIR / "raw_core_banking" / "account_holders.csv",    d.account_holders)

    write_csv(SEEDS_DIR / "raw_transactions" / "transactions.csv",          d.transactions)
    write_csv(SEEDS_DIR / "raw_transactions" / "transaction_categories.csv",d.transaction_categories)
    write_csv(SEEDS_DIR / "raw_transactions" / "atm_withdrawals.csv",       d.atm_withdrawals)
    write_csv(SEEDS_DIR / "raw_transactions" / "wire_transfers.csv",        d.wire_transfers)
    write_csv(SEEDS_DIR / "raw_transactions" / "ach_transfers.csv",         d.ach_transfers)

    write_csv(SEEDS_DIR / "raw_cards" / "card_products.csv",        d.card_products)
    write_csv(SEEDS_DIR / "raw_cards" / "cards.csv",                d.cards)
    write_csv(SEEDS_DIR / "raw_cards" / "card_authorizations.csv",  d.card_authorizations)
    write_csv(SEEDS_DIR / "raw_cards" / "card_disputes.csv",        d.card_disputes)
    write_csv(SEEDS_DIR / "raw_cards" / "merchants.csv",            d.merchants)

    write_csv(SEEDS_DIR / "raw_lending" / "loan_products.csv",      d.loan_products)
    write_csv(SEEDS_DIR / "raw_lending" / "loan_applications.csv",  d.loan_applications)
    write_csv(SEEDS_DIR / "raw_lending" / "loans.csv",              d.loans)
    write_csv(SEEDS_DIR / "raw_lending" / "loan_payments.csv",      d.loan_payments)
    write_csv(SEEDS_DIR / "raw_lending" / "collateral.csv",         d.collateral)

    write_csv(SEEDS_DIR / "raw_risk" / "credit_scores.csv",                 d.credit_scores)
    write_csv(SEEDS_DIR / "raw_risk" / "kyc_checks.csv",                    d.kyc_checks)
    write_csv(SEEDS_DIR / "raw_risk" / "aml_alerts.csv",                    d.aml_alerts)
    write_csv(SEEDS_DIR / "raw_risk" / "sanctions_screening.csv",           d.sanctions_screening)
    write_csv(SEEDS_DIR / "raw_risk" / "suspicious_activity_reports.csv",   d.suspicious_activity_reports)

    write_csv(SEEDS_DIR / "raw_wealth" / "investment_accounts.csv",  d.investment_accounts)
    write_csv(SEEDS_DIR / "raw_wealth" / "securities.csv",           d.securities)
    write_csv(SEEDS_DIR / "raw_wealth" / "holdings.csv",             d.holdings)
    write_csv(SEEDS_DIR / "raw_wealth" / "trades.csv",               d.trades)

    write_csv(SEEDS_DIR / "raw_digital" / "web_sessions.csv",       d.web_sessions)
    write_csv(SEEDS_DIR / "raw_digital" / "mobile_app_events.csv",  d.mobile_app_events)
    write_csv(SEEDS_DIR / "raw_digital" / "login_attempts.csv",     d.login_attempts)

    write_csv(SEEDS_DIR / "raw_marketing" / "campaigns.csv",                d.campaigns)
    write_csv(SEEDS_DIR / "raw_marketing" / "customer_segments.csv",        d.customer_segments)
    write_csv(SEEDS_DIR / "raw_marketing" / "customer_interactions.csv",    d.customer_interactions)

    # account_types lookup goes into raw_core_banking too
    write_csv(
        SEEDS_DIR / "raw_core_banking" / "account_types.csv",
        gen_account_types_lookup(),
    )

    logger.info("Done. 38 CSVs generated under %s", SEEDS_DIR)


if __name__ == "__main__":
    main()
