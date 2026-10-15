-- One row per application: where it came from, how far it got, and how long each step took.
with apps as (
    select * from {{ ref('stg_recruiting__applications') }}
),
stages as (
    select * from {{ ref('int_application_stage_dates') }}
),
reqs as (
    select * from {{ ref('stg_recruiting__requisitions') }}
)
select
    a.application_id,
    a.requisition_id,
    a.candidate_id,
    a.application_source,
    r.department,
    r.job_role,
    r.level_band,
    a.applied_date,
    s.furthest_stage_order,
    case s.furthest_stage_order
        when 1 then 'applied' when 2 then 'recruiter_screen' when 3 then 'hiring_manager_interview'
        when 4 then 'values_fit_interview' when 5 then 'offer' when 6 then 'hired'
    end                                                  as furthest_stage,
    s.hired_at is not null                               as was_hired,
    datediff('day', a.applied_date, s.screened_at)       as days_to_screen,
    datediff('day', a.applied_date, s.offer_at)          as days_to_offer,
    datediff('day', a.applied_date, s.hired_at)          as days_to_hire
from apps a
left join stages s using (application_id)
left join reqs r using (requisition_id)
