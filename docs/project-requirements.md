# Project Requirements

## 1. Background

The company migrated its CRM from **Pipedrive to Rework CRM**. Since the
two systems use different APIs and data structures, the existing data
pipeline could no longer support Sales reporting.

Historical Pipedrive data had also been migrated into Rework. Some original
values were stored in custom fields, while standard Rework fields could
represent the migration date rather than the original business event.

**Goal:** Rebuild the data pipeline for Rework CRM while preserving
historical data and reporting continuity.

---

## 2. Users & Reporting Needs

| User | Reporting Need |
|---|---|
| **Sales Manager** | Monitor team performance, pipeline health, and warning signals |
| **Sales Admin** | Monitor team-level metrics and investigate operational issues |
| **Sales Team** | Primarily works directly in Rework CRM |

The Power BI dashboard serves as a **management and monitoring layer**,
rather than replacing the CRM.

Key reporting needs:

- Sales pipeline & deal stages
- Win/loss performance
- Lost reasons
- Sales activities
- Historical performance
- Warning signals

---

## 3. Requirements

The rebuilt system needed to:

1. Ingest Deal, Contact, Account, Pipeline, Stage, and Activity data from Rework CRM.
2. Support incremental loading for new and updated records.
3. Handle deal activities through parent-child API requests.
4. Store source data in a BigQuery raw layer.
5. Clean nested JSON, custom fields, encoded values, and duplicates.
6. Preserve original Pipedrive values for migrated records when required.
7. Build fact and dimension tables for Sales analysis.
8. Provide the Data Mart used by Power BI.
9. Produce results that could be validated against the previous dashboard and Rework CRM.

---

## 4. Scope

**In scope**

`Rework API → Airbyte → BigQuery → Dataform → Data Mart → Power BI`

Including historical Pipedrive data reconciliation and reporting validation.

**Out of scope**

- CRM application development
- Sales process redesign
- Replacement of operational CRM workflows

---

## 5. Execution Plan

```text
Requirements
    ↓
CRM Entity Mapping
    ↓
API Exploration & Postman Testing
    ↓
Airbyte Ingestion
    ↓
BigQuery Raw Layer
    ↓
Dataform Staging
    ↓
Historical Data Reconciliation
    ↓
Data Mart
    ↓
Power BI
    ↓
Validation
