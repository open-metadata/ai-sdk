-- Monthly branch KPIs for the CFO dashboard.
--
-- Combines, per (branch, period_month):
--   * new_accounts_opened   — count of accounts opened that month at the branch.
--   * new_loans_originated  — count + total principal of loans originated that
--                             month for customers of the branch (via account.branch_id).
--   * transaction_count     — count of transactions posted at accounts of the branch.
--   * transaction_volume    — sum of |amount| of those transactions.
--
-- Grain: (branch_id, period_month).

{{ config(materialized='table') }}

with branches as (
    select branch_id, branch_name
    from {{ ref('int_branches__performance') }}
),

accounts as (
    select
        account_id,
        branch_id,
        opened_date
    from {{ ref('int_accounts__enriched') }}
),

new_accounts as (
    select
        {{ dbt.date_trunc('month', 'opened_date') }} as period_month,
        branch_id,
        count(*) as new_accounts_opened
    from accounts
    where opened_date is not null
    group by 1, 2
),

new_loans as (
    select
        {{ dbt.date_trunc('month', 'l.origination_date') }} as period_month,
        l.branch_id,
        count(*)        as new_loans_originated,
        sum(l.principal) as new_loan_principal
    from {{ ref('stg_lending__loans') }} l
    where l.origination_date is not null
      and l.branch_id is not null
    group by 1, 2
),

txn_agg as (
    select
        {{ dbt.date_trunc('month', 't.posted_at') }} as period_month,
        a.branch_id,
        count(*)            as transaction_count,
        sum(abs(t.amount))  as transaction_volume
    from {{ ref('stg_transactions__transactions') }} t
    inner join accounts a on t.account_id = a.account_id
    where a.branch_id is not null
    group by 1, 2
),

all_keys as (
    select period_month, branch_id from new_accounts
    union distinct
    select period_month, branch_id from new_loans
    union distinct
    select period_month, branch_id from txn_agg
)

select
    k.period_month,
    k.branch_id,
    b.branch_name,
    coalesce(na.new_accounts_opened, 0)  as new_accounts_opened,
    coalesce(nl.new_loans_originated, 0) as new_loans_originated,
    coalesce(nl.new_loan_principal, 0)   as new_loan_principal,
    coalesce(t.transaction_count, 0)     as transaction_count,
    coalesce(t.transaction_volume, 0)    as transaction_volume
from all_keys k
left join branches b      on k.branch_id    = b.branch_id
left join new_accounts na on k.period_month = na.period_month and k.branch_id = na.branch_id
left join new_loans nl    on k.period_month = nl.period_month and k.branch_id = nl.branch_id
left join txn_agg t       on k.period_month = t.period_month  and k.branch_id = t.branch_id
