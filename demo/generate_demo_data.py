"""
Generate a FAKE dataset with exactly the same tables and columns as the
`dm_rework_crm` mart, so the Power BI report can be pointed at it and shared
publicly without exposing any real customer, staff or revenue data.

Every name, value and date below is randomly generated. Nothing is copied
from the real data. Business *logic* (funnel stages, lost reasons per stage,
tracking conventions) follows docs/metric-definitions.md so the report's
measures behave the same way as on real data.

Usage:
    python demo/generate_demo_data.py            # writes CSVs to demo/data/
    python demo/generate_demo_data.py --deals 5000

Only the Python standard library is used.
"""

import argparse
import csv
import random
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

SEED = 42
START_DATE = date(2025, 1, 1)
END_DATE = date(2026, 9, 27)
OUT_DIR = Path(__file__).parent / "data"

# ---------------------------------------------------------------------------
# Reference data - edit these lists to match the labels your Power BI
# measures filter on (stage names, pipeline names, lost reasons...).
# ---------------------------------------------------------------------------

PIPELINES = {
    1: ("Sales | Prospecting Pipeline", [
        "Lead In", "Interested", "Engaged", "Needs Exploration",
        "Solution Fit", "Ready To Purchase", "Payment Completion"]),
    2: ("CS | Retention Pipeline", [
        "Lead In", "Interested", "Engaged", "Ready To Purchase", "Payment Completion"]),
    3: ("B2B pipeline", [
        "Lead In", "Needs Exploration", "Proposal", "Negotiation", "Payment Completion"]),
    4: ("Nurturing Pipeline", ["Timing Not Ready", "Re-Activated"]),
}
PIPELINE_WEIGHTS = {1: 0.82, 2: 0.10, 3: 0.05, 4: 0.03}

# Lost reasons allowed at each Sales-pipeline stage (from the funnel rules)
LOST_REASONS_BY_STAGE = {
    "Lead In": ["Trash: Đăng ký trùng deal", "Trash: Không có nhu cầu",
                "Communication: Not Connected: Không liên hệ được", "Communication: Invalid Contact"],
    "Interested": ["Trash: Không có nhu cầu", "Communication: Not Connected: Không liên hệ được",
                   "Sales Process: Sales không follow-up khách"],
    "Engaged": ["Communication: No Response", "Low engagement: Không còn nhu cầu học",
                "Bad Timing: Không sắp xếp được thời gian học", "Budget: Giá quá cao",
                "Communication: Ghosted After Demo/Call"],
    "Needs Exploration": ["Relevance: Use Case Misfit: Nhu cầu không đúng với sản phẩm",
                          "Relevance: Not ICP fit", "Budget: Not willing to pay",
                          "Choose Competitor: Đã đi học bên khác"],
    "Solution Fit": ["Bad Timing: No Immediate Priority",
                     "Bad Timing: Không sắp xếp được thời gian học"],
    "Ready To Purchase": ["Budget: Giá quá cao", "Choose Competitor: Không học online"],
}
GENERIC_LOST_REASONS = ["Budget: Giá quá cao", "Bad Timing: No Immediate Priority",
                        "Communication: No Response"]

# Fake product catalogue: (course name, list price in VND)
COURSES = [
    ("Course A - Foundation", 4_500_000), ("Course B - Foundation", 5_000_000),
    ("Course C - Advanced", 7_500_000), ("Course D - Advanced", 8_000_000),
    ("Course E - Specialist", 9_500_000), ("Course F - Short course", 2_500_000),
    ("Program G - Professional", 18_000_000), ("Combo: Course A + Course C", 11_000_000),
]
COURSE_WEIGHTS = [18, 16, 14, 12, 10, 14, 6, 10]
LEARNING_FORMATS = ["Online", "Offline", "Hybrid"]

# (utm_source, utm_medium, weight). "inbox" is tagged only on won deals, as in the real process.
CHANNELS = [
    ("facebook", "cpc", 30), ("facebook", "fanpage", 12), ("google", "cpc", 12),
    ("email", "newsletter", 8), ("blog", "organic", 6), ("homepage", "organic", 6),
    ("zalo", "oa", 4), (None, None, 22),
]

STAFF = [
    ("Sales Manager", 1), ("Sales Consultant", 5),
    ("Customer Service Manager", 1), ("Customer Service", 2),
]

LAST_NAMES = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan", "Vũ", "Võ", "Đặng",
              "Bùi", "Đỗ", "Hồ", "Ngô", "Dương", "Lý"]
MIDDLE_NAMES = ["Văn", "Thị", "Minh", "Ngọc", "Thanh", "Quốc", "Hải", "Thu", "Gia", "Bảo", "Anh"]
FIRST_NAMES = ["An", "Bình", "Châu", "Dung", "Giang", "Hà", "Hùng", "Khoa", "Lan", "Linh", "Long",
               "Mai", "Nam", "Nhi", "Phúc", "Quân", "Sơn", "Tâm", "Thảo", "Trang", "Tuấn", "Vy", "Yến"]
LOCATIONS = ["Hà Nội", "TP. Hồ Chí Minh", "Đà Nẵng", "Hải Phòng", "Cần Thơ", "Bình Dương", "Huế"]
JOB_TITLES = ["Marketing Executive", "Data Analyst", "Business Analyst", "Sales Executive",
              "Student", "Brand Manager", "Product Owner", "Founder", "Account Manager", None]
INDUSTRIES = ["Retail", "FMCG", "Banking", "Technology", "Logistics", "Education"]
COMPANY_SIZES = ["1-10", "11-50", "51-200", "201-500", "unknown"]


def fake_name(rng):
    return f"{rng.choice(LAST_NAMES)} {rng.choice(MIDDLE_NAMES)} {rng.choice(FIRST_NAMES)}"


def rand_datetime(rng, start, end):
    span = (end - start).days
    d = start + timedelta(days=rng.randint(0, span))
    # More leads on weekdays and during the day
    if d.weekday() >= 5 and rng.random() < 0.4:
        d -= timedelta(days=rng.randint(1, 2))
    return datetime(d.year, d.month, d.day, rng.choice(range(7, 24)), rng.randint(0, 59), rng.randint(0, 59))


def fmt(v):
    if v is None:
        return ""
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, bool):
        return "true" if v else "false"
    return v


def write_csv(name, rows, columns):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_DIR / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(columns)
        for r in rows:
            w.writerow([fmt(r.get(c)) for c in columns])
    print(f"  {name:<22} {len(rows):>7,} rows")


def main(n_deals):
    rng = random.Random(SEED)
    now = datetime.combine(END_DATE, datetime.min.time()) + timedelta(hours=12)

    # --- dim_pipeline / dim_stage ------------------------------------------
    dim_pipeline, dim_stage, stage_ids = [], [], {}
    sid = 100
    for pid, (pname, stages) in PIPELINES.items():
        dim_pipeline.append({"pipeline_id": pid, "pipeline_name": pname, "pipeline_content": None})
        for s in stages:
            sid += 1
            stage_ids[(pid, s)] = sid
            dim_stage.append({"stage_id": sid, "pipeline_id": pid, "stage_name": s})

    # --- dim_user ------------------------------------------------------------
    dim_user, sales_ids, cs_ids = [], [], []
    uid = 1000
    for title, count in STAFF:
        for _ in range(count):
            uid += 1
            name = fake_name(rng)
            dim_user.append({"user_id": uid, "username": f"user{uid}", "full_name": name,
                             "job_title": title, "email": f"user{uid}@example.com"})
            (cs_ids if "Customer Service" in title else sales_ids).append(uid)

    # --- dim_account -----------------------------------------------------------
    dim_account = []
    for aid in range(1, 41):
        created = rand_datetime(rng, START_DATE, END_DATE)
        dim_account.append({
            "account_id": aid, "account_name": f"Company {aid:03d} JSC",
            "account_address": None, "account_description": None, "brand_name": None,
            "industry": rng.choice(INDUSTRIES), "website": None, "linkedin_profile": None,
            "company_size": rng.choice(COMPANY_SIZES), "created_at": created, "updated_at": created,
        })

    # --- dim_class_schedule ---------------------------------------------------
    dim_class_schedule, classes_by_course = [], {}
    cid = 0
    for course, _ in COURSES:
        d = START_DATE + timedelta(days=rng.randint(10, 40))
        n = 0
        while d <= END_DATE + timedelta(days=60):
            cid += 1
            n += 1
            code = f"{course.split()[1]}{n:02d}"
            dim_class_schedule.append({"class_id": cid, "class_code": code,
                                       "class_start_date": d, "course": course})
            classes_by_course.setdefault(course, []).append((code, d))
            d += timedelta(days=rng.randint(45, 75))

    # --- dim_contact (SCD2: ~5% of contacts get a second version) ---------------
    n_contacts = int(n_deals * 0.85)
    dim_contact, contact_versions = [], {}
    for cid_ in range(1, n_contacts + 1):
        created = rand_datetime(rng, START_DATE, END_DATE)
        base = {
            "contact_id": cid_,
            "account_id": rng.choice(dim_account)["account_id"] if rng.random() < 0.05 else 0,
            "contact_name": fake_name(rng),
            "email": f"contact{cid_}@example.com", "phone": f"09{rng.randint(10_000_000, 99_999_999)}",
            "date_of_birth": str(rng.randint(1985, 2005)) if rng.random() < 0.74 else None,
            "facebook": None, "university": None,
            "location": rng.choice(LOCATIONS), "job_title": rng.choice(JOB_TITLES),
            "created_at": created,
        }
        v1 = dict(base, contact_key=str(uuid.UUID(int=rng.getrandbits(128))),
                  effective_date=created.date(), end_date=None, is_current=True)
        versions = [v1]
        if rng.random() < 0.05 and created.date() < END_DATE - timedelta(days=60):
            change = created.date() + timedelta(days=rng.randint(30, (END_DATE - created.date()).days - 1))
            v1.update(end_date=change, is_current=False)
            v2 = dict(base, contact_key=str(uuid.UUID(int=rng.getrandbits(128))),
                      job_title=rng.choice([j for j in JOB_TITLES if j]),
                      effective_date=change, end_date=None, is_current=True)
            versions.append(v2)
        dim_contact.extend(versions)
        contact_versions[cid_] = versions

    # --- fact_deal + fact_deal_activity --------------------------------------
    fact_deal, fact_activity = [], []
    act_id = 500_000
    course_names = [c for c, _ in COURSES]
    price = dict(COURSES)

    def add_activity(deal_id, owner, when, a_type, content):
        nonlocal act_id
        act_id += 1
        fact_activity.append({"activity_id": act_id, "deal_id": deal_id, "activity_type": a_type,
                              "activity_content": content, "owner_user_id": owner,
                              "created_at": when, "updated_at": when})

    for deal_id in range(10_001, 10_001 + n_deals):
        pid = rng.choices(list(PIPELINE_WEIGHTS), weights=list(PIPELINE_WEIGHTS.values()))[0]
        stages = PIPELINES[pid][1]
        # A deal is created on or after its contact's creation date
        contact_id = rng.randint(1, n_contacts)
        contact_created = contact_versions[contact_id][0]["created_at"]
        created = min(contact_created + timedelta(days=rng.expovariate(1 / 10.0)), now - timedelta(hours=1))
        version = next(v for v in contact_versions[contact_id]
                       if v["effective_date"] <= created.date()
                       and (v["end_date"] is None or created.date() < v["end_date"]))
        owner = rng.choice(cs_ids if pid == 2 else sales_ids)
        course = rng.choices(course_names, weights=COURSE_WEIGHTS)[0]
        age_days = (now - created).days

        # Outcome: recent deals are more likely to still be open
        p_open = 0.65 if age_days < 21 else 0.25 if age_days < 60 else 0.04
        p_won = {1: 0.38, 2: 0.62, 3: 0.80, 4: 0.0}[pid]
        r = rng.random()
        status = "open" if r < p_open else ("won" if rng.random() < p_won else "lost")
        if pid == 4 and status == "won":
            status = "open"

        # How far the deal progressed through the stages
        last = len(stages) - 1
        if status == "won":
            reached = last
        else:
            weights = [max(1, 6 - i) for i in range(last)]
            reached = rng.choices(range(last), weights=weights)[0]
        stage = stages[reached]

        # Stage history as changelog activities, and a cycle time
        t = created
        for i in range(reached + 1):
            if i > 0:
                t += timedelta(days=rng.expovariate(1 / 4.0), hours=rng.randint(1, 8))
                if t > now:
                    t = now - timedelta(hours=1)
                add_activity(deal_id, owner, t, "Thay đổi hệ thống",
                             f"Stage changed: {stages[i-1]} → {stages[i]}")
            if rng.random() < 0.7:
                add_activity(deal_id, owner, t + timedelta(hours=rng.randint(1, 30)),
                             rng.choice(["Cuộc gọi", "Ghi chú", "Email", "Nhật ký hoạt động"]),
                             "Demo activity")
        closed = None
        if status != "open":
            closed = min(t + timedelta(days=rng.randint(0, 5), hours=rng.randint(1, 8)), now)

        lost_reason = None
        if status == "lost":
            lost_reason = rng.choice(LOST_REASONS_BY_STAGE.get(stage, GENERIC_LOST_REASONS)) \
                if pid == 1 else rng.choice(GENERIC_LOST_REASONS)

        src, med, _ = rng.choices(CHANNELS, weights=[c[2] for c in CHANNELS])[0]
        if status == "won" and rng.random() < 0.08:
            src, med = "inbox", "inbox"

        classes = [c for c in classes_by_course.get(course, []) if c[1] >= created.date()]
        class_code = classes[0][0] if classes and rng.random() < 0.8 else None
        value = round(price[course] * rng.choice([1, 1, 1, 0.9, 0.85]), -3) if status == "won" else None

        fact_deal.append({
            "deal_id": deal_id, "contact_key": version["contact_key"],
            "stage_id": stage_ids[(pid, stage)], "owner_user_id": owner,
            "deal_name": f"Deal {deal_id}", "deal_status": status, "deal_value": value,
            "labels": "lead cks" if pid == 1 and status == "open" and rng.random() < 0.05 else None,
            "is_alumni": "Cựu học viên" if rng.random() < 0.03 else None,
            "group_registration": None, "course_selected": course,
            "learning_format": rng.choice(LEARNING_FORMATS), "class_code": class_code,
            "expectation": "Demo expectation" if rng.random() < 0.6 else None,
            "promotion_code": rng.choice(["EARLYBIRD", "REFERRAL", None, None, None]),
            "gift": None, "need_consulting": None, "preferred_consulting_time": None,
            "pain_point_captured": None, "pending_reason": None, "pending_reason_detail": None,
            "has_followup_plan": None, "next_step": None,
            "lost_reason": lost_reason, "lost_reason_detail": None,
            "utm_source": src, "utm_medium": med,
            "utm_content": f"campaign_{rng.randint(1, 12):02d}" if src else None,
            "utm_product": None, "utm_person": None,
            "created_at": created, "updated_at": closed or t, "closed_at": closed,
            "is_test_deal": False,
        })

    print(f"Writing fake data to {OUT_DIR}/")
    write_csv("dim_pipeline", dim_pipeline, ["pipeline_id", "pipeline_name", "pipeline_content"])
    write_csv("dim_stage", dim_stage, ["stage_id", "pipeline_id", "stage_name"])
    write_csv("dim_user", dim_user, ["user_id", "username", "full_name", "job_title", "email"])
    write_csv("dim_account", dim_account, [
        "account_id", "account_name", "account_address", "account_description", "brand_name",
        "industry", "website", "linkedin_profile", "company_size", "created_at", "updated_at"])
    write_csv("dim_contact", dim_contact, [
        "contact_key", "contact_id", "account_id", "contact_name", "email", "phone", "date_of_birth",
        "facebook", "university", "location", "job_title", "created_at",
        "effective_date", "end_date", "is_current"])
    write_csv("dim_class_schedule", dim_class_schedule,
              ["class_id", "class_code", "class_start_date", "course"])
    write_csv("fact_deal", fact_deal, [
        "deal_id", "contact_key", "stage_id", "owner_user_id", "deal_name", "deal_status",
        "deal_value", "labels", "is_alumni", "group_registration", "course_selected",
        "learning_format", "class_code", "expectation", "promotion_code", "gift", "need_consulting",
        "preferred_consulting_time", "pain_point_captured", "pending_reason", "pending_reason_detail",
        "has_followup_plan", "next_step", "lost_reason", "lost_reason_detail", "utm_source",
        "utm_medium", "utm_content", "utm_product", "utm_person", "created_at", "updated_at",
        "closed_at", "is_test_deal"])
    write_csv("fact_deal_activity", fact_activity, [
        "activity_id", "deal_id", "activity_type", "activity_content", "owner_user_id",
        "created_at", "updated_at"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--deals", type=int, default=3000, help="number of fake deals (default 3000)")
    main(parser.parse_args().deals)
