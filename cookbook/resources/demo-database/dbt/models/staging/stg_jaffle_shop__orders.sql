with source as (
    select * from {{ source('jaffle_shop', 'orders') }}
),

cleaned as (
    select
        id as order_id,
        customer_id,
        order_date,
        status as order_status,
        coalesce(order_total, 0) as order_total,
        coalesce(shipping_cost, 0) as shipping_cost,
        coalesce(discount_amount, 0) as discount_amount,
        round(coalesce(order_total, 0) * 0.08, 2) as tax_amount,
        coalesce(order_total, 0)
            + coalesce(shipping_cost, 0)
            + round(coalesce(order_total, 0) * 0.08, 2)
            - coalesce(discount_amount, 0) as gross_total,
        coupon_code,
        created_at,
        updated_at
    from source
    where id is not null
      and order_date is not null
)

select * from cleaned
