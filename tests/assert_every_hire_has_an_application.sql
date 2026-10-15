-- Every hired event must belong to an application we know about.
select e.application_id
from {{ ref('stg_recruiting__stage_events') }} e
left join {{ ref('stg_recruiting__applications') }} a using (application_id)
where e.stage = 'hired'
  and a.application_id is null
