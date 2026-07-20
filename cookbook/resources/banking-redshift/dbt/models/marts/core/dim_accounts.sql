-- Account dimension. Wraps int_accounts__enriched with the primary customer's
-- first/last name resolved for convenience in BI tools.
-- Grain: one row per account_id.

with accounts as (
    select * from {{ ref('int_accounts__enriched') }}
),

customers as (
    select
        customer_id,
        first_name,
        last_name
    from {{ ref('int_customers__360') }}
)

select
    a.account_id,
    a.customer_id as primary_customer_id,
    c.first_name  as primary_customer_first_name,
    c.last_name   as primary_customer_last_name,
    a.account_type,
    a.account_type_name,
    a.product_category,
    a.product_code,
    a.opened_date,
    a.closed_date,
    a.status,
    a.balance,
    a.currency,
    a.branch_id,
    a.interest_rate,
    a.credit_limit,
    a.is_joint,
    a.created_at,
    a.updated_at,
    a.holder_count,
    a.customer_ids,
    a.days_open
from accounts a
left join customers c on a.customer_id = c.customer_id
