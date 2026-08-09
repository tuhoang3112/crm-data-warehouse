[Tiếng Việt](README.vi.md)

# Data Warehouse Migration: From Pipedrive to Rework CRM

## Background

The company switched CRM systems, moving from Pipedrive to Rework CRM. The two platforms have completely different data structures and APIs.

**The problem:** the old warehouse was built around Pipedrive's structure, so it stopped working. But the Sales team still needed to track the pipeline (which stage deals are in, win rates, common reasons deals fall through) without interruption.

**The task:** rebuild the entire ingestion pipeline and data model to match Rework's structure, while keeping the historical data that was migrated over from Pipedrive.

## Architecture

```
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
Dataform (mart)  →  star schema: fact + dimension
      │
      ▼
Power BI
```

**Data mart:**
- `fact_deal` — one row per deal
- `fact_deal_activity` — one row per activity (call, note, change log...)
- `dim_pipeline`, `dim_stage`, `dim_contact`, `dim_account`, `dim_user` — descriptive tables

*(insert ERD image here)*

## How it was built

Rework CRM has API documentation covering its main endpoints.

**1. Exploring the API**
Went through each group of endpoints (Pipeline, Deal, Account, Contact) following the [official documentation](https://rework-standard.apidocs.rework.site/document/8), and tested them in Postman to confirm actual behavior before building the pipeline.

**2. Pulling data with Airbyte**
- The API takes credentials through the request body, not the header, which is unusual.
- Pagination had to be configured manually (page/limit).
- Used a parent-child stream: pull all deals first, then pull each deal's activity — the API doesn't support fetching activity in bulk.
- Used Incremental Sync so each run only pulls what changed, instead of reloading all ~25,000 deals and ~25,000 contacts every time.

**3. Cleaning the data (Dataform staging)**
- Parsed nested JSON fields (address, form, owners).
- Handled custom fields — Rework stores them as a dynamic JSON array instead of fixed columns, so they had to be unnested and then pivoted back into columns using `MAX(IF(...))`.
- Decoded encoded values (HTML, base64 with odd prefixes).
- Removed duplicates with `QUALIFY ROW_NUMBER()`, keeping each original row intact instead of mixing values from different rows.

**4. Reconciling old data from Pipedrive**
This was the hardest part. Since the old data was imported from Pipedrive, some fields in Rework don't reflect reality if used directly. For example, `created_at` in Rework actually records when the record was imported, not when the deal or contact was originally created — so the real creation date had to come from a field that stores the original Pipedrive value instead. Several fields like this also have no readable name, just a random string of characters, which had to be looked up manually in the Rework UI. Used `COALESCE` to prefer the original Pipedrive value when it exists, falling back to Rework's value otherwise, so the data reflects the actual event date rather than the import date.

**5. Building the data mart**
From the cleaned data, designed a star schema, separating fact tables (transactions) from dimension tables (descriptions), ready for Power BI.

## Skills used

- Reading and testing an API without full documentation (Postman, pagination, parent-child streams)
- Airbyte: Low-code Connector Builder, Incremental Sync
- Advanced SQL in BigQuery: `JSON_VALUE`, `UNNEST` for nested JSON, `QUALIFY ROW_NUMBER()` for deduplication, pivoting custom fields
- Data modeling: star schema, ERD design
- Dataform: organizing code by layer (declarations → staging → mart)

## Results
The main goal was to reconnect the new CRM data source to the existing Power BI reports after the migration, so reporting could keep running normally without disrupting the Sales team.

## Limitations & next steps

**Limitations:**
- The data is real company data, so it can't be published directly.

**Next steps:**
- Build a demo version with fake data so the code and dashboard can be shared publicly
