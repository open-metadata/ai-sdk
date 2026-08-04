with source as (
    select * from {{ source('raw_marketing', 'customer_segments') }}
),
renamed as (
    select
        upper(segment_code) as segment_code,
        segment_name,
        description
    from source
)
select * from renamed
