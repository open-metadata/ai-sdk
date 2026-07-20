-- AML alerts enriched with customer, account and (when present) flagged transaction context.
-- Account and transaction joins are LEFT JOINs because some alerts reference closed or
-- orphaned entities (a deliberate DQ scenario for the demo).

with alerts as (
    select * from {{ ref('stg_risk__aml_alerts') }}
),

customers as (
    select
        customer_id,
        customer_segment,
        risk_band
    from {{ ref('stg_core_banking__customers') }}
),

accounts as (
    select
        account_id,
        account_type,
        status as account_status
    from {{ ref('stg_core_banking__accounts') }}
),

transactions as (
    select
        transaction_id,
        amount    as flagged_amount,
        posted_at as flagged_posted_at
    from {{ ref('stg_transactions__transactions') }}
)

select
    a.alert_id,
    a.customer_id,
    a.account_id,
    a.transaction_id,
    a.alert_type,
    a.severity,
    a.status,
    a.alert_date,
    a.triaged_date,
    a.closed_date,
    a.assigned_to_employee_id,
    a.narrative,
    a.scenario_code,
    a.created_at,
    c.customer_segment,
    c.risk_band,
    acc.account_type,
    acc.account_status,
    t.flagged_amount,
    t.flagged_posted_at
from alerts a
left join customers c   on a.customer_id    = c.customer_id
left join accounts acc  on a.account_id     = acc.account_id
left join transactions t on a.transaction_id = t.transaction_id
