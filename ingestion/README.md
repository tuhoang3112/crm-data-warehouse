# Ingestion

Two sources land in the BigQuery raw dataset `dw_rework_crm`:

| # | Source | Method | Type | Raw tables |
|---|---|---|---|---|
| 1 | **Rework CRM** (REST API) | Custom **Airbyte** connector built with the Low-code Connector Builder ([`airbyte/rework-crm-connector.yaml`](./airbyte/rework-crm-connector.yaml)) | API | `deal`, `deal_activities`, `contact`, `account`, `pipeline`, `stage`, `contact_service`, `account_services` |
| 2 | **Staff list** (internal Google Sheet) | **BigQuery external table** on Google Sheets, the native connector with no extra infrastructure | Built-in connector | `user` |

Airbyte runs self-hosted (Docker) on a small GCP Compute Engine VM that is only switched on during the sync window (see [`../orchestration/`](../orchestration/)).

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
| `deal` | ~25.6k | **Incremental** on `last_update` | Largest, changes daily |
| `contact` | ~26.7k | **Incremental** on `last_update` | Large, changes rarely |
| `deal_activities` | ~54k activities | Substream of `deal` | See recommendation below |
| `account` | ~30 | Full refresh | Tiny, so incremental adds complexity for no gain |
| `pipeline`, `stage` | 4 / 24 | Full refresh | Reference data, tiny |
| `contact_service`, `account_services` | small | Full refresh | Reference data |

### Duplicate protection (two layers)

1. **Raw:** incremental syncs append new versions of changed records, so the raw layer keeps history. Duplicates at this layer are expected.
2. **Staging:** every `stg_*` model keeps only the latest version of each record:
   ```sql
   QUALIFY ROW_NUMBER() OVER (PARTITION BY id ORDER BY _airbyte_extracted_at DESC) = 1
   ```
3. **Test:** `uniqueKey` assertions on every mart table fail the run if a duplicate ever gets through.

### Recommended improvements (not yet applied, test in Connector Builder first)

These are written as recommendations rather than edits to the YAML, because the YAML in this repo must stay identical to what runs in production.

1. **Make `deal_activities` truly incremental.** It is a substream of `deal`. By default, a low-code parent stream is read in **full** to build the partitions, which means one API call per deal (~25k calls) on every sync. Add this to its `ParentStreamConfig`:
   ```yaml
   incremental_dependency: true
   ```
   After that, activities are only fetched for deals whose `last_update` moved since the last sync. First check in Rework that adding a note/call/changelog updates the deal's `last_update`. This matters for the schedule too: the VM only stays up for about 30 minutes after the sync starts.
2. **Declare `primary_key: id`** on `deal`, `contact`, `account`, `pipeline` and `stage`. Airbyte can then use *Incremental | Append + Deduped*, so the raw table stays small. Keep the `QUALIFY` in staging as a safety net.
3. **Check the cursor request options.** In `deal` and `contact`, `start_time_option` and `end_time_option` both inject into the same body field (`last_update_stime`), so one value overwrites the other. Confirm in the Builder's request preview which value the API actually receives. If it is the end time, set `end_time_option` to a different field or remove it.

### Schema change handling

| Change in the CRM | What happens | How it is detected |
|---|---|---|
| **New custom field** (the common case) | Custom fields live inside the `form` JSON array, so the **raw schema does not change** and nothing breaks. The new field is simply not used until it is mapped in `stg_*` | `mon_custom_field_registry` + assertion `assert_new_custom_fields` fails on the run where a new field code first appears, which triggers the failure alert |
| New top-level column | Airbyte (schema auto-import on) adds it to raw. Staging selects explicit columns, so nothing breaks | Visible in the Airbyte schema-change notification |
| Column removed or renamed | Staging view fails to compile, the Dataform run fails, and the alert fires. The dashboard keeps the last good data (mart tables are only replaced on success) | Workflow-failure alert |

**Action when a new field appears:** add one line to the pivot in the matching staging model, e.g.
`MAX(IF(code = 'custom_new_field', final_value, NULL)) AS new_field`.

---

## 2. Staff Google Sheet

The staff list (user ID, name, job title) is maintained by hand in a Google Sheet and exposed in BigQuery as an **external table** (`dw_rework_crm.user`). BigQuery reads the sheet live at query time, so there is no sync job to schedule.

- It is declared in Dataform as a source ([`transform/definitions/declarations/user.sqlx`](../transform/definitions/declarations/user.sqlx)) and modeled into `dim_user`.
- **Risk:** someone edits the sheet structure. This is covered by the `dim_user` `uniqueKey`/`nonNull` assertions and by `assert_owner_orphan_rate`, which flags a sudden jump in deals whose owner is missing from `dim_user`.
- The Dataform service account needs viewer access to the sheet (share it with the service account's email).

---

## Reproduce

1. Airbyte → Builder → **Import YAML** → `airbyte/rework-crm-connector.yaml`.
2. Fill in the connector config: `domain`, `access_token`, `password`, `service_id`, `user_id`. Store them only in Airbyte, never in Git.
3. Create a connection to a BigQuery destination (dataset `dw_rework_crm`) with the sync modes from the table above.
4. In BigQuery, create an external table `dw_rework_crm.user` from the staff Google Sheet (*Create table → Source: Drive → Google Sheets*).
