with source as (
    select * from {{ source('support', 'reviews') }}
),

cleaned as (
    select
        id as review_id,
        product_id,
        customer_id,
        order_id,
        rating,
        title as review_title,
        review_text,
        is_verified_purchase,
        coalesce(helpful_votes, 0) as helpful_votes,
        created_at as review_created_at
    from source
    where id is not null
      and rating between 1 and 5
)

select * from cleaned
