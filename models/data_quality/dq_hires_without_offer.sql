-- Hires with no offer record: the offer was never logged, or was logged in another system.
select s.application_id, s.hired_at
from {{ ref('int_application_stage_dates') }} s
left join {{ ref('stg_recruiting__offers') }} o using (application_id)
where s.hired_at is not null
  and o.offer_id is null
