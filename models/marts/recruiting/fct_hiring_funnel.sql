-- Stage-by-stage funnel for each department and role: how many reached each stage,
-- and what share converted from the stage before and from the top of the funnel.
with apps as (
    select * from {{ ref('fct_applications') }}
),
stages as (
    select * from (values
        (1, 'applied'), (2, 'recruiter_screen'), (3, 'hiring_manager_interview'),
        (4, 'values_fit_interview'), (5, 'offer'), (6, 'hired')
    ) as t(stage_order, stage)
),
reached as (
    select
        a.department,
        a.job_role,
        s.stage_order,
        s.stage,
        count(*) as candidates_reached
    from apps a
    join stages s on a.furthest_stage_order >= s.stage_order
    group by 1, 2, 3, 4
)
select
    department,
    job_role,
    stage_order,
    stage,
    candidates_reached,
    round(candidates_reached * 1.0
          / lag(candidates_reached) over (partition by department, job_role order by stage_order), 4) as conversion_from_prior_stage,
    round(candidates_reached * 1.0
          / first_value(candidates_reached) over (partition by department, job_role order by stage_order), 4) as conversion_from_applied
from reached
