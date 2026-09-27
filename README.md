# CRM Data System: From Scattered CRM Data to a Trusted Sales Dashboard

> An end-to-end data system (**Airbyte → BigQuery → Dataform → Power BI**) built on real company data after a CRM migration (Pipedrive → Rework CRM). It covers API ingestion, historical reconciliation, dimensional modeling, data tests, and one shared set of metric definitions.

![Architecture](docs/architecture.png)

---

## The problem

The company migrated its CRM from **Pipedrive to Rework CRM**. After that:

- The old reports still read from the Pipedrive database, which was no longer used, so **they stopped reflecting reality**.
- New reports built on Rework showed **wrong dates**: when historical data was imported into Rework, each record's real creation time was replaced with the **import time**.
- Getting a number meant **combining data by hand**.

**Goal:** one system that brings CRM data into one place, cleans it, keeps it up to date, and defines every metric once, while **preserving Pipedrive history**.

---

## Business questions

| # | Question | Answer |
|---|---|---|
| 1 | **Where do the enrolment/revenue numbers come from, and why did sources disagree?** | Now one source: Rework CRM API → `fact_deal`. Numbers disagreed because **(a)** the old reports still read from the retired Pipedrive database, and **(b)** reports on Rework used the **import time** as the creation date for all migrated records. The original Pipedrive dates survive in Rework custom fields, so the model restores them: `COALESCE(pipedrive_created_at, rework_created_at)`. Separately, some tracking values on real deals were recorded inconsistently at the source (e.g. `fanpage` vs `fanpage_tm`); these are merged under the rules in [metric-definitions.md](docs/metric-definitions.md) |
| 2 | **How far behind reality is the dashboard?** | The pipeline runs **daily at 12:00**; exact latency is *not yet measured*. The query is ready ([`pipeline_run_history.sql`](orchestration/sql/pipeline_run_history.sql)), and `assert_source_freshness` fails the Dataform run when raw data is older than a set threshold |
| 3 | **When a dashboard number is wrong, how long does it take to trace it to the source?** | *Not yet measured.* The trace path exists: every metric lists its source tables ([metric-definitions](docs/metric-definitions.md)), Dataform's `ref()` graph links mart → staging → raw, and each raw row keeps `_airbyte_extracted_at` |
| 4 | **What does the warehouse cost per month, and is it over budget?** | *Not yet measured.* Query ready: [`cost_monitoring.sql`](orchestration/sql/cost_monitoring.sql) |
| 5 | **When the source changes structure, does the pipeline break, and how fast do we know?** | CRM custom fields are stored inside a JSON array (`form`), so a **new CRM field does not change the raw table schema** and does not break the pipeline. It is only picked up once it is added to the staging pivot. `assert_new_custom_fields` is written to flag new fields on the next run. Details: [ingestion/README](ingestion/README.md#schema-change-handling) |

---

## Architecture decisions

| Decision | Choice | Why |
|---|---|---|
| **Warehouse** | **BigQuery** | Already used by the company. The staff Google Sheet connects natively as an external table, and Dataform runs inside BigQuery |
| **ETL or ELT** | **ELT** | Raw CRM data (including nested JSON custom fields) is loaded as-is, and all transformation is done in SQL with Dataform. Because staging models are views and marts are rebuilt in full, a logic change is re-applied to all history without re-extracting |
| **Data Lake** | **Not needed** | All sources are structured tables. There are no files or unstructured data to store |
| **Data Mart** | **Yes** | Power BI reads clean fact and dimension tables instead of raw API data |
| **Schema** | Fact + dimension tables, with one snowflaked branch `dim_stage → dim_pipeline` | Each stage belongs to one pipeline, as in the CRM |
| **Ingestion tool** | **Airbyte (self-hosted)**, custom low-code connector | Built in the Airbyte Connector Builder to handle the Rework API's auth, pagination and parent-child endpoints |
| **Transformation** | **Dataform** | SQLX + Git, dependency graph via `ref()`, assertions (tests) and scheduling inside BigQuery |

---

## Sources & ingestion

| Source | Method |
|---|---|
| **Rework CRM API**: deals, activities, contacts, accounts, pipelines, stages, services (8 streams) | Custom Airbyte connector ([YAML](ingestion/airbyte/rework-crm-connector.yaml)). `deal` and `contact` sync incrementally on `last_update`; the other streams are full refresh |
| **Staff Google Sheet** | BigQuery external table |
| **Class schedule** (Google Sheet, filled in by Sales) | BigQuery external table → `dim_class_schedule`: class code, class start date, course. *Declaration not yet in this repo* |

Duplicates: each staging model keeps only the latest version per ID (`QUALIFY ROW_NUMBER()`), and `uniqueKey` assertions check every mart table.
→ [ingestion/README](ingestion/README.md)

---

## Data model

![Data model](docs/data-model.png)

| Table | Grain | Notes |
|---|---|---|
| `fact_deal` | 1 row per deal | Status, stage, owner, **deal value (revenue)**, course, attribution (UTM), Pipedrive-reconciled dates, `is_test_deal` |
| `fact_deal_activity` | 1 row per activity | Notes, calls, emails, changelog |
| `dim_contact` | 1 row per contact **version** | **SCD Type 2** on `job_title`, `location`. Deals join the version valid at deal creation |
| `dim_account`, `dim_user`, `dim_pipeline`, `dim_stage` | 1 row per entity | `dim_user` comes from the staff Google Sheet |
| `dim_class_schedule` | 1 row per class | Class code, start date, course, from the class-schedule Google Sheet |

→ [Data Dictionary](docs/data-dictionary.md) (columns) · [Metric Definitions](docs/metric-definitions.md) (metrics)

---

## Transformation & data quality

Dataform builds **6 staging views → 7 mart tables** (`dim_class_schedule` is not yet in this repo). **22 assertions** are defined:

- **Uniqueness / not-null** on every mart key
- **Referential integrity**: deal → stage, deal → contact version, activity → deal, stage → pipeline
- **Validity**: `deal_status ∈ {open, won, lost}`, `deal_value ≥ 0`, SCD2 date logic
- **SCD2**: exactly one current version per contact, no overlaps
- **Freshness**: raw data not older than a set threshold
- **Schema change**: new CRM custom fields

Before the dashboard was built, a [Data Quality Review](docs/data-quality-review.pdf) was run on the mart. For example, it found a 99.97% orphan rate on `dim_contact.account_id`. Part of this is the business rule `account_id = 0` = contact without a company; the remaining orphans are still being investigated. The dashboard was also [reconciled](docs/testing-validation.md) against the previous Pipedrive-based dashboard and against Rework CRM.
→ [transform/README](transform/README.md)

---

## Orchestration

Runs **daily at 12:00**: VM start → Airbyte sync → VM stop → Dataform production run → **Power BI scheduled refresh** (after Dataform finishes).
→ [orchestration/README](orchestration/README.md)

---

## Case study in numbers

| | |
|---|---|
| Sources | **3** (Rework CRM API with 8 streams, staff Google Sheet, class-schedule Google Sheet) |
| Tables | **10** raw (8 Airbyte + 2 Google Sheets) → **6** staging views → **8** mart tables |
| Volume | ~**25.6k** deals · ~**54k** activities · ~**26.7k** contacts (history since 2021, incl. migrated Pipedrive data) |
| Data tests | **22** assertions defined |
| Refresh frequency | **Daily at 12:00** (Airbyte → Dataform → Power BI) |
| Data latency | *to be measured* |
| Monthly cost | *to be measured* |

---

## Planned / in progress

- [ ] Add the `dim_class_schedule` source and model to `transform/`
- [ ] **AI report automation (next phase):** weekly/monthly reports are still built by hand (pull numbers, paste into sheets/slides, write commentary on changes), so they take time, are often late, and anomalies are only caught when someone happens to notice. Next step: generate them automatically from this warehouse, using [metric-definitions.md](docs/metric-definitions.md) as the AI's context
- [ ] Run the 22 assertions on production data and record results
- [ ] Measure data latency and monthly cost (queries in [`orchestration/sql/`](orchestration/sql/))
- [ ] Document the exact schedule times, alert and access setup, with screenshots in [`docs/proof-of-running/`](docs/proof-of-running/)
- [ ] Apply the connector improvements listed in [ingestion/README](ingestion/README.md#recommended-improvements-not-yet-applied-test-in-connector-builder-first)

---

## Reproduce from scratch

1. **GCP:** create datasets `dw_rework_crm` (raw), `dm_rework_crm_view` (staging), `dm_rework_crm` (mart).
2. **Airbyte:** import [`rework-crm-connector.yaml`](ingestion/airbyte/rework-crm-connector.yaml) in the Connector Builder, add credentials, and create a BigQuery connection ([details](ingestion/README.md#reproduce)).
3. **Staff sheet:** create the external table `dw_rework_crm.user` from the Google Sheet.
4. **Dataform:** set `defaultProject` in `transform/workflow_settings.yaml`, then `dataform compile` → `dataform run` ([details](transform/README.md#run-it)).
5. **Power BI:** connect to the `dm_rework_crm` dataset and apply the definitions in [metric-definitions.md](docs/metric-definitions.md).

---

## Repository structure

```text
crm-data-warehouse/
├── ingestion/                  # Airbyte connector (Rework API) + Google Sheet source
├── transform/                  # Dataform: staging, marts, assertions, monitoring
├── orchestration/              # scheduling configs, cost & latency SQL
├── dashboard/                  # Power BI screenshots
├── demo/                       # fake-data generator for a shareable Power BI demo
└── docs/
    ├── architecture.png        # data flow source → BI
    ├── data-model.png          # ERD
    ├── metric-definitions.md   # metric formulas, sources, users, pitfalls
    ├── data-dictionary.md      # column definitions
    ├── data-quality-review.pdf
    ├── testing-validation.md   # dashboard reconciliation
    ├── project-requirements.md
    └── proof-of-running/       # screenshots of runs, tests, alerts
```

## Data privacy

Based on real company data. This repository contains **code, configuration and documentation only**: no customer records, no credentials (connector values are placeholders), no GCP project ID, and no revenue values. Contact email and phone are not included in the schema that AI-assisted analysis is allowed to query.
