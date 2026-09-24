-- Monthly BigQuery cost for this project (on-demand pricing).
-- Answers: "How much does the warehouse cost per month, and are we over budget?"
-- Change `region-us` to the region of your datasets.
-- Price: on-demand query pricing per TiB for your region (US multi-region: $6.25/TiB);
-- the first 1 TiB queried each month is free.

DECLARE price_per_tib FLOAT64 DEFAULT 6.25;

SELECT
  FORMAT_TIMESTAMP('%Y-%m', creation_time) AS month,
  -- Who/what ran the queries: Dataform service account, Power BI refresh, analysts...
  user_email,
  COUNT(*) AS jobs,
  ROUND(SUM(total_bytes_billed) / POW(1024, 4), 4) AS tib_billed,
  ROUND(SUM(total_bytes_billed) / POW(1024, 4) * price_per_tib, 2) AS est_cost_usd_before_free_tier
FROM `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 180 DAY)
  AND job_type = 'QUERY'
  AND state = 'DONE'
GROUP BY month, user_email
ORDER BY month DESC, tib_billed DESC;

-- Storage footprint per dataset (active + long-term logical bytes)
SELECT
  table_schema AS dataset,
  ROUND(SUM(active_logical_bytes) / POW(1024, 3), 3) AS active_gib,
  ROUND(SUM(long_term_logical_bytes) / POW(1024, 3), 3) AS long_term_gib
FROM `region-us`.INFORMATION_SCHEMA.TABLE_STORAGE
GROUP BY dataset
ORDER BY active_gib DESC;
