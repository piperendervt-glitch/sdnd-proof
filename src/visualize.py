"""
visualize.py
実験結果の可視化
- 実験A・Bの正解率推移グラフ（折れ線）
- 実験Bのflow_weight変化グラフ
"""

import json
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.patches as mpatches
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
matplotlib.rcParams["axes.unicode_minus"] = False

RESULTS_DIR = Path(__file__).parent.parent / "results"
GRAPHS_DIR = Path(__file__).parent.parent / "graphs"
GRAPHS_DIR.mkdir(exist_ok=True)


def load_jsonl(path: Path) -> list:
    """JSONLファイルを読み込む"""
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def compute_window_accuracy(results: list, window_size: int = 10) -> list:
    """n問ごとの正解率を計算する"""
    accuracies = []
    for i in range(0, len(results), window_size):
        window = results[i:i + window_size]
        acc = sum(1 for r in window if r["is_correct"]) / max(len(window), 1)
        accuracies.append(acc)
    return accuracies


def compute_cumulative_accuracy(results: list) -> list:
    """累積正解率を計算する"""
    correct = 0
    accuracies = []
    for i, r in enumerate(results):
        if r["is_correct"]:
            correct += 1
        accuracies.append(correct / (i + 1))
    return accuracies


def plot_accuracy_comparison():
    """実験A・Bの正解率推移グラフを生成する"""
    path_a = RESULTS_DIR / "experiment_a.jsonl"
    path_b = RESULTS_DIR / "experiment_b.jsonl"

    if not path_a.exists() or not path_b.exists():
        print(f"ERROR: 結果ファイルが見つかりません")
        print(f"  {path_a}")
        print(f"  {path_b}")
        return False

    results_a = load_jsonl(path_a)
    results_b = load_jsonl(path_b)

    if not results_a or not results_b:
        print("ERROR: 結果ファイルが空です")
        return False

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    fig.patch.set_facecolor("#0f1117")

    color_a = "#4C9BE8"
    color_b = "#F5A623"
    color_bg = "#0f1117"
    color_grid = "#2a2d3a"
    color_text = "#e8eaf0"
    color_midline = "#444860"

    # ── グラフ1: 10問ごとの正解率 ──
    ax1 = axes[0]
    ax1.set_facecolor("#1a1d2e")

    window_a = compute_window_accuracy(results_a)
    window_b = compute_window_accuracy(results_b)
    x_windows = [f"{i*10+1}-{i*10+10}" for i in range(len(window_a))]
    x_pos = np.arange(len(window_a))

    ax1.plot(x_pos, window_a, "o-", color=color_a, linewidth=2.5,
             markersize=8, label="Experiment A (Fixed)", zorder=3)
    ax1.plot(x_pos, window_b, "s-", color=color_b, linewidth=2.5,
             markersize=8, label="Experiment B (Adaptive)", zorder=3)

    # 後半エリアを強調
    if len(x_pos) >= 5:
        ax1.axvspan(4.5, len(x_pos) - 0.5, alpha=0.08, color=color_b, zorder=1)
        ax1.text(
            (4.5 + len(x_pos) - 0.5) / 2, 0.03,
            "Second Half\n(Q51-100)",
            ha="center", va="bottom", fontsize=8,
            color=color_b, alpha=0.7
        )

    # 値ラベル
    for i, (va, vb) in enumerate(zip(window_a, window_b)):
        ax1.annotate(f"{va:.0%}", (i, va), textcoords="offset points",
                     xytext=(0, 10), ha="center", fontsize=7, color=color_a, alpha=0.8)
        ax1.annotate(f"{vb:.0%}", (i, vb), textcoords="offset points",
                     xytext=(0, -16), ha="center", fontsize=7, color=color_b, alpha=0.8)

    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(x_windows, rotation=30, ha="right", fontsize=8, color=color_text)
    ax1.set_ylim(0, 1.1)
    ax1.set_yticks(np.arange(0, 1.1, 0.1))
    ax1.set_yticklabels([f"{v:.0%}" for v in np.arange(0, 1.1, 0.1)], color=color_text)
    ax1.set_xlabel("Question Range (per 10)", color=color_text, fontsize=10)
    ax1.set_ylabel("Accuracy", color=color_text, fontsize=10)
    ax1.set_title("Accuracy per 10 Questions", color=color_text, fontsize=13, fontweight="bold", pad=12)
    ax1.grid(True, color=color_grid, linewidth=0.8, alpha=0.7, zorder=0)
    ax1.legend(loc="lower right", facecolor="#252840", edgecolor=color_grid,
               labelcolor=color_text, fontsize=9)
    ax1.spines[:].set_color(color_grid)
    ax1.tick_params(colors=color_text)

    # ── グラフ2: 累積正解率 ──
    ax2 = axes[1]
    ax2.set_facecolor("#1a1d2e")

    cum_a = compute_cumulative_accuracy(results_a)
    cum_b = compute_cumulative_accuracy(results_b)
    x = np.arange(1, len(cum_a) + 1)

    ax2.plot(x, cum_a, "-", color=color_a, linewidth=2.5,
             label="Experiment A (Fixed)", alpha=0.9, zorder=3)
    ax2.plot(x, cum_b, "-", color=color_b, linewidth=2.5,
             label="Experiment B (Adaptive)", alpha=0.9, zorder=3)

    # 50問目の垂直線
    ax2.axvline(x=50, color=color_midline, linestyle="--", linewidth=1.2,
                alpha=0.7, zorder=2, label="Q50 (Midpoint)")
    ax2.text(50.5, 0.05, "Midpoint", color=color_midline,
             fontsize=8, va="bottom", alpha=0.8)

    # 最終値をアノテーション
    final_a = cum_a[-1]
    final_b = cum_b[-1]
    ax2.annotate(f"Final: {final_a:.1%}", xy=(len(cum_a), final_a),
                 xytext=(-60, 10), textcoords="offset points",
                 color=color_a, fontsize=9, fontweight="bold",
                 arrowprops=dict(arrowstyle="->", color=color_a, lw=1.2))
    ax2.annotate(f"Final: {final_b:.1%}", xy=(len(cum_b), final_b),
                 xytext=(-60, -20), textcoords="offset points",
                 color=color_b, fontsize=9, fontweight="bold",
                 arrowprops=dict(arrowstyle="->", color=color_b, lw=1.2))

    ax2.set_xlim(1, len(x))
    ax2.set_ylim(0, 1.05)
    ax2.set_yticks(np.arange(0, 1.05, 0.1))
    ax2.set_yticklabels([f"{v:.0%}" for v in np.arange(0, 1.05, 0.1)], color=color_text)
    ax2.set_xlabel("Question Number", color=color_text, fontsize=10)
    ax2.set_ylabel("Cumulative Accuracy", color=color_text, fontsize=10)
    ax2.set_title("Cumulative Accuracy Over Time", color=color_text, fontsize=13, fontweight="bold", pad=12)
    ax2.grid(True, color=color_grid, linewidth=0.8, alpha=0.7, zorder=0)
    ax2.legend(loc="lower right", facecolor="#252840", edgecolor=color_grid,
               labelcolor=color_text, fontsize=9)
    ax2.spines[:].set_color(color_grid)
    ax2.tick_params(colors=color_text)

    # 全体タイトル
    total_a = sum(1 for r in results_a if r["is_correct"])
    total_b = sum(1 for r in results_b if r["is_correct"])
    fig.suptitle(
        f"Fixed vs Adaptive Network  |  A: {total_a}/100 ({total_a:.0f}%)  "
        f"B: {total_b}/100 ({total_b:.0f}%)",
        color=color_text, fontsize=14, fontweight="bold", y=1.01
    )

    plt.tight_layout()
    out_path = GRAPHS_DIR / "accuracy_comparison.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=color_bg)
    plt.close()
    print(f"✓ accuracy_comparison.png を保存: {out_path}")
    return True


def plot_flow_weight_evolution():
    """実験Bのflow_weight変化グラフを生成する"""
    path = RESULTS_DIR / "flow_weights.jsonl"
    if not path.exists():
        print(f"ERROR: {path} が見つかりません")
        return False

    records = load_jsonl(path)
    if not records:
        print("ERROR: flow_weights.jsonl が空です")
        return False

    # 接続ごとにweightの推移を集める
    connections = ["1->2", "2->1", "2->3", "3->2", "1->3", "3->1"]
    weight_series = {conn: [] for conn in connections}
    steps = []

    for rec in records:
        steps.append(rec["step"])
        for conn in connections:
            weight_series[conn].append(rec["weights"].get(conn, 0.5))

    steps = np.array(steps)

    # カラーマップ
    colors = {
        "1->2": "#4C9BE8",
        "2->1": "#84C4F5",
        "2->3": "#F5A623",
        "3->2": "#F5C66B",
        "1->3": "#7ED321",
        "3->1": "#A8E05F",
    }

    labels = {
        "1->2": "Node1 → Node2 (forward)",
        "2->1": "Node2 → Node1 (feedback)",
        "2->3": "Node2 → Node3 (forward)",
        "3->2": "Node3 → Node2 (feedback)",
        "1->3": "Node1 → Node3 (shortcut)",
        "3->1": "Node3 → Node1 (skip-back)",
    }

    color_bg = "#0f1117"
    color_grid = "#2a2d3a"
    color_text = "#e8eaf0"

    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    fig.patch.set_facecolor(color_bg)

    # ── グラフ1: 前進方向の接続 ──
    ax1 = axes[0]
    ax1.set_facecolor("#1a1d2e")
    forward_conns = ["1->2", "2->3", "1->3"]

    for conn in forward_conns:
        ax1.plot(steps, weight_series[conn], "-",
                 color=colors[conn], linewidth=2.5,
                 label=labels[conn], alpha=0.9)

    ax1.axhline(y=0.5, color="#444860", linestyle="--", linewidth=1,
                alpha=0.7, label="Initial weight (0.5)")
    ax1.axvline(x=50, color="#666880", linestyle=":", linewidth=1.2,
                alpha=0.6, label="Q50 midpoint")

    ax1.set_xlim(1, max(steps))
    ax1.set_ylim(0, 1.05)
    ax1.set_yticks(np.arange(0, 1.05, 0.1))
    ax1.set_yticklabels([f"{v:.1f}" for v in np.arange(0, 1.05, 0.1)], color=color_text)
    ax1.set_xlabel("Question Number", color=color_text, fontsize=10)
    ax1.set_ylabel("Flow Weight", color=color_text, fontsize=10)
    ax1.set_title("Forward Connections - Flow Weight Evolution", color=color_text,
                  fontsize=12, fontweight="bold", pad=10)
    ax1.grid(True, color=color_grid, linewidth=0.8, alpha=0.7)
    ax1.legend(loc="upper right", facecolor="#252840", edgecolor=color_grid,
               labelcolor=color_text, fontsize=9)
    ax1.spines[:].set_color(color_grid)
    ax1.tick_params(colors=color_text)

    # ── グラフ2: フィードバック方向の接続 ──
    ax2 = axes[1]
    ax2.set_facecolor("#1a1d2e")
    feedback_conns = ["2->1", "3->2", "3->1"]

    for conn in feedback_conns:
        ax2.plot(steps, weight_series[conn], "-",
                 color=colors[conn], linewidth=2.5,
                 label=labels[conn], alpha=0.9)

    ax2.axhline(y=0.5, color="#444860", linestyle="--", linewidth=1,
                alpha=0.7, label="Initial weight (0.5)")
    ax2.axvline(x=50, color="#666880", linestyle=":", linewidth=1.2,
                alpha=0.6, label="Q50 midpoint")

    ax2.set_xlim(1, max(steps))
    ax2.set_ylim(0, 1.05)
    ax2.set_yticks(np.arange(0, 1.05, 0.1))
    ax2.set_yticklabels([f"{v:.1f}" for v in np.arange(0, 1.05, 0.1)], color=color_text)
    ax2.set_xlabel("Question Number", color=color_text, fontsize=10)
    ax2.set_ylabel("Flow Weight", color=color_text, fontsize=10)
    ax2.set_title("Feedback Connections - Flow Weight Evolution", color=color_text,
                  fontsize=12, fontweight="bold", pad=10)
    ax2.grid(True, color=color_grid, linewidth=0.8, alpha=0.7)
    ax2.legend(loc="upper right", facecolor="#252840", edgecolor=color_grid,
               labelcolor=color_text, fontsize=9)
    ax2.spines[:].set_color(color_grid)
    ax2.tick_params(colors=color_text)

    # 最終値のサマリー
    final_weights = {conn: weight_series[conn][-1] for conn in connections}
    strongest = max(final_weights, key=final_weights.get)
    weakest = min(final_weights, key=final_weights.get)
    fig.suptitle(
        f"Adaptive Network: Flow Weight Dynamics  |  "
        f"Strongest: {strongest} ({final_weights[strongest]:.3f})  "
        f"Weakest: {weakest} ({final_weights[weakest]:.3f})",
        color=color_text, fontsize=12, fontweight="bold", y=1.005
    )

    plt.tight_layout()
    out_path = GRAPHS_DIR / "flow_weight_evolution.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=color_bg)
    plt.close()
    print(f"✓ flow_weight_evolution.png を保存: {out_path}")
    return True


def main():
    print("可視化を開始します...")
    print()

    ok1 = plot_accuracy_comparison()
    ok2 = plot_flow_weight_evolution()

    print()
    if ok1 and ok2:
        print("✓ 全グラフの生成が完了しました")
        print(f"  graphs/accuracy_comparison.png")
        print(f"  graphs/flow_weight_evolution.png")
    else:
        print("✗ 一部のグラフ生成に失敗しました")
        sys.exit(1)


if __name__ == "__main__":
    main()
