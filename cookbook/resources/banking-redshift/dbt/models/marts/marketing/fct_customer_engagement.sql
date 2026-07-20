-- Composite engagement score per customer.
--
-- Combines digital signals (web, mobile, login_success) from
-- int_digital__engagement with in-person/branch interactions from
-- customer_interactions. The weighted score is bucketed into a tier.
--
-- Grain: one row per customer_id (snapshot).

{{ config(materialized='table') }}

with digital as (
    select * from {{ ref('int_digital__engagement') }}
),

interactions_agg as (
    select
        customer_id,
        count(*)                       as interaction_count,
        max(interaction_timestamp)     as last_interaction_at
    from {{ ref('stg_marketing__customer_interactions') }}
    group by customer_id
),

all_customers as (
    select customer_id from digital
    union
    select customer_id from interactions_agg
),

combined as (
    select
        c.customer_id,
        coalesce(d.web_session_count, 0)    as web_session_count,
        coalesce(d.mobile_event_count, 0)   as mobile_event_count,
        coalesce(d.login_success_count, 0)  as login_success_count,
        coalesce(d.login_failure_count, 0)  as login_failure_count,
        coalesce(i.interaction_count, 0)    as interaction_count,
        d.last_mobile_event_at,
        d.last_login_at,
        i.last_interaction_at
    from all_customers c
    left join digital d          on c.customer_id = d.customer_id
    left join interactions_agg i on c.customer_id = i.customer_id
),

scored as (
    select
        *,
        (mobile_event_count   * 0.3)
        + (web_session_count  * 0.2)
        + (login_success_count * 0.1)
        + (interaction_count  * 1.0) as engagement_score
    from combined
)

select
    customer_id,
    web_session_count,
    mobile_event_count,
    login_success_count,
    login_failure_count,
    interaction_count,
    last_mobile_event_at,
    last_login_at,
    last_interaction_at,
    engagement_score,
    case
        when engagement_score >= 100 then 'highly_engaged'
        when engagement_score >= 30  then 'engaged'
        when engagement_score >= 5   then 'occasional'
        else                              'dormant'
    end as engagement_tier
from scored
