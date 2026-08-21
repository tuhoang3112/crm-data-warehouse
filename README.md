# CRM Data System Rebuild: From Pipedrive to Rework CRM

> An end-to-end rebuild of a CRM analytics pipeline after migrating from Pipedrive to Rework CRM, with historical reconciliation, dimensional modeling, data-quality validation, and Power BI reporting.

## Background

The company migrated its CRM from **Pipedrive to Rework CRM**.

The existing Data Warehouse had been built around Pipedrive's data structure, so the data pipeline could no longer support Sales reporting after the migration.

At the same time, historical Pipedrive data needed to be preserved so key Sales metrics such as **pipeline performance, deal stages, win rate, and lost reasons** could continue to be tracked consistently.

**Goal:** Rebuild the data pipeline and analytical model for Rework CRM while preserving historical Pipedrive data and maintaining reporting continuity.

---

## Architecture

```text
Rework CRM API
      │
      ▼
Airbyte (self-hosted)
Ingestion + Incremental Sync
      │
      ▼
BigQuery
Raw Data Layer
      │
      ▼
Dataform
Staging + Transformation
      │
      ▼
BigQuery Data Mart
Fact + Dimension Tables
      │
      ▼
Power BI
Sales Management & Monitoring
```

---

## Data Model

The Data Mart follows a **Snowflake Schema** designed around Deals and Deal Activities, with supporting dimensions for Contacts, Accounts, Pipelines, Stages, and Users.

![CRM Data Mart](assets/erd.png)

### Main Tables

- `fact_deal` — one row per deal
- `fact_deal_activity` — one row per deal activity
- `dim_contact` — Contact dimension with SCD Type 2 for selected attributes
- `dim_account` — Account/company information
- `dim_pipeline` — Sales pipeline information
- `dim_stage` — Sales stage information
- `dim_user` — Sales owner/user information

→ [View Data Dictionary](./docs/data-dictionary.md)

---

# Implementation

## 1. Understanding the Data & Migration

The main CRM entities and historical data were reviewed to understand how Rework CRM differed from Pipedrive.

Not every historical field could be mapped directly. Some Pipedrive values were stored in Rework custom fields, while some Rework fields represented the migration event rather than the original business event.

This analysis determined which source fields should be used in the analytical layer.

→ [View Project Requirements](./docs/project-requirements.md)

## 2. API Exploration & Ingestion

The main Rework CRM API endpoints were explored and tested in **Postman** before building the Airbyte connector.

The main challenges were:

- Authentication
- `page / limit` pagination
- Nested data
- Deal → Activity parent-child streams
- Incremental Sync

Airbyte self-hosted with the Low-code Connector Builder was then used to ingest the CRM data into BigQuery.

→ [View Airbyte Connector](./airbyte-custom-connector/)

## 3. Raw Data & Transformation

Airbyte loads the extracted CRM data into a **BigQuery raw layer**, preserving the source structure before transformation.

**Dataform** is then used to build the staging layer and transform the data into analytics-ready tables.

Key transformations include:

- Extracting nested custom fields with `UNNEST`
- Pivoting dynamic key/value fields into analytical columns
- Standardizing CRM statuses
- Mapping lost-reason identifiers
- Removing duplicate source versions with `QUALIFY ROW_NUMBER()`

The transformation layer also reconciles historical Pipedrive data where Rework timestamps represent migration events.

For example:

```sql
COALESCE(
    pipedrive_created_at,
    rework_created_at
)
```

This prevents the CRM migration itself from distorting historical Sales reporting.

→ [View Dataform Models](./dataform/)

## 4. Data Mart

The cleaned staging data is transformed into a **Snowflake Schema** centered around Deals and Deal Activities.

`dim_contact` uses **Slowly Changing Dimension Type 2 (SCD2)** to preserve historical versions of selected Contact attributes such as job title and location.

→ [View Data Dictionary](./docs/data-dictionary.md)

---

# Testing & Validation

The project was validated at **two levels**:

1. **Data Mart validation before Power BI**
2. **Power BI validation after the dashboard was built**

## 1. Data Mart Validation — Before Power BI

Before building Power BI, the Data Mart was validated for:

- Referential integrity
- Completeness and NULL patterns
- Categorical consistency
- Duplicate records
- SCD Type 2 logic
- Historical data reconciliation

The review identified issues including:

- `dim_contact.account_id → dim_account.account_id` — **99.97% orphan rate**
- Inconsistent casing and formatting across tracking/business values
- High NULL rates in selected business fields
- Low-value fields with little or no variation
- SCD2 checks requiring continued validation

The detailed findings and remediation actions are documented in the **[Data Quality Review](./docs/data-quality-review.pdf)**.

```text
Raw / Staging
      ↓
Data Mart
      ↓
Data Quality Validation
      ↓
Fix / Investigate Issues
      ↓
Validated Data Mart
```

**Only after this validation was completed was the Data Mart used as the source for Power BI.**

## 2. Power BI

The validated Data Mart was used as the source for the Sales Pipeline dashboard in **Power BI**.

The dashboard provides Sales Manager and Sales Admin with a management-level view of:

- Sales pipeline performance
- Deal stages
- Win / loss performance
- Sales activities
- Team performance
- Warning signals requiring attention

→ [View Dashboard](./sales_dashboard/)

## 3. Power BI Validation — After Dashboard Build

After the dashboard was built, the reporting layer was validated against the **validated Data Mart**, **Rework CRM**, and the **previous Power BI dashboard** where applicable.

Key metrics included:

- Deal count
- Deal stage
- Won / Lost deals
- Win rate
- Lost reasons
- Team performance

→ [View detailed Testing & Validation](./docs/testing-validation.md)

---

# Results

The rebuilt pipeline restored the flow from **Rework CRM to the Data Warehouse and Power BI** while preserving historical Pipedrive data.

The Data Mart was validated before reporting, and the final Power BI layer was independently checked against the validated Data Mart and relevant source/reporting references.

As a result, **Sales Manager and Sales Admin can continue monitoring team-level Sales performance, pipeline health, and warning signals through Power BI**, while Sales representatives continue using Rework CRM for day-to-day operations.

→ [View Power BI Dashboard](./sales_dashboard/)

---

## Skills & Tools

| Area | Skills & Tools |
|---|---|
| **API** | REST API, Postman, pagination, parent-child streams |
| **Data Ingestion** | Airbyte, Low-code Connector Builder, Incremental Sync |
| **Data Warehouse** | BigQuery |
| **SQL** | `JSON_VALUE`, `UNNEST`, `QUALIFY ROW_NUMBER()`, window functions |
| **Transformation** | Dataform, staging & mart layers |
| **Data Modeling** | Snowflake Schema, Fact & Dimension tables, SCD Type 2 |
| **Data Quality** | Referential integrity, completeness, categorical consistency, SCD2 validation |
| **BI** | Power BI, Sales Pipeline reporting |

---

## Public Portfolio & Data Privacy

This project is based on real business data. The public repository intentionally excludes sensitive information and is designed to demonstrate the **architecture, transformation logic, analytical model, validation approach, and data-quality process** rather than expose company data.

- Raw customer records are not included in the public repository.
- Credentials, API keys, and secrets are not stored in the repository.
- Sensitive identifying fields and business-specific values are excluded from public analytical outputs where appropriate.
- Aggregate data-quality metrics may be shown to demonstrate validation work without exposing individual records.

### AI-Assisted Analysis

AI is used as an analytical interface, while data access is controlled at the Data Mart layer.

Sensitive and credential-related fields are removed from the analytical layer before AI-assisted analysis. The AI can generate Python/SQL queries and execute them through an **already-authenticated database connection**.

The AI may access data returned by a query when required for analysis, but it does not receive database credentials, and fields excluded from the Data Mart are not available to query.

> **Key principle:** privacy is enforced at the **data-access and data-model layer**, rather than relying on the AI to hide sensitive information after retrieval.

---

## Repository Structure

```text
crm-data-warehouse/
│
├── docs/
│   ├── project-requirements.md   # Requirements, scope & execution plan
│   ├── data-dictionary.md        # Data model & field definitions
│   ├── data-quality-review.pdf   # Detailed Data Quality Review
│   └── testing-validation.md     # Reporting & Data Mart validation
│
├── airbyte-custom-connector/     # Rework CRM API ingestion
├── dataform/                     # Transformation & Data Mart
├── sales_dashboard/              # Power BI reporting
└── assets/                       # ERD & screenshots
```

> **Note:** No raw customer records, credentials, or sensitive business values are included in this public repository.
