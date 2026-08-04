-- Net Interest Margin per month.
--
-- Demo-grade approximation:
--   interest_income      sum of interest_portion from posted loan payments per month.
--   interest_expense     0.1% × current sum of positive deposit balances (proxy for
--                        cost-of-funds, repeated across months).
--   avg_earning_assets   current deposit balances + current loan balances (constant
--                        snapshot, repeated across months).
--   nim_pct              safe_divide(net_interest_income * 12, avg_earning_assets)
--                        — annualized.
--
-- Grain: period_month.

{{ config(materialized='table') }}

with loan_payments as (
    select
        {{ dbt.date_trunc('month', 'payment_date') }} as period_month,
        sum(interest_portion) as interest_income
    from {{ ref('stg_lending__loan_payments') }}
    where status = 'posted'
    group by 1
),

deposit_balances as (
    select
        sum(case when balance > 0 then balance else 0 end) as deposit_total
    from {{ ref('int_accounts__enriched') }}
    where product_category in ('deposit', 'savings', 'checking')
),

loan_balances as (
    select
        sum(case when balance > 0 then balance else 0 end) as loan_total
    from {{ ref('stg_lending__loans') }}
)

select
    lp.period_month,
    lp.interest_income,
    d.deposit_total * 0.001                                    as interest_expense,
    lp.interest_income - (d.deposit_total * 0.001)             as net_interest_income,
    d.deposit_total + l.loan_total                             as avg_earning_assets,
    {{ safe_divide(
        '(lp.interest_income - (d.deposit_total * 0.001)) * 12',
        'd.deposit_total + l.loan_total'
    ) }} as nim_pct
from loan_payments lp
cross join deposit_balances d
cross join loan_balances l
