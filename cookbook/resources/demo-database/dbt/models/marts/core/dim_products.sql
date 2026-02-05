-- Product dimension with performance metrics

select
    product_id,
    sku,
    product_name,
    product_description,
    category,
    subcategory,
    unit_cost,
    unit_price,
    unit_margin,
    margin_percent,
    is_active,

    -- Review metrics
    review_count,
    round(avg_rating::decimal, 2) as avg_rating,
    positive_reviews,
    negative_reviews,
    total_helpful_votes,

    -- Sales metrics
    times_ordered,
    units_sold,
    total_revenue,
    total_margin,

    -- Derived metrics
    case
        when review_count > 0
        then round(positive_reviews::decimal / review_count * 100, 2)
        else null
    end as positive_review_pct,

    case
        when units_sold > 0
        then round(total_revenue / units_sold, 2)
        else null
    end as avg_selling_price,

    -- Product tier
    case
        when units_sold >= 50 then 'Top Seller'
        when units_sold >= 20 then 'Popular'
        when units_sold >= 5 then 'Moderate'
        when units_sold > 0 then 'Slow Moving'
        else 'No Sales'
    end as sales_tier,

    case
        when avg_rating >= 4.5 then 'Excellent'
        when avg_rating >= 4.0 then 'Good'
        when avg_rating >= 3.0 then 'Average'
        when avg_rating is not null then 'Poor'
        else 'Unrated'
    end as rating_tier

from {{ ref('int_products__with_reviews') }}
