-- One row per data-quality check: how many records it flagged, as a share of all applications.
with total as (select count(*) as n from {{ ref('stg_recruiting__applications') }})
select 'stage_skips' as check_name, count(*) as flagged_records,
       round(count(*) * 1.0 / (select n from total), 4) as share_of_applications
from {{ ref('dq_stage_skips') }}
union all
select 'hires_without_offer', count(*), round(count(*) * 1.0 / (select n from total), 4)
from {{ ref('dq_hires_without_offer') }}
union all
select 'events_out_of_order', count(*), round(count(*) * 1.0 / (select n from total), 4)
from {{ ref('dq_events_out_of_order') }}
