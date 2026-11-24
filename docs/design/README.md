# Design pack v1.0 — Legacy fleet system (current state)

Date: 24 Nov 2026. Scope: the legacy system only (how it works today and its pain points).
The AI phase is v2.0 and is not covered here.

| File | What it is |
|---|---|
| `Legacy_Fleet_System_HLD_v1.0.docx` | High-level design, 19 pages |
| `Legacy_Fleet_System_LLD_v1.0.docx` | Low-level design, 16 pages |
| `Legacy_Fleet_System_Business_Proposal_v1.0.docx` | Business proposal, 11 pages |
| `Legacy_Fleet_System_Overview_v1.0.pptx` | 5-slide overview deck with speaker notes |
| `pdf/` | PDF copies of all four, for quick review |
| `diagrams/` | Every diagram as PNG (d1–d11 for the documents, w1–w5 for the slides) |
| `diagrams/src/` | Diagram sources: Pillow board scripts, matplotlib charts, Mermaid files |
| `src/` | The scripts that built the documents and the deck |

Harborline Cold Chain and its people are fictional. The numbers come from the real
dataset loaded in `legacy_fleet.TBL_SC_FLEET_HIST_RAW` (32,065 hourly readings).

## Re-rendering the diagrams (optional)

The scripts were run in Claude's Linux workspace, so image paths inside `src/*.js` and
`src/build_deck.py` point there; change the path constant at the top of each file first.
On Windows and macOS the boards pick up Calibri or Arial instead of DejaVu Sans, so line
breaks can shift slightly: look at each PNG after re-rendering.

**Windows (PowerShell)**
```powershell
cd $HOME\Documents\FDE_PB_Sol\docs\design\diagrams\src
py -m pip install pillow matplotlib
py diagrams.py ..\
py deck_diagrams.py ..\
py chart_d5.py ..\d5_averages_hide_breaches.png
```

**macOS (Terminal)**
```bash
cd ~/Documents/FDE_PB_Sol/docs/design/diagrams/src
python3 -m pip install pillow matplotlib
python3 diagrams.py ../
python3 deck_diagrams.py ../
python3 chart_d5.py ../d5_averages_hide_breaches.png
```

Mermaid files (`mmd/*.mmd`) render with the Mermaid CLI:
`npx -y @mermaid-js/mermaid-cli -i mmd/d6_seq_today.mmd -o ../d6_seq_today.png -c mmd/theme.json -b "#FBFAF8" -s 2 -w 1500`
