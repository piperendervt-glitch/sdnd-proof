"""
visualize_trials.py
5試行の統計結果を可視化する

出力グラフ:
1. trials_accuracy.png  — 試行ごとの正解率分布（箱ひげ図 + 各試行のライン）
2. trials_statistics.png — p値・効果量・信頼区間の可視化
"""

import json
import math
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
from pathlib import Path

# CJKフォント設定
_cjk_candidates = [
    'Noto Sans CJK JP', 'Noto Sans JP', 'Yu Gothic', 'Meiryo',
    'MS Gothic', 'IPAGothic', 'TakaoGothic',
]
_available = {f.name for f in fm.fontManager.ttflist}
for _fc in _cjk_candidates:
    if _fc in _available:
        matplotlib.rcParams['font.family'] = _fc
        break

BASE_DIR = Path(__file__).parent.parent
TRIALS_DIR = BASE_DIR / "results" / "trials"
ANALYSIS_PATH = BASE_DIR / "results" / "statistical_analysis.json"
GRAPHS_DIR = BASE_DIR / "graphs"
GRAPHS_DIR.mkdir(exist_ok=True)

# 言語テキスト
LANG_JA = {
    "suptitle_acc": "統計的有意性検定 — {n}試行の総合結果",
    "ax1_title": "実験A (固定) — 試行別 10問ごと正解率",
    "ax2_title": "実験B (可変) — 試行別 10問ごと正解率",
    "ax3_title": "差分 (B - A) — 各窓での優位性",
    "xlabel_qnum": "問題番号（末尾）",
    "ylabel_acc": "正解率",
    "ylabel_diff": "正解率差 (B-A)",
    "label_mean": "平均",
    "label_mean_diff": "平均差(B-A)",
    "ax4_title": "後半50問 正解率（試行別）",
    "ax4_xa": "実験A\n(固定)",
    "ax4_xb": "実験B\n(可変)",
    "ax4_label_a": "A平均 {v:.1%}",
    "ax4_label_b": "B平均 {v:.1%}",
    "trial_label": "試行{tid}",
    "ax5_title": "後半50問 差分 B-A（試行別）",
    "ax5_mean": "平均差: {v:+.1%}",
    "ax5_xtick": "試行{i}",
    "ax6_title": "最終 flow_weight 平均（実験B）",
    "ax6_init": "初期値 0.5",
    "ax6_nodata": "dry-runのため\nデータなし",
    "conn_labels": ["1→2\n前進", "2→1\nFB", "2→3\n前進", "3→2\nFB", "1→3\nSC", "3→1\nSC-R"],
    # statistics
    "suptitle_stat": "統計検定結果  |  {verdict}  p={p:.4f}  B優位: {bw}試行  後半平均差: {md:+.1%}",
    "verdict_yes": "✓ 仮説支持",
    "verdict_trend": "△ 傾向あり",
    "verdict_no": "✗ 仮説否定",
    "ci_title": "95%信頼区間",
    "ci_xlabel": "差分 B-A の 95%信頼区間",
    "ci_zero": "ゼロ（差なし）",
    "ci_y_overall": "全体",
    "ci_y_second": "後半50問\n★主要",
    "pval_title": "p値（有意水準との比較）",
    "pval_ylabel": "p値",
    "pval_overall": "全体正解率",
    "pval_second": "後半50問",
    "pval_sig": "有意 ✓",
    "pval_nonsig": "非有意",
    "d_title": "効果量 Cohen's d",
    "d_overall": "全体\n正解率",
    "d_second": "後半50問\n★主要",
    "d_none": "効果なし",
    "d_small": "効果:小",
    "d_medium": "効果:中",
    "d_large": "効果:大",
    "thresh_small": "小 (0.2)",
    "thresh_medium": "中 (0.5)",
    "thresh_large": "大 (0.8)",
    "file_acc": "trials_accuracy.png",
    "file_stat": "trials_statistics.png",
}

LANG_EN = {
    "suptitle_acc": "Statistical Significance Test — Results of {n} Trials",
    "ax1_title": "Experiment A (Fixed) — Accuracy per 10 Questions",
    "ax2_title": "Experiment B (Adaptive) — Accuracy per 10 Questions",
    "ax3_title": "Difference (B - A) — Advantage per Window",
    "xlabel_qnum": "Question Number (end)",
    "ylabel_acc": "Accuracy",
    "ylabel_diff": "Relative Advantage (B-A)",
    "label_mean": "Mean",
    "label_mean_diff": "Mean diff (B-A)",
    "ax4_title": "Accuracy on Q51–100 (per Trial)",
    "ax4_xa": "Experiment A\n(Fixed)",
    "ax4_xb": "Experiment B\n(Adaptive)",
    "ax4_label_a": "A Mean {v:.1%}",
    "ax4_label_b": "B Mean {v:.1%}",
    "trial_label": "Trial {tid}",
    "ax5_title": "Q51–100 Difference B-A (per Trial)",
    "ax5_mean": "Mean diff: {v:+.1%}",
    "ax5_xtick": "Trial {i}",
    "ax6_title": "Final flow_weight Mean (Experiment B)",
    "ax6_init": "Initial value 0.5",
    "ax6_nodata": "No data\n(dry-run)",
    "conn_labels": ["1→2\nFwd", "2→1\nFB", "2→3\nFwd", "3→2\nFB", "1→3\nSC", "3→1\nSC-R"],
    # statistics
    "suptitle_stat": "Statistical Test Results  |  {verdict}  p={p:.4f}  B wins: {bw} trials  Mean diff (Q51–100): {md:+.1%}",
    "verdict_yes": "✓ Hypothesis Supported",
    "verdict_trend": "△ Trend observed",
    "verdict_no": "✗ Hypothesis Rejected",
    "ci_title": "95% Confidence Interval",
    "ci_xlabel": "95% CI of Difference B-A",
    "ci_zero": "Zero (no diff)",
    "ci_y_overall": "Overall",
    "ci_y_second": "Q51–100\n★Primary",
    "pval_title": "p-value (vs. Significance Level)",
    "pval_ylabel": "p-value",
    "pval_overall": "Overall Accuracy",
    "pval_second": "Q51–100",
    "pval_sig": "Significant ✓",
    "pval_nonsig": "Not significant",
    "d_title": "Effect Size Cohen's d",
    "d_overall": "Overall\nAccuracy",
    "d_second": "Q51–100\n★Primary",
    "d_none": "No effect",
    "d_small": "Small",
    "d_medium": "Medium",
    "d_large": "Large effect",
    "thresh_small": "Small (0.2)",
    "thresh_medium": "Medium (0.5)",
    "thresh_large": "Large (0.8)",
    "file_acc": "trials_accuracy_en.png",
    "file_stat": "trials_statistics_en.png",
}

# カラー設定
C_BG     = "#0f1117"
C_PANEL  = "#1a1d2e"
C_GRID   = "#2a2d3a"
C_TEXT   = "#e8eaf0"
C_A      = "#4C9BE8"   # 固定ネットワーク
C_B      = "#F5A623"   # 可変ネットワーク
C_DIFF   = "#7ED321"   # 差分
C_ZERO   = "#555870"


def load_trials():
    files = sorted(TRIALS_DIR.glob("trial_*.json"))
    return [json.loads(f.read_text(encoding="utf-8"))
            for f in files if json.loads(f.read_text()).get("completed")]


def load_analysis():
    if not ANALYSIS_PATH.exists():
        return None
    return json.loads(ANALYSIS_PATH.read_text(encoding="utf-8"))


def plot_trials_accuracy(trials: list, L: dict):
    """試行ごとの正解率推移 + 箱ひげ図"""
    n = len(trials)

    fig = plt.figure(figsize=(18, 10), facecolor=C_BG)
    gs = GridSpec(2, 3, figure=fig, hspace=0.38, wspace=0.32)

    # ── 左上: 全試行の10問ごと正解率（実験A） ──
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.set_facecolor(C_PANEL)
    x = np.arange(1, 11)
    x_labels = [f"{i*10}" for i in range(1, 11)]

    for t in trials:
        wa = t.get("window_acc_a", [])
        if wa:
            ax1.plot(x[:len(wa)], wa, "-o", color=C_A,
                     alpha=0.4, linewidth=1.5, markersize=4)

    # 平均線
    if trials and trials[0].get("window_acc_a"):
        mean_a = [
            sum(t["window_acc_a"][i] for t in trials if i < len(t.get("window_acc_a", [])))
            / n
            for i in range(10)
        ]
        ax1.plot(x, mean_a, "-o", color=C_A, linewidth=2.5,
                 markersize=7, label=L["label_mean"], zorder=5)

    _style_ax(ax1, L["ax1_title"], L["xlabel_qnum"], L["ylabel_acc"], x_labels)

    # ── 中上: 全試行の10問ごと正解率（実験B） ──
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.set_facecolor(C_PANEL)

    for t in trials:
        wb = t.get("window_acc_b", [])
        if wb:
            ax2.plot(x[:len(wb)], wb, "-o", color=C_B,
                     alpha=0.4, linewidth=1.5, markersize=4)

    if trials and trials[0].get("window_acc_b"):
        mean_b = [
            sum(t["window_acc_b"][i] for t in trials if i < len(t.get("window_acc_b", [])))
            / n
            for i in range(10)
        ]
        ax2.plot(x, mean_b, "-o", color=C_B, linewidth=2.5,
                 markersize=7, label=L["label_mean"], zorder=5)

    _style_ax(ax2, L["ax2_title"], L["xlabel_qnum"], L["ylabel_acc"], x_labels)

    # ── 右上: B-A の差分推移 ──
    ax3 = fig.add_subplot(gs[0, 2])
    ax3.set_facecolor(C_PANEL)

    for t in trials:
        wa = t.get("window_acc_a", [])
        wb = t.get("window_acc_b", [])
        if wa and wb:
            diffs = [b - a for a, b in zip(wa, wb)]
            ax3.plot(x[:len(diffs)], diffs, "-o",
                     color=C_DIFF, alpha=0.4, linewidth=1.5, markersize=4)

    if trials and trials[0].get("window_acc_a"):
        mean_diff = [mean_b[i] - mean_a[i] for i in range(10)]
        ax3.plot(x, mean_diff, "-o", color=C_DIFF, linewidth=2.5,
                 markersize=7, label=L["label_mean_diff"], zorder=5)

    ax3.axhline(y=0, color=C_ZERO, linestyle="--", linewidth=1.2, alpha=0.8)
    _style_ax(ax3, L["ax3_title"], L["xlabel_qnum"], L["ylabel_diff"], x_labels, center_zero=True)

    # ── 左下: 後半50問の正解率 散布図 ──
    ax4 = fig.add_subplot(gs[1, 0])
    ax4.set_facecolor(C_PANEL)

    acc_a = [t["summary"]["acc_a_second"] for t in trials]
    acc_b = [t["summary"]["acc_b_second"] for t in trials]
    trial_ids = [t["trial_id"] for t in trials]

    # 各試行をドット+接続線で表示
    for i, (a, b, tid) in enumerate(zip(acc_a, acc_b, trial_ids)):
        ax4.plot([1, 2], [a, b], "-", color=C_GRID, linewidth=1.5, alpha=0.7, zorder=1)
        ax4.scatter([1], [a], color=C_A, s=80, zorder=3)
        ax4.scatter([2], [b], color=C_B, s=80, zorder=3)
        ax4.text(2.08, b, L["trial_label"].format(tid=tid), va="center", color=C_TEXT,
                 fontsize=8, alpha=0.8)

    # 平均をバー
    ax4.scatter([1], [sum(acc_a)/n], color=C_A, s=200, marker="D",
                zorder=5, label=L["ax4_label_a"].format(v=sum(acc_a)/n))
    ax4.scatter([2], [sum(acc_b)/n], color=C_B, s=200, marker="D",
                zorder=5, label=L["ax4_label_b"].format(v=sum(acc_b)/n))

    ax4.set_xticks([1, 2])
    ax4.set_xticklabels([L["ax4_xa"], L["ax4_xb"]], color=C_TEXT, fontsize=10)
    ax4.set_xlim(0.7, 2.6)
    ax4.set_ylim(0, 1.05)
    ax4.set_yticks(np.arange(0, 1.05, 0.1))
    ax4.set_yticklabels([f"{v:.0%}" for v in np.arange(0, 1.05, 0.1)], color=C_TEXT)
    ax4.set_title(L["ax4_title"], color=C_TEXT, fontsize=11, fontweight="bold")
    ax4.grid(True, color=C_GRID, linewidth=0.8, alpha=0.7)
    ax4.spines[:].set_color(C_GRID)
    ax4.legend(facecolor="#252840", edgecolor=C_GRID, labelcolor=C_TEXT, fontsize=8)

    # ── 中下: 差分のバープロット（試行別） ──
    ax5 = fig.add_subplot(gs[1, 1])
    ax5.set_facecolor(C_PANEL)

    diffs = [t["summary"]["diff_second"] for t in trials]
    colors = [C_DIFF if d >= 0 else "#E8504C" for d in diffs]
    bars = ax5.bar(trial_ids, diffs, color=colors, alpha=0.85, zorder=3)

    # 値ラベル
    for bar, d in zip(bars, diffs):
        ypos = d + 0.005 if d >= 0 else d - 0.015
        ax5.text(bar.get_x() + bar.get_width()/2, ypos,
                 f"{d:+.1%}", ha="center", va="bottom" if d >= 0 else "top",
                 color=C_TEXT, fontsize=9, fontweight="bold")

    ax5.axhline(y=0, color=C_ZERO, linestyle="-", linewidth=1.5, alpha=0.8)
    mean_diff_val = sum(diffs) / n
    ax5.axhline(y=mean_diff_val, color=C_DIFF, linestyle="--",
                linewidth=1.5, alpha=0.8, label=L["ax5_mean"].format(v=mean_diff_val))

    ax5.set_xticks(trial_ids)
    ax5.set_xticklabels([L["ax5_xtick"].format(i=i) for i in trial_ids], color=C_TEXT, fontsize=9)
    ax5.set_ylim(-0.3, 0.3)
    ax5.set_yticks(np.arange(-0.3, 0.31, 0.1))
    ax5.set_yticklabels([f"{v:+.0%}" for v in np.arange(-0.3, 0.31, 0.1)], color=C_TEXT)
    ax5.set_title(L["ax5_title"], color=C_TEXT, fontsize=11, fontweight="bold")
    ax5.grid(True, color=C_GRID, linewidth=0.8, alpha=0.7, axis="y")
    ax5.spines[:].set_color(C_GRID)
    ax5.legend(facecolor="#252840", edgecolor=C_GRID, labelcolor=C_TEXT, fontsize=8)

    # ── 右下: flow_weight最終値（実験B平均） ──
    ax6 = fig.add_subplot(gs[1, 2])
    ax6.set_facecolor(C_PANEL)

    conn_keys = ["1->2", "2->1", "2->3", "3->2", "1->3", "3->1"]

    final_weights_all = []
    for t in trials:
        fw = t.get("final_weights", {})
        if fw:
            final_weights_all.append([fw.get(k, 0.5) for k in conn_keys])

    if final_weights_all:
        mean_weights = [sum(w[i] for w in final_weights_all) / len(final_weights_all)
                        for i in range(len(conn_keys))]
        bar_colors = [C_B if w > 0.5 else C_A for w in mean_weights]
        bars2 = ax6.bar(range(len(conn_keys)), mean_weights,
                        color=bar_colors, alpha=0.85, zorder=3)
        ax6.axhline(y=0.5, color=C_ZERO, linestyle="--",
                    linewidth=1.5, alpha=0.8, label=L["ax6_init"])

        for bar, w in zip(bars2, mean_weights):
            ax6.text(bar.get_x() + bar.get_width()/2, w + 0.01,
                     f"{w:.3f}", ha="center", va="bottom",
                     color=C_TEXT, fontsize=8)
    else:
        ax6.text(0.5, 0.5, L["ax6_nodata"],
                 ha="center", va="center", transform=ax6.transAxes,
                 color=C_TEXT, fontsize=12)

    ax6.set_xticks(range(len(conn_keys)))
    ax6.set_xticklabels(L["conn_labels"], color=C_TEXT, fontsize=8)
    ax6.set_ylim(0, 1.05)
    ax6.set_yticks(np.arange(0, 1.05, 0.1))
    ax6.set_yticklabels([f"{v:.1f}" for v in np.arange(0, 1.05, 0.1)], color=C_TEXT)
    ax6.set_title(L["ax6_title"], color=C_TEXT, fontsize=11, fontweight="bold")
    ax6.grid(True, color=C_GRID, linewidth=0.8, alpha=0.7, axis="y")
    ax6.spines[:].set_color(C_GRID)
    ax6.legend(facecolor="#252840", edgecolor=C_GRID, labelcolor=C_TEXT, fontsize=8)

    fig.suptitle(L["suptitle_acc"].format(n=n),
                 color=C_TEXT, fontsize=14, fontweight="bold", y=1.01)

    out = GRAPHS_DIR / L["file_acc"]
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=C_BG)
    plt.close()
    print(f"✓ {L['file_acc']} saved: {out}")


def plot_statistics(analysis: dict, L: dict):
    """p値・効果量・信頼区間の可視化"""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), facecolor=C_BG)

    # ── グラフ1: 95%信頼区間 ──
    ax1 = axes[0]
    ax1.set_facecolor(C_PANEL)

    tests = {
        L["ci_y_overall"]: analysis["test_total"],
        L["ci_y_second"]: analysis["test_second_half"],
    }

    y_pos = [1, 0]
    for (label, test), y in zip(tests.items(), y_pos):
        ci = test["ci_95"]
        mean_val = (ci[0] + ci[1]) / 2
        ax1.barh([y], [ci[1] - ci[0]], left=[ci[0]],
                 color=C_B if test["p_value"] < 0.05 else C_GRID,
                 alpha=0.6, height=0.4, zorder=3)
        ax1.scatter([mean_val], [y], color=C_B if test["p_value"] < 0.05 else C_TEXT,
                    s=100, zorder=5)
        p_label = f"p={test['p_value']:.3f}"
        sig = " *" if test["p_value"] < 0.05 else ""
        ax1.text(max(ci[1], 0.01) + 0.005, y, f"{p_label}{sig}",
                 va="center", color=C_TEXT, fontsize=9)

    ax1.axvline(x=0, color="#E8504C", linestyle="--", linewidth=1.5,
                alpha=0.9, label=L["ci_zero"])
    ax1.set_yticks([0, 1])
    ax1.set_yticklabels([L["ci_y_second"], L["ci_y_overall"]], color=C_TEXT, fontsize=9)
    ax1.set_xlabel(L["ci_xlabel"], color=C_TEXT, fontsize=10)
    ax1.set_title(L["ci_title"], color=C_TEXT, fontsize=12, fontweight="bold")
    ax1.grid(True, color=C_GRID, linewidth=0.8, alpha=0.7, axis="x")
    ax1.spines[:].set_color(C_GRID)
    ax1.tick_params(colors=C_TEXT)

    # ── グラフ2: p値の可視化 ──
    ax2 = axes[1]
    ax2.set_facecolor(C_PANEL)

    p_vals = {
        L["pval_overall"]: analysis["test_total"]["p_value"],
        L["pval_second"]: analysis["test_second_half"]["p_value"],
    }

    labels = list(p_vals.keys())
    values = list(p_vals.values())
    bar_colors = [C_B if v < 0.05 else C_GRID for v in values]

    bars = ax2.bar(labels, values, color=bar_colors, alpha=0.85, zorder=3)
    ax2.axhline(y=0.05, color="#E8504C", linestyle="--",
                linewidth=2, alpha=0.9, label="α=0.05", zorder=4)
    ax2.axhline(y=0.01, color="#F5A623", linestyle=":",
                linewidth=1.5, alpha=0.7, label="α=0.01", zorder=4)

    for bar, v in zip(bars, values):
        sig = L["pval_sig"] if v < 0.05 else L["pval_nonsig"]
        color = C_B if v < 0.05 else C_TEXT
        ax2.text(bar.get_x() + bar.get_width()/2, v + 0.003,
                 f"p={v:.3f}\n{sig}", ha="center", va="bottom",
                 color=color, fontsize=9, fontweight="bold")

    ax2.set_ylim(0, max(max(values) * 1.4, 0.12))
    ax2.set_xticklabels(labels, color=C_TEXT, fontsize=10)
    ax2.set_ylabel(L["pval_ylabel"], color=C_TEXT, fontsize=10)
    ax2.set_title(L["pval_title"], color=C_TEXT, fontsize=12, fontweight="bold")
    ax2.grid(True, color=C_GRID, linewidth=0.8, alpha=0.7, axis="y")
    ax2.legend(facecolor="#252840", edgecolor=C_GRID, labelcolor=C_TEXT, fontsize=9)
    ax2.spines[:].set_color(C_GRID)
    ax2.tick_params(colors=C_TEXT)

    # ── グラフ3: Cohen's d ──
    ax3 = axes[2]
    ax3.set_facecolor(C_PANEL)

    d_vals = {
        L["d_overall"]: analysis["test_total"]["cohens_d"],
        L["d_second"]: analysis["test_second_half"]["cohens_d"],
    }

    labels3 = list(d_vals.keys())
    values3 = list(d_vals.values())
    bar_colors3 = [C_B if v > 0 else "#E8504C" for v in values3]

    bars3 = ax3.bar(labels3, values3, color=bar_colors3, alpha=0.85, zorder=3)

    # 効果量の閾値線
    for thresh, label, color in [
        (0.2, L["thresh_small"], "#aaaaaa"),
        (0.5, L["thresh_medium"], "#cccccc"),
        (0.8, L["thresh_large"], "#eeeeee"),
    ]:
        ax3.axhline(y=thresh, color=color, linestyle=":",
                    linewidth=1, alpha=0.5)
        ax3.text(len(labels3) - 0.4, thresh + 0.01, label,
                 color=color, fontsize=7, alpha=0.7)

    for bar, v in zip(bars3, values3):
        if abs(v) < 0.2:
            size_label = L["d_none"]
        elif abs(v) < 0.5:
            size_label = L["d_small"]
        elif abs(v) < 0.8:
            size_label = L["d_medium"]
        else:
            size_label = L["d_large"]
        ax3.text(bar.get_x() + bar.get_width()/2,
                 v + (0.03 if v >= 0 else -0.06),
                 f"d={v:.3f}\n{size_label}",
                 ha="center", va="bottom" if v >= 0 else "top",
                 color=C_TEXT, fontsize=9, fontweight="bold")

    ax3.axhline(y=0, color=C_ZERO, linestyle="-", linewidth=1.5, alpha=0.8)
    lim = max(max(abs(v) for v in values3) * 1.5, 1.0)
    ax3.set_ylim(-lim * 0.3, lim)
    ax3.set_xticklabels(labels3, color=C_TEXT, fontsize=10)
    ax3.set_ylabel("Cohen's d", color=C_TEXT, fontsize=10)
    ax3.set_title(L["d_title"], color=C_TEXT, fontsize=12, fontweight="bold")
    ax3.grid(True, color=C_GRID, linewidth=0.8, alpha=0.7, axis="y")
    ax3.spines[:].set_color(C_GRID)
    ax3.tick_params(colors=C_TEXT)

    # 仮説判定をタイトルに
    h = analysis["hypothesis"]
    if h["supported"]:
        verdict = L["verdict_yes"]
    elif h["mean_diff"] > 0:
        verdict = L["verdict_trend"]
    else:
        verdict = L["verdict_no"]
    fig.suptitle(
        L["suptitle_stat"].format(verdict=verdict, p=h["p_value"],
                                  bw=h["b_wins"], md=h["mean_diff"]),
        color=C_TEXT, fontsize=13, fontweight="bold", y=1.02
    )

    plt.tight_layout()
    out = GRAPHS_DIR / L["file_stat"]
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=C_BG)
    plt.close()
    print(f"✓ {L['file_stat']} saved: {out}")


def _style_ax(ax, title, xlabel, ylabel, x_labels, center_zero=False):
    ax.set_xticks(range(1, 11))
    ax.set_xticklabels(x_labels, color=C_TEXT, fontsize=8)
    if center_zero:
        ax.set_ylim(-0.5, 0.5)
        ax.set_yticks(np.arange(-0.5, 0.51, 0.1))
        ax.axhline(y=0, color=C_ZERO, linestyle="--", linewidth=1.2, alpha=0.8)
    else:
        ax.set_ylim(0, 1.05)
        ax.set_yticks(np.arange(0, 1.05, 0.2))
    ax.set_yticklabels([f"{v:.0%}" if not center_zero else f"{v:+.0%}"
                        for v in ax.get_yticks()], color=C_TEXT)
    ax.set_xlabel(xlabel, color=C_TEXT, fontsize=9)
    ax.set_ylabel(ylabel, color=C_TEXT, fontsize=9)
    ax.set_title(title, color=C_TEXT, fontsize=10, fontweight="bold")
    ax.grid(True, color=C_GRID, linewidth=0.8, alpha=0.7)
    ax.spines[:].set_color(C_GRID)
    ax.tick_params(colors=C_TEXT)


def main():
    trials = load_trials()
    if not trials:
        print("Error: No trial data found. Run run_trials.py first.")
        sys.exit(1)

    analysis = load_analysis()
    if not analysis:
        print("Error: No analysis data found. Run statistical_analysis.py first.")
        sys.exit(1)

    langs = []
    if "--en" in sys.argv:
        langs.append(("en", LANG_EN))
    elif "--all" in sys.argv:
        langs.append(("ja", LANG_JA))
        langs.append(("en", LANG_EN))
    else:
        langs.append(("ja", LANG_JA))

    for lang_code, L in langs:
        print(f"Generating graphs ({lang_code})...")
        plot_trials_accuracy(trials, L)
        plot_statistics(analysis, L)
        print(f"  -> {L['file_acc']}")
        print(f"  -> {L['file_stat']}")

    print("\n✓ Done")


if __name__ == "__main__":
    main()
