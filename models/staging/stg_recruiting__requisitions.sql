select
    requisition_id,
    department,
    job_role,
    level_band,
    cast(opened_date as date) as opened_date
from {{ source('recruiting', 'requisitions') }}
