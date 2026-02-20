with source as (
    select * from {{ source('jaffle_shop', 'order_items') }}
),

cleaned as (
    select
        id as order_item_id,
        order_id,
        product_id,
        quantity,
        unit_price,
        quantity * unit_price as line_total,
        created_at
    from source
    where id is not null
      and order_id is not null
      and quantity > 0
)

select * from cleaned
