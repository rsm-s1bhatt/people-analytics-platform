-- The attrition mart must account for every employee in the source, no more and no fewer.
select
    (select sum(headcount) from {{ ref('fct_attrition_by_segment') }}) as mart_headcount,
    (select count(*) from {{ ref('stg_ibm__employees') }})             as source_headcount
where (select sum(headcount) from {{ ref('fct_attrition_by_segment') }})
   != (select count(*) from {{ ref('stg_ibm__employees') }})
