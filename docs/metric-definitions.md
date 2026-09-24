# Metric Definitions

One agreed definition per metric, so Sales, Marketing and Customer Service read the same number.
This document is also the context given to AI-assisted analysis, so an AI answer uses the same definitions as the dashboard.

> **How this differs from the [Data Dictionary](./data-dictionary.md):** the dictionary describes **columns** (what a field contains). This document describes **metrics**: how a number is calculated, from which tables, for whom, and how it is commonly misread.

---

## 0. Global rules (apply to every metric)

| # | Rule | Why |
|---|---|---|
| G1 | **Exclude test deals:** `WHERE NOT is_test_deal` | 20 internal test deals created while testing the CRM (1 of them `won`) |
| G2 | **Time bucketing uses `fact_deal.created_at`** (deal creation date), never `closed_at` / `updated_at` | A deal created in June and won in October is a "June deal" in every trend chart. Name charts "Win rate by **created** month" to avoid ambiguity |
| G3 | **Operational KPIs use `created_at >= 2026-01-01`.** Data-quality checks use full history | Records before 2026 were migrated from Pipedrive, and many already had outcomes at migration time. Full-history win rate (~55%) vs 2026 (~37%) is not a contradiction: they answer different questions |
| G4 | **Never compare pipelines directly.** Report *Sales Prospecting*, *CS Retention* and *B2B* separately | Different processes and populations. B2B win rate is ~95% on a small volume, and merging it distorts every other number |
| G5 | **Nurturing Pipeline is not a separate pipeline.** Its deals are merged into *Sales Prospecting* | It was used to "park" leads waiting for the next class |
| G6 | **Empty string, `NULL` and `"unknown"` are one group** ("no data") when counting or grouping | Otherwise one real answer shows up as 3–4 categories |
| G7 | **Merge equivalent labels before grouping:** `utm_medium` `fanpage` = `fanpage_tm`; `utm_source` `activecampaign` = `email`; renamed courses count as one course | Historical naming changes |

---

## 1. Lead funnel

**Scope:** *Sales | Prospecting Pipeline* only (incl. Nurturing, per G5). Not applicable to CS Retention or B2B.
**Source:** `fact_deal` ⋈ `dim_stage` ⋈ `dim_pipeline`
**Used by:** Marketing (lead quality by channel/course), Sales Manager (funnel bottlenecks)

Stage order: `Lead In → Interested → Engaged → Needs Exploration → Solution Fit → Ready To Purchase → Payment Completion`

Each level = previous level − deals that "failed" at that level. A deal fails at a level when it is **open at that stage**, or **lost at that stage with one of the listed reasons**. Exclusion is based on the exact **(stage, lost_reason)** pair. A deal lost at a stage with a reason *not* on the list (including `NULL`) still counts as having reached that level.

| Metric | Formula | Deals removed at this level (`Not_X`) |
|---|---|---|
| **Lead** | Count of all deals | – |
| **MQL** | Lead − Not_MQL | Open in `Lead In`/`Interested`, or lost there with: `Trash: Đăng ký trùng deal`, `Trash: Không có nhu cầu`, `Communication: Not Connected`, `Communication: Invalid Contact`, `Sales Process: Sales không follow-up khách` (at `Interested`) |
| **SQL – Discovery** | MQL − Not_SQL_Discovery | Open in `Engaged`, or lost there with: `Communication: No Response`, `Low engagement`, `Bad Timing: Không sắp xếp được thời gian học`, `Choose Competitor` (both), `Budget: Giá quá cao`, `Sales Process: Sales không follow-up khách`, `Unhappy: Không đồng ý với quy trình vận hành lớp` |
| **SQL – Fit** | SQL Discovery − Not_SQL_Fit | Open in `Needs Exploration`, or lost there with: `Relevance: Use Case Misfit`, `Relevance: Not ICP fit`, `Choose Competitor` (both), `Budget: Giá quá cao`, `Budget: Not willing to pay`, `Sales Process: Sales không follow-up khách` |
| **Opportunity** | SQL Fit − Not_Opportunity | Open in `Solution Fit`, or lost there with `Bad Timing` (both reasons), **or any Nurturing Pipeline deal** (counted as SQL Fit, then removed here as "waiting for next class") |
| **Won deals** | `deal_status = 'won'` | – |
| **Lost deals** | `deal_status = 'lost'` | – |
| **Open deals** | `deal_status = 'open'` | – |

### Funnel rates: the denominator is always Total Lead

| Metric | Formula |
|---|---|
| MQL Rate | MQL / Lead |
| SQL Discovery Rate | SQL Discovery / Lead |
| SQL Fit Rate | SQL Fit / Lead |
| Opportunity Rate | Opportunity / Lead |
| Lost Rate | Lost / Lead |

**Common misreadings**
- ❌ *"Conversion from MQL to SQL"* using MQL as the denominator. All rates here use **Lead** as the denominator, so they can be compared side by side and add up along the funnel.
- ❌ Treating `Communication: Ghosted After Demo/Call` as a Discovery failure. The call/demo **did happen**, so the deal **did** reach SQL Discovery.

---

## 2. Win Rate

| | |
|---|---|
| **Formula** | `Won deals / Total deals` (**all statuses**: won + lost + open) |
| **Source** | `fact_deal` (+ `dim_stage` → `dim_pipeline` for the pipeline filter) |
| **Used by** | Sales Manager, Sales Admin, CS Manager, Marketing |
| **Variants** | *Win rate LP*: same formula on the previous period of equal length. *Win rate LY*: same period last year |

**Common misreadings**
- ❌ `won / (won + lost)`. That is **close rate**, not win rate, and it is always higher because open deals are ignored. This is the #1 reason two teams have reported different win rates.
- ❌ Comparing the current month's win rate with an old month. Recent months still have many **open** deals, so their win rate rises over time. Compare cohorts of the same age, or wait until most deals are closed.
- ❌ **Win rate by course including "Combo" courses.** The course field is often switched to a Combo **after** a successful upsell, which inflates Combo win rates. Exclude Combo courses from the main course comparison.
- ❌ **Win rate by channel including `utm_medium = 'inbox'`** (or `utm_source` `inbox`/`zalo`). These tags are added by Sales **after** the deal is won (survivorship bias), so they show ~100% win rate. Exclude them from channel comparisons, or show them with a warning.
- ❌ Comparing channels across pipelines. Build **one channel table per pipeline** (Marketing channels ≠ CS channels).
- ✅ Channel analysis should cross `utm_source × utm_medium` (e.g. facebook × cpc = paid, facebook × fanpage = organic).
- ✅ `utm_source` NULL is a **valid group** ("unknown source": organic search or lost UTM). Keep it in comparisons; it is not a tracking bug.

---

## 3. Owner & team performance

| | |
|---|---|
| **Formula** | Win rate / deal count grouped by owner team |
| **Source** | `fact_deal.owner_user_id` → `dim_user.job_title` |
| **Used by** | Sales Manager, CS Manager |

**Team assignment**

| Team | Rule |
|---|---|
| Sales | Owner job title is Sales Manager / Sales Consultant |
| Customer Service | Owner job title is one of the Customer Service titles |
| **Migration-default** | Owner **not in `dim_user`** (staff who left) + the two admin accounts used as default owner during the CRM migration + non-sales/CS staff (e.g. system owner) |

- For **team totals**, migration-default deals are allocated **by pipeline**: Sales Prospecting → Sales team, CS Retention → CS team. B2B is always reported separately.
- **Never** rank individuals inside migration-default, because the real owner is unknown.

**Common misreadings**
- ❌ CS win rate ≈ 90%. It is inflated by a block of ~1,000 migrated deals that already had outcomes. Always also show *CS win rate excluding migrated deals* (~64%).
- ❌ Adding B2B into the Sales team total. Report it as "X deals (Sales Pipeline) + Y deals (B2B)".

---

## 4. Revenue

| Metric | Formula | Source |
|---|---|---|
| **Won Revenue** | `SUM(deal_value)` where `deal_status = 'won'` | `fact_deal.deal_value` |
| **Average Deal Size** | Won Revenue / count of won deals **with a non-null `deal_value`** | `fact_deal` |
| **Open Pipeline Value** | `SUM(deal_value)` where `deal_status = 'open'` | `fact_deal` |

**How `deal_value` is built (in `stg_deal`):** `COALESCE(pipedrive_product_amount, NULLIF(rework_value, 0))`. Migrated deals use the original Pipedrive amount; Rework-native deals use the Rework deal value, and `0` is treated as "not entered".

**Used by:** Sales Manager, management.

**Common misreadings**
- ❌ Treating `deal_value` as cash collected. It is the **deal value recorded in the CRM**, not a payment, invoice or accounting revenue. Discounts, refunds and instalments are not reflected.
- ❌ Averaging over all won deals, including those with no value. Deals with `NULL` value would pull the average down. Check the share of won deals with a value before trusting the number.
- ❌ Comparing revenue before and after the migration without checking coverage. Pipedrive amounts and Rework values were entered under different processes.

> **Privacy:** revenue values are never published in this repository or in public screenshots.

---

## 5. Speed metrics

| Metric | Formula | Source | Used by |
|---|---|---|---|
| **Deal cycle time (days)** | `DATE_DIFF(closed_at, created_at, DAY)` for closed deals | `fact_deal` | Sales Manager |
| **Time in stage (days)** | Time between consecutive stage-change events of a deal | `fact_deal_activity` (changelog activities) | Sales Manager |
| **Avg. stages per deal** | Distinct stages a deal passed through | `fact_deal_activity` (changelog) | Sales Manager |
| **First response time** | First activity `created_at` − deal `created_at` | `fact_deal_activity` ⋈ `fact_deal` | Marketing, Sales Manager |
| **Avg. leads per day / week** | Lead count / number of days (weeks) in the selected period | `fact_deal` | Marketing |

**Common misreadings**
- ❌ Cycle time on migrated deals. Use `created_at >= 2026-01-01` (G3).
- ❌ Reading high weekday volume or late-night lead creation as a system/batch error. It is real customer behaviour.

---

## 6. Derived segments

### 6.1 "Lead CKS" backlog (waiting for next class)

A deal is **lead cks** if **any** of these is true:
1. `labels = 'lead cks'` (manual tag)
2. The deal is in the Nurturing Pipeline (old mechanism)
3. The deal was created before the start date of its class, that start date has passed, and the deal is still `open`

**Backlog** = lead cks deals still `open`. **Used by:** Sales Manager (not Marketing: the lead was qualified, but Sales did not close it before the class deadline).
❌ Using `labels` alone misses about half of the backlog.

### 6.2 Alumni (returning customers)

A deal belongs to an alumnus if **any** of these is true:
1. `is_alumni` tag is set
2. The contact has **≥ 2 won deals**, in which case every later deal of that contact is also counted
3. The deal is a **won** deal on a combo / program / advanced course

**Used by:** Sales, CS.
❌ Using `is_alumni` alone captures only ~8% of real alumni. The count is in **deals**, not people.
❌ "Alumni" (who the customer is) ≠ "CS Retention Pipeline" (which team handles it). Most alumni deals are handled proactively by Sales, by design.

---

## 7. Data-quality notes that affect metrics

| Field | Note |
|---|---|
| `lost_reason` | `NULL` on migrated deals created before 2026 (old reasons could not be mapped). Not an issue in the 2026 scope |
| `pain_point_captured`, `pending_reason`, `next_step`, `has_followup_plan` | 97–99% NULL because they were **added recently**, not because of a tracking failure. Use `expectation` to measure "customer need identified" |
| `dim_contact.account_id = 0` | Means "no company". Report account match rate **with and without** `0` |
| `owner_user_id` not in `dim_user` | Staff who have left → migration-default (section 3) |
