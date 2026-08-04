-- Transactions enriched with category metadata and merchant info (where available).
-- Only PURCHASE-type transactions carry a merchant_id; the merchant join is therefore
-- a left join.

with transactions as (
    select * from {{ ref('stg_transactions__transactions') }}
),

categories as (
    select * from {{ ref('stg_transactions__transaction_categories') }}
),

merchants as (
    select * from {{ ref('stg_cards__merchants') }}
)

select
    t.transaction_id,
    t.account_id,
    t.posted_at,
    t.amount,
    t.currency,
    t.transaction_type,
    t.merchant_id,
    t.description,
    t.is_reversal,
    t.channel,
    t.running_balance,
    t.created_at,
    c.category_name,
    c.category_group,
    c.sign_hint,
    m.merchant_name,
    m.mcc_code,
    m.mcc_description,
    m.city    as merchant_city,
    m.state   as merchant_state,
    m.country as merchant_country
from transactions t
left join categories c on t.transaction_type = c.category_code
left join merchants m  on t.merchant_id      = m.merchant_id
