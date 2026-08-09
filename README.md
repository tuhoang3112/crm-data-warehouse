[Tiếng Việt](README.vi.md)

# Data Warehouse Migration: From Pipedrive to Rework CRM

## Background

The company switched its CRM from **Pipedrive to Rework CRM**. The two systems have different data structures and APIs.

**Problem:** The existing Data Warehouse was built around Pipedrive's structure, so the data pipeline stopped working after the migration. At the same time, the Sales team still needed to track the pipeline: which stage deals were in, win rates, and common reasons why deals were lost.

**Goal:** Rebuild the ingestion pipeline and data model for Rework CRM while keeping the historical data migrated from Pipedrive, so Sales reporting could continue without interruption.

---

## Architecture

```text id="o8hpkh"
Rework CRM API
      │
      ▼
Airbyte (self-hosted)  →  raw ingest, incremental sync
      │
      ▼
BigQuery (raw layer)
      │
      ▼
Dataform (staging)  →  clean data, extract custom fields
      │
      ▼
Dataform (mart)  →  Snowflake Schema: fact + dimension
      │
      ▼
Power BI
```

### Data Mart

The Data Mart follows a **Snowflake Schema**, including:

* `fact_deal` — one row per deal
* `fact_deal_activity` — one row per deal activity, such as calls, notes, and change logs
* `dim_pipeline`, `dim_stage`, `dim_contact`, `dim_user` — dimension tables containing information used for analysis
* `dim_account` — stores account/company information in a separate table shared by deals and contacts

*(Insert ERD here)*

---

## Implementation

### 1. Exploring and Testing the API

Reviewed the main Rework CRM API endpoints, including **Pipeline, Deal, Account, and Contact**, based on the API documentation.

Each endpoint was then tested in **Postman** to check the actual response, data structure, pagination, and relationships between endpoints before building the ingestion pipeline.

### 2. Pulling Data with Airbyte

Used **Airbyte self-hosted** and its Low-code Connector Builder to pull data from the Rework CRM API into BigQuery.

A few things needed extra handling:

* The API sends credentials through the **request body** instead of the header.
* Pagination using `page/limit` had to be configured manually.
* Activities cannot be pulled in bulk, so a **parent-child stream** was used: pull all deals first, then pull the activities for each deal.
* **Incremental Sync** was used so each run only pulls new or updated data instead of reloading all ~**25,000 deals and 25,000 contacts**.

### 3. Cleaning Data with Dataform

After the raw data was loaded into BigQuery, **Dataform** was used to build the staging layer and clean the data before loading it into the Data Mart.

The main steps included:

* Parsing nested JSON fields such as `address`, `form`, and `owners`.
* Handling **custom fields** stored by Rework as dynamic JSON arrays: `UNNEST` the data first, then pivot it back into columns using `MAX(IF(...))`.
* Decoding values stored as HTML or Base64 with unusual prefixes.
* Removing duplicates with `QUALIFY ROW_NUMBER()`, keeping one complete original record instead of combining values from different rows.

### 4. Handling Historical Data from Pipedrive

This was the most challenging part of the migration.

Because the old data was imported from Pipedrive, some fields in Rework could not be used directly.

For example, `created_at` in Rework shows **when the record was imported**, not when the deal or contact was originally created. The actual creation date had to be taken from a custom field that stores the original Pipedrive value.

Some custom fields also had no readable names and appeared only as random strings. These fields had to be manually checked in the Rework UI to understand what data they represented.

After identifying the correct fields, `COALESCE` was used to take the original Pipedrive value when available and use the Rework value otherwise.

This kept historical dates accurate instead of treating the CRM migration date as the actual event date.

### 5. Building the Data Mart

The cleaned staging data was used to build a **Snowflake Schema** with fact and dimension tables for analysis.

Account information appeared in both deals and contacts, so it was separated into `dim_account` to reduce duplicated data and keep the data model cleaner.

The Data Mart was then used as the data source for **Power BI** Sales Pipeline reporting.

---

## Skills & Tools

* **API & Postman:** API documentation, endpoint testing, pagination, parent-child streams
* **Airbyte:** Low-code Connector Builder, Incremental Sync
* **BigQuery & SQL:** `JSON_VALUE`, `UNNEST`, `QUALIFY ROW_NUMBER()`, nested JSON, custom field pivoting
* **Dataform:** data transformation organized into `declarations → staging → mart`
* **Data Modeling:** Snowflake Schema, Fact & Dimension tables, ERD
* **Power BI:** Data Mart integration for Sales Pipeline reporting

---

## Results

Successfully connected **Rework CRM** to the Data Warehouse and restored the data flow for the existing Power BI reports after the CRM migration.

The new pipeline also kept the historical Pipedrive data accurate, so key Sales Pipeline metrics such as **deal stage, win rate, and lost reasons** could continue to be tracked consistently.

As a result, the Sales team could continue using their reports without interruption after switching to the new CRM.

> **Note:** This project was built using real company data. The dataset and sensitive information in this repository have been replaced with synthetic data to protect confidentiality.
