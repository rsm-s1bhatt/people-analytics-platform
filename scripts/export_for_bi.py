"""Export the mart tables to CSV so they can be loaded into Tableau or Power BI."""
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "target" / "people_analytics.duckdb"
OUT = ROOT / "exports"
TABLES = ["fct_hiring_funnel", "fct_time_to_hire", "fct_applications",
          "fct_attrition_by_segment", "dim_employee", "dq_summary"]

OUT.mkdir(exist_ok=True)
con = duckdb.connect(str(DB), read_only=True)
for t in TABLES:
    path = OUT / f"{t}.csv"
    con.sql(f"copy (select * from {t}) to '{path}' (header, delimiter ',')")
    print(f"exported {t} -> exports/{path.name}")
