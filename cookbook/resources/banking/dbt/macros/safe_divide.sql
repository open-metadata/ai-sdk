{# Division that yields NULL instead of erroring when the denominator is 0 or NULL. #}
{% macro safe_divide(numerator, denominator) %}
  {{ return(adapter.dispatch('safe_divide')(numerator, denominator)) }}
{% endmacro %}

{% macro default__safe_divide(numerator, denominator) %}
    case
        when {{ denominator }} = 0 or {{ denominator }} is null then null
        else cast({{ numerator }} as float) / ({{ denominator }})
    end
{% endmacro %}

{# BigQuery has no FLOAT alias for FLOAT64, so the default cast would not
   compile. Its built-in SAFE_DIVIDE already returns NULL for a zero or NULL
   denominator and produces FLOAT64, which is exactly this macro's contract. #}
{% macro bigquery__safe_divide(numerator, denominator) %}
    safe_divide({{ numerator }}, {{ denominator }})
{% endmacro %}
