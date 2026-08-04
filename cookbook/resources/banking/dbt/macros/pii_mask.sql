{# Both masks compile unchanged on Redshift and BigQuery, so neither dispatches.
   right() and || exist on both, and both read '\\1' in a string literal as the
   regex backreference \1. #}
{% macro mask_ssn(column) %}
    case
        when {{ column }} is null then null
        else 'XXX-XX-' || right({{ column }}, 4)
    end
{% endmacro %}

{% macro mask_email(column) %}
    case
        when {{ column }} is null then null
        else regexp_replace({{ column }}, '(.).+(@.+)', '\\1***\\2')
    end
{% endmacro %}
