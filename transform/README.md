# Transform (Dataform)

All transformations run in **Dataform** (BigQuery-native, SQLX + Git). Dataform resolves dependencies from `${ref()}`, and builds models in the right order.

```text
transform/
├── workflow_settings.yaml        # project defaults
└── definitions/
    ├── declarations/             # sources: 6 Airbyte tables + 2 Google Sheets (staff, class schedule)
    ├── staging/   (6 views)      # clean, decode, pivot custom fields, dedupe, reconcile Pipedrive history
    ├── marts/     (8 tables)     # fact_deal, fact_deal_activity, dim_contact (SCD2), dim_account, dim_pipeline, dim_stage, dim_user, dim_class_schedule
```

## Layers

| Layer | Dataset | Materialization | Purpose |
|---|---|---|---|
| Raw | `dw_rework_crm` | Airbyte tables + Google Sheets external tables | Untouched source data, full history |
| Staging | `dm_rework_crm_view` | **Views** | Always reflects the latest raw data; no storage cost |
| Mart | `dm_rework_crm` | **Tables** (full rebuild), `dim_contact` **incremental** | Fast, stable tables for Power BI |

## Key transformation logic

- **Custom fields:** `UNNEST(JSON_QUERY_ARRAY(form))`, then pivot with `MAX(IF(code = ..., value, NULL))`. For `select`-type fields the display label is used instead of the internal ID.
- **Historical reconciliation:** migrated records carry their original Pipedrive dates in custom fields. Rework's own `since` is the **migration date**, so:
  `created_at = COALESCE(pipedrive_created_at, rework_since)`. `closed_at` and `deal_value` follow the same pattern.
- **Encoded values:** Pipedrive notes/next steps are Base64 (`SAFE.FROM_BASE64`), HTML tags/entities are stripped with `REGEXP_REPLACE`, and lost-reason IDs are mapped to labels.
- **Dedup:** `QUALIFY ROW_NUMBER() OVER (PARTITION BY id ORDER BY _airbyte_extracted_at DESC) = 1`.
- **SCD Type 2 (`dim_contact`):** a new version is inserted when `job_title` or `location` changes. A post-operation closes the previous version (`end_date`, `is_current = FALSE`). `fact_deal` joins the contact version valid at the deal's `created_at`.

## Data quality

Known and **accepted** data issues are documented in [`../docs/data-dictionary.md`](../docs/data-dictionary.md). Example: `dim_contact.account_id = 0` means "contact without a company".

## Run it

```bash
npm i -g @dataform/cli@3.0.52
cd transform
dataform compile                       # validates SQLX + dependency graph (no credentials needed)
dataform init-creds                    # BigQuery credentials (.df-credentials.json, git-ignored)
dataform run --schema-suffix dev       # build everything into *_dev datasets
dataform run --actions fact_deal --include-deps   # rebuild one model and its upstream
```

Set `defaultProject` in `workflow_settings.yaml` to your GCP project ID before running.
