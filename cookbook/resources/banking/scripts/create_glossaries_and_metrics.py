"""
Create OpenMetadata Glossaries, Glossary Terms, Metrics, and PII Classifications
for the banking demo database.

Requires:
    pip install openmetadata-ingestion

Usage:
    export AI_SDK_HOST=http://localhost:8585
    export AI_SDK_TOKEN=<your-jwt-token>
    python create_glossaries_and_metrics.py

    # Or pass arguments directly:
    python create_glossaries_and_metrics.py --host http://localhost:8585 --token <jwt>

    # Custom service / database names for PII tagging:
    python create_glossaries_and_metrics.py --service banking-bigquery --database my-gcp-project
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from dataclasses import dataclass, field

from metadata.generated.schema.api.classification.createClassification import (
    CreateClassificationRequest,
)
from metadata.generated.schema.api.classification.createTag import CreateTagRequest
from metadata.generated.schema.api.data.createGlossary import CreateGlossaryRequest
from metadata.generated.schema.api.data.createGlossaryTerm import (
    CreateGlossaryTermRequest,
)
from metadata.generated.schema.api.data.createMetric import CreateMetricRequest
from metadata.generated.schema.entity.data.glossary import Glossary
from metadata.generated.schema.entity.data.glossaryTerm import GlossaryTerm
from metadata.generated.schema.entity.data.metric import (
    Language,
    Metric,
    MetricExpression,
    MetricGranularity,
    MetricType,
    UnitOfMeasurement,
)
from metadata.generated.schema.entity.data.table import Table
from metadata.generated.schema.entity.services.connections.metadata.openMetadataConnection import (
    AuthProvider,
    OpenMetadataConnection,
)
from metadata.generated.schema.entity.teams.user import User
from metadata.generated.schema.security.client.openMetadataJWTClientConfig import (
    OpenMetadataJWTClientConfig,
)
from metadata.generated.schema.type.basic import (
    EntityName,
    FullyQualifiedEntityName,
    Markdown,
)
from metadata.generated.schema.type.entityReference import EntityReference
from metadata.generated.schema.type.entityReferenceList import EntityReferenceList
from metadata.generated.schema.type.status import EntityStatus
from metadata.generated.schema.type.tagLabel import (
    LabelType,
    State,
    TagFQN,
    TagLabel,
    TagSource,
)
from metadata.ingestion.models.custom_pydantic import CustomSecretStr
from metadata.ingestion.models.table_metadata import ColumnTag
from metadata.ingestion.ometa.ometa_api import OpenMetadata

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------


def get_metadata_client(host: str, token: str) -> OpenMetadata:
    """Create and return an OpenMetadata client."""
    host_port = f"{host.rstrip('/')}/api" if not host.rstrip("/").endswith("/api") else host
    server_config = OpenMetadataConnection(
        hostPort=host_port,
        authProvider=AuthProvider.openmetadata,
        securityConfig=OpenMetadataJWTClientConfig(
            jwtToken=CustomSecretStr(token),
        ),
    )
    metadata = OpenMetadata(server_config)
    if not metadata.health_check():
        logger.error("OpenMetadata server at %s is not healthy", host)
        sys.exit(1)
    logger.info("Connected to OpenMetadata at %s", host)
    return metadata


# ---------------------------------------------------------------------------
# Glossary definitions
# ---------------------------------------------------------------------------

GLOSSARIES: list[dict] = [
    {
        "name": "BankingCore",
        "displayName": "Banking Core",
        "description": (
            "Core retail banking concepts: customers, accounts, branches, "
            "employees, and the transaction taxonomy used across the bank."
        ),
    },
    {
        "name": "LendingAndCredit",
        "displayName": "Lending and Credit",
        "description": (
            "Loan products, credit scoring, amortization, collateral, "
            "delinquency, and charge-off terminology."
        ),
    },
    {
        "name": "RiskAndAML",
        "displayName": "Risk and AML",
        "description": (
            "KYC, AML, sanctions screening, suspicious activity, and "
            "customer risk classification."
        ),
    },
    {
        "name": "WealthManagement",
        "displayName": "Wealth Management",
        "description": (
            "Investment accounts, securities, holdings, trades, and "
            "assets-under-management concepts."
        ),
    },
    {
        "name": "FinancialMetrics",
        "displayName": "Financial Metrics",
        "description": (
            "Profitability, interest income, fee income, credit loss, "
            "and balance-sheet ratio terminology used across the bank."
        ),
    },
    {
        "name": "DataPrivacyPII",
        "displayName": "Data Privacy and PII",
        "description": (
            "PII classification and data sensitivity terminology for "
            "columns containing personally identifiable information."
        ),
    },
]

# Each term: (glossary_name, name, display_name, description, parent_name | None, synonyms)
#
# Descriptions for high-importance terms (regulatory, formula-bearing, or
# PII categories) are multi-paragraph and include the relevant citation
# (FFIEC, IFRS 9, Basel III, GDPR, BSA/FinCEN, Reg E, etc.), the canonical
# formula in math/SQL notation, and example use cases.
GLOSSARY_TERMS: list[tuple[str, str, str, str, str | None, list[str]]] = [
    # ── BankingCore ─────────────────────────────────────────────────────
    # Customer hierarchy
    ("BankingCore", "Customer", "Customer",
     "A person or legal entity with a banking relationship.",
     None, ["client", "account holder"]),
    ("BankingCore", "RetailCustomer", "Retail Customer",
     "An individual customer holding personal banking products.",
     "Customer", []),
    ("BankingCore", "BusinessCustomer", "Business Customer",
     "A legal entity (LLC, corporation, partnership) holding commercial banking products.",
     "Customer", ["commercial customer"]),
    ("BankingCore", "PrivateBankingCustomer", "Private Banking Customer",
     "A high-net-worth customer served by the private banking and wealth desk.",
     "Customer", ["HNW", "private client"]),
    # Account hierarchy
    ("BankingCore", "Account", "Account",
     "A financial account held by one or more customers at the bank.",
     None, []),
    ("BankingCore", "CheckingAccount", "Checking Account",
     "A demand deposit account used for everyday transactions.",
     "Account", ["DDA", "current account"]),
    ("BankingCore", "SavingsAccount", "Savings Account",
     "An interest-bearing deposit account with limited transaction activity.",
     "Account", []),
    ("BankingCore", "MoneyMarketAccount", "Money Market Account",
     "A higher-yield deposit account that may have minimum balance requirements.",
     "Account", ["MMA"]),
    ("BankingCore", "CD", "Certificate of Deposit",
     "A time deposit account with a fixed term and interest rate.",
     "Account", ["time deposit", "certificate"]),
    ("BankingCore", "CreditCardAccount", "Credit Card Account",
     "A revolving credit account linked to one or more cards.",
     "Account", []),
    # Branch & Employee
    ("BankingCore", "Branch", "Branch",
     "A physical retail location where customers transact in person.",
     None, ["office"]),
    ("BankingCore", "Employee", "Employee",
     "A staff member of the bank, including branch and corporate personnel.",
     None, []),
    # Transaction hierarchy
    ("BankingCore", "Transaction", "Transaction",
     "Any debit, credit, or transfer posted to an account.",
     None, ["txn"]),
    ("BankingCore", "Debit", "Debit",
     "A transaction reducing the account balance (e.g., withdrawal, purchase).",
     "Transaction", ["withdrawal"]),
    ("BankingCore", "Credit", "Credit",
     "A transaction increasing the account balance (e.g., deposit, refund).",
     "Transaction", ["deposit"]),
    ("BankingCore", "Reversal", "Reversal",
     "A transaction that cancels or reverses a prior posting.",
     "Transaction", []),
    ("BankingCore", "ACH", "ACH Transfer",
     "An Automated Clearing House electronic funds transfer.",
     "Transaction", []),
    ("BankingCore", "Wire", "Wire Transfer",
     (
         "A real-time electronic funds transfer settled over Fedwire (domestic) or SWIFT "
         "(cross-border).\n\n"
         "**Regulatory context.** Wires are subject to Regulation E only for consumer "
         "remittance transfers (UCC Article 4A governs commercial wires). International "
         "wires must include a Bank Identifier Code (BIC) and either an IBAN or full "
         "originator/beneficiary information per FATF Recommendation 16 ('Travel Rule').\n\n"
         "**Risk markers.** Wires are a high-priority AML scenario because of finality, "
         "speed, and cross-border reach. The `wire_transfers` table is monitored for "
         "structuring (just-below-$10K patterns), high-risk corridors, and same-day "
         "in-then-out flow-through.\n\n"
         "**Example use cases.** Cross-border remittance, large business payments, "
         "real estate closing settlement."
     ),
     "Transaction", []),
    ("BankingCore", "ATM", "ATM Withdrawal",
     "A cash withdrawal performed at an automated teller machine.",
     "Transaction", []),

    # ── LendingAndCredit ────────────────────────────────────────────────
    # Loan hierarchy
    ("LendingAndCredit", "Loan", "Loan",
     "A credit product where the bank lends a principal amount to be repaid over time.",
     None, []),
    ("LendingAndCredit", "Mortgage", "Mortgage",
     "A loan secured by real estate used to purchase or refinance property.",
     "Loan", ["home loan"]),
    ("LendingAndCredit", "AutoLoan", "Auto Loan",
     "A loan secured by a vehicle and used to finance its purchase.",
     "Loan", []),
    ("LendingAndCredit", "PersonalLoan", "Personal Loan",
     "An unsecured installment loan for general consumer use.",
     "Loan", []),
    ("LendingAndCredit", "HELOC", "Home Equity Line of Credit",
     "A revolving line of credit secured by the equity in a residential property.",
     "Loan", []),
    ("LendingAndCredit", "BusinessLoan", "Business Loan",
     "A loan extended to a business entity for working capital or capex.",
     "Loan", ["commercial loan"]),
    # Supporting concepts
    ("LendingAndCredit", "Collateral", "Collateral",
     "An asset pledged by a borrower to secure repayment of a loan.",
     None, []),
    ("LendingAndCredit", "Principal", "Principal",
     "The original loan amount excluding interest and fees.",
     None, []),
    ("LendingAndCredit", "Interest", "Interest",
     "The cost of borrowing, expressed as a rate applied to the outstanding principal.",
     None, []),
    ("LendingAndCredit", "Amortization", "Amortization",
     "The schedule by which a loan's principal is repaid over time.",
     None, []),
    ("LendingAndCredit", "DPD", "Days Past Due",
     "The number of days a loan payment is past its scheduled due date.",
     None, ["delinquency days"]),
    ("LendingAndCredit", "Delinquency", "Delinquency",
     "A state where a loan has one or more missed or late payments.",
     None, []),
    ("LendingAndCredit", "ChargeOff", "Charge-Off",
     "A loan balance the bank no longer expects to collect and removes from active receivables.",
     None, ["write-off"]),
    ("LendingAndCredit", "FICO", "FICO Score",
     "A credit risk score produced by Fair Isaac Corporation, range 300-850.",
     None, []),
    ("LendingAndCredit", "VantageScore", "VantageScore",
     "An alternative consumer credit score produced by the three major credit bureaus.",
     None, []),
    ("LendingAndCredit", "LoanApplication", "Loan Application",
     "A formal request by a customer for a loan, subject to underwriting review.",
     None, []),
    ("LendingAndCredit", "Underwriting", "Underwriting",
     "The process of assessing borrower creditworthiness and approving loan terms.",
     None, []),

    # ── RiskAndAML ──────────────────────────────────────────────────────
    # KYC hierarchy
    ("RiskAndAML", "KYC", "Know Your Customer",
     (
         "The end-to-end process of verifying a customer's identity, beneficial "
         "ownership structure, source of funds, and risk profile before onboarding "
         "and on an ongoing basis throughout the relationship.\n\n"
         "**Regulatory citation.** US: 31 CFR §1020.220 (Customer Identification "
         "Program) and FinCEN's 2016 Customer Due Diligence Rule (31 CFR §1010.230) "
         "which adds Beneficial Ownership (UBO ≥25%) requirements. EU: Directive (EU) "
         "2015/849 (4AMLD) as amended by 2018/843 (5AMLD). Wolfsberg AML Principles "
         "set industry best practice.\n\n"
         "**Components.** Identity verification (government-issued ID, address proof), "
         "screening against sanctions (OFAC, UN, EU) and PEP lists, source-of-funds "
         "documentation, and ongoing periodic refresh (typically every 1, 3, or 5 years "
         "depending on customer risk band).\n\n"
         "**Example use cases.** New account opening, periodic refresh triggered by "
         "risk-band changes, remediation after a SAR filing."
     ),
     None, []),
    ("RiskAndAML", "CDD", "Customer Due Diligence",
     (
         "Standard identity verification and risk assessment performed at onboarding "
         "for customers in low- and medium-risk segments.\n\n"
         "**Regulatory citation.** FinCEN CDD Rule (31 CFR §1010.230), effective May 2018: "
         "(1) identify and verify the customer, (2) identify and verify beneficial owners "
         "(legal entity customers), (3) understand the nature and purpose of the "
         "relationship, and (4) conduct ongoing monitoring.\n\n"
         "**Data captured.** Full legal name, residential address, date of birth, "
         "government-issued identifier (SSN/TIN/EIN), occupation, employer, expected "
         "transaction volumes and counterparties.\n\n"
         "**Contrast with EDD.** CDD is the baseline; EDD is the elevated tier applied "
         "to high-risk customers (PEPs, high-cash businesses, foreign correspondents)."
     ),
     "KYC", []),
    ("RiskAndAML", "EDD", "Enhanced Due Diligence",
     (
         "The elevated scrutiny applied to customers classified as high-risk under the "
         "bank's risk-rating methodology, including PEPs, high-cash-intensive businesses, "
         "shell companies, foreign correspondents, and customers in high-risk "
         "jurisdictions (FATF grey/black list).\n\n"
         "**Regulatory citation.** FinCEN CDD Rule (31 CFR §1010.230), USA PATRIOT Act "
         "§312 (correspondent and private banking EDD), FATF Recommendation 10 paragraph 20. "
         "EU: 5AMLD Article 18.\n\n"
         "**Additional steps.** Senior management approval to onboard, enhanced source-of-funds "
         "and source-of-wealth documentation, more frequent KYC refresh (typically annual), "
         "elevated transaction monitoring thresholds, and quarterly account review.\n\n"
         "**Example use cases.** Onboarding a politically exposed person, "
         "non-resident customer from a FATF-listed jurisdiction, money services business."
     ),
     "KYC", []),
    # AML & reports
    ("RiskAndAML", "AMLAlert", "AML Alert",
     "An automated alert raised by transaction monitoring rules for review by analysts.",
     None, []),
    ("RiskAndAML", "SAR", "Suspicious Activity Report",
     (
         "A confidential regulatory filing reporting transactions or activity that the "
         "bank knows, suspects, or has reason to suspect involves money laundering, "
         "fraud, tax evasion, or other illegal activity.\n\n"
         "**Regulatory citation.** Bank Secrecy Act (31 USC §5318(g)), implemented at "
         "31 CFR §1020.320. Filed with FinCEN within 30 calendar days of detection "
         "(extendable to 60 days if the subject is unknown). Continuing-activity SARs "
         "must be filed every 90 days.\n\n"
         "**Mandatory thresholds.** $5,000 (transaction-based) for known suspect, "
         "$25,000 for unknown suspect, or any amount for insider abuse / unauthorized "
         "computer intrusion. No threshold for terrorist financing.\n\n"
         "**Confidentiality.** SARs are protected by 31 USC §5318(g)(2): banks must "
         "not disclose to the subject. Tipping off is a separate criminal offense.\n\n"
         "**Example use cases.** Structuring detected by transaction monitoring, "
         "sanctions evasion, unexplained wire activity, account takeover fraud."
     ),
     None, []),
    ("RiskAndAML", "CTR", "Currency Transaction Report",
     (
         "A mandatory filing for cash (currency) transactions exceeding $10,000 in a "
         "single business day by or on behalf of one person.\n\n"
         "**Regulatory citation.** Bank Secrecy Act (31 USC §5313), 31 CFR §1010.311. "
         "Form 112 is filed with FinCEN within 15 calendar days of the transaction. "
         "Aggregation rule: multiple same-day cash transactions by the same person are "
         "aggregated when their sum exceeds $10,000.\n\n"
         "**Structuring.** Splitting cash transactions to stay below $10,000 to avoid "
         "the CTR (31 USC §5324) is itself a federal crime, regardless of the underlying "
         "funds' legality. Pattern detection is a primary AML transaction-monitoring use case.\n\n"
         "**Exempt persons.** Banks may exempt certain qualified customers (Phase I/II "
         "filers) from CTRs after due diligence; FinCEN Form 110 documents the exemption."
     ),
     None, []),
    ("RiskAndAML", "Structuring", "Structuring",
     (
         "The act of breaking up cash transactions into amounts below the $10,000 CTR "
         "reporting threshold for the purpose of evading the report.\n\n"
         "**Regulatory citation.** 31 USC §5324 makes structuring a separate federal "
         "felony regardless of the underlying funds' legality (5-year sentence, "
         "10 years if part of a pattern of illegal activity > $100K/12 months). FinCEN "
         "Form 8300 covers analogous structuring in non-bank trades or businesses.\n\n"
         "**Detection patterns.** Common AML scenarios: multiple cash deposits "
         "$9,000–$9,999, deposits at different branches/ATMs on the same day, "
         "deposits across multiple related accounts, sudden change from cheque-based "
         "to cash-based business activity.\n\n"
         "**Outcome.** Confirmed structuring is filed via SAR (Form 111) and may be "
         "referred to law enforcement."
     ),
     None, []),
    ("RiskAndAML", "PEP", "Politically Exposed Person",
     "An individual with a prominent public function, requiring enhanced due diligence.",
     None, []),
    ("RiskAndAML", "SanctionsList", "Sanctions List",
     "A regulatory watchlist (e.g., OFAC, UN, EU) used to block prohibited parties.",
     None, []),
    ("RiskAndAML", "TransactionMonitoring", "Transaction Monitoring",
     "Automated review of transactions against rule-based scenarios to detect risk.",
     None, []),
    # Risk band hierarchy
    ("RiskAndAML", "RiskBand", "Risk Band",
     "A categorical assessment of customer or loan risk.",
     None, []),
    ("RiskAndAML", "LowRisk", "Low Risk",
     "A customer or exposure assessed as low likelihood of loss or compliance issue.",
     "RiskBand", []),
    ("RiskAndAML", "MediumRisk", "Medium Risk",
     "A customer or exposure with moderate likelihood of loss or compliance issue.",
     "RiskBand", []),
    ("RiskAndAML", "HighRisk", "High Risk",
     "A customer or exposure with elevated likelihood of loss or compliance issue.",
     "RiskBand", []),
    ("RiskAndAML", "CriticalRisk", "Critical Risk",
     "A customer or exposure requiring immediate escalation and remediation.",
     "RiskBand", []),
    # ── IFRS 9 staging ──────────────────────────────────────────────────
    ("RiskAndAML", "IFRS9Stage1", "IFRS 9 Stage 1",
     (
         "Performing financial assets that have not experienced a significant increase "
         "in credit risk (SICR) since initial recognition. The bank books a 12-month "
         "expected credit loss (ECL) allowance.\n\n"
         "**Regulatory citation.** IFRS 9 paragraph 5.5.5; impairment model paragraphs "
         "5.5.1–5.5.20. Issued by the IASB; effective for annual periods beginning on "
         "or after 1 January 2018.\n\n"
         "**Formula.** `Stage1_ECL = PD_12m × LGD × EAD × discount_factor`.\n\n"
         "**Example.** A current credit-card balance held by a customer with a "
         "stable risk grade since origination. Interest revenue is recognised on the "
         "gross carrying amount (effective interest rate × gross balance)."
     ),
     "RiskBand", []),
    ("RiskAndAML", "IFRS9Stage2", "IFRS 9 Stage 2",
     (
         "Performing financial assets that have experienced a significant increase in "
         "credit risk (SICR) since initial recognition, but are not yet credit-impaired. "
         "The bank books a lifetime expected credit loss (ECL) allowance.\n\n"
         "**Regulatory citation.** IFRS 9 paragraph 5.5.3; SICR criteria in paragraph "
         "B5.5.17. The 30-days-past-due rebuttable presumption is set in paragraph 5.5.11.\n\n"
         "**Formula.** `Stage2_ECL = sum over lifetime t of [PD_t × LGD_t × EAD_t × DF_t]`.\n\n"
         "**SICR triggers (examples).** PD doubling since origination, credit-grade "
         "downgrade by ≥2 notches, 30+ DPD, forbearance, watch-list addition.\n\n"
         "**Example.** A loan that moved from 0 DPD to 45 DPD; or a borrower whose "
         "industry sector has been downgraded by the bank's economic outlook model."
     ),
     "RiskBand", []),
    ("RiskAndAML", "IFRS9Stage3", "IFRS 9 Stage 3",
     (
         "Credit-impaired financial assets (i.e., default has occurred). Lifetime ECL "
         "is computed and interest revenue is recognised on the net carrying amount "
         "(gross less allowance).\n\n"
         "**Regulatory citation.** IFRS 9 paragraph 5.5.13; default definition aligned "
         "with paragraph B5.5.37 (90+ DPD rebuttable presumption) and CRR Article 178 "
         "for EU banks. Aligned with the prudential definition of non-performing "
         "exposure (EBA/GL/2016/07).\n\n"
         "**Formula.** `Stage3_ECL = sum over lifetime t of [PD_t × LGD_t × EAD_t × DF_t]` "
         "where PD ≈ 1 for already-defaulted exposures.\n\n"
         "**Outcomes.** Reported as Non-Performing Loans (NPLs); collection, restructuring, "
         "or charge-off processes initiated. Cure period (typically 90+ days of consistent "
         "performance) required to migrate back to Stage 2."
     ),
     "RiskBand", []),
    # ── Capital & Liquidity (Basel III) ─────────────────────────────────
    ("RiskAndAML", "BaselIII", "Basel III",
     (
         "A global regulatory framework issued by the Basel Committee on Banking "
         "Supervision (BCBS) covering capital adequacy, leverage, liquidity, and "
         "large-exposure limits for internationally active banks.\n\n"
         "**Components.** Capital (CET1/Tier 1/Total ratios, capital conservation and "
         "countercyclical buffers, SIFI surcharge), Liquidity (LCR, NSFR), Leverage "
         "(LR), and Large Exposures.\n\n"
         "**Regulatory citation.** BCBS Basel III: A global regulatory framework for "
         "more resilient banks and banking systems (Dec 2010, revised 2011). Implemented "
         "in the US via the Federal Reserve's Regulation Q (12 CFR Part 217); in the EU "
         "via CRR/CRD (Regulation (EU) 575/2013, as amended by CRR2/CRR3).\n\n"
         "**Successor.** Basel III final reforms ('Basel IV', BCBS d424, Dec 2017) "
         "introduce a standardised-approach output floor and revisions to credit, "
         "market, and operational risk RWAs, phasing in 2023–2028."
     ),
     None, []),
    ("RiskAndAML", "RegulatoryCapital", "Regulatory Capital",
     (
         "Capital recognised under prudential regulation as available to absorb losses, "
         "stratified into CET1, Additional Tier 1, Tier 2, and total capital. Distinct "
         "from accounting equity.\n\n"
         "**Regulatory citation.** US: 12 CFR Part 217 (Federal Reserve Reg Q). EU: CRR "
         "Articles 25–91. Basel III standard: BCBS document d189.\n\n"
         "**Composition.** CET1 = common shares + retained earnings + AOCI − goodwill "
         "− DTAs − other regulatory deductions. AT1 includes perpetual contingent-convertible "
         "instruments. Tier 2 includes subordinated debt with original maturity ≥ 5 years."
     ),
     None, []),
    ("RiskAndAML", "CET1Ratio", "Common Equity Tier 1 Ratio",
     (
         "Common Equity Tier 1 capital divided by risk-weighted assets (RWA), expressed "
         "as a percentage. The highest-quality regulatory-capital ratio.\n\n"
         "**Formula.** `CET1 Ratio = CET1 Capital / RWA × 100`.\n\n"
         "**Regulatory minimum.** 4.5% under Basel III, plus a 2.5% capital conservation "
         "buffer (so practical minimum ≈ 7.0% before MDA restrictions). Global SIFIs add "
         "1.0–3.5% surcharge per FSB methodology. Countercyclical buffer 0–2.5% set by "
         "national supervisors (US Federal Reserve, EU national authorities).\n\n"
         "**Citation.** 12 CFR §217.10 (US); CRR Article 92(1)(a) (EU).\n\n"
         "**Example.** A US bank holding company with $20bn CET1 and $200bn RWA reports "
         "CET1 ratio = 10.0%."
     ),
     None, []),
    ("RiskAndAML", "Tier1Ratio", "Tier 1 Capital Ratio",
     (
         "Tier 1 capital (CET1 + Additional Tier 1) divided by risk-weighted assets, "
         "expressed as a percentage.\n\n"
         "**Formula.** `Tier1 Ratio = (CET1 + AT1) / RWA × 100`.\n\n"
         "**Regulatory minimum.** 6.0% under Basel III (CRR Article 92(1)(b); "
         "12 CFR §217.10).\n\n"
         "**Example.** A US bank holding company with $20bn CET1, $2bn AT1, and "
         "$200bn RWA reports Tier 1 ratio = 11.0%."
     ),
     None, []),
    ("RiskAndAML", "RWA", "Risk-Weighted Assets",
     (
         "On- and off-balance-sheet exposures multiplied by their applicable risk weights, "
         "summing across credit risk, market risk, and operational risk. The denominator "
         "of all Basel capital ratios.\n\n"
         "**Approaches.** Credit risk RWAs computed under the Standardised Approach "
         "(prescribed risk weights) or Internal Ratings-Based (foundation/advanced IRB). "
         "Market risk under SA-FRTB (Basel d424) or Internal Model Approach. Operational "
         "risk under SMA (Basel III final reforms).\n\n"
         "**Citation.** CRR Part Three (EU); 12 CFR §§217.30–.124 (US).\n\n"
         "**Example.** A $1m residential mortgage at 50% risk weight contributes $500K to "
         "credit-risk RWA; an unsecured corporate loan to an unrated SME at 100% contributes "
         "$1m."
     ),
     None, []),
    ("RiskAndAML", "LCR", "Liquidity Coverage Ratio",
     (
         "High-Quality Liquid Assets (HQLA) divided by net cash outflows over a 30-day "
         "severe-stress horizon. A short-term liquidity-resilience standard.\n\n"
         "**Formula.** `LCR = HQLA / Net Cash Outflows (30d stress)`.\n\n"
         "**Regulatory minimum.** 100% under Basel III (BCBS d238). US: 12 CFR Part 249 "
         "(Federal Reserve Reg WW), applied to LISCC, Category I–IV firms with thresholds. "
         "EU: CRR Article 412 and Commission Delegated Regulation (EU) 2015/61.\n\n"
         "**HQLA tiers.** Level 1 (cash, central-bank reserves, sovereigns 0% RW): no haircut. "
         "Level 2A (15% haircut, ≤40% of HQLA): high-quality sovereigns/corporates. "
         "Level 2B (25–50% haircut, ≤15% of HQLA): RMBS, corporate equities, lower-rated "
         "corporates.\n\n"
         "**Companion.** Net Stable Funding Ratio (NSFR) provides a 1-year structural-funding "
         "view."
     ),
     None, []),
    ("RiskAndAML", "CreditRisk", "Credit Risk",
     (
         "The risk of loss due to a counterparty failing to meet contractual obligations. "
         "Captured for capital purposes through PD × LGD × EAD and for accounting purposes "
         "through IFRS 9 / CECL ECL.\n\n"
         "**Regulatory framework.** Basel III credit risk standard (SA / F-IRB / A-IRB), "
         "supplemented by Basel III final reforms (BCBS d424).\n\n"
         "**Components.** Default risk, recovery risk (LGD), exposure dynamics (EAD on "
         "off-balance-sheet commitments), counterparty credit risk on derivatives "
         "(SA-CCR per BCBS d279)."
     ),
     None, []),
    ("RiskAndAML", "MarketRisk", "Market Risk",
     (
         "The risk of loss from movements in market prices: interest rates, FX, equity "
         "prices, commodity prices, and credit spreads on trading-book positions.\n\n"
         "**Regulatory framework.** Fundamental Review of the Trading Book (FRTB, BCBS d352 "
         "and d457): Standardised Approach (sensitivities-based + Default Risk Charge + "
         "Residual Risk Add-on) or Internal Model Approach (expected shortfall, P&L "
         "attribution tests).\n\n"
         "**US implementation.** 12 CFR §§217.201–217.212 (interim final). EU: CRR2 Article 325."
     ),
     None, []),
    ("RiskAndAML", "OperationalRisk", "Operational Risk",
     (
         "The risk of loss resulting from inadequate or failed internal processes, people "
         "and systems, or external events (including legal risk and conduct risk; excluding "
         "strategic and reputational risk).\n\n"
         "**Regulatory framework.** Basel III final reforms (BCBS d424) replaces "
         "AMA/BIA/TSA with a single Standardised Measurement Approach (SMA) based on the "
         "Business Indicator and the Internal Loss Multiplier.\n\n"
         "**Example events.** Internal fraud, external fraud, employment practices, "
         "clients/products/business practices, damage to physical assets, business "
         "disruption and system failures, execution/delivery/process management."
     ),
     None, []),
    # ── CECL (US GAAP IFRS-9 analogue) ──────────────────────────────────
    ("RiskAndAML", "CECL", "Current Expected Credit Losses",
     (
         "The US GAAP credit-loss accounting model that requires recognition of lifetime "
         "expected credit losses on all in-scope financial assets at origination/purchase, "
         "rather than waiting for losses to be probable.\n\n"
         "**Regulatory citation.** FASB ASC 326 (Financial Instruments — Credit Losses), "
         "ASU 2016-13 effective for SEC filers 1 Jan 2020 (delayed for smaller "
         "reporters). Replaces the incurred-loss model under ASC 310/450.\n\n"
         "**Contrast with IFRS 9.** CECL requires lifetime ECL from day 1 for all assets "
         "(no staging); IFRS 9 uses 12-month ECL in Stage 1 and lifetime ECL only after "
         "SICR. Both use PD × LGD × EAD building blocks.\n\n"
         "**Scope.** Loans held for investment, debt securities held-to-maturity, trade "
         "receivables, off-balance-sheet credit exposures (commitments, financial guarantees)."
     ),
     None, []),

    # ── WealthManagement ────────────────────────────────────────────────
    ("WealthManagement", "InvestmentAccount", "Investment Account",
     "A brokerage or advisory account holding securities on behalf of a customer.",
     None, []),
    ("WealthManagement", "Holding", "Holding",
     "A specific security position held within an investment account.",
     None, ["position"]),
    # Security hierarchy
    ("WealthManagement", "Security", "Security",
     "A tradable financial instrument such as a stock, bond, mutual fund, or ETF.",
     None, ["instrument"]),
    ("WealthManagement", "Equity", "Equity",
     "An ownership share in a publicly or privately traded company.",
     "Security", ["stock", "share"]),
    ("WealthManagement", "Bond", "Bond",
     "A debt security with fixed or floating coupon payments and a maturity.",
     "Security", []),
    ("WealthManagement", "MutualFund", "Mutual Fund",
     "A pooled investment vehicle priced once per day at net asset value.",
     "Security", []),
    ("WealthManagement", "ETF", "Exchange-Traded Fund",
     "A pooled investment vehicle traded intraday on an exchange.",
     "Security", []),
    ("WealthManagement", "AUM", "Assets Under Management",
     "The total market value of customer assets managed by the wealth business.",
     None, []),
    ("WealthManagement", "Trade", "Trade",
     "An executed buy or sell order of a security within an investment account.",
     None, []),

    # ── FinancialMetrics ────────────────────────────────────────────────
    ("FinancialMetrics", "NIM", "Net Interest Margin",
     (
         "Net interest income divided by average interest-earning assets, expressed as "
         "a percentage. A primary measure of bank profitability from intermediation.\n\n"
         "**Formula.** `NIM = (Interest Income − Interest Expense) / Average Earning Assets × 100`.\n\n"
         "**FFIEC reporting.** Computed on the Call Report (FFIEC 031/041), Schedule RI-A. "
         "FDIC publishes quarterly bank-level and aggregate NIM in the Quarterly Banking Profile.\n\n"
         "**Drivers.** Asset yield (loan rates, securities yield, deposit balances at the "
         "Fed), funding cost (deposit rates, FHLB advances, wholesale funding), balance-sheet "
         "mix, and the rate environment.\n\n"
         "**Example use cases.** Tracking yield-curve sensitivity, profitability by "
         "branch/region, comparison vs peer banks of similar asset size and business mix."
     ),
     None, []),
    ("FinancialMetrics", "NII", "Net Interest Income",
     "Interest income minus interest expense.",
     None, []),
    # Non-interest income hierarchy
    ("FinancialMetrics", "NonInterestIncome", "Non-Interest Income",
     "Revenue from fees, commissions, and other non-interest sources.",
     None, ["fee income"]),
    ("FinancialMetrics", "FeeIncome", "Fee Income",
     "Service fees collected from customers (account, ATM, wire, overdraft, etc.).",
     "NonInterestIncome", []),
    ("FinancialMetrics", "OverdraftFee", "Overdraft Fee",
     "A fee charged when an account is overdrawn or processed against insufficient funds.",
     "FeeIncome", []),
    ("FinancialMetrics", "ChargeOffRate", "Charge-Off Rate",
     "Net charge-offs divided by average outstanding loans, expressed as a percentage.",
     None, []),
    # ── New profitability / capital ratios ─────────────────────────────
    ("FinancialMetrics", "CostToIncomeRatio", "Cost-to-Income Ratio",
     (
         "Operating expense divided by total revenue (net interest income plus "
         "non-interest income). A measure of operating efficiency: lower is better.\n\n"
         "**Formula.** `Cost-to-Income = Non-Interest Expense / (NII + Non-Interest Income) × 100`.\n\n"
         "**Benchmarks.** Best-in-class universal banks operate near 50%; "
         "regional US banks typically 55–65%. Above 70% signals efficiency concerns."
     ),
     None, ["efficiency ratio"]),
    ("FinancialMetrics", "EfficiencyRatio", "Efficiency Ratio",
     (
         "Alias for Cost-to-Income Ratio used in US bank reporting (FDIC, FFIEC). "
         "Non-interest expense divided by the sum of net interest income and "
         "non-interest income.\n\n"
         "**Formula.** `Efficiency Ratio = Non-Interest Expense / (NII + Non-Interest Income) × 100`."
     ),
     None, []),
    ("FinancialMetrics", "ROA", "Return on Assets",
     (
         "Net income divided by average total assets, expressed as a percentage. "
         "Measures profitability relative to the bank's asset base.\n\n"
         "**Formula.** `ROA = Net Income / Average Total Assets × 100`.\n\n"
         "**Benchmark.** A 'well-run' US community/regional bank typically targets 1.0%+ "
         "ROA; large-cap money-center banks often 0.8–1.2%."
     ),
     None, []),
    ("FinancialMetrics", "ROE", "Return on Equity",
     (
         "Net income divided by average common shareholders' equity, expressed as a "
         "percentage. The headline shareholder-return metric.\n\n"
         "**Formula.** `ROE = Net Income / Average Common Equity × 100`.\n\n"
         "**Benchmark.** Cost of equity for large US banks is typically 9–11%; ROE above "
         "cost of equity creates shareholder value.\n\n"
         "**DuPont decomposition.** `ROE = ROA × Equity Multiplier = (Net Income / Assets) × "
         "(Assets / Equity)`. Higher leverage boosts ROE but also risk."
     ),
     None, []),
    ("FinancialMetrics", "CET1Ratio", "CET1 Ratio (Metric)",
     (
         "Common Equity Tier 1 capital divided by risk-weighted assets, the headline "
         "Basel III capital-adequacy ratio. See `RiskAndAML.CET1Ratio` for the full "
         "regulatory definition.\n\n"
         "**Formula.** `CET1 Ratio = CET1 Capital / RWA × 100`."
     ),
     None, []),
    # ECL hierarchy
    ("FinancialMetrics", "ECL", "Expected Credit Loss",
     (
         "The probability-weighted estimate of credit losses over the life of a financial "
         "instrument, computed as `ECL = PD × LGD × EAD` (discounted to present value at "
         "the effective interest rate).\n\n"
         "**Regulatory citation.** IFRS 9 paragraphs 5.5.17–5.5.20 (IASB); US GAAP "
         "equivalent is CECL (FASB ASC 326). Required by IASB for all reporting periods "
         "beginning on or after 1 Jan 2018; CECL effective 1 Jan 2020 for SEC filers.\n\n"
         "**Formula (one-period).** `ECL = PD × LGD × EAD × discount_factor`.\n\n"
         "**Formula (lifetime).** `Lifetime ECL = sum over t of [PD_t × LGD_t × EAD_t × DF_t]` "
         "where t ranges over remaining contractual periods.\n\n"
         "**Use case.** Booked monthly as an allowance for credit losses on loans, debt "
         "securities, and off-balance-sheet commitments. Movements are reported in P&L "
         "as the 'provision for credit losses'."
     ),
     None, []),
    ("FinancialMetrics", "PD", "Probability of Default",
     (
         "The probability that an obligor will default on contractual obligations within "
         "a given horizon (12-month PD for Basel and IFRS 9 Stage 1; lifetime PD for "
         "IFRS 9 Stage 2/3 and CECL).\n\n"
         "**Regulatory citation.** Basel III credit risk standard (12 CFR Part 217 / "
         "CRR Article 178); IFRS 9 paragraph B5.5.41; CECL ASC 326-20.\n\n"
         "**Default definition.** 90+ days past due (rebuttable) or unlikely to pay (e.g. "
         "specific provision, restructuring with loss, bankruptcy).\n\n"
         "**Estimation.** Cohort-based historical default rates with point-in-time vs "
         "through-the-cycle calibration; logistic regression / GBM scoring; macroeconomic "
         "overlays."
     ),
     "ECL", []),
    ("FinancialMetrics", "LGD", "Loss Given Default",
     (
         "The fraction of EAD that is lost if a default occurs, after recoveries from "
         "collateral, guarantees, and workout. `LGD = 1 − Recovery Rate`.\n\n"
         "**Regulatory citation.** Basel III A-IRB approach (CRR Article 181), IFRS 9 "
         "paragraph B5.5.55, CECL ASC 326-20-30.\n\n"
         "**Drivers.** Collateral type and seniority, jurisdiction (foreclosure speed), "
         "macro conditions at workout. Workout LGD vs market-implied LGD are alternatives.\n\n"
         "**Typical values.** Senior secured corporate: 25–45%. Unsecured corporate: 60–75%. "
         "Residential mortgage: 15–25%. Credit card: 60–75%."
     ),
     "ECL", []),
    ("FinancialMetrics", "EAD", "Exposure at Default",
     (
         "The expected outstanding exposure at the moment of default, including drawn "
         "balance and expected drawdown of committed but undrawn lines (credit conversion "
         "factor, CCF).\n\n"
         "**Regulatory citation.** Basel III credit risk standard (CRR Article 166); "
         "IFRS 9 paragraph B5.5.46.\n\n"
         "**Formula.** `EAD = Drawn + CCF × Undrawn`.\n\n"
         "**CCF examples.** Unconditionally cancellable retail commitments: 10%. "
         "Off-balance-sheet commitments ≤1 year: 20%. Off-balance-sheet commitments >1 year: 50%. "
         "Direct credit substitutes (e.g. financial guarantees): 100%."
     ),
     "ECL", []),
    ("FinancialMetrics", "NPLRatio", "Non-Performing Loan Ratio",
     (
         "Non-performing loans divided by gross outstanding loans, expressed as a "
         "percentage. The primary asset-quality indicator.\n\n"
         "**Formula.** `NPL Ratio = NPL Balance / Total Gross Loans × 100`.\n\n"
         "**Definition of NPL.** EBA harmonised: 90+ DPD or unlikely-to-pay (EBA/GL/2016/07, "
         "aligned with CRR Article 178). US regulatory: 'nonaccrual' loans (FFIEC Call "
         "Report Schedule RC-N).\n\n"
         "**Benchmark.** US large banks typically <1%; stressed regimes (post-GFC EU "
         "periphery) saw 10–40%."
     ),
     None, []),
    ("FinancialMetrics", "LDR", "Loan-to-Deposit Ratio",
     "Total outstanding loans divided by total customer deposits.",
     None, []),

    # ── DataPrivacyPII ──────────────────────────────────────────────────
    ("DataPrivacyPII", "PII", "PII",
     (
         "Personally Identifiable Information — any data that can directly or indirectly "
         "identify a natural person, alone or in combination with other reasonably "
         "available data.\n\n"
         "**Regulatory citations.**\n"
         "- US: GLBA Safeguards Rule (16 CFR Part 314), NIST SP 800-122, state breach-"
         "notification laws (e.g. California Civil Code §1798.82).\n"
         "- EU: GDPR Article 4(1) defines 'personal data' (functionally equivalent, with "
         "stricter scope and rights).\n"
         "- California: CCPA/CPRA defines 'personal information' (Cal. Civ. Code §1798.140).\n\n"
         "**Direct identifiers.** Name, SSN/TIN, passport number, IBAN, account number, "
         "biometric data, photograph.\n\n"
         "**Indirect identifiers.** ZIP code, date of birth, gender (the well-known "
         "Sweeney study: 87% of US population uniquely identified by ZIP + DOB + gender)."
     ),
     None, ["personal data"]),
    ("DataPrivacyPII", "SSN", "Social Security Number",
     (
         "A US Social Security Number — a 9-digit identifier (`AAA-GG-SSSS`) issued by "
         "the Social Security Administration. The last 4 digits ('SSN4') are also "
         "considered PII when combined with other identifying data.\n\n"
         "**Regulatory citation.** GLBA Safeguards Rule (16 CFR Part 314); state SSN "
         "protection laws (e.g. NY Gen Bus Law §399-ddd). NIST SP 800-122 classifies SSN "
         "as 'high impact' PII.\n\n"
         "**Handling rules.** Must be encrypted at rest and in transit; masked in UIs "
         "(typically `XXX-XX-####`); access tightly controlled; never logged.\n\n"
         "**In this dataset.** Stored in `raw_core_banking.customers.ssn` (column tagged "
         "PII.Sensitive)."
     ),
     "PII", []),
    ("DataPrivacyPII", "DOB", "Date of Birth",
     (
         "The birth date of an individual. A quasi-identifier that combined with ZIP "
         "code and gender uniquely identifies 87% of the US population.\n\n"
         "**Regulatory citation.** GDPR Article 4(1) (personal data); GLBA Safeguards Rule. "
         "Used as a KBA factor at multiple banks — but its widespread breach exposure "
         "(see Equifax 2017) limits its standalone authentication value.\n\n"
         "**In this dataset.** Stored in `raw_core_banking.customers.date_of_birth`."
     ),
     "PII", []),
    ("DataPrivacyPII", "EmailAddress", "Email Address",
     "An electronic mail address used for communication.",
     "PII", []),
    ("DataPrivacyPII", "PhoneNumber", "Phone Number",
     "A telephone or mobile contact number.",
     "PII", []),
    ("DataPrivacyPII", "PhysicalAddress", "Physical Address",
     "Street address, city, state, and postal code.",
     "PII", []),
    ("DataPrivacyPII", "IPAddress", "IP Address",
     "Internet Protocol address identifying a network connection.",
     "PII", []),
    ("DataPrivacyPII", "PaymentCardInfo", "Payment Card Info",
     "Credit/debit card details such as PAN, last four digits, expiry, and CVV.",
     "PII", ["PCI data"]),
    ("DataPrivacyPII", "IBAN", "IBAN",
     (
         "International Bank Account Number — a standardised account identifier defined "
         "by ISO 13616 used for cross-border payments. Length varies by country (15–34 "
         "alphanumeric characters; UK = 22, DE = 22, ES = 24, etc.).\n\n"
         "**Structure.** `[Country code 2][Check digits 2][BBAN — bank+branch+account]`. "
         "Always validated with ISO 7064 MOD-97-10.\n\n"
         "**Companion identifier.** BIC/SWIFT code (ISO 9362, 8 or 11 alphanumeric) "
         "identifies the bank. SEPA payments require IBAN + BIC; FATF Recommendation 16 "
         "('Travel Rule') requires both for cross-border wires.\n\n"
         "**In this dataset.** Stored in `raw_transactions.wire_transfers.from_iban` and "
         "`.to_iban`."
     ),
     "PII", []),
    ("DataPrivacyPII", "SWIFT", "SWIFT/BIC Code",
     (
         "Business Identifier Code (ISO 9362) used by the SWIFT network to route "
         "cross-border financial messages. 8 characters (institution + country + location) "
         "or 11 characters (with branch code).\n\n"
         "**Companion.** Always paired with IBAN for SEPA / cross-border wires per "
         "FATF Recommendation 16."
     ),
     "PII", ["BIC"]),
    ("DataPrivacyPII", "TaxID", "Tax ID",
     "A government-issued tax identification number (e.g., EIN, TIN).",
     "PII", ["EIN"]),
    ("DataPrivacyPII", "MothersMaidenName", "Mother's Maiden Name",
     "A common knowledge-based authentication factor and PII element.",
     "PII", []),
    ("DataPrivacyPII", "BeneficialOwner", "Beneficial Owner",
     "An individual who ultimately owns or controls a legal entity (>=25% threshold per FinCEN).",
     "PII", ["UBO"]),
    ("DataPrivacyPII", "GeoLocation", "Geolocation",
     "GPS coordinates or precise location data tied to a customer or device.",
     "PII", []),
    # ── GDPR / CCPA conceptual terms ────────────────────────────────────
    ("DataPrivacyPII", "DataSubject", "Data Subject",
     (
         "An identified or identifiable natural person whose personal data is processed. "
         "Under CCPA/CPRA called a 'consumer' (Cal. Civ. Code §1798.140(g)).\n\n"
         "**Regulatory citation.** GDPR Article 4(1).\n\n"
         "**Rights.** Subjects have rights to access (Article 15), rectification "
         "(Article 16), erasure (Article 17, 'right to be forgotten'), restriction "
         "(Article 18), portability (Article 20), and to object (Article 21)."
     ),
     None, ["consumer"]),
    ("DataPrivacyPII", "Controller", "Data Controller",
     (
         "The natural or legal person, public authority, agency or other body which, "
         "alone or jointly with others, determines the purposes and means of the "
         "processing of personal data.\n\n"
         "**Regulatory citation.** GDPR Article 4(7); CCPA equivalent is 'business' "
         "(Cal. Civ. Code §1798.140(d)).\n\n"
         "**Accountability.** The controller bears primary accountability for compliance "
         "(GDPR Article 24) and must demonstrate compliance with the data-protection "
         "principles in Article 5."
     ),
     None, []),
    ("DataPrivacyPII", "Processor", "Data Processor",
     (
         "A natural or legal person, public authority, agency or other body which "
         "processes personal data on behalf of the controller.\n\n"
         "**Regulatory citation.** GDPR Article 4(8); contract-required obligations in "
         "Article 28 (data processing agreement / DPA).\n\n"
         "**Example.** A cloud-hosted CRM is a processor; the bank using it is the "
         "controller. The processor must follow the controller's documented instructions "
         "and may only engage sub-processors with the controller's authorisation."
     ),
     None, []),
    ("DataPrivacyPII", "LawfulBasis", "Lawful Basis of Processing",
     (
         "One of six grounds under GDPR Article 6(1) that legitimises the processing of "
         "personal data: (a) consent, (b) contract necessity, (c) legal obligation, "
         "(d) vital interests, (e) public interest, (f) legitimate interests.\n\n"
         "**Regulatory citation.** GDPR Article 6 (general data); Article 9 (special "
         "categories, e.g. health, biometric); Article 10 (criminal-conviction data).\n\n"
         "**Banking application.** Account opening: contract (6(1)(b)). KYC/AML/SAR "
         "filings: legal obligation (6(1)(c)). Marketing: consent (6(1)(a)) or legitimate "
         "interests (6(1)(f)) with opt-out."
     ),
     None, ["legal basis"]),
    ("DataPrivacyPII", "GDPRArticle6", "GDPR Article 6",
     (
         "The GDPR provision that enumerates the six lawful bases for processing "
         "personal data. Without one of these, processing is unlawful.\n\n"
         "**Citation.** Regulation (EU) 2016/679 Article 6(1)(a)–(f)."
     ),
     "LawfulBasis", []),
    ("DataPrivacyPII", "DSAR", "Data Subject Access Request",
     (
         "A formal request by a data subject to a controller to obtain confirmation of "
         "processing and a copy of the personal data being processed, along with metadata "
         "(purposes, categories, recipients, retention, etc.).\n\n"
         "**Regulatory citation.** GDPR Article 15 (right of access). Controller must "
         "respond within 1 month (extendable by 2 months for complex requests, GDPR "
         "Article 12(3)). Generally free of charge (Article 12(5)).\n\n"
         "**CCPA equivalent.** Cal. Civ. Code §1798.110 (right to know) and §1798.130 "
         "(verifiable request). 45-day response window (extendable to 90 days).\n\n"
         "**Example use cases.** Banking customer requests all data the bank holds about "
         "them — required for transparency and to enable downstream rights (rectification, "
         "erasure, portability)."
     ),
     None, ["subject access request", "SAR (privacy)"]),
    ("DataPrivacyPII", "RightToErasure", "Right to Erasure",
     (
         "The data subject's right to obtain the deletion of their personal data without "
         "undue delay, when one of six grounds applies (no longer necessary; consent "
         "withdrawn; objection; unlawful processing; legal obligation; child consent).\n\n"
         "**Regulatory citation.** GDPR Article 17 (Right to be Forgotten).\n\n"
         "**CCPA equivalent.** Cal. Civ. Code §1798.105 (right to delete).\n\n"
         "**Banking exemption.** Right does not apply when processing is necessary for "
         "compliance with a legal obligation (Article 17(3)(b)) — e.g., BSA 5-year "
         "transaction-record retention, 31 CFR §1010.430; SOX 7-year retention, "
         "15 USC §7241."
     ),
     None, ["right to be forgotten"]),
    ("DataPrivacyPII", "CCPAOptOut", "CCPA Right to Opt Out",
     (
         "A California consumer's right to direct a business not to sell or share their "
         "personal information, exercised via a 'Do Not Sell or Share My Personal "
         "Information' link on the business's homepage.\n\n"
         "**Regulatory citation.** California Civil Code §1798.120 (sale opt-out) and "
         "§1798.135 (notice / link requirement); CPRA amendments 2023 added 'sharing' "
         "(cross-context behavioural advertising).\n\n"
         "**GPC.** Global Privacy Control header signals opt-out; California AG "
         "regulations (Cal. Code Regs. tit. 11 §7025) require honoring GPC as a valid "
         "opt-out signal."
     ),
     None, ["DNS"]),
]


# ---------------------------------------------------------------------------
# Metric definitions
# ---------------------------------------------------------------------------

# (name, display_name, description, metric_type, unit, granularity, sql, related)
METRICS: list[tuple[str, str, str, MetricType, UnitOfMeasurement, MetricGranularity, str, list[str]]] = [
    # ── Profitability ───────────────────────────────────────────────────
    (
        "net_interest_margin",
        "Net Interest Margin",
        "Net interest income divided by average earning assets, expressed as a percentage.",
        MetricType.PERCENTAGE,
        UnitOfMeasurement.PERCENTAGE,
        MetricGranularity.MONTH,
        "SELECT period_month, nim_pct\n"
        "FROM marts_finance.fct_nim",
        [],
    ),
    (
        "net_interest_income",
        "Net Interest Income",
        "Interest income minus interest expense for the period.",
        MetricType.SUM,
        UnitOfMeasurement.DOLLARS,
        MetricGranularity.MONTH,
        "SELECT period_month, net_interest_income\n"
        "FROM marts_finance.fct_nim",
        ["net_interest_margin"],
    ),
    (
        "total_interest_income",
        "Total Interest Income",
        "Gross interest revenue earned on loans and investment securities.",
        MetricType.SUM,
        UnitOfMeasurement.DOLLARS,
        MetricGranularity.MONTH,
        "SELECT period_month, interest_income\n"
        "FROM marts_finance.fct_nim",
        ["net_interest_income"],
    ),

    # ── Fee Revenue ─────────────────────────────────────────────────────
    (
        "fee_revenue",
        "Fee Revenue",
        "Total non-interest fee revenue, broken down by fee category.",
        MetricType.SUM,
        UnitOfMeasurement.DOLLARS,
        MetricGranularity.MONTH,
        "SELECT period_month, fee_category, SUM(fee_amount) AS fee_revenue\n"
        "FROM marts_finance.fct_fee_revenue\n"
        "GROUP BY 1, 2",
        [],
    ),
    (
        "overdraft_fee_revenue",
        "Overdraft Fee Revenue",
        "Fee revenue from overdraft and non-sufficient-funds events.",
        MetricType.SUM,
        UnitOfMeasurement.DOLLARS,
        MetricGranularity.MONTH,
        "SELECT period_month, SUM(fee_amount) AS overdraft_fee_revenue\n"
        "FROM marts_finance.fct_fee_revenue\n"
        "WHERE fee_category = 'overdraft'\n"
        "GROUP BY 1",
        ["fee_revenue"],
    ),
    (
        "atm_fee_revenue",
        "ATM Fee Revenue",
        "Fee revenue from ATM withdrawals at foreign or out-of-network machines.",
        MetricType.SUM,
        UnitOfMeasurement.DOLLARS,
        MetricGranularity.MONTH,
        "SELECT period_month, SUM(fee_amount) AS atm_fee_revenue\n"
        "FROM marts_finance.fct_fee_revenue\n"
        "WHERE fee_category = 'atm'\n"
        "GROUP BY 1",
        ["fee_revenue"],
    ),
    (
        "wire_fee_revenue",
        "Wire Fee Revenue",
        "Fee revenue from domestic and international wire transfer charges.",
        MetricType.SUM,
        UnitOfMeasurement.DOLLARS,
        MetricGranularity.MONTH,
        "SELECT period_month, SUM(fee_amount) AS wire_fee_revenue\n"
        "FROM marts_finance.fct_fee_revenue\n"
        "WHERE fee_category = 'wire'\n"
        "GROUP BY 1",
        ["fee_revenue"],
    ),
    (
        "card_interchange_revenue",
        "Card Interchange Revenue",
        "Interchange revenue earned on card transactions from merchant payments.",
        MetricType.SUM,
        UnitOfMeasurement.DOLLARS,
        MetricGranularity.MONTH,
        "SELECT period_month, SUM(fee_amount) AS card_interchange_revenue\n"
        "FROM marts_finance.fct_fee_revenue\n"
        "WHERE fee_category = 'interchange'\n"
        "GROUP BY 1",
        ["fee_revenue"],
    ),

    # ── Credit Risk ─────────────────────────────────────────────────────
    (
        "npl_ratio",
        "Non-Performing Loan Ratio",
        "Non-performing loans divided by total outstanding loans, expressed as a percentage.",
        MetricType.PERCENTAGE,
        UnitOfMeasurement.PERCENTAGE,
        MetricGranularity.MONTH,
        "SELECT period_month, npl_ratio\n"
        "FROM marts_risk.fct_delinquency",
        [],
    ),
    (
        "charge_off_rate",
        "Charge-Off Rate",
        "Net charge-offs divided by average outstanding loans, expressed as a percentage.",
        MetricType.PERCENTAGE,
        UnitOfMeasurement.PERCENTAGE,
        MetricGranularity.MONTH,
        "SELECT period_month, product_code,\n"
        "       SUM(CASE WHEN delinquency_bucket = 'charge_off' THEN total_balance END)\n"
        "         / NULLIF(SUM(total_balance), 0) * 100 AS charge_off_rate\n"
        "FROM marts_risk.fct_delinquency\n"
        "GROUP BY 1, 2",
        ["npl_ratio"],
    ),
    (
        "ecl_total",
        "Expected Credit Loss (Total)",
        "Total expected credit loss provisioning across the loan book.",
        MetricType.SUM,
        UnitOfMeasurement.DOLLARS,
        MetricGranularity.MONTH,
        "SELECT date_trunc('month', current_date) AS period_month,\n"
        "       SUM(expected_credit_loss) AS ecl_total\n"
        "FROM marts_risk.fct_loan_loss_provision",
        [],
    ),
    (
        "ecl_coverage_ratio",
        "ECL Coverage Ratio",
        "Expected credit loss divided by total non-performing loans, expressed as a percentage.",
        MetricType.PERCENTAGE,
        UnitOfMeasurement.PERCENTAGE,
        MetricGranularity.MONTH,
        "SELECT date_trunc('month', current_date)::date AS period_month,\n"
        "       SUM(p.expected_credit_loss)\n"
        "         / NULLIF((\n"
        "             SELECT SUM(total_balance) FROM marts_risk.fct_delinquency\n"
        "             WHERE delinquency_bucket IN ('dpd_90_plus', 'charge_off')\n"
        "           ), 0) * 100 AS ecl_coverage_ratio\n"
        "FROM marts_risk.fct_loan_loss_provision p",
        ["ecl_total", "npl_ratio"],
    ),

    # ── Balance Sheet ───────────────────────────────────────────────────
    (
        "loan_to_deposit_ratio",
        "Loan-to-Deposit Ratio",
        "Total outstanding loans divided by total customer deposits, expressed as a percentage.",
        MetricType.PERCENTAGE,
        UnitOfMeasurement.PERCENTAGE,
        MetricGranularity.MONTH,
        "SELECT date_trunc('month', current_date)::date AS period_month,\n"
        "       (SELECT SUM(balance) FROM staging.stg_lending__loans\n"
        "        WHERE status NOT IN ('paid_off','charged_off'))\n"
        "         / NULLIF(\n"
        "           (SELECT SUM(balance) FROM intermediate.int_accounts__enriched\n"
        "            WHERE product_category IN ('deposit','savings','checking')\n"
        "              AND balance > 0), 0) * 100 AS loan_to_deposit_ratio",
        [],
    ),
    (
        "deposit_growth_rate",
        "Deposit Growth Rate",
        "Month-over-month percentage growth in total customer deposits.",
        MetricType.PERCENTAGE,
        UnitOfMeasurement.PERCENTAGE,
        MetricGranularity.MONTH,
        "WITH monthly_deposits AS (\n"
        "    SELECT date_trunc('month', balance_date)::date AS period_month,\n"
        "           SUM(end_of_day_balance) AS deposit_balance\n"
        "    FROM marts_finance.fct_daily_balances\n"
        "    WHERE product_category IN ('deposit','savings','checking')\n"
        "      AND end_of_day_balance > 0\n"
        "    GROUP BY 1\n"
        ")\n"
        "SELECT period_month,\n"
        "       (deposit_balance - LAG(deposit_balance) OVER (ORDER BY period_month))\n"
        "         / NULLIF(LAG(deposit_balance) OVER (ORDER BY period_month), 0) * 100\n"
        "         AS deposit_growth_pct\n"
        "FROM monthly_deposits",
        ["loan_to_deposit_ratio"],
    ),
    (
        "loan_origination_volume",
        "Loan Origination Volume",
        "Total dollar volume of new loans originated in the period.",
        MetricType.SUM,
        UnitOfMeasurement.DOLLARS,
        MetricGranularity.MONTH,
        "SELECT date_trunc('month', origination_date)::date AS period_month,\n"
        "       SUM(principal) AS loan_origination_volume\n"
        "FROM staging.stg_lending__loans\n"
        "WHERE origination_date IS NOT NULL\n"
        "GROUP BY 1",
        [],
    ),
    (
        "average_loan_balance",
        "Average Loan Balance",
        "Average outstanding loan balance across the active loan book.",
        MetricType.AVERAGE,
        UnitOfMeasurement.DOLLARS,
        MetricGranularity.MONTH,
        "SELECT date_trunc('month', current_date)::date AS period_month,\n"
        "       AVG(balance) AS average_loan_balance\n"
        "FROM staging.stg_lending__loans\n"
        "WHERE status NOT IN ('paid_off','charged_off')",
        ["loan_origination_volume"],
    ),

    # ── Customers & Accounts ────────────────────────────────────────────
    (
        "active_customer_count",
        "Active Customer Count",
        "Distinct customers with at least one active account.",
        MetricType.COUNT,
        UnitOfMeasurement.COUNT,
        MetricGranularity.MONTH,
        "SELECT date_trunc('month', current_date) AS period_month,\n"
        "       COUNT(DISTINCT customer_id) AS active_customer_count\n"
        "FROM marts_core.dim_customers\n"
        "WHERE account_count > 0",
        [],
    ),
    (
        "dormant_account_rate",
        "Dormant Account Rate",
        "Percentage of accounts flagged as dormant (no activity in 12+ months).",
        MetricType.PERCENTAGE,
        UnitOfMeasurement.PERCENTAGE,
        MetricGranularity.MONTH,
        "SELECT date_trunc('month', current_date)::date AS period_month,\n"
        "       COUNT(CASE WHEN status = 'dormant' THEN 1 END)::float\n"
        "           / NULLIF(COUNT(*), 0) * 100 AS dormant_account_rate\n"
        "FROM marts_core.dim_accounts",
        ["active_customer_count"],
    ),
    (
        "average_account_balance",
        "Average Account Balance",
        "Mean balance across all active deposit accounts.",
        MetricType.AVERAGE,
        UnitOfMeasurement.DOLLARS,
        MetricGranularity.MONTH,
        "SELECT date_trunc('month', current_date)::date AS period_month,\n"
        "       AVG(balance) AS average_account_balance\n"
        "FROM marts_core.dim_accounts\n"
        "WHERE product_category IN ('checking', 'savings', 'money_market')\n"
        "  AND status = 'active'",
        [],
    ),

    # ── Compliance & AML ────────────────────────────────────────────────
    (
        "aml_alert_rate",
        "AML Alert Rate",
        "AML alerts raised as a percentage of total transactions screened.",
        MetricType.PERCENTAGE,
        UnitOfMeasurement.PERCENTAGE,
        MetricGranularity.MONTH,
        "SELECT a.period_month,\n"
        "       a.alerts_count::float / NULLIF(t.transaction_count, 0) * 100\n"
        "           AS aml_alert_rate\n"
        "FROM marts_risk.fct_aml_pipeline a\n"
        "LEFT JOIN (\n"
        "    SELECT date_trunc('month', posted_at)::date AS period_month,\n"
        "           COUNT(*) AS transaction_count\n"
        "    FROM marts_core.fct_transactions\n"
        "    GROUP BY 1\n"
        ") t ON a.period_month = t.period_month",
        [],
    ),
    (
        "sar_filing_rate",
        "SAR Filing Rate",
        "Percentage of AML alerts that resulted in a Suspicious Activity Report filing.",
        MetricType.PERCENTAGE,
        UnitOfMeasurement.PERCENTAGE,
        MetricGranularity.MONTH,
        "SELECT period_month,\n"
        "       sar_filed_count::float / NULLIF(alerts_count, 0) * 100 AS sar_filing_rate\n"
        "FROM marts_risk.fct_aml_pipeline",
        ["aml_alert_rate"],
    ),
    (
        "kyc_refresh_compliance",
        "KYC Refresh Compliance",
        "Percentage of customers with up-to-date KYC documentation per refresh policy.",
        MetricType.PERCENTAGE,
        UnitOfMeasurement.PERCENTAGE,
        MetricGranularity.MONTH,
        "SELECT date_trunc('month', current_date) AS period_month,\n"
        "       COUNT(CASE WHEN kyc_status = 'current' THEN 1 END)::float\n"
        "           / NULLIF(COUNT(*), 0) * 100 AS kyc_refresh_compliance\n"
        "FROM marts_risk.dim_credit_risk",
        [],
    ),

    # ── Wealth Management ───────────────────────────────────────────────
    (
        "aum_total",
        "Assets Under Management (Total)",
        "Total market value of customer assets managed by the wealth business.",
        MetricType.SUM,
        UnitOfMeasurement.DOLLARS,
        MetricGranularity.MONTH,
        "SELECT period_month, SUM(aum) AS aum_total\n"
        "FROM marts_wealth.fct_aum\n"
        "GROUP BY 1",
        [],
    ),
    (
        "aum_growth_rate",
        "AUM Growth Rate",
        "Month-over-month percentage growth in total assets under management.",
        MetricType.PERCENTAGE,
        UnitOfMeasurement.PERCENTAGE,
        MetricGranularity.MONTH,
        "WITH monthly_aum AS (\n"
        "    SELECT period_month, SUM(aum) AS aum_total\n"
        "    FROM marts_wealth.fct_aum\n"
        "    GROUP BY period_month\n"
        ")\n"
        "SELECT period_month,\n"
        "       (aum_total - LAG(aum_total) OVER (ORDER BY period_month))\n"
        "         / NULLIF(LAG(aum_total) OVER (ORDER BY period_month), 0) * 100\n"
        "         AS aum_growth_pct\n"
        "FROM monthly_aum",
        ["aum_total"],
    ),
    (
        "trade_volume",
        "Trade Volume",
        "Total notional dollar volume of executed trades.",
        MetricType.SUM,
        UnitOfMeasurement.DOLLARS,
        MetricGranularity.MONTH,
        "SELECT period_month, SUM(total_volume) AS trade_volume\n"
        "FROM marts_wealth.fct_trades\n"
        "GROUP BY 1",
        ["aum_total"],
    ),
    (
        "average_trade_size",
        "Average Trade Size",
        "Mean notional value per executed trade.",
        MetricType.AVERAGE,
        UnitOfMeasurement.DOLLARS,
        MetricGranularity.MONTH,
        "SELECT period_month,\n"
        "       SUM(total_volume)::float / NULLIF(SUM(trade_count), 0) AS average_trade_size\n"
        "FROM marts_wealth.fct_trades\n"
        "GROUP BY 1",
        ["trade_volume"],
    ),

    # ── Marketing & Digital ─────────────────────────────────────────────
    (
        "campaign_conversion_rate",
        "Campaign Conversion Rate",
        "Percentage of campaign-targeted customers who completed the intended action.",
        MetricType.PERCENTAGE,
        UnitOfMeasurement.PERCENTAGE,
        MetricGranularity.MONTH,
        "SELECT date_trunc('month', current_date)::date AS period_month,\n"
        "       SUM(attributed_account_openings)::float\n"
        "         / NULLIF(SUM(interactions_count), 0) * 100\n"
        "           AS campaign_conversion_rate\n"
        "FROM marts_marketing.fct_campaign_attribution",
        [],
    ),
    (
        "mobile_dau",
        "Mobile DAU",
        "Daily active users of the mobile banking app.",
        MetricType.COUNT,
        UnitOfMeasurement.COUNT,
        MetricGranularity.DAY,
        "SELECT cast(event_timestamp as date) AS event_date,\n"
        "       COUNT(DISTINCT customer_id) AS mobile_dau\n"
        "FROM staging.stg_digital__mobile_app_events\n"
        "GROUP BY 1",
        [],
    ),
    (
        "mobile_mau",
        "Mobile MAU",
        "Monthly active users of the mobile banking app.",
        MetricType.COUNT,
        UnitOfMeasurement.COUNT,
        MetricGranularity.MONTH,
        "SELECT date_trunc('month', event_timestamp)::date AS period_month,\n"
        "       COUNT(DISTINCT customer_id) AS mobile_mau\n"
        "FROM staging.stg_digital__mobile_app_events\n"
        "GROUP BY 1",
        ["mobile_dau"],
    ),
    (
        "login_failure_rate",
        "Login Failure Rate",
        "Percentage of login attempts that failed authentication.",
        MetricType.PERCENTAGE,
        UnitOfMeasurement.PERCENTAGE,
        MetricGranularity.DAY,
        "SELECT cast(attempted_at as date) AS attempt_date,\n"
        "       COUNT(CASE WHEN NOT success THEN 1 END)::float\n"
        "           / NULLIF(COUNT(*), 0) * 100 AS login_failure_rate\n"
        "FROM staging.stg_digital__login_attempts\n"
        "GROUP BY 1",
        [],
    ),

    # ── Profitability & Capital Ratios (new) ────────────────────────────
    # NOTE: fct_monthly_pnl materialises interest_income, fee_income,
    # interest_expense, non_interest_expense, and net_income. Total assets,
    # equity, and RWA are NOT materialised — for ROA, ROE, and CET1 we use
    # sentinel denominators so the metric still returns a non-NULL value;
    # replace the denominators when a balance-sheet mart is built.
    (
        "cost_to_income_ratio",
        "Cost-to-Income Ratio",
        "Non-interest expense divided by total revenue (NII + non-interest income), expressed as a percentage. Lower is better.",
        MetricType.PERCENTAGE,
        UnitOfMeasurement.PERCENTAGE,
        MetricGranularity.MONTH,
        "SELECT period_month,\n"
        "       non_interest_expense\n"
        "         / NULLIF(\n"
        "             (interest_income - interest_expense) + fee_income, 0\n"
        "           ) * 100 AS cost_to_income_ratio\n"
        "FROM marts_finance.fct_monthly_pnl",
        ["net_interest_income"],
    ),
    (
        "efficiency_ratio",
        "Efficiency Ratio",
        "Alias for Cost-to-Income Ratio used in US bank reporting (FDIC, FFIEC).",
        MetricType.PERCENTAGE,
        UnitOfMeasurement.PERCENTAGE,
        MetricGranularity.MONTH,
        "SELECT period_month,\n"
        "       non_interest_expense\n"
        "         / NULLIF(\n"
        "             (interest_income - interest_expense) + fee_income, 0\n"
        "           ) * 100 AS efficiency_ratio\n"
        "FROM marts_finance.fct_monthly_pnl",
        ["cost_to_income_ratio"],
    ),
    (
        "return_on_assets",
        "Return on Assets",
        "Net income divided by average total assets, expressed as a percentage.",
        MetricType.PERCENTAGE,
        UnitOfMeasurement.PERCENTAGE,
        MetricGranularity.MONTH,
        # Placeholder: total assets is not materialised. Approximate using
        # net_income scaled by an assumed asset base of $1e9 (illustrative
        # only) so the metric is non-NULL and dashboards render.
        "SELECT period_month,\n"
        "       net_income / 1e9 * 100 AS return_on_assets\n"
        "FROM marts_finance.fct_monthly_pnl\n"
        "-- TODO: replace the $1e9 sentinel with the actual\n"
        "-- average-total-assets column once a balance-sheet mart exists.",
        ["net_interest_income"],
    ),
    (
        "return_on_equity",
        "Return on Equity",
        "Net income divided by average common shareholders' equity, expressed as a percentage.",
        MetricType.PERCENTAGE,
        UnitOfMeasurement.PERCENTAGE,
        MetricGranularity.MONTH,
        # Placeholder: equity is not materialised. Approximate using
        # net_income scaled by an assumed equity base of $1e8 (illustrative
        # only).
        "SELECT period_month,\n"
        "       net_income / 1e8 * 100 AS return_on_equity\n"
        "FROM marts_finance.fct_monthly_pnl\n"
        "-- TODO: replace the $1e8 sentinel with the actual\n"
        "-- average-common-equity column once a balance-sheet mart exists.",
        ["return_on_assets"],
    ),
    (
        "cet1_ratio",
        "CET1 Ratio",
        "Common Equity Tier 1 capital divided by risk-weighted assets, expressed as a percentage.",
        MetricType.PERCENTAGE,
        UnitOfMeasurement.PERCENTAGE,
        MetricGranularity.MONTH,
        # Placeholder: neither CET1 capital nor RWA are materialised in
        # this dataset. The metric returns a constant 12.0 (a typical
        # large-US-bank CET1) for each month so the metric is non-NULL.
        "SELECT period_month,\n"
        "       12.0 AS cet1_ratio\n"
        "FROM marts_finance.fct_monthly_pnl\n"
        "-- TODO: replace constant 12.0 with cet1_capital / rwa * 100\n"
        "-- once a regulatory-capital mart exists.",
        [],
    ),
]


# ---------------------------------------------------------------------------
# Metric → glossary term linkage
# ---------------------------------------------------------------------------
#
# Each metric name maps to the list of glossary-term FQNs that define the
# business concept it implements. OpenMetadata represents this linkage by
# attaching the glossary term as a TagLabel (source = Glossary) on the
# metric entity — the same mechanism used to tag a column.

METRIC_GLOSSARY_TERMS: dict[str, list[str]] = {
    # Profitability
    "net_interest_margin": ["FinancialMetrics.NIM"],
    "net_interest_income": ["FinancialMetrics.NII"],
    "total_interest_income": ["FinancialMetrics.NII"],
    "cost_to_income_ratio": [
        "FinancialMetrics.CostToIncomeRatio",
        "FinancialMetrics.EfficiencyRatio",
    ],
    "efficiency_ratio": [
        "FinancialMetrics.EfficiencyRatio",
        "FinancialMetrics.CostToIncomeRatio",
    ],
    "return_on_assets": ["FinancialMetrics.ROA"],
    "return_on_equity": ["FinancialMetrics.ROE"],
    "cet1_ratio": ["FinancialMetrics.CET1Ratio", "RiskAndAML.CET1Ratio"],
    # Fee revenue
    "fee_revenue": ["FinancialMetrics.FeeIncome", "FinancialMetrics.NonInterestIncome"],
    "overdraft_fee_revenue": ["FinancialMetrics.OverdraftFee"],
    "atm_fee_revenue": ["FinancialMetrics.FeeIncome", "BankingCore.ATM"],
    "wire_fee_revenue": ["FinancialMetrics.FeeIncome", "BankingCore.Wire"],
    "card_interchange_revenue": ["FinancialMetrics.FeeIncome"],
    # Credit risk
    "npl_ratio": ["FinancialMetrics.NPLRatio", "RiskAndAML.IFRS9Stage3"],
    "charge_off_rate": [
        "FinancialMetrics.ChargeOffRate",
        "LendingAndCredit.ChargeOff",
    ],
    "ecl_total": [
        "FinancialMetrics.ECL",
        "FinancialMetrics.PD",
        "FinancialMetrics.LGD",
        "FinancialMetrics.EAD",
        "RiskAndAML.CECL",
    ],
    "ecl_coverage_ratio": ["FinancialMetrics.ECL", "FinancialMetrics.NPLRatio"],
    # Balance sheet
    "loan_to_deposit_ratio": [
        "FinancialMetrics.LDR",
        "LendingAndCredit.Loan",
        "BankingCore.SavingsAccount",
    ],
    "deposit_growth_rate": ["BankingCore.SavingsAccount", "BankingCore.CheckingAccount"],
    "loan_origination_volume": ["LendingAndCredit.Loan"],
    "average_loan_balance": ["LendingAndCredit.Loan", "LendingAndCredit.Principal"],
    # Customers & accounts
    "active_customer_count": ["BankingCore.Customer"],
    "dormant_account_rate": ["BankingCore.Account"],
    "average_account_balance": ["BankingCore.Account"],
    # Compliance & AML
    "aml_alert_rate": ["RiskAndAML.AMLAlert", "RiskAndAML.TransactionMonitoring"],
    "sar_filing_rate": ["RiskAndAML.SAR", "RiskAndAML.AMLAlert"],
    "kyc_refresh_compliance": ["RiskAndAML.KYC", "RiskAndAML.CDD"],
    # Wealth
    "aum_total": ["WealthManagement.AUM"],
    "aum_growth_rate": ["WealthManagement.AUM"],
    "trade_volume": ["WealthManagement.Trade"],
    "average_trade_size": ["WealthManagement.Trade"],
    # Marketing & digital
    "campaign_conversion_rate": [],
    "mobile_dau": [],
    "mobile_mau": [],
    "login_failure_rate": [],
}


# ---------------------------------------------------------------------------
# Metric → owner mapping  (user name)
# ---------------------------------------------------------------------------

METRIC_OWNERS: dict[str, str] = {
    # Profitability + Balance Sheet metrics → CFO (robert.garcia)
    "net_interest_margin": "robert.garcia",
    "net_interest_income": "robert.garcia",
    "total_interest_income": "robert.garcia",
    "cost_to_income_ratio": "robert.garcia",
    "efficiency_ratio": "robert.garcia",
    "return_on_assets": "robert.garcia",
    "return_on_equity": "robert.garcia",
    "cet1_ratio": "robert.garcia",
    "fee_revenue": "robert.garcia",
    "overdraft_fee_revenue": "robert.garcia",
    "atm_fee_revenue": "robert.garcia",
    "wire_fee_revenue": "robert.garcia",
    "card_interchange_revenue": "robert.garcia",
    "loan_to_deposit_ratio": "robert.garcia",
    "deposit_growth_rate": "robert.garcia",
    "loan_origination_volume": "robert.garcia",
    "average_loan_balance": "robert.garcia",
    # Credit Risk + ECL metrics → Head of Credit Risk (marcus.williams)
    "npl_ratio": "marcus.williams",
    "charge_off_rate": "marcus.williams",
    "ecl_total": "marcus.williams",
    "ecl_coverage_ratio": "marcus.williams",
    # Compliance + AML metrics → Chief Compliance Officer (david.kim)
    "aml_alert_rate": "david.kim",
    "sar_filing_rate": "david.kim",
    "kyc_refresh_compliance": "david.kim",
    # Wealth metrics → Head of Wealth (priya.patel)
    "aum_total": "priya.patel",
    "aum_growth_rate": "priya.patel",
    "trade_volume": "priya.patel",
    "average_trade_size": "priya.patel",
    # Customers + Marketing + Digital metrics → Data Steward (alice.chen)
    "active_customer_count": "alice.chen",
    "dormant_account_rate": "alice.chen",
    "average_account_balance": "alice.chen",
    "campaign_conversion_rate": "alice.chen",
    "mobile_dau": "alice.chen",
    "mobile_mau": "alice.chen",
    "login_failure_rate": "alice.chen",
}


# ---------------------------------------------------------------------------
# Glossary → reviewer user
# ---------------------------------------------------------------------------

GLOSSARY_REVIEWERS: dict[str, str] = {
    "BankingCore": "alice.chen",
    "LendingAndCredit": "marcus.williams",
    "RiskAndAML": "david.kim",
    "WealthManagement": "priya.patel",
    "FinancialMetrics": "robert.garcia",
    "DataPrivacyPII": "alice.chen",
}


# ---------------------------------------------------------------------------
# Classifications & Tags
# ---------------------------------------------------------------------------
#
# Top-level classifications carry sensitivity / regulatory tags that are
# applied to columns. Each entry: (name, displayName, description,
# mutuallyExclusive flag).

CLASSIFICATIONS: list[dict] = [
    {
        "name": "PII",
        "displayName": "PII",
        "description": (
            "Personally Identifiable Information classifications used to "
            "indicate the sensitivity tier of columns containing personal data."
        ),
        "mutuallyExclusive": True,
    },
    {
        "name": "Banking",
        "displayName": "Banking",
        "description": (
            "Banking and regulatory classifications used to indicate "
            "applicable supervisory frameworks (FFIEC, IFRS 9, BSA/AML, GDPR)."
        ),
        "mutuallyExclusive": False,
    },
]


# Each tag: (classification_name, tag_name, display_name, description).
TAGS: list[tuple[str, str, str, str]] = [
    # PII sensitivity tiers
    ("PII", "Sensitive", "Sensitive PII",
     "High-sensitivity PII that, if disclosed, would create a substantial risk of "
     "identity theft, fraud, or regulatory harm. Examples: SSN, full payment card "
     "numbers, government IDs, biometric data."),
    ("PII", "NonSensitive", "Non-Sensitive PII",
     "PII whose disclosure poses limited harm in isolation but may become sensitive "
     "in combination with other identifiers. Examples: name, public email, public "
     "title."),
    ("PII", "Restricted", "Restricted PII",
     "PII subject to specific regulatory restrictions on collection, processing, "
     "or sharing — e.g., children's data (COPPA), health data (HIPAA), or special "
     "categories under GDPR Article 9."),
    # Banking / regulatory tiers
    ("Banking", "RestrictedAML", "AML Restricted",
     "Data restricted to authorised AML/BSA Compliance personnel — e.g., SAR "
     "narratives, suspect identifiers, ongoing-investigation flags."),
    ("Banking", "FFIEC", "FFIEC",
     "Data subject to FFIEC reporting standards (Call Report, Quarterly Banking "
     "Profile)."),
    ("Banking", "IFRS9", "IFRS 9",
     "Data used in IFRS 9 expected-credit-loss measurement and staging."),
    ("Banking", "GDPR", "GDPR",
     "Data subject to GDPR (Regulation (EU) 2016/679) processing requirements."),
]


# ---------------------------------------------------------------------------
# PII column tagging
# ---------------------------------------------------------------------------
#
# Each entry: (schema, table, column, [tag FQNs to apply]).
# Tag FQNs use the dot-form `<classification>.<tag>` for classification tags
# or `<glossary>.<term>` for glossary terms. Source is inferred from the
# prefix: tags whose classification name matches a CLASSIFICATIONS entry are
# treated as classification tags; otherwise they are treated as glossary terms.

_CLASSIFICATION_NAMES = {c["name"] for c in CLASSIFICATIONS}


PII_COLUMN_TAGS: list[tuple[str, str, str, list[str]]] = [
    # raw_core_banking
    ("raw_core_banking", "customers", "ssn",
     ["PII.Sensitive", "DataPrivacyPII.SSN"]),
    ("raw_core_banking", "customers", "tax_id",
     ["PII.Sensitive", "DataPrivacyPII.TaxID"]),
    ("raw_core_banking", "customers", "email",
     ["PII.Sensitive", "DataPrivacyPII.EmailAddress"]),
    ("raw_core_banking", "customers", "phone",
     ["PII.Sensitive", "DataPrivacyPII.PhoneNumber"]),
    ("raw_core_banking", "customers", "date_of_birth",
     ["PII.Sensitive", "DataPrivacyPII.DOB"]),
    # customer_contacts is a multi-purpose contact-value column. We mark
    # it Sensitive but the per-row glossary term (email vs phone) depends
    # on the contact_type. Since OpenMetadata column tags cannot vary by
    # row value, we apply the strongest applicable PII term (EmailAddress)
    # and accept that PhoneNumber rows are over-classified; the safer
    # default for sensitivity tooling.
    ("raw_core_banking", "customer_contacts", "contact_value",
     ["PII.Sensitive", "DataPrivacyPII.EmailAddress",
      "DataPrivacyPII.PhoneNumber"]),
    ("raw_core_banking", "customer_addresses", "address_line_1",
     ["PII.Sensitive", "DataPrivacyPII.PhysicalAddress"]),
    ("raw_core_banking", "customer_addresses", "address_line_2",
     ["PII.Sensitive", "DataPrivacyPII.PhysicalAddress"]),
    ("raw_core_banking", "customer_addresses", "city",
     ["PII.Sensitive", "DataPrivacyPII.PhysicalAddress"]),
    ("raw_core_banking", "customer_addresses", "state",
     ["PII.Sensitive", "DataPrivacyPII.PhysicalAddress"]),
    ("raw_core_banking", "customer_addresses", "postal_code",
     ["PII.Sensitive", "DataPrivacyPII.PhysicalAddress"]),
    # raw_cards
    ("raw_cards", "cards", "card_number_masked",
     ["PII.Sensitive", "DataPrivacyPII.PaymentCardInfo"]),
    ("raw_cards", "card_authorizations", "ip_address",
     ["PII.Sensitive", "DataPrivacyPII.IPAddress"]),
    # raw_digital
    ("raw_digital", "web_sessions", "ip_address",
     ["PII.Sensitive", "DataPrivacyPII.IPAddress"]),
    ("raw_digital", "login_attempts", "ip_address",
     ["PII.Sensitive", "DataPrivacyPII.IPAddress"]),
    ("raw_digital", "mobile_app_events", "geo_latitude",
     ["PII.Sensitive", "DataPrivacyPII.GeoLocation"]),
    ("raw_digital", "mobile_app_events", "geo_longitude",
     ["PII.Sensitive", "DataPrivacyPII.GeoLocation"]),
    # raw_transactions
    ("raw_transactions", "wire_transfers", "from_iban",
     ["PII.Sensitive", "DataPrivacyPII.IBAN"]),
    ("raw_transactions", "wire_transfers", "to_iban",
     ["PII.Sensitive", "DataPrivacyPII.IBAN"]),
]


# ---------------------------------------------------------------------------
# Creation helpers
# ---------------------------------------------------------------------------


@dataclass
class CreationResult:
    """Track created and failed entities across all entity types."""

    glossaries_created: list[str] = field(default_factory=list)
    glossaries_failed: list[str] = field(default_factory=list)
    terms_created: list[str] = field(default_factory=list)
    terms_failed: list[str] = field(default_factory=list)
    metrics_created: list[str] = field(default_factory=list)
    metrics_failed: list[str] = field(default_factory=list)
    metrics_linked: list[str] = field(default_factory=list)
    metrics_link_failed: list[str] = field(default_factory=list)
    classifications_created: list[str] = field(default_factory=list)
    classifications_failed: list[str] = field(default_factory=list)
    tags_created: list[str] = field(default_factory=list)
    tags_failed: list[str] = field(default_factory=list)
    columns_tagged: list[str] = field(default_factory=list)
    columns_tag_failed: list[str] = field(default_factory=list)

    @property
    def has_failures(self) -> bool:
        return bool(
            self.glossaries_failed
            or self.terms_failed
            or self.metrics_failed
            or self.metrics_link_failed
            or self.classifications_failed
            or self.tags_failed
            or self.columns_tag_failed
        )

    def print_summary(self) -> None:
        total_ok = (
            len(self.glossaries_created)
            + len(self.terms_created)
            + len(self.metrics_created)
            + len(self.classifications_created)
            + len(self.tags_created)
            + len(self.columns_tagged)
        )
        total_fail = (
            len(self.glossaries_failed)
            + len(self.terms_failed)
            + len(self.metrics_failed)
            + len(self.classifications_failed)
            + len(self.tags_failed)
            + len(self.columns_tag_failed)
        )

        logger.info("")
        logger.info("=" * 60)
        logger.info("SUMMARY")
        logger.info("=" * 60)
        logger.info(
            "Glossaries      : %d created, %d failed (of %d)",
            len(self.glossaries_created),
            len(self.glossaries_failed),
            len(GLOSSARIES),
        )
        logger.info(
            "Glossary Terms  : %d created, %d failed (of %d)",
            len(self.terms_created),
            len(self.terms_failed),
            len(GLOSSARY_TERMS),
        )
        logger.info(
            "Metrics         : %d created, %d failed (of %d)",
            len(self.metrics_created),
            len(self.metrics_failed),
            len(METRICS),
        )
        logger.info(
            "Metric Links    : %d linked, %d failed",
            len(self.metrics_linked),
            len(self.metrics_link_failed),
        )
        logger.info(
            "Classifications : %d created, %d failed (of %d)",
            len(self.classifications_created),
            len(self.classifications_failed),
            len(CLASSIFICATIONS),
        )
        logger.info(
            "Tags            : %d created, %d failed (of %d)",
            len(self.tags_created),
            len(self.tags_failed),
            len(TAGS),
        )
        logger.info(
            "Columns Tagged  : %d tagged, %d failed (of %d)",
            len(self.columns_tagged),
            len(self.columns_tag_failed),
            len(PII_COLUMN_TAGS),
        )
        logger.info("-" * 60)
        logger.info("Total           : %d succeeded, %d failed", total_ok, total_fail)

        if self.glossaries_failed:
            logger.warning("Failed glossaries: %s", ", ".join(self.glossaries_failed))
        if self.terms_failed:
            logger.warning("Failed terms: %s", ", ".join(self.terms_failed))
        if self.metrics_failed:
            logger.warning("Failed metrics: %s", ", ".join(self.metrics_failed))
        if self.metrics_link_failed:
            logger.warning(
                "Failed metric links: %s", ", ".join(self.metrics_link_failed)
            )
        if self.classifications_failed:
            logger.warning(
                "Failed classifications: %s", ", ".join(self.classifications_failed)
            )
        if self.tags_failed:
            logger.warning("Failed tags: %s", ", ".join(self.tags_failed))
        if self.columns_tag_failed:
            logger.warning(
                "Failed column tagging: %s", ", ".join(self.columns_tag_failed)
            )

        if not self.has_failures:
            logger.info("All entities created successfully.")
        logger.info("=" * 60)


def _custom_unit_for_metric(name: str, unit: UnitOfMeasurement) -> str | None:
    """Return the custom unit string when unit is OTHER, else None."""
    if unit != UnitOfMeasurement.OTHER:
        return None
    if "rating" in name or "satisfaction" in name:
        return "score"
    return "hours"


def fetch_users(
    metadata: OpenMetadata, user_names: list[str]
) -> dict[str, User]:
    """Look up users by name (the local part of the email)."""
    user_map: dict[str, User] = {}
    for name in user_names:
        try:
            user = metadata.get_by_name(entity=User, fqn=name)
        except Exception:
            logger.exception("Failed to fetch user: %s", name)
            continue
        if user is None:
            logger.warning(
                "User %s not found in OpenMetadata — owner/reviewer assignment "
                "for this user will be skipped. Run create_owners_and_domains.py first.",
                name,
            )
            continue
        user_map[name] = user
    return user_map


def _owners_for_user(user: User | None) -> EntityReferenceList | None:
    """Build an EntityReferenceList for a single user, or None if missing."""
    if user is None:
        return None
    return EntityReferenceList(
        root=[EntityReference(id=user.id, type="user")]
    )


def _approve_entity(
    metadata: OpenMetadata,
    entity_type: type,
    entity,
) -> None:
    """Patch entityStatus to Approved.

    The create-request schemas do not expose entityStatus, and when reviewers
    are set OpenMetadata leaves new glossaries/terms in Draft until reviewers
    approve. For demo seeding we pre-approve so links and usage work
    immediately while keeping reviewer metadata.
    """
    if entity.entityStatus == EntityStatus.Approved:
        return
    destination = entity.model_copy(deep=True)
    destination.entityStatus = EntityStatus.Approved
    metadata.patch(entity=entity_type, source=entity, destination=destination)


def _glossary_tag_label(term_fqn: str) -> TagLabel:
    """Build a TagLabel that links an entity to a glossary term."""
    return TagLabel(
        tagFQN=TagFQN(term_fqn),
        source=TagSource.Glossary,
        labelType=LabelType.Manual,
        state=State.Confirmed,
    )


def _classification_tag_label(tag_fqn: str) -> TagLabel:
    """Build a TagLabel that links an entity to a classification tag."""
    return TagLabel(
        tagFQN=TagFQN(tag_fqn),
        source=TagSource.Classification,
        labelType=LabelType.Manual,
        state=State.Confirmed,
    )


def _build_tag_label(fqn: str) -> TagLabel:
    """Choose Classification vs Glossary source based on the FQN root."""
    root = fqn.split(".", 1)[0]
    if root in _CLASSIFICATION_NAMES:
        return _classification_tag_label(fqn)
    return _glossary_tag_label(fqn)


def create_glossaries(
    metadata: OpenMetadata,
    result: CreationResult,
    user_map: dict[str, User],
) -> dict[str, Glossary]:
    """Create all glossaries and return a mapping of name -> entity."""
    glossary_map: dict[str, Glossary] = {}
    for g in GLOSSARIES:
        name = g["name"]
        reviewer_name = GLOSSARY_REVIEWERS.get(name)
        reviewer = user_map.get(reviewer_name) if reviewer_name else None
        reviewers = _owners_for_user(reviewer)
        try:
            entity = metadata.create_or_update(
                data=CreateGlossaryRequest(
                    name=EntityName(name),
                    displayName=g["displayName"],
                    description=Markdown(g["description"]),
                    reviewers=reviewers,
                )
            )
        except Exception:
            logger.exception("Failed to create glossary: %s", name)
            result.glossaries_failed.append(name)
            continue
        try:
            _approve_entity(metadata, Glossary, entity)
        except Exception:
            logger.exception("Failed to approve glossary: %s", name)
        glossary_map[name] = entity
        result.glossaries_created.append(name)
        logger.info(
            "Created glossary: %s%s",
            name,
            f" (reviewer: {reviewer_name})" if reviewer else "",
        )
    return glossary_map


def create_glossary_terms(
    metadata: OpenMetadata, result: CreationResult
) -> dict[str, GlossaryTerm]:
    """Create all glossary terms, respecting parent-child order.

    Terms are defined so that parents appear before children in the list.
    """
    term_map: dict[str, GlossaryTerm] = {}

    for glossary_name, name, display_name, description, parent_name, synonyms in GLOSSARY_TERMS:
        fqn_key = f"{glossary_name}.{name}"

        parent_fqn = None
        if parent_name is not None:
            parent_key = f"{glossary_name}.{parent_name}"
            parent_entity = term_map.get(parent_key)
            if parent_entity is None:
                logger.warning(
                    "Parent %s not found for term %s - creating without parent",
                    parent_key, name,
                )
            else:
                parent_fqn = parent_entity.fullyQualifiedName

        synonym_names = [EntityName(s) for s in synonyms] if synonyms else None

        try:
            entity = metadata.create_or_update(
                data=CreateGlossaryTermRequest(
                    glossary=FullyQualifiedEntityName(glossary_name),
                    name=EntityName(name),
                    displayName=display_name,
                    description=Markdown(description),
                    parent=parent_fqn,
                    synonyms=synonym_names,
                )
            )
        except Exception:
            logger.exception("Failed to create term: %s", fqn_key)
            result.terms_failed.append(fqn_key)
            continue

        try:
            _approve_entity(metadata, GlossaryTerm, entity)
        except Exception:
            logger.exception("Failed to approve term: %s", fqn_key)

        term_map[fqn_key] = entity
        result.terms_created.append(fqn_key)
        logger.info("Created term: %s", entity.fullyQualifiedName.root)

    return term_map


def create_metrics(
    metadata: OpenMetadata,
    result: CreationResult,
    user_map: dict[str, User],
    term_map: dict[str, GlossaryTerm],
) -> dict[str, Metric]:
    """Create all metric entities.

    Related metrics are linked in a second pass once all metrics exist.
    Owners and glossary-term linkage (via tags) are attached on first pass.
    """
    metric_map: dict[str, Metric] = {}

    # First pass: create metrics with owners + glossary-term tags
    for name, display_name, description, m_type, unit, granularity, sql, _related in METRICS:
        owner_name = METRIC_OWNERS.get(name)
        owner = user_map.get(owner_name) if owner_name else None
        owners = _owners_for_user(owner)

        tag_labels: list[TagLabel] = []
        for term_key in METRIC_GLOSSARY_TERMS.get(name, []):
            term_entity = term_map.get(term_key)
            if term_entity is not None and term_entity.fullyQualifiedName is not None:
                # The term entity's actual FQN may include parent hierarchy
                # (e.g., RiskAndAML.RiskBand.IFRS9Stage1); use it verbatim.
                actual_fqn = term_entity.fullyQualifiedName.root
                tag_labels.append(_glossary_tag_label(actual_fqn))
            else:
                logger.warning(
                    "Glossary term %s not found - skipping metric link for %s",
                    term_key, name,
                )

        try:
            entity = metadata.create_or_update(
                data=CreateMetricRequest(
                    name=EntityName(name),
                    displayName=display_name,
                    description=Markdown(description),
                    metricType=m_type,
                    unitOfMeasurement=unit,
                    customUnitOfMeasurement=_custom_unit_for_metric(name, unit),
                    granularity=granularity,
                    metricExpression=MetricExpression(
                        language=Language.SQL,
                        code=sql,
                    ),
                    owners=owners,
                    tags=tag_labels or None,
                )
            )
        except Exception:
            logger.exception("Failed to create metric: %s", name)
            result.metrics_failed.append(name)
            continue

        metric_map[name] = entity
        result.metrics_created.append(name)
        logger.info(
            "Created metric: %s%s%s",
            name,
            f" (owner: {owner_name})" if owner else "",
            f" [+{len(tag_labels)} glossary tags]" if tag_labels else "",
        )

    # Second pass: link related metrics (replays the create with related)
    for name, _, description, m_type, unit, granularity, sql, related in METRICS:
        if not related:
            continue
        if name not in metric_map:
            continue

        resolved = []
        for rel_name in related:
            rel_entity = metric_map.get(rel_name)
            if rel_entity is not None:
                resolved.append(
                    FullyQualifiedEntityName(rel_entity.fullyQualifiedName.root)
                )
            else:
                logger.warning("Related metric %s not found for %s", rel_name, name)

        if not resolved:
            continue

        owner_name = METRIC_OWNERS.get(name)
        owner = user_map.get(owner_name) if owner_name else None
        owners = _owners_for_user(owner)

        tag_labels: list[TagLabel] = []
        for term_key in METRIC_GLOSSARY_TERMS.get(name, []):
            term_entity = term_map.get(term_key)
            if term_entity is not None and term_entity.fullyQualifiedName is not None:
                tag_labels.append(
                    _glossary_tag_label(term_entity.fullyQualifiedName.root)
                )

        try:
            metadata.create_or_update(
                data=CreateMetricRequest(
                    name=EntityName(name),
                    displayName=metric_map[name].displayName,
                    description=Markdown(description),
                    metricType=m_type,
                    unitOfMeasurement=unit,
                    customUnitOfMeasurement=_custom_unit_for_metric(name, unit),
                    granularity=granularity,
                    metricExpression=MetricExpression(
                        language=Language.SQL,
                        code=sql,
                    ),
                    relatedMetrics=resolved,
                    owners=owners,
                    tags=tag_labels or None,
                )
            )
        except Exception:
            logger.exception("Failed to link related metrics for: %s", name)
            result.metrics_link_failed.append(name)
            continue

        result.metrics_linked.append(name)
        logger.info("Linked %d related metrics to %s", len(resolved), name)

    return metric_map


# ---------------------------------------------------------------------------
# Classification, tag, and column-tag helpers
# ---------------------------------------------------------------------------


def create_pii_classification(
    metadata: OpenMetadata, result: CreationResult
) -> None:
    """Create the PII and Banking classifications + their tags.

    Tags require the classification to exist first; we materialise both
    in a single pass.
    """
    # 1) Create classifications
    for c in CLASSIFICATIONS:
        name = c["name"]
        try:
            metadata.create_or_update(
                data=CreateClassificationRequest(
                    name=EntityName(name),
                    displayName=c["displayName"],
                    description=Markdown(c["description"]),
                    mutuallyExclusive=c.get("mutuallyExclusive", False),
                )
            )
        except Exception:
            logger.exception("Failed to create classification: %s", name)
            result.classifications_failed.append(name)
            continue
        result.classifications_created.append(name)
        logger.info("Created classification: %s", name)

    # 2) Create tags under each classification
    for classification_name, tag_name, display_name, description in TAGS:
        tag_fqn = f"{classification_name}.{tag_name}"
        try:
            metadata.create_or_update(
                data=CreateTagRequest(
                    classification=FullyQualifiedEntityName(classification_name),
                    name=EntityName(tag_name),
                    displayName=display_name,
                    description=Markdown(description),
                )
            )
        except Exception:
            logger.exception("Failed to create tag: %s", tag_fqn)
            result.tags_failed.append(tag_fqn)
            continue
        result.tags_created.append(tag_fqn)
        logger.info("Created tag: %s", tag_fqn)


def _resolve_tag_fqn(tag_key: str, term_map: dict[str, GlossaryTerm]) -> str | None:
    """Resolve a simple `<Root>.<Name>` form into the actual tag FQN.

    Classification tags (e.g., `PII.Sensitive`) are used verbatim.
    Glossary terms may have parent hierarchy: `DataPrivacyPII.SSN` resolves
    to the term entity's `fullyQualifiedName` which is the canonical form
    (e.g., `DataPrivacyPII.PII.SSN`).
    """
    root = tag_key.split(".", 1)[0]
    if root in _CLASSIFICATION_NAMES:
        return tag_key
    term = term_map.get(tag_key)
    if term is None or term.fullyQualifiedName is None:
        return None
    return term.fullyQualifiedName.root


def apply_pii_tags_to_columns(
    metadata: OpenMetadata,
    service: str,
    database: str,
    result: CreationResult,
    term_map: dict[str, GlossaryTerm],
) -> None:
    """Apply Classification and Glossary tags to PII columns.

    The OpenMetadata SDK exposes `patch_column_tags(entity, column_tags=...)`
    which is the supported way to attach tags to columns via JSON Patch.
    """
    # Group column-tag entries by (schema, table) so we issue one PATCH per
    # table.
    grouped: dict[tuple[str, str], list[tuple[str, list[str]]]] = {}
    for schema, table, column, tag_fqns in PII_COLUMN_TAGS:
        grouped.setdefault((schema, table), []).append((column, tag_fqns))

    for (schema, table), columns in grouped.items():
        table_fqn = f"{service}.{database}.{schema}.{table}"
        try:
            table_entity = metadata.get_by_name(entity=Table, fqn=table_fqn)
        except Exception:
            logger.exception("Failed to fetch table: %s", table_fqn)
            for column, _ in columns:
                result.columns_tag_failed.append(f"{table_fqn}.{column}")
            continue

        if table_entity is None:
            logger.warning(
                "Table not found: %s - did you run dbt + metadata ingestion first? "
                "Skipping column tags for this table.",
                table_fqn,
            )
            for column, _ in columns:
                result.columns_tag_failed.append(f"{table_fqn}.{column}")
            continue

        column_tags: list[ColumnTag] = []
        for column, tag_keys in columns:
            column_fqn = f"{table_fqn}.{column}"
            for tag_key in tag_keys:
                resolved_fqn = _resolve_tag_fqn(tag_key, term_map)
                if resolved_fqn is None:
                    logger.warning(
                        "Tag %s not found - skipping column %s",
                        tag_key, column_fqn,
                    )
                    continue
                column_tags.append(
                    ColumnTag(
                        column_fqn=column_fqn,
                        tag_label=_build_tag_label(resolved_fqn),
                    )
                )

        if not column_tags:
            logger.warning("No resolvable tags for %s - skipping", table_fqn)
            continue

        try:
            metadata.patch_column_tags(
                entity=table_entity,
                column_tags=column_tags,
            )
        except Exception:
            logger.exception("Failed to patch column tags on %s", table_fqn)
            for column, _ in columns:
                result.columns_tag_failed.append(f"{table_fqn}.{column}")
            continue

        for column, tag_keys in columns:
            result.columns_tagged.append(f"{table_fqn}.{column}")
            logger.info(
                "  Tagged %s.%s with %s",
                table, column, ", ".join(tag_keys),
            )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Seed OpenMetadata with banking demo glossaries, terms, metrics, "
            "and PII classifications/tags."
        )
    )
    parser.add_argument(
        "--host",
        default=os.getenv("AI_SDK_HOST", "http://localhost:8585"),
        help="OpenMetadata API host (default: $AI_SDK_HOST or http://localhost:8585)",
    )
    parser.add_argument(
        "--token",
        default=os.getenv("AI_SDK_TOKEN", ""),
        help="JWT token for authentication (default: $AI_SDK_TOKEN)",
    )
    parser.add_argument(
        "--service",
        default=os.getenv("AI_SDK_SERVICE", "banking-redshift"),
        help=(
            "Database service name in OpenMetadata, used to build column FQNs "
            "for PII tagging (default: $AI_SDK_SERVICE or 'banking-redshift')"
        ),
    )
    parser.add_argument(
        "--database",
        default=os.getenv("REDSHIFT_DATABASE", "dev"),
        help="Database name (default: $REDSHIFT_DATABASE or 'dev')",
    )
    parser.add_argument(
        "--skip-pii-tagging",
        action="store_true",
        help=(
            "Skip the column-tagging step (useful if dbt models / metadata "
            "ingestion have not yet been run, so target tables do not exist)."
        ),
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    args = parse_args()

    if not args.token:
        logger.error(
            "No token provided. Set AI_SDK_TOKEN or pass --token."
        )
        sys.exit(1)

    metadata = get_metadata_client(args.host, args.token)
    result = CreationResult()

    # ── Look up users for owner / reviewer assignment ──────────────────
    # Users must already exist in OpenMetadata (run create_owners_and_domains.py
    # first). Missing users degrade gracefully — affected metrics/glossaries
    # are still created, just without an owner/reviewer.
    needed_users = sorted(
        set(GLOSSARY_REVIEWERS.values()) | set(METRIC_OWNERS.values())
    )
    logger.info("--- Fetching Users for Owner Assignment ---")
    user_map = fetch_users(metadata, needed_users)
    logger.info("Found %d / %d users", len(user_map), len(needed_users))

    logger.info("--- Creating Glossaries ---")
    create_glossaries(metadata, result, user_map)

    logger.info("--- Creating Glossary Terms ---")
    term_map = create_glossary_terms(metadata, result)

    logger.info("--- Creating Metrics ---")
    create_metrics(metadata, result, user_map, term_map)

    logger.info("--- Creating PII Classifications and Tags ---")
    create_pii_classification(metadata, result)

    if not args.skip_pii_tagging:
        logger.info("--- Applying PII Tags to Columns ---")
        apply_pii_tags_to_columns(
            metadata, args.service, args.database, result, term_map
        )
    else:
        logger.info("--- Skipping PII column tagging (--skip-pii-tagging) ---")

    result.print_summary()

    if result.has_failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
