-- Stage events dated earlier than the stage before them for the same application.
with ordered as (
    select
        application_id,
        stage,
        event_date,
        lag(stage)      over (partition by application_id order by stage_order) as prior_stage,
        lag(event_date) over (partition by application_id order by stage_order) as prior_event_date
    from {{ ref('stg_recruiting__stage_events') }}
)
select *
from ordered
where prior_event_date is not null
  and event_date < prior_event_date
