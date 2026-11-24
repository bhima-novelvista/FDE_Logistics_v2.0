# Step 3: Data Integration Layer Guide (Windows first, then macOS)

**Project:** Cold-Chain Logistics FDE (FDE_PB_Sol)
**Version of the project:** v2.0 Engineering Core, Step 3 of 4
**What you build:** a safe, read-only way into the legacy data for the new rule service: a readable view, a least-privilege database login, an append-only audit table and a self-test
**Platforms:** **Windows 10/11 with PowerShell (primary)** · macOS with Terminal
**Guide version:** 1.1, 24 Nov 2026

| Version | Date | Change |
|---|---|---|
| 1.1 | 24 Nov 2026 | Appendix B: the audit outcomes used by the Step 4 rule service |
| 1.0 | 24 Nov 2026 | First version |

---

## 0. What Step 3 adds (summary)

**Status:** tested in the build environment (17 of 17 checks passed). **Waiting for you to run it.**

**Why this step exists.** In v2.0 a rule service (Step 4) applies the company's SOP rules to the fleet readings and answers over an API. Before any new software touches the legacy database, we give it a door that is safe by design:

- The legacy table is **not changed**, so v1.0 (Step 1 and the Step 2 dashboard) keeps working exactly as before.
- The service sees **readable names** (`Current_Temperature_C` instead of `IOT_TEMP_VAL_C`) and only the **11 columns** it needs.
- The service's login can do **two things only**: read the view, and add audit rows. MySQL itself refuses everything else. That makes the database the real security boundary, whatever the service code does.
- Every decision the service makes will be written to an **audit table that the service cannot read, change or delete** (rule C3 of the story: record every step).

```text
                                  (Step 4)
                               rule service
                                    |  logs in as rule_svc
                 +------------------+---------------------+
                 | SELECT only                            | INSERT only
                 v                                        v
   fde_views.vw_fleet_readings               fde_audit.RuleDecisionLog
   11 readable columns, read-only            append-only audit trail
                 |
                 |  the view runs with the admin's rights (SQL SECURITY DEFINER)
                 v
   legacy_fleet.TBL_SC_FLEET_HIST_RAW   <- unchanged; rule_svc has no rights on it
```

**Decisions taken**

| # | Decision | Why |
|---|---|---|
| 1 | Read the legacy table **through a view**, never directly | The legacy system stays exactly as it is (story constraints: keep the database, read-only). |
| 2 | The view shows **11 of the 29 columns** | Least data: only what the SOP rules and the API need (Appendix A). |
| 3 | 9 of the view's names are **the names in HLD v1.2** (Table 8-2) | The AI step (v3.0) can use the same names without changes. |
| 4 | The view uses **SQL SECURITY DEFINER** | It runs with the admin's rights, so `rule_svc` needs no right on the legacy table. |
| 5 | A new login **`rule_svc`** with exactly **SELECT on the view and INSERT on the audit table** | Least privilege. Even a bug in the service cannot change data or rewrite history. |
| 6 | An **append-only audit table** `fde_audit.RuleDecisionLog` | Who asked what, when, and what the rules decided. The service can add rows but not read, change or delete them. |
| 7 | Two new schemas, **`fde_views`** and **`fde_audit`** | Clear ownership: `legacy_fleet` stays untouched. |
| 8 | The new password is typed at a **hidden prompt** by `update_env` | Same rule as Step 1: secrets are never shown, printed or committed. |
| 9 | A **17-point self-test** that logs in **as the service** | Proves what is allowed, what is refused, and the rule counts Step 4 must reproduce. |

**The numbers the self-test checks** (*captured*, through the view, out of 32,065 readings):

| Rule (SOP v2.4) | Condition | Readings |
|---|---|---|
| R1 critical breach | temperature > 4.0 °C | 8,674 |
| R2 breach + late: divert | temperature > 4.0 °C and ETA more than 1 hour late | 6,621 |
| R3 port congestion: divert to Inland Empire depot | port congestion > 7.0 | 19,566 |
| R4 Tier 2 escalation | High Risk and delay probability > 0.65 | 15,440 |
| G1 SOP gap (no rule exists) | temperature < 0.0 °C | 21,817 |
| in range | 0.0 to 4.0 °C | 1,574 |

`ETA_Variation_Hours` runs from −2 to +5: a positive value means hours **late**, a negative value means early. Rule R2 uses "more than 1 hour late" for the SOP's "ETA delay greater than 1 hour".

---

## How to use this guide

- **Before you start:** Step 1 is done (the v1.0 Base) and **Docker Desktop is running** (Step 1, C4).
- The conventions are the same as in Step 1:
  - Work through the parts **in order**. Each step has three parts: **What it does** → **Command** (copy the whole grey block) → **Expected output**.
  - **Windows (PowerShell)** blocks are the main path. **macOS (Terminal)** blocks follow. Blocks marked **Windows and macOS (same command)** work from any folder.
  - Platform blocks start by moving to the project folder. If your project is not in *Documents*, change that first line (Step 1, "How to use this guide").
  - ***captured*** = the real output of these scripts in the build environment. ***example*** = typical output; versions, paths and times on your computer differ.
- Everything after Part C runs inside the Linux container, so its output is the same on Windows and macOS.

---

## Part A: Check the starting point

### A1. Check that the legacy MySQL is running

**What it does:** Shows the state of the `fde-mysql` container.

**Windows and macOS (same command)**
```text
docker ps --filter name=fde-mysql --format "{{.Names}}  {{.Status}}"
```

**Expected output** (*example*):

```text
fde-mysql  Up 2 hours (healthy)
```

If nothing is printed, MySQL is not running: start it with Step 1, **I2**, then come back.

### A2. Check that the new Step 3 files are in place

**What it does:** Lists the database scripts. Step 3 adds `05` to `08`.

**Windows (PowerShell)**
```powershell
Set-Location "$([Environment]::GetFolderPath('MyDocuments'))\FDE_PB_Sol"
Get-ChildItem .\legacy_system\mysql\scripts | Select-Object -ExpandProperty Name
```

**macOS (Terminal)**
```bash
cd ~/Documents/FDE_PB_Sol
ls legacy_system/mysql/scripts
```

**Expected output** (*captured*):

```text
01_create_legacy_schema.sql
02_create_bi_analyst.sh
03_load_legacy_data.sql
04_verify_load.sql
05_create_integration_layer.sql
06_create_rule_svc_login.sh
07_verify_integration.sh
08_show_recent_audit.sql
run_sql.sh
```

(macOS prints the same names side by side.)

### A3. (Windows only) Check the line endings of the new scripts

**What it does:** Runs the same check as Step 1, **A3**, which now also covers the two new `.sh` scripts.

**Windows (PowerShell)**
```powershell
Set-Location "$([Environment]::GetFolderPath('MyDocuments'))\FDE_PB_Sol"
Get-ChildItem .\legacy_system\mysql\scripts\*.sh | ForEach-Object { if ([IO.File]::ReadAllText($_.FullName).Contains("`r")) { "$($_.Name): Windows line endings - run the fix in Step 1, A3" } else { "$($_.Name): OK" } }
```

**Expected output** (*example*):

```text
02_create_bi_analyst.sh: OK
06_create_rule_svc_login.sh: OK
07_verify_integration.sh: OK
run_sql.sh: OK
```

---

## Part B: Add the new settings to .env

### B1. Run update_env

**What it does:** Adds the Step 3 settings to your **existing** `.env` and asks for **one new password**, for the rule service's database login `rule_svc`. The script:
- never changes or removes a setting that already has a value (your root and bi_analyst passwords stay as they are);
- asks for the password twice, hidden (Windows shows `*`, macOS shows nothing);
- needs at least 8 characters, using only letters, digits and `_ @ % + = . -`;
- never prints the password;
- can be run again: the second time it says `nothing to add`.

Use a password **different from** the root and bi_analyst passwords. You only type it again in Part F (optional); the rule service in Step 4 reads it from `.env` itself.

**Windows (PowerShell)**
```powershell
Set-Location "$([Environment]::GetFolderPath('MyDocuments'))\FDE_PB_Sol"
powershell -NoProfile -ExecutionPolicy Bypass -File .\legacy_system\update_env.ps1
```

**macOS (Terminal)**
```bash
cd ~/Documents/FDE_PB_Sol
bash legacy_system/update_env.sh
```

**Expected output** (*captured* with `update_env.sh` on a `.env` made by Step 1. `update_env.ps1` prints the same lines, with a Windows path and `*` after each prompt):

```text
Updating /Users/<you>/Documents/FDE_PB_Sol/.env

  added   FDE_VIEWS_DB
  added   FDE_AUDIT_DB
  added   RULE_SVC_USER

New password for the rule service database login (rule_svc) (hidden):
Type it again:
  added   RULE_SVC_PASSWORD

OK: 4 setting(s) added to .env (passwords and secrets not shown).
Settings in the file:
DB_ENGINE=MYSQL
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_ADMIN_USER=root
MYSQL_ROOT_PASSWORD=******** (set)
LEGACY_DB=legacy_fleet
LEGACY_TABLE=TBL_SC_FLEET_HIST_RAW
BI_ANALYST_USER=bi_analyst
BI_ANALYST_PASSWORD=******** (set)
FDE_VIEWS_DB=fde_views
FDE_AUDIT_DB=fde_audit
RULE_SVC_USER=rule_svc
RULE_SVC_PASSWORD=******** (set)
```

If you mistype, the script says why (for example `x The two entries are different. Please try again.`) and asks again.

### B2. Back up .env again

**What it does:** Replaces your private backup from Step 1 (D2) with the new `.env`, which now has three passwords.

**Windows (PowerShell)**
```powershell
Set-Location "$([Environment]::GetFolderPath('MyDocuments'))\FDE_PB_Sol"
Copy-Item .env "$HOME\fde_pb_sol_env_backup.env"
"Backup saved to $HOME\fde_pb_sol_env_backup.env"
```

**macOS (Terminal)**
```bash
cd ~/Documents/FDE_PB_Sol
cp .env ~/fde_pb_sol_env_backup.env && chmod 600 ~/fde_pb_sol_env_backup.env && echo "Backup saved to ~/fde_pb_sol_env_backup.env"
```

**Expected output** (*example*): `Backup saved to C:\Users\<you>\fde_pb_sol_env_backup.env` (Windows) or `Backup saved to ~/fde_pb_sol_env_backup.env` (macOS)

---

## Part C: Restart MySQL so that it sees the new settings

### C1. Recreate the MySQL container

**What it does:** The container reads its settings from `.env` only when it is created. This command notices that the settings changed and **recreates the container**. Your data is safe: it lives in the volume `fde_mysql_data`, which is kept. The root and bi_analyst passwords do not change. It takes about 10–30 seconds.

**Windows (PowerShell)**
```powershell
Set-Location "$([Environment]::GetFolderPath('MyDocuments'))\FDE_PB_Sol"
docker compose -f legacy_system/docker-compose.yml --env-file .env up -d --wait
```

**macOS (Terminal)**
```bash
cd ~/Documents/FDE_PB_Sol
docker compose -f legacy_system/docker-compose.yml --env-file .env up -d --wait
```

**Expected output** (*example*):

```text
[+] Running 1/1
 ✔ Container fde-mysql  Healthy
```

(Docker may first show `Recreate` and `Recreated` for `fde-mysql`; that is expected.)

### C2. Check that the container received the new password (without showing it)

**What it does:** Asks the container whether `RULE_SVC_PASSWORD` has a value. It prints only `OK` or `PROBLEM`, never the password.

**Windows and macOS (same command)**
```text
docker exec fde-mysql sh -c 'case ${RULE_SVC_PASSWORD:-} in ?*) echo OK: RULE_SVC_PASSWORD is set in the container ;; *) echo PROBLEM: RULE_SVC_PASSWORD is empty in the container ;; esac'
```

**Expected output** (*captured*):

```text
OK: RULE_SVC_PASSWORD is set in the container
```

If you see `PROBLEM`, run **B1** and **C1** again (see H3).

---

## Part D: Build the integration layer

### D1. Create the readable view and the audit table

**What it does:** Creates the schemas `fde_views` and `fde_audit`, the view `fde_views.vw_fleet_readings` (11 readable columns over the legacy table) and the empty audit table `fde_audit.RuleDecisionLog`. It changes nothing in `legacy_fleet`. Safe to run again: the view is replaced with the same definition and audit rows are kept.

**Windows and macOS (same command)**
```text
docker exec fde-mysql sh /scripts/run_sql.sh /scripts/05_create_integration_layer.sql
```

**Expected output** (*captured*):

```text
+---------------------------------------------------------------------+
| status                                                              |
+---------------------------------------------------------------------+
| fde_views.vw_fleet_readings and fde_audit.RuleDecisionLog are ready |
+---------------------------------------------------------------------+
+--------------+
| rows_in_view |
+--------------+
|        32065 |
+--------------+
+-----------------+
| columns_in_view |
+-----------------+
|              11 |
+-----------------+
```

### D2. Create the rule service's login

**What it does:** Creates the login `rule_svc` with the password from `.env` and gives it exactly two rights: **SELECT on the view** and **INSERT on the audit table**. It first removes any other right the login may have, so running it again always brings the login back to these two rights (and resets its password to the one in `.env`).

**Windows and macOS (same command)**
```text
docker exec fde-mysql sh /scripts/06_create_rule_svc_login.sh
```

**Expected output** (*captured*):

```text
+------------------------------------------------------------------------+
| status                                                                 |
+------------------------------------------------------------------------+
| rule_svc can now log in (read the view, add audit rows - nothing else) |
+------------------------------------------------------------------------+
+-------------------------------------------------------------------+
| Grants for rule_svc@%                                             |
+-------------------------------------------------------------------+
| GRANT USAGE ON *.* TO `rule_svc`@`%`                              |
| GRANT INSERT ON `fde_audit`.`RuleDecisionLog` TO `rule_svc`@`%`   |
| GRANT SELECT ON `fde_views`.`vw_fleet_readings` TO `rule_svc`@`%` |
+-------------------------------------------------------------------+
```

(`USAGE` means "may log in"; it grants no rights to any data.)

---

## Part E: Self-test

### E1. Run the 17-point check as the rule service

**What it does:** Logs in **as `rule_svc`** (not as root) and proves three things:
- **A.** It can do what it needs: log in, read the view, add an audit row.
- **B.** MySQL refuses everything else: reading the legacy table, changing data through the view, reading, changing or deleting audit rows, creating tables.
- **C.** The view gives the expected count for each SOP rule. These are the numbers the Step 4 rule engine must reproduce.

Check 5 adds one audit row marked `SELF_TEST` each time you run it. The service login cannot delete it, by design.

**Windows and macOS (same command)**
```text
docker exec fde-mysql sh /scripts/07_verify_integration.sh
```

**Expected output** (*captured*):

```text
Self-test of the data integration layer, logged in as 'rule_svc'

A. What the rule service may do
 1. PASS  Log in as the service login                    rule_svc@%
 2. PASS  Read the view: number of readings              32065
 3. PASS  Read the view: number of columns               11
 4. PASS  Read the view: latest reading time             2024-08-29 00:00:00
 5. PASS  Add an audit row (marked SELF_TEST)            allowed

B. What the rule service must NOT be able to do
 6. PASS  Read the legacy table directly                 refused (as expected)
 7. PASS  Change data through the view                   refused (as expected)
 8. PASS  Read audit rows                                refused (as expected)
 9. PASS  Change an audit row                            refused (as expected)
10. PASS  Delete audit rows                              refused (as expected)
11. PASS  Create a table                                 refused (as expected)

C. SOP rule counts through the view (Step 4 must reproduce these)
12. PASS  R1  temperature > 4.0 C (breach)               8674
13. PASS  R2  breach and > 1 h late (divert)             6621
14. PASS  R3  port congestion > 7.0 (divert)             19566
15. PASS  R4  High Risk and delay > 0.65 (Tier 2)        15440
16. PASS  G1  temperature < 0.0 C (SOP gap)              21817
17. PASS      inside 0.0 to 4.0 C (in range)             1574

RESULT: 17 of 17 checks passed. The integration layer is ready for the rule service.
```

**This is the end of the required part of Step 3.** Part F is optional.

---

## Part F: See it for yourself (optional)

### F1. Log in as the rule service and try it

**What it does:** Opens the MySQL command line inside the container as `rule_svc`. Type the **rule_svc password** from B1 when asked; it stays invisible while you type.

**Windows and macOS (same command)**
```text
docker exec -it fde-mysql mysql -u rule_svc -p
```

At the `mysql>` prompt, paste these two lines. The first reads the three newest readings through the view; the second tries to read the legacy table directly:

```sql
SELECT Reading_ID, `Timestamp`, Current_Temperature_C, ETA_Variation_Hours, Port_Congestion_Level, Delay_Probability, Risk_Classification FROM fde_views.vw_fleet_readings ORDER BY `Timestamp` DESC LIMIT 3;
SELECT * FROM legacy_fleet.TBL_SC_FLEET_HIST_RAW LIMIT 1;
```

**Expected output** (*captured*; in the interactive shell the table is also followed by `3 rows in set (0.00 sec)`):

```text
+------------+---------------------+-----------------------+---------------------+-----------------------+--------------------+---------------------+
| Reading_ID | Timestamp           | Current_Temperature_C | ETA_Variation_Hours | Port_Congestion_Level | Delay_Probability  | Risk_Classification |
+------------+---------------------+-----------------------+---------------------+-----------------------+--------------------+---------------------+
|      32065 | 2024-08-29 00:00:00 |     18.79651453879272 |   4.068439877608897 |     7.693642636880453 | 0.9992302873270055 | High Risk           |
|      32064 | 2024-08-28 23:00:00 |    -6.951137131277026 |   4.759411000702818 |     9.697466737351231 | 0.5573400961448669 | High Risk           |
|      32063 | 2024-08-28 22:00:00 |    29.410878231505777 |  0.4852883023149972 |   0.49823517234472153 | 0.9591972134481881 | Moderate Risk       |
+------------+---------------------+-----------------------+---------------------+-----------------------+--------------------+---------------------+
ERROR 1142 (42000): SELECT command denied to user 'rule_svc'@'localhost' for table 'TBL_SC_FLEET_HIST_RAW'
```

Compare this with Step 1, **H1**: the same readings, but now with readable names, and the legacy table is out of reach. Reading 32065 is a good test case for Step 4: 18.8 °C, 4.1 hours late, port congestion 7.7, High Risk with delay probability 0.999, so rules R1, R2, R3 and R4 all apply. Type `exit` to leave.

### F2. Look at the audit trail (as the admin)

**What it does:** Shows the 10 newest audit rows. This runs as root, because the rule service itself may not read the audit trail. Right after E1 you see the one `SELF_TEST` row; in Step 4 you will see each API decision appear here.

**Windows and macOS (same command)**
```text
docker exec fde-mysql sh /scripts/run_sql.sh /scripts/08_show_recent_audit.sql
```

**Expected output** (*captured* after one run of E1; your time is different):

```text
+---------------------+
| audit_rows_in_total |
+---------------------+
|                   1 |
+---------------------+
+--------+-------------------------+----------+-------------+-------------+--------------------------+------------+-----------+-------------+
| Log_ID | Logged_At_UTC           | Caller   | Caller_Role | Auth_Method | Endpoint                 | Reading_ID | Outcome   | Fired_Rules |
+--------+-------------------------+----------+-------------+-------------+--------------------------+------------+-----------+-------------+
|      1 | 2026-11-24 15:18:03.540 | rule_svc | service     | self_test   | 07_verify_integration.sh |       NULL | SELF_TEST | NULL        |
+--------+-------------------------+----------+-------------+-------------+--------------------------+------------+-----------+-------------+
```

---

## Part G: Daily use

| Situation | What to do |
|---|---|
| After a reboot | Start MySQL as usual (Step 1, **I2**). The view, the login and the audit rows live in the data volume, so there is nothing to redo. |
| Check everything is still fine | Run **E1** (it adds one `SELF_TEST` row each time). |
| Change the rule_svc password | Open `.env` in a text editor (Windows `notepad .env`, macOS `open -e .env`), change the `RULE_SVC_PASSWORD=` line, save, then run **C1**, **D2**, **E1** and **B2**. (`update_env` never changes a value that is already set, on purpose.) |
| Someone gave rule_svc extra rights | Run **D2**: it removes every right except the two it needs. Then **E1**. |
| The legacy data was reloaded (Step 1, F3) | Nothing to do: the view reads the table live. Run **E1** to confirm the counts. |
| v1.0 still the same? | Yes. Step 1, **G1** still reports `ALL 13 CHECKS PASSED`, and the Step 2 dashboard works as before (`bi_analyst` is unchanged and cannot see the new schemas). |

**Removing Step 3 completely** (⚠️ this **deletes the audit trail** for good; the legacy table and v1.0 are not affected). Log in as root (type the root password when asked):

```text
docker exec -it fde-mysql mysql -u root -p
```

then paste:

```sql
DROP USER IF EXISTS 'rule_svc'@'%';
DROP DATABASE IF EXISTS fde_views;
DROP DATABASE IF EXISTS fde_audit;
exit
```

To build it again, run Part D and Part E.

---

## Part H: Troubleshooting

| # | Platform | You see | Why | Fix |
|---|---|---|---|---|
| H1 | Both | `ERROR: … .env not found` from update_env | The command was not run from the project folder, or Step 1 D1 was never done | Copy the full B1 block (it starts by moving to the project folder). If `.env` really is missing, do Step 1, **D1** first. |
| H2 | Windows | `update_env.ps1 cannot be loaded because running scripts is disabled` | Started without `-ExecutionPolicy Bypass` | Use the exact **B1** command. If your company blocks even that, open `.env` in Notepad and add the four lines from `.env.example` (section "v2.0 Step 3"), with your new password after `RULE_SVC_PASSWORD=`. |
| H3 | Both | `RULE_SVC_PASSWORD is not set in the container` (D2 or E1), or `PROBLEM` in C2 | `.env` was updated but the container was not recreated, or B1 was skipped | Run **B1**, then **C1**, then **C2**. |
| H4 | Both | E1 shows `FAIL` with `ERROR 1045 (28000): Access denied for user 'rule_svc'` | The password in `.env` is not the one MySQL has: `.env` was edited after D2, or C1 was not run after B1 | Run **C1**, then **D2** (it sets the password from `.env`), then **E1**. |
| H5 | Both | `set: Illegal option -` or `$'\r': command not found` | Windows line endings in a `.sh` file | Run **A3**, then the fix in Step 1, **A3**. |
| H6 | Both | `ERROR 1146 … Table 'fde_views.vw_fleet_readings' doesn't exist` | D1 was not run (or Step 3 was removed) | Run **D1**, **D2**, **E1**. |
| H7 | Both | Check 5 `FAIL` with `INSERT command denied` | D2 was not run, or its rights were removed | Run **D2**, then **E1**. |
| H8 | Both | A check in section B says `NOT refused` | Someone gave `rule_svc` extra rights | Run **D2** (it removes extra rights), then **E1**. |
| H9 | Both | Checks 2 or 12–17 `FAIL` with different numbers | The legacy table does not hold the original CSV | Run Step 1, **G1**. If it fails too, follow Step 1, **J13**. |
| H10 | Both | `ERROR 2002 … Can't connect to local MySQL server` | MySQL is still starting, or stopped | Wait 30 seconds and try again; check with **A1**; logs: `docker logs --tail 50 fde-mysql`. |
| H11 | Windows | `the input device is not a TTY` in F1 | Run in PowerShell ISE or Git Bash | Use Windows Terminal or the normal PowerShell window (Step 1, **J14**). |

---

## Appendix A: The view's columns

`fde_views.vw_fleet_readings`, 11 columns, read-only, 32,065 rows.

| Readable name (view) | Legacy column | CSV column | HLD v1.2 name? | Used for |
|---|---|---|---|---|
| `Reading_ID` | `REC_ID` | *(system)* | new | Asking for one reading by number (not a truck or shipment ID) |
| `Timestamp` | `TS_UTC` | timestamp | ✔ | Latest readings, time windows |
| `Latitude` | `V_LAT` | vehicle_gps_latitude | ✔ | Area filters |
| `Longitude` | `V_LON` | vehicle_gps_longitude | ✔ | Area filters |
| `Current_Temperature_C` | `IOT_TEMP_VAL_C` | iot_temperature | ✔ | R1, R2, G1 |
| `ETA_Variation_Hours` | `ETA_VAR_HRS` | eta_variation_hours | new | R2 (hours late: + late, − early) |
| `Port_Congestion_Level` | `PRT_CNG_LVL` | port_congestion_level | ✔ | R3 |
| `Delay_Probability` | `DELAY_PROB_DEC` | delay_probability | ✔ | R4 |
| `Risk_Classification` | `RISK_CLS_TXT` | risk_classification | ✔ | R4 |
| `Cargo_Condition_Code` | `CGO_COND_CD` | cargo_condition_status | ✔ | Shown with each reading |
| `Route_Risk_Index` | `RT_RSK_IDX` | route_risk_level | ✔ | Shown with each reading |

The other 18 legacy columns stay in the legacy table and remain available to `bi_analyst` and the Step 2 dashboard.

## Appendix B: The audit table's columns

`fde_audit.RuleDecisionLog`. The rule service can only **add** rows. The admin (root) can read them (**F2**).

| Column | Type | Meaning |
|---|---|---|
| `Log_ID` | BIGINT, auto number | Row number |
| `Logged_At_UTC` | DATETIME(3) | When, in UTC, to the millisecond (set by MySQL) |
| `Request_ID` | VARCHAR(64) | The request ID the API returns to the caller, so a caller's answer can be traced to its row |
| `Caller` | VARCHAR(64) | User name (JWT) or client name (API key) |
| `Caller_Role` | VARCHAR(32) | dispatcher, supervisor, admin, service, … |
| `Auth_Method` | VARCHAR(16) | `jwt`, `api_key` or `self_test` |
| `Endpoint` | VARCHAR(128) | Which API call, for example `GET /v1/readings/{id}/decision` |
| `Reading_ID` | BIGINT | The reading the decision is about (if any) |
| `Rules_Version` | VARCHAR(16) | The SOP rules version used, for example `2.4` |
| `Outcome` | VARCHAR(32) | Decisions: `ACTION_REQUIRED`, `REVIEW`, `NO_ACTION`. Other events: `SCAN`, `RULES_RELOADED`, `RULES_REJECTED`, `SELF_TEST` |
| `Fired_Rules` | VARCHAR(255) | For example `R3,G1` |
| `Detail_JSON` | JSON | The full decision as returned to the caller |

## Appendix C: Files created or changed in Step 3

| File | New or changed | What it is |
|---|---|---|
| `legacy_system/mysql/scripts/05_create_integration_layer.sql` | new | Schemas, view and audit table |
| `legacy_system/mysql/scripts/06_create_rule_svc_login.sh` | new | The `rule_svc` login and its two rights |
| `legacy_system/mysql/scripts/07_verify_integration.sh` | new | The 17-point self-test |
| `legacy_system/mysql/scripts/08_show_recent_audit.sql` | new | Shows the newest audit rows (admin) |
| `legacy_system/update_env.ps1` / `update_env.sh` | new | Adds missing settings to an existing `.env`; later steps extend it |
| `legacy_system/docker-compose.yml` | changed | Passes `RULE_SVC_USER` and `RULE_SVC_PASSWORD` into the container (empty by default, so v1.0 still starts without them) |
| `.env.example` | changed | New section "v2.0 Step 3" (names only, no secrets) |
| `docs/03_Data_Integration_Guide.md` | new | This guide |

The legacy scripts `01`–`04`, `run_sql.sh`, `create_env.*` and the Step 2 dashboard are unchanged.

## Appendix D: What was tested

| Item | How | Result |
|---|---|---|
| D1, D2, E1, F1, F2 | Run exactly as written, through `run_sql.sh` and the scripts' own login, against **MySQL 8.0.46** on Linux holding the real 32,065 rows. Docker Hub was not reachable from the build environment, so the `mysql:8.4` image itself was not run. | All *captured* outputs above; **17 of 17 checks passed** |
| Re-runs | D1 and D2 run twice; E1 run twice | No errors; audit rows kept; second E1 added one more `SELF_TEST` row |
| Extra rights removed | Gave `rule_svc` SELECT on `legacy_fleet.*`, then ran D2 | Only the two intended rights remained |
| Wrong or missing password | E1 with a wrong password; D2 and E1 with an empty one | `FAIL` lines showing `ERROR 1045`; clear "not set" message and exit code 1 |
| v1.0 untouched | Step 1, G1 after Step 3 | `ALL 13 CHECKS PASSED` |
| Speed through the view | `EXPLAIN` of "latest 3 readings" through the view | Uses the legacy index `IX_FLEET_HIST_TS` (reads 3 rows, not 32,065) |
| `update_env.sh` | First run, second run, an empty value, a mismatched password, a file without a final new line, no `.env` | Added only missing settings; never changed set values; `.env` stayed mode 600; clear errors |
| `docker-compose.yml` | Parsed as YAML; new settings default to empty | Valid; v1.0 start unaffected |
| **Not run in the build environment** | `update_env.ps1`, every PowerShell command, `docker compose` (C1), `docker exec` itself, C2 inside the real container | Their outputs are marked *example*, or *captured* where the same script or command was run directly in the Linux shell |
