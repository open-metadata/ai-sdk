{# Returns the number of whole days from start_date to end_date as integer. #}
{% macro days_between(start_date, end_date) %}
  {{ return(adapter.dispatch('days_between')(start_date, end_date)) }}
{% endmacro %}

{% macro default__days_between(start_date, end_date) %}
  ({{ end_date }} - {{ start_date }})
{% endmacro %}

{% macro redshift__days_between(start_date, end_date) %}
  datediff('day', {{ start_date }}, {{ end_date }})
{% endmacro %}

{% macro trino__days_between(start_date, end_date) %}
  date_diff('day', {{ start_date }}, {{ end_date }})
{% endmacro %}

{# BigQuery reverses the operand order relative to Trino and takes the date part
   as a bare keyword rather than a string literal. #}
{% macro bigquery__days_between(start_date, end_date) %}
  date_diff({{ end_date }}, {{ start_date }}, day)
{% endmacro %}
