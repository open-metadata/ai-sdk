{# Returns the number of fractional hours from start_ts to end_ts as a numeric. #}
{% macro hours_between(start_ts, end_ts) %}
  {{ return(adapter.dispatch('hours_between')(start_ts, end_ts)) }}
{% endmacro %}

{% macro default__hours_between(start_ts, end_ts) %}
  extract(epoch from ({{ end_ts }} - {{ start_ts }})) / 3600
{% endmacro %}

{% macro trino__hours_between(start_ts, end_ts) %}
  date_diff('second', {{ start_ts }}, {{ end_ts }}) / 3600.0
{% endmacro %}
