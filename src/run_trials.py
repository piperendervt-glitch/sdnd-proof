"""
run_trials.py
5試行を順番に実行し、統計的有意性の検定に必要なデータを収集する
- シード管理で再現性を保証
- 途中保存で中断・再開に対応
- 各試行の結果を trials/ ディレクトリに保存

実行方法:
    python src/run_trials.py
    python src/run_trials.py --trials 5   # 試行数を指定
    python src/run_trials.py --resume     # 途中から再開
    python src/run_trials.py --dry-run    # 動作確認（Ollama不要）
"""

import sys
import json
import time
import random
import argparse
import traceback
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from task_generator import generate_tasks
from fixed_network import FixedNetwork
from adaptive_network import AdaptiveNetwork

# ディレクトリ設定
BASE_DIR = Path(__file__).parent.parent
TRIALS_DIR = BASE_DIR / "results" / "trials"
TRIALS_DIR.mkdir(parents=True, exist_ok=True)

SUMMARY_PATH = BASE_DIR / "results" / "trials_summary.json"

# 各試行のランダムシード（再現性のために固定）
TRIAL_SEEDS = [42, 137, 256, 512, 1024]


# ─────────────────────────────────────────
# ユーティリティ
# ─────────────────────────────────────────

def log(msg: str, level: str = "INFO"):
    now = datetime.now().strftime("%H:%M:%S")
    prefix = {"INFO": "  ", "OK": "✓ ", "WARN": "⚠ ", "ERR": "✗ "}.get(level, "  ")
    print(f"[{now}] {prefix}{msg}", flush=True)


def eta_str(elapsed_sec: float, done: int, total: int) -> str:
    if done == 0:
        return "算出中..."
    per_item = elapsed_sec / done
    remaining = per_item * (total - done)
    h, m = divmod(int(remaining), 3600)
    m, s = divmod(m, 60)
    if h > 0:
        return f"残り約 {h}時間{m:02d}分"
    elif m > 0:
        return f"残り約 {m}分{s:02d}秒"
    else:
        return f"残り約 {s}秒"


def trial_path(trial_id: int) -> Path:
    return TRIALS_DIR / f"trial_{trial_id:02d}.json"


def is_trial_done(trial_id: int) -> bool:
    p = trial_path(trial_id)
    if not p.exists():
        return False
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data.get("completed", False)
    except Exception:
        return False


# ─────────────────────────────────────────
# 1試行の実行
# ─────────────────────────────────────────

def run_one_trial(
    trial_id: int,
    seed: int,
    dry_run: bool = False,
    verbose: bool = True,
) -> dict:
    """
    1試行を実行して結果を返す
    dry_run=True の場合はOllamaを呼ばず乱数でシミュレート（動作確認用）
    """
    log(f"試行 {trial_id}/5 開始 (seed={seed})", "INFO")

    # タスクをシードでシャッフルして試行ごとに順序を変える
    rng = random.Random(seed)
    tasks = generate_tasks()
    shuffled = list(tasks)
    rng.shuffle(shuffled)

    result_a = []
    result_b = []
    trial_start = time.time()

    # ── 実験A: 固定構造 ──
    log(f"  実験A (固定構造) 開始...")
    network_a = FixedNetwork()
    correct_a = 0

    for i, task in enumerate(shuffled):
        q_start = time.time()

        if dry_run:
            # シミュレート: 固定60%正解率
            prediction = rng.random() < 0.60
            raw = "矛盾しない" if prediction else "矛盾する"
            time.sleep(0.01)  # 実際の処理時間を模倣（短縮）
        else:
            try:
                out = network_a.predict(task.world_rule, task.question)
                prediction = out["prediction"]
                raw = out["raw_output"]
            except Exception as e:
                log(f"    A[{i+1}] エラー: {e}", "WARN")
                prediction = False
                raw = f"ERROR: {e}"

        is_correct = (prediction == task.label)
        correct_a += 1 if is_correct else 0
        elapsed = time.time() - q_start

        record = {
            "q": i + 1,
            "task_id": task.task_id,
            "correct": is_correct,
            "prediction": prediction,
            "label": task.label,
            "elapsed": round(elapsed, 2),
        }
        result_a.append(record)

        if verbose and (i + 1) % 10 == 0:
            acc = correct_a / (i + 1)
            total_elapsed = time.time() - trial_start
            log(f"    A [{i+1:3d}/100] 正解率={acc:.1%}  {eta_str(total_elapsed, i+1, 200)}")

    # ── 実験B: 可変構造 ──
    log(f"  実験B (可変構造) 開始...")
    network_b = AdaptiveNetwork()
    correct_b = 0

    for i, task in enumerate(shuffled):
        q_start = time.time()

        if dry_run:
            # シミュレート: 前半55% → 後半75% に徐々に上昇
            progress = i / 100
            prob = 0.55 + progress * 0.22 + rng.gauss(0, 0.05)
            prob = max(0.3, min(0.95, prob))
            prediction = rng.random() < prob
            raw = "矛盾しない" if prediction else "矛盾する"
            path_used = [[1, 2], [2, 3]]
            used_feedback = False
            time.sleep(0.01)
        else:
            try:
                out = network_b.predict(task.world_rule, task.question)
                prediction = out["prediction"]
                raw = out["raw_output"]
                path_used = out["path_used"]
                used_feedback = out["used_feedback"]
                network_b.update_weights(
                    success=(prediction == task.label),
                    path_used=out["path_used"],
                    used_feedback=out["used_feedback"],
                )
            except Exception as e:
                log(f"    B[{i+1}] エラー: {e}", "WARN")
                prediction = False
                raw = f"ERROR: {e}"
                path_used = []
                used_feedback = False

        is_correct = (prediction == task.label)
        correct_b += 1 if is_correct else 0
        elapsed = time.time() - q_start

        record = {
            "q": i + 1,
            "task_id": task.task_id,
            "correct": is_correct,
            "prediction": prediction,
            "label": task.label,
            "elapsed": round(elapsed, 2),
            "path_used": [list(p) for p in path_used] if path_used else [],
            "used_feedback": used_feedback,
            "weights": network_b.get_weights_snapshot(),
        }
        result_b.append(record)

        if verbose and (i + 1) % 10 == 0:
            acc = correct_b / (i + 1)
            total_elapsed = time.time() - trial_start
            done_total = 100 + i + 1
            log(f"    B [{i+1:3d}/100] 正解率={acc:.1%}  {eta_str(total_elapsed, done_total, 200)}")

    # ── 集計 ──
    total_elapsed = time.time() - trial_start

    # 前半（1-50問）と後半（51-100問）の正解率
    acc_a_first  = sum(1 for r in result_a[:50] if r["correct"]) / 50
    acc_a_second = sum(1 for r in result_a[50:] if r["correct"]) / 50
    acc_b_first  = sum(1 for r in result_b[:50] if r["correct"]) / 50
    acc_b_second = sum(1 for r in result_b[50:] if r["correct"]) / 50

    # 10問ごとの正解率
    def window_acc(results):
        return [
            sum(1 for r in results[i:i+10] if r["correct"]) / 10
            for i in range(0, 100, 10)
        ]

    trial_result = {
        "trial_id": trial_id,
        "seed": seed,
        "completed": True,
        "dry_run": dry_run,
        "elapsed_sec": round(total_elapsed, 1),
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "acc_a_total":  round(sum(1 for r in result_a if r["correct"]) / 100, 4),
            "acc_b_total":  round(sum(1 for r in result_b if r["correct"]) / 100, 4),
            "acc_a_first":  round(acc_a_first, 4),
            "acc_a_second": round(acc_a_second, 4),
            "acc_b_first":  round(acc_b_first, 4),
            "acc_b_second": round(acc_b_second, 4),
            "diff_total":   round(sum(1 for r in result_b if r["correct"]) / 100
                                 - sum(1 for r in result_a if r["correct"]) / 100, 4),
            "diff_second":  round(acc_b_second - acc_a_second, 4),
        },
        "window_acc_a": window_acc(result_a),
        "window_acc_b": window_acc(result_b),
        "final_weights": network_b.get_weights_snapshot() if not dry_run else {},
        "results_a": result_a,
        "results_b": result_b,
    }

    # 保存
    p = trial_path(trial_id)
    p.write_text(json.dumps(trial_result, ensure_ascii=False, indent=2), encoding="utf-8")

    log(f"  完了 ({total_elapsed:.0f}秒) | "
        f"A={trial_result['summary']['acc_a_total']:.1%} "
        f"B={trial_result['summary']['acc_b_total']:.1%} "
        f"後半差={trial_result['summary']['diff_second']:+.1%}", "OK")

    return trial_result


# ─────────────────────────────────────────
# 全試行のサマリー保存
# ─────────────────────────────────────────

def save_summary(all_results: list):
    summary = {
        "n_trials": len(all_results),
        "timestamp": datetime.now().isoformat(),
        "trials": [r["summary"] | {"trial_id": r["trial_id"], "seed": r["seed"]}
                   for r in all_results],
        "acc_a_total_mean": round(
            sum(r["summary"]["acc_a_total"] for r in all_results) / len(all_results), 4),
        "acc_b_total_mean": round(
            sum(r["summary"]["acc_b_total"] for r in all_results) / len(all_results), 4),
        "acc_a_second_mean": round(
            sum(r["summary"]["acc_a_second"] for r in all_results) / len(all_results), 4),
        "acc_b_second_mean": round(
            sum(r["summary"]["acc_b_second"] for r in all_results) / len(all_results), 4),
        "diff_second_values": [r["summary"]["diff_second"] for r in all_results],
    }
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"サマリー保存: {SUMMARY_PATH}", "OK")


# ─────────────────────────────────────────
# メイン
# ─────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=5)
    parser.add_argument("--resume", action="store_true", help="完了済み試行をスキップ")
    parser.add_argument("--dry-run", action="store_true", help="Ollamaなしで動作確認")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    n_trials = min(args.trials, len(TRIAL_SEEDS))
    seeds = TRIAL_SEEDS[:n_trials]

    print()
    print("=" * 60)
    print(f"  統計的有意性検定 — {n_trials}試行 実行")
    if args.dry_run:
        print("  ⚠ DRY RUN モード（Ollama不使用・動作確認のみ）")
    print("=" * 60)

    # Ollama疎通確認（dry-runでない場合）
    if not args.dry_run:
        import urllib.request
        try:
            urllib.request.urlopen("http://localhost:11434", timeout=3)
            log("Ollama 接続確認 OK", "OK")
        except Exception:
            log("Ollamaに接続できません。Ollamaが起動しているか確認してください。", "ERR")
            log("動作確認のみなら --dry-run オプションを使ってください。", "WARN")
            sys.exit(1)

    all_results = []
    overall_start = time.time()

    for i, seed in enumerate(seeds, 1):
        trial_id = i

        if args.resume and is_trial_done(trial_id):
            log(f"試行 {trial_id}/5 スキップ（完了済み）")
            data = json.loads(trial_path(trial_id).read_text(encoding="utf-8"))
            all_results.append(data)
            continue

        print()
        result = run_one_trial(
            trial_id=trial_id,
            seed=seed,
            dry_run=args.dry_run,
            verbose=not args.quiet,
        )
        all_results.append(result)

        # 途中経過
        done = len(all_results)
        elapsed = time.time() - overall_start
        if done < n_trials:
            log(f"進捗: {done}/{n_trials} 完了  {eta_str(elapsed, done, n_trials)}")

    # 全試行完了
    save_summary(all_results)

    print()
    print("=" * 60)
    print("  全試行完了 — 統計分析を実行してください")
    print()
    print("  次のコマンドを実行：")
    print("    python src/statistical_analysis.py")
    print("    python src/visualize_trials.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
