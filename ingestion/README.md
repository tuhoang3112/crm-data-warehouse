# Ingestion

Three sources land in BigQuery:

| # | Source | Method | Type | Raw tables |
|---|---|---|---|---|
| 1 | **Rework CRM** (REST API) | Custom **Airbyte** connector built with the Low-code Connector Builder ([`airbyte/rework-crm-connector.yaml`](./airbyte/rework-crm-connector.yaml)) | API | `deal`, `deal_activities`, `contact`, `account`, `pipeline`, `stage`, `contact_service`, `account_services` |
| 2 | **Staff list** (internal Google Sheet) | **BigQuery external table** on Google Sheets, the native connector with no extra infrastructure | Built-in connector | `user` |
| 3 | **Class schedule** (Google Sheet filled in by Sales) | **BigQuery external table** on Google Sheets | Built-in connector | `course_schedule` |

Airbyte runs self-hosted (Docker) on a GCP Compute Engine VM that is switched on around the sync (see [`../orchestration/`](../orchestration/)).

---

## 1. Rework CRM connector

### What was hard about this API

| Challenge | How it is handled in the connector |
|---|---|
| Auth via `access_token` + `password` in the **POST body** (not headers) | `request_body_data` on every requester. Values are placeholders in this repo |
| `page` / `limit` pagination | `DefaultPaginator` + `PageIncrement` (page size 1000) |
| Deals can only be listed **per pipeline** | `deal` is a substream of `pipeline` (`SubstreamPartitionRouter`, parent key `id`) |
| Activities can only be fetched **per deal** | `deal_activities` is a substream of `deal` |
| Nested JSON / custom fields stored as a `form` array | Loaded as-is into raw and parsed in Dataform staging (ELT) |

### Stream sync strategy

| Stream | Rows (approx.) | Sync mode | Why |
|---|---|---|---|
| `deal` | ~25.6k | **Incremental** on `last_update` | Largest stream |
| `contact` | ~26.7k | **Incremental** on `last_update` | Large stream |
| `deal_activities` | ~54k activities | Substream of `deal` | Activities can only be fetched per deal |
| `account` | ~30 | Full refresh | Very small |
| `pipeline`, `stage` | 4 / 24 | Full refresh | Reference data, tiny |
| `contact_service`, `account_services` | – | Full refresh | Reference data |

### Duplicate protection

1. **Raw:** the same record can appear more than once (e.g. re-synced after an update).
2. **Staging:** every `stg_*` model keeps only the latest version of each record:
   ```sql
   QUALIFY ROW_NUMBER() OVER (PARTITION BY id ORDER BY _airbyte_extracted_at DESC) = 1
   ```

### Schema change handling

| Change in the CRM | What happens | How it is detected |
|---|---|---|
| **New custom field** | Custom fields live inside the `form` JSON array, so the **raw schema does not change** and nothing breaks. The new field is simply not used until it is mapped in `stg_*` | Not detected automatically: a new field is added to the staging pivot when it is needed |
| New top-level column | Staging selects explicit columns, so the new column is ignored until it is added to the model | Airbyte connection schema settings |
| Column removed or renamed | The staging view errors, so the Dataform run fails and downstream marts are not rebuilt (they keep the last good data) | Failed Dataform run |

**Action when a new field appears:** add one line to the pivot in the matching staging model, e.g.
`MAX(IF(code = 'custom_new_field', final_value, NULL)) AS new_field`.

---

## 2. Staff Google Sheet

The staff list (user ID, name, job title) is maintained by hand in a Google Sheet and connected to BigQuery as an **external table** (`user`). BigQuery reads the sheet live at query time, so there is no sync job to schedule.

- Declared in Dataform as a source ([`declarations/user.sqlx`](../transform/definitions/declarations/user.sqlx)) and modeled into `dim_user` ([model](../transform/definitions/marts/dim_user.sqlx)):

  | Sheet column | `dim_user` column |
  |---|---|
  | `id` | `user_id` |
  | `username` | `username` |
  | `last_name` + `first_name` | `full_name` |
  | `title` | `job_title` |
  | `email` | `email` |

- `fact_deal.owner_user_id` and `fact_deal_activity.activity_owner_user_id` join to `dim_user.user_id`.

---

## 3. Class schedule Google Sheet

The class schedule (class ID, class code, start date, course) is filled in by Sales in a Google Sheet and connected to BigQuery as an **external table** (`course_schedule`). BigQuery reads the sheet live at query time, so there is no sync job to schedule.

- Declared in Dataform as a source ([`declarations/course_schedule.sqlx`](../transform/definitions/declarations/course_schedule.sqlx)) and modeled into `dim_class_schedule` ([model](../transform/definitions/marts/dim_class_schedule.sqlx)):

  | Sheet column | `dim_class_schedule` column |
  |---|---|
  | `ID` | `class_id` |
  | `Name` | `class_code` |
  | `Ngày khai giảng` | `class_start_date` |
  | `Product` | `course` |

- `fact_deal.class_code` joins to `dim_class_schedule.class_code`.

> For both sheets, the Dataform service account needs viewer access to the sheet (share it with the service account's email).
