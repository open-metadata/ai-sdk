-- Per-customer KYC status with derived compliance bucket.

with kyc as (
    select * from {{ ref('stg_risk__kyc_checks') }}
),

agg as (
    select
        customer_id,
        max(case when check_type   = 'initial' then check_date end) as initial_kyc_date,
        max(case when check_type   = 'refresh' then check_date end) as last_refresh_date,
        max(case when check_status = 'failed'  then check_date end) as last_failed_date,
        max(check_date) as last_check_date
    from kyc
    group by customer_id
),

last_status as (
    select customer_id, last_check_status
    from (
        select
            customer_id,
            check_status as last_check_status,
            row_number() over (
                partition by customer_id
                order by check_date desc
            ) as rn
        from kyc
    ) ranked
    where rn = 1
)

select
    a.customer_id,
    a.initial_kyc_date,
    a.last_refresh_date,
    a.last_failed_date,
    a.last_check_date,
    s.last_check_status,
    case
        when s.last_check_status = 'failed'                                            then 'failed_open'
        when {{ days_between('a.last_check_date', 'current_date') }} > 365             then 'expired'
        when s.last_check_status = 'passed'                                            then 'compliant'
        else 'pending'
    end as kyc_status
from agg a
left join last_status s on a.customer_id = s.customer_id
