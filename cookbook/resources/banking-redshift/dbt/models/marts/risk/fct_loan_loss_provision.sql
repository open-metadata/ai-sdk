-- Expected Credit Loss (ECL) per loan computed as PD * LGD * EAD.
-- PD is bucketed from the latest FICO score (defaulting to 650 when missing).
-- LGD is product-class specific. EAD is the current loan balance.
-- Grain: one row per loan_id.

with l as (
    select * from {{ ref('int_loans__delinquency') }}
),

credit as (
    select customer_id, fico_score
    from (
        select
            customer_id,
            score_value as fico_score,
            row_number() over (
                partition by customer_id
                order by score_date desc
            ) as rn
        from {{ ref('stg_risk__credit_scores') }}
        where score_type = 'FICO'
    ) ranked
    where rn = 1
)

select
    l.loan_id,
    l.customer_id,
    l.product_code,
    l.balance,
    coalesce(credit.fico_score, 650) as fico_score,
    case
        when coalesce(credit.fico_score, 650) < 580 then 0.20
        when coalesce(credit.fico_score, 650) < 670 then 0.10
        when coalesce(credit.fico_score, 650) < 740 then 0.04
        else 0.01
    end as pd_estimate,
    case l.product_code
        when 'MORTGAGE_30Y'  then 0.30
        when 'MORTGAGE_15Y'  then 0.25
        when 'AUTO_LOAN'     then 0.45
        when 'HELOC'         then 0.55
        when 'BUSINESS_LOAN' then 0.60
        else 0.70
    end as lgd_estimate,
    l.balance as ead,
    l.balance *
        (case
            when coalesce(credit.fico_score, 650) < 580 then 0.20
            when coalesce(credit.fico_score, 650) < 670 then 0.10
            when coalesce(credit.fico_score, 650) < 740 then 0.04
            else 0.01
        end) *
        (case l.product_code
            when 'MORTGAGE_30Y'  then 0.30
            when 'MORTGAGE_15Y'  then 0.25
            when 'AUTO_LOAN'     then 0.45
            when 'HELOC'         then 0.55
            when 'BUSINESS_LOAN' then 0.60
            else 0.70
        end) as expected_credit_loss,
    l.delinquency_bucket
from l
left join credit on l.customer_id = credit.customer_id
