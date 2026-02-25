-- Campaign performance aggregated

with campaigns as (
    select * from {{ ref('stg_marketing__campaigns') }}
),

ad_spend as (
    select
        campaign_id,
        min(spend_date) as first_spend_date,
        max(spend_date) as last_spend_date,
        count(distinct spend_date) as active_days,
        sum(impressions) as total_impressions,
        sum(clicks) as total_clicks,
        sum(conversions) as total_conversions,
        sum(spend_amount) as total_spend
    from {{ ref('stg_marketing__ad_spend') }}
    group by campaign_id
)

select
    c.campaign_id,
    c.campaign_name,
    c.channel,
    c.start_date,
    c.end_date,
    c.budget,
    c.target_audience,
    c.campaign_status,
    coalesce(a.active_days, 0) as active_days,
    coalesce(a.total_impressions, 0) as total_impressions,
    coalesce(a.total_clicks, 0) as total_clicks,
    coalesce(a.total_conversions, 0) as total_conversions,
    coalesce(a.total_spend, 0) as total_spend,
    c.budget - coalesce(a.total_spend, 0) as remaining_budget,
    case
        when coalesce(a.total_impressions, 0) > 0
        then round(a.total_clicks::decimal / a.total_impressions * 100, 2)
        else 0
    end as overall_ctr,
    case
        when coalesce(a.total_clicks, 0) > 0
        then round(a.total_conversions::decimal / a.total_clicks * 100, 2)
        else 0
    end as overall_conversion_rate,
    case
        when coalesce(a.total_conversions, 0) > 0
        then round(a.total_spend / a.total_conversions, 2)
        else 0
    end as cost_per_acquisition,
    case
        when c.budget > 0
        then round(coalesce(a.total_spend, 0) / c.budget * 100, 2)
        else 0
    end as budget_utilization_pct
from campaigns c
left join ad_spend a on c.campaign_id = a.campaign_id
