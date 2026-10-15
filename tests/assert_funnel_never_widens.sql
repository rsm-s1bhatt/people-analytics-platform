-- A funnel can only narrow: no stage may have more candidates than the stage before it.
select *
from {{ ref('fct_hiring_funnel') }}
where conversion_from_prior_stage > 1
