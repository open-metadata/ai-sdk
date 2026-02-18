with source as (
    select * from {{ source('marketing', 'ad_spend') }}
),

cleaned as (
    select
        id as ad_spend_id,
        campaign_id,
        spend_date,
        coalesce(impressions, 0) as impressions,
        coalesce(clicks, 0) as clicks,
        coalesce(conversions, 0) as conversions,
        spend_amount,
        platform,
        -- Calculated metrics
        case
            when coalesce(impressions, 0) > 0
            then round(clicks::decimal / impressions * 100, 4)
            else 0
        end as click_through_rate,
        case
            when coalesce(clicks, 0) > 0
            then round(conversions::decimal / clicks * 100, 4)
            else 0
        end as conversion_rate,
        case
            when coalesce(clicks, 0) > 0
            then round(spend_amount / clicks, 2)
            else 0
        end as cost_per_click
    from source
    where id is not null
)

select * from cleaned
