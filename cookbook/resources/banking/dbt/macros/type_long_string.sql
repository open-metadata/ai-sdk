{# The string type used for accumulated text, such as the recursive org-chain path.

   dbt's built-in {{ dbt.type_string() }} is not usable here: it renders TEXT on
   Redshift, which is an alias for VARCHAR(256) and silently truncates a deep
   manager chain. #}
{% macro type_long_string() %}
  {{ return(adapter.dispatch('type_long_string')()) }}
{% endmacro %}

{% macro default__type_long_string() %}
    varchar(4096)
{% endmacro %}

{% macro bigquery__type_long_string() %}
    string
{% endmacro %}
