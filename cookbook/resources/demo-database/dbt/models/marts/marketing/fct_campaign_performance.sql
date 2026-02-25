-- Campaign performance mart

select
    campaign_id,
    campaign_name,
    channel,
    start_date,
    end_date,
    campaign_status,
    budget,
    target_audience,

    -- Activity metrics
    active_days,
    total_impressions,
    total_clicks,
    total_conversions,
    total_spend,
    remaining_budget,
    budget_utilization_pct,

    -- Performance metrics
    overall_ctr,
    overall_conversion_rate,
    cost_per_acquisition,

    -- Calculated metrics
    case
        when total_impressions > 0
        then round(total_spend / (total_impressions / 1000.0), 2)
        else 0
    end as cpm, -- Cost per mille (thousand impressions)

    -- Performance tiers
    case
        when overall_ctr >= 3.0 then 'Excellent'
        when overall_ctr >= 1.5 then 'Good'
        when overall_ctr >= 0.5 then 'Average'
        else 'Poor'
    end as ctr_tier,

    case
        when overall_conversion_rate >= 5.0 then 'Excellent'
        when overall_conversion_rate >= 2.0 then 'Good'
        when overall_conversion_rate >= 1.0 then 'Average'
        else 'Poor'
    end as conversion_tier,

    -- ROI estimate (assuming $30 avg order value)
    case
        when total_spend > 0
        then round((total_conversions * 30 - total_spend) / total_spend * 100, 2)
        else 0
    end as estimated_roi_pct

from {{ ref('int_campaigns__performance') }}
