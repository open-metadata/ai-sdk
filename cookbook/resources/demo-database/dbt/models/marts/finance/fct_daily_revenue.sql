-- Daily revenue aggregation

with orders as (
    select * from {{ ref('fct_orders') }}
    where order_status = 'completed'
)

select
    order_date,
    order_week,
    order_month,
    order_quarter,

    -- Order counts
    count(distinct order_id) as total_orders,
    count(distinct customer_id) as unique_customers,
    sum(total_units) as total_units_sold,

    -- Revenue metrics
    sum(order_total) as gross_revenue,
    sum(discount_amount) as total_discounts,
    sum(shipping_cost) as shipping_revenue,
    sum(net_order_value) as net_revenue,

    -- Averages
    round(avg(net_order_value), 2) as avg_order_value,
    round(avg(item_count), 1) as avg_items_per_order,

    -- Coupon usage
    sum(case when used_coupon then 1 else 0 end) as orders_with_coupon,
    round(
        sum(case when used_coupon then 1 else 0 end)::decimal / count(*) * 100,
        2
    ) as coupon_usage_rate,

    -- Payment methods
    sum(case when payment_method = 'credit_card' then 1 else 0 end) as credit_card_orders,
    sum(case when payment_method = 'paypal' then 1 else 0 end) as paypal_orders,
    sum(case when payment_method = 'apple_pay' then 1 else 0 end) as apple_pay_orders

from orders
group by order_date, order_week, order_month, order_quarter
order by order_date
