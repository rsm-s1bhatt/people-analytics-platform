# People Analytics Data Platform: Hiring Funnel & Attrition

A tested, documented data platform for recruiting and workforce analytics. It is built with dbt on DuckDB and checked automatically by GitHub Actions on every pull request.

It answers two questions People teams ask constantly:

- **Recruiting:** where do candidates drop out of the hiring funnel, how long does hiring take, and how often are offers accepted?
- **Workforce:** where are we losing people, by department, role, tenure and overtime?

It also watches its own inputs. Data-quality models flag gaps in the upstream recruiting system, such as a candidate who skipped a stage, a hire with no offer record, or stage dates out of order, so they can be raised with the system's owners.

## Data

| Source | What it is | Rows |
|---|---|---|
| `data/raw/ibm_hr_attrition.csv` | IBM HR Analytics Employee Attrition sample dataset, from [IBM's GitHub](https://github.com/IBM/employee-attrition-aif360). **IBM created this as fictional sample data for teaching.** | 1,470 employees |
| `data/raw/recruiting_*.csv` | **Synthetic** recruiting funnel made by `scripts/generate_recruiting_funnel.py`. Real candidate-level data is private, so it is generated (seeded, so every run is identical). Requisitions use the same departments and roles as the IBM data. | 123 requisitions, 6,047 applications, 9,285 stage events, 202 offers |

The generator plants a small, known set of data problems: 14 stage skips, 2 hires without an offer, and 5 out-of-order events. The data-quality models are expected to find exactly these, which proves the checks work. They currently do, flagging all 21 and nothing else.

## Pipeline

```
data/raw (CSV)
  └── staging        stg_ibm__employees, stg_recruiting__*        clean, rename, type
       └── intermediate   int_application_stage_dates            one row per application, date per stage
            ├── marts/recruiting   fct_applications, fct_hiring_funnel, fct_time_to_hire
            ├── marts/workforce    dim_employee, fct_attrition_by_segment
            └── data_quality       dq_stage_skips, dq_hires_without_offer, dq_events_out_of_order, dq_summary
```

15 models, 49 data tests.

### Tests

- **Source contracts:** unique and not-null keys, accepted values (for example `Attrition` is only Yes/No, stages come from a fixed list), and referential integrity between applications and requisitions.
- **Business rules:**
  - `assert_funnel_never_widens`: no stage can have more candidates than the stage before it.
  - `assert_headcount_reconciles_to_source`: the attrition mart accounts for every employee, no more and no fewer.
  - `assert_every_hire_has_an_application`: every hired event belongs to a known application.
- **Range checks:** rates between 0 and 1, non-negative pay and tenure, using a custom `accepted_range` test with no external packages.
- **Data-quality checks:** a custom `is_empty` test on each data-quality model, set to **warn**. Upstream gaps are reported in every run without blocking it. Every other test is set to **error**, so a broken model fails the build.

## CI/CD

`.github/workflows/ci.yml` runs on every pull request, on every push to `main`, and every Monday on a schedule:

1. Installs pinned dependencies.
2. Generates the synthetic recruiting data.
3. Runs `dbt build`: every model and every test. **Any error-level test failure fails the run and blocks the pull request.**
4. Prints the data-quality summary.
5. Builds the dbt documentation site. On `main`, it publishes the site to GitHub Pages, with model descriptions, column docs and the lineage graph.

The weekly scheduled run catches upstream data changes even when no one has touched the code.

## Run it locally

```bash
pip install -r requirements.txt
python scripts/generate_recruiting_funnel.py
dbt build --profiles-dir .
dbt docs generate --profiles-dir . && dbt docs serve --profiles-dir .   # browse the docs
python scripts/export_for_bi.py                                        # CSVs for Tableau / Power BI
```

## Dashboard

`scripts/export_for_bi.py` writes the mart tables to `exports/`, and `scripts/build_tableau_workbook.py` packages them into `dashboard/People_Analytics_Dashboard.twbx` (open in Tableau Desktop or upload to Tableau Public). The dashboard covers:

- Hiring funnel: candidates reaching each stage
- Median days to hire and offer acceptance rate by department
- Attrition rate by tenure band, and by department split by overtime
- Data-quality summary: upstream issues flagged by each check

## What the data shows

From the IBM sample data:

- Attrition is highest in an employee's **first year (36%)**, and falls to **8% after 11+ years**.
- **Sales** has the highest attrition (21%), against 14% in Research & Development.

From the synthetic funnel, by design: about 3% of applicants are hired, with a median of 35–42 days from application to hire depending on department.

## Setting up the GitHub repo

1. Create a new public repo and push this folder to it.
2. In the repo's **Settings > Pages**, set the source to **GitHub Actions**.
3. Push to `main`. The workflow runs, goes green, and publishes the docs site.
4. In **Settings > Branches**, add a rule for `main` that requires the `build-and-test` check to pass before merging.
5. To see CI block a bad change: open a pull request that breaks a test, for example by removing a stage from the accepted values list in `models/staging/_sources.yml`. The check fails and the PR can't be merged until it's fixed.
