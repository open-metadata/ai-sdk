-- Campaign attribution: interactions plus downstream account openings.
--
-- For every interaction tied to a campaign, we look for a new account opened
-- by the same customer within 30 days of the interaction_timestamp. Each new
-- account is credited to a single (campaign, interaction) pair; if a customer
-- has multiple interactions within the window we may double-count — see notes
-- below for the simple guard we apply.
--
-- Grain: one row per campaign_id.

{{ config(materialized='table') }}

with campaigns as (
    select * from {{ ref('stg_marketing__campaigns') }}
),

interactions as (
    select *
    from {{ ref('stg_marketing__customer_interactions') }}
    where campaign_id is not null
),

accounts as (
    select
        account_id,
        customer_id,
        opened_date,
        balance
    from {{ ref('stg_core_banking__accounts') }}
    where opened_date is not null
),

-- Attribute each new account to the earliest qualifying interaction
-- (within 30 days) to avoid double-counting across multiple touches.
account_attribution as (
    select
        i.campaign_id,
        a.account_id,
        a.balance,
        row_number() over (
            partition by a.account_id
            order by i.interaction_timestamp
        ) as attribution_rank
    from interactions i
    inner join accounts a
        on i.customer_id = a.customer_id
       and a.opened_date >= cast(i.interaction_timestamp as date)
       and a.opened_date <= dateadd(day, 30, cast(i.interaction_timestamp as date))
),

attributed as (
    select
        campaign_id,
        count(*)        as attributed_account_openings,
        sum(balance)    as attributed_aum
    from account_attribution
    where attribution_rank = 1
    group by campaign_id
),

interaction_agg as (
    select
        campaign_id,
        count(*)                       as interactions_count,
        count(distinct customer_id)    as unique_customers_reached
    from interactions
    group by campaign_id
)

select
    c.campaign_id,
    c.campaign_name,
    c.channel,
    c.objective,
    c.start_date,
    c.end_date,
    c.budget,
    c.target_segment,
    c.status,
    coalesce(ia.interactions_count, 0)            as interactions_count,
    coalesce(ia.unique_customers_reached, 0)      as unique_customers_reached,
    coalesce(att.attributed_account_openings, 0)  as attributed_account_openings,
    coalesce(att.attributed_aum, 0)               as attributed_aum,
    {{ safe_divide('att.attributed_account_openings', 'ia.interactions_count') }} as conversion_rate
from campaigns c
left join interaction_agg ia on c.campaign_id = ia.campaign_id
left join attributed att     on c.campaign_id = att.campaign_id
