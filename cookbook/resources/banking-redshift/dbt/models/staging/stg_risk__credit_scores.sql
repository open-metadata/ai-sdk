with source as (
    select * from {{ source('raw_risk', 'credit_scores') }}
),
renamed as (
    select
        score_id,
        customer_id,
        upper(score_type) as score_type,
        score_value,
        score_date,
        upper(bureau) as bureau,
        lower(pull_reason) as pull_reason,
        created_at
    from source
)
select * from renamed
