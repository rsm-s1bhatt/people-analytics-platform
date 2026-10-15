"""Build the People Analytics Tableau workbook (dashboard/People_Analytics_Dashboard.twbx)
from the CSVs that scripts/export_for_bi.py writes to exports/.

The workbook is generated as XML so the dashboard is reproducible from code, like the rest
of the pipeline. Open the .twbx in Tableau Desktop or upload it to Tableau Public.
"""
import csv
import zipfile
from pathlib import Path
from xml.sax.saxutils import quoteattr as qa, escape

ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "exports"
OUTDIR = ROOT / "dashboard"
OUTDIR.mkdir(exist_ok=True)

INK, MUTED, BAR, RED, PALE, BG, HEAD = "#171A20", "#6B7280", "#3E4451", "#E31937", "#F3D3D9", "#F4F5F7", "#171A20"
FONT = "Tableau Book"

TABLES = {
    "dim_employee": "Employees",
    "fct_applications": "Applications",
    "fct_hiring_funnel": "Hiring Funnel",
    "fct_time_to_hire": "Time to Hire",
    "dq_summary": "Data Quality",
}
CAPTIONS = {
    "candidates_reached": "Candidates", "median_days_to_hire": "Median days to hire",
    "offer_acceptance_rate": "Offer acceptance", "department": "Department", "tenure_band": "Tenure",
    "flagged_records": "Records flagged",
}
# (name, datatype, formula, role, type)
CALCS = {
    "dim_employee": [
        ("Headcount", "integer", "COUNT([employee_id])", "measure", "quantitative"),
        ("Attrition Rate", "real", "SUM(IIF([has_left],1,0)) / COUNT([employee_id])", "measure", "quantitative"),
        ("First Year Attrition", "real",
         "SUM(IIF([years_at_company] < 1 AND [has_left],1,0)) / SUM(IIF([years_at_company] < 1,1,0))", "measure", "quantitative"),
        ("Overtime", "string", "IIF([works_overtime],'Overtime','No overtime')", "dimension", "nominal"),
        ("Dept", "string", "REPLACE([department],'Research & Development','R&D')", "dimension", "nominal"),
        ("Overtime Flag", "integer", "MIN(IIF([works_overtime],1,0))", "measure", "quantitative"),
    ],
    "fct_applications": [
        ("Applicants", "integer", "COUNT([application_id])", "measure", "quantitative"),
        ("Hire Rate", "real", "SUM(IIF([was_hired],1,0)) / COUNT([application_id])", "measure", "quantitative"),
        ("Median Days to Hire", "real", "MEDIAN([days_to_hire])", "measure", "quantitative"),
        ("Source", "string", "PROPER(REPLACE([application_source],'_',' '))", "dimension", "nominal"),
    ],
    "fct_hiring_funnel": [
        ("Stage", "string",
         "STR([stage_order]) + '. ' + PROPER(REPLACE(REPLACE(REPLACE([stage],'hiring_manager','manager'),'_interview',' interview'),'_',' '))",
         "dimension", "nominal"),
        ("Share of Applicants", "real",
         "SUM([candidates_reached]) / MIN({FIXED : SUM(IIF([stage_order] = 1, [candidates_reached], 0))})",
         "measure", "quantitative"),
    ],
    "fct_time_to_hire": [
        ("Dept", "string", "REPLACE([department],'Research & Development','R&D')", "dimension", "nominal"),
        ("Department ", "string",
         "REPLACE(REPLACE([department],'Research & Development','R&D'),'Human Resources','HR') + '  (' + STR(ROUND([offer_acceptance_rate]*100)) + '% accept)'",
         "dimension", "nominal"),
    ],
    "dq_summary": [
        ("Check", "string", "PROPER(REPLACE([check_name],'_',' '))", "dimension", "nominal"),
    ],
}
# discrete colour maps, applied at the data-source level
COLOR_MAPS = {"dim_employee": {"Overtime": {"Overtime": RED, "No overtime": "#B8BCC4"}}}


def infer(vals):
    v = [x for x in vals if x != ""]
    if v and all(x in ("true", "false") for x in v):
        return "boolean"
    for t, f in (("integer", int), ("real", float)):
        try:
            [f(x) for x in v]
            return t
        except ValueError:
            pass
    if v and all(len(x) == 10 and x[4] == "-" for x in v):
        return "date"
    return "string"


DS = {}
for t in TABLES:
    rows = list(csv.reader(open(EXP / f"{t}.csv")))
    DS[t] = [(h, infer([r[i] for r in rows[1:]])) for i, h in enumerate(rows[0])]


def calc_id(n):
    return "Calc_" + n.replace(" ", "_")


def field(t, name):
    """Return (internal name, datatype, role, type, formula|None, caption|None)."""
    for n, dt, f, r, ty in CALCS.get(t, []):
        if n == name:
            return calc_id(n), dt, r, ty, f, n
    dt = dict(DS[t])[name]
    r, ty = (("measure", "quantitative") if dt in ("integer", "real") else ("dimension", "nominal"))
    return name, dt, r, ty, None, CAPTIONS.get(name)


def inst(t, name, agg):
    n = field(t, name)[0]
    key = {"none": ("none", "nk", "None", "nominal"), "user": ("usr", "qk", "User", "quantitative"),
           "sum": ("sum", "qk", "Sum", "quantitative")}[agg]
    return n, f"[{key[0]}:{n}:{key[1]}]", key[2], key[3]


def ref(t, name, agg):
    return f"[federated.{t}].{inst(t, name, agg)[1]}"


def datasource(t):
    cols = DS[t]
    x = f"<datasource caption={qa(TABLES[t])} inline='true' name='federated.{t}' version='18.1'>"
    x += "<connection class='federated'><named-connections>"
    x += (f"<named-connection caption={qa(t)} name='textscan.{t}'><connection class='textscan' "
          f"directory='Data/exports' filename='{t}.csv' password='' server='' /></named-connection></named-connections>")
    x += (f"<relation connection='textscan.{t}' name='{t}.csv' table='[{t}#csv]' type='table'>"
          "<columns character-set='UTF-8' header='yes' locale='en_US' separator=','>")
    x += "".join(f"<column datatype='{dt}' name={qa(c)} ordinal='{i}' />" for i, (c, dt) in enumerate(cols))
    x += "</columns></relation><metadata-records>"
    rt = {"integer": 20, "real": 5, "string": 129, "boolean": 11, "date": 7}
    for i, (c, dt) in enumerate(cols):
        x += (f"<metadata-record class='column'><remote-name>{c}</remote-name><remote-type>{rt[dt]}</remote-type>"
              f"<local-name>[{c}]</local-name><parent-name>[{t}.csv]</parent-name><remote-alias>{c}</remote-alias>"
              f"<ordinal>{i}</ordinal><local-type>{dt}</local-type><contains-null>true</contains-null></metadata-record>")
    x += "</metadata-records></connection>"
    for c, dt in cols:
        _, _, r, ty, _, cap = field(t, c)
        if c.endswith("_id") or c in ("stage_order", "job_level", "furthest_stage_order"):
            r, ty = "dimension", ("ordinal" if dt != "string" else "nominal")
        x += f"<column{' caption=' + qa(cap) if cap else ''} datatype='{dt}' name='[{c}]' role='{r}' type='{ty}' />"
    for n, dt, f, r, ty in CALCS.get(t, []):
        x += (f"<column caption={qa(n)} datatype='{dt}' name='[{calc_id(n)}]' role='{r}' type='{ty}'>"
              f"<calculation class='tableau' formula={qa(f)} /></column>")
    if False:
        x += "<style><style-rule element='mark'>"
        for fname, m in COLOR_MAPS[t].items():
            x += f"<encoding attr='color' field='{inst(t, fname, 'none')[1]}' type='palette'>"
            x += "".join(f"<map to='{c}'><bucket>&quot;{escape(v)}&quot;</bucket></map>" for v, c in m.items())
            x += "</encoding>"
        x += "</style-rule></style>"
    x += "</datasource>"
    return x


def run(text, size=10, color=INK, bold=False):
    return (f"<run fontcolor='{color}' fontname={qa(FONT)} fontsize='{size}'"
            f"{' bold=' + qa('true') if bold else ''}>{escape(text)}</run>")


BR = "<run>Æ&#10;</run>"


def worksheet(name, t, *, rows=(), cols=(), mark="Bar", color=None, color_cont=None, text=(), label_runs=None,
              fmt=(), mark_color=None, palette=("#FCE8EB", RED), hide_axis=None, title=None, subtitle=None, sort=None, size=None):
    used = list(rows) + list(cols) + ([color] if color else []) + ([color_cont] if color_cont else []) + list(text)
    deps, seen = "", set()
    for nm, agg in used:
        n, dt, r, ty, f, cap = field(t, nm)
        if n not in seen:
            seen.add(n)
            capx = f" caption={qa(cap)}" if cap else ""
            body = f"<calculation class='tableau' formula={qa(f)} />" if f else ""
            deps += f"<column{capx} datatype='{dt}' name='[{n}]' role='{r}' type='{ty}'>{body}</column>"
        _, iname, der, ity = inst(t, nm, agg)
        if f"ci:{iname}" not in seen:
            seen.add(f"ci:{iname}")
            deps += f"<column-instance column='[{n}]' derivation='{der}' name='{iname}' pivot='key' type='{ity}' />"
    R = lambda fa: ref(t, *fa)
    style = (f"<style-rule element='worksheet'><format attr='font-family' value={qa(FONT)} />"
             f"<format attr='font-size' value='9' /><format attr='color' value='{INK}' /></style-rule>"
             "<style-rule element='gridline'><format attr='line-visibility' scope='rows' value='off' />"
             "<format attr='line-visibility' scope='cols' value='off' /></style-rule>"
             "<style-rule element='zeroline'><format attr='line-visibility' value='off' /></style-rule>"
             "<style-rule element='table-div'><format attr='line-visibility' scope='rows' value='off' />"
             "<format attr='line-visibility' scope='cols' value='off' /></style-rule>")
    if fmt:
        for el in ("cell", "axis", "label"):
            style += f"<style-rule element='{el}'>" + "".join(
                f"<format attr='text-format' field='{R(fa)}' value='{v}' />" for fa, v in fmt) + "</style-rule>"
    if hide_axis:
        style += (f"<style-rule element='axis'><format attr='display' class='0' field='{R(hide_axis)}' "
                  f"scope='cols' value='false' /></style-rule>")
    if size:
        style += f"<style-rule element='header'><format attr='width' field='{R(size[0])}' value='{size[1]}' /></style-rule>"
    enc = ""
    if color:
        enc += f"<color column='{R(color)}' />"
    if color_cont:
        enc += f"<color column='{R(color_cont)}' />"
    for tf in text:
        enc += f"<text column='{R(tf)}' />"
    pstyle = "<style-rule element='mark'>"
    if text:
        pstyle += "<format attr='mark-labels-show' value='true' />"
    if mark_color:
        pstyle += f"<format attr='mark-color' value='{mark_color}' />"
    if mark == "Square":
        pstyle += "<format attr='mark-labels-cull' value='false' />"
    pstyle += "</style-rule>"
    if color_cont:
        style += (f"<style-rule element='mark'><encoding attr='color' field='{R(color_cont)}' type='custom-interpolated'>"
                  f"<color-palette custom='true' name='' type='ordered-sequential'><color>{palette[0]}</color>"
                  f"<color>{palette[1]}</color></color-palette></encoding></style-rule>")
    if color and color[0] in COLOR_MAPS.get(t, {}):
        style += f"<style-rule element='mark'><encoding attr='color' field='{R(color)}' type='palette'>"
        style += "".join(f"<map to='{c}'><bucket>&quot;{escape(v)}&quot;</bucket></map>" for v, c in COLOR_MAPS[t][color[0]].items())
        style += "</encoding></style-rule>"
    customized = f"<customized-label><formatted-text>{label_runs}</formatted-text></customized-label>" if label_runs else ""
    sorts = ""
    if sort:
        dim, meas, direction = sort
        sorts = f"<sort class='computed' column='{R(dim)}' direction='{direction}' using='{R(meas)}' />"
    x = f"<worksheet name={qa(name)}>"
    if title:
        x += "<layout-options><title><formatted-text>" + run(title, 11, INK, True)
        if subtitle:
            x += BR + run(subtitle, 8, MUTED)
        x += "</formatted-text></title></layout-options>"
    x += (f"<table><view><datasources><datasource caption={qa(TABLES[t])} name='federated.{t}' /></datasources>"
          f"<datasource-dependencies datasource='federated.{t}'>{deps}</datasource-dependencies>"
          f"{sorts}<aggregation value='true' /></view>")
    x += f"<style>{style}</style>"
    x += (f"<panes><pane selection-relaxation-option='selection-relaxation-allow'><view><breakdown value='auto' /></view>"
          f"<mark class='{mark}' /><mark-sizing mark-sizing-setting='marks-scaling-off' />"
          f"<encodings>{enc}</encodings>{customized}<style>{pstyle}</style></pane></panes>")
    x += f"<rows>{' / '.join(R(r) for r in rows)}</rows><cols>{' / '.join(R(c) for c in cols)}</cols></table></worksheet>"
    return x


def kpi(name, t, measure, label, fmtv, color=INK, note=""):
    lr = (run(label.upper(), 8, MUTED, True) + BR +
          f"<run bold='true' fontcolor='{color}' fontname={qa(FONT)} fontsize='22'>&lt;{ref(t, measure, 'user')}&gt;</run>")
    if note:
        lr += BR + run(note, 8, MUTED)
    return worksheet(name, t, mark="Text", text=[(measure, "user")], label_runs=lr, fmt=[((measure, "user"), fmtv)])


PCT, INT, ONE = "p0%", "n#,##0;-#,##0", "n#,##0.0;-#,##0.0"
PCT1 = "p0.0%"
E, A, F, T, Q = "dim_employee", "fct_applications", "fct_hiring_funnel", "fct_time_to_hire", "dq_summary"

kpis = [
    kpi("KPI Headcount", E, "Headcount", "Headcount", INT, note="employees"),
    kpi("KPI Attrition", E, "Attrition Rate", "Attrition", PCT1, note="left the company"),
    kpi("KPI First Year", E, "First Year Attrition", "First-year attrition", PCT, RED, "of employees under 1 year"),
    kpi("KPI Applicants", A, "Applicants", "Applicants", INT, note="applications"),
    kpi("KPI Hire Rate", A, "Hire Rate", "Hire rate", PCT1, note="of applicants hired"),
    kpi("KPI Days", A, "Median Days to Hire", "Median days to hire", "n#,##0;-#,##0", note="application to hire"),
]
sheets = kpis + [
    worksheet("Funnel", F, rows=[("Stage", "none")], cols=[("candidates_reached", "sum")],
              text=[("candidates_reached", "sum"), ("Share of Applicants", "user")],
              label_runs=(f"<run fontname={qa(FONT)} fontsize='9' fontcolor='{INK}' bold='true'>&lt;{ref(F, 'candidates_reached', 'sum')}&gt;</run>"
                          f"<run fontname={qa(FONT)} fontsize='9' fontcolor='{MUTED}'>  (&lt;{ref(F, 'Share of Applicants', 'user')}&gt;)</run>"),
              fmt=[(("Share of Applicants", "user"), PCT1), (("candidates_reached", "sum"), INT)],
              mark_color=BAR, hide_axis=("candidates_reached", "sum"),
              title="Hiring funnel", subtitle="Candidates reaching each stage, and share of all applicants"),
    worksheet("Attrition Heatmap", E, rows=[("Dept", "none")], cols=[("tenure_band", "none")], mark="Square",
              color_cont=("Attrition Rate", "user"), text=[("Attrition Rate", "user")], fmt=[(("Attrition Rate", "user"), PCT)],
              title="Where people leave", subtitle="Attrition rate by department and tenure"),
    worksheet("Overtime", E, rows=[("Dept", "none"), ("Overtime", "none")], cols=[("Attrition Rate", "user")],
              color_cont=("Overtime Flag", "user"), palette=("#B8BCC4", RED), text=[("Attrition Rate", "user")], fmt=[(("Attrition Rate", "user"), PCT)],
              hide_axis=("Attrition Rate", "user"),
              title="Overtime and attrition", subtitle="Attrition rate by department; red = works overtime"),
    worksheet("Source", A, rows=[("Source", "none")], cols=[("Hire Rate", "user")], text=[("Hire Rate", "user")],
              fmt=[(("Hire Rate", "user"), PCT1)], mark_color=BAR, hide_axis=("Hire Rate", "user"),
              sort=(("Source", "none"), ("Hire Rate", "user"), "DESC"),
              title="Hire rate by source", subtitle="Share of applicants hired, by channel"),
    worksheet("Time to Hire", T, rows=[("Department ", "none")], cols=[("median_days_to_hire", "sum")],
              text=[("median_days_to_hire", "sum")],
              label_runs=f"<run fontname={qa(FONT)} fontsize='9' fontcolor='{INK}' bold='true'>&lt;{ref(T, 'median_days_to_hire', 'sum')}&gt; days</run>",
              fmt=[(("median_days_to_hire", "sum"), "n#,##0;-#,##0")],
              mark_color=BAR, hide_axis=("median_days_to_hire", "sum"),
              title="Speed and close rate", subtitle="Median days to hire and offer acceptance"),
    worksheet("Data Quality", Q, rows=[("Check", "none")], cols=[("flagged_records", "sum")],
              text=[("flagged_records", "sum")], mark_color=RED, hide_axis=("flagged_records", "sum"),
              title="Pipeline data checks", subtitle="Upstream records flagged by the dbt tests"),
]
names = [s.split("name=", 1)[1].split(">", 1)[0].strip("'\"") for s in sheets]

# ---------- dashboard layout (fixed 1300 x 900) ----------
DW, DH = 1200, 880
U = lambda px, total: round(px / total * 100000)
zones, zid = [], [10]


def zone(x, y, w, h, *, name=None, ztype=None, content="", bg="#FFFFFF", margin=6, pad=8):
    zid[0] += 1
    attrs = f"h='{U(h, DH)}' id='{zid[0]}' w='{U(w, DW)}' x='{U(x, DW)}' y='{U(y, DH)}'"
    if name:
        attrs += f" name={qa(name)}"
    if ztype:
        attrs += f" type-v2='{ztype}'"
    if name and not ztype:
        attrs += " show-title='true'" if not name.startswith("KPI") else " show-title='false'"
    style = (f"<zone-style><format attr='border-color' value='#E5E7EB' /><format attr='border-style' value='solid' />"
             f"<format attr='border-width' value='1' /><format attr='margin' value='{margin}' />"
             f"<format attr='padding' value='{pad}' /><format attr='background-color' value='{bg}' /></zone-style>")
    if bg == HEAD:
        style = (f"<zone-style><format attr='border-style' value='none' /><format attr='margin' value='0' />"
                 f"<format attr='padding' value='12' /><format attr='background-color' value='{bg}' /></zone-style>")
    zones.append(f"<zone {attrs}>{content}{style}</zone>")


# header band
zone(0, 0, DW, 88, ztype="text", bg=HEAD, content="<formatted-text>" +
     run("People Analytics  |  Hiring & Retention", 20, "#FFFFFF", True) + BR +
     run("Workforce: IBM HR sample dataset (fictional, 1,470 employees).  Recruiting: synthetic funnel (6,047 applications).  "
         "Built on a tested dbt pipeline; CI runs 49 data tests on every change.", 9, "#AEB4BE") + "</formatted-text>")
# KPI row
kx, ky, kw, kh = 6, 92, (DW - 12) / 6, 104
for i, n in enumerate(names[:6]):
    zone(kx + i * kw, ky, kw, kh, name=n)
# row A
ay, ah = 198, 334
zone(6, ay, 430, ah, name="Funnel")
zone(436, ay, 400, ah, name="Attrition Heatmap")
insights = ("<formatted-text>" + run("WHAT THIS TELLS US", 9, RED, True) + BR + BR +
            run("Retention risk is front-loaded.", 10, INK, True) + BR +
            run("36% of first-year employees leave (n=44), over 4x the 8% rate after 11+ years. Onboarding is the highest-leverage window.", 9, INK) + BR + BR +
            run("Overtime triples attrition.", 10, INK, True) + BR +
            run("31% of employees on overtime leave vs 10% without; Sales on overtime peaks at 38%.", 9, INK) + BR + BR +
            run("The screen is the biggest filter.", 10, INK, True) + BR +
            run("Only 29% of applicants pass the recruiter screen; 2.8% are hired. Referrals convert at about 2x campus.", 9, INK) + BR + BR +
            run("The numbers are trusted.", 10, INK, True) + BR +
            run("Every refresh is tested; 21 source issues flagged.", 9, INK) +
            "</formatted-text>")
zone(836, ay, 358, ah, ztype="text", content=insights, pad=14)
# row B
by, bh = 534, 340
zone(6, by, 340, bh, name="Overtime")
zone(346, by, 290, bh, name="Source")
zone(636, by, 290, bh, name="Time to Hire")
zone(926, by, 268, bh, name="Data Quality")

dash = ("<dashboards><dashboard name='People Analytics'>"
        f"<style><style-rule element='table'><format attr='background-color' value='{BG}' /></style-rule></style>"
        f"<size maxheight='{DH}' maxwidth='{DW}' minheight='{DH}' minwidth='{DW}' sizing-mode='fixed' />"
        "<zones><zone h='100000' id='1' type-v2='layout-basic' w='100000' x='0' y='0'>" + "".join(zones) +
        "</zone></zones></dashboard></dashboards>")
wins = "<windows>" + "".join(
    f"<window class='worksheet' name={qa(n)}><cards><edge name='left'><strip size='160'><card type='pages' />"
    "<card type='filters' /><card type='marks' /></strip></edge><edge name='top'><strip size='2147483647'>"
    "<card type='columns' /></strip><strip size='2147483647'><card type='rows' /></strip><strip size='31'>"
    "<card type='title' /></strip></edge></cards></window>" for n in names) + (
    "<window class='dashboard' maximized='true' name='People Analytics'><viewpoints>" +
    "".join(f"<viewpoint name={qa(n)}><zoom type='{'entire-view' if (n.startswith('KPI') or n == 'Attrition Heatmap') else 'fit-width'}' /></viewpoint>" for n in names) + "</viewpoints><active id='-1' /></window></windows>")

xml = ("<?xml version='1.0' encoding='utf-8' ?>\n<workbook original-version='18.1' source-build='2025.2.0 (20252.25.0101.0000)' "
       "source-platform='mac' version='18.1' xmlns:user='http://www.tableausoftware.com/xml/user'>\n"
       "<datasources>" + "".join(datasource(t) for t in TABLES) + "</datasources>\n<worksheets>" + "".join(sheets) +
       "</worksheets>\n" + dash + wins + "</workbook>\n")
twb = OUTDIR / "People_Analytics.twb"
twb.write_text(xml)
with zipfile.ZipFile(OUTDIR / "People_Analytics_Dashboard.twbx", "w", zipfile.ZIP_DEFLATED) as z:
    z.write(twb, "People_Analytics.twb")
    for t in TABLES:
        z.write(EXP / f"{t}.csv", f"Data/exports/{t}.csv")
twb.unlink()
print("wrote dashboard/People_Analytics_Dashboard.twbx")
