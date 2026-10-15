{% test is_empty(model) %}
-- Used on data-quality models: any row returned is an upstream problem to raise.
select * from {{ model }}
{% endtest %}
