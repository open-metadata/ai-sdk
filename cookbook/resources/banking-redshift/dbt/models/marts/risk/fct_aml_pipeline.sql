-- Monthly AML alert funnel: counts of alerts, triaged, escalated, closed-no-action
-- and SAR-filed outcomes per month. Built from int_aml__alert_context.
-- alert_type_breakdown is a comma-separated "type:count" rollup useful for BI.
-- Grain: one row per period_month.

with alerts as (
    select * from {{ ref('int_aml__alert_context') }}
),

monthly as (
    select
        date_trunc('month', alert_date)::date as period_month,
        count(*)                                                       as alerts_count,
        count(case when triaged_date is not null then 1 end)           as triaged_count,
        count(case when status = 'escalated' then 1 end)               as escalated_count,
        count(case when status = 'closed_no_action' then 1 end)        as closed_no_action_count,
        count(case when status = 'closed_sar_filed' then 1 end)        as sar_filed_count
    from alerts
    where alert_date is not null
    group by date_trunc('month', alert_date)
),

type_counts as (
    select
        date_trunc('month', alert_date)::date as period_month,
        alert_type,
        count(*) as type_count
    from alerts
    where alert_date is not null
    group by date_trunc('month', alert_date), alert_type
),

type_breakdown as (
    select
        period_month,
        listagg(alert_type || ':' || type_count, ', ')
            within group (order by alert_type) as alert_type_breakdown
    from type_counts
    group by period_month
)

select
    m.period_month,
    m.alerts_count,
    m.triaged_count,
    m.escalated_count,
    m.closed_no_action_count,
    m.sar_filed_count,
    {{ safe_divide('m.triaged_count',          'm.alerts_count')   }} as triage_rate,
    {{ safe_divide('m.escalated_count',        'm.triaged_count')  }} as escalation_rate,
    {{ safe_divide('m.sar_filed_count',        'm.escalated_count')}} as sar_filing_rate,
    tb.alert_type_breakdown
from monthly m
left join type_breakdown tb on m.period_month = tb.period_month
