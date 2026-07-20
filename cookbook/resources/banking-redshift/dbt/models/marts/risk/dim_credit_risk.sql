-- Per-customer credit risk profile combining current FICO + VantageScore
-- with customer attributes from int_customers__360. risk_band and pd_estimate
-- are derived from the latest FICO score (defaulting to 650 when missing).
-- Grain: one row per customer_id.

with customers as (
    select * from {{ ref('int_customers__360') }}
),

scores as (
    select * from {{ ref('stg_risk__credit_scores') }}
),

current_fico as (
    select customer_id, fico_score, fico_score_date, fico_bureau
    from (
        select
            customer_id,
            score_value as fico_score,
            score_date  as fico_score_date,
            bureau      as fico_bureau,
            row_number() over (
                partition by customer_id
                order by score_date desc
            ) as rn
        from scores
        where score_type = 'FICO'
    ) ranked
    where rn = 1
),

current_vantage as (
    select customer_id, vantage_score, vantage_score_date, vantage_bureau
    from (
        select
            customer_id,
            score_value as vantage_score,
            score_date  as vantage_score_date,
            bureau      as vantage_bureau,
            row_number() over (
                partition by customer_id
                order by score_date desc
            ) as rn
        from scores
        where score_type = 'VANTAGE'
    ) ranked
    where rn = 1
)

select
    c.customer_id,
    c.first_name,
    c.last_name,
    c.customer_segment,
    c.customer_type,
    c.branch_id,
    c.kyc_status,
    c.risk_band as customer_risk_band,
    f.fico_score,
    f.fico_score_date,
    f.fico_bureau,
    v.vantage_score,
    v.vantage_score_date,
    v.vantage_bureau,
    case
        when coalesce(f.fico_score, 650) < 580 then 'critical'
        when coalesce(f.fico_score, 650) < 670 then 'high'
        when coalesce(f.fico_score, 650) < 740 then 'medium'
        else 'low'
    end as risk_band,
    case
        when coalesce(f.fico_score, 650) < 580 then 0.20
        when coalesce(f.fico_score, 650) < 670 then 0.10
        when coalesce(f.fico_score, 650) < 740 then 0.04
        else 0.01
    end as pd_estimate
from customers c
left join current_fico f    on c.customer_id = f.customer_id
left join current_vantage v on c.customer_id = v.customer_id
