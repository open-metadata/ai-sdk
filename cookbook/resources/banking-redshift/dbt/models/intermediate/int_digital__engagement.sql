-- Per-customer digital engagement rollup across web, mobile and login channels.

with web_agg as (
    select
        customer_id,
        count(*) as web_session_count
    from {{ ref('stg_digital__web_sessions') }}
    group by customer_id
),

mobile_agg as (
    select
        customer_id,
        count(*)              as mobile_event_count,
        max(event_timestamp)  as last_mobile_event_at
    from {{ ref('stg_digital__mobile_app_events') }}
    group by customer_id
),

login_agg as (
    select
        customer_id,
        sum(case when success = true  then 1 else 0 end) as login_success_count,
        sum(case when success = false then 1 else 0 end) as login_failure_count,
        max(attempted_at)                                 as last_login_at
    from {{ ref('stg_digital__login_attempts') }}
    group by customer_id
),

all_customers as (
    select customer_id from web_agg
    union
    select customer_id from mobile_agg
    union
    select customer_id from login_agg
)

select
    c.customer_id,
    coalesce(w.web_session_count, 0)   as web_session_count,
    coalesce(m.mobile_event_count, 0)  as mobile_event_count,
    m.last_mobile_event_at,
    coalesce(l.login_success_count, 0) as login_success_count,
    coalesce(l.login_failure_count, 0) as login_failure_count,
    l.last_login_at,
    {{ safe_divide(
        'l.login_success_count',
        'l.login_success_count + l.login_failure_count'
    ) }} as login_success_rate
from all_customers c
left join web_agg w    on c.customer_id = w.customer_id
left join mobile_agg m on c.customer_id = m.customer_id
left join login_agg l  on c.customer_id = l.customer_id
