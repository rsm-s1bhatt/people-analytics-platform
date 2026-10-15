-- Attrition rate for every combination of department, role, tenure band and overtime.
select
    department,
    job_role,
    tenure_band,
    works_overtime,
    count(*)                                         as headcount,
    count(*) filter (where has_left)                 as leavers,
    round(avg(case when has_left then 1.0 else 0 end), 4) as attrition_rate
from {{ ref('dim_employee') }}
group by 1, 2, 3, 4
