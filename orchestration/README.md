# Orchestration & Monitoring

No Airflow or Composer. The pipeline runs on the schedulers already built into each managed tool. For one weekly batch pipeline run by one person, a dedicated orchestrator would cost more (and need more maintenance) than the whole pipeline.

## Weekly schedule (Sunday, Asia/Bangkok)

```text
11:50  Cloud Scheduler  → start Airbyte VM          (cloud-scheduler.sh)
~11:52 systemd          → Airbyte auto-starts       (airbyte.service)
12:00  Airbyte          → sync Rework CRM → BigQuery raw
12:30  Cloud Scheduler  → stop Airbyte VM
14:00  Dataform         → run "production" release: staging → marts → assertions
       Power BI         → scheduled dataset refresh after Dataform
```

| Step | Tool | Config |
|---|---|---|
| VM on/off | Cloud Scheduler (2 HTTP jobs calling the Compute Engine API) | [`cloud-scheduler.sh`](./cloud-scheduler.sh) |
| Airbyte auto-start on boot | systemd service | [`airbyte.service`](./airbyte.service) |
| Extract & load | Airbyte connection schedule: weekly, Sunday 12:00 | Airbyte UI → Connection → Settings |
| Transform & test | Dataform **release configuration** `production` (branch `main`) + **workflow configuration**: weekly, Sunday 14:00, Asia/Bangkok | BigQuery → Dataform → Release & Scheduling |
| BI refresh | Power BI Service scheduled refresh | Power BI dataset settings |

**Why the gaps:** Dataform starts 1.5 h after the VM stops, so the transform never reads a half-loaded raw table. The cost is up to 2 h of extra latency, which is fine for a weekly management dashboard.

**Why weekly:** the dashboard is used for weekly Sales management reviews. Sales reps work in the CRM itself for real-time needs. The VM runs ~40 min/week (≈2.7 h/month) instead of 24/7.

## Dev → Production

| | Development | Production |
|---|---|---|
| Git branch | feature branch / Dataform workspace | `main` |
| Where it runs | Dataform **workspace** (manual runs) | Dataform **release config** `production` + scheduled workflow |
| Output datasets | Same names + **schema suffix `_dev`** (e.g. `dm_rework_crm_dev`), set in the workspace compilation overrides | `dm_rework_crm`, `dm_rework_crm_view` |
| Who reads it | Only me | Power BI, AI analysis |

Flow: change a model in a workspace → run it and its assertions into `_dev` datasets → commit → merge to `main` → the next scheduled production run picks it up. Production tables are never edited by hand.

## Backfill

| Scenario | How |
|---|---|
| Transformation logic changed (e.g. new lost-reason mapping) | Nothing extra. Every staging model is a view and every mart (except `dim_contact`) is a full-rebuild `table`, so the **whole history is recomputed on every run** |
| Raw data missing for a period (sync failed) | Airbyte → connection → **Refresh / reset** the affected stream(s). Incremental streams re-read from `start_datetime` (2025-06-01). Then run Dataform |
| New custom field needs history | Nothing extra. Raw keeps the full `form` JSON, so adding the field to the staging pivot fills it for all past records |
| `dim_contact` (SCD2, incremental) | ⚠️ **Do not** run it with *full refresh* casually. That rebuilds it from the current snapshot and **deletes all historical contact versions**. Only full-refresh it on purpose, e.g. after changing the SCD2 logic |

## Alerts

| What | How it is detected | Channel |
|---|---|---|
| Airbyte sync fails | Airbyte notification settings → *Failed syncs* | Email / Slack webhook |
| Dataform run fails (SQL error, schema change, **any assertion fails**) | Workflow configuration failure → Cloud Logging → **log-based alert** (filter below) | Email via Cloud Monitoring |
| **Data is late** (sync did not run, VM did not start) | Assertion `assert_source_freshness`: raw data older than `freshness_max_hours` (192 h = 7 days + 1 day buffer) fails the run | Same Dataform alert |
| New CRM custom field | Assertion `assert_new_custom_fields` | Same Dataform alert |
| Cost overrun | GCP **Budget alert** at 50% / 90% / 100% of the monthly budget | Email |

Log-based alert filter for failed Dataform workflow runs:

```text
resource.type="dataform.googleapis.com/Repository"
jsonPayload.@type="type.googleapis.com/google.cloud.dataform.logging.v1.WorkflowInvocationCompletionLogEntry"
jsonPayload.terminalState="FAILED"
```

## Access control

| Principal | Role | Why |
|---|---|---|
| Airbyte service account | `BigQuery Data Editor` on `dw_rework_crm` only + `BigQuery Job User` | Writes raw data, nothing else |
| Dataform service account | `BigQuery Data Editor` on the mart/staging datasets, `Data Viewer` on raw, `Job User`; viewer on the staff Google Sheet | Reads raw, writes models |
| Cloud Scheduler service account | `Compute Instance Admin (v1)` | Starts/stops the VM |
| Power BI / AI analysis account | `BigQuery Data Viewer` on the **mart dataset only**, with sensitive contact columns excluded | Least privilege. Raw and staging (which still hold PII custom fields) are not visible |

## Cost control

- **VM runs ~2.7 h/month** instead of 730 h, which is the biggest saving.
- **BigQuery on-demand**: data is small (tens of MB), so transform + dashboard queries stay inside the 1 TiB/month free tier. Query: [`sql/cost_monitoring.sql`](./sql/cost_monitoring.sql).
- **Budget alert** on the billing account.
- **Custom query quota** (BigQuery → Quotas → *Query usage per day*) caps the damage from a runaway query.

## Setup checklist

Tick each item once it is live, and add the matching screenshot to [`docs/proof-of-running/`](../docs/proof-of-running/).

- [x] Cloud Scheduler start/stop VM jobs
- [x] `airbyte.service` auto-start
- [x] Airbyte weekly sync schedule
- [x] Dataform `production` release + weekly workflow configuration
- [ ] Dataform workspace compilation override: schema suffix `_dev`
- [ ] Airbyte failed-sync notification
- [ ] Cloud Monitoring log-based alert on failed Dataform runs
- [ ] GCP budget alert
- [ ] BigQuery custom query quota
- [ ] Power BI / AI account restricted to the mart dataset

## Monitoring queries

- [`sql/cost_monitoring.sql`](./sql/cost_monitoring.sql): monthly bytes billed and estimated cost per user/service account, plus storage per dataset
- [`sql/pipeline_run_history.sql`](./sql/pipeline_run_history.sql): last extraction per raw stream and last refresh per mart table (data latency)
