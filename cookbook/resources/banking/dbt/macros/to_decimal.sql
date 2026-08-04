{# Cast to a fixed-point number, preserving the source column's scale.

   A bare `cast(x as numeric)` is not portable: Redshift defaults it to
   NUMERIC(18,0) and silently drops every decimal place, while BigQuery
   defaults to NUMERIC(38,9) and keeps them. The two targets would disagree on
   holdings quantities, trade prices and geo coordinates.

   Always pass the precision and scale of the underlying raw column, as
   declared in schema/registry.py. #}
{% macro to_decimal(expression, precision, scale) %}
  {{ return(adapter.dispatch('to_decimal')(expression, precision, scale)) }}
{% endmacro %}

{% macro default__to_decimal(expression, precision, scale) %}
    cast({{ expression }} as numeric({{ precision }}, {{ scale }}))
{% endmacro %}

{# BigQuery's bare NUMERIC is (38,9), which holds every precision/scale this
   project declares without loss. Spelling it out avoids depending on
   parameterised types being accepted inside a CAST. #}
{% macro bigquery__to_decimal(expression, precision, scale) %}
    cast({{ expression }} as numeric)
{% endmacro %}
