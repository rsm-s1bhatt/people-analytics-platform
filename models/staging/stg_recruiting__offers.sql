select
    offer_id,
    application_id,
    cast(offer_date as date) as offer_date,
    status as offer_status
from {{ source('recruiting', 'offers') }}
