# -*- coding: utf-8 -*-
"""Wide, large-type boards for the 5-slide overview deck."""
import os, sys
from miro_engine import MiroBoard, CORAL, INK, MUTED, _font

OUT = sys.argv[1] if len(sys.argv) > 1 else "assets/diagrams"
os.makedirs(OUT, exist_ok=True)


def chip(b, card, text, size=24):
    x, y, w, h = card
    f = _font(b._S(size), bold=True)
    tw = b.d.textlength(text, font=f); pad = b._S(10)
    asc, desc = f.getmetrics()
    x1, y1 = b._S(x + w - 14), b._S(y + h - 14)
    box = [x1 - tw - 2 * pad, y1 - (asc + desc) - pad, x1, y1]
    b.d.rounded_rectangle(box, radius=b._S(9), fill=(*CORAL, 255))
    b.d.text((box[0] + pad, box[1] + pad / 2), text, font=f, fill=(255, 255, 255, 255))


def w1_legacy():
    b = MiroBoard(2400, 830)
    for x, t in [(60, "DATA SOURCES"), (720, "STORAGE"), (1380, "REPORTING & DECISION"), (2010, "OUTSIDE")]:
        b.label(x, 40, t, 26, MUTED, True)
    gps = b.card(60, 95, 520, 205, "GPS data", "Location · route · speed", title_size=38, body_size=32)
    sen = b.card(60, 330, 520, 205, "Truck sensors", "Temperature · fuel · engine", title_size=38, body_size=32)
    rte = b.card(60, 565, 520, 205, "Route telemetry", "Distance · stops · travel time", title_size=38, body_size=32)
    db = b.card(720, 250, 520, 340, "Legacy database",
                "SQL Server 2022. ID + password only. No API. Cryptic column names.",
                accent=True, title_size=38, body_size=32)
    dash = b.card(1380, 95, 520, 300, "BI dashboard", "Fixed reports, charts and KPIs",
                  accent=True, title_size=38, body_size=32)
    ana = b.card(1380, 470, 520, 300, "Dispatcher", "\"Where are my trucks? Any risk?\" Decides by hand.",
                 title_size=38, body_size=32)
    out = b.card(2010, 300, 340, 400, "By hand", "SOP files, weather website, phone calls.",
                 sticky=True, body_size=32)
    for s in (gps, sen, rte):
        b.connect(s, db)
    b.connect(db, dash, label="reports")
    b.connect(dash, ana)
    b.connect(out, ana, dashed=True)
    return b.save(os.path.join(OUT, "w1_legacy.png"))


def w3_night_shift():
    b = MiroBoard(2400, 830)
    steps = [("Driver", "1 · Call", "Cargo is warming", "P1"),
             ("Dispatcher", "2 · Log in", "ID + password", "P2 P10"),
             ("Database / BI", "3 · Find truck", "Coded labels, fixed reports", "P2 P3 P4 P7"),
             ("SOP files", "4 · Find rule", "Maybe an old copy", "P5"),
             ("Website", "5 · Weather", "Separate site", "P6"),
             ("Dispatcher", "6 · Decide", "Cool, divert or call?", "P1 P9"),
             ("Tier 2", "7 · Escalate", "Phone call", "P1 P8")]
    W, gap, x0 = 300, 30, 60
    cards = []
    for i, (who, t, body, pain) in enumerate(steps):
        x = x0 + i * (W + gap)
        b.label(x + 4, 60, who, 28, CORAL, True)
        c = b.card(x, 120, W, 360, t, body, title_size=36, body_size=30)
        chip(b, c, pain, 26)
        cards.append(c)
    for a, c in zip(cards, cards[1:]):
        b.connect(a, c)
    b.card(60, 600, 1090, 150, None, "Meanwhile the cargo keeps warming.", sticky=True, body_size=36)
    b.card(1250, 600, 1090, 150, None, "No record is kept of how the decision was made.", sticky=True, body_size=36)
    return b.save(os.path.join(OUT, "w3_night_shift.png"))


def w4_pain():
    b = MiroBoard(2400, 860)
    T, B = 28, 30
    b.group(40, 70, 700, 760, label="Getting answers · Sarah, Emily")
    b.group(770, 70, 640, 760, label="Seeing the risk · Sarah")
    b.group(1440, 70, 380, 760, label="Rules & trust · Tom")
    b.group(1850, 70, 510, 760, label="Platform · Mike")
    def pc(x, y, w, h, t, body): return b.card(x, y, w, h, t, body, title_size=T, body_size=B)
    pc(70, 130, 310, 330, "P1 Manual chain", "One step after another")
    pc(400, 130, 310, 330, "P2 Few experts", "29 cryptic column names")
    pc(70, 480, 310, 320, "P3 Fixed reports", "New question = new report")
    pc(400, 480, 310, 320, "P9 Uneven calls", "Night shift decides differently")
    pc(800, 130, 580, 330, "P4 Averages hide breaches", "Average 0.04 °C, yet 8,674 readings above 4 °C")
    pc(800, 480, 280, 320, "P7 No places", "Coordinates only, no truck ID")
    pc(1100, 480, 280, 320, "P6 No weather", "Checked on another website")
    pc(1470, 130, 320, 330, "P5 Rules outside", "SOP files, sometimes old copies")
    pc(1470, 480, 320, 320, "P8 No audit trail", "No record of decisions")
    pc(1880, 130, 450, 330, "P10 Closed system", "ID + password, no API, cannot be replaced")
    b.card(1880, 480, 450, 320, "Finding", "68% of readings are below zero, and no rule covers them.",
           sticky=True, body_size=30)
    return b.save(os.path.join(OUT, "w4_pain.png"))


if __name__ == "__main__":
    for fn in (w1_legacy, w3_night_shift, w4_pain):
        print(fn())
