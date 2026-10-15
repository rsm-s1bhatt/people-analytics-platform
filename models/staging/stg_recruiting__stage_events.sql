-- Adds the expected order of each stage so later models can spot skips and reversals.
select
    event_id,
    application_id,
    stage,
    cast(event_date as date) as event_date,
    case stage
        when 'applied'                  then 1
        when 'recruiter_screen'         then 2
        when 'hiring_manager_interview' then 3
        when 'values_fit_interview'     then 4
        when 'offer'                    then 5
        when 'hired'                    then 6
    end as stage_order
from {{ source('recruiting', 'stage_events') }}
