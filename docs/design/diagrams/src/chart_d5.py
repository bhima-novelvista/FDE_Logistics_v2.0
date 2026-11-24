# D5: averages hide breaches (real counts from the CSV / 13-point check)
import sys, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker
out = sys.argv[1]
PAPER, INK, MUTED, CORAL, GREY = "#FBFAF8", "#21201E", "#6E6A64", "#D97757", "#B9B3AA"
bands = ["Below 0 °C", "0 to 4 °C\n(the SOP range)", "Above 4 °C\n(critical breach)"]
counts = [21817, 1574, 8674]; total = 32065
plt.rcParams.update({"font.family": "DejaVu Sans"})
fig, ax = plt.subplots(figsize=(10, 4.6), dpi=180)
fig.patch.set_facecolor(PAPER); ax.set_facecolor(PAPER)
bars = ax.bar(bands, counts, color=[GREY, GREY, CORAL], width=0.58, zorder=3)
for b, c in zip(bars, counts):
    ax.text(b.get_x() + b.get_width()/2, c + 500, f"{c:,}  ({c/total:.1%})", ha="center",
            va="bottom", fontsize=13, color=INK, fontweight="bold")
ax.set_ylim(0, 26500)
ax.set_ylabel("Readings", color=MUTED, fontsize=12)
ax.tick_params(colors=INK, labelsize=12)
ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, p: f"{int(v):,}"))
ax.yaxis.grid(True, color="#E4E0D8", zorder=0); ax.set_axisbelow(True)
for s in ("top", "right", "left"): ax.spines[s].set_visible(False)
ax.spines["bottom"].set_color(GREY)
ax.set_title("The dashboard average says 0.04 °C. 95% of readings are outside 0 to 4 °C.",
             loc="left", fontsize=15, color=INK, fontweight="bold", pad=14)
fig.text(0.01, 0.01, "Source: legacy_fleet.TBL_SC_FLEET_HIST_RAW, 32,065 hourly readings, 1 Jan 2021 to 29 Aug 2024.",
         fontsize=10, color=MUTED)
fig.tight_layout(rect=(0, 0.04, 1, 1))
fig.savefig(out, facecolor=PAPER)
print(out)
