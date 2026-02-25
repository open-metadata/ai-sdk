with source as (
    select * from {{ source('inventory', 'products') }}
),

cleaned as (
    select
        id as product_id,
        sku,
        name as product_name,
        description as product_description,
        category,
        subcategory,
        unit_cost,
        unit_price,
        unit_price - unit_cost as unit_margin,
        case
            when unit_cost > 0 then round((unit_price - unit_cost) / unit_cost * 100, 2)
            else 0
        end as margin_percent,
        weight_kg,
        is_active,
        created_at,
        updated_at
    from source
    where id is not null
)

select * from cleaned
