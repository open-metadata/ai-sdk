with source as (
    select * from {{ source('marketing', 'campaigns') }}
),

cleaned as (
    select
        id as campaign_id,
        name as campaign_name,
        channel,
        start_date,
        end_date,
        budget,
        target_audience,
        status as campaign_status,
        created_by
    from source
    where id is not null
)

select * from cleaned
