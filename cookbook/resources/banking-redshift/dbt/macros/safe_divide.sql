{% macro safe_divide(numerator, denominator) %}
    case
        when {{ denominator }} = 0 or {{ denominator }} is null then null
        else ({{ numerator }})::float / ({{ denominator }})
    end
{% endmacro %}
