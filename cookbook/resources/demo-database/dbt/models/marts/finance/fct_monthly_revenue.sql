-- Monthly revenue summary with growth metrics

with daily as (
    select * from {{ ref('fct_daily_revenue') }}
),

monthly as (
    select
        order_month,
        sum(total_orders) as total_orders,
        sum(unique_customers) as unique_customers,
        sum(total_units_sold) as total_units_sold,
        sum(gross_revenue) as gross_revenue,
        sum(total_discounts) as total_discounts,
        sum(shipping_revenue) as shipping_revenue,
        sum(net_revenue) as net_revenue,
        round(avg(avg_order_value), 2) as avg_order_value,
        sum(orders_with_coupon) as orders_with_coupon,
        count(distinct order_date) as active_days
    from daily
    group by order_month
)

select
    order_month,
    total_orders,
    unique_customers,
    total_units_sold,
    gross_revenue,
    total_discounts,
    shipping_revenue,
    net_revenue,
    avg_order_value,
    orders_with_coupon,
    active_days,

    -- Growth metrics (vs previous month)
    lag(net_revenue) over (order by order_month) as prev_month_revenue,
    net_revenue - lag(net_revenue) over (order by order_month) as revenue_change,
    case
        when lag(net_revenue) over (order by order_month) > 0
        then round(
            (net_revenue - lag(net_revenue) over (order by order_month))
            / lag(net_revenue) over (order by order_month) * 100,
            2
        )
        else null
    end as revenue_growth_pct,

    lag(total_orders) over (order by order_month) as prev_month_orders,
    total_orders - lag(total_orders) over (order by order_month) as orders_change,
    case
        when lag(total_orders) over (order by order_month) > 0
        then round(
            (total_orders - lag(total_orders) over (order by order_month))::decimal
            / lag(total_orders) over (order by order_month) * 100,
            2
        )
        else null
    end as orders_growth_pct

from monthly
order by order_month
