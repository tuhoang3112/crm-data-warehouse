# Proof of Running

Screenshots showing the pipeline runs on schedule, surfaces failures, and can backfill.
File names are numbered so they read as a story.

| # | File | What it proves | Where to capture it |
|---|---|---|---|
| 01 | `01_airbyte_sync_history.png` | Scheduled syncs succeed | Airbyte → Connection → **Job history** (several runs, status *Succeeded*, rows synced, duration) |
| 02 | `02_cloud_scheduler_jobs.png` | VM is switched on/off automatically | Cloud Scheduler → the 2 jobs, *Last run* = Success |
| 03 | `03_dataform_workflow_runs.png` | Transform runs on schedule | BigQuery → Dataform → **Workflow execution logs** (several scheduled runs) |
| 04 | `04_failed_run.png` | A failure is caught | A failed workflow run (e.g. a broken column), with the failing action and error message visible |
| 05 | `05_failure_alert.png` | Someone is notified | The alert received for that failure (blur email addresses) |
| 06 | `06_backfill.png` | History can be reloaded | Airbyte stream **refresh/reset** job, or a Dataform run after a logic change, with row counts before/after |
| 07 | `07_dataform_dag.png` | Dependencies are managed | Dataform **compiled graph** (source → staging → mart) |
| 08 | `08_cost.png` | Cost is known | Billing report filtered to BigQuery + Compute Engine |
| 09 | `09_data_latency.png` | Data latency is measured | Last Airbyte sync time vs. last Dataform run time |
| – | `bigquery-raw-layer.png` | Raw layer exists | Already included |

**Before committing any screenshot:** blur people's names, emails, customer/company names, the GCP project ID, and any revenue value.
