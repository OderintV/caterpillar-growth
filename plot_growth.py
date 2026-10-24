"""Plot caterpillar growth from observations.csv.

Produces two figures in ./figures:
  1. length_over_time.png  - caterpillar length (mm) against date
  2. growth_change.png     - change in length since the previous observation
  3. growth_rate.png       - growth rate (mm/day) between observations

Usage:
    python plot_growth.py
    python plot_growth.py --csv observations.csv --out figures
"""
import argparse
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

GAP_DAYS = 5  # a gap between measurements this long counts as "unobserved"

GREEN = "#4C7C3A"
DARK = "#2B3A2A"
AMBER = "#D98E04"
RED = "#B23A3A"
GREY = "#6B7280"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.edgecolor": GREY,
    "axes.labelcolor": DARK,
    "xtick.color": DARK,
    "ytick.color": DARK,
    "axes.titleweight": "bold",
    "axes.titlesize": 14,
    "figure.dpi": 100,
})


def load(csv_path):
    df = pd.read_csv(csv_path, parse_dates=["date"]).sort_values("date")
    df = df.reset_index(drop=True)
    df["change_mm"] = df["length_mm"].diff()          # computed, not typed in
    df["gap_days"] = df["date"].diff().dt.days
    df["event"] = df["event"].fillna("")
    return df


def style_dates(ax, df):
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=3))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.set_xlim(df["date"].min() - pd.Timedelta(days=1),
                df["date"].max() + pd.Timedelta(days=1.5))
    ax.grid(axis="y", color="#E5E7EB", linewidth=0.8)
    ax.set_axisbelow(True)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")

    start = df["date"].min()
    top = ax.secondary_xaxis(
        "top",
        functions=(lambda x: x - mdates.date2num(start) + 1,
                   lambda d: d + mdates.date2num(start) - 1),
    )
    top.set_xlabel("Day of observation (Day 1 = 7 Sep)", color=GREY)
    top.xaxis.set_major_locator(plt.MultipleLocator(5))
    top.tick_params(colors=GREY)
    top.spines["top"].set_visible(False)


def plot_length(df, out):
    fig, ax = plt.subplots(figsize=(11, 6))

    gaps = df[df["gap_days"] >= GAP_DAYS]
    for i in gaps.index:
        a, b = df.loc[i - 1], df.loc[i]
        ax.axvspan(a["date"], b["date"], color=AMBER, alpha=0.10, lw=0)
        ax.text(a["date"] + (b["date"] - a["date"]) / 2, 8,
                "Not measured\n(midterm break,\ngardener's care)",
                ha="center", va="bottom", fontsize=9, color=AMBER, style="italic")

    # solid line where consecutive readings exist, dashed across big gaps
    for i in range(1, len(df)):
        a, b = df.loc[i - 1], df.loc[i]
        dashed = b["gap_days"] >= GAP_DAYS
        ax.plot([a["date"], b["date"]], [a["length_mm"], b["length_mm"]],
                color=GREEN, lw=2.4, ls="--" if dashed else "-", zorder=2)

    exact = df[df["measurement"] != "approx"]
    approx = df[df["measurement"] == "approx"]
    ax.scatter(exact["date"], exact["length_mm"], s=55, color=GREEN,
               edgecolor="white", linewidth=1.2, zorder=3, label="Measured (ruler)")
    ax.scatter(approx["date"], approx["length_mm"], s=70, facecolor="white",
               edgecolor=GREEN, linewidth=2, zorder=3, label="Approximate")

    notes = {
        "Horn-like structures on head": (0, 22),
        "Turned yellowish": (-8, 28),
        "Turned greener": (14, -30),
        "Found dead": (-6, -34),
    }
    for _, row in df[df["event"].isin(notes)].iterrows():
        dx, dy = notes[row["event"]]
        color = RED if row["event"] == "Found dead" else DARK
        ax.annotate(row["event"], (row["date"], row["length_mm"]),
                    xytext=(dx, dy), textcoords="offset points",
                    ha="center", fontsize=9, color=color,
                    arrowprops=dict(arrowstyle="-", color=GREY, lw=0.8))

    last = df.iloc[-1]
    ax.scatter([last["date"]], [last["length_mm"]], marker="X", s=130,
               color=RED, zorder=4, label="Death observed")

    ax.set_ylim(0, df["length_mm"].max() * 1.15)
    ax.set_ylabel("Length (mm)")
    ax.set_xlabel("Date (2026)")
    ax.set_title("Caterpillar length over time", loc="left", pad=36)
    ax.legend(frameon=False, loc="upper left")
    style_dates(ax, df)
    fig.tight_layout()
    fig.savefig(out, dpi=200)
    plt.close(fig)


def plot_change(df, out):
    d = df.dropna(subset=["change_mm"]).copy()
    d["after_gap"] = d["gap_days"] >= GAP_DAYS

    fig, ax = plt.subplots(figsize=(11, 6))
    width = 0.8
    normal_max = d.loc[~d["after_gap"], "change_mm"].max()
    cap = normal_max * 1.45   # the +38 bar is truncated so the small changes stay readable
    for _, r in d.iterrows():
        if r["after_gap"]:
            # span the whole unobserved interval so the bar isn't misleading
            left = r["date"] - pd.Timedelta(days=r["gap_days"])
            mid = left + (r["date"] - left) / 2
            ax.bar(mid, cap, width=r["gap_days"], color=AMBER, alpha=0.35,
                   edgecolor=AMBER, hatch="//", linewidth=1, zorder=2)
            # "axis break" marks near the top of the truncated bar
            ax.plot([left, r["date"]], [cap * 0.9, cap * 0.9 + 0.12], color="white", lw=6, zorder=3)
            ax.plot([left, r["date"]], [cap * 0.84, cap * 0.84 + 0.12], color="white", lw=6, zorder=3)
            ax.text(mid, cap * 0.5,
                    f"+{r['change_mm']:g} mm over {int(r['gap_days'])} days\n"
                    f"(≈{r['change_mm'] / r['gap_days']:.1f} mm/day avg.)\n"
                    "not observed\n(bar truncated)",
                    ha="center", va="center", fontsize=10, color="#8A5A00",
                    bbox=dict(boxstyle="round", fc="white", ec=AMBER, alpha=0.9), zorder=4)
        else:
            ax.bar(r["date"], r["change_mm"], width=width,
                   color=GREEN if r["change_mm"] > 0 else GREY, zorder=2)
            label = f"+{r['change_mm']:g}" if r["change_mm"] > 0 else "0"
            ax.annotate(label, (r["date"], r["change_mm"]), xytext=(0, 4),
                        textcoords="offset points", ha="center",
                        fontsize=9, color=DARK)

    ax.axhline(0, color=GREY, lw=0.8)
    ax.set_ylim(0, cap * 1.08)
    ax.set_ylabel("Change in length since previous observation (mm)")
    ax.set_xlabel("Date of observation (2026)")
    ax.set_title("Growth change between observations", loc="left", pad=36)
    style_dates(ax, df)
    fig.text(0.01, 0.005,
             "Observations were 1–3 days apart (12 days across the midterm break), "
             "so bar heights are not per-day rates.",
             fontsize=8, color=GREY)
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    fig.savefig(out, dpi=200)
    plt.close(fig)


def plot_rate(df, out):
    d = df.dropna(subset=["change_mm"]).copy()
    d["rate"] = d["change_mm"] / d["gap_days"]
    d["after_gap"] = d["gap_days"] >= GAP_DAYS

    fig, ax = plt.subplots(figsize=(11, 6))
    for _, r in d.iterrows():
        if r["after_gap"]:
            left = r["date"] - pd.Timedelta(days=r["gap_days"])
            mid = left + (r["date"] - left) / 2
            ax.bar(mid, r["rate"], width=r["gap_days"], color=AMBER, alpha=0.35,
                   edgecolor=AMBER, hatch="//", linewidth=1, zorder=2)
            ax.text(mid, r["rate"] / 2,
                    f"Average over {int(r['gap_days'])} unobserved days\n"
                    f"(+{r['change_mm']:g} mm total)\n≈{r['rate']:.1f} mm/day",
                    ha="center", va="center", fontsize=10, color="#8A5A00",
                    bbox=dict(boxstyle="round", fc="white", ec=AMBER, alpha=0.9), zorder=4)
        else:
            ax.bar(r["date"], r["rate"], width=0.8, color=GREEN if r["rate"] > 0 else GREY, zorder=2)
            ax.annotate(f"{round(r['rate'], 2):g}", (r["date"], r["rate"]), xytext=(0, 4),
                        textcoords="offset points", ha="center", fontsize=9, color=DARK)

    ax.axhline(0, color=GREY, lw=0.8)
    ax.set_ylim(0, d["rate"].max() * 1.15)
    ax.set_ylabel("Growth rate since previous observation (mm/day)")
    ax.set_xlabel("Date of observation (2026)")
    ax.set_title("Growth rate between observations", loc="left", pad=36)
    style_dates(ax, df)
    fig.text(0.01, 0.005,
             "Rate = change in length / days since previous observation. "
             "Rates are averages over each interval.",
             fontsize=8, color=GREY)
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    fig.savefig(out, dpi=200)
    plt.close(fig)


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--csv", default="observations.csv")
    p.add_argument("--out", default="figures")
    args = p.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    df = load(args.csv)
    plot_length(df, out / "length_over_time.png")
    plot_change(df, out / "growth_change.png")
    plot_rate(df, out / "growth_rate.png")
    print(f"Saved figures to {out.resolve()}")


if __name__ == "__main__":
    main()
