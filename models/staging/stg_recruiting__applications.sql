select
    application_id,
    requisition_id,
    candidate_id,
    source as application_source,
    cast(applied_date as date) as applied_date
from {{ source('recruiting', 'applications') }}
