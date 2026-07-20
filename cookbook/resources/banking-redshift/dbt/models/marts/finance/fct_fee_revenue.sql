-- Fee revenue by category by month.
--
-- Combines three fee sources:
--   * ATM Fee     — atm_withdrawals.fee_amount (where > 0)
--   * Wire Fee    — wire_transfers.fee_amount  (where > 0)
--   * Account Fee — transactions where transaction_type = 'fee'
--
-- Grain: (period_month, fee_category).

{{ config(materialized='table') }}

with atm_fees as (
    select
        date_trunc('month', withdrawn_at) as period_month,
        'ATM Fee'                         as fee_category,
        fee_amount                        as fee_amount
    from {{ ref('stg_transactions__atm_withdrawals') }}
    where fee_amount > 0
),

wire_fees as (
    select
        date_trunc('month', sent_at) as period_month,
        'Wire Fee'                   as fee_category,
        fee_amount                   as fee_amount
    from {{ ref('stg_transactions__wire_transfers') }}
    where fee_amount > 0
),

account_fees as (
    select
        date_trunc('month', posted_at) as period_month,
        'Account Fee'                  as fee_category,
        -amount                        as fee_amount
    from {{ ref('stg_transactions__transactions') }}
    where transaction_type = 'fee'
),

unioned as (
    select * from atm_fees
    union all
    select * from wire_fees
    union all
    select * from account_fees
)

select
    period_month,
    fee_category,
    count(*)         as fee_transaction_count,
    sum(fee_amount)  as fee_revenue
from unioned
group by 1, 2
