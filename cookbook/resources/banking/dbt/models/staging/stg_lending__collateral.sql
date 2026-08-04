with source as (
    select * from {{ source('raw_lending', 'collateral') }}
),
renamed as (
    select
        collateral_id,
        loan_id,
        lower(collateral_type) as collateral_type,
        description,
        appraised_value,
        appraisal_date,
        ltv_ratio,
        lien_position
    from source
)
select * from renamed
