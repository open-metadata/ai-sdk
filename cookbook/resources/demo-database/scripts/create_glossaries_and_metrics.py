"""
Create OpenMetadata Glossaries, Glossary Terms, and Metrics
for the Jaffle Shop demo database.

Requires:
    pip install openmetadata-ingestion

Usage:
    export AI_SDK_HOST=http://localhost:8585
    export AI_SDK_TOKEN=<your-jwt-token>
    python create_glossaries_and_metrics.py

    # Or pass arguments directly:
    python create_glossaries_and_metrics.py --host http://localhost:8585 --token <jwt>
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from dataclasses import dataclass, field

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
from metadata.generated.schema.entity.services.connections.metadata.openMetadataConnection import (
    AuthProvider,
    OpenMetadataConnection,
)
from metadata.generated.schema.security.client.openMetadataJWTClientConfig import (
    OpenMetadataJWTClientConfig,
)
from metadata.generated.schema.type.basic import (
    EntityName,
    FullyQualifiedEntityName,
    Markdown,
)
from metadata.ingestion.models.custom_pydantic import CustomSecretStr
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
        "name": "JaffleShopBusiness",
        "displayName": "Jaffle Shop Business",
        "description": (
            "Core e-commerce business concepts for the Jaffle Shop, "
            "covering orders, customers, products, payments, and support."
        ),
    },
    {
        "name": "FinancialMetrics",
        "displayName": "Financial Metrics",
        "description": (
            "Revenue, cost, and profitability terminology used across "
            "the Jaffle Shop data warehouse."
        ),
    },
    {
        "name": "MarketingAnalytics",
        "displayName": "Marketing Analytics",
        "description": (
            "Campaign performance, digital advertising, and channel "
            "attribution terminology."
        ),
    },
    {
        "name": "CustomerAnalytics",
        "displayName": "Customer Analytics",
        "description": (
            "Customer segmentation, lifecycle, and product performance "
            "classification concepts."
        ),
    },
    {
        "name": "DataPrivacy",
        "displayName": "Data Privacy",
        "description": (
            "PII classification and data sensitivity terminology for "
            "columns that contain personally identifiable information."
        ),
    },
]

# Each term: (glossary_name, name, display_name, description, parent_name | None, synonyms)
GLOSSARY_TERMS: list[tuple[str, str, str, str, str | None, list[str]]] = [
    # ── JaffleShopBusiness ──────────────────────────────────────────────
    # Top-level
    ("JaffleShopBusiness", "Customer", "Customer",
     "A person registered on the Jaffle Shop platform.",
     None, ["buyer", "shopper"]),
    ("JaffleShopBusiness", "Order", "Order",
     "A purchase transaction placed by a customer.",
     None, ["purchase", "transaction"]),
    ("JaffleShopBusiness", "Product", "Product",
     "An item available for sale (food, beverage, or merchandise).",
     None, ["item", "SKU"]),
    ("JaffleShopBusiness", "Coupon", "Coupon",
     "A discount code applied to an order to reduce the total amount.",
     None, ["promo code", "discount code"]),
    ("JaffleShopBusiness", "Payment", "Payment",
     "A financial transaction used to settle an order.",
     None, []),
    ("JaffleShopBusiness", "Supplier", "Supplier",
     "A vendor that provides raw materials or finished products to the shop.",
     None, ["vendor"]),
    ("JaffleShopBusiness", "SupportTicket", "Support Ticket",
     "A customer service request or complaint raised through the support channel.",
     None, ["case", "issue"]),
    ("JaffleShopBusiness", "ProductReview", "Product Review",
     "Customer feedback and star rating on a purchased product.",
     None, ["review", "feedback"]),
    # Children of Order
    ("JaffleShopBusiness", "CompletedOrder", "Completed Order",
     "An order that has been fulfilled and delivered to the customer.",
     "Order", ["fulfilled order"]),
    ("JaffleShopBusiness", "CancelledOrder", "Cancelled Order",
     "An order that was cancelled before fulfillment.",
     "Order", []),
    ("JaffleShopBusiness", "PendingOrder", "Pending Order",
     "An order awaiting processing or shipment.",
     "Order", []),
    # Children of Product
    ("JaffleShopBusiness", "Jaffle", "Jaffle",
     "A toasted sandwich — the core menu item of the Jaffle Shop.",
     "Product", ["toastie"]),
    # Children of Payment
    ("JaffleShopBusiness", "Refund", "Refund",
     "A full or partial reversal of a payment, issued to the customer.",
     "Payment", ["reimbursement"]),
    # Children of ProductReview
    ("JaffleShopBusiness", "VerifiedPurchase", "Verified Purchase",
     "A review confirmed to come from an actual buyer with a linked order.",
     "ProductReview", []),

    # ── FinancialMetrics ────────────────────────────────────────────────
    ("FinancialMetrics", "GrossRevenue", "Gross Revenue",
     "Total order value before discounts and adjustments.",
     None, ["top-line revenue"]),
    ("FinancialMetrics", "NetRevenue", "Net Revenue",
     "Revenue after subtracting discounts and adding shipping charges.",
     None, ["bottom-line revenue"]),
    ("FinancialMetrics", "AverageOrderValue", "Average Order Value",
     "Mean revenue per order (gross revenue divided by order count).",
     None, ["AOV"]),
    ("FinancialMetrics", "CustomerLifetimeValue", "Customer Lifetime Value",
     "Total revenue generated by a single customer over their entire relationship.",
     None, ["LTV", "CLV"]),
    ("FinancialMetrics", "UnitMargin", "Unit Margin",
     "Difference between a product's selling price and its cost.",
     None, ["profit per unit"]),
    ("FinancialMetrics", "MarginPercent", "Margin Percent",
     "Unit margin expressed as a percentage of unit cost.",
     None, ["margin rate"]),
    ("FinancialMetrics", "DiscountAmount", "Discount Amount",
     "Dollar value of discounts applied to an order.",
     None, []),
    ("FinancialMetrics", "ShippingRevenue", "Shipping Revenue",
     "Revenue collected from shipping charges on orders.",
     None, ["shipping cost"]),

    # ── MarketingAnalytics ──────────────────────────────────────────────
    ("MarketingAnalytics", "Campaign", "Campaign",
     "A coordinated marketing effort with a defined budget, channel, and target audience.",
     None, []),
    ("MarketingAnalytics", "EmailCampaign", "Email Campaign",
     "A campaign delivered via the email channel (e.g., Mailchimp).",
     "Campaign", []),
    ("MarketingAnalytics", "SocialCampaign", "Social Campaign",
     "A campaign on social media platforms such as Facebook, Instagram, or TikTok.",
     "Campaign", []),
    ("MarketingAnalytics", "PaidSearchCampaign", "Paid Search Campaign",
     "A campaign using paid search ads on Google Ads or Bing Ads.",
     "Campaign", ["SEM campaign"]),
    ("MarketingAnalytics", "Impression", "Impression",
     "A single display of an advertisement to a user.",
     None, ["ad view"]),
    ("MarketingAnalytics", "Click", "Click",
     "A user interaction (click) with an advertisement.",
     None, []),
    ("MarketingAnalytics", "Conversion", "Conversion",
     "A desired action completed by a user after interacting with an ad.",
     None, []),
    ("MarketingAnalytics", "ClickThroughRate", "Click-Through Rate",
     "Percentage of impressions that result in clicks (clicks / impressions * 100).",
     None, ["CTR"]),
    ("MarketingAnalytics", "ConversionRate", "Conversion Rate",
     "Percentage of clicks that result in conversions (conversions / clicks * 100).",
     None, ["CVR"]),
    ("MarketingAnalytics", "CostPerAcquisition", "Cost Per Acquisition",
     "Average spend required to acquire one conversion.",
     None, ["CPA"]),
    ("MarketingAnalytics", "CostPerClick", "Cost Per Click",
     "Average spend per individual ad click.",
     None, ["CPC"]),
    ("MarketingAnalytics", "CostPerMille", "Cost Per Mille",
     "Cost per thousand ad impressions.",
     None, ["CPM"]),
    ("MarketingAnalytics", "BudgetUtilization", "Budget Utilization",
     "Percentage of campaign budget that has been spent.",
     None, ["spend rate"]),
    ("MarketingAnalytics", "ReturnOnInvestment", "Return on Investment",
     "Revenue generated relative to marketing spend.",
     None, ["ROI"]),

    # ── CustomerAnalytics ───────────────────────────────────────────────
    # Value segments (mutually exclusive group)
    ("CustomerAnalytics", "ValueSegment", "Value Segment",
     "Customer grouping based on lifetime spend value.",
     None, []),
    ("CustomerAnalytics", "HighValue", "High Value",
     "A customer with lifetime value of $200 or more.",
     "ValueSegment", []),
    ("CustomerAnalytics", "MediumValue", "Medium Value",
     "A customer with lifetime value between $100 and $199.",
     "ValueSegment", []),
    ("CustomerAnalytics", "LowValue", "Low Value",
     "A customer with lifetime value greater than $0 and less than $100.",
     "ValueSegment", []),
    # Customer types (mutually exclusive group)
    ("CustomerAnalytics", "CustomerType", "Customer Type",
     "Customer grouping based on order frequency and engagement.",
     None, ["loyalty tier"]),
    ("CustomerAnalytics", "LoyalCustomer", "Loyal Customer",
     "A customer with 5 or more completed orders.",
     "CustomerType", []),
    ("CustomerAnalytics", "RepeatCustomer", "Repeat Customer",
     "A customer with 2 to 4 completed orders.",
     "CustomerType", ["returning customer"]),
    ("CustomerAnalytics", "NewCustomer", "New Customer",
     "A customer with exactly 1 completed order.",
     "CustomerType", ["first-time buyer"]),
    ("CustomerAnalytics", "Prospect", "Prospect",
     "A registered user who has not placed any orders.",
     "CustomerType", ["lead"]),
    # Sales tiers
    ("CustomerAnalytics", "SalesTier", "Sales Tier",
     "Product grouping based on total units sold.",
     None, []),
    ("CustomerAnalytics", "TopSeller", "Top Seller",
     "A product with 50 or more units sold.",
     "SalesTier", ["best seller"]),
    ("CustomerAnalytics", "SlowMoving", "Slow Moving",
     "A product with fewer than 5 units sold.",
     "SalesTier", []),
    # Rating tiers
    ("CustomerAnalytics", "RatingTier", "Rating Tier",
     "Product grouping based on average customer review rating.",
     None, []),
    ("CustomerAnalytics", "Excellent", "Excellent",
     "Average product rating of 4.5 or above.",
     "RatingTier", []),
    ("CustomerAnalytics", "Poor", "Poor",
     "Average product rating below 3.0.",
     "RatingTier", []),

    # ── DataPrivacy ─────────────────────────────────────────────────────
    ("DataPrivacy", "PII", "PII",
     "Personally Identifiable Information — data that can directly or indirectly identify an individual.",
     None, ["personal data"]),
    ("DataPrivacy", "EmailAddress", "Email Address",
     "An electronic mail address used for communication (e.g., customers.email, payments.billing_email).",
     "PII", ["email"]),
    ("DataPrivacy", "PhoneNumber", "Phone Number",
     "A telephone contact number (e.g., customers.phone_number).",
     "PII", ["mobile", "phone"]),
    ("DataPrivacy", "SSN", "Social Security Number",
     "Social Security Number or its last 4 digits (e.g., customers.ssn_last_four).",
     "PII", ["social security"]),
    ("DataPrivacy", "DateOfBirth", "Date of Birth",
     "The birth date of an individual (e.g., customers.date_of_birth).",
     "PII", ["DOB", "birthday"]),
    ("DataPrivacy", "PhysicalAddress", "Physical Address",
     "Street address, city, state, and postal code (e.g., customers.address_line_1).",
     "PII", ["mailing address"]),
    ("DataPrivacy", "IPAddress", "IP Address",
     "Internet Protocol address identifying a network connection (e.g., payments.ip_address).",
     "PII", ["IP"]),
    ("DataPrivacy", "PaymentCardInfo", "Payment Card Info",
     "Credit/debit card details such as last four digits and card brand (e.g., payments.card_last_four).",
     "PII", ["card info", "PCI data"]),
]


# ---------------------------------------------------------------------------
# Metric definitions
# ---------------------------------------------------------------------------

# (name, display_name, description, metric_type, unit, granularity, sql, related)
METRICS: list[tuple[str, str, str, MetricType, UnitOfMeasurement, MetricGranularity, str, list[str]]] = [
    # ── Revenue ─────────────────────────────────────────────────────────
    (
        "gross_revenue",
        "Gross Revenue",
        "Total order value before discounts for completed orders.",
        MetricType.SUM,
        UnitOfMeasurement.DOLLARS,
        MetricGranularity.DAY,
        "SELECT order_date, SUM(order_total) AS gross_revenue\n"
        "FROM marts_core.fct_orders\n"
        "WHERE order_status = 'completed'\n"
        "GROUP BY order_date",
        [],
    ),
    (
        "net_revenue",
        "Net Revenue",
        "Revenue after discounts and shipping for completed orders.",
        MetricType.SUM,
        UnitOfMeasurement.DOLLARS,
        MetricGranularity.DAY,
        "SELECT order_date, SUM(order_total - discount_amount + shipping_cost) AS net_revenue\n"
        "FROM marts_core.fct_orders\n"
        "WHERE order_status = 'completed'\n"
        "GROUP BY order_date",
        ["gross_revenue"],
    ),
    (
        "total_discounts",
        "Total Discounts",
        "Total dollar value of discounts applied to completed orders.",
        MetricType.SUM,
        UnitOfMeasurement.DOLLARS,
        MetricGranularity.DAY,
        "SELECT order_date, SUM(discount_amount) AS total_discounts\n"
        "FROM marts_core.fct_orders\n"
        "WHERE order_status = 'completed'\n"
        "GROUP BY order_date",
        ["gross_revenue", "net_revenue"],
    ),
    (
        "average_order_value",
        "Average Order Value",
        "Mean order total for completed orders.",
        MetricType.AVERAGE,
        UnitOfMeasurement.DOLLARS,
        MetricGranularity.DAY,
        "SELECT order_date, AVG(order_total) AS average_order_value\n"
        "FROM marts_core.fct_orders\n"
        "WHERE order_status = 'completed'\n"
        "GROUP BY order_date",
        ["gross_revenue"],
    ),
    (
        "shipping_revenue",
        "Shipping Revenue",
        "Total shipping charges collected from completed orders.",
        MetricType.SUM,
        UnitOfMeasurement.DOLLARS,
        MetricGranularity.DAY,
        "SELECT order_date, SUM(shipping_cost) AS shipping_revenue\n"
        "FROM marts_core.fct_orders\n"
        "WHERE order_status = 'completed'\n"
        "GROUP BY order_date",
        ["net_revenue"],
    ),
    (
        "revenue_growth_pct",
        "Revenue Growth %",
        "Month-over-month percentage change in net revenue.",
        MetricType.PERCENTAGE,
        UnitOfMeasurement.PERCENTAGE,
        MetricGranularity.MONTH,
        "SELECT order_month, revenue_growth_pct\n"
        "FROM marts_finance.fct_monthly_revenue",
        ["net_revenue"],
    ),

    # ── Customer ────────────────────────────────────────────────────────
    (
        "customer_lifetime_value",
        "Customer Lifetime Value",
        "Total revenue generated by a single customer over their entire relationship.",
        MetricType.SUM,
        UnitOfMeasurement.DOLLARS,
        MetricGranularity.QUARTER,
        "SELECT customer_id, SUM(order_total) AS ltv\n"
        "FROM marts_core.fct_orders\n"
        "WHERE order_status = 'completed'\n"
        "GROUP BY customer_id",
        ["gross_revenue"],
    ),
    (
        "unique_customers",
        "Unique Customers",
        "Count of distinct customers who placed orders in the period.",
        MetricType.COUNT,
        UnitOfMeasurement.COUNT,
        MetricGranularity.DAY,
        "SELECT order_date, COUNT(DISTINCT customer_id) AS unique_customers\n"
        "FROM marts_core.fct_orders\n"
        "GROUP BY order_date",
        [],
    ),
    (
        "coupon_usage_rate",
        "Coupon Usage Rate",
        "Percentage of orders that used a coupon code.",
        MetricType.PERCENTAGE,
        UnitOfMeasurement.PERCENTAGE,
        MetricGranularity.DAY,
        "SELECT order_date,\n"
        "       COUNT(CASE WHEN used_coupon THEN 1 END)::float / COUNT(*) * 100\n"
        "           AS coupon_usage_rate\n"
        "FROM marts_core.fct_orders\n"
        "GROUP BY order_date",
        [],
    ),
    (
        "customer_retention_rate",
        "Customer Retention Rate",
        "Percentage of customers who have placed more than one order.",
        MetricType.PERCENTAGE,
        UnitOfMeasurement.PERCENTAGE,
        MetricGranularity.MONTH,
        "SELECT COUNT(DISTINCT CASE WHEN total_orders > 1 THEN customer_id END)::float\n"
        "       / NULLIF(COUNT(DISTINCT customer_id), 0) * 100\n"
        "           AS retention_rate\n"
        "FROM marts_core.dim_customers",
        ["unique_customers"],
    ),

    # ── Product ─────────────────────────────────────────────────────────
    (
        "units_sold",
        "Units Sold",
        "Total product units sold in completed orders.",
        MetricType.SUM,
        UnitOfMeasurement.COUNT,
        MetricGranularity.DAY,
        "SELECT order_date, SUM(total_units) AS units_sold\n"
        "FROM marts_core.fct_orders\n"
        "WHERE order_status = 'completed'\n"
        "GROUP BY order_date",
        [],
    ),
    (
        "product_margin_percent",
        "Product Margin %",
        "Product-level margin expressed as a percentage of unit cost.",
        MetricType.PERCENTAGE,
        UnitOfMeasurement.PERCENTAGE,
        MetricGranularity.MONTH,
        "SELECT product_id, product_name,\n"
        "       (unit_price - unit_cost) / NULLIF(unit_cost, 0) * 100\n"
        "           AS margin_percent\n"
        "FROM staging.stg_inventory__products",
        [],
    ),
    (
        "average_product_rating",
        "Average Product Rating",
        "Mean customer review rating for products with at least one review.",
        MetricType.AVERAGE,
        UnitOfMeasurement.OTHER,
        MetricGranularity.MONTH,
        "SELECT product_id, product_name, avg_rating\n"
        "FROM marts_core.dim_products\n"
        "WHERE review_count > 0",
        [],
    ),
    (
        "total_product_margin",
        "Total Product Margin",
        "Aggregate dollar margin across all product sales.",
        MetricType.SUM,
        UnitOfMeasurement.DOLLARS,
        MetricGranularity.MONTH,
        "SELECT SUM(total_margin) AS total_margin\n"
        "FROM marts_core.dim_products",
        ["product_margin_percent", "units_sold"],
    ),

    # ── Marketing ───────────────────────────────────────────────────────
    (
        "click_through_rate",
        "Click-Through Rate",
        "Percentage of ad impressions that result in clicks.",
        MetricType.RATIO,
        UnitOfMeasurement.PERCENTAGE,
        MetricGranularity.DAY,
        "SELECT spend_date,\n"
        "       SUM(clicks)::float / NULLIF(SUM(impressions), 0) * 100 AS ctr\n"
        "FROM staging.stg_marketing__ad_spend\n"
        "GROUP BY spend_date",
        [],
    ),
    (
        "conversion_rate",
        "Conversion Rate",
        "Percentage of ad clicks that result in conversions.",
        MetricType.RATIO,
        UnitOfMeasurement.PERCENTAGE,
        MetricGranularity.DAY,
        "SELECT spend_date,\n"
        "       SUM(conversions)::float / NULLIF(SUM(clicks), 0) * 100\n"
        "           AS conversion_rate\n"
        "FROM staging.stg_marketing__ad_spend\n"
        "GROUP BY spend_date",
        ["click_through_rate"],
    ),
    (
        "cost_per_acquisition",
        "Cost Per Acquisition",
        "Average marketing spend required to acquire one conversion.",
        MetricType.AVERAGE,
        UnitOfMeasurement.DOLLARS,
        MetricGranularity.DAY,
        "SELECT spend_date,\n"
        "       SUM(spend_amount) / NULLIF(SUM(conversions), 0) AS cpa\n"
        "FROM staging.stg_marketing__ad_spend\n"
        "GROUP BY spend_date",
        ["conversion_rate"],
    ),
    (
        "cost_per_click",
        "Cost Per Click",
        "Average marketing spend per ad click.",
        MetricType.AVERAGE,
        UnitOfMeasurement.DOLLARS,
        MetricGranularity.DAY,
        "SELECT spend_date,\n"
        "       SUM(spend_amount) / NULLIF(SUM(clicks), 0) AS cpc\n"
        "FROM staging.stg_marketing__ad_spend\n"
        "GROUP BY spend_date",
        ["click_through_rate"],
    ),
    (
        "campaign_roi",
        "Campaign ROI",
        "Estimated return on investment per campaign (assumes $30 average order value).",
        MetricType.PERCENTAGE,
        UnitOfMeasurement.PERCENTAGE,
        MetricGranularity.MONTH,
        "SELECT campaign_id, campaign_name,\n"
        "       (total_conversions * 30 - total_spend)\n"
        "           / NULLIF(total_spend, 0) * 100 AS roi_pct\n"
        "FROM marts_marketing.fct_campaign_performance",
        ["conversion_rate", "cost_per_acquisition"],
    ),
    (
        "budget_utilization",
        "Budget Utilization",
        "Percentage of total campaign budget that has been spent.",
        MetricType.PERCENTAGE,
        UnitOfMeasurement.PERCENTAGE,
        MetricGranularity.MONTH,
        "SELECT campaign_id, campaign_name, budget_utilization_pct\n"
        "FROM marts_marketing.fct_campaign_performance",
        [],
    ),

    # ── Operations ──────────────────────────────────────────────────────
    (
        "order_count",
        "Order Count",
        "Total number of orders placed.",
        MetricType.COUNT,
        UnitOfMeasurement.COUNT,
        MetricGranularity.DAY,
        "SELECT order_date, COUNT(*) AS order_count\n"
        "FROM marts_core.fct_orders\n"
        "GROUP BY order_date",
        [],
    ),
    (
        "cancellation_rate",
        "Cancellation Rate",
        "Percentage of orders that were cancelled.",
        MetricType.PERCENTAGE,
        UnitOfMeasurement.PERCENTAGE,
        MetricGranularity.MONTH,
        "SELECT order_month,\n"
        "       COUNT(CASE WHEN order_status = 'cancelled' THEN 1 END)::float\n"
        "           / COUNT(*) * 100 AS cancellation_rate\n"
        "FROM marts_core.fct_orders\n"
        "GROUP BY order_month",
        ["order_count"],
    ),
    (
        "refund_rate",
        "Refund Rate",
        "Percentage of payments that resulted in a refund.",
        MetricType.PERCENTAGE,
        UnitOfMeasurement.PERCENTAGE,
        MetricGranularity.MONTH,
        "SELECT COUNT(DISTINCT r.refund_id)::float\n"
        "       / NULLIF(COUNT(DISTINCT p.payment_id), 0) * 100\n"
        "           AS refund_rate\n"
        "FROM staging.stg_stripe__payments p\n"
        "LEFT JOIN staging.stg_stripe__refunds r ON p.payment_id = r.payment_id",
        [],
    ),
    (
        "avg_resolution_hours",
        "Avg Resolution Hours",
        "Average time in hours to resolve customer support tickets.",
        MetricType.AVERAGE,
        UnitOfMeasurement.OTHER,
        MetricGranularity.MONTH,
        "SELECT AVG(resolution_hours) AS avg_resolution_hours\n"
        "FROM staging.stg_support__tickets\n"
        "WHERE resolution_hours IS NOT NULL",
        [],
    ),
    (
        "avg_satisfaction_score",
        "Avg Satisfaction Score",
        "Average customer satisfaction score (1-5) from resolved support tickets.",
        MetricType.AVERAGE,
        UnitOfMeasurement.OTHER,
        MetricGranularity.MONTH,
        "SELECT AVG(satisfaction_score) AS avg_satisfaction_score\n"
        "FROM staging.stg_support__tickets\n"
        "WHERE satisfaction_score IS NOT NULL",
        [],
    ),
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

    @property
    def has_failures(self) -> bool:
        return bool(
            self.glossaries_failed
            or self.terms_failed
            or self.metrics_failed
            or self.metrics_link_failed
        )

    def print_summary(self) -> None:
        total_ok = (
            len(self.glossaries_created)
            + len(self.terms_created)
            + len(self.metrics_created)
        )
        total_fail = (
            len(self.glossaries_failed)
            + len(self.terms_failed)
            + len(self.metrics_failed)
        )

        logger.info("")
        logger.info("=" * 60)
        logger.info("SUMMARY")
        logger.info("=" * 60)
        logger.info(
            "Glossaries     : %d created, %d failed (of %d)",
            len(self.glossaries_created),
            len(self.glossaries_failed),
            len(GLOSSARIES),
        )
        logger.info(
            "Glossary Terms : %d created, %d failed (of %d)",
            len(self.terms_created),
            len(self.terms_failed),
            len(GLOSSARY_TERMS),
        )
        logger.info(
            "Metrics        : %d created, %d failed (of %d)",
            len(self.metrics_created),
            len(self.metrics_failed),
            len(METRICS),
        )
        logger.info(
            "Metric Links   : %d linked, %d failed",
            len(self.metrics_linked),
            len(self.metrics_link_failed),
        )
        logger.info("-" * 60)
        logger.info("Total          : %d succeeded, %d failed", total_ok, total_fail)

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


def create_glossaries(
    metadata: OpenMetadata, result: CreationResult
) -> dict[str, Glossary]:
    """Create all glossaries and return a mapping of name -> entity."""
    glossary_map: dict[str, Glossary] = {}
    for g in GLOSSARIES:
        name = g["name"]
        try:
            entity = metadata.create_or_update(
                data=CreateGlossaryRequest(
                    name=EntityName(name),
                    displayName=g["displayName"],
                    description=Markdown(g["description"]),
                )
            )
        except Exception:
            logger.exception("Failed to create glossary: %s", name)
            result.glossaries_failed.append(name)
            continue
        glossary_map[name] = entity
        result.glossaries_created.append(name)
        logger.info("Created glossary: %s", name)
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
                    "Parent %s not found for term %s — creating without parent",
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

        term_map[fqn_key] = entity
        result.terms_created.append(fqn_key)
        logger.info("Created term: %s", entity.fullyQualifiedName.root)

    return term_map


def create_metrics(
    metadata: OpenMetadata, result: CreationResult
) -> dict[str, Metric]:
    """Create all metric entities.

    Related metrics are linked in a second pass once all metrics exist.
    """
    metric_map: dict[str, Metric] = {}

    # First pass: create metrics without related metrics
    for name, display_name, description, m_type, unit, granularity, sql, _related in METRICS:
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
                )
            )
        except Exception:
            logger.exception("Failed to create metric: %s", name)
            result.metrics_failed.append(name)
            continue

        metric_map[name] = entity
        result.metrics_created.append(name)
        logger.info("Created metric: %s", name)

    # Second pass: link related metrics
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
# Main
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed OpenMetadata with Jaffle Shop glossaries, terms, and metrics."
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

    logger.info("--- Creating Glossaries ---")
    create_glossaries(metadata, result)

    logger.info("--- Creating Glossary Terms ---")
    create_glossary_terms(metadata, result)

    logger.info("--- Creating Metrics ---")
    create_metrics(metadata, result)

    result.print_summary()

    if result.has_failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
