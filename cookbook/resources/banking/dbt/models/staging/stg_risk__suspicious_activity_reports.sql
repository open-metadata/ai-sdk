with source as (
    select * from {{ source('raw_risk', 'suspicious_activity_reports') }}
),
renamed as (
    select
        sar_id,
        alert_id,
        customer_id,
        filing_date,
        filing_institution,
        regulator,
        filing_reference,
        lower(suspicious_activity_type) as suspicious_activity_type,
        total_amount_involved,
        narrative,
        filed_by_employee_id,
        lower(status) as status,
        created_at
    from source
)
select * from renamed
