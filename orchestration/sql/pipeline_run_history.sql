-- Data latency & run history, answering "how stale is the dashboard?"
-- Latest extraction per raw stream vs. now.

SELECT 'deal' AS stream, MAX(_airbyte_extracted_at) AS last_extracted_at FROM `your-project-id.dw_rework_crm.deal`
UNION ALL
SELECT 'deal_activities', MAX(_airbyte_extracted_at) FROM `your-project-id.dw_rework_crm.deal_activities`
UNION ALL
SELECT 'contact', MAX(_airbyte_extracted_at) FROM `your-project-id.dw_rework_crm.contact`
ORDER BY stream;

-- Mart refresh time (last successful Dataform build)
SELECT table_name, TIMESTAMP_MILLIS(last_modified_time) AS last_refreshed_at
FROM `your-project-id.dm_rework_crm.__TABLES__`
ORDER BY table_name;
