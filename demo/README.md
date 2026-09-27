# Demo data (fake)

A **randomly generated** dataset with exactly the same tables and columns as the `dm_rework_crm` mart. Point the Power BI report at it to share or publish the dashboard **without exposing any real customer, staff or revenue data**.

- Every name, number and date is random. Nothing is copied from real data.
- The *business logic* follows [metric-definitions.md](../docs/metric-definitions.md): funnel stages, lost reasons allowed per stage, `inbox` tags only on won deals, SCD2 contact versions, and more open deals in recent weeks. Charts therefore look realistic.
- It is reproducible: a fixed seed gives the same data on every run.

## 1. Generate

```bash
python demo/generate_demo_data.py              # 3,000 deals (default)
python demo/generate_demo_data.py --deals 8000
```

Output: `demo/data/*.csv`, one file per table:
`fact_deal`, `fact_deal_activity`, `dim_contact`, `dim_account`, `dim_user`, `dim_pipeline`, `dim_stage`, `dim_class_schedule`.

Labels that Power BI measures filter on must match the real mart **exactly**. Pipeline IDs/names, stage IDs/names, activity types and lost reasons are taken from the real mart. Course names, prices, people and companies are intentionally fake.

## 2. Load into Power BI

**Option A: BigQuery demo dataset (recommended).** Switching becomes a one-word change.

1. BigQuery → create dataset `dm_rework_crm_demo`.
2. Load each CSV as a table with the same name: *Create table → Upload → CSV → Auto-detect schema → header rows to skip: 1*.
3. Power BI Desktop → **Save As** a copy of the report (e.g. `sales_dashboard_demo.pbix`).
4. **Transform data** → for each table, open the *Navigation* step and change the dataset from `dm_rework_crm` to `dm_rework_crm_demo` → **Close & Apply**.

**Option B: CSV files directly.**

1. Save a copy of the report.
2. **Transform data** → for each table, **Source** step → replace the BigQuery source with *Text/CSV* pointing to `demo/data/<table>.csv`.
3. Check column types: dates → *Date/Time*, `deal_value` → *Decimal*, `is_current` → *True/False* → **Close & Apply**.

## 3. Check and share

- Spot-check a few cards (lead count, win rate, funnel) to confirm the measures work.
- The data is fake, so you can use **Publish to web** for a public link, or export screenshots without blurring.
- Label the report clearly, e.g. a text box: *"Demo data - randomly generated"*.

## Changelog format

Changelog rows (`activity_type = "Thay đổi hệ thống"`) follow the real patterns:

- `<user> set <contact> as primary contact of deal <deal name>`
- `<user> move deal <deal name> to pipeline <pipeline> with stage <stage>`, where `|` in the pipeline name is stored as `&#124;`, exactly as in the mart

Deal names follow `<contact> - <course> - <ONL/OFF>`. Nurturing deals first move through Sales stages, then get moved to the Nurturing pipeline.
