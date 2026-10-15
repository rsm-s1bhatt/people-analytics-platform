-- Hiring speed and offer outcomes by department.
with apps as (
    select * from {{ ref('fct_applications') }}
),
offers as (
    select o.*, a.department
    from {{ ref('stg_recruiting__offers') }} o
    join apps a using (application_id)
)
select
    a.department,
    count(*)                                                   as applications,
    count(*) filter (where a.was_hired)                        as hires,
    median(a.days_to_hire)                                     as median_days_to_hire,
    round(avg(a.days_to_hire), 1)                              as avg_days_to_hire,
    (select count(*) from offers o where o.department = a.department)                                as offers_extended,
    round((select avg(case when o.offer_status = 'accepted' then 1.0 else 0 end)
           from offers o where o.department = a.department), 4)                                       as offer_acceptance_rate
from apps a
group by a.department
