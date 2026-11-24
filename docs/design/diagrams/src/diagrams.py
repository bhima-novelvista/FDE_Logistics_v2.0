# -*- coding: utf-8 -*-
"""Diagrams for the Legacy System v1.0 document set (HLD, LLD, Business Proposal, deck)."""
import os, sys
from miro_engine import MiroBoard, CORAL, INK, MUTED

OUT = sys.argv[1] if len(sys.argv) > 1 else "assets/diagrams"
os.makedirs(OUT, exist_ok=True)
T, B = 30, 25          # default card title / body sizes for a 1600-px board


def legacy_block():
    """D1: the legacy half of the architecture diagram, redrawn (all four deliverables)."""
    b = MiroBoard(1600, 1040)
    b.label(60, 36, "The legacy system today: data is stored, viewed and analysed by hand", 33, INK, True)
    for x, t in [(60, "DATA SOURCES"), (600, "STORAGE"), (1100, "REPORTING & DECISION")]:
        b.label(x, 112, t, 22, MUTED, True)
    gps = b.card(60, 160, 430, 175, "GPS data", "Location · route · speed", title_size=T, body_size=B)
    sen = b.card(60, 370, 430, 175, "Truck sensors", "Temperature · fuel · engine health", title_size=T, body_size=B)
    rte = b.card(60, 580, 430, 175, "Route telemetry", "Distance · stops · travel time", title_size=T, body_size=B)
    db = b.card(600, 250, 410, 400, "Legacy database",
                "Client: Microsoft SQL Server 2022. v1.0 replica: MySQL 8.4 in Docker. "
                "ID + password only, no API, cryptic column names.",
                accent=True, title_size=T, body_size=B)
    dash = b.card(1110, 160, 430, 250, "BI dashboard",
                  "Static reports, charts and KPIs. Fixed filters. No real-time reasoning.",
                  accent=True, title_size=T, body_size=B)
    ana = b.card(1110, 480, 430, 275, "Analyst / dispatcher",
                 "\"Where are my trucks? Any risk? Let me check the dashboard...\" Manual analysis.",
                 title_size=T, body_size=B)
    out = b.card(600, 690, 410, 150, "Outside the system",
                 "SOP files · weather website · phone calls", sticky=True, body_size=B)
    for s in (gps, sen, rte):
        b.connect(s, db)
    b.connect(db, dash, label="reports")
    b.connect(dash, ana, label="manual review")
    b.connect(out, ana, label="looked up by hand", dashed=True)
    b.card(60, 880, 1480, 120, "Limitations",
           "Manual analysis and queries · static dashboards · no external data (weather) · "
           "no access to company SOPs · no audit trail · limited scalability", sticky=True, body_size=B)
    return b.save(os.path.join(OUT, "d1_legacy_block.png"))


def as_built():
    """D2: the v1.0 replica as built (HLD, LLD)."""
    b = MiroBoard(1600, 900)
    b.label(60, 36, "Legacy system v1.0 as built (replica of the client's set-up)", 33, INK, True)
    csv = b.card(40, 210, 320, 280, "Source data",
                 "Kaggle CSV: 32,065 hourly readings, 26 columns. Mounted read-only.",
                 title_size=T, body_size=B)
    b.card(40, 560, 320, 270, "Set-up scripts",
           "create_env, 01-04 SQL, run_sql.sh. Run inside fde-mysql as root.", sticky=True, body_size=B)
    b.group(520, 150, 520, 680, label="Docker Desktop")
    my = b.card(550, 220, 460, 300, "fde-mysql: MySQL 8.4",
                "Database legacy_fleet, table TBL_SC_FLEET_HIST_RAW (29 columns). Port 127.0.0.1:3306.",
                accent=True, title_size=T, body_size=B)
    vol = b.card(550, 620, 460, 160, "Volume fde_mysql_data", "Data survives restarts",
                 title_size=T, body_size=B)
    dash = b.card(1170, 220, 380, 300, "BI dashboard",
                  "Streamlit app.py, port 8502. Logs in as bi_analyst (read-only).",
                  accent=True, title_size=T, body_size=B)
    brw = b.card(1170, 620, 380, 160, "Analyst's browser", "http://localhost:8502",
                 title_size=T, body_size=B)
    b.connect(csv, my, label="LOAD DATA")
    b.connect(my, vol, arrow="none")
    b.connect(dash, my, label="SELECT")
    b.connect(brw, dash, label="clicks")
    return b.save(os.path.join(OUT, "d2_as_built.png"))


def _chip(b, card, text):
    """Small coral pain-point chip at the bottom-right inside a card."""
    from miro_engine import _font
    x, y, w, h = card
    f = _font(b._S(19), bold=True)
    tw = b.d.textlength(text, font=f)
    pad = b._S(9)
    x1 = b._S(x + w - 12); y1 = b._S(y + h - 12)
    asc, desc = f.getmetrics()
    box = [x1 - tw - 2 * pad, y1 - (asc + desc) - pad, x1, y1]
    b.d.rounded_rectangle(box, radius=b._S(8), fill=(*CORAL, 255))
    b.d.text((box[0] + pad, box[1] + pad / 2), text, font=f, fill=(255, 255, 255, 255))


def night_shift():
    """D3: today's incident handling as vertical swim lanes, pain points marked."""
    b = MiroBoard(1600, 1620)
    b.label(50, 30, "One night shift today: seven manual steps across five places", 33, INK, True)
    lanes = ["Driver", "Database / BI", "Outside system", "Dispatcher", "Tier 2 manager"]
    lx0, lw, lg, ytop = 40, 296, 10, 130
    for i, name in enumerate(lanes):
        b.group(lx0 + i * (lw + lg), ytop, lw, 1450, label=name)
    W, H = 256, 168
    def st(lane, row, title, body, pain):
        c = b.card(lx0 + lane * (lw + lg) + 20, 190 + row * 196, W, H, title, body,
                   title_size=26, body_size=22)
        _chip(b, c, pain)
        return c
    s1 = st(0, 0, "1 · Call", "Cargo drifting above 0-4 °C", "P1")
    s2 = st(3, 1, "2 · Log in", "ID + password, trained staff", "P2 P10")
    s3 = st(1, 2, "3 · Find truck", "Coded labels, fixed reports", "P2 P3 P4 P7")
    s4 = st(2, 3, "4 · Find rule", "SOP files, maybe old copy", "P5")
    s5 = st(2, 4, "5 · Weather", "Separate website", "P6")
    s6 = st(3, 5, "6 · Decide", "Cool, divert or call Tier 2?", "P1 P9")
    s7 = st(4, 6, "7 · Escalate", "Phone call to Tier 2", "P1")
    for a, c in [(s1, s2), (s2, s3), (s3, s4), (s4, s5), (s5, s6), (s6, s7)]:
        b.connect(a, c)
    b.card(lx0 + 20, 190 + 2 * 196, W, 300, None, "Meanwhile the cargo keeps warming.",
           sticky=True, body_size=24)
    b.card(lx0 + 4 * (lw + lg) + 20, 190 + 1 * 196, W, 380, None,
           "No record is kept of how the decision was made (P8).", sticky=True, body_size=24)
    return b.save(os.path.join(OUT, "d3_night_shift.png"))


def pain_map():
    """D4: the ten pain points, grouped by who feels them."""
    b = MiroBoard(1600, 1140)
    b.label(60, 30, "Ten pain points, grouped by who feels them", 33, INK, True)
    b.group(40, 130, 770, 520, label="Getting answers (Sarah, Emily)")
    b.group(850, 130, 710, 520, label="Seeing the risk (Sarah)")
    b.group(40, 720, 770, 380, label="Rules and trust (Tom, Sarah)")
    b.group(850, 720, 710, 380, label="The platform (Mike)")
    cw, ch = 345, 210
    def pc(x, y, t, body, w=cw, h=ch):
        return b.card(x, y, w, h, t, body, title_size=24, body_size=21)
    pc(70, 180, "P1 · Manual chain", "Call, log in, dashboards, SOP files, weather, decide: one step after another.")
    pc(435, 180, "P2 · Few experts", "Coded labels only trained staff understand. 29 cryptic columns.")
    pc(70, 415, "P3 · Fixed dashboards", "Every new question means a new report or hand-written SQL.")
    pc(435, 415, "P9 · Uneven decisions", "New night-shift staff may not make the same call.")
    pc(880, 180, "P4 · Averages hide breaches", "Average 0.04 °C, yet 8,674 readings are above 4 °C.", w=655)
    pc(880, 415, "P7 · No place names", "Coordinates only; no truck or shipment ID.", w=320)
    pc(1215, 415, "P6 · No outside data", "Weather is checked on a separate website.", w=320)
    pc(70, 770, "P5 · Rules outside", "SOPs spread across files; sometimes an old copy.", h=200)
    pc(435, 770, "P8 · No audit trail", "Nobody can show how a decision was made.", h=200)
    pc(880, 770, "P10 · Closed system", "SQL Server, ID + password, no API. Cannot be replaced; must stay read-only.",
       w=655, h=150)
    b.card(880, 945, 655, 120, None,
           "Finding: 68% of readings are below 0 °C, and the SOP has no rule for them.",
           sticky=True, body_size=22)
    return b.save(os.path.join(OUT, "d4_pain_map.png"))


def load_flow():
    """D7 (LLD): how the CSV becomes the legacy table, and how it is checked."""
    b = MiroBoard(1600, 760)
    b.label(60, 30, "Building and loading the legacy table (run as root inside the container)", 31, INK, True)
    s1 = b.card(60, 140, 330, 220, "01 Schema", "Database legacy_fleet, 29-column raw table", title_size=T, body_size=B)
    s2 = b.card(450, 140, 330, 220, "02 Login", "bi_analyst: SELECT on legacy_fleet.*", title_size=T, body_size=B)
    b.card(840, 140, 700, 220, "run_sql.sh",
           "Reads the root password from the container, writes it to a private temporary file, runs one SQL file.",
           sticky=True, body_size=24)
    csv = b.card(60, 470, 330, 230, "CSV (read-only)", "/import/raw in the container", title_size=T, body_size=B)
    s3 = b.card(450, 470, 330, 230, "03 Load", "TRUNCATE, then LOAD DATA LOCAL (26 columns)", accent=True, title_size=T, body_size=B)
    tbl = b.card(840, 470, 330, 230, "Raw table", "32,065 rows, 0 warnings", title_size=T, body_size=B)
    s4 = b.card(1230, 470, 310, 230, "04 Verify", "13 PASS / FAIL checks", accent=True, title_size=T, body_size=B)
    b.connect(s1, s2); b.connect(s2, s3)
    b.connect(csv, s3, label="reads")
    b.connect(s3, tbl, label="writes")
    b.connect(tbl, s4, label="checked")
    return b.save(os.path.join(OUT, "d7_load_flow.png"))


def db_access():
    """D8 (LLD): who can do what in the legacy database."""
    b = MiroBoard(1600, 820)
    b.label(60, 30, "Database access: two logins, one of them read-only", 33, INK, True)
    root = b.card(60, 150, 420, 240, "root (admin)", "Set-up scripts only, via run_sql.sh inside the container",
                  accent=True, title_size=T, body_size=B)
    bi = b.card(60, 470, 420, 260, "bi_analyst (read-only)", "BI dashboard, SQL console, desktop tools",
                accent=True, title_size=T, body_size=B)
    db = b.card(640, 280, 420, 300, "legacy_fleet", "TBL_SC_FLEET_HIST_RAW. Port 127.0.0.1:3306 (this computer only).",
                title_size=T, body_size=B)
    ok = b.card(1180, 150, 360, 220, "Allowed", "SELECT on every table in legacy_fleet", title_size=T, body_size=B)
    no = b.card(1180, 450, 360, 250, "Refused", "INSERT, UPDATE, DELETE, DROP: ERROR 1142", sticky=True, body_size=B)
    b.connect(root, db, label="all rights")
    b.connect(bi, db, label="SELECT")
    b.connect(db, ok, arrow="none", dashed=True)
    b.connect(db, no, arrow="none", dashed=True)
    return b.save(os.path.join(OUT, "d8_db_access.png"))


def deployment():
    """D9 (HLD): where everything runs. Windows first."""
    b = MiroBoard(1600, 900)
    b.label(60, 30, "Deployment: one computer, Windows first (macOS works the same way)", 33, INK, True)
    b.group(40, 130, 1520, 600, label="Windows 10/11 PC (primary)")
    b.group(80, 210, 560, 470, label="Docker Desktop on WSL 2")
    my = b.card(120, 280, 480, 220, "fde-mysql", "MySQL 8.4 container, 127.0.0.1:3306", accent=True, title_size=T, body_size=B)
    vol = b.card(120, 540, 480, 110, "fde_mysql_data", None, title_size=26, body_size=B)
    b.group(700, 210, 400, 470, label="Python venv_legacy")
    st = b.card(740, 280, 320, 220, "Streamlit", "app.py on localhost:8502", accent=True, title_size=T, body_size=B)
    br = b.card(1160, 280, 360, 220, "Browser", "Analyst opens localhost:8502", title_size=T, body_size=B)
    fol = b.card(1160, 540, 360, 140, "Documents\\FDE_PB_Sol", ".env, data, scripts, docs", title_size=24, body_size=22)
    b.connect(st, my, label="SQL")
    b.connect(br, st, label="HTTP")
    b.connect(my, vol, arrow="none")
    b.card(40, 770, 1520, 100, None,
           "macOS: the same layout with Docker Desktop for Apple Silicon and the Terminal commands in the guides. "
           "Nothing is reachable from the network.", sticky=True, body_size=23)
    return b.save(os.path.join(OUT, "d9_deployment.png"))


def dashboard_modules():
    """D10 (LLD): inside app.py."""
    b = MiroBoard(1600, 900)
    b.label(60, 30, "Inside the BI dashboard (legacy_system/bi_dashboard/app.py)", 33, INK, True)
    s1 = b.card(60, 140, 330, 200, "1 Settings", ".env, LABELS, column lists", title_size=T, body_size=B)
    s3 = b.card(60, 400, 330, 200, "3 Login", "login_page(), connect()", title_size=T, body_size=B)
    s5 = b.card(60, 660, 330, 190, "5 Main", "Login first, then sidebar + page", title_size=T, body_size=B)
    pg = b.card(470, 260, 400, 470, "4 Report pages",
                "Fleet Overview · Where are my trucks? · Risk & Delay · Operations · SQL console",
                accent=True, title_size=T, body_size=B)
    rq = b.card(930, 140, 300, 230, "2 run_query()", "Runs one SELECT, records it", accent=True, title_size=T, body_size=B)
    db = b.card(1290, 140, 260, 230, "MySQL", "as bi_analyst", title_size=T, body_size=B)
    log = b.card(930, 460, 300, 190, "QUERY_LOG", "SQL, rows, ms", title_size=T, body_size=B)
    bp = b.card(1290, 460, 260, 270, "Back-end panel", "What happened at the back end", title_size=24, body_size=23)
    b.connect(s5, s3); b.connect(s3, s1, arrow="none", dashed=True)
    b.connect(s5, pg); b.connect(pg, rq); b.connect(rq, db, label="SQL")
    b.connect(rq, log); b.connect(log, bp)
    return b.save(os.path.join(OUT, "d10_dashboard_modules.png"))


if __name__ == "__main__":
    for fn in (legacy_block, as_built, night_shift, pain_map, load_flow, db_access, deployment, dashboard_modules):
        print(fn())
