-- Applications that reached a later stage without a record of an earlier one.
-- Points to a gap in the upstream recruiting system (a missed or deleted stage update).
select
    application_id,
    furthest_stage_order,
    case
        when screened_at is null and coalesce(hm_interview_at, values_fit_at, offer_at, hired_at) is not null
            then 'recruiter_screen missing'
        when hm_interview_at is null and coalesce(values_fit_at, offer_at, hired_at) is not null
            then 'hiring_manager_interview missing'
        when values_fit_at is null and coalesce(offer_at, hired_at) is not null
            then 'values_fit_interview missing'
    end as issue
from {{ ref('int_application_stage_dates') }}
where (screened_at is null and coalesce(hm_interview_at, values_fit_at, offer_at, hired_at) is not null)
   or (hm_interview_at is null and coalesce(values_fit_at, offer_at, hired_at) is not null)
   or (values_fit_at is null and coalesce(offer_at, hired_at) is not null)
