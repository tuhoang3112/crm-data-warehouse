# Data Dictionary

## Data Model

![CRM Data Mart](../assets/erd.png)

The Data Mart follows a **Snowflake Schema** centered around Deals and Deal Activities.

> **Public-data note:** field definitions are documented for modeling purposes. Raw customer records, credentials, and sensitive business values are not included in the public repository.

---

## `fact_deal`

**Grain:** One row per deal

| Field | Definition | Data Quality Consideration |
|---|---|---|
| `deal_id` | Unique identifier of the deal | Should be unique and non-null |
| `contact_key` | Contact version associated with the deal | Validate FK relationship to `dim_contact.contact_key` |
| `stage_id` | Current Sales stage | Validate FK relationship to `dim_stage.stage_id` |
| `owner_user_id` | Sales owner responsible for the deal | Validate FK relationship to `dim_user.user_id` |
| `deal_name` | Name of the deal | Raw values are not included in public outputs |
| `deal_status` | Deal status: Open, Won, or Lost | Standardize categorical values |
| `course_selected` | Course/product selected by the customer | Review completeness and category consistency |
| `learning_format` | Selected learning format | Review completeness and category consistency |
| `pain_point_captured` | Whether the customer's pain point has been identified | High NULL rate requires source-workflow review |
| `pending_reason` | Reason why the deal is pending | Review completeness and category consistency |
| `next_step` | Next planned Sales action | High NULL rate requires source-workflow review |
| `lost_reason` | Standardized reason why the deal was lost | Validate standardized categories and completeness |
| `lost_reason_detail` | Additional detail about the lost reason | Review completeness and business usage |
| `utm_source` | Marketing acquisition source | Normalize casing and whitespace |
| `utm_medium` | Marketing acquisition medium | Normalize casing and whitespace |
| `utm_content` | Campaign/content attribution | Normalize casing, whitespace, and equivalent values |
| `created_at` | Original deal creation date | For migrated records, preserve original Pipedrive date when available |
| `updated_at` | Last update date | Validate timestamp behavior |
| `closed_at` | Deal close date | For migrated records, validate historical date handling |

> For migrated records, historical Pipedrive dates are used when the corresponding Rework timestamps represent the migration event.

---

## `fact_deal_activity`

**Grain:** One row per deal activity

| Field | Definition | Data Quality Consideration |
|---|---|---|
| `activity_id` | Unique identifier of the activity | Should be unique and non-null |
| `deal_id` | Deal associated with the activity | Validate FK relationship to `fact_deal.deal_id` |
| `activity_type` | Activity type, such as Call, Note, or Change Log | Standardize activity categories |
| `activity_content` | Activity content or description | Raw values are not included in public outputs |
| `owner_user_id` | User associated with the activity | Validate FK relationship to `dim_user.user_id` |
| `created_at` | Activity creation time | Validate timestamp consistency |

---

## `dim_contact`

**Grain:** One row per Contact version (SCD Type 2)

| Field | Definition | Data Quality Consideration |
|---|---|---|
| `contact_key` | Surrogate key for a Contact version | Must be unique |
| `contact_id` | CRM Contact identifier | Validate business-key/version uniqueness |
| `account_id` | Account associated with the Contact | **FK integrity requires investigation** |
| `contact_name` | Contact name | Raw values are not included in public outputs |
| `location` | Contact location | Historical changes preserved through SCD2 |
| `job_title` | Contact job title | Historical changes preserved through SCD2 |
| `created_at` | Original Contact creation date | Validate against historical migration logic |
| `effective_date` | Date the version became effective | Required for SCD2 period validation |
| `end_date` | Date the version stopped being effective | NULL is expected for current versions |
| `is_current` | Whether this is the current Contact version | Only one current version should exist per Contact |

> SCD Type 2 is used to preserve changes in `job_title` and `location`.

---

## `dim_account`

**Grain:** One row per account

| Field | Definition | Data Quality Consideration |
|---|---|---|
| `account_id` | Unique Account identifier | Primary key; used by Contact FK relationship |
| `account_name` | Company/account name | Raw values are not included in public outputs |
| `industry` | Company industry | Review category consistency |
| `company_size` | Company size | Review category consistency |
| `website` | Company website | Review whether the field provides analytical value |

---

## `dim_pipeline`

| Field | Definition | Data Quality Consideration |
|---|---|---|
| `pipeline_id` | Unique Pipeline identifier | Should be unique and non-null |
| `pipeline_name` | Pipeline name | Validate category consistency |

---

## `dim_stage`

| Field | Definition | Data Quality Consideration |
|---|---|---|
| `stage_id` | Unique Stage identifier | Should be unique and non-null |
| `pipeline_id` | Pipeline containing the Stage | Validate FK relationship to `dim_pipeline.pipeline_id` |
| `stage_name` | Stage name | Validate stage mapping and category consistency |

---

## `dim_user`

| Field | Definition | Data Quality Consideration |
|---|---|---|
| `user_id` | Internal user identifier | Validate FK relationships from fact tables |
| `full_name` | Employee name | Raw values are not included in public outputs |
| `job_title` | Employee job title | Review consistency where used analytically |

---

## Data Quality Review

The Data Dictionary should be read together with the detailed Data Quality Review.

The review covers:

1. Referential integrity
2. Categorical and tracking-value consistency
3. High-null columns
4. Low-value fields
5. SCD Type 2 validation
6. Automated data-quality controls as a next step

→ [View the full Data Quality Review](./data-quality-review.pdf)
