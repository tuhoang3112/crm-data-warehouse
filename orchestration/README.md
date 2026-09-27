# Orchestration

Airbyte runs on a GCP Compute Engine VM. To avoid paying for a VM running 24/7, the VM is only switched on around the sync. The full setup is described step by step in [Schedule pipeline](https://zoedatalens.substack.com/p/schedule-pipeline) (series: *Build Data Systems from Scratch*).

## Flow

```text
Daily, 12:00:
Cloud Scheduler → start VM
systemd         → Airbyte starts automatically on boot
Airbyte         → scheduled sync → BigQuery raw
Cloud Scheduler → stop VM
Dataform        → scheduled "production" release: staging → marts
Power BI        → scheduled dataset refresh, after Dataform finishes
```

| Step | Tool | Config in this repo |
|---|---|---|
| VM on/off | Cloud Scheduler: 2 HTTP jobs calling the Compute Engine `start` / `stop` API. The scheduler's service account needs the *Compute Instance Admin* role | [`cloud-scheduler.sh`](./cloud-scheduler.sh) |
| Airbyte auto-start on boot | systemd service (`docker compose up -d` after Docker starts) | [`airbyte.service`](./airbyte.service) |
| Extract & load | Airbyte connection schedule | set in Airbyte UI → Connection → Settings |
| Transform & test | Dataform: *Release & Scheduling* → release `production` from branch `main` + a scheduled workflow | set in BigQuery → Dataform |
| BI refresh | Power BI Service scheduled refresh, timed after the Dataform run | set in Power BI Service |

Order matters: Dataform is scheduled **after** the Airbyte sync window, so the transform reads a fully loaded raw layer.

## Backfill

Based on how the models are built:

| Scenario | How |
|---|---|
| Transformation logic changed | Nothing extra: staging models are views and marts (except `dim_contact`) are full-rebuild tables, so the next run recomputes all history |
| Raw data missing for a period | Airbyte → connection → refresh/reset the affected stream, then run Dataform. Incremental streams (`deal`, `contact`) restart from `start_datetime` in the connector (`2025-06-01`) |
| New custom field needs history | Nothing extra: the raw `form` JSON is kept, so adding the field to the staging pivot fills it for all records |
| `dim_contact` (SCD2, incremental) | ⚠️ A *full refresh* rebuilds it from the current snapshot and **deletes all historical contact versions**. Only do this on purpose |

## Monitoring queries

- [`sql/cost_monitoring.sql`](./sql/cost_monitoring.sql): monthly bytes billed and estimated query cost per user/service account, plus storage per dataset
- [`sql/pipeline_run_history.sql`](./sql/pipeline_run_history.sql): last extraction per raw stream and last refresh per mart table (data latency)

## To document

- [ ] Exact times of each step (the pipeline starts at 12:00 daily)
- [ ] Alert setup (failed sync / failed run / late data)
- [ ] Access control setup
- [ ] Cost control setup and monthly cost
- [ ] Screenshots in [`docs/proof-of-running/`](../docs/proof-of-running/)
