// LLD v1.0 - Legacy fleet system (Harborline Cold Chain, fictional)
const L = require("./doclib");
const { p, bullets, table, figure, note, code, h1, h2, h3, caption } = L;
const IMG = "/home/claude/legacy_docs/assets/docimg/";
const OUT = process.argv[2];

const meta = {
  client: "Harborline Cold Chain (fictional)", system: "Legacy Fleet System", title: "Low-Level Design (LLD)",
  short: "LLD v1.0",
  tagline: "Files, database objects, the data load, the BI dashboard, error handling and tests of the v1.0 replica.",
  fields: [
    ["Document", "Low-Level Design (LLD)"], ["Version", "1.0 (v1.0 Base Version)"], ["Date", "24 November 2026"],
    ["Status", "Baseline, for review"], ["Prepared by", "Forward Deployed Engineer (FDE)"],
    ["Code baseline", "FDE_PB_Sol v1.0 Base Version (snapshot releases/FDE_PB_Sol_v1.0_Base.zip)"],
    ["Companion documents", "HLD v1.0 · Business Proposal v1.0 · Overview deck v1.0 · docs/01 and docs/02 setup guides"],
  ],
};

const COLS = [
  ["–", "REC_ID", "BIGINT UNSIGNED, PK, auto", "(system)", "Row number; not a shipment ID", "system"],
  ["1", "TS_UTC", "DATETIME NOT NULL, indexed", "timestamp", "Reading time (UTC)", "core"],
  ["2", "V_LAT", "DOUBLE", "vehicle_gps_latitude", "Latitude", "core"],
  ["3", "V_LON", "DOUBLE", "vehicle_gps_longitude", "Longitude", "core"],
  ["4", "FUEL_CONS_RT", "DOUBLE", "fuel_consumption_rate", "Fuel consumption rate", "ops"],
  ["5", "ETA_VAR_HRS", "DOUBLE", "eta_variation_hours", "ETA variation (hours)", "ops"],
  ["6", "TRF_CNG_LVL", "DOUBLE", "traffic_congestion_level", "Traffic congestion (0–10)", "ops"],
  ["7", "WH_INV_LVL", "DOUBLE", "warehouse_inventory_level", "Warehouse inventory level", "other"],
  ["8", "LD_ULD_TM", "DOUBLE", "loading_unloading_time", "Loading / unloading time", "other"],
  ["9", "HDL_EQP_AVL", "DOUBLE", "handling_equipment_availability", "Handling equipment availability", "other"],
  ["10", "ORD_FUL_STS", "DOUBLE", "order_fulfillment_status", "Order fulfilment status", "other"],
  ["11", "WX_SEV_IDX", "DOUBLE", "weather_condition_severity", "Stored weather severity (0–1)", "ops"],
  ["12", "PRT_CNG_LVL", "DOUBLE", "port_congestion_level", "Port congestion (0–10)", "core"],
  ["13", "SHP_CST_AMT", "DOUBLE", "shipping_costs", "Shipping cost", "ops"],
  ["14", "SUP_REL_SCR", "DOUBLE", "supplier_reliability_score", "Supplier reliability", "other"],
  ["15", "LEAD_TM_DAYS", "DOUBLE", "lead_time_days", "Lead time (days)", "other"],
  ["16", "HIST_DMD_QTY", "DOUBLE", "historical_demand", "Historical demand", "other"],
  ["17", "IOT_TEMP_VAL_C", "DOUBLE", "iot_temperature", "Cargo temperature (°C)", "core"],
  ["18", "CGO_COND_CD", "DOUBLE", "cargo_condition_status", "Cargo condition code", "core"],
  ["19", "RT_RSK_IDX", "DOUBLE", "route_risk_level", "Route risk (0–10)", "core"],
  ["20", "CUST_CLR_TM", "DOUBLE", "customs_clearance_time", "Customs clearance time", "other"],
  ["21", "DRV_BHV_SCR", "DOUBLE", "driver_behavior_score", "Driver behaviour (0–1)", "ops"],
  ["22", "DRV_FTG_SCR", "DOUBLE", "fatigue_monitoring_score", "Driver fatigue (0–1)", "ops"],
  ["23", "DSRP_LKH_SCR", "DOUBLE", "disruption_likelihood_score", "Disruption likelihood", "other"],
  ["24", "DELAY_PROB_DEC", "DOUBLE", "delay_probability", "Delay probability (0–1)", "core"],
  ["25", "RISK_CLS_TXT", "VARCHAR(50)", "risk_classification", "Risk class", "core"],
  ["26", "DLV_TM_DEV", "DOUBLE", "delivery_time_deviation", "Delivery time deviation", "ops"],
  ["–", "SYS_INGEST_FLAG", "CHAR(1) NOT NULL DEFAULT 'Y'", "(system)", "Row came from the batch load", "system"],
  ["–", "SYS_LOAD_TS", "DATETIME DEFAULT CURRENT_TIMESTAMP", "(system)", "When the row was loaded (UTC)", "system"],
];

const body = [
  ...L.cover(meta),
  ...L.docControl([["1.0", "24 Nov 2026", "Baseline", "First version, written from the v1.0 Base Version code. Values marked captured were produced by running the code against the real CSV."]]),
  ...L.contents(["1. Introduction", "2. Code and file structure", "3. Runtime model", "4. Database design", "5. Data load design",
    "6. Configuration", "7. BI dashboard design", "8. Error handling", "9. Testing", "10. Operations command reference",
    "11. Known limitations", "12. Suggested code comments", "Appendix A. CSV header order", "Appendix B. Diagram sources"]),

  h1("1. Introduction"),
  p("This document describes the v1.0 replica of Harborline's legacy fleet system file by file, so that a developer can run, maintain or extend it without reading all the code first. The HLD explains the system and its pain points; this document goes one level deeper."),
  h2("1.1 Conventions"),
  ...bullets([
    "**Windows first.** Commands are given for Windows PowerShell first, then macOS Terminal.",
    "Paths are relative to the project folder `Documents\\FDE_PB_Sol` (macOS: `~/Documents/FDE_PB_Sol`).",
    "**Captured** means the value or output was produced by running the code; **illustrative** means a typical value.",
    "Names in `code` style are exact file, table, column, function or setting names.",
  ]),

  h1("2. Code and file structure"),
  ...code(`FDE_PB_Sol/
├── .env.example / .env          settings template / private settings (git-ignored)
├── .gitignore / .gitattributes  secrets out of git / LF endings for container scripts
├── VERSION / CHANGELOG.md       1.0 Base Version
├── data/raw/                    dynamic_supply_chain_logistics_dataset.csv (never modified)
├── legacy_system/
│   ├── docker-compose.yml       container fde-mysql
│   ├── create_env.ps1 / .sh     create .env (Windows / macOS)
│   ├── mysql/scripts/           run inside the container
│   │   ├── run_sql.sh
│   │   ├── 01_create_legacy_schema.sql
│   │   ├── 02_create_bi_analyst.sh
│   │   ├── 03_load_legacy_data.sql
│   │   └── 04_verify_load.sql
│   └── bi_dashboard/
│       ├── app.py               Streamlit BI dashboard
│       └── requirements.txt
├── docs/                        guides, prompts, images, design documents
└── releases/                    v1.0 snapshot + SHA-256 manifest`),
  caption("Table", "Files of the legacy system"),
  table(["File", "Lines", "Runs on", "Purpose"], [
    ["`legacy_system/docker-compose.yml`", "57", "Docker", "Container, ports, mounts, health check, server options"],
    ["`legacy_system/create_env.ps1`", "105", "Windows", "Create `.env` with hidden, validated prompts"],
    ["`legacy_system/create_env.sh`", "89", "macOS", "The same for macOS (bash 3.2)"],
    ["`mysql/scripts/run_sql.sh`", "33", "Container", "Run a SQL file as root without showing the password"],
    ["`mysql/scripts/01_create_legacy_schema.sql`", "64", "Container", "Database and the 29-column table"],
    ["`mysql/scripts/02_create_bi_analyst.sh`", "27", "Container", "Read-only login `bi_analyst`"],
    ["`mysql/scripts/03_load_legacy_data.sql`", "75", "Container", "Empty the table and load the CSV"],
    ["`mysql/scripts/04_verify_load.sql`", "118", "Container", "13-point PASS/FAIL check"],
    ["`bi_dashboard/app.py`", "439", "Python 3.12", "BI dashboard: login, five screens, back-end panel"],
    ["`bi_dashboard/requirements.txt`", "8", "pip", "Six pinned packages"],
  ], [2.6, 0.6, 1, 2.6]),

  h1("3. Runtime model"),
  ...figure(IMG + "d2_as_built.png", "Runtime components of the replica", 6.2),
  caption("Table", "Processes and ports"),
  table(["Process", "Started by", "Listens on", "Talks to"], [
    ["MySQL 8.4 (`mysqld`) in container `fde-mysql`", "`docker compose … up -d --wait`", "127.0.0.1:3306", "Volume `fde_mysql_data`"],
    ["Set-up scripts (`sh`, `mysql` client)", "`docker exec fde-mysql …`", "—", "MySQL through its socket, as root"],
    ["Streamlit server (`app.py`)", "`python -m streamlit run …`", "localhost:8502", "MySQL as `bi_analyst` (TCP)"],
    ["Browser", "The analyst", "—", "Streamlit"],
  ], [2.2, 2, 1.1, 1.7]),
  h2("3.1 Container definition"),
  caption("Table", "docker-compose.yml settings"),
  table(["Setting", "Value", "Why"], [
    ["Project / container", "`fde-legacy` / `fde-mysql`", "Same container name as the HLD v1.2, so later steps plug in"],
    ["Image", "`mysql:8.4`", "MySQL 8.4 LTS; native on Intel, AMD and Apple Silicon"],
    ["Server options", "`--local-infile=ON`, `--character-set-server=utf8mb4`, `--collation-server=utf8mb4_0900_ai_ci`, `--default-time-zone=+00:00`", "Allow the CSV load; full Unicode; times stay UTC"],
    ["Environment", "`MYSQL_ROOT_PASSWORD`, `BI_ANALYST_USER`, `BI_ANALYST_PASSWORD` (from `.env`)", "Compose stops with \"missing a value\" if a password is not set"],
    ["Port", "`127.0.0.1:${MYSQL_PORT:-3306}:3306`", "Reachable from this computer only"],
    ["Mounts", "`fde_mysql_data:/var/lib/mysql`; `./mysql/scripts:/scripts:ro`; `../data/raw:/import/raw:ro`", "Data persists; scripts and CSV are read-only"],
    ["Health check", "`mysqladmin ping -h 127.0.0.1 --silent`, every 5 s, 36 retries, 30 s start period", "`up --wait` returns only when the real server is ready"],
  ], [1.3, 3.2, 2.2], { size: 17 }),

  h1("4. Database design"),
  h2("4.1 Objects"),
  caption("Table", "Database objects"),
  table(["Object", "Name", "Created by", "Notes"], [
    ["Database", "`legacy_fleet` (utf8mb4)", "01", "`CREATE DATABASE IF NOT EXISTS`"],
    ["Table", "`TBL_SC_FLEET_HIST_RAW` (InnoDB)", "01", "29 columns; primary key `REC_ID`"],
    ["Index", "`IX_FLEET_HIST_TS` on `TS_UTC`", "01", "Speeds up \"latest reading\" and date filters"],
    ["Login", "`root`@`%`", "MySQL image (first start)", "Password from `.env`, fixed when the volume is first created"],
    ["Login", "`bi_analyst`@`%`", "02", "`GRANT SELECT ON legacy_fleet.*`; password reset on every run of 02"],
  ], [0.9, 2.2, 1.4, 2.4]),
  h2("4.2 Table definition and column mapping"),
  p("All 26 CSV columns are kept under cryptic legacy names, in CSV order, plus three system columns. Group: **core** = the 9 columns every screen uses (and the AI system will use later); **ops** = the 8 operations columns; **other** = stored for future questions."),
  caption("Table", "TBL_SC_FLEET_HIST_RAW: all 29 columns"),
  table(["#", "Legacy column", "Type", "CSV column", "Meaning", "Group"], COLS, [0.35, 1.45, 1.6, 1.9, 1.75, 0.6], { size: 16 }),
  h2("4.3 Access and grants"),
  ...figure(IMG + "d8_db_access.png", "Database access: two logins, one of them read-only", 6.0),
  p("Captured output of `SHOW GRANTS FOR 'bi_analyst'@'%'` after step 02:"),
  ...code(`GRANT USAGE ON *.* TO \`bi_analyst\`@\`%\`
GRANT SELECT ON \`legacy_fleet\`.* TO \`bi_analyst\`@\`%\``),

  h1("5. Data load design"),
  ...figure(IMG + "d7_load_flow.png", "Building and loading the legacy table", 6.3),
  caption("Table", "Set-up scripts in order"),
  table(["Step", "Script", "Does", "Safe to re-run"], [
    ["01", "`01_create_legacy_schema.sql`", "Creates the database and table; prints the column count (29)", "Yes: nothing is dropped"],
    ["02", "`02_create_bi_analyst.sh`", "Creates `bi_analyst`, resets its password from `.env`, grants SELECT, prints the grants", "Yes"],
    ["03", "`03_load_legacy_data.sql`", "TRUNCATE, then LOAD DATA LOCAL; prints warnings and the row count", "Yes: the table is emptied first"],
    ["04", "`04_verify_load.sql`", "13 PASS/FAIL checks against values computed from the CSV", "Yes: read-only"],
  ], [0.5, 2, 3, 1.3]),
  h2("5.1 run_sql.sh"),
  ...L.numbered([
    "Stop with a clear message if `MYSQL_ROOT_PASSWORD` is not set in the container.",
    "Set `umask 077` and create a temporary option file (`mktemp`, fallback `/tmp/.run_sql_$$.cnf`); remove it on exit.",
    "Write `[client] user=root password=\"…\"` into it, so the password never appears on screen or in the process list.",
    "Run `mysql --defaults-extra-file=<file> --local-infile=1 --table` with the given SQL file (or standard input). Stop if the file does not exist.",
  ]),
  h2("5.2 03_load_legacy_data.sql"),
  ...code(`TRUNCATE TABLE TBL_SC_FLEET_HIST_RAW;
LOAD DATA LOCAL INFILE '/import/raw/dynamic_supply_chain_logistics_dataset.csv'
INTO TABLE TBL_SC_FLEET_HIST_RAW
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\\n'
IGNORE 1 LINES
(@csv_timestamp, V_LAT, V_LON, FUEL_CONS_RT, ... , RISK_CLS_TXT, @csv_delivery_dev)
SET TS_UTC          = STR_TO_DATE(@csv_timestamp, '%Y-%m-%d %H:%i:%s'),
    DLV_TM_DEV      = NULLIF(TRIM(TRAILING '\\r' FROM @csv_delivery_dev), ''),
    SYS_INGEST_FLAG = 'Y';
SHOW WARNINGS LIMIT 5;
SELECT @@warning_count AS load_warnings;`),
  ...bullets([
    "**LOCAL** means the `mysql` client inside the container reads the file, so the server needs no file privileges.",
    "The column list follows the CSV header order exactly (Appendix A); the timestamp text becomes a DATETIME.",
    "A trailing carriage return is removed from the last column, so a CSV saved with Windows line endings still loads.",
    "Values MySQL cannot store become warnings, listed by column and row; the expected count is 0.",
  ]),
  h2("5.3 Verification (04_verify_load.sql)"),
  caption("Table", "The 13 checks; expected values computed directly from the CSV"),
  table(["#", "Check", "Expected", "Result (captured)"], [
    ["1", "Rows loaded", "32065", "PASS"], ["2", "Distinct hourly timestamps", "32065", "PASS"],
    ["3", "First reading", "2021-01-01 00:00:00", "PASS"], ["4", "Last reading", "2024-08-29 00:00:00", "PASS"],
    ["5", "High Risk rows", "23944", "PASS"], ["6", "Moderate Risk rows", "5011", "PASS"], ["7", "Low Risk rows", "3110", "PASS"],
    ["8", "Rows with a missing value", "0", "PASS"], ["9", "Columns in table (26 + 3)", "29", "PASS"],
    ["10", "Checksum SUM(FUEL_CONS_RT), column 4", "256896.28", "PASS"], ["11", "Checksum SUM(IOT_TEMP_VAL_C), column 17", "1436.24", "PASS"],
    ["12", "Checksum SUM(DLV_TM_DEV), column 26", "166021.29", "PASS"], ["13", "Rows with SYS_INGEST_FLAG = Y", "32065", "PASS"],
  ], [0.4, 3.2, 1.8, 1.3]),
  p("The three checksums prove that the first, a middle and the last numeric columns landed in the right place with full precision. The final line reads `ALL 13 CHECKS PASSED - the legacy system is ready`."),

  h1("6. Configuration"),
  h2("6.1 .env settings"),
  caption("Table", "Settings in .env"),
  table(["Setting", "Default", "Used by"], [
    ["`DB_ENGINE`", "MYSQL", "Later steps (AI system)"],
    ["`MYSQL_HOST` / `MYSQL_PORT`", "127.0.0.1 / 3306", "Compose port mapping; BI dashboard"],
    ["`MYSQL_ADMIN_USER` / `MYSQL_ROOT_PASSWORD`", "root / (typed)", "Container first start; `run_sql.sh`"],
    ["`LEGACY_DB` / `LEGACY_TABLE`", "legacy_fleet / TBL_SC_FLEET_HIST_RAW", "BI dashboard; later steps"],
    ["`BI_ANALYST_USER` / `BI_ANALYST_PASSWORD`", "bi_analyst / (typed)", "Step 02; the user types the password at the dashboard login"],
  ], [2.3, 2, 2.4]),
  h2("6.2 create_env.ps1 (Windows) and create_env.sh (macOS)"),
  caption("Table", "Behaviour of the .env helpers"),
  table(["Behaviour", "Windows: create_env.ps1", "macOS: create_env.sh"], [
    ["Run with", "`powershell -NoProfile -ExecutionPolicy Bypass -File .\\legacy_system\\create_env.ps1`", "`bash legacy_system/create_env.sh`"],
    ["Prompts", "`Read-Host -AsSecureString`, twice per password (shows *)", "`read -s`, twice per password (shows nothing)"],
    ["Rules", "≥ 8 characters; letters, digits and `_ @ % + = . -` only", "Same"],
    ["Existing `.env`", "Never overwritten; prints INFO and stops", "Same"],
    ["File format", "UTF-8 without BOM, Unix line endings", "UTF-8, Unix line endings"],
    ["Protection", "`icacls`: only the current user (best effort)", "`umask 077` → mode 600"],
    ["Output", "The 9 settings with passwords shown as `******** (set)`", "Same"],
  ], [1.2, 2.9, 2.6]),
  h2("6.3 Git rules"),
  ...bullets([
    "`.gitignore`: `.env` and copies (except `.env.example`), `.DS_Store`, `venv*/`, `__pycache__/`, `data/cache/`, `releases/*.zip`.",
    "`.gitattributes`: `*.sh`, `*.sql`, `*.yml`, `*.md` keep LF line endings; `*.ps1` uses CRLF; `*.csv` is never converted.",
  ]),

  h1("7. BI dashboard design"),
  ...figure(IMG + "d10_dashboard_modules.png", "Inside the BI dashboard (app.py)", 6.2),
  h2("7.1 Functions"),
  caption("Table", "Functions in app.py"),
  table(["Function", "Section", "Does"], [
    ["`connect(user, password)`", "2", "Builds the SQLAlchemy engine (`mysql+pymysql`, `pool_pre_ping=True`) and runs `SELECT 1`; raises on a wrong password"],
    ["`sql_for_display(sql, params)`", "2", "Fills parameter values into the SQL text for the back-end panel"],
    ["`run_query(purpose, sql, params)`", "2", "Runs one SELECT with named parameters; appends purpose, SQL, rows and ms to `QUERY_LOG`"],
    ["`where(conditions)`", "2", "Joins filter conditions into a WHERE clause"],
    ["`show_table(df)`", "2", "Shows a result with readable labels from `LABELS`"],
    ["`backend_panel()`", "2", "The \"What happened at the back end\" expander"],
    ["`login_page()`", "3", "User ID (pre-filled) and password form; shows the driver error on failure"],
    ["`page_overview()`, `page_map()`, `page_risk()`, `page_operations()`, `page_sql_console()`", "4", "The five screens"],
  ], [2.5, 0.7, 3.5]),
  h2("7.2 Session and reruns"),
  ...bullets([
    "Streamlit re-runs `app.py` from top to bottom on every click; `QUERY_LOG` is a module-level list, so it starts empty each run.",
    "`st.session_state` keeps the engine, the user and the back-end checkbox for the browser session. Log out disposes the engine and clears the state.",
    "No caching: every screen queries MySQL each time (the queries take milliseconds).",
  ]),
  h2("7.3 Login and page flow"),
  ...figure(IMG + "d11_seq_login.png", "Login and page flow", 6.0),
  h2("7.4 Screens and their queries"),
  caption("Table", "Screens, inputs and queries"),
  table(["Screen", "Inputs", "Queries (purpose)", "Columns"], [
    ["Fleet Overview", "None", "KPI tiles (one query); readings per risk class; monthly average temperature", "Core + `FUEL_CONS_RT`"],
    ["Where are my trucks?", "Date range (default: last 7 days of data), risk class, latitude/longitude box", "Count matching readings; latest 500 matching readings", "9 core"],
    ["Risk & Delay report", "Risk class, year, month; optional limits: temperature, delay probability, port congestion (strict >, only when typed)", "Readings for risk/year/month; readings matching all filters; per month; latest 100", "9 core"],
    ["Operations", "Year; measure", "Averages of the 8 operations columns; monthly average of the chosen measure", "8 ops"],
    ["Analyst SQL console", "Free SQL", "DESCRIBE the table; the user's query (raw driver connection)", "Any"],
  ], [1.3, 2.2, 2.4, 0.9]),
  h2("7.5 Example queries (as shown in the back-end panel)"),
  ...code(`-- Where are my trucks? Los Angeles box over the whole history (captured: 35 rows)
SELECT COUNT(*) AS n FROM TBL_SC_FLEET_HIST_RAW
WHERE TS_UTC >= '2021-01-01 00:00:00'
  AND TS_UTC < '2024-08-30 00:00:00'
  AND V_LAT BETWEEN 33.3 AND 34.3
  AND V_LON BETWEEN -118.6 AND -117.6

-- Risk & Delay report: High Risk above 4 °C (captured: 6,455)
SELECT COUNT(*) AS n FROM TBL_SC_FLEET_HIST_RAW
WHERE RISK_CLS_TXT = 'High Risk'
  AND IOT_TEMP_VAL_C > 4.0`),
  h2("7.6 SQL console safety"),
  ...bullets([
    "Runs through `engine.raw_connection()` with no parameters, so a `%` in the user's SQL (for example in DATE_FORMAT) works.",
    "Sets `SET SESSION max_execution_time = 15000` first (15 seconds), then fetches at most 1,000 rows.",
    "Any change is refused by MySQL itself (`bi_analyst` has SELECT only); the error is shown as `MySQL refused the query: …`.",
  ]),
  h2("7.7 Start options"),
  caption("Table", "Streamlit options used in the run command"),
  table(["Option", "Effect"], [
    ["`--server.port 8502`", "The HLD's AI console uses 8501, so both can run side by side later"],
    ["`--server.address localhost`", "Reachable from this computer only"],
    ["`--server.headless true`", "No first-run e-mail prompt; the URL is printed instead of opening a browser"],
    ["`--browser.gatherUsageStats false`", "No usage statistics are sent"],
    ["`--client.toolbarMode minimal`", "Hides the developer toolbar (Deploy button)"],
  ], [2.3, 4.4]),

  h1("8. Error handling"),
  caption("Table", "Failures and what the user sees"),
  table(["Failure", "Where handled", "What the user sees"], [
    ["Password not set in `.env`", "Docker Compose interpolation", "`required variable … is missing a value`"],
    ["Wrong root password (changed after first start)", "MySQL", "`ERROR 1045 … Access denied for user 'root'`"],
    ["CSV missing or renamed", "LOAD DATA (client)", "`ERROR 2 … File '/import/raw/…' not found`"],
    ["Local load disabled (container started without the options)", "MySQL", "`ERROR 3948 … Loading local data is disabled`"],
    ["A value cannot be stored", "LOAD DATA", "Warnings table (column, row) and `load_warnings` > 0"],
    ["Windows line endings in a `.sh` script", "Container shell", "`set: Illegal option -` (fix: guide step A3)"],
    ["Wrong `bi_analyst` password", "`login_page()`", "`Login failed: (1045, …)` plus a hint"],
    ["MySQL not running", "`login_page()`", "`Login failed: (2003, \"Can't connect …\")` plus a hint"],
    ["Write attempted in the SQL console", "MySQL grants", "`MySQL refused the query: (1142, \"DELETE command denied …\")`"],
    ["Filters match nothing", "`page_map()`", "`No readings match these filters.`"],
  ], [2.4, 1.5, 2.8], { size: 17 }),

  h1("9. Testing"),
  h2("9.1 What was run (captured)"),
  caption("Table", "Tests of the v1.0 replica"),
  table(["Test", "How", "Result"], [
    ["Schema, login, load, verify", "Scripts 01–04 through `run_sql.sh` against MySQL 8.0.46 with the real CSV", "13 of 13 checks PASS; 0 load warnings; load under 1 second; re-runs create no duplicates"],
    ["Bad values and Windows line endings", "5-row CSV copy with 2 bad values and CRLF endings", "2 warnings reported by column and row; CRLF handled"],
    ["Failure paths", "Missing CSV; local load switched off; wrong root password; missing variable", "Errors as in Section 8"],
    ["Read-only login", "SELECT, DELETE, wrong password as `bi_analyst`", "SELECT allowed; DELETE refused (1142); login refused (1045)"],
    ["create_env.sh", "Mismatched, short and invalid passwords, then valid; second run", "Rejected with reasons; `.env` mode 600; not overwritten"],
    ["docker-compose.yml", "`docker compose config` with and without `.env`; CRLF `.env`; BOM `.env`", "Valid; clear error without `.env`; CRLF and BOM read correctly"],
    ["BI dashboard", "Streamlit `AppTest`: every screen and the 12 sample inputs of guide 02", "34 of 34 checks passed"],
    ["BI dashboard in a browser", "Real server with the C2 options, Chrome, every screen", "All screens render; screenshots in `docs/images/step2`"],
    ["Full set-up on the user's machine", "The user followed guide 01", "Confirmed working (24 Nov 2026)"],
  ], [1.6, 2.7, 2.4], { size: 17 }),
  ...figure(IMG + "s2_03_risk_report.png", "Risk & Delay report for High Risk above 4 °C: 6,455 readings (captured)", 5.4),
  h2("9.2 Not tested"),
  p("The `mysql:8.4` image itself (Docker Hub was not reachable from the test environment; the scripts were run against MySQL 8.0.46), `create_env.ps1` and the other PowerShell commands, winget, WSL and the map background (needs internet)."),

  h1("10. Operations command reference"),
  p("Run from the project folder. Windows (PowerShell) first; the `docker exec` commands are the same on both platforms."),
  h3("Windows (PowerShell)"),
  ...code(`Set-Location "$([Environment]::GetFolderPath('MyDocuments'))\\FDE_PB_Sol"
docker compose -f legacy_system/docker-compose.yml --env-file .env up -d --wait
docker exec fde-mysql sh /scripts/run_sql.sh /scripts/04_verify_load.sql
.\\venv_legacy\\Scripts\\python.exe -m streamlit run legacy_system/bi_dashboard/app.py --server.port 8502 --server.address localhost --server.headless true --browser.gatherUsageStats false --client.toolbarMode minimal
docker compose -f legacy_system/docker-compose.yml --env-file .env stop`),
  h3("macOS (Terminal)"),
  ...code(`cd ~/Documents/FDE_PB_Sol
docker compose -f legacy_system/docker-compose.yml --env-file .env up -d --wait
docker exec fde-mysql sh /scripts/run_sql.sh /scripts/04_verify_load.sql
./venv_legacy/bin/python -m streamlit run legacy_system/bi_dashboard/app.py --server.port 8502 --server.address localhost --server.headless true --browser.gatherUsageStats false --client.toolbarMode minimal
docker compose -f legacy_system/docker-compose.yml --env-file .env stop`),
  caption("Table", "Other operations"),
  table(["Task", "Command (both platforms, from the project folder)"], [
    ["Reload the CSV", "`docker exec fde-mysql sh /scripts/run_sql.sh /scripts/03_load_legacy_data.sql`, then 04"],
    ["Reset the analyst password", "Edit `.env`, `docker compose … up -d --wait`, then `docker exec fde-mysql sh /scripts/02_create_bi_analyst.sh`"],
    ["Logs", "`docker logs --tail 20 fde-mysql`"],
    ["Full reset (deletes all data)", "`docker compose -f legacy_system/docker-compose.yml --env-file .env down -v`"],
  ], [1.7, 5]),

  h1("11. Known limitations"),
  caption("Table", "Verified limitations of the replica"),
  table(["#", "Limitation", "Effect", "Follow-up"], [
    ["1", "The root password is fixed when the volume is first created", "Changing it in `.env` later breaks set-up scripts (1045)", "Keep the `.env` back-up; reset with `down -v`"],
    ["2", "No audit trail", "Nobody can see who looked at what", "Requirement C3 for the next phase"],
    ["3", "No truck or shipment ID in the data", "Per-truck questions cannot be answered", "Agree the data contract with the business"],
    ["4", "Positions do not form routes", "The map shows scattered points", "Use a real feed in production"],
    ["5", "SOP rules and weather are not in the system", "Thresholds are typed by hand", "By design: this is the legacy state"],
    ["6", "Tested against MySQL 8.0.46, not the 8.4 image", "Minor version differences possible", "Run guide 01 G1 on the target machine (done by the user)"],
    ["7", "The map background needs internet", "Dots on a blank background offline", "None needed"],
  ], [0.35, 2.2, 2.1, 2.1], { size: 17 }),

  h1("12. Suggested code comments"),
  p("Listed here rather than added to the code, so the v1.0 code stays as tested."),
  caption("Table", "Comments worth adding later"),
  table(["File", "Location", "Suggested comment"], [
    ["`app.py`", "`QUERY_LOG = []`", "Module-level on purpose: Streamlit re-runs the script on every click, so the log starts empty for each page view."],
    ["`app.py`", "`login_page()`", "The password is typed by the user and never read from .env: legacy systems are reached by ID and password only."],
    ["`app.py`", "`page_sql_console()`", "Raw driver connection with no parameters so that % in user SQL is not treated as a placeholder."],
    ["`app.py`", "`page_risk()` limits", "Limits are applied only when typed; a default of −10 would silently drop the 18 readings at exactly −10.0 °C."],
    ["`03_load_legacy_data.sql`", "`TRIM(TRAILING '\\r' …)`", "Keeps the load working if the CSV is ever re-saved with Windows line endings."],
    ["`docker-compose.yml`", "`healthcheck`", "ping succeeds even when access is denied; it only proves the real server (not the first-start set-up server) is up."],
    ["`run_sql.sh`", "temporary option file", "Keeps the root password out of the screen and the process list."],
  ], [1.4, 1.6, 3.7], { size: 17 }),

  h1("Appendix A. CSV header order"),
  p("timestamp, vehicle_gps_latitude, vehicle_gps_longitude, fuel_consumption_rate, eta_variation_hours, traffic_congestion_level, warehouse_inventory_level, loading_unloading_time, handling_equipment_availability, order_fulfillment_status, weather_condition_severity, port_congestion_level, shipping_costs, supplier_reliability_score, lead_time_days, historical_demand, iot_temperature, cargo_condition_status, route_risk_level, customs_clearance_time, driver_behavior_score, fatigue_monitoring_score, disruption_likelihood_score, delay_probability, risk_classification, delivery_time_deviation", { run: { size: 18 } }),
  h1("Appendix B. Diagram sources"),
  p("The block diagrams are drawn with a small Pillow script (`diagrams.py`, Miro-board style); the sequence diagrams are Mermaid files; the chart is matplotlib. Sources and PNGs are saved in `docs/design/diagrams/` so they can be edited and re-rendered."),
];

L.build(OUT, meta, body);
