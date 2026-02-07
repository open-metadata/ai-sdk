-- Fact table for orders

select
    order_id,
    customer_id,
    order_date,
    order_status,

    -- Amounts
    order_total,
    shipping_cost,
    discount_amount,
    net_order_value,
    paid_amount,

    -- Order details
    item_count,
    total_units,
    items_subtotal,
    coupon_code,
    used_coupon,
    payment_method,
    payment_attempts,

    -- Customer context (for quick lookups)
    first_name,
    last_name,
    customer_email,
    customer_city,
    customer_state,

    -- Timestamps
    created_at as order_created_at,
    last_payment_at,

    -- Date dimensions for easy filtering
    date_trunc('week', order_date)::date as order_week,
    date_trunc('month', order_date)::date as order_month,
    date_trunc('quarter', order_date)::date as order_quarter,
    extract(dow from order_date) as day_of_week,
    extract(hour from created_at) as order_hour

from {{ ref('int_orders__enriched') }}
