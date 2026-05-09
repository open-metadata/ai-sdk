{# Returns a boolean expression: is the given column a syntactically valid email? #}
{% macro valid_email(col) %}
  {{ return(adapter.dispatch('valid_email')(col)) }}
{% endmacro %}

{% macro default__valid_email(col) %}
  {{ col }} ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
{% endmacro %}

{% macro trino__valid_email(col) %}
  regexp_like({{ col }}, '^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$')
{% endmacro %}
