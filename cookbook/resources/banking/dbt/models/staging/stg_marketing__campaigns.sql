with source as (
    select * from {{ source('raw_marketing', 'campaigns') }}
),
renamed as (
    select
        trim(campaign_id)         as campaign_id,
        campaign_name,
        lower(channel)            as channel,
        lower(objective)          as objective,
        cast(start_date as date)          as start_date,
        cast(end_date as date)            as end_date,
        {{ to_decimal('budget', 18, 4) }}           as budget,
        upper(target_segment)     as target_segment,
        trim(owner_employee_id)   as owner_employee_id,
        lower(status)             as status
    from source
)
select * from renamed
