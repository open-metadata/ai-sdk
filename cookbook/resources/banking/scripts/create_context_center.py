"""Populate the Context Center with banking-themed demo content.

Seeds Folders, Files, Pages (articles + quick links), and Context Memories so
the ``/context-center/dashboard`` view has realistic content to showcase the
demo's banking data.

Entities created:

* **Folders** – a hierarchical tree (Compliance > KYC, Risk Management > Fraud,
  Finance & Reporting > IFRS-9, etc.).
* **Files** – markdown documents uploaded via multipart to
  ``/v1/contextCenter/drive/files/upload`` (KYC policy, AML procedures, fraud
  runbooks, IFRS9 staging methodology, ...). Falls back to metadata-only
  ``POST /v1/contextCenter/drive/files`` when object storage is not configured.
* **Pages** – knowledge-base ``Article`` pages with markdown bodies and
  ``QuickLink`` pages pointing at the demo's Superset dashboards and external
  regulator portals.
* **Memories** – Q/A memories of every memory type (Faq, Runbook, UseCase,
  Note, Preference). Memories that target a specific Redshift table attach to
  it via ``primaryEntity`` once the table is resolved via FQN; if the table
  is not yet ingested the memory still seeds without ``primaryEntity``. Every
  memory carries an ``owner_username`` (spread across alice / bob /
  carol / dave) and is POSTed with an ``X-Impersonate-User`` header so the
  memory's author (``updatedBy``) matches the assigned owner — gives a
  realistic "different teammates contributed these" feel in the UI.
  Impersonation requires a bot JWT; the script auto-falls-back to no
  impersonation if the server rejects it.

Idempotent: every entity is looked up by name (or FQN) before creation. Add
``--force`` to overwrite existing entities (DELETE + recreate).

Requires:
    pip install requests

Usage:
    export AI_SDK_HOST=https://your-instance.getcollate.io
    export AI_SDK_TOKEN=<your-jwt-token>

    # Default invocation — Redshift-target defaults baked in.
    python create_context_center.py

    # Point at a specific service / database for FQN resolution. On BigQuery the
    # "database" is the GCP project.
    python create_context_center.py --db-service banking-redshift --database dev
    python create_context_center.py --db-service banking-bigquery --database my-gcp-project

    # Skip multipart file uploads (just create file metadata entries).
    python create_context_center.py --no-upload

    # Dry run.
    python create_context_center.py --dry-run
"""

from __future__ import annotations

import argparse
import io
import logging
import os
import sys
from dataclasses import dataclass, field
from typing import Any

import requests

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# REST paths
# ---------------------------------------------------------------------------

FOLDERS_PATH = "/v1/contextCenter/drive/folders"
FILES_PATH = "/v1/contextCenter/drive/files"
FILES_UPLOAD_PATH = "/v1/contextCenter/drive/files/upload"
PAGES_PATH = "/v1/contextCenter/pages"
MEMORIES_PATH = "/v1/contextCenter/memories"
TABLES_PATH = "/v1/tables"
USERS_PATH = "/v1/users"


# ---------------------------------------------------------------------------
# Content definitions — folders, files, pages, memories
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FolderSpec:
    name: str
    display_name: str
    description: str
    icon: str | None = None
    color: str | None = None
    parent: str | None = None  # parent folder name (resolved to FQN at runtime)


@dataclass(frozen=True)
class FileSpec:
    name: str  # entity name; also used as filename for upload
    display_name: str
    description: str
    folder: str  # parent folder name
    body: str  # markdown body uploaded as the file content


@dataclass(frozen=True)
class ArticleSpec:
    name: str
    display_name: str
    description: str  # markdown body; page-schema Article has no body field


@dataclass(frozen=True)
class QuickLinkSpec:
    name: str
    display_name: str
    description: str
    url: str


@dataclass(frozen=True)
class MemorySpec:
    name: str
    title: str
    question: str
    answer: str
    memory_type: str  # Faq | Runbook | UseCase | Note | Preference
    memory_scope: str = "EntityScoped"  # UserGlobal | EntityScoped
    visibility: str = "Shared"  # Private | Entity | Shared
    primary_table: str | None = None  # "<schema>.<table>" tail of the FQN
    owner_username: str | None = None  # OM username; None = no explicit owner


FOLDERS: list[FolderSpec] = [
    FolderSpec(
        name="Compliance",
        display_name="Compliance",
        description="KYC, AML, GDPR and sanctions-screening artefacts.",
        icon="shield",
        color="#1d4ed8",
    ),
    FolderSpec(
        name="KYC",
        display_name="KYC / Customer Due Diligence",
        description="KYC policy, CDD/EDD procedures, periodic-review SOPs.",
        parent="Compliance",
    ),
    FolderSpec(
        name="AML",
        display_name="AML / Sanctions",
        description="AML procedures, sanctions screening, SAR templates.",
        parent="Compliance",
    ),
    FolderSpec(
        name="RiskManagement",
        display_name="Risk Management",
        description="Credit risk, fraud, market and operational-risk playbooks.",
        icon="alert-triangle",
        color="#b91c1c",
    ),
    FolderSpec(
        name="CreditRisk",
        display_name="Credit Risk",
        description="Scorecards, PD/LGD/EAD methodology, credit-policy notes.",
        parent="RiskManagement",
    ),
    FolderSpec(
        name="Fraud",
        display_name="Fraud Operations",
        description="Card-not-present fraud, ATO playbooks, chargeback handling.",
        parent="RiskManagement",
    ),
    FolderSpec(
        name="CustomerOperations",
        display_name="Customer Operations",
        description="Customer-360 data dictionary, dispute SOPs, contact-centre runbooks.",
        icon="users",
        color="#0e7490",
    ),
    FolderSpec(
        name="FinanceAndReporting",
        display_name="Finance & Reporting",
        description="IFRS 9, Basel III, daily P&L and capital reporting.",
        icon="bar-chart-3",
        color="#0f766e",
    ),
    FolderSpec(
        name="IFRS9",
        display_name="IFRS 9",
        description="Staging methodology, ECL calculation, transition rules.",
        parent="FinanceAndReporting",
    ),
    FolderSpec(
        name="BaselIII",
        display_name="Basel III",
        description="Capital adequacy, RWA, liquidity reporting.",
        parent="FinanceAndReporting",
    ),
    FolderSpec(
        name="DataEngineering",
        display_name="Data Engineering",
        description="dbt conventions, PII classification, ingestion runbooks.",
        icon="database",
        color="#7c3aed",
    ),
]


FILES: list[FileSpec] = [
    # --- Compliance / KYC ---------------------------------------------------
    FileSpec(
        name="kyc-policy",
        display_name="KYC Policy v3.4",
        description="Customer identification, verification and ongoing-monitoring policy.",
        folder="KYC",
        body="""# Know Your Customer (KYC) Policy

**Version**: 3.4
**Owner**: Chief Compliance Officer
**Last review**: 2026-Q1
**Next review**: 2027-Q1

## 1. Purpose

This policy establishes the minimum standards the bank applies when onboarding
and monitoring customers, in line with the FATF 40 Recommendations, the EU 6th
Anti-Money-Laundering Directive, and the BSA/Patriot Act for US-domiciled
entities.

## 2. Customer Identification Programme (CIP)

All natural-person customers must provide:

* Full legal name and any prior names
* Date of birth (must match a government-issued document)
* Residential address (P.O. boxes are rejected)
* Government identifier (SSN, national ID, passport, or tax ID)

The Customer Identification table `raw_core_banking.customers` stores the
hashed identifier in the `ssn_hash` column; raw SSNs are never persisted.

## 3. Risk Rating

Every customer is assigned a KYC risk rating of **Low**, **Medium**, **High**
or **Prohibited** at onboarding. The rating is recomputed:

* Every 36 months for Low-risk retail customers
* Every 12 months for Medium-risk customers
* Every 6 months for High-risk customers
* Immediately on any high-value cross-border transaction

Stage transitions are written to `raw_risk.customer_risk_history` with a full
audit trail (effective_from / effective_to). The latest rating is exposed via
the `dbt_marts_core.dim_customers.kyc_risk_rating` column.

## 4. Enhanced Due Diligence (EDD)

EDD is triggered for:

* PEPs (Politically Exposed Persons)
* Customers from FATF "grey" or "black" jurisdictions
* Source-of-wealth verification above $250k
* Cash-intensive business segments (MCC catalogue maintained in
  `raw_cards.merchant_category_codes`)

## 5. Periodic Review

The KYC team owns the periodic review queue. Reviews overdue by >30 days are
escalated to the second-line MLRO and surfaced as DQ failures on
`dbt_marts_core.dim_customers` via the `kyc_review_overdue` test.
""",
    ),
    FileSpec(
        name="customer-due-diligence-procedures",
        display_name="Customer Due Diligence Procedures",
        description="Step-by-step CDD and EDD operating procedures.",
        folder="KYC",
        body="""# Customer Due Diligence (CDD) Procedures

## When to apply

* Account opening (all segments).
* Material change in beneficial ownership.
* Cumulative cross-border activity > USD 10,000 in any rolling 30-day window.
* Trigger events: court orders, adverse media, sanctions hits.

## CDD checklist

1. **Identity** – two independent identity documents matched against the
   government registry.
2. **Address** – utility bill, bank statement or notarised letter not older
   than 3 months.
3. **Source of funds** – payslip, audited accounts, sale-of-asset deed.
4. **Sanctions screening** – OFAC, EU consolidated, UN sanctions, plus
   internal denied-party list.
5. **Adverse-media screening** – at least one global database
   (e.g. World-Check, Dow Jones RiskCenter).

## Output

CDD outcomes are recorded with one row per customer per review in
`raw_risk.kyc_reviews`, with columns: `review_id`, `customer_id`, `outcome`
(`Pass | Pass-with-EDD | Fail`), `notes`, `reviewer_employee_id`.

## Operational SLAs

* CDD at onboarding must complete within **24 business hours**.
* Periodic CDD must complete within **5 business days** of the trigger.
* CDD failure must be escalated to the MLRO within **4 hours**.
""",
    ),
    # --- Compliance / AML ---------------------------------------------------
    FileSpec(
        name="aml-procedures-manual",
        display_name="AML Procedures Manual",
        description="Transaction monitoring, alert handling and case management.",
        folder="AML",
        body="""# AML Procedures Manual

## Transaction-monitoring scenarios

The bank operates a rule-based transaction-monitoring engine plus an ML
anomaly model. Rule definitions live in `raw_risk.tm_rules`; alerts are
materialised into `dbt_marts_risk.fct_aml_pipeline`.

### Active scenarios

| Code   | Description                                              | SLA   |
|--------|----------------------------------------------------------|-------|
| TM-001 | Structuring: 3+ cash deposits < $10k in 24h              | 4h    |
| TM-002 | Round-amount cross-border wires > $9,500                 | 4h    |
| TM-003 | Velocity spike vs. customer 30d baseline (>4 sigma)      | 8h    |
| TM-004 | Counter-party hit on internal denied-party list          | 1h    |
| TM-005 | First-time crypto on/off-ramp activity                   | 24h   |
| TM-006 | Geographic outlier (country mismatch with KYC profile)   | 24h   |

## Alert lifecycle

1. **Open** – created by the rules engine or the anomaly model.
2. **Triage** – L1 analyst reviews customer context, KYC rating, and the
   `int_aml__alert_context` model.
3. **Investigation** – L2 analyst documents findings in the case-management
   system; pulls counter-party history from `dbt_marts_core.fct_transactions`.
4. **Disposition** – `Close-NoConcern`, `Close-Cleared`, or `SAR-Filed`.
5. **SAR** – if filed, the SAR number is written back to
   `raw_risk.sar_filings`.

## Quality metrics

* False-positive rate per scenario (target <70%).
* Median triage time (target <30 minutes).
* Backlog age >5 business days triggers an MLRO escalation.
""",
    ),
    FileSpec(
        name="sanctions-screening-runbook",
        display_name="Sanctions Screening Runbook",
        description="What to do when a customer or counter-party matches a sanctions list.",
        folder="AML",
        body="""# Sanctions Screening Runbook

## Sources screened

* OFAC SDN + non-SDN consolidated list
* EU consolidated list
* UN consolidated list
* HM Treasury (UK) consolidated list
* Internal denied-party list (DPL) loaded from `raw_risk.denied_parties`

Screening is performed at:

* Account opening (full screen).
* Every transaction with a counter-party outside the bank.
* Daily rescreen of the entire customer base against the latest list deltas.

## On a hit

1. **Freeze** – the transaction is automatically held by the payment hub.
2. **Verify** – analyst compares the matched record against the customer
   profile in `dbt_marts_core.dim_customers`. Look for date-of-birth,
   nationality and alias overlap.
3. **Decision** – `True positive`, `Possible match` or `False positive`.
4. **True positive** – escalate to MLRO within 30 minutes. Funds remain
   frozen pending regulatory direction.
5. **False positive** – release the transaction and add the record to the
   whitelist with a 12-month review date.

## Audit trail

Every match decision is appended to `raw_risk.sanctions_hits` with the full
list snapshot version (so we can replay historical hits with the list as it
existed at the time of the decision).
""",
    ),
    FileSpec(
        name="suspicious-activity-report-template",
        display_name="SAR Filing Template",
        description="Suspicious Activity Report narrative template and FinCEN field map.",
        folder="AML",
        body="""# Suspicious Activity Report (SAR) Template

## Narrative structure

Every SAR narrative must follow the **5 W's**:

1. **Who** – subject(s) of the report (full identifiers; pull from
   `dbt_marts_core.dim_customers`).
2. **What** – the suspicious activity: amounts, channels, instruments.
3. **When** – activity window (`activity_start_at`, `activity_end_at`).
4. **Where** – geography, accounts, branches involved.
5. **Why** – why this activity is suspicious (red flags observed, scenario
   codes matched, ML score, KYC mismatches).

## Required data points

| Field                  | Source                                             |
|------------------------|----------------------------------------------------|
| Customer demographics  | `dbt_marts_core.dim_customers`                     |
| Transaction history    | `dbt_marts_core.fct_transactions` (last 13 months) |
| Card activity          | `dbt_marts_core.fct_card_authorizations`           |
| KYC rating history     | `raw_risk.customer_risk_history`                   |
| Alerts associated      | `dbt_marts_risk.fct_aml_pipeline`                  |

## Filing windows

* 30 calendar days from initial detection (FinCEN).
* 60 calendar days if a suspect has not been identified.
* Continuing-activity SARs every 90 days while activity persists.
""",
    ),
    # --- Risk / Credit ------------------------------------------------------
    FileSpec(
        name="credit-scoring-methodology",
        display_name="Credit Scoring Methodology",
        description="PD / LGD / EAD model methodology and validation cadence.",
        folder="CreditRisk",
        body="""# Credit Scoring Methodology

## Models in production

| Model         | Segment              | PD horizon | Owner         |
|---------------|----------------------|------------|---------------|
| CSCR-Retail-1 | Retail unsecured     | 12 months  | Credit Risk   |
| CSCR-Retail-2 | Retail mortgage      | 12 months  | Credit Risk   |
| CSCR-SME-1    | SME term loan        | 12 months  | Credit Risk   |
| CSCR-Auto-1   | Auto loan            | 12 months  | Credit Risk   |
| LGD-Retail-1  | Retail unsecured     | n/a        | Credit Risk   |
| LGD-Sec-1     | Secured (all)        | n/a        | Credit Risk   |

## Inputs

PD models consume:

* Customer demographics (`dbt_marts_core.dim_customers`).
* Account and product holdings (`dbt_marts_core.dim_accounts`).
* Behavioural features (30/90/180 day rolling spend, balance volatility,
  delinquency depth) — computed in `int_loans__delinquency`.
* External bureau score (TransUnion / Experian) joined via
  `raw_risk.bureau_pulls`.

## Validation

Every model is independently validated **annually**. Validation covers:

* Discriminatory power — AUC, Gini, KS by segment and vintage.
* Calibration — Hosmer-Lemeshow, observed-vs-expected by decile.
* Stability — PSI vs. the development window.

Validation reports are stored alongside the model card in the model registry
and summarised in the `dbt_marts_risk.dim_credit_risk` dimension.
""",
    ),
    # --- Risk / Fraud -------------------------------------------------------
    FileSpec(
        name="fraud-incident-response",
        display_name="Fraud Incident Response Plan",
        description="What the fraud-ops team does when a burst is detected.",
        folder="Fraud",
        body="""# Fraud Incident Response Plan

## Burst detection

A **fraud burst** is defined as any cluster of 10+ card authorisations on a
single customer within a 24-hour window, or 40+ disputes on a single merchant
within 7 days. Detection runs every 5 minutes against
`dbt_marts_core.fct_card_authorizations` and `fct_disputes`.

## P1 — Containment (0-30 min)

1. Auto-block all cards in the cluster (push to the issuing processor).
2. Page the on-call fraud analyst.
3. Open an incident in PagerDuty (`fraud-burst`).
4. Snapshot the affected customer set in `raw_risk.fraud_burst_snapshots`.

## P2 — Investigation (30 min – 4 h)

1. Pivot on common attributes: device fingerprint, geolocation, BIN, merchant.
2. Pull last-7-day customer activity from `dbt_marts_core.fct_transactions`.
3. Cross-reference dark-web alerts (e.g. recent BIN dumps).
4. Decide on customer-comms strategy (SMS / email / app push).

## P3 — Remediation (4 h – 72 h)

1. Reissue affected cards.
2. File disputes upstream where applicable.
3. Re-tune the rule that fired (or didn't fire) the burst signal.
4. Post-incident review within 5 business days.

## KPIs

* MTTD (median): target <10 minutes.
* MTTR (full block): target <30 minutes.
* Fraud-loss-rate-per-1k-cards: target <$2.
""",
    ),
    FileSpec(
        name="card-fraud-typology-catalog",
        display_name="Card Fraud Typology Catalogue",
        description="Common card-fraud typologies and the MCC codes that surface them.",
        folder="Fraud",
        body="""# Card Fraud Typology Catalogue

## Card-not-present (CNP) fraud

* **Mass enumeration** – attacker iterates card numbers via small auth tests
  ($0.99, $1.00). Surfaces as a velocity spike of low-value declines on
  merchants in MCC 5734 (computer software) and 5816 (digital goods).
* **Account takeover (ATO)** – legitimate credentials are stolen and used to
  add a new shipping address. Pivot: `raw_digital.login_attempts` for a
  successful login from a new device + a profile change within 30 minutes.
* **Friendly fraud** – cardholder disputes a legitimate charge. Pivot on
  `dbt_marts_core.fct_disputes` where dispute_reason in ('Did not recognize',
  'Goods not received') and the device fingerprint matches prior good txns.

## Card-present fraud

* **Skimming** – cloned card used in CNP. Pivot on geographically improbable
  authorisations (home country vs auth country mismatch in
  `fct_card_authorizations`).
* **First-party stand-in** – PIN-verified ATM withdrawal followed by a card-
  not-present chargeback. Always investigate.

## MCC red-flag catalogue

| MCC  | Description                  | Why suspicious                          |
|------|------------------------------|-----------------------------------------|
| 7995 | Gambling                     | Money laundering proxy                  |
| 6051 | Quasi-cash / crypto on-ramps | Layering risk                           |
| 5993 | Cigar / tobacco stores       | Structuring proxy in CTR-prone regions  |
| 6010 | Manual cash disbursement     | Bust-out / mule signal                  |
| 4829 | Wire transfer money orders   | Layering proxy                          |

The catalogue is maintained in `raw_cards.merchant_category_codes` and
surfaced in `dbt_marts_core.fct_card_authorizations.mcc_risk_tier`.
""",
    ),
    # --- Customer Ops -------------------------------------------------------
    FileSpec(
        name="customer-360-data-dictionary",
        display_name="Customer-360 Data Dictionary",
        description="Canonical Customer-360 fields, owners, and sources.",
        folder="CustomerOperations",
        body="""# Customer-360 Data Dictionary

The Customer-360 surface is materialised in
`dbt_marts_core.dim_customers` and refreshed every 6 hours. Source of truth
for every consuming dashboard, CRM and CDP push.

## Identity attributes

| Column                 | Source                              | PII | Owner          |
|------------------------|-------------------------------------|-----|----------------|
| customer_id            | `raw_core_banking.customers`        | No  | Core Banking   |
| customer_status        | derived                             | No  | Customer Ops   |
| full_name              | `raw_core_banking.customers`        | Yes | Compliance     |
| email_hash             | `raw_core_banking.customer_contacts`| No  | Compliance     |
| phone_hash             | `raw_core_banking.customer_contacts`| No  | Compliance     |
| ssn_hash               | `raw_core_banking.customers`        | No  | Compliance     |
| date_of_birth          | `raw_core_banking.customers`        | Yes | Compliance     |
| country_of_residence   | `raw_core_banking.customer_addresses`| No  | Customer Ops   |

## Behavioural attributes

| Column                 | Window  | Refresh |
|------------------------|---------|---------|
| balance_total          | live    | 1h      |
| spend_30d              | 30d     | 1h      |
| spend_90d              | 90d     | 1h      |
| logins_30d             | 30d     | 1h      |
| nps_score              | latest  | 24h     |

## Risk attributes

| Column                 | Source                                   |
|------------------------|------------------------------------------|
| kyc_risk_rating        | `raw_risk.customer_risk_history` latest   |
| pep_flag               | `raw_risk.pep_screening`                  |
| sanctions_hit_count_1y | `raw_risk.sanctions_hits`                 |
| ml_churn_probability   | model `CHURN-Retail-2`                    |

Any change to this contract requires sign-off from Customer Ops AND the
Compliance domain.
""",
    ),
    FileSpec(
        name="dispute-resolution-sop",
        display_name="Dispute Resolution SOP",
        description="Step-by-step card-dispute handling for the contact centre.",
        folder="CustomerOperations",
        body="""# Card Dispute Resolution SOP

## Step 1 — Customer call

1. Authenticate the customer (challenge questions; pull profile from
   `dbt_marts_core.dim_customers`).
2. Confirm the disputed transaction(s); fetch with
   `select * from dbt_marts_core.fct_transactions where customer_id = ? and ...`.
3. Capture the dispute reason from the Visa / Mastercard reason-code list.
4. Open a dispute row in `raw_cards.card_disputes` with the reason and
   timestamp.

## Step 2 — Provisional credit

If the disputed amount is < USD 250 and the customer has had < 3 disputes in
the last 12 months, issue a provisional credit immediately. Otherwise escalate
to the back-office.

## Step 3 — Investigation

Back-office pulls evidence:

* Original auth record from `dbt_marts_core.fct_card_authorizations`.
* Device fingerprint and IP from the digital-channels feed.
* Merchant-side documentation (receipt, signature, IP, 3DS result).

## Step 4 — Chargeback or decline

* **Chargeback** – issue chargeback through the scheme; update dispute row to
  `state = 'chargeback-filed'`.
* **Decline** – respond to the customer with the evidence; mark dispute as
  `state = 'declined'`.

## Step 5 — Reporting

Daily dispute volumes are visualised on the Customer Ops dashboard
(Superset). Anomalies trigger a chargeback-storm playbook (see
`fraud-incident-response`).
""",
    ),
    # --- Finance / IFRS9 ----------------------------------------------------
    FileSpec(
        name="ifrs9-staging-methodology",
        display_name="IFRS 9 Staging Methodology",
        description="Stage 1 / 2 / 3 classification logic and SICR triggers.",
        folder="IFRS9",
        body="""# IFRS 9 Staging Methodology

## Stage definitions

* **Stage 1 — Performing.** Initial recognition, no Significant Increase in
  Credit Risk (SICR). 12-month ECL applies.
* **Stage 2 — Under-performing.** SICR observed but no objective evidence of
  impairment. Lifetime ECL applies.
* **Stage 3 — Non-performing.** Objective evidence of credit impairment.
  Lifetime ECL applies; interest recognised on net carrying amount.

## SICR triggers (Stage 1 → Stage 2)

A loan moves to Stage 2 when **any** of the following are true:

1. Days-past-due > 30 (quantitative backstop).
2. PD at reporting date is >2x the PD at initial recognition.
3. Watch-list / forbearance flag set in `int_loans__delinquency`.
4. External bureau score deteriorates by >100 points vs. origination.

## Stage 3 triggers

* Days-past-due > 90 (mandatory).
* Bankruptcy filing observed.
* Counter-party in default per the Basel definition (cross-default applies
  across all of the customer's facilities at the bank).

## Outputs

The staging vector and ECL are materialised on every loan in
`dbt_marts_risk.fct_loan_loss_provision` with one row per
(loan_id, reporting_date). The dashboard at
Superset → "Risk & Compliance" reflects this table.
""",
    ),
    FileSpec(
        name="ecl-calculation-guide",
        display_name="ECL Calculation Guide",
        description="Expected Credit Loss formula, PD × LGD × EAD discounting.",
        folder="IFRS9",
        body="""# Expected Credit Loss (ECL) Calculation Guide

## Formula

For Stage 1 (12-month ECL):

```
ECL_12m = sum over t in [1..12] of (PD_t * LGD_t * EAD_t) / (1 + EIR)^t
```

For Stage 2 / 3 (lifetime ECL):

```
ECL_lifetime = sum over t in [1..T] of (PD_t * LGD_t * EAD_t) / (1 + EIR)^t
```

where `T` is the remaining contractual term (capped at behavioural life for
revolving products).

## Inputs

| Input | Source                                                     |
|-------|------------------------------------------------------------|
| PD_t  | PD model (12-month or lifetime curve)                      |
| LGD_t | LGD model output, conditioned on collateral coverage       |
| EAD_t | Amortisation schedule from `int_loans__schedule`           |
| EIR   | Effective Interest Rate from `raw_lending.loan_originations` |

## Macro overlays

We adjust the through-the-cycle PD curve with three macroeconomic scenarios
(Baseline / Upside / Downside) weighted at 50/20/30 by default. Scenario
weights are stored in `raw_risk.ifrs9_scenarios` with effective dating, so we
can replay historical reporting periods exactly.

## Reconciliation

Stage-by-stage ECL totals are reconciled to the General Ledger every
month-end. Differences > $50k trigger an automatic Jira to the Risk team.
""",
    ),
    # --- Finance / Basel ----------------------------------------------------
    FileSpec(
        name="basel3-capital-reporting",
        display_name="Basel III Capital Reporting",
        description="RWA, CET1 and capital adequacy reporting cadence.",
        folder="BaselIII",
        body="""# Basel III Capital Reporting

## Reporting cadence

| Output         | Cadence    | Owner     | Source                                 |
|----------------|------------|-----------|----------------------------------------|
| RWA by segment | Daily      | Finance   | `dbt_marts_risk.fct_loan_loss_provision`|
| CET1 ratio     | Monthly    | Treasury  | derived                                |
| Leverage ratio | Monthly    | Treasury  | derived                                |
| COREP returns  | Quarterly  | Regulatory| derived                                |
| Pillar 3       | Semi-annual| Regulatory| derived                                |

## RWA approach

We use the **Standardised Approach** for credit risk, the **Basic Indicator
Approach** for operational risk, and the **Standardised Approach** for market
risk. IRB transition is on the multi-year roadmap (see Strategy folder).

## Materiality thresholds

Any one-day movement of >25 bps in the CET1 ratio is escalated to ALCO.
Any breach of the Pillar 2 Capital Conservation Buffer triggers a P1 incident
and an out-of-cycle dividend review.
""",
    ),
    # --- Data Engineering ---------------------------------------------------
    FileSpec(
        name="dbt-model-conventions",
        display_name="dbt Model Conventions",
        description="Naming, materialisation, testing and ownership conventions.",
        folder="DataEngineering",
        body="""# dbt Model Conventions (Banking)

## Naming

* `stg_<source>__<table>` — staging models.
* `int_<concept>__<subject>` — intermediate (business logic).
* `dim_<entity>` — conformed dimensions.
* `fct_<event>` — fact tables.

## Materialisation

| Layer        | Materialisation | Schema target          |
|--------------|-----------------|------------------------|
| Staging      | view            | `dbt_staging`          |
| Intermediate | view            | `dbt_intermediate`     |
| Mart (core)  | table           | `dbt_marts_core`       |
| Mart (risk)  | table           | `dbt_marts_risk`       |
| Mart (finance)| table          | `dbt_marts_finance`    |

## Tests

Every staging model must have at least:

* `not_null` on the primary key.
* `unique` on the primary key.
* Source freshness check declared in `sources.yml`.

Every mart fact must declare a `relationships` test against its dimensions
and at least one custom business-logic test.

## Ownership

Each domain owns its mart schema:

| Domain               | Schemas owned                  |
|----------------------|--------------------------------|
| Customer Ops         | `dbt_marts_core`, marketing    |
| Risk & Compliance    | `dbt_marts_risk`               |
| Finance              | `dbt_marts_finance`            |
| Wealth Management    | `dbt_marts_wealth`             |
| Digital              | (consumes core + risk)         |
""",
    ),
    FileSpec(
        name="pii-classification-guide",
        display_name="PII Classification Guide",
        description="How we tag PII columns and which tags to apply.",
        folder="DataEngineering",
        body="""# PII Classification Guide

## Tag catalogue

The PII classification surfaces nine tags under the `PII.Banking` classification:

| Tag                      | Examples                                |
|--------------------------|-----------------------------------------|
| `PII.Sensitive`          | SSN, passport, national ID              |
| `PII.NonSensitive`       | First name, last name (alone)           |
| `PII.Financial`          | IBAN, account number, masked PAN        |
| `PII.Contact`            | Email, phone, address                   |
| `PII.Biometric`          | Face image, fingerprint hash            |
| `PII.Geolocation`        | Lat/long, IP                            |
| `PII.Device`             | Device fingerprint, advertising ID      |
| `PII.HealthRelated`      | Insurance claim notes                   |
| `PII.AuthCredentials`    | Password hash, session token            |

## Auto-classification

The classification ingestion workflow runs daily and tags columns based on
regex + dictionary matches (see `ingestion/redshift_autoclassification.yaml`).
Manual overrides take precedence; tags can be locked with `lockTag: true`.

## Storage rules

* `PII.Sensitive` must never be stored in plaintext. Use the SHA-256 hashing
  helpers in `dbt/macros/hash_pii.sql`.
* `PII.Financial` may be tokenised (preferred) or stored masked
  (e.g. `4111 **** **** 1234`).
* Any `PII.*` column added to a `dbt_marts_*` table requires a domain owner
  approval recorded in the PR description.

## Right-to-erasure (GDPR / CCPA)

DSAR delete requests are processed via `cookbook/resources/gdpr-demo` — see
that cookbook for the full flow.
""",
    ),
]


ARTICLES: list[ArticleSpec] = [
    ArticleSpec(
        name="customer-360-data-model",
        display_name="Customer-360 Data Model",
        description="""# Customer-360 Data Model

The Customer-360 layer joins identity, behavioural, risk and product data
into a single conformed dimension that every downstream consumer can rely on.

## Source layout

```
raw_core_banking.customers           ─┐
raw_core_banking.customer_addresses  ─┼─► stg_core_banking__*
raw_core_banking.customer_contacts   ─┘
raw_cards.cards                       ─► stg_cards__cards
raw_lending.loan_applications         ─► stg_lending__loan_applications
raw_wealth.holdings                   ─► stg_wealth__holdings
raw_digital.web_sessions              ─► stg_digital__web_sessions
                                       └─► int_customers__360
                                            └─► dim_customers
```

## Refresh

* `dim_customers` is rebuilt every 6 hours in dbt.
* The CDC stream into the CDP runs every 30 minutes.

## Consumers

* CRM (`customer_id`, `kyc_risk_rating`, behavioural attributes).
* Superset Customer Ops dashboard.
* Marketing CDP (cohorts powered by `int_customers__360`).
* AI agents (Customer 360 lookup pattern memory references this article).
""",
    ),
    ArticleSpec(
        name="ifrs9-staging-logic",
        display_name="IFRS 9 Staging Logic (Quick Reference)",
        description="""# IFRS 9 Staging Logic — Quick Reference

A condensed view of the staging logic that runs nightly to populate
`dbt_marts_risk.fct_loan_loss_provision`.

## Logic at a glance

```
case
    when dpd > 90                          then 'Stage 3'
    when default_flag                      then 'Stage 3'
    when dpd > 30                          then 'Stage 2'
    when pd_at_reporting > 2 * pd_at_origination then 'Stage 2'
    when bureau_delta < -100               then 'Stage 2'
    when watchlist_flag                    then 'Stage 2'
    else 'Stage 1'
end as ifrs9_stage
```

## Cure logic

A facility cures from Stage 3 only after 12 consecutive months of full
contractual servicing. Cure from Stage 2 requires 3 consecutive months below
all SICR thresholds.

## Demo distribution (banking demo seeds)

| Stage    | Count   | % portfolio |
|----------|---------|-------------|
| Stage 1  | 18,200  | 81%         |
| Stage 2  | 3,150   | 14%         |
| Stage 3  | 1,150   | 5%          |
""",
    ),
    ArticleSpec(
        name="fraud-burst-playbook",
        display_name="Fraud Burst Playbook",
        description="""# Fraud Burst Playbook

The banking demo ships an engineered fraud burst: 10 customers × 80
card authorisations each over a single 24-hour window, surfaced in
`dbt_marts_core.fct_card_authorizations`. Walk it like an analyst would.

## 1. Trigger

`TM-003 — velocity spike vs 30d baseline` fires for every one of the ten
victim customers. The alert lands in `dbt_marts_risk.fct_aml_pipeline`.

## 2. Pivot

```sql
select customer_id, count(*) as auths, sum(amount_usd) as gross
from dbt_marts_core.fct_card_authorizations
where authorized_at between '2026-04-02' and '2026-04-03'
group by 1
order by gross desc
limit 50;
```

## 3. Common attributes

* Same BIN family (a chunk of compromised cards from a recent BIN dump).
* Many merchants in MCC 5816 (digital goods) — typical cash-out target.
* Authorisations from IPs that geolocate >2,000 km from the customer's home.

## 4. Containment

Auto-block all 10 cards. Notify the customers via push within 5 minutes.
""",
    ),
    ArticleSpec(
        name="pii-tag-taxonomy",
        display_name="PII Tag Taxonomy",
        description="""# PII Tag Taxonomy

The `PII.Banking` classification carries nine tags. See the
`pii-classification-guide` file for storage rules.

| Tag                   | Example columns                          | Found in                                |
|-----------------------|------------------------------------------|-----------------------------------------|
| `PII.Sensitive`       | `ssn_hash`                               | `raw_core_banking.customers`            |
| `PII.NonSensitive`    | `first_name`, `last_name`                | `raw_core_banking.customers`            |
| `PII.Financial`       | `account_number_masked`, `pan_masked`    | `raw_cards.payment_card_tokens`         |
| `PII.Contact`         | `email_hash`, `phone_hash`               | `raw_core_banking.customer_contacts`    |
| `PII.Biometric`       | `face_match_score`                       | `raw_risk.kyc_reviews`                  |
| `PII.Geolocation`     | `lat`, `lon`, `ip_address_hash`          | `raw_digital.login_attempts`            |
| `PII.Device`          | `device_fingerprint`                     | `raw_digital.login_attempts`            |
| `PII.HealthRelated`   | `claim_notes`                            | (not used in banking demo)              |
| `PII.AuthCredentials` | `session_token_hash`, `password_hash`    | `raw_digital.login_attempts`            |

Auto-classification settings live in
`ingestion/redshift_autoclassification.yaml`.
""",
    ),
    ArticleSpec(
        name="dispute-resolution-quickref",
        display_name="Dispute Resolution Quick Reference",
        description="""# Dispute Resolution SOP

This article mirrors the SOP file in the Drive; refer to that for the
authoritative version. Quick links to the supporting datasets:

* Dispute records — `raw_cards.card_disputes`
* Original auth — `dbt_marts_core.fct_card_authorizations`
* Customer profile — `dbt_marts_core.dim_customers`

## Dispute reason codes (top 5)

| Reason code         | Volume share | Outcome (declined %) |
|---------------------|--------------|----------------------|
| Goods not received  | 31%          | 22%                  |
| Did not recognize   | 24%          | 41%                  |
| Duplicate charge    | 14%          | 9%                   |
| Quality not as desc | 12%          | 18%                  |
| Cancelled service   | 11%          | 14%                  |
""",
    ),
    ArticleSpec(
        name="dbt-model-layers",
        display_name="dbt Model Layers (banking demo)",
        description="""# dbt Model Layers

The banking dbt project follows the standard staging /
intermediate / marts pattern.

```
seeds (raw_*.csv)
  └── staging  (dbt_staging)             # 1:1 with the raw layer
        └── intermediate (dbt_intermediate)  # business logic, no joins
              └── marts (dbt_marts_*)         # consumer-facing facts/dims
```

## Marts by domain

| Domain     | Schema              | Highlights                                              |
|------------|---------------------|---------------------------------------------------------|
| Core       | `dbt_marts_core`    | `dim_customers`, `fct_transactions`, `fct_card_*`       |
| Finance    | `dbt_marts_finance` | `fct_daily_balances`, `fct_monthly_pnl`, `fct_nim`      |
| Risk       | `dbt_marts_risk`    | `fct_loan_loss_provision`, `fct_aml_pipeline`           |
| Wealth     | `dbt_marts_wealth`  | `fct_aum`, `fct_trades`, `dim_holdings`                 |
| Marketing  | `dbt_marts_marketing`| `fct_campaign_attribution`, `fct_customer_engagement`  |

Lineage to the upstream Redshift raw layer is captured by the dbt ingestion
workflow; lineage from the marts to Superset dashboards is captured by the
Superset ingestion workflow.
""",
    ),
    ArticleSpec(
        name="data-quality-defects-catalog",
        display_name="Data Quality Defects Catalogue",
        description="""# Data Quality Defects Catalogue

The banking demo seed data ships eight intentional DQ defects so demos
can exercise the platform's DQ features. Each defect maps to a dbt test or a
profiler expectation.

| # | Defect                                                  | Table                              | Test type     |
|---|---------------------------------------------------------|------------------------------------|---------------|
| 1 | 0.4% of `customer_id` rows are NULL                     | `raw_core_banking.customer_contacts`| `not_null`    |
| 2 | `account_balance` < -10,000 in 12 rows                  | `raw_core_banking.accounts`        | `accepted_range` |
| 3 | Duplicate `transaction_id` (2 rows)                     | `raw_transactions.transactions`     | `unique`      |
| 4 | `ssn_hash` length != 64 in 8 rows                       | `raw_core_banking.customers`       | `string_length` |
| 5 | Future-dated `transaction_at`                           | `raw_transactions.transactions`     | `expression`  |
| 6 | Unknown `country_code` (not in ISO 3166)                | `raw_core_banking.customer_addresses`| `accepted_values` |
| 7 | `interest_rate` is NULL on Stage-1 loans                | `raw_lending.loan_originations`    | `not_null`    |
| 8 | `mcc` not in `merchant_category_codes`                  | `raw_cards.card_authorizations`    | `relationships` |
""",
    ),
]


QUICK_LINKS: list[QuickLinkSpec] = [
    QuickLinkSpec(
        name="superset-cfo-dashboard",
        display_name="Superset — Executive / CFO",
        description="Daily P&L, NIM, fee income and CET1 ratio.",
        url="http://localhost:8088/dashboard/list/?filters=(dashboard_title:(label:Executive%20%2F%20CFO,value:Executive%20%2F%20CFO))",
    ),
    QuickLinkSpec(
        name="superset-risk-dashboard",
        display_name="Superset — Risk & Compliance",
        description="IFRS 9 staging, AML alert pipeline, sanctions hits.",
        url="http://localhost:8088/dashboard/list/?filters=(dashboard_title:(label:Risk%20%26%20Compliance,value:Risk%20%26%20Compliance))",
    ),
    QuickLinkSpec(
        name="superset-customer-ops-dashboard",
        display_name="Superset — Customer Operations",
        description="NPS, dispute volumes, contact-centre KPIs.",
        url="http://localhost:8088/dashboard/list/?filters=(dashboard_title:(label:Customer%20Operations,value:Customer%20Operations))",
    ),
    QuickLinkSpec(
        name="fincen-bsa-resources",
        display_name="FinCEN — BSA Resource Centre",
        description="Authoritative FinCEN guidance on BSA, SAR filing and CTRs.",
        url="https://www.fincen.gov/resources",
    ),
    QuickLinkSpec(
        name="basel-committee-bcbs",
        display_name="BIS — Basel Committee Publications",
        description="Basel III standards, RWA computation guidance.",
        url="https://www.bis.org/bcbs/publications.htm",
    ),
]


MEMORIES: list[MemorySpec] = [
    # --- Faq ----------------------------------------------------------------
    MemorySpec(
        name="faq-where-are-masked-pans",
        owner_username="carol",
        title="Where are masked PANs stored?",
        question="Which Redshift table contains masked PANs for our card portfolio?",
        answer=(
            "Masked Primary Account Numbers (PANs) live in "
            "`raw_cards.payment_card_tokens`. The `pan_masked` column shows the "
            "first six and last four digits (e.g. `4111 ** **** 1234`). The "
            "full PAN is never persisted — only the token reference issued by "
            "the card processor. The classification ingestion workflow tags "
            "`pan_masked` with `PII.Banking.PII.Financial` automatically."
        ),
        memory_type="Faq",
        primary_table="raw_cards.payment_card_tokens",
    ),
    MemorySpec(
        name="faq-login-attempts-location",
        owner_username="bob",
        title="Where do we store login attempts?",
        question="Which table tracks digital login attempts (success and failure)?",
        answer=(
            "`raw_digital.login_attempts`. Every authentication attempt — "
            "successful or otherwise — is recorded with `customer_id`, "
            "`session_token_hash`, `device_fingerprint`, `ip_address_hash`, "
            "`country_code`, `attempt_outcome` (`success | mfa-required | "
            "denied`) and `attempted_at`. This is the canonical feed for ATO "
            "investigations and the source for the digital-engagement marts."
        ),
        memory_type="Faq",
        primary_table="raw_digital.login_attempts",
    ),
    MemorySpec(
        name="faq-ifrs9-staging-table",
        owner_username="bob",
        title="Which table holds IFRS 9 staging?",
        question="Where do I find each loan's IFRS 9 stage and ECL?",
        answer=(
            "`dbt_marts_risk.fct_loan_loss_provision`. One row per "
            "(`loan_id`, `reporting_date`). Key columns: `ifrs9_stage` "
            "(`Stage 1 | Stage 2 | Stage 3`), `pd_12m`, `pd_lifetime`, "
            "`lgd`, `ead`, `ecl_amount`, `ecl_currency`. The staging logic is "
            "documented in the `ifrs9-staging-methodology` file in Compliance "
            "→ IFRS 9."
        ),
        memory_type="Faq",
        primary_table="dbt_marts_risk.fct_loan_loss_provision",
    ),
    MemorySpec(
        name="faq-customer-360-table",
        owner_username="dave",
        title="What is the Customer-360 table?",
        question="Which table powers the Customer-360 view?",
        answer=(
            "`dbt_marts_core.dim_customers`. Conformed dimension with one row "
            "per `customer_id`, refreshed every 6 hours. Joins identity (from "
            "`raw_core_banking.customers`), behavioural (rolling spend, "
            "logins), risk (KYC rating, PEP flag) and product (cards, loans, "
            "deposits, holdings) attributes."
        ),
        memory_type="Faq",
        primary_table="dbt_marts_core.dim_customers",
    ),
    # --- Runbook ------------------------------------------------------------
    MemorySpec(
        name="runbook-fraud-burst-response",
        owner_username="bob",
        title="Respond to a fraud burst",
        question="What do I do when a fraud burst alert fires on a customer?",
        answer=(
            "Follow the **Fraud Incident Response Plan** (in Risk Management → "
            "Fraud). High-level:\n\n"
            "1. **Contain (0-30m)** — auto-block all cards in the cluster.\n"
            "2. **Investigate (30m-4h)** — pivot on device, geo, BIN, merchant "
            "using `dbt_marts_core.fct_card_authorizations`.\n"
            "3. **Remediate (4-72h)** — reissue cards, file disputes, tune the "
            "detection rule.\n\n"
            "The engineered banking demo burst (10 customers × 80 "
            "authorisations) lives on 2026-04-02 → 2026-04-03 in the same "
            "table — use it to rehearse the playbook."
        ),
        memory_type="Runbook",
        primary_table="dbt_marts_core.fct_card_authorizations",
    ),
    MemorySpec(
        name="runbook-chargeback-storm",
        owner_username="dave",
        title="Handle a chargeback storm",
        question="A merchant has 40+ disputes in 7 days — what's the playbook?",
        answer=(
            "A chargeback storm is a P2 incident. Steps:\n\n"
            "1. Pause settlement to the merchant via the acquiring processor.\n"
            "2. Pull every dispute from `raw_cards.card_disputes` joined to "
            "`dbt_marts_core.fct_card_authorizations` for that merchant_id.\n"
            "3. Classify reason codes — concentration in `Goods not received` "
            "or `Cancelled service` usually means merchant insolvency, not "
            "fraud.\n"
            "4. Escalate to merchant-acquiring risk; consider holding reserves.\n"
            "5. File a Visa / Mastercard merchant-monitoring report if the "
            "dispute-to-sales ratio exceeds 1%."
        ),
        memory_type="Runbook",
        primary_table="raw_cards.card_disputes",
    ),
    MemorySpec(
        name="runbook-ecl-recalculation",
        owner_username="bob",
        title="Recalculate ECL for a portfolio",
        question="How do I trigger an ad-hoc ECL recalculation for a specific portfolio?",
        answer=(
            "The ECL pipeline is dbt-driven and runs nightly. For an ad-hoc "
            "recalculation:\n\n"
            "```bash\n"
            "cd cookbook/resources/banking/dbt\n"
            "DBT_PROFILES_DIR=$(pwd) dbt run \\\n"
            "  --select +dbt_marts_risk.fct_loan_loss_provision \\\n"
            '  --vars \'{"reporting_date": "2026-03-31", "scenario_weights": '
            '{"baseline": 0.5, "upside": 0.2, "downside": 0.3}}\'\n'
            "```\n\n"
            "After the run, confirm the ECL totals reconcile to the GL within "
            "$50k per stage. If not, open a Jira to the Risk team before "
            "approving the report."
        ),
        memory_type="Runbook",
        primary_table="dbt_marts_risk.fct_loan_loss_provision",
    ),
    MemorySpec(
        name="runbook-sanctions-hit",
        owner_username="carol",
        title="Handle a sanctions screening hit",
        question="A transaction screened positive against OFAC — what now?",
        answer=(
            "See the **Sanctions Screening Runbook** in Compliance → AML. "
            "Summary:\n\n"
            "1. The payment hub freezes the transaction automatically.\n"
            "2. The on-call analyst compares the matched record against the "
            "customer profile in `dbt_marts_core.dim_customers` — look for "
            "DOB, nationality and alias overlap.\n"
            "3. If a **true positive**, escalate to the MLRO within 30 "
            "minutes; funds remain frozen pending regulatory direction.\n"
            "4. If a **false positive**, release and add to the whitelist "
            "with a 12-month review date.\n\n"
            "Every decision is appended to `raw_risk.sanctions_hits` with the "
            "list snapshot version so historical hits can be replayed exactly."
        ),
        memory_type="Runbook",
    ),
    # --- UseCase ------------------------------------------------------------
    MemorySpec(
        name="usecase-customer-churn",
        owner_username="dave",
        title="Compute customer churn",
        question="How do I compute monthly customer churn from the warehouse?",
        answer=(
            "Use `dbt_marts_core.dim_customers` with the engagement flags "
            "from `dbt_marts_marketing.fct_customer_engagement`. A customer is "
            "considered churned in month `M` when:\n\n"
            "* `last_transaction_at < M - 90 days`, AND\n"
            "* `total_balance < $50` at the end of month `M`, AND\n"
            "* No active card, loan or wealth account.\n\n"
            "```sql\n"
            "select date_trunc('month', as_of) as month,\n"
            "       count(*) filter (where churned) * 1.0 / count(*) as churn_rate\n"
            "from dbt_marts_marketing.fct_customer_engagement\n"
            "group by 1\n"
            "order by 1;\n"
            "```"
        ),
        memory_type="UseCase",
        primary_table="dbt_marts_core.dim_customers",
    ),
    MemorySpec(
        name="usecase-cfo-daily-revenue",
        owner_username="alice",
        title="Daily revenue for the CFO dashboard",
        question="How is the CFO dashboard daily-revenue tile sourced?",
        answer=(
            "From `dbt_marts_finance.fct_fee_revenue` joined to "
            "`dbt_marts_finance.fct_nim` for net-interest income. The Superset "
            "chart sums `fee_amount + nim_amount` grouped by `revenue_date`, "
            "with a 7-day moving average overlay. The chart is named "
            "`CFO — Daily Revenue (7-day MA)` and lives on the "
            "`Executive / CFO` dashboard."
        ),
        memory_type="UseCase",
        primary_table="dbt_marts_finance.fct_fee_revenue",
    ),
    MemorySpec(
        name="usecase-daily-fraud-query",
        owner_username="bob",
        title="Daily fraud monitoring query",
        question="What's the canonical daily query for fraud monitoring?",
        answer=(
            "```sql\n"
            "select customer_id,\n"
            "       count(*) as auths_24h,\n"
            "       sum(amount_usd) as gross_24h,\n"
            "       array_agg(distinct mcc) as mccs,\n"
            "       array_agg(distinct country_code) as countries\n"
            "from dbt_marts_core.fct_card_authorizations\n"
            "where authorized_at >= current_date - interval '1 day'\n"
            "group by 1\n"
            "having count(*) >= 10\n"
            "   and array_length(array_agg(distinct country_code), 1) >= 2\n"
            "order by gross_24h desc;\n"
            "```\n\n"
            "Flag any cluster with >10 authorisations and 2+ countries in 24h. "
            "Cross-reference with `raw_digital.login_attempts` for ATO context."
        ),
        memory_type="UseCase",
        primary_table="dbt_marts_core.fct_card_authorizations",
    ),
    MemorySpec(
        name="usecase-customer-360-lookup",
        owner_username="dave",
        title="Customer-360 lookup pattern",
        question="What's the recommended pattern for a Customer-360 lookup from an agent?",
        answer=(
            "Always go through `dbt_marts_core.dim_customers` — never query "
            "`raw_core_banking.customers` directly. The marts dimension "
            "applies the canonical filters (excludes test customers, masks PII "
            "where appropriate, joins KYC risk rating). Recommended columns "
            "for an agent answer: `customer_id`, `customer_segment`, "
            "`kyc_risk_rating`, `total_balance`, `last_transaction_at`, "
            "`active_products`. See the `customer-360-data-model` article for "
            "the full schema."
        ),
        memory_type="UseCase",
        primary_table="dbt_marts_core.dim_customers",
    ),
    # --- Note ---------------------------------------------------------------
    MemorySpec(
        name="note-pii-on-customers",
        owner_username="carol",
        title="PII columns on dim_customers",
        question="Which columns in dim_customers are PII?",
        answer=(
            "Tagged `PII.Banking.PII.Sensitive`: `ssn_hash` (note: hashed, but "
            "still treated as Sensitive because it's a direct identifier).\n\n"
            "Tagged `PII.Banking.PII.NonSensitive`: `full_name`, "
            "`date_of_birth`.\n\n"
            "Tagged `PII.Banking.PII.Contact`: `email_hash`, `phone_hash`.\n\n"
            "Tagged `PII.Banking.PII.Geolocation`: `country_of_residence`.\n\n"
            "Auto-classification is run nightly and the tags are locked once "
            "applied — manual overrides require an approved change."
        ),
        memory_type="Note",
        primary_table="dbt_marts_core.dim_customers",
    ),
    MemorySpec(
        name="note-hour-of-day-seasonality",
        owner_username="alice",
        title="Why we see hour-of-day seasonality",
        question="Why does transaction volume show strong hour-of-day seasonality?",
        answer=(
            "The banking demo seed generator (`generate_seed_data.py`) "
            "applies an intra-day curve plus a day-of-week factor plus a "
            "holiday calendar. Peak intra-day activity is at 11:00-13:00 and "
            "17:00-19:00 local time, with a trough at 03:00-05:00. Weekends "
            "show ~70% of weekday volume, public holidays ~40%. The seasonal "
            "shape is deterministic at seed=42 — useful when demoing baseline "
            "computations and anomaly detection."
        ),
        memory_type="Note",
        primary_table="dbt_marts_core.fct_transactions",
    ),
    MemorySpec(
        name="note-stage3-definition",
        owner_username="bob",
        title="What is a Stage 3 loan?",
        question="What does it mean for a loan to be in Stage 3 under IFRS 9?",
        answer=(
            "Stage 3 means the loan has objective evidence of credit "
            "impairment. The mandatory backstop is days-past-due > 90, but a "
            "loan can also be Stage 3 if the counter-party has defaulted on "
            "any of its other facilities (cross-default applies). Once in "
            "Stage 3, lifetime ECL applies and interest is recognised on the "
            "net carrying amount. Cure to Stage 2 only happens after 12 "
            "consecutive months of full contractual servicing."
        ),
        memory_type="Note",
        memory_scope="UserGlobal",
    ),
    MemorySpec(
        name="note-iban-mod97",
        owner_username="alice",
        title="IBAN modulo-97 check",
        question="Why do our IBANs validate with a modulo-97 check?",
        answer=(
            "ISO 13616 specifies that an IBAN is valid if, when rearranged "
            "(country code + check digits moved to the end) and converted to a "
            "number (letters → 2-digit codes A=10..Z=35), the result mod 97 "
            "equals 1. The seed generator computes correct check digits for "
            "every synthetic IBAN, so the demo dataset round-trips through "
            "any production validator. See the macro "
            "`dbt/macros/validate_iban.sql`."
        ),
        memory_type="Note",
        memory_scope="UserGlobal",
    ),
    MemorySpec(
        name="note-mcc-fraud-tiers",
        owner_username="carol",
        title="MCC fraud tiers",
        question="How are MCCs classified into fraud risk tiers?",
        answer=(
            "`raw_cards.merchant_category_codes` carries a `fraud_risk_tier` "
            "column (`High | Medium | Low`). High-risk MCCs include 7995 "
            "(gambling), 6051 (quasi-cash/crypto), 6010 (manual cash "
            "disbursement), 4829 (wire money orders). The tier is surfaced "
            "downstream on `dbt_marts_core.fct_card_authorizations.mcc_risk_tier`."
        ),
        memory_type="Note",
        primary_table="raw_cards.merchant_category_codes",
    ),
    # --- Preference ---------------------------------------------------------
    MemorySpec(
        name="pref-column-naming",
        owner_username="alice",
        title="Column naming convention",
        question="What's our column-naming convention?",
        answer=(
            "* `*_id` for foreign keys (always `bigint`).\n"
            "* `*_at` for absolute timestamps (always `timestamptz`).\n"
            "* `*_date` for calendar dates (no timezone).\n"
            "* `*_amount` for monetary values; pair with `*_currency` (ISO 4217).\n"
            "* `*_hash` for hashed PII (SHA-256 hex).\n"
            "* `*_flag` for booleans.\n"
            "* `is_*` is reserved for derived booleans in `dbt_marts_*` only.\n"
            "* Avoid abbreviations except for well-known industry terms "
            "(`pan`, `mcc`, `dpd`, `ecl`, `pd`, `lgd`, `ead`)."
        ),
        memory_type="Preference",
        memory_scope="UserGlobal",
    ),
    MemorySpec(
        name="pref-dashboard-palette",
        owner_username="alice",
        title="Dashboard colour palette",
        question="What colour palette do our dashboards use?",
        answer=(
            "Domain-keyed palette (consistent across Superset and OpenMetadata):\n\n"
            "* Customer Ops — `#0e7490` (cyan-700).\n"
            "* Risk & Compliance — `#b91c1c` (red-700).\n"
            "* Finance — `#0f766e` (teal-700).\n"
            "* Wealth Management — `#7c2d12` (orange-900).\n"
            "* Digital — `#1d4ed8` (blue-700).\n"
            "* Data Engineering — `#7c3aed` (violet-600).\n\n"
            "Always render the IFRS 9 stages with green (Stage 1), amber "
            "(Stage 2), red (Stage 3) for instant readability."
        ),
        memory_type="Preference",
        memory_scope="UserGlobal",
    ),
    MemorySpec(
        name="pref-exclude-test-customers",
        owner_username="dave",
        title="Always exclude test customers from KPIs",
        question="Should I include test customers in headline KPIs?",
        answer=(
            "Never. Filter on `dim_customers.customer_segment <> 'test'` (or "
            "the equivalent `is_test_customer = false` boolean on the mart) "
            "for every headline KPI, board pack, regulator report and "
            "external dashboard. The seed dataset reserves customer_ids "
            "1..50 for test accounts. They're useful for QA and end-to-end "
            "agent demos but must not contaminate published metrics."
        ),
        memory_type="Preference",
        primary_table="dbt_marts_core.dim_customers",
    ),
    MemorySpec(
        name="pref-default-time-zone",
        owner_username="alice",
        title="Default time zone for analysis",
        question="Which time zone should analytical queries use?",
        answer=(
            "Always **UTC** in storage; convert to the customer's local time "
            "zone only at the presentation layer. Timestamps on the marts are "
            "`timestamptz` and are stored in UTC. The intra-day seasonality "
            "curve (see `note-hour-of-day-seasonality`) is applied in UTC, "
            "then shifted by `customer.timezone` for behavioural features."
        ),
        memory_type="Preference",
        memory_scope="UserGlobal",
    ),
]


# ---------------------------------------------------------------------------
# Result tracking
# ---------------------------------------------------------------------------


@dataclass
class CategoryResult:
    label: str
    created: list[str] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class RunResult:
    folders: CategoryResult = field(default_factory=lambda: CategoryResult("Folders"))
    files: CategoryResult = field(default_factory=lambda: CategoryResult("Files"))
    pages: CategoryResult = field(default_factory=lambda: CategoryResult("Pages"))
    memories: CategoryResult = field(default_factory=lambda: CategoryResult("Memories"))

    @property
    def categories(self) -> list[CategoryResult]:
        return [self.folders, self.files, self.pages, self.memories]

    @property
    def has_failures(self) -> bool:
        return any(c.failed for c in self.categories)

    def print_summary(self) -> None:
        logger.info("--- Summary ---")
        for cat in self.categories:
            logger.info(
                "  %-9s created=%d skipped=%d failed=%d",
                cat.label + ":",
                len(cat.created),
                len(cat.skipped),
                len(cat.failed),
            )
            for name in cat.created:
                logger.debug("    + %s", name)
            for name, reason in cat.skipped:
                logger.debug("    = %s (%s)", name, reason)
            for name, reason in cat.failed:
                logger.error("    ! %s — %s", name, reason)


# ---------------------------------------------------------------------------
# HTTP client
# ---------------------------------------------------------------------------


def _normalize_host(host: str) -> str:
    host = host.rstrip("/")
    if not host.endswith("/api"):
        host = f"{host}/api"
    return host


class CollateClient:
    """Thin wrapper around requests for the Context Center REST endpoints."""

    def __init__(self, host: str, token: str) -> None:
        self.base = _normalize_host(host)
        self.token = token
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            }
        )

    # -- generic helpers --------------------------------------------------

    def _json_headers(self) -> dict[str, str]:
        return {"Content-Type": "application/json"}

    def _multipart_headers(self) -> dict[str, str]:
        # requests sets Content-Type on multipart automatically; only auth + accept
        # are needed.
        return {}

    def health(self) -> None:
        url = f"{self.base}/v1/system/version"
        response = self.session.get(url, timeout=15)
        response.raise_for_status()
        logger.info("Connected to OpenMetadata at %s", self.base)

    # -- folders ----------------------------------------------------------

    def folder_get_by_fqn(self, fqn: str) -> dict[str, Any] | None:
        url = f"{self.base}{FOLDERS_PATH}/name/{fqn}"
        response = self.session.get(url, timeout=15)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    def folder_create(self, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base}{FOLDERS_PATH}"
        response = self.session.post(
            url, json=payload, headers=self._json_headers(), timeout=30
        )
        if response.status_code >= 400:
            raise RuntimeError(f"POST {url} -> {response.status_code}: {response.text}")
        return response.json()

    def folder_delete(self, folder_id: str) -> None:
        url = f"{self.base}{FOLDERS_PATH}/{folder_id}"
        response = self.session.delete(
            url, params={"hardDelete": True, "recursive": True}, timeout=30
        )
        if response.status_code >= 400 and response.status_code != 404:
            raise RuntimeError(
                f"DELETE {url} -> {response.status_code}: {response.text}"
            )

    # -- files ------------------------------------------------------------

    def file_get_by_fqn(self, fqn: str) -> dict[str, Any] | None:
        url = f"{self.base}{FILES_PATH}/name/{fqn}"
        response = self.session.get(url, timeout=15)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    def file_upload(
        self,
        *,
        filename: str,
        body: bytes,
        display_name: str,
        description: str,
        folder_fqn: str,
        content_type: str = "text/markdown",
    ) -> dict[str, Any]:
        url = f"{self.base}{FILES_UPLOAD_PATH}"
        files = {"file": (filename, io.BytesIO(body), content_type)}
        data = {
            "displayName": display_name,
            "description": description,
            "folder": folder_fqn,
        }
        response = self.session.post(url, files=files, data=data, timeout=60)
        if response.status_code >= 400:
            raise RuntimeError(f"POST {url} -> {response.status_code}: {response.text}")
        return response.json()

    def file_create_metadata(self, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base}{FILES_PATH}"
        response = self.session.post(
            url, json=payload, headers=self._json_headers(), timeout=30
        )
        if response.status_code >= 400:
            raise RuntimeError(f"POST {url} -> {response.status_code}: {response.text}")
        return response.json()

    def file_delete(self, file_id: str) -> None:
        url = f"{self.base}{FILES_PATH}/{file_id}"
        response = self.session.delete(url, params={"hardDelete": True}, timeout=30)
        if response.status_code >= 400 and response.status_code != 404:
            raise RuntimeError(
                f"DELETE {url} -> {response.status_code}: {response.text}"
            )

    # -- pages ------------------------------------------------------------

    def page_get_by_fqn(self, fqn: str) -> dict[str, Any] | None:
        url = f"{self.base}{PAGES_PATH}/name/{fqn}"
        response = self.session.get(url, timeout=15)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    def page_create(self, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base}{PAGES_PATH}"
        response = self.session.post(
            url, json=payload, headers=self._json_headers(), timeout=30
        )
        if response.status_code >= 400:
            raise RuntimeError(f"POST {url} -> {response.status_code}: {response.text}")
        return response.json()

    def page_delete(self, page_id: str) -> None:
        url = f"{self.base}{PAGES_PATH}/{page_id}"
        response = self.session.delete(url, params={"hardDelete": True}, timeout=30)
        if response.status_code >= 400 and response.status_code != 404:
            raise RuntimeError(
                f"DELETE {url} -> {response.status_code}: {response.text}"
            )

    # -- memories ---------------------------------------------------------

    def memory_get_by_name(self, name: str) -> dict[str, Any] | None:
        url = f"{self.base}{MEMORIES_PATH}/name/{name}"
        response = self.session.get(url, timeout=15)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    def memory_create(
        self,
        payload: dict[str, Any],
        *,
        impersonate_as: str | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base}{MEMORIES_PATH}"
        headers = self._json_headers()
        if impersonate_as is not None:
            headers["X-Impersonate-User"] = impersonate_as
        response = self.session.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code >= 400:
            raise RuntimeError(f"POST {url} -> {response.status_code}: {response.text}")
        return response.json()

    def memory_delete(self, memory_id: str) -> None:
        url = f"{self.base}{MEMORIES_PATH}/{memory_id}"
        response = self.session.delete(url, params={"hardDelete": True}, timeout=30)
        if response.status_code >= 400 and response.status_code != 404:
            raise RuntimeError(
                f"DELETE {url} -> {response.status_code}: {response.text}"
            )

    # -- table ref --------------------------------------------------------

    def table_get_by_fqn(self, fqn: str) -> dict[str, Any] | None:
        url = f"{self.base}{TABLES_PATH}/name/{fqn}"
        response = self.session.get(url, timeout=15)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    # -- user ref ---------------------------------------------------------

    def user_get_by_name(self, name: str) -> dict[str, Any] | None:
        url = f"{self.base}{USERS_PATH}/name/{name}"
        response = self.session.get(url, timeout=15)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    # -- pagination -------------------------------------------------------

    def _list_all(self, path: str, page_size: int = 100) -> list[dict[str, Any]]:
        """Page through a list endpoint and return every entity."""
        url = f"{self.base}{path}"
        results: list[dict[str, Any]] = []
        params: dict[str, Any] = {"limit": page_size}
        while True:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            body = response.json()
            results.extend(body.get("data", []))
            after = (body.get("paging") or {}).get("after")
            if not after:
                break
            params = {"limit": page_size, "after": after}
        return results

    def list_folders(self) -> list[dict[str, Any]]:
        return self._list_all(FOLDERS_PATH)

    def list_files(self) -> list[dict[str, Any]]:
        return self._list_all(FILES_PATH)

    def list_pages(self) -> list[dict[str, Any]]:
        return self._list_all(PAGES_PATH)

    def list_memories(self) -> list[dict[str, Any]]:
        return self._list_all(MEMORIES_PATH)


# ---------------------------------------------------------------------------
# Seeders
# ---------------------------------------------------------------------------


def seed_folders(
    client: CollateClient,
    *,
    dry_run: bool,
    force: bool,
    result: RunResult,
) -> dict[str, str]:
    """Create folders in two passes (parents first, then children).

    Returns a mapping of folder name → FQN, used downstream for files.
    """
    fqn_by_name: dict[str, str] = {}

    # Sort: parents before children (parents have parent=None).
    ordered = sorted(FOLDERS, key=lambda f: (f.parent is not None, f.name))

    for spec in ordered:
        parent_fqn = fqn_by_name.get(spec.parent) if spec.parent else None
        expected_fqn = f"{parent_fqn}.{spec.name}" if parent_fqn else spec.name

        existing = client.folder_get_by_fqn(expected_fqn)
        if existing is not None and not force:
            fqn_by_name[spec.name] = existing.get("fullyQualifiedName", expected_fqn)
            result.folders.skipped.append((spec.name, "already exists"))
            logger.info("Folder %s already exists", expected_fqn)
            continue

        if existing is not None and force:
            if dry_run:
                logger.info("[dry-run] would delete folder %s", expected_fqn)
            else:
                client.folder_delete(existing["id"])
                logger.info("Deleted folder %s for recreation", expected_fqn)

        payload: dict[str, Any] = {
            "name": spec.name,
            "displayName": spec.display_name,
            "description": spec.description,
        }
        if spec.icon is not None:
            payload["icon"] = spec.icon
        if spec.color is not None:
            payload["color"] = spec.color
        if parent_fqn is not None:
            payload["parent"] = parent_fqn

        if dry_run:
            fqn_by_name[spec.name] = expected_fqn
            result.folders.created.append(spec.name)
            logger.info("[dry-run] would create folder %s", expected_fqn)
            continue

        try:
            created = client.folder_create(payload)
        except Exception as exc:  # noqa: BLE001 — collected to summary
            result.folders.failed.append((spec.name, str(exc)))
            logger.error("Failed to create folder %s: %s", spec.name, exc)
            continue

        fqn_by_name[spec.name] = created.get("fullyQualifiedName", expected_fqn)
        result.folders.created.append(spec.name)
        logger.info("Created folder %s", fqn_by_name[spec.name])

    return fqn_by_name


def seed_files(
    client: CollateClient,
    folder_fqns: dict[str, str],
    *,
    dry_run: bool,
    force: bool,
    upload_enabled: bool,
    result: RunResult,
) -> None:
    """Upload each markdown file to its parent folder."""
    for spec in FILES:
        if spec.folder not in folder_fqns:
            result.files.failed.append(
                (spec.name, f"parent folder '{spec.folder}' not in folder map")
            )
            continue
        folder_fqn = folder_fqns[spec.folder]
        expected_fqn = f"{folder_fqn}.{spec.name}"

        existing = client.file_get_by_fqn(expected_fqn)
        if existing is not None and not force:
            result.files.skipped.append((spec.name, "already exists"))
            logger.info("File %s already exists", expected_fqn)
            continue

        if existing is not None and force:
            if dry_run:
                logger.info("[dry-run] would delete file %s", expected_fqn)
            else:
                client.file_delete(existing["id"])
                logger.info("Deleted file %s for recreation", expected_fqn)

        if dry_run:
            result.files.created.append(spec.name)
            logger.info("[dry-run] would create file %s", expected_fqn)
            continue

        body_bytes = spec.body.encode("utf-8")
        filename = f"{spec.name}.md"

        if upload_enabled:
            try:
                client.file_upload(
                    filename=filename,
                    body=body_bytes,
                    display_name=spec.display_name,
                    description=spec.description,
                    folder_fqn=folder_fqn,
                )
                result.files.created.append(spec.name)
                logger.info("Uploaded file %s", expected_fqn)
                continue
            except Exception as exc:  # noqa: BLE001 — fall back to metadata
                msg = str(exc)
                if "503" in msg or "Object storage" in msg:
                    logger.warning(
                        "Multipart upload unavailable (storage not configured?); "
                        "falling back to metadata-only for %s",
                        spec.name,
                    )
                else:
                    result.files.failed.append((spec.name, msg))
                    logger.error("Upload failed for %s: %s", spec.name, msg)
                    continue

        payload: dict[str, Any] = {
            "name": spec.name,
            "displayName": spec.display_name,
            "description": (spec.description + "\n\n---\n\n" + spec.body),
            "fileType": "Document",
            "contentType": "text/markdown",
            "fileExtension": "md",
            "fileSize": len(body_bytes),
            "sourceType": "Upload",
            "folder": folder_fqn,
        }
        try:
            client.file_create_metadata(payload)
        except Exception as exc:  # noqa: BLE001 — collected to summary
            result.files.failed.append((spec.name, str(exc)))
            logger.error("Failed to create file %s: %s", spec.name, exc)
            continue

        result.files.created.append(spec.name)
        logger.info("Created file metadata %s", expected_fqn)


def seed_pages(
    client: CollateClient,
    *,
    dry_run: bool,
    force: bool,
    result: RunResult,
) -> None:
    """Create articles + quick-link pages."""

    def _process(
        name: str,
        payload: dict[str, Any],
    ) -> None:
        existing = client.page_get_by_fqn(name)
        if existing is not None and not force:
            result.pages.skipped.append((name, "already exists"))
            logger.info("Page %s already exists", name)
            return
        if existing is not None and force:
            if dry_run:
                logger.info("[dry-run] would delete page %s", name)
            else:
                client.page_delete(existing["id"])
                logger.info("Deleted page %s for recreation", name)

        if dry_run:
            result.pages.created.append(name)
            logger.info("[dry-run] would create page %s", name)
            return
        try:
            client.page_create(payload)
        except Exception as exc:  # noqa: BLE001 — collected to summary
            result.pages.failed.append((name, str(exc)))
            logger.error("Failed to create page %s: %s", name, exc)
            return
        result.pages.created.append(name)
        logger.info("Created page %s", name)

    for article in ARTICLES:
        payload = {
            "name": article.name,
            "displayName": article.display_name,
            "description": article.description,
            "pageType": "Article",
            "page": {},
            "entityStatus": "Approved",
        }
        _process(article.name, payload)

    for link in QUICK_LINKS:
        payload = {
            "name": link.name,
            "displayName": link.display_name,
            "description": link.description,
            "pageType": "QuickLink",
            "page": {"url": link.url},
            "entityStatus": "Approved",
        }
        _process(link.name, payload)


def _resolve_owners(
    client: CollateClient, usernames: set[str]
) -> dict[str, dict[str, Any]]:
    """Resolve OM usernames to EntityReference dicts. Missing users return {}."""
    resolved: dict[str, dict[str, Any]] = {}
    for username in sorted(usernames):
        user = client.user_get_by_name(username)
        if user is None:
            logger.warning(
                "Owner '%s' not found — memories with this owner will be created "
                "without an explicit owner.",
                username,
            )
            continue
        resolved[username] = {
            "id": user["id"],
            "type": "user",
            "name": user["name"],
            "fullyQualifiedName": user.get("fullyQualifiedName", user["name"]),
        }
    return resolved


def seed_memories(
    client: CollateClient,
    *,
    db_service: str,
    database: str,
    dry_run: bool,
    force: bool,
    impersonate: bool,
    result: RunResult,
) -> None:
    """Create context memories, attaching to Redshift tables when resolvable.

    When ``impersonate`` is True we POST each memory with the
    ``X-Impersonate-User`` header set to ``spec.owner_username`` so the
    memory's ``updatedBy`` (and hence the "Created by" displayed in the UI)
    reflects the assigned author. Impersonation is rejected with 403 unless
    the JWT belongs to a bot user; on that failure we log a warning and
    retry without the header so the script still completes.
    """
    # Pre-resolve owners once so we don't hammer /v1/users/name for each memory.
    needed_owners = {
        spec.owner_username for spec in MEMORIES if spec.owner_username is not None
    }
    owner_refs = _resolve_owners(client, needed_owners) if needed_owners else {}

    # Tracks whether impersonation has been disabled mid-run (e.g. because the
    # caller's token is not a bot token) so we stop trying on subsequent rows.
    impersonate_enabled = impersonate

    for spec in MEMORIES:
        existing = client.memory_get_by_name(spec.name)
        if existing is not None and not force:
            result.memories.skipped.append((spec.name, "already exists"))
            logger.info("Memory %s already exists", spec.name)
            continue
        if existing is not None and force:
            if dry_run:
                logger.info("[dry-run] would delete memory %s", spec.name)
            else:
                client.memory_delete(existing["id"])
                logger.info("Deleted memory %s for recreation", spec.name)

        primary_entity = None
        if spec.primary_table is not None:
            table_fqn = f"{db_service}.{database}.{spec.primary_table}"
            table = client.table_get_by_fqn(table_fqn)
            if table is None:
                logger.warning(
                    "Memory %s: table %s not in catalog — creating without "
                    "primaryEntity",
                    spec.name,
                    table_fqn,
                )
            else:
                primary_entity = {
                    "id": table["id"],
                    "type": "table",
                    "name": table["name"],
                    "fullyQualifiedName": table.get("fullyQualifiedName", table_fqn),
                }

        payload: dict[str, Any] = {
            "name": spec.name,
            "title": spec.title,
            "question": spec.question,
            "answer": spec.answer,
            "memoryType": spec.memory_type,
            "memoryScope": spec.memory_scope,
            "shareConfig": {"visibility": spec.visibility},
        }
        if primary_entity is not None:
            payload["primaryEntity"] = primary_entity
        if spec.owner_username is not None and spec.owner_username in owner_refs:
            payload["owners"] = [owner_refs[spec.owner_username]]

        # Only attempt impersonation when the user exists on the target instance.
        # `impersonate_as=None` means "post as the caller", which is what we want
        # for memories with no owner_username or with an unresolved owner.
        impersonate_as: str | None = None
        if (
            impersonate_enabled
            and spec.owner_username is not None
            and spec.owner_username in owner_refs
        ):
            impersonate_as = spec.owner_username

        if dry_run:
            result.memories.created.append(spec.name)
            logger.info(
                "[dry-run] would create memory %s (owner=%s, impersonate=%s)",
                spec.name,
                spec.owner_username or "—",
                impersonate_as or "—",
            )
            continue

        try:
            client.memory_create(payload, impersonate_as=impersonate_as)
            created_via = impersonate_as
        except Exception as exc:  # noqa: BLE001 — handled below
            msg = str(exc)
            impersonation_rejected = impersonate_as is not None and (
                "Only bot users can impersonate" in msg
                or " 403" in msg
                or " 401" in msg
            )
            if not impersonation_rejected:
                result.memories.failed.append((spec.name, msg))
                logger.error("Failed to create memory %s: %s", spec.name, exc)
                continue

            logger.warning(
                "Impersonation rejected by server (token is not a bot user). "
                "Disabling impersonation and retrying %s without header.",
                spec.name,
            )
            impersonate_enabled = False
            try:
                client.memory_create(payload, impersonate_as=None)
            except Exception as exc2:  # noqa: BLE001 — collected to summary
                result.memories.failed.append((spec.name, str(exc2)))
                logger.error(
                    "Failed to create memory %s (after impersonation retry): %s",
                    spec.name,
                    exc2,
                )
                continue
            created_via = None

        result.memories.created.append(spec.name)
        logger.info(
            "Created memory %s (owner=%s, author=%s)",
            spec.name,
            spec.owner_username or "—",
            created_via or "caller",
        )


# ---------------------------------------------------------------------------
# Purge
# ---------------------------------------------------------------------------


@dataclass
class PurgeResult:
    deleted: dict[str, int] = field(
        default_factory=lambda: {
            "folders": 0,
            "files": 0,
            "pages": 0,
            "memories": 0,
        }
    )
    failed: list[tuple[str, str]] = field(default_factory=list)

    @property
    def has_failures(self) -> bool:
        return bool(self.failed)

    def print_summary(self) -> None:
        logger.info("--- Purge Summary ---")
        for label, count in self.deleted.items():
            logger.info("  %-9s deleted=%d", label + ":", count)
        if self.failed:
            for name, reason in self.failed:
                logger.error("  ! %s — %s", name, reason)


def purge_all(client: CollateClient, *, dry_run: bool) -> PurgeResult:
    """Hard-delete every Context Center folder, file, page and memory."""
    result = PurgeResult()

    # Order matters: memories + pages + files first, then folders (which can
    # cascade through their children once their content is gone).
    plan: list[tuple[str, list[dict[str, Any]], Any]] = [
        ("memories", client.list_memories(), client.memory_delete),
        ("pages", client.list_pages(), client.page_delete),
        ("files", client.list_files(), client.file_delete),
        # For folders use recursive delete so any leftover children go too.
        ("folders", client.list_folders(), client.folder_delete),
    ]

    for label, entities, delete_fn in plan:
        logger.info("Purging %d %s…", len(entities), label)
        for entity in entities:
            entity_id = entity.get("id")
            entity_name = entity.get("fullyQualifiedName") or entity.get("name", "?")
            if not entity_id:
                continue
            if dry_run:
                logger.info("[dry-run] would delete %s %s", label, entity_name)
                result.deleted[label] += 1
                continue
            try:
                delete_fn(entity_id)
            except Exception as exc:  # noqa: BLE001 — keep going past one bad row
                result.failed.append((f"{label}:{entity_name}", str(exc)))
                logger.error("Failed to delete %s %s: %s", label, entity_name, exc)
                continue
            result.deleted[label] += 1
            logger.info("Deleted %s %s", label, entity_name)

    return result


# ---------------------------------------------------------------------------
# Orchestration + CLI
# ---------------------------------------------------------------------------


def run(
    client: CollateClient,
    *,
    db_service: str,
    database: str,
    upload_enabled: bool,
    dry_run: bool,
    force: bool,
    impersonate: bool,
) -> RunResult:
    result = RunResult()

    logger.info("Seeding folders…")
    folder_fqns = seed_folders(client, dry_run=dry_run, force=force, result=result)

    logger.info("Seeding files (upload=%s)…", upload_enabled)
    seed_files(
        client,
        folder_fqns,
        dry_run=dry_run,
        force=force,
        upload_enabled=upload_enabled,
        result=result,
    )

    logger.info("Seeding pages…")
    seed_pages(client, dry_run=dry_run, force=force, result=result)

    logger.info(
        "Seeding memories (db_service=%s database=%s impersonate=%s)…",
        db_service,
        database,
        impersonate,
    )
    seed_memories(
        client,
        db_service=db_service,
        database=database,
        dry_run=dry_run,
        force=force,
        impersonate=impersonate,
        result=result,
    )

    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Seed banking-themed Context Center content (folders, files, "
            "pages, memories) into OpenMetadata for the banking demo."
        )
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("AI_SDK_HOST"),
        help="OpenMetadata host (or env AI_SDK_HOST).",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("AI_SDK_TOKEN"),
        help="JWT bearer token (or env AI_SDK_TOKEN).",
    )
    parser.add_argument(
        "--db-service",
        default="banking-redshift",
        help="Redshift service name in OpenMetadata (for FQN resolution).",
    )
    parser.add_argument(
        "--database",
        default=os.environ.get("REDSHIFT_DATABASE", "dev"),
        help="Redshift database name (for FQN resolution).",
    )
    parser.add_argument(
        "--no-upload",
        dest="upload",
        action="store_false",
        default=True,
        help="Skip multipart file uploads; create metadata-only file entries.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete and recreate entities that already exist.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be created without making changes.",
    )
    parser.add_argument(
        "--no-impersonate",
        dest="impersonate",
        action="store_false",
        default=True,
        help=(
            "Do not set X-Impersonate-User when creating memories; every "
            "memory will be authored by the caller's token. Default is to "
            "impersonate the owner_username on each memory (requires a bot "
            "JWT; auto-falls-back to no impersonation on 401/403)."
        ),
    )
    parser.add_argument(
        "--purge",
        action="store_true",
        help=(
            "Hard-delete every Context Center entity (folders, files, pages, "
            "memories) and exit. Does NOT re-seed."
        ),
    )
    parser.add_argument(
        "--purge-memories",
        action="store_true",
        help=(
            "Hard-delete every Context Center memory and exit. Does NOT touch "
            "folders, files or pages, and does NOT re-seed."
        ),
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level (DEBUG/INFO/WARNING/ERROR).",
    )
    return parser.parse_args()


def _purge_memories_only(client: CollateClient, *, dry_run: bool) -> PurgeResult:
    """Hard-delete every Context Center memory and return the summary."""
    result = PurgeResult()
    entities = client.list_memories()
    logger.info("Purging %d memories…", len(entities))
    for entity in entities:
        entity_id = entity.get("id")
        entity_name = entity.get("fullyQualifiedName") or entity.get("name", "?")
        if not entity_id:
            continue
        if dry_run:
            logger.info("[dry-run] would delete memory %s", entity_name)
            result.deleted["memories"] += 1
            continue
        try:
            client.memory_delete(entity_id)
        except Exception as exc:  # noqa: BLE001 — keep going past one bad row
            result.failed.append((f"memories:{entity_name}", str(exc)))
            logger.error("Failed to delete memory %s: %s", entity_name, exc)
            continue
        result.deleted["memories"] += 1
        logger.info("Deleted memory %s", entity_name)
    return result


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s %(levelname)s %(message)s",
    )

    if not args.host or not args.token:
        logger.error("Set AI_SDK_HOST and AI_SDK_TOKEN (or pass --host/--token).")
        return 2

    if args.purge and args.purge_memories:
        logger.error("--purge and --purge-memories are mutually exclusive.")
        return 2

    client = CollateClient(args.host, args.token)
    if not args.dry_run:
        client.health()

    if args.purge:
        logger.info(
            "Purging ALL Context Center entities against %s (dry_run=%s)",
            args.host,
            args.dry_run,
        )
        purge_result = purge_all(client, dry_run=args.dry_run)
        purge_result.print_summary()
        return 1 if purge_result.has_failures else 0

    if args.purge_memories:
        logger.info(
            "Purging Context Center memories against %s (dry_run=%s)",
            args.host,
            args.dry_run,
        )
        purge_result = _purge_memories_only(client, dry_run=args.dry_run)
        purge_result.print_summary()
        return 1 if purge_result.has_failures else 0

    logger.info(
        "Seeding Context Center against %s (dry_run=%s, force=%s, upload=%s)",
        args.host,
        args.dry_run,
        args.force,
        args.upload,
    )

    result = run(
        client,
        db_service=args.db_service,
        database=args.database,
        upload_enabled=args.upload,
        dry_run=args.dry_run,
        force=args.force,
        impersonate=args.impersonate,
    )
    result.print_summary()
    return 1 if result.has_failures else 0


if __name__ == "__main__":
    sys.exit(main())
