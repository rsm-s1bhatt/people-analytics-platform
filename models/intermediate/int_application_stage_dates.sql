-- Pivots stage events into one row per application, with the date each stage was reached.
select
    application_id,
    min(case when stage = 'applied'                  then event_date end) as applied_at,
    min(case when stage = 'recruiter_screen'         then event_date end) as screened_at,
    min(case when stage = 'hiring_manager_interview' then event_date end) as hm_interview_at,
    min(case when stage = 'values_fit_interview'     then event_date end) as values_fit_at,
    min(case when stage = 'offer'                    then event_date end) as offer_at,
    min(case when stage = 'hired'                    then event_date end) as hired_at,
    max(stage_order)                                                      as furthest_stage_order
from {{ ref('stg_recruiting__stage_events') }}
group by application_id
