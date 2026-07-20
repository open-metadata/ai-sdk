-- Central transaction fact. One row per transaction with foreign keys to the
-- customer, account and branch dimensions, plus an is_orphan flag that
-- surfaces transactions whose account_id cannot be resolved (a DQ scenario).
-- Grain: one row per transaction_id.

with transactions as (
    select * from {{ ref('int_transactions__categorized') }}
),

accounts as (
    select
        account_id,
        customer_id,
        branch_id
    from {{ ref('int_accounts__enriched') }}
)

select
    t.transaction_id,
    t.account_id,
    a.customer_id,
    a.branch_id,
    t.posted_at,
    t.posted_at::date as posted_date,
    t.amount,
    t.currency,
    t.transaction_type,
    t.merchant_id,
    t.description,
    t.is_reversal,
    t.channel,
    t.running_balance,
    t.created_at,
    t.category_name,
    t.category_group,
    t.sign_hint,
    t.merchant_name,
    t.mcc_code,
    t.mcc_description,
    t.merchant_city,
    t.merchant_state,
    t.merchant_country,
    case
        when a.account_id is null then true
        else false
    end as is_orphan
from transactions t
left join accounts a on t.account_id = a.account_id
