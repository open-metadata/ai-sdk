with source as (
    select * from {{ source('jaffle_shop', 'customers') }}
),

cleaned as (
    select
        id as customer_id,
        nullif(trim(first_name), '') as first_name,
        nullif(trim(last_name), '') as last_name,
        case
            when email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
            then lower(email)
            else null
        end as email,
        phone_number,
        case
            when date_of_birth > current_date or date_of_birth < '1900-01-01'
            then null
            else date_of_birth
        end as date_of_birth,
        ssn_last_four,
        nullif(trim(address_line_1), '') as address_line_1,
        nullif(trim(city), '') as city,
        nullif(trim(state), '') as state,
        nullif(trim(postal_code), '') as postal_code,
        coalesce(nullif(trim(country), ''), 'USA') as country,
        created_at,
        updated_at
    from source
    where id is not null
)

select * from cleaned
