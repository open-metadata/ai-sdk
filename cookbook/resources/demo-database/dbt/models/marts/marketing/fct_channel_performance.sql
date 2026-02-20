-- Channel-level marketing performance

with campaigns as (
    select * from {{ ref('fct_campaign_performance') }}
)

select
    channel,
    count(distinct campaign_id) as total_campaigns,
    sum(case when campaign_status = 'active' then 1 else 0 end) as active_campaigns,
    sum(case when campaign_status = 'completed' then 1 else 0 end) as completed_campaigns,

    -- Budget
    sum(budget) as total_budget,
    sum(total_spend) as total_spend,
    sum(remaining_budget) as total_remaining,
    round(avg(budget_utilization_pct), 2) as avg_budget_utilization,

    -- Performance
    sum(total_impressions) as total_impressions,
    sum(total_clicks) as total_clicks,
    sum(total_conversions) as total_conversions,

    -- Calculated metrics
    case
        when sum(total_impressions) > 0
        then round(sum(total_clicks)::decimal / sum(total_impressions) * 100, 2)
        else 0
    end as overall_ctr,

    case
        when sum(total_clicks) > 0
        then round(sum(total_conversions)::decimal / sum(total_clicks) * 100, 2)
        else 0
    end as overall_conversion_rate,

    case
        when sum(total_conversions) > 0
        then round(sum(total_spend) / sum(total_conversions), 2)
        else 0
    end as avg_cpa,

    case
        when sum(total_clicks) > 0
        then round(sum(total_spend) / sum(total_clicks), 2)
        else 0
    end as avg_cpc

from campaigns
group by channel
order by total_spend desc
