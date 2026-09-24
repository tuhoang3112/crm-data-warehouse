# Proof of Running

Screenshots showing the pipeline runs on schedule, detects failures, can backfill, and passes its tests.
File names are numbered so they read as a story.

| # | File | What it proves | Where to capture it |
|---|---|---|---|
| 01 | `01_airbyte_sync_history.png` | Weekly syncs succeed on schedule | Airbyte → Connection → **Job history** (several Sundays, status *Succeeded*, rows synced, duration) |
| 02 | `02_cloud_scheduler_jobs.png` | VM is switched on/off automatically | Cloud Scheduler → the 2 jobs, *Last run* = Success |
| 03 | `03_dataform_workflow_runs.png` | Transform runs on schedule | BigQuery → Dataform → **Workflow execution logs** (several weekly runs) |
| 04 | `04_data_tests_passed.png` | Data tests pass | A successful run expanded: all `assert_*` / `*_assertions_*` actions green |
| 05 | `05_failed_run.png` | A failure is caught | A failed workflow run (e.g. an assertion or a broken column), with the failing action and error message visible |
| 06 | `06_failure_alert.png` | Someone is notified | The alert email / Slack message from that failure (blur email addresses) |
| 07 | `07_backfill.png` | History can be reloaded | Airbyte stream **refresh/reset** job, or a Dataform run after a logic change, with row counts before/after |
| 08 | `08_dataform_dag.png` | Dependencies are managed | Dataform **compiled graph** (source → staging → mart → assertions) |
| 09 | `09_cost.png` | Cost is known and under budget | Result of `orchestration/sql/cost_monitoring.sql`, or Billing report filtered to BigQuery + Compute Engine |
| 10 | `10_data_latency.png` | Data latency is measured | Result of `orchestration/sql/pipeline_run_history.sql` |
| – | `bigquery-raw-layer.png` | Raw layer exists | Already included |

**Easy way to create #05 + #06 for real:** in a dev workspace, temporarily set `freshness_max_hours: "1"` in `workflow_settings.yaml` and run. `assert_source_freshness` fails and the alert fires. Revert afterwards.

**Before committing any screenshot:** blur people's names, emails, customer/company names, the GCP project ID, and any revenue value.
