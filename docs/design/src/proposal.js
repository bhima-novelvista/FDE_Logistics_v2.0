// Business Proposal v1.0 - Legacy fleet system (Harborline Cold Chain, fictional)
const L = require("./doclib");
const { p, bullets, table, figure, note, h1, h2, h3, caption } = L;
const IMG = "/home/claude/legacy_docs/assets/docimg/";
const OUT = process.argv[2];

const meta = {
  client: "Harborline Cold Chain (fictional)", system: "Legacy Fleet System", title: "Business Proposal",
  short: "Business Proposal v1.0",
  tagline: "How our cold-chain operation runs today, what it costs us in time and trust, and the case for change.",
  fields: [
    ["Document", "Business Proposal"], ["Version", "1.0 (v1.0 Base Version)"], ["Date", "24 November 2026"],
    ["Status", "Baseline, for review"], ["Prepared by", "Forward Deployed Engineer (FDE)"],
    ["Prepared for", "Tom (COO), Sarah (Tier 2 Logistics Manager), Emily (Director of Digital Transformation), Mike (CIO)"],
    ["Companion documents", "HLD v1.0 · LLD v1.0 · Overview deck v1.0"],
  ],
};

const body = [
  ...L.cover(meta),
  ...L.docControl([["1.0", "24 Nov 2026", "Baseline", "First version. Describes the legacy system and its pain points, with evidence from a working replica and the fleet data. It proposes what any change must achieve and the next steps; it does not design the solution."]]),
  ...L.contents(["1. Executive summary", "2. Harborline today", "3. How the legacy system works", "4. A night shift, step by step",
    "5. Pain points", "6. What the data shows", "7. What must not change", "8. The case for change",
    "9. Measures to capture first", "10. Next steps", "11. FDE skills shown so far", "Appendix. Glossary and sources"]),

  h1("1. Executive summary"),
  p("Harborline's control tower runs cold-chain operations on an older SQL Server database and a set of fixed dashboards. The system holds a complete history and keeps the data safe, but **every incident is handled by hand**: a driver calls, a dispatcher logs in, reads coded labels and fixed dashboards, searches SOP files for the right rule, checks the weather on a separate website, decides, and phones the Tier 2 manager. The cargo keeps warming while this happens, decisions differ between experienced and new staff, and **nothing records how a decision was made**."),
  p("To study this safely, the FDE built a working **replica** of the legacy system (v1.0 Base Version) with the same characteristics and 32,065 hourly fleet readings. It confirms ten pain points and shows two facts the dashboards hide:"),
  ...bullets([
    "**Averages hide breaches.** The average cargo temperature is 0.04 °C, which looks safe, yet **8,674 readings (27.1%) are above 4 °C** and 95% are outside the 0 to 4 °C range.",
    "**A rule gap.** **68% of readings are below 0 °C**, and the SOP has no rule for them.",
  ]),
  p("This proposal asks the leadership team to agree the problem, the constraints any change must respect (keep the database, read only, record every step, no lock-in), the baseline measures to capture, and the next steps. **It makes no cost or saving claims**: no baseline figures exist yet, and Section 9 says how to get them."),

  h1("2. Harborline today"),
  p("Harborline Cold Chain (a fictional company) runs a control tower in Southern California. Screens track trucks carrying perishables between the ports and the inland depots. Fresh perishables must stay between **0.0 °C and 4.0 °C**."),
  p("On discovery day, four leaders described the problem in their own words:"),
  ...L.quote("We run our cold-chain operations on an older database and a set of dashboards that have served us for years, but spoilage and slow escalations are still costing us.", "Tom, Chief Operating Officer"),
  ...L.quote("Our system works, but it's slow, and only a few people really know how to get answers out of it.", "Sarah, Tier 2 Logistics Manager"),
  ...L.quote("We aren't sure whether the gap is in our data, our dashboards or our procedures, so we need help finding where automation would make the biggest difference.", "Emily, Director of Digital Transformation"),
  ...L.quote("We can't replace the existing database, our teams depend on it every day, and I don't want anything touching our data.", "Mike, Chief Information Officer"),

  h1("3. How the legacy system works"),
  p("The legacy system has three kinds of data, one database, one set of dashboards and one person who puts it all together. Company rules, the weather and the phone sit outside it."),
  ...figure(IMG + "d1_legacy_block.png", "The legacy system: data is stored, viewed and analysed by hand", 6.3),
  caption("Table", "The legacy system in plain words"),
  table(["Part", "What it is", "What it means for the dispatcher"], [
    ["Data sources", "GPS (location, route, speed), truck sensors (temperature, fuel, engine health), route telemetry (distance, stops, travel time)", "The facts exist, but only inside the database"],
    ["Legacy database", "Microsoft SQL Server 2022; user ID and password; no API", "Only trained staff can read it; other tools cannot connect"],
    ["BI dashboard", "Static reports, charts and KPIs with fixed filters", "Answers only the questions it was built for"],
    ["Analyst / dispatcher", "The person on shift", "Combines everything in their head"],
    ["Outside the system", "SOP files, a weather website, phone calls", "Looked up by hand, sometimes in an old copy"],
  ], [1.3, 2.7, 2.5]),
  h2("3.1 The replica we built to study it"),
  p("To see the system work without touching production, the FDE built a replica in the project folder **FDE_PB_Sol (v1.0 Base Version)**: a MySQL 8.4 database in Docker with the same cryptic column names and ID-and-password access, loaded with 32,065 hourly readings (1 Jan 2021 to 29 Aug 2024), and a BI dashboard with the same fixed reports. Every number in this proposal comes from it."),
  ...figure(IMG + "s2_02_overview.png", "The replica's Fleet Overview: fixed KPIs and charts (captured)", 5.4),

  h1("4. A night shift, step by step"),
  p("Sarah described a typical night. Seven manual steps across five places; the pain points from Section 5 are marked where they happen."),
  ...figure(IMG + "d3_night_shift.png", "One night shift today: seven manual steps across five places", 5.5),
  caption("Table", "What each step costs"),
  table(["Step", "What happens", "What it costs"], [
    ["1 Call", "The driver phones: the cargo is drifting above 0 to 4 °C", "The clock starts; the cargo is warming"],
    ["2 Log in", "ID and password to the old database", "Only trained staff can continue"],
    ["3 Find the truck", "Coded labels, fixed dashboards, coordinates instead of places", "Minutes of searching; averages hide the breach"],
    ["4 Find the rule", "SOP documents, spreadsheets and text files", "Risk of an old or wrong rule"],
    ["5 Check weather", "A separate website", "Another tool, another delay"],
    ["6 Decide", "Restart the cooling, divert, or call Tier 2", "Depends on who is on shift"],
    ["7 Escalate", "Phone call to the Tier 2 manager", "No record of how the decision was made"],
  ], [1.1, 2.8, 2.6]),

  h1("5. Pain points"),
  ...figure(IMG + "d4_pain_map.png", "Ten pain points, grouped by who feels them", 6.3),
  caption("Table", "Pain points, business impact and evidence"),
  table(["ID", "Pain point", "Who feels it", "Business impact", "Evidence"], [
    ["P1", "Incident handling is a manual chain", "Sarah, Tom", "Slow response; the cargo warms at every hand-off", "Story; architecture diagram"],
    ["P2", "Only a few people can get answers", "Sarah", "Dependence on experts; a bottleneck at night", "29 cryptic columns, no descriptions"],
    ["P3", "Dashboards show only what they were built for", "Sarah, Emily", "Every new question waits for a new report", "Fixed reports; SQL needed otherwise"],
    ["P4", "Averages hide breaches", "Sarah", "Breaches go unseen until someone calls", "0.04 °C average vs 8,674 readings above 4 °C"],
    ["P5", "Rules live outside the system", "Sarah, Emily", "Wrong or outdated rules applied", "Thresholds typed by hand; old SOP copies"],
    ["P6", "No outside data", "Sarah", "Weather risk checked late or not at all", "Separate weather website"],
    ["P7", "No place names, no truck ID", "Sarah", "\"Where are my trucks?\" is hard to answer", "Coordinates only; no ID column"],
    ["P8", "No audit trail", "Tom", "Spoilage cannot be traced to a decision", "Nothing is recorded"],
    ["P9", "Uneven decisions", "Sarah", "Night-shift calls differ from experts' calls", "Story"],
    ["P10", "Closed system", "Mike", "No safe way to add new tools", "SQL Server; ID and password; no API"],
  ], [0.45, 1.7, 0.9, 2, 1.8], { size: 17 }),

  h1("6. What the data shows"),
  ...figure(IMG + "d5_averages_hide_breaches.png", "Averages hide breaches: readings per temperature band (captured)", 6.2),
  caption("Table", "Findings from 32,065 readings"),
  table(["Finding", "Number (captured)", "Why it matters"], [
    ["The average looks safe", "0.04 °C", "A dashboard tile gives no warning"],
    ["Readings above 4 °C (critical breach under the SOP)", "8,674 (27.1%)", "Each one needs action under the SOP"],
    ["Readings below 0 °C", "21,817 (68.0%)", "The SOP has no rule for them: operations must agree one"],
    ["Readings inside 0 to 4 °C", "1,574 (4.9%)", "Only 1 in 20 readings is in the safe range"],
    ["High Risk readings", "23,944 (74.7%)", "Most of the fleet is flagged High Risk"],
    ["High Risk with delay probability above 0.65 (Tier 2 trigger)", "15,440", "About 11 a day on average; today each one is a phone call"],
    ["High Risk, above 4 °C and delay above 0.65", "4,209", "The most urgent group, found only with hand-typed thresholds"],
  ], [2.6, 1.4, 2.6]),
  note("Note:", "The data is a public dataset used in the replica; the patterns, not the exact figures, are what Harborline should check against its own production data."),

  h1("7. What must not change"),
  h2("7.1 Constraints from the leadership team"),
  caption("Table", "Constraints any change must respect"),
  table(["ID", "Constraint", "Raised by"], [
    ["C1", "The existing database stays; it cannot be replaced", "Mike"],
    ["C2", "Anything new reads the data and never writes to it", "Mike"],
    ["C3", "Every step taken to reach an answer is recorded", "Mike, Tom"],
    ["C4", "No dependence on a single AI company", "Mike"],
    ["C5", "It works alongside the existing set-up", "Mike"],
  ], [0.5, 4.5, 1.2]),
  h2("7.2 What works and should be kept"),
  ...bullets([
    "**A complete, clean history:** every reading is there, with no missing values.",
    "**Safe access:** ID and password only, with read-only logins for analysts (proved in the replica: any change is refused).",
    "**Familiar screens:** dispatchers know the dashboards; new help should sit beside them.",
  ]),

  h1("8. The case for change"),
  p("The database is not the problem: in the replica its queries take milliseconds. **The process around it is.** Data, rules and weather sit in different places, and a person must join them by hand, under time pressure, at night. That is why spoilage and slow escalations persist, why calls differ between staff, and why nobody can show how a decision was made."),
  p("The FDE summed up what any change must achieve in one question:"),
  ...L.quote("How might we give every dispatcher one clear answer, backed by the company's rules, from the data you already have, without changing it?", "The FDE, on discovery day"),
  caption("Table", "What good looks like"),
  table(["Need", "Closes pain points", "Respects"], [
    ["One answer that combines the truck readings, the conditions outside and the rule that applies", "P1, P5, P6", "C5"],
    ["Ask in plain words, including place names, without knowing the column names", "P2, P3, P7", "C1"],
    ["Breaches found by rule, not hidden in averages", "P4", "C2"],
    ["The same, rule-based answer for every dispatcher on every shift", "P9", "C3"],
    ["A record of every step and every answer", "P8", "C3"],
    ["Read-only, alongside the existing database, not tied to one vendor", "P10", "C1, C2, C4"],
  ], [3.8, 1.3, 1.2]),
  p("The architecture diagram's second part sketches one way to meet these needs: an AI assistant that reads the same database through a read-only view, looks up the SOPs, checks live weather and records every step. That is the **next phase (planned as v2.0)**; its design is in HLD v1.2 and will be confirmed after the steps below."),

  h1("9. Measures to capture first"),
  p("No baseline figures exist today, so no saving can be claimed. Before any change, capture these over two to four weeks, starting with the night-shift observation the FDE asked Sarah for:"),
  caption("Table", "Baseline measures"),
  table(["Measure", "How to capture it", "Owner"], [
    ["Time from the driver's call to a decision", "Observe shifts; note the call time and the decision time", "Sarah, FDE"],
    ["Share of escalations that follow the SOP", "Compare each escalation with the SOP rule", "Sarah"],
    ["Spoilage incidents per month and their value", "From incident and claims records", "Tom"],
    ["New-report requests to the technology team", "Count requests per month", "Emily"],
    ["Time to answer \"Where are my trucks near X?\"", "Timed test with a dispatcher on the dashboards", "FDE"],
  ], [2.4, 2.8, 1.1]),

  h1("10. Next steps"),
  caption("Table", "Proposed next steps"),
  table(["#", "Step", "Owner", "Outcome"], [
    ["1", "Sit with the night shift and watch the process", "FDE with Sarah's team", "Confirmed steps and first timings"],
    ["2", "Agree a rule for readings below 0 °C", "Sarah, operations", "The SOP gap closed"],
    ["3", "Confirm the read-only access path to SQL Server 2022", "Mike", "A read-only account and connection route"],
    ["4", "Collect the current SOP files and retire old copies", "Emily", "One source of rules"],
    ["5", "Capture the baseline measures (Section 9)", "Sarah, Tom, Emily", "Numbers to judge any change by"],
    ["6", "Decide the scope of the next phase (v2.0)", "Tom, with all four leaders", "Go / no-go and priorities"],
  ], [0.4, 2.8, 1.6, 2]),

  h1("11. FDE skills shown so far"),
  p("The 15 Forward Deployed Engineering Skills framework, rated on what v1.0 shows. **Strong** = done, with proof. **Partial** = started, with a named gap. **Not yet** = belongs to the next phase. The rating judges the evidence, not the people."),
  caption("Table", "Skills demonstrated in v1.0"),
  table(["Skill", "What the FDE did", "Rating"], [
    ["Customer Discovery & Context Mapping", "Met four leaders; mapped the night-shift process and the constraints", "Strong"],
    ["Problem Framing & Decomposition", "Ten pain points, six findings and one guiding question", "Strong"],
    ["Business Value & ROI Modelling", "Baseline measures defined; figures still to be captured", "Partial"],
    ["Data & Systems Integration", "A working, verified replica of the legacy system", "Strong"],
    ["Reliability, Security & Compliance", "Read-only access proved; audit trail still missing (it is a legacy gap)", "Partial"],
    ["Executive Storytelling & Demo Craft", "This proposal, the overview deck and a live replica", "Partial"],
    ["AI skills (model judgment, retrieval, agents)", "Belong to the next phase", "Not yet"],
  ], [2.3, 3.3, 0.8]),

  h1("Appendix. Glossary and sources"),
  caption("Table", "Glossary"),
  table(["Term", "Meaning"], [
    ["SOP", "Standard Operating Procedure: the company's written rules"],
    ["Tier 2", "The Tier 2 Logistics Manager, who handles escalated incidents"],
    ["BI dashboard", "Screens with fixed reports, charts and KPIs"],
    ["Replica", "A working copy of the legacy set-up, built to study it safely"],
    ["FDE", "Forward Deployed Engineer: works inside the client's operation to understand, design and build"],
  ], [1.2, 4.8]),
  p("**Sources:** The Story (Harborline discovery day); the architecture diagram, Part 1; Business Proposal v1.3 and HLD/LLD v1.2 (earlier problem statements and SOP rules); FDE_PB_Sol v1.0 Base Version (all numbers, captured)."),
];

L.build(OUT, meta, body);
