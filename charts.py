"""Charts for the yield report. This module only holds functions."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def plot_daily_yield(trend:pd.DataFrame,path:Path)->None:
    """Line chart: first-pass and final yield per date (date is the index)."""
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(trend.index, trend["first_pass_yield_pct"], marker="o", label="First-pass")
    ax.plot(trend.index, trend["final_yield_pct"], marker="o", label="Final")
    ax.set_title("Daily yield")
    ax.set_xlabel("Date")
    ax.set_ylabel("Yield (%)")
    ax.set_ylim(0, 100)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)

def plot_station_yield(stations: pd.DataFrame, path: Path) -> None:
    """Grouped bar chart: first-pass and final yield for each station."""
    x = range(len(stations))          # 0, 1：每个站的中心位置
    w = 0.38                          # 每根柱子的宽度
    fig, ax = plt.subplots(figsize=(7, 4))
    first = ax.bar([i - w / 2 for i in x], stations["first_pass_yield_pct"], w, label="First-pass")
    final = ax.bar([i + w / 2 for i in x], stations["final_yield_pct"], w, label="Final")
    ax.bar_label(first, fmt="%.1f")
    ax.bar_label(final, fmt="%.1f")
    ax.set_xticks(list(x))
    ax.set_xticklabels(stations["station"])
    ax.set_title("Yield by station")
    ax.set_ylabel("Yield (%)")
    ax.set_ylim(0, 100)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)

def plot_top_failing(top_tests:pd.DataFrame,path:Path)->None:
    """Horizontal bar chart: Top failing percentage for each test."""
    fig,ax=plt.subplots(figsize=(7,4))
    bars=ax.barh(top_tests.index,top_tests["fail_rate_pct"])
    ax.bar_label(bars, fmt="%.1f%%", padding=3)
    ax.set_title(f"Top {len(top_tests)} failing tests")
    ax.set_ylabel("Test")
    ax.set_xlabel("Fail Rate (%)")
    ax.invert_yaxis()
    ax.margins(x=0.15)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)