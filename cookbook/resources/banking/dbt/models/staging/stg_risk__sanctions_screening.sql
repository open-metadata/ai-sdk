with source as (
    select * from {{ source('raw_risk', 'sanctions_screening') }}
),
renamed as (
    select
        screening_id,
        customer_id,
        screening_date,
        list_name,
        lower(screen_result) as screen_result,
        match_score,
        matched_name,
        lower(disposition) as disposition,
        screened_by_system,
        created_at
    from source
)
select * from renamed
