{# Returns the ISO day-of-week as integer: 1 = Monday ... 7 = Sunday. #}
{% macro day_of_week_iso(date_col) %}
  {{ return(adapter.dispatch('day_of_week_iso')(date_col)) }}
{% endmacro %}

{% macro default__day_of_week_iso(date_col) %}
  extract(isodow from {{ date_col }})
{% endmacro %}

{% macro trino__day_of_week_iso(date_col) %}
  day_of_week({{ date_col }})
{% endmacro %}
