"""Generate a SYNTHETIC recruiting funnel that sits alongside the IBM HR dataset.

No public dataset exposes real candidate-level recruiting data (it is private by
nature), so this script builds one. It is seeded, so every run produces the same
files, and it is clearly labeled synthetic in the README.

Requisitions are drawn from the departments and job roles in the IBM data, so the
recruiting models join cleanly to the workforce models.

A small number of known data problems are planted on purpose (stage skips, hires
with no offer, events out of order). The data-quality models in dbt are expected
to find exactly these, which is how the pipeline proves its checks work.
"""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

SEED = 42
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
STAGES = ["applied", "recruiter_screen", "hiring_manager_interview", "values_fit_interview", "offer", "hired"]
# Probability of moving from each stage to the next, by job level band.
PASS_RATES = {
    "entry":  [0.30, 0.45, 0.50, 0.55, 0.85],
    "senior": [0.20, 0.40, 0.45, 0.60, 0.80],
}
# Typical days spent waiting before each next stage (min, max).
STAGE_GAP_DAYS = [(2, 9), (3, 12), (4, 14), (2, 10), (3, 15)]
ANOMALY_RATE = {"stage_skip": 0.010, "hire_without_offer": 0.25, "out_of_order": 0.005}


def load_roles():
    with open(RAW / "ibm_hr_attrition.csv", newline="") as f:
        rows = list(csv.DictReader(f))
    roles = {}
    for r in rows:
        key = (r["Department"], r["JobRole"])
        roles[key] = roles.get(key, 0) + 1
    return roles


def main():
    rng = random.Random(SEED)
    roles = load_roles()
    reqs, apps, events, offers = [], [], [], []
    planted = {"stage_skip": 0, "hire_without_offer": 0, "out_of_order": 0}
    req_id = app_id = event_id = offer_id = 0
    start, end = date(2024, 1, 1), date(2025, 12, 31)

    for (dept, role), headcount in sorted(roles.items()):
        band = "senior" if any(k in role for k in ("Manager", "Director")) else "entry"
        n_reqs = max(2, round(headcount / 12))
        for _ in range(n_reqs):
            req_id += 1
            opened = start + timedelta(days=rng.randint(0, (end - start).days - 120))
            reqs.append({"requisition_id": f"REQ{req_id:04d}", "department": dept, "job_role": role,
                         "level_band": band, "opened_date": opened.isoformat()})
            n_apps = rng.randint(25, 90) if band == "entry" else rng.randint(12, 40)
            for _ in range(n_apps):
                app_id += 1
                aid = f"APP{app_id:06d}"
                applied = opened + timedelta(days=rng.randint(0, 45))
                apps.append({"application_id": aid, "requisition_id": f"REQ{req_id:04d}",
                             "candidate_id": f"CAND{rng.randint(1, 9000):05d}",
                             "source": rng.choices(["referral", "job_board", "career_site", "agency", "campus"],
                                                   weights=[15, 35, 30, 10, 10])[0],
                             "applied_date": applied.isoformat()})
                # Walk the candidate through the funnel.
                reached = [("applied", applied)]
                current = applied
                for i, p in enumerate(PASS_RATES[band]):
                    if rng.random() > p:
                        break
                    lo, hi = STAGE_GAP_DAYS[i]
                    current = current + timedelta(days=rng.randint(lo, hi))
                    reached.append((STAGES[i + 1], current))
                names = [s for s, _ in reached]

                # Planted anomaly 1: a candidate skips the recruiter screen.
                if "hiring_manager_interview" in names and rng.random() < ANOMALY_RATE["stage_skip"]:
                    reached = [x for x in reached if x[0] != "recruiter_screen"]
                    planted["stage_skip"] += 1
                # Planted anomaly 2: a hire with no offer record (offer event dropped).
                drop_offer = "hired" in names and rng.random() < ANOMALY_RATE["hire_without_offer"] / 10
                if drop_offer:
                    reached = [x for x in reached if x[0] != "offer"]
                    planted["hire_without_offer"] += 1
                # Planted anomaly 3: timestamps out of order.
                if len(reached) >= 3 and rng.random() < ANOMALY_RATE["out_of_order"]:
                    s, d = reached[-1]
                    reached[-1] = (s, reached[-2][1] - timedelta(days=rng.randint(1, 5)))
                    planted["out_of_order"] += 1

                for stage, d in reached:
                    event_id += 1
                    events.append({"event_id": f"EVT{event_id:07d}", "application_id": aid,
                                   "stage": stage, "event_date": d.isoformat()})
                if "offer" in [s for s, _ in reached]:
                    offer_id += 1
                    offer_date = dict(reached)["offer"]
                    offers.append({"offer_id": f"OFR{offer_id:05d}", "application_id": aid,
                                   "offer_date": offer_date.isoformat(),
                                   "status": "accepted" if "hired" in names else "declined"})

    for name, rows in [("requisitions", reqs), ("applications", apps), ("stage_events", events), ("offers", offers)]:
        path = RAW / f"recruiting_{name}.csv"
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"wrote {len(rows):>6} rows -> {path.name}")
    print("planted data problems (dbt data-quality models should flag these):", planted)


if __name__ == "__main__":
    main()
