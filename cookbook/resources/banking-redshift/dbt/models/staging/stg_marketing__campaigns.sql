with source as (
    select * from {{ source('raw_marketing', 'campaigns') }}
),
renamed as (
    select
        trim(campaign_id)         as campaign_id,
        campaign_name,
        lower(channel)            as channel,
        lower(objective)          as objective,
        start_date::date          as start_date,
        end_date::date            as end_date,
        budget::numeric           as budget,
        upper(target_segment)     as target_segment,
        trim(owner_employee_id)   as owner_employee_id,
        lower(status)             as status
    from source
)
select * from renamed
