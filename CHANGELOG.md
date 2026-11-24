# Changelog: FDE_PB_Sol (Cold-Chain Logistics FDE project)

## v2.0 Engineering Core (in progress)

**Goal:** a rule-based service that applies the company's SOP rules to the legacy data and answers over an API, deployed in Docker next to the legacy database. It covers FDE pillar 02 Engineering Core: Production Software Engineering, Backend & API Design, Data & Systems Integration. No AI in this version.

**Decisions (approved 24 Nov 2026)**

| # | Decision |
|---|---|
| 1 | Versions: v1.x legacy fixes · **v2.x Engineering Core (rule services)** · **v3.0 AI solution** (was v2.0) |
| 2 | **One service** (`rule_service`, FastAPI); microservice ideas shown through its design, a sample client and the guide |
| 3 | Rules in a versioned **YAML file** (`sop_rules_v2.4.yaml`) read by a small, tested Python engine |
| 4 | SOP rules R1 breach > 4.0 °C · R2 breach and ETA > 1 h late (`ETA_VAR_HRS`) · R3 port congestion > 7.0 (applied to **all readings**, with the assumption stated) · R4 High Risk and delay > 0.65 · G1 below 0 °C = SOP gap, refer to supervisor (no action invented) |
| 5 | Login: **JWT** for people (roles dispatcher, supervisor, admin) and an **API key** for machine clients |

**Progress**

| Step | Status | Files |
|---|---|---|
| Step 3: data integration layer (readable view, least-privilege login `rule_svc`, append-only audit table, 17-point self-test) | Built and tested in the build environment: **17 of 17 checks passed**, v1.0 13-point check still passes. **Waiting for you to run it.** | `legacy_system/mysql/scripts/05`–`08`, `legacy_system/update_env.ps1` / `.sh`, `legacy_system/docker-compose.yml` (changed), `.env.example` (changed), `docs/03_Data_Integration_Guide.md` |
| Step 4: rule service API (FastAPI, Pydantic, JWT + API key, Swagger, tests, Docker) | Next, after Step 3 runs on your machine | — |
| v2.0 release (VERSION, zip) and optional design pack | After Step 4 | — |

## v1.0 Design pack: legacy system, current state (24 Nov 2026)

Fresh v1.0 documents for the **legacy system only**: how it works today and its ten pain points. They start from *The Story* (Harborline Cold Chain, fictional) and the legacy part (Part 1) of `AI_FDE_Block_Diagram.pdf`. The numbers in them are the counts captured from the loaded table (32,065 readings). **Waiting for your review.**

| Deliverable | Size | Where |
|---|---|---|
| High-level design (HLD) | 19 pages | `docs/design/Legacy_Fleet_System_HLD_v1.0.docx` |
| Low-level design (LLD) | 16 pages | `docs/design/Legacy_Fleet_System_LLD_v1.0.docx` |
| Business proposal | 11 pages | `docs/design/Legacy_Fleet_System_Business_Proposal_v1.0.docx` |
| Overview deck | 5 slides, speaker notes | `docs/design/Legacy_Fleet_System_Overview_v1.0.pptx` |
| PDF copies of all four | | `docs/design/pdf/` |
| Diagrams | 11 for the documents, 4 for the slides, with sources | `docs/design/diagrams/`, `docs/design/diagrams/src/` |
| Build scripts | docx-js and python-pptx | `docs/design/src/` |

**Checked:** Word validation passed for all three documents; every page and every slide was rendered to an image and looked at for overlap and cut-off text; the deck's (click) marks match its animations (4 on slide 5, none elsewhere).
**Not checked:** opening the files in Microsoft Word and PowerPoint themselves (rendered with LibreOffice).
The earlier AI design documents (HLD, LLD v1.2 and Proposal v1.3) are not changed.

## v1.0, Base Version (24 Nov 2026)

**The complete, verified legacy system.** This is the baseline that the AI system will be built on. Approved by Bhimashankar on 24 Nov 2026 ("All looks good").

### What v1.0 contains

| Area | What | Where |
|---|---|---|
| Step 1: legacy database | MySQL 8.4 LTS in Docker (container `fde-mysql`, port `127.0.0.1:3306`, volume `fde_mysql_data`). Database `legacy_fleet`, table `TBL_SC_FLEET_HIST_RAW` with all 26 CSV columns under cryptic legacy names plus 3 system columns; 32,065 rows. Logins: `root` (admin) and `bi_analyst` (read-only). `.env` created with hidden password prompts (Windows and macOS scripts). | `legacy_system/docker-compose.yml`, `legacy_system/create_env.ps1`, `legacy_system/create_env.sh`, `legacy_system/mysql/scripts/` |
| Step 2: legacy BI dashboard | Streamlit 1.67.0 app on port 8502 (local only): login, Fleet Overview, Where are my trucks?, Risk & Delay report, Truck/route/driver operations, Analyst SQL console, and a "What happened at the back end" panel on every screen. Uses the 9 core columns plus 8 operations columns. | `legacy_system/bi_dashboard/app.py`, `legacy_system/bi_dashboard/requirements.txt` |
| Guides (Windows first, then macOS) | Step 1 set-up guide v2.0; Step 2 dashboard guide v1.0 with 12 sample inputs and expected results | `docs/01_Legacy_System_Setup_Guide.md`, `docs/02_Legacy_BI_Dashboard_Guide.md`, `docs/images/step2/` |
| Copilot prompt | Prompt to rebuild the Step 2 dashboard with GitHub Copilot, with acceptance checks | `docs/prompts/02_Copilot_Prompt_Legacy_BI_Dashboard.md` |
| Data | Kaggle *Logistics and Supply Chain Dataset*: 32,065 hourly readings, 1 Jan 2021 to 29 Aug 2024, 26 columns (unchanged) | `data/raw/`, `data/source/data.txt` |
| Project files | README, settings template, git rules, version file | `README.md`, `.env.example`, `.gitignore`, `.gitattributes`, `VERSION` |

### How v1.0 was verified

- **Step 1:** the load scripts were run against MySQL with the real CSV, and the 13-point check passed (row count, dates, risk counts, missing values, column count, checksums). You then ran the set-up successfully on your own machine on 24 Nov 2026.
- **Step 2:** an automated run of every screen passed 34 of 34 checks, including all expected values of the sample inputs. All screens were also opened in a browser. Reviewed and approved by you.
- **Not run in the test environment:** the Windows and macOS install commands (Docker Desktop, Python, winget, Homebrew). Those outputs are marked *example* in the guides.

### Known differences from the HLD/LLD v1.2 (to update in the next revision of those documents)

- The legacy table keeps all 26 columns (the HLD/LLD say 9) and stores numbers as DOUBLE (the LLD says FLOAT).
- Extra system columns `REC_ID` and `SYS_LOAD_TS`, and an index on `TS_UTC`.
- The project folder is `Documents\FDE_PB_Sol`, not `C:\ClaudeWorks\cold-chain-logistics-FDE-Project`.
- New in v1.0 and not in the HLD: the read-only `bi_analyst` login and the legacy BI dashboard on port 8502.

### Not in v1.0 (next steps, as in the HLD)

The AI system: the readable view `vw_active_fleet`, the least-privilege AI login, the audit table, SOP documents and search (RAG), the AI agents (router, telemetry, weather, SOP, report writer), the live weather API, the AI console on port 8501, and the AWS deployment.

### Snapshot and how to restore it

A zip of the whole project as it was at v1.0 is saved in `releases/`, with a SHA-256 checksum list:

- `releases/FDE_PB_Sol_v1.0_Base.zip`
- `releases/FDE_PB_Sol_v1.0_Base_MANIFEST.txt`

It **does not contain** your private `.env` (passwords), the Python environment `venv_legacy`, or caches. After restoring, create `.env` again (Step 1, D1) and `venv_legacy` (Step 2, B1).

To restore into a new folder next to the current one:

**Windows (PowerShell)**
```powershell
Set-Location "$([Environment]::GetFolderPath('MyDocuments'))"
Expand-Archive -Path .\FDE_PB_Sol\releases\FDE_PB_Sol_v1.0_Base.zip -DestinationPath .\FDE_PB_Sol_v1.0_restore
```

**macOS (Terminal)**
```bash
cd ~/Documents
unzip FDE_PB_Sol/releases/FDE_PB_Sol_v1.0_Base.zip -d FDE_PB_Sol_v1.0_restore
```

The restored project is in `FDE_PB_Sol_v1.0_restore\FDE_PB_Sol`.

### Versioning from here

- **v1.x:** fixes and small additions to the legacy system.
- **v2.0:** the AI system (Step 3 onwards), built on this base.
