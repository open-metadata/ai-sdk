-- Products enriched with review statistics

with products as (
    select * from {{ ref('stg_inventory__products') }}
),

reviews as (
    select
        product_id,
        count(*) as review_count,
        avg(rating) as avg_rating,
        sum(case when rating >= 4 then 1 else 0 end) as positive_reviews,
        sum(case when rating <= 2 then 1 else 0 end) as negative_reviews,
        sum(helpful_votes) as total_helpful_votes
    from {{ ref('stg_support__reviews') }}
    where is_verified_purchase = true
    group by product_id
),

sales as (
    select
        product_id,
        count(distinct order_id) as times_ordered,
        sum(quantity) as units_sold,
        sum(line_total) as total_revenue
    from {{ ref('stg_jaffle_shop__order_items') }}
    group by product_id
)

select
    p.product_id,
    p.sku,
    p.product_name,
    p.product_description,
    p.category,
    p.subcategory,
    p.unit_cost,
    p.unit_price,
    p.unit_margin,
    p.margin_percent,
    p.is_active,
    coalesce(r.review_count, 0) as review_count,
    r.avg_rating,
    coalesce(r.positive_reviews, 0) as positive_reviews,
    coalesce(r.negative_reviews, 0) as negative_reviews,
    coalesce(r.total_helpful_votes, 0) as total_helpful_votes,
    coalesce(s.times_ordered, 0) as times_ordered,
    coalesce(s.units_sold, 0) as units_sold,
    coalesce(s.total_revenue, 0) as total_revenue,
    coalesce(s.units_sold, 0) * p.unit_margin as total_margin
from products p
left join reviews r on p.product_id = r.product_id
left join sales s on p.product_id = s.product_id
