-- Customer dimension with lifetime metrics

with customers as (
    select * from {{ ref('stg_jaffle_shop__customers') }}
),

orders as (
    select * from {{ ref('int_orders__enriched') }}
),

customer_orders as (
    select
        customer_id,
        count(distinct order_id) as total_orders,
        sum(case when order_status = 'completed' then 1 else 0 end) as completed_orders,
        sum(case when order_status = 'cancelled' then 1 else 0 end) as cancelled_orders,
        sum(net_order_value) as lifetime_value,
        avg(net_order_value) as avg_order_value,
        min(order_date) as first_order_date,
        max(order_date) as last_order_date,
        sum(total_units) as total_items_purchased,
        sum(case when used_coupon then 1 else 0 end) as orders_with_coupon
    from orders
    where customer_id is not null
    group by customer_id
),

tickets as (
    select
        customer_id,
        count(*) as total_tickets,
        avg(satisfaction_score) as avg_satisfaction
    from {{ ref('stg_support__tickets') }}
    where customer_id is not null
    group by customer_id
)

select
    c.customer_id,
    c.first_name,
    c.last_name,
    c.first_name || ' ' || c.last_name as full_name,
    c.email,
    c.phone_number,
    c.city,
    c.state,
    c.postal_code,
    c.country,
    c.created_at as customer_created_at,

    -- Order metrics
    coalesce(co.total_orders, 0) as total_orders,
    coalesce(co.completed_orders, 0) as completed_orders,
    coalesce(co.cancelled_orders, 0) as cancelled_orders,
    coalesce(co.lifetime_value, 0) as lifetime_value,
    co.avg_order_value,
    co.first_order_date,
    co.last_order_date,
    coalesce(co.total_items_purchased, 0) as total_items_purchased,
    coalesce(co.orders_with_coupon, 0) as orders_with_coupon,

    -- Derived metrics
    case
        when co.first_order_date is not null
        then co.last_order_date - co.first_order_date
        else null
    end as days_as_customer,
    current_date - coalesce(co.last_order_date, c.created_at::date) as days_since_last_order,

    -- Customer segments
    case
        when coalesce(co.lifetime_value, 0) >= 200 then 'High Value'
        when coalesce(co.lifetime_value, 0) >= 100 then 'Medium Value'
        when coalesce(co.lifetime_value, 0) > 0 then 'Low Value'
        else 'No Purchases'
    end as value_segment,

    case
        when coalesce(co.total_orders, 0) >= 5 then 'Loyal'
        when coalesce(co.total_orders, 0) >= 2 then 'Repeat'
        when coalesce(co.total_orders, 0) = 1 then 'New'
        else 'Prospect'
    end as customer_type,

    -- Support metrics
    coalesce(t.total_tickets, 0) as total_support_tickets,
    t.avg_satisfaction as avg_support_satisfaction

from customers c
left join customer_orders co on c.customer_id = co.customer_id
left join tickets t on c.customer_id = t.customer_id
