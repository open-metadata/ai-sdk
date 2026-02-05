with source as (
    select * from {{ source('support', 'tickets') }}
),

cleaned as (
    select
        id as ticket_id,
        customer_id,
        order_id,
        subject,
        description,
        priority,
        status as ticket_status,
        category,
        assigned_to,
        created_at as ticket_created_at,
        resolved_at as ticket_resolved_at,
        satisfaction_score,
        -- Calculated fields
        case
            when resolved_at is not null
            then extract(epoch from (resolved_at - created_at)) / 3600
            else null
        end as resolution_hours
    from source
    where id is not null
)

select * from cleaned
