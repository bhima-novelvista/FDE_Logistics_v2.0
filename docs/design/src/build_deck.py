# -*- coding: utf-8 -*-
"""Legacy Fleet System v1.0 overview deck (5 slides)."""
import sys, os
from PIL import Image
from pptx.util import Pt, Emu
from pptx.enum.text import MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from deck_engine import Deck, LEFT, CWIDTH, PAPER, INK, CORAL, MUTED, _rgb

OUT = sys.argv[1] if len(sys.argv) > 1 else "../out/Legacy_Fleet_System_Overview_v1.0.pptx"
D = "/home/claude/legacy_docs/assets/diagrams/"

d = Deck()

# ---------- 1. Title ----------
d.title_slide(
    "Harborline Cold Chain  ·  Legacy fleet system  ·  v1.0",
    ["How the legacy fleet", "system works today"],
    "Current state and pain points of the cold-chain control tower, Southern California.  "
    "24 Nov 2026.  Harborline and its people are fictional; the sensor data is a real public dataset.",
    notes_intro=(
        "Good afternoon. In the next few minutes I want to show you how Harborline's cold-chain fleet "
        "system works today, before anyone changes anything. Harborline runs refrigerated trucks out of a "
        "control tower in Southern California, and the promise to every customer is simple: the cargo stays "
        "between zero and four degrees Celsius from pickup to delivery. "
        "This is version 1.0 of our design pack, and it covers the legacy system only. There are three "
        "documents behind this deck, the high-level design, the low-level design and the business proposal, "
        "and this deck is the short version of all three. "
        "One honest note before we start: Harborline and the people you will hear about are fictional, "
        "but every number I show you comes from a real public dataset of about thirty-two thousand truck "
        "readings that we loaded into a working replica of the legacy database."
    ),
)

# ---------- 2. Legacy at a glance ----------
d.diagram(
    "The legacy system at a glance",
    "Three data feeds, one closed database, fixed reports,\nand every decision made by hand",
    D + "w1_legacy.png",
    caption="32,065 hourly readings, Jan 2021 to Aug 2024  ·  26 coded columns  ·  "
            "replica: MySQL 8.4 in Docker, read-only login",
    notes_intro=(
        "This is the whole legacy system on one page, and it reads from left to right. "
        "On the left are the three data feeds. GPS gives the location, the route and the speed. The truck "
        "sensors give the cargo temperature, the fuel and the engine readings. Route telemetry gives "
        "distance, stops and travel time. "
        "All three land in one place in the middle, the legacy database. At Harborline that is SQL Server "
        "2022. It opens with an ID and a password only, there is no API, and the column names are codes "
        "like I-O-T temp val C rather than plain words, so only a few people can read it. "
        "Out of the database comes the BI dashboard: fixed reports, charts and KPIs. If you want a question "
        "that the dashboard was not built for, someone has to build a new report. "
        "And then there is the dispatcher, who is really asking two things: where are my trucks, and is "
        "anything at risk? To answer that, the dispatcher also needs the things on the right that sit "
        "outside the system completely: the SOP files with the company's rules, a weather website, and "
        "phone calls. All of that is looked up and combined by hand. "
        "To study this safely we built a replica of it: MySQL 8.4 in Docker, loaded with the same thirty-two "
        "thousand and sixty-five hourly readings from January 2021 to August 2024, plus a simple dashboard "
        "that uses a read-only login. Nothing in the replica can change the data. "
        "(If they ask why MySQL and not SQL Server: the replica only needs to behave like a closed legacy "
        "store with coded column names and a password login. The table layout and the queries carry over "
        "to SQL Server unchanged.)"
    ),
)

# ---------- 3. One night shift ----------
d.diagram(
    "How it works today  ·  one night shift",
    "One temperature alarm: seven manual steps,\ntwo phone calls, and no record afterwards",
    D + "w3_night_shift.png",
    caption="Each coral tag shows the pain point that step exposes (P1 to P10, next slide).",
    notes_intro=(
        "Now let me show you how the system is actually used, with one real situation from the story. "
        "It is the night shift, and a driver calls in: the cargo is warming. That is step one, and it is "
        "already a phone call. "
        "Step two, the dispatcher logs in to the legacy system with an ID and a password. "
        "Step three, they try to find the truck. The labels are coded, the reports are fixed, the dashboard "
        "shows averages, and there is no truck ID and no place name in the data, only coordinates. That one "
        "step alone touches four of our pain points. "
        "Step four, they look for the rule. The SOP lives in files outside the system, and sometimes the copy "
        "on the shared drive is an old one. "
        "Step five, they open a separate website to check the weather on the route. "
        "Step six, they put all of that together in their head and decide: restart the cooling, divert the "
        "truck, or call someone. "
        "Step seven, if the risk is high, they phone the Tier 2 manager. "
        "And look at the two notes at the bottom, because they are the real cost. While all seven steps "
        "happen, the cargo keeps warming. And when it is over, nothing records how the decision was made, so "
        "the next morning nobody can say which rule was used or why. "
        "(If they ask how long this takes: the story does not give a measured time, so we have not put a "
        "number on it. Measuring the time from alarm to decision is one of the first things a pilot should "
        "do.)"
    ),
)

# ---------- 4. Ten pain points ----------
d.diagram(
    "Pain points",
    "Ten pain points, grouped by the person who feels them",
    D + "w4_pain.png",
    caption="Sources: the Harborline story and interviews, plus our own analysis of the 32,065 readings.",
    notes_intro=(
        "Here are the ten pain points from that night shift, grouped by the person who feels each one. "
        "On the left, getting answers, which is Sarah, the Tier 2 logistics manager, and Emily, who leads "
        "digital transformation. The process is a manual chain, one step after another. Only a few experts "
        "can read twenty-nine coded column names. The reports are fixed, so a new question means a new "
        "report. And decisions are uneven, because the night shift does not always decide the way the day "
        "shift would. "
        "Next, seeing the risk. The biggest one is P4: the averages hide the breaches. The average "
        "temperature across all the data is 0.04 degrees, which looks perfect, and yet more than eight "
        "thousand six hundred readings are above four degrees. The data also has no place names and no truck "
        "ID, and the weather has to be checked on another website. "
        "Third, rules and trust, which is Tom, the COO. The rules live outside the system, sometimes in old "
        "copies, and there is no audit trail of what was decided. "
        "And on the right, the platform, which is Mike, the CIO. It is a closed system with an ID and a "
        "password, no API, and it cannot be replaced. "
        "The yellow note is something we found ourselves in the data: sixty-eight percent of all readings "
        "are below zero, and the SOP has no rule at all for cargo that is too cold. That is a gap in the "
        "rules, not just in the system."
    ),
)

# ---------- 5. What the data shows + the ask (custom, animated) ----------
s = d._slide(); d._bg(s, PAPER)
d._eyebrow(s, "What the data shows  ·  and the ask")
d._title(s, "The dashboard says all is well.\nThe readings say otherwise.", size=29)

spids = []
bw = 5150000
items = [
    ("Averages hide breaches: ", "the average is 0.04 °C, yet 95% of readings sit outside 0 to 4 °C."),
    ("A gap in the rules: ", "68% of readings are below 0 °C, and the SOP has no action for them."),
    ("Who and where: ", "no truck ID and no place names, only coordinates."),
]
y = 2250000
for lead, rest in items:
    tb, tf = d._textbox(s, LEFT, y, bw, 780000, anchor=MSO_ANCHOR.TOP)
    p = tf.paragraphs[0]; p.line_spacing = 1.06
    d._run(p, "▪   ", 17, CORAL, bold=True)
    d._run(p, lead, 17, INK, bold=True)
    d._run(p, rest, 17, INK)
    spids.append(tb.shape_id)
    y += 860000

# chart on the right, kept to its own aspect ratio (not animated)
img = D + "w5_temperature_bands.png"
iw, ih = Image.open(img).size
cw = 4900000; ch = int(cw * ih / iw)
cx = 12192000 - cw - 600000
d._pic(s, img, cx, 1900000, cw, ch)

# the ask: a coral bar plus the How-Might-We question
bar_y = 5000000
bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Emu(LEFT), Emu(bar_y), Emu(54000), Emu(1150000))
bar.fill.solid(); bar.fill.fore_color.rgb = _rgb(CORAL); bar.line.fill.background(); bar.shadow.inherit = False
tb, tf = d._textbox(s, LEFT + 260000, bar_y + 20000, CWIDTH - 260000, 1150000, anchor=MSO_ANCHOR.TOP)
p = tf.paragraphs[0]; p.line_spacing = 1.04
d._run(p, "THE ASK", 12, CORAL, bold=True, spc=200)
p2 = tf.add_paragraph(); p2.line_spacing = 1.04; p2.space_before = Pt(4)
d._run(p2, "How might we give every dispatcher one clear answer, backed by the company's rules, "
           "from the data you already have, without changing it?", 21, INK, bold=True, font="Cambria")
# the question fades in on the 4th click; the coral bar fades in with it (withEffect twin)
spids.append(tb.shape_id)
d._add_timing(s, spids)
from lxml import etree
import copy
P = "http://schemas.openxmlformats.org/presentationml/2006/main"
timing = s._element.find("{%s}timing" % P)
eff = [c for c in timing.iter("{%s}cTn" % P) if c.get("nodeType") == "clickEffect"][-1]
eff_par = eff.getparent()
twin = copy.deepcopy(eff_par)
max_id = max(int(c.get("id")) for c in timing.iter("{%s}cTn" % P))
for c in twin.iter("{%s}cTn" % P):
    max_id += 1; c.set("id", str(max_id))
twin.find("{%s}cTn" % P).set("nodeType", "withEffect")
for t in twin.iter("{%s}spTgt" % P):
    t.set("spid", str(bar.shape_id))
eff_par.addnext(twin)
bld = timing.find("{%s}bldLst" % P)
etree.SubElement(bld, "{%s}bldP" % P, spid=str(bar.shape_id), grpId="0", animBg="1")

d._notes(s,
    "Let me finish with what the data itself tells us, because this is where the legacy system's "
    "problems stop being opinions. The chart on the right is every one of the thirty-two thousand and "
    "sixty-five readings, sorted into three groups: below zero, inside the zero to four degree range the "
    "SOP asks for, and above four degrees, which the SOP calls a critical breach.",
    [
        "First, the averages hide the breaches. The dashboard average is 0.04 degrees, which sits right "
        "inside the safe range and looks like good news. But only about five percent of the readings are "
        "actually between zero and four. Ninety-five percent are outside it, and more than eight thousand "
        "six hundred are above four degrees. An average cannot show you that.",
        "Second, there is a gap in the rules themselves. Sixty-eight percent of the readings are below zero. "
        "The SOP says what to do when cargo is too warm, but it says nothing about cargo that is too cold. "
        "That is a question for Tom and the operations team, not for the technology.",
        "Third, the data cannot tell you who or where. There is no truck ID and there are no place names, "
        "only latitude and longitude, so even a perfect query cannot say which truck it is or which town it "
        "is near. (If they ask: positions also do not join up into routes, so the data is best read as "
        "hourly snapshots of the fleet rather than as individual trips.)",
        "So this is the question we are taking into the next phase, written in the client's own terms. How "
        "might we give every dispatcher one clear answer, backed by the company's rules, from the data you "
        "already have, without changing it? The constraints come with it: keep the database, read-only "
        "access, record every step, no lock-in to a single AI vendor, and work alongside the current "
        "system. That is version 2.0, the AI phase, and it is a separate conversation. Today's point is "
        "simply that the legacy system works, and this is exactly where it stops working. Thank you.",
    ],
)

os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
d.save(OUT)
print("saved", OUT)
