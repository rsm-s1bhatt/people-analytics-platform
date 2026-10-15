-- Employee dimension with tenure and pay bands for slicing attrition.
select
    *,
    case
        when years_at_company < 1  then '0 - <1 yr'
        when years_at_company < 3  then '1 - 2 yrs'
        when years_at_company < 6  then '3 - 5 yrs'
        when years_at_company < 11 then '6 - 10 yrs'
        else '11+ yrs'
    end as tenure_band,
    case
        when monthly_income < 3000  then '< 3k'
        when monthly_income < 6000  then '3k - 6k'
        when monthly_income < 10000 then '6k - 10k'
        else '10k+'
    end as monthly_income_band
from {{ ref('stg_ibm__employees') }}
