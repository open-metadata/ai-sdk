-- Monthly profit-and-loss roll-up for the CFO dashboard.
--
-- Components:
--   interest_income      sum of interest_portion from posted loan payments.
--   fee_income           sum of fee transactions (negated so it's positive).
--   interest_expense     synthesized as 0.1% monthly cost-of-funds on positive
--                        deposit balances.
--   non_interest_expense flat $50,000 overhead per month (demo placeholder).
--
-- Grain: period_month.

{{ config(materialized='table') }}

with loan_payments as (
    select
        date_trunc('month', payment_date) as period_month,
        sum(interest_portion) as interest_income
    from {{ ref('stg_lending__loan_payments') }}
    where status = 'posted'
    group by 1
),

fee_transactions as (
    select
        date_trunc('month', posted_at) as period_month,
        sum(-amount) as fee_income
    from {{ ref('stg_transactions__transactions') }}
    where transaction_type = 'fee'
    group by 1
),

deposit_balance as (
    select
        sum(case when balance > 0 then balance else 0 end) as deposit_balance_total
    from {{ ref('int_accounts__enriched') }}
    where product_category in ('deposit', 'savings', 'checking')
),

months as (
    select period_month from loan_payments
    union
    select period_month from fee_transactions
),

combined as (
    select
        m.period_month,
        coalesce(lp.interest_income, 0)                            as interest_income,
        coalesce(ft.fee_income, 0)                                 as fee_income,
        coalesce(d.deposit_balance_total, 0) * 0.001               as interest_expense,
        50000.0                                                    as non_interest_expense
    from months m
    left join loan_payments lp  on m.period_month = lp.period_month
    left join fee_transactions ft on m.period_month = ft.period_month
    cross join deposit_balance d
)

select
    period_month,
    interest_income,
    fee_income,
    interest_expense,
    non_interest_expense,
    interest_income + fee_income - interest_expense - non_interest_expense as net_income
from combined
