# GitHub Copilot prompt: Legacy BI Dashboard (Step 2)

**Part of:** v1.0 Base Version, 24 Nov 2026
**Purpose:** rebuild the Step 2 legacy BI dashboard (`legacy_system/bi_dashboard/app.py`) with GitHub Copilot.
**Reference result:** the dashboard in this project, described in `docs/02_Legacy_BI_Dashboard_Guide.md`.

## How to use it

1. Open the `FDE_PB_Sol` folder in VS Code.
2. Open Copilot Chat and switch to **Agent** mode.
3. Optional, so Copilot sees the schema: attach `#file:legacy_system/mysql/scripts/01_create_legacy_schema.sql` and `#file:.env.example`.
4. Paste the whole prompt below.
5. Run the app and work through the **acceptance checks** at the end of the prompt. Copilot's code will not be identical to the reference, but if every number matches, it has built the same dashboard. If one doesn't match, paste that screen's back-end SQL or the error back into Copilot and ask it to fix that page.

> This prompt was written from the tested reference app. It has not been run through Copilot itself, so the acceptance checks are the real test.

## The prompt

```text
Build a small "legacy BI dashboard" in Python with Streamlit. It must look and behave like an OLD business-intelligence tool on top of a legacy database, so I can later contrast it with an AI assistant. Keep the code simple, readable and well commented: a beginner must understand what happens at the back end.

## Context (already exists, do not change it)
- MySQL 8.4 runs in Docker (container fde-mysql) at 127.0.0.1:3306.
- Database `legacy_fleet`, table `TBL_SC_FLEET_HIST_RAW`: 32,065 hourly readings from 2021-01-01 00:00 to 2024-08-29 00:00. There is no truck or shipment ID.
- Cryptic legacy column -> meaning (all numeric columns are DOUBLE):
  TS_UTC (DATETIME) reading time UTC | V_LAT latitude | V_LON longitude | IOT_TEMP_VAL_C cargo temperature °C | CGO_COND_CD cargo condition code | RISK_CLS_TXT (VARCHAR: 'High Risk','Moderate Risk','Low Risk') risk class | DELAY_PROB_DEC delay probability 0-1 | PRT_CNG_LVL port congestion 0-10 | RT_RSK_IDX route risk 0-10 | FUEL_CONS_RT fuel consumption rate | ETA_VAR_HRS ETA variation hours | TRF_CNG_LVL traffic congestion 0-10 | DRV_BHV_SCR driver behaviour 0-1 | DRV_FTG_SCR driver fatigue 0-1 | WX_SEV_IDX stored weather severity 0-1 | DLV_TM_DEV delivery time deviation | SHP_CST_AMT shipping cost.
  The 9 CORE columns are: TS_UTC, V_LAT, V_LON, IOT_TEMP_VAL_C, CGO_COND_CD, RISK_CLS_TXT, DELAY_PROB_DEC, PRT_CNG_LVL, RT_RSK_IDX. The 8 OPS columns are the remaining 8 above.
- Read-only MySQL login `bi_analyst` (SELECT only).
- The project-root `.env` holds MYSQL_HOST, MYSQL_PORT, LEGACY_DB, BI_ANALYST_USER, BI_ANALYST_PASSWORD. Load it with python-dotenv from Path(__file__).resolve().parents[2] / ".env".

## Files to create
1. legacy_system/bi_dashboard/app.py: ONE file with 5 numbered, commented sections: 1 Settings, 2 Database helpers, 3 Login screen, 4 Report pages, 5 Main.
2. legacy_system/bi_dashboard/requirements.txt, pinned: streamlit==1.67.0, pandas==3.1.1, SQLAlchemy==2.1.9, PyMySQL==1.2.4, cryptography==50.0.2, python-dotenv==1.2.4

## Technical rules
- Only Streamlit built-ins: st.metric, st.bar_chart, st.line_chart, st.map, st.dataframe, st.form. No plotly, no st.cache_*, no extra packages.
- st.set_page_config(page_title="Legacy BI Dashboard", page_icon="🚚", layout="wide").
- SQLAlchemy 2: create_engine(URL.create("mysql+pymysql", ...), pool_pre_ping=True). Use text() with named parameters; never put user values into SQL with string formatting (except in the SQL console page).
- Always query the RAW table with its cryptic names. Convert them to readable labels only for display, through one LABELS dict.
- Do not pass use_container_width (deprecated). For informational metric deltas use delta_color="off", delta_arrow="off".

## Login screen
- A form with User ID (prefilled with BI_ANALYST_USER) and Password (type="password"). The user TYPES the password; never read it from .env.
- On submit: connect, run SELECT 1, store the engine and user in st.session_state, then st.rerun(). On failure: st.error("Login failed: <driver error>") plus a hint to check the password in .env and that the fde-mysql container is running.

## Back-end transparency (on every page)
- run_query(purpose, sql, params) executes the query and appends {purpose, sql with the parameter values filled in for display, row count, milliseconds} to a module-level QUERY_LOG list (it resets on every rerun).
- At the bottom of every page: an expander "🔧 What happened at the back end" (expanded when the sidebar checkbox is on). It shows login, server, database and table, then each query with st.code(..., language="sql") and "N row(s) · X ms", then a small table "Legacy column -> Shown as" for every cryptic column that appears in the page's SQL.

## Sidebar
Header "🚚 Fleet BI Dashboard"; caption "Logged in as <user> (read-only)"; a radio with the 5 pages; a checkbox "Show what happens at the back end" (default True); a DISABLED text_input "💬 Ask a question in plain English" with placeholder "Not available in the legacy system"; an expander "⚠️ What this legacy system cannot do" with 6 bullets (plain-English questions, live data such as weather, company SOPs, explanations or suggested actions, audit trail, new questions without new reports or hand-written SQL); a "Log out" button (dispose the engine, clear the session, rerun).

## Pages (each starts with st.title and an st.caption beginning "Legacy note:")
1. "📊 Fleet Overview": one KPI query, then 8 st.metric tiles in 2 rows of 4: Total readings; Years covered (value "2021 – 2024", delta "01 Jan 2021 → 29 Aug 2024"); High Risk readings (percentage, delta = count); Readings above 4 °C (count, delta = % of all); Average cargo temperature; Average delay probability; Average port congestion "x.xx / 10"; Average fuel consumption rate. An st.info saying the average temperature looks safe but hides the readings above 4 °C. Two bar charts side by side: readings per risk class, and readings per temperature band (below 0 / 0 to 4 / above 4 °C). A line chart of the monthly average temperature (DATE_FORMAT(TS_UTC, '%Y-%m')).
2. "🗺️ Where are my trucks?": a form with a date range (default: the last 7 days of data; min/max = the data range), risk class (All/High/Moderate/Low), latitude from/to (30/50), longitude from/to (-120/-70) and a "Run report" button. The end date is inclusive (TS_UTC < end + 1 day). A count query plus the latest 500 rows of the 9 core columns. Show the count as a metric, st.map with dots coloured by risk (High #d62728, Moderate #ff7f0e, Low #2ca02c, size 15000) with a caption legend, and the table.
3. "⚠️ Risk & Delay report": a form with risk class, year (All/2021-2024), month (All/1-12) and three OPTIONAL number_inputs with value=None and placeholder "no limit": cargo temperature above, delay probability above (0-1), port congestion above (0-10). Add a condition ONLY when a value is typed, using a strict ">". Metrics: readings matching all filters; readings for the chosen risk class/year/month; share. A bar chart of matching readings per month, then a table of the latest 100 matches (9 core columns).
4. "🛠️ Truck, route & driver operations": a year select; 8 metric tiles with the averages of the 8 OPS columns; a select box to pick one OPS measure -> line chart of its monthly average.
5. "🧑‍💻 Analyst SQL console": an expander showing DESCRIBE of the table (cryptic names, no descriptions); a text_area prefilled with "SELECT RISK_CLS_TXT, COUNT(*) AS readings FROM TBL_SC_FLEET_HIST_RAW GROUP BY RISK_CLS_TXT;"; a "Run query" button. Execute through a raw DB-API connection (engine.raw_connection(); cursor.execute(sql) with NO parameters, so a % inside the SQL works); first run SET SESSION max_execution_time = 15000; fetchmany(1000); show the result. On error: st.error("MySQL refused the query: <error>"). Record the query in QUERY_LOG.

## Run command (Windows PowerShell first, then macOS), from the project root
Windows: .\venv_legacy\Scripts\python.exe -m streamlit run legacy_system/bi_dashboard/app.py --server.port 8502 --server.address localhost --server.headless true --browser.gatherUsageStats false --client.toolbarMode minimal
macOS:   ./venv_legacy/bin/python -m streamlit run legacy_system/bi_dashboard/app.py --server.port 8502 --server.address localhost --server.headless true --browser.gatherUsageStats false --client.toolbarMode minimal

## Acceptance checks (my data must give exactly these)
- Overview: Total readings 32,065; High Risk 74.7%; above 4 °C 8,674; average temperature 0.04 °C.
- Map: date range 2021/01/01-2024/08/29, latitude 33.3-34.3, longitude -118.6 to -117.6 -> 35 readings; the latest is 2024-08-16 06:00, -9.98 °C, High Risk.
- Map: 2024/08/28-2024/08/29 with the full latitude/longitude box -> 25 readings.
- Risk report: High Risk + temperature above 4 -> 6,455; High Risk + delay above 0.65 -> 15,440; both -> 4,209; port congestion above 7 (all risk classes) -> 19,566.
- Operations: year 2023 -> 8,760 readings.
- SQL console: a DELETE is refused with error 1142.

## Do not
Add AI features, call external APIs, create database views, write to the database, use caching, or add extra pages.

After creating the files, show me the run commands and walk me through the acceptance checks.
```
