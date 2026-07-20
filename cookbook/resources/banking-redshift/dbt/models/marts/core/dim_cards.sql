-- Card dimension. Wraps int_cards__activity with the cardholder's first/last
-- name. The card PAN is already masked upstream (card_number_masked).
-- Grain: one row per card_id.

with cards as (
    select * from {{ ref('int_cards__activity') }}
),

customers as (
    select
        customer_id,
        first_name,
        last_name
    from {{ ref('int_customers__360') }}
)

select
    c.card_id,
    c.customer_id,
    cu.first_name as customer_first_name,
    cu.last_name  as customer_last_name,
    c.card_number_masked,
    c.product_code,
    c.issued_date,
    c.expires_date,
    c.status,
    c.credit_limit,
    c.linked_account_id,
    c.total_auths,
    c.approved_auths,
    c.declined_auths,
    c.last_used_at,
    c.dispute_count,
    c.chargeback_amount_total,
    c.approval_rate
from cards c
left join customers cu on c.customer_id = cu.customer_id
