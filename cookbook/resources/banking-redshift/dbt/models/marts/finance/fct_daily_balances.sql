-- Point-in-time daily balance fact (month-start sampling).
--
-- We don't have a true history of account balances, so we synthesize a snapshot
-- table by cross-joining current account balances with a month-start date spine.
-- The same balance is repeated across every month-start within the window — this
-- is illustrative for the CFO dashboard demo, not a real point-in-time table.
--
-- Grain: (account_id, balance_date) — one row per account per month-start.

{{ config(materialized='table') }}

with date_spine as (
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('" ~ var('start_date') ~ "' as date)",
        end_date="cast('" ~ var('end_date') ~ "' as date)"
    ) }}
),

month_starts as (
    select cast(date_day as date) as balance_date
    from date_spine
    where extract(day from date_day) = 1
),

accounts as (
    select
        account_id,
        account_type,
        account_type_name,
        product_category,
        balance,
        currency,
        branch_id,
        status,
        opened_date,
        closed_date
    from {{ ref('int_accounts__enriched') }}
)

select
    a.account_id,
    m.balance_date,
    a.account_type,
    a.account_type_name,
    a.product_category,
    a.branch_id,
    a.currency,
    a.status,
    a.balance as end_of_day_balance
from accounts a
cross join month_starts m
where a.opened_date <= m.balance_date
  and (a.closed_date is null or a.closed_date >= m.balance_date)
