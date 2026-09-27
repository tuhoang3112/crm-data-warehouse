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

All scheduling is set up in the tools' own interfaces (no scripts in this repo):

| Step | Tool | Where it is set up |
|---|---|---|
| VM on/off | Cloud Scheduler: 2 HTTP jobs calling the Compute Engine API `.../instances/{instance}/start` and `.../stop`. The scheduler's service account needs the *Compute Instance Admin* role | Cloud Scheduler console |
| Airbyte auto-start on boot | systemd service on the VM that runs `docker compose up -d` after Docker starts | On the VM |
| Extract & load | Airbyte connection schedule | Airbyte UI → Connection → Settings |
| Transform | Dataform: *Release & Scheduling* → release `production` from branch `main` + a scheduled workflow | BigQuery → Dataform |
| BI refresh | Power BI Service scheduled refresh, timed after the Dataform run | Power BI Service |

Order matters: Dataform is scheduled **after** the Airbyte sync window, so the transform reads a fully loaded raw layer.

## Backfill

Based on how the models are built:

| Scenario | How |
|---|---|
| Transformation logic changed | Nothing extra: staging models are views and marts (except `dim_contact`) are full-rebuild tables, so the next run recomputes all history |
| Raw data missing for a period | Airbyte → connection → refresh/reset the affected stream, then run Dataform. Incremental streams (`deal`, `contact`) restart from `start_datetime` in the connector (`2025-06-01`) |
| New custom field needs history | Nothing extra: the raw `form` JSON is kept, so adding the field to the staging pivot fills it for all records |
| `dim_contact` (SCD2, incremental) | ⚠️ A *full refresh* rebuilds it from the current snapshot and **deletes all historical contact versions**. Only do this on purpose |
