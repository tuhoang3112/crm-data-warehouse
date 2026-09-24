# Transform (Dataform)

All transformations run in **Dataform** (BigQuery-native, SQLX + Git). Dataform resolves dependencies from `${ref()}`, builds models in the right order, and runs the data tests after each build.

```text
transform/
├── workflow_settings.yaml        # project defaults + vars (freshness threshold, orphan tolerance)
├── includes/constants.js         # business constants (test deal IDs)
└── definitions/
    ├── declarations/             # raw sources: 7 Airbyte tables + staff Google Sheet
    ├── staging/   (6 views)      # clean, decode, pivot custom fields, dedupe, reconcile Pipedrive history
    ├── marts/     (7 tables)     # fact_deal, fact_deal_activity, dim_contact (SCD2), dim_account, dim_pipeline, dim_stage, dim_user
    ├── monitoring/               # mon_custom_field_registry (schema-change detection)
    └── assertions/               # custom data tests
```

## Layers

| Layer | Dataset | Materialization | Purpose |
|---|---|---|---|
| Raw | `dw_rework_crm` | Airbyte tables + Sheets external table | Untouched source data, full history |
| Staging | `dm_rework_crm_view` | **Views** | Always reflects the latest raw data; no storage cost |
| Mart | `dm_rework_crm` | **Tables** (full rebuild), `dim_contact` **incremental** | Fast, stable tables for Power BI |
| Monitoring | `dm_rework_crm_monitoring` | Incremental | Pipeline metadata |

## Key transformation logic

- **Custom fields:** `UNNEST(JSON_QUERY_ARRAY(form))`, then pivot with `MAX(IF(code = ..., value, NULL))`. For `select`-type fields the display label is used instead of the internal ID.
- **Historical reconciliation:** migrated records carry their original Pipedrive dates in custom fields. Rework's own `since` is the **migration date**, so:
  `created_at = COALESCE(pipedrive_created_at, rework_since)`. `closed_at` and `deal_value` follow the same pattern.
- **Encoded values:** Pipedrive notes/next steps are Base64 (`SAFE.FROM_BASE64`), HTML tags/entities are stripped with `REGEXP_REPLACE`, and lost-reason IDs are mapped to labels.
- **Dedup:** `QUALIFY ROW_NUMBER() OVER (PARTITION BY id ORDER BY _airbyte_extracted_at DESC) = 1`.
- **SCD Type 2 (`dim_contact`):** a new version is inserted when `job_title` or `location` changes. A post-operation closes the previous version (`end_date`, `is_current = FALSE`). `fact_deal` joins the contact version valid at the deal's `created_at`.
- **Test deals** are flagged (`is_test_deal`), not deleted, so they stay traceable but are excluded from metrics.

## Data tests (22 assertions)

| Type | Where | Checks |
|---|---|---|
| Uniqueness | every mart table (`uniqueKey`) | `deal_id`, `activity_id`, `contact_key`, `account_id`, `pipeline_id`, `stage_id`, `user_id` |
| Completeness | every mart table (`nonNull`) | keys + critical fields (`deal_status`, `created_at`, `effective_date`...) |
| Validity | `rowConditions` | `deal_status ∈ {open, won, lost}`, `deal_value ≥ 0`, SCD2 date logic |
| Referential integrity | `assertions/assert_fk_*` | deal→stage, deal→contact version, activity→deal, stage→pipeline |
| Tolerated integrity | `assert_owner_orphan_rate` | share of deals owned by users missing from `dim_user` (people who left) ≤ 10% |
| SCD2 | `assert_scd2_one_current_version` | exactly one current version per contact, no overlapping periods |
| Freshness | `assert_source_freshness` | raw data extracted within `freshness_max_hours` |
| Schema change | `assert_new_custom_fields` | no unmapped CRM custom field appeared since the last run |

A failing assertion fails the workflow run, which triggers the alert (see [`../orchestration/`](../orchestration/)).

Known and **accepted** data issues are documented rather than asserted, so the pipeline does not fail every week for a known business behaviour. Example: `dim_contact.account_id = 0` means "contact without a company". See [`../docs/data-dictionary.md`](../docs/data-dictionary.md).

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
