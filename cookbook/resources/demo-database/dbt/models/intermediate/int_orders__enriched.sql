-- Enrich orders with customer info and payment details

with orders as (
    select * from {{ ref('stg_jaffle_shop__orders') }}
),

customers as (
    select * from {{ ref('stg_jaffle_shop__customers') }}
),

payments as (
    select
        order_id,
        sum(case when payment_status = 'success' then payment_amount else 0 end) as paid_amount,
        count(*) as payment_attempts,
        max(payment_created_at) as last_payment_at,
        max(case when payment_status = 'success' then payment_method end) as payment_method
    from {{ ref('stg_stripe__payments') }}
    group by order_id
),

order_items_agg as (
    select
        order_id,
        count(*) as item_count,
        sum(quantity) as total_units,
        sum(line_total) as items_subtotal
    from {{ ref('stg_jaffle_shop__order_items') }}
    group by order_id
)

select
    o.order_id,
    o.customer_id,
    c.first_name,
    c.last_name,
    c.email as customer_email,
    c.city as customer_city,
    c.state as customer_state,
    o.order_date,
    o.order_status,
    o.order_total,
    o.shipping_cost,
    o.discount_amount,
    o.coupon_code,
    coalesce(oi.item_count, 0) as item_count,
    coalesce(oi.total_units, 0) as total_units,
    coalesce(oi.items_subtotal, 0) as items_subtotal,
    coalesce(p.paid_amount, 0) as paid_amount,
    coalesce(p.payment_attempts, 0) as payment_attempts,
    p.payment_method,
    p.last_payment_at,
    o.order_total - o.discount_amount + o.shipping_cost as net_order_value,
    case
        when o.coupon_code is not null then true
        else false
    end as used_coupon,
    o.created_at,
    o.updated_at
from orders o
left join customers c on o.customer_id = c.customer_id
left join payments p on o.order_id = p.order_id
left join order_items_agg oi on o.order_id = oi.order_id
