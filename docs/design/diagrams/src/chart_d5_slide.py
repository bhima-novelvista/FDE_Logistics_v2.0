# D5 slide variant: same real counts, larger type, no title (the slide title carries it)
import sys, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker
out = sys.argv[1]
PAPER, INK, MUTED, CORAL, GREY = "#FBFAF8", "#21201E", "#6E6A64", "#D97757", "#B9B3AA"
bands = ["Below 0 °C", "0 to 4 °C\n(SOP range)", "Above 4 °C\n(breach)"]
counts = [21817, 1574, 8674]; total = 32065
plt.rcParams.update({"font.family": "DejaVu Sans"})
fig, ax = plt.subplots(figsize=(7, 4.4), dpi=200)
fig.patch.set_facecolor(PAPER); ax.set_facecolor(PAPER)
bars = ax.bar(bands, counts, color=[GREY, GREY, CORAL], width=0.62, zorder=3)
for b, c in zip(bars, counts):
    ax.text(b.get_x() + b.get_width()/2, c + 600, f"{c:,}\n{c/total:.1%}", ha="center",
            va="bottom", fontsize=17, color=INK, fontweight="bold", linespacing=1.1)
ax.set_ylim(0, 29000)
ax.set_yticks([])
ax.tick_params(axis="x", colors=INK, labelsize=16, length=0, pad=8)
for s in ("top", "right", "left"): ax.spines[s].set_visible(False)
ax.spines["bottom"].set_color(GREY)
fig.text(0.01, 0.015, "All 32,065 hourly readings, Jan 2021 to Aug 2024", fontsize=12, color=MUTED)
fig.tight_layout(rect=(0, 0.05, 1, 1))
fig.savefig(out, facecolor=PAPER)
print(out)
