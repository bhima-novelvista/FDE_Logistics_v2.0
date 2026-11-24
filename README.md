# FDE_PB_Sol: Cold-Chain Logistics FDE Project

This project shows how a Forward Deployed Engineer (FDE) turns a **legacy logistics system** into an **AI-powered dispatch assistant**. It follows the project's architecture diagram (*Legacy System vs AI-Powered Architecture*) and the HLD, LLD and Business Proposal.

**Version: 1.0 Base Version (24 Nov 2026)**, the complete, verified legacy system. See [CHANGELOG.md](CHANGELOG.md) for what it contains and how to restore its snapshot.

All guides put **Windows (PowerShell) first** and macOS second, in one file per step.

## Status

| Step | What | Status · Guide |
|---|---|---|
| **1** | **Legacy database:** MySQL 8.4 in Docker, legacy-style table with cryptic names, CSV loaded (32,065 rows, 26 columns), read-only `bi_analyst` login | ✅ Done · [docs/01_Legacy_System_Setup_Guide.md](docs/01_Legacy_System_Setup_Guide.md) |
| **2** | **Legacy BI dashboard:** Streamlit app with login, KPIs, map, risk report, operations, SQL console and a "what happened at the back end" panel (port 8502) | ✅ Built · [docs/02_Legacy_BI_Dashboard_Guide.md](docs/02_Legacy_BI_Dashboard_Guide.md) |
| 3 | AI system, as described in the HLD (readable view, least-privilege AI login, SOP search, agents, weather, audit trail, AI console on port 8501, AWS deployment) | Next (planned as v2.0), when you decide |

## Project structure

```text
FDE_PB_Sol/
├── README.md                     this file
├── VERSION / CHANGELOG.md        current version (1.0 Base Version) and what each version contains
├── .env.example                  settings template (no secrets)
├── .env                          YOUR private settings (Step 1, never committed)
├── .gitignore / .gitattributes   keep secrets out of git / keep Unix line endings in container scripts
├── data/
│   ├── raw/                      dynamic_supply_chain_logistics_dataset.csv (source data, never modified)
│   ├── source/data.txt           where the data came from (Kaggle)
│   └── policy/                   SOP documents (later step)
├── legacy_system/                the legacy system (Steps 1 and 2)
│   ├── docker-compose.yml        MySQL 8.4 container fde-mysql, port 127.0.0.1:3306, volume fde_mysql_data
│   ├── create_env.ps1 / .sh      create .env with hidden password prompts (Windows / macOS)
│   ├── mysql/scripts/            SQL + helpers that run inside the Linux container
│   └── bi_dashboard/             Step 2: app.py (Streamlit) + requirements.txt
├── docs/
│   ├── 01_Legacy_System_Setup_Guide.md
│   ├── 02_Legacy_BI_Dashboard_Guide.md
│   ├── images/step2/             screenshots for the Step 2 guide
│   ├── prompts/                  GitHub Copilot prompt to rebuild the Step 2 dashboard
│   └── archive/                  earlier versions of the guides
├── releases/                     v1.0 snapshot zip + SHA-256 manifest
├── venv_legacy/                  Step 2 Python environment (created by you, not committed)
└── src_maf/                      AI solution (later step)
```

## Quick start (after the first setup)

**Windows (PowerShell):** start Docker Desktop, wait until it shows *Engine running*, then:

```powershell
Set-Location "$([Environment]::GetFolderPath('MyDocuments'))\FDE_PB_Sol"
docker compose -f legacy_system/docker-compose.yml --env-file .env up -d --wait
.\venv_legacy\Scripts\python.exe -m streamlit run legacy_system/bi_dashboard/app.py --server.port 8502 --server.address localhost --server.headless true --browser.gatherUsageStats false --client.toolbarMode minimal
```

**macOS (Terminal):**

```bash
cd ~/Documents/FDE_PB_Sol
open -a Docker
until docker info >/dev/null 2>&1; do echo "waiting for Docker to start..."; sleep 3; done
docker compose -f legacy_system/docker-compose.yml --env-file .env up -d --wait
./venv_legacy/bin/python -m streamlit run legacy_system/bi_dashboard/app.py --server.port 8502 --server.address localhost --server.headless true --browser.gatherUsageStats false --client.toolbarMode minimal
```

Then open <http://localhost:8502> and log in as `bi_analyst`.

## Data

- **Source:** Kaggle, *Logistics and Supply Chain Dataset* by datasetengineer (see `data/source/data.txt`).
- **Content:** 32,065 hourly readings, 1 Jan 2021 00:00 to 29 Aug 2024 00:00, 26 columns, no missing values, no truck or shipment ID.
- **Legacy table:** `legacy_fleet.TBL_SC_FLEET_HIST_RAW` keeps all 26 columns under cryptic legacy names (mapping in Appendix A of the Step 1 guide).
