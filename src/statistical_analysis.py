"""
statistical_analysis.py
5試行の結果に対して統計的有意性を検定する

検定内容:
1. 対応のあるt検定（paired t-test）
   - 実験A vs 実験B の後半50問正解率
   - 帰無仮説: 両者の正解率に差はない
   - 有意水準: α=0.05

2. 効果量 Cohen's d
   - d < 0.2: 無視できる差
   - 0.2 ≤ d < 0.5: 小さな効果
   - 0.5 ≤ d < 0.8: 中程度の効果
   - d ≥ 0.8: 大きな効果

3. 信頼区間（95%CI）

実行方法:
    python src/statistical_analysis.py
"""

import json
import math
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
TRIALS_DIR = BASE_DIR / "results" / "trials"
SUMMARY_PATH = BASE_DIR / "results" / "trials_summary.json"
ANALYSIS_PATH = BASE_DIR / "results" / "statistical_analysis.json"


# ─────────────────────────────────────────
# 統計関数（標準ライブラリのみ）
# ─────────────────────────────────────────

def mean(xs: list) -> float:
    return sum(xs) / len(xs)


def variance(xs: list, ddof: int = 1) -> float:
    m = mean(xs)
    return sum((x - m) ** 2 for x in xs) / (len(xs) - ddof)


def std(xs: list, ddof: int = 1) -> float:
    return math.sqrt(variance(xs, ddof))


def paired_t_test(a: list, b: list) -> tuple[float, float, float]:
    """
    対応のあるt検定
    Returns: (t統計量, p値の近似, 差分の平均)
    """
    assert len(a) == len(b)
    n = len(a)
    diffs = [bi - ai for ai, bi in zip(a, b)]
    d_mean = mean(diffs)
    d_std = std(diffs)

    if d_std == 0:
        return float("inf"), 0.0, d_mean

    t_stat = d_mean / (d_std / math.sqrt(n))

    # p値をt分布の近似で計算（自由度 n-1）
    df = n - 1
    p_value = _t_p_value(abs(t_stat), df) * 2  # 両側検定

    return t_stat, p_value, d_mean


def _t_p_value(t: float, df: int) -> float:
    """
    t分布のp値を数値積分で近似（片側）
    Abramowitz & Stegun 26.7.8 の近似式を使用
    """
    # 正規分布への変換（df > 30 の場合は正規分布で近似）
    if df >= 30:
        return _normal_tail(t)

    # betaI の不完全ベータ関数による正確な計算
    x = df / (df + t * t)
    return 0.5 * _beta_inc(x, df / 2, 0.5)


def _normal_tail(z: float) -> float:
    """標準正規分布の片側p値（Abramowitz近似）"""
    t = 1.0 / (1.0 + 0.2316419 * z)
    poly = t * (0.319381530 + t * (-0.356563782 + t * (
        1.781477937 + t * (-1.821255978 + t * 1.330274429))))
    return poly * math.exp(-0.5 * z * z) / math.sqrt(2 * math.pi)


def _beta_inc(x: float, a: float, b: float, max_iter: int = 200) -> float:
    """不完全ベータ関数 I_x(a,b) を連分数展開で計算"""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0

    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(math.log(x) * a + math.log(1 - x) * b - lbeta) / a

    # Lentz's continued fraction
    f, c, d = 1.0, 1.0, 1.0 - (a + b) * x / (a + 1)
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    f = d

    for m in range(1, max_iter + 1):
        for step in range(2):
            if step == 0:
                num = m * (b - m) * x / ((a + 2*m - 1) * (a + 2*m))
            else:
                num = -(a + m) * (a + b + m) * x / ((a + 2*m) * (a + 2*m + 1))

            d = 1.0 + num * d
            c = 1.0 + num / c
            if abs(d) < 1e-30:
                d = 1e-30
            if abs(c) < 1e-30:
                c = 1e-30
            d = 1.0 / d
            delta = c * d
            f *= delta

            if abs(delta - 1.0) < 1e-10:
                return front * f

    return front * f


def cohens_d(a: list, b: list) -> float:
    """Cohen's d 効果量"""
    diffs = [bi - ai for ai, bi in zip(a, b)]
    d_mean = mean(diffs)
    # 対応あり検定用のd: 差分の平均 / 差分のSD
    d_std = std(diffs)
    if d_std == 0:
        return float("inf") if d_mean != 0 else 0.0
    return d_mean / d_std


def confidence_interval_95(a: list, b: list) -> tuple[float, float]:
    """差分の95%信頼区間"""
    n = len(a)
    diffs = [bi - ai for ai, bi in zip(a, b)]
    d_mean = mean(diffs)
    d_std = std(diffs)
    se = d_std / math.sqrt(n)

    # t臨界値（df=n-1）
    # n=5 の場合 df=4 → t_crit ≈ 2.776
    t_crits = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776,
               5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306,
               9: 2.262, 10: 2.228, 29: 2.045, 30: 2.042}
    df = n - 1
    t_crit = t_crits.get(df, 1.96)  # 30以上は正規近似

    margin = t_crit * se
    return (d_mean - margin, d_mean + margin)


def interpret_p(p: float, alpha: float = 0.05) -> str:
    if p < 0.001:
        return f"p={p:.4f} *** (α=0.05 で高度に有意)"
    elif p < 0.01:
        return f"p={p:.4f} ** (α=0.05 で有意)"
    elif p < alpha:
        return f"p={p:.4f} * (α=0.05 で有意)"
    elif p < 0.1:
        return f"p={p:.4f} （有意傾向、ただしα=0.05 では非有意）"
    else:
        return f"p={p:.4f} （有意差なし）"


def interpret_d(d: float) -> str:
    ad = abs(d)
    if ad < 0.2:
        return f"d={d:.3f} → 効果量: 無視できるレベル"
    elif ad < 0.5:
        return f"d={d:.3f} → 効果量: 小 (small)"
    elif ad < 0.8:
        return f"d={d:.3f} → 効果量: 中 (medium)"
    else:
        return f"d={d:.3f} → 効果量: 大 (large)"


# ─────────────────────────────────────────
# メイン分析
# ─────────────────────────────────────────

def run_analysis():
    # 試行データを読み込む
    trial_files = sorted(TRIALS_DIR.glob("trial_*.json"))
    if not trial_files:
        print("エラー: 試行データが見つかりません。")
        print("  先に run_trials.py を実行してください。")
        sys.exit(1)

    trials = []
    for f in trial_files:
        data = json.loads(f.read_text(encoding="utf-8"))
        if data.get("completed"):
            trials.append(data)

    n = len(trials)
    print()
    print("=" * 60)
    print(f"  統計的有意性検定  (n={n} 試行)")
    print("=" * 60)

    if n < 3:
        print(f"\n⚠ 試行数が {n} と少なすぎます。最低3試行が必要です。")
        sys.exit(1)

    # ── データ抽出 ──
    acc_a_total  = [t["summary"]["acc_a_total"]  for t in trials]
    acc_b_total  = [t["summary"]["acc_b_total"]  for t in trials]
    acc_a_second = [t["summary"]["acc_a_second"] for t in trials]
    acc_b_second = [t["summary"]["acc_b_second"] for t in trials]
    diff_second  = [t["summary"]["diff_second"]  for t in trials]

    # ── 記述統計 ──
    print(f"\n【記述統計】")
    print(f"{'':20} {'実験A(固定)':>12} {'実験B(可変)':>12} {'差(B-A)':>10}")
    print("-" * 58)

    def row(label, a_list, b_list):
        a_m = mean(a_list)
        b_m = mean(b_list)
        diffs = [b - a for a, b in zip(a_list, b_list)]
        d_m = mean(diffs)
        a_s = std(a_list) if len(a_list) > 1 else 0
        b_s = std(b_list) if len(b_list) > 1 else 0
        print(f"  {label:<18} {a_m:.1%}±{a_s:.1%}  {b_m:.1%}±{b_s:.1%}  {d_m:+.1%}")

    row("全体正解率", acc_a_total, acc_b_total)
    row("後半50問", acc_a_second, acc_b_second)

    print(f"\n  試行別 後半正解率:")
    print(f"  {'試行':>4}  {'実験A':>8}  {'実験B':>8}  {'差(B-A)':>9}  {'判定':>6}")
    print(f"  {'-'*4}  {'-'*8}  {'-'*8}  {'-'*9}  {'-'*6}")
    for t in trials:
        a = t["summary"]["acc_a_second"]
        b = t["summary"]["acc_b_second"]
        d = t["summary"]["diff_second"]
        mark = "B優位 ✓" if d > 0 else "A優位" if d < 0 else "同率"
        print(f"  {t['trial_id']:>4}  {a:>8.1%}  {b:>8.1%}  {d:>+9.1%}  {mark:>6}")

    # ── 検定1: 全体正解率 ──
    print(f"\n【検定1: 全体正解率（対応のあるt検定）】")
    t1, p1, d1_mean = paired_t_test(acc_a_total, acc_b_total)
    d1 = cohens_d(acc_a_total, acc_b_total)
    ci1 = confidence_interval_95(acc_a_total, acc_b_total)
    print(f"  t({n-1}) = {t1:.4f}")
    print(f"  {interpret_p(p1)}")
    print(f"  {interpret_d(d1)}")
    print(f"  95%CI: [{ci1[0]:+.4f}, {ci1[1]:+.4f}]")

    # ── 検定2: 後半50問 ──
    print(f"\n【検定2: 後半50問正解率（対応のあるt検定）★主要検定】")
    t2, p2, d2_mean = paired_t_test(acc_a_second, acc_b_second)
    d2 = cohens_d(acc_a_second, acc_b_second)
    ci2 = confidence_interval_95(acc_a_second, acc_b_second)
    print(f"  t({n-1}) = {t2:.4f}")
    print(f"  {interpret_p(p2)}")
    print(f"  {interpret_d(d2)}")
    print(f"  95%CI: [{ci2[0]:+.4f}, {ci2[1]:+.4f}]")

    # ── 仮説判定 ──
    print(f"\n{'='*60}")
    print(f"  仮説判定")
    print(f"{'='*60}")

    b_wins = sum(1 for d in diff_second if d > 0)
    hypothesis_supported = (p2 < 0.05) and (d2_mean > 0)

    print(f"\n  仮説:「可変構造は固定構造より後半の正解率が高い」")
    print(f"\n  B優位の試行数: {b_wins}/{n}")
    print(f"  後半差の平均:  {d2_mean:+.1%}")
    print()

    if hypothesis_supported:
        print("  ✓ 仮説支持")
        print(f"    統計的に有意（p={p2:.4f} < 0.05）かつ")
        print(f"    実験Bが実験Aを平均 {d2_mean:+.1%} 上回った")
    elif p2 < 0.05 and d2_mean < 0:
        print("  ✗ 仮説否定（逆方向に有意）")
        print(f"    統計的に有意（p={p2:.4f} < 0.05）だが")
        print(f"    実験Aが実験Bを上回った（差={d2_mean:+.1%}）")
    elif p2 >= 0.05 and d2_mean > 0:
        print("  △ 仮説：傾向あり・有意差なし")
        print(f"    B優位の傾向（平均{d2_mean:+.1%}）はあるが")
        print(f"    統計的に有意ではない（p={p2:.4f} ≥ 0.05）")
        print(f"    → 試行数を増やすか、タスク設計を見直すことで改善する可能性あり")
    else:
        print("  ✗ 仮説否定")
        print(f"    有意差なし（p={p2:.4f}）かつB優位の傾向もなし")
        print(f"    → 現在の設計では可変構造の優位性は確認できなかった")

    print()
    print(f"  ⚠ 注意: n={n}は最低ラインです。より確実な結論には")
    print(f"    n≥10が推奨されます。")

    # ── 結果保存 ──
    analysis_result = {
        "n_trials": n,
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "descriptive": {
            "acc_a_total_mean":  mean(acc_a_total),
            "acc_b_total_mean":  mean(acc_b_total),
            "acc_a_second_mean": mean(acc_a_second),
            "acc_b_second_mean": mean(acc_b_second),
            "diff_second_mean":  d2_mean,
            "diff_second_std":   std(diff_second) if n > 1 else 0,
            "b_wins": b_wins,
        },
        "test_total": {
            "t_stat": t1, "p_value": p1,
            "cohens_d": d1, "ci_95": list(ci1),
        },
        "test_second_half": {
            "t_stat": t2, "p_value": p2,
            "cohens_d": d2, "ci_95": list(ci2),
        },
        "hypothesis": {
            "supported": hypothesis_supported,
            "p_value": p2,
            "mean_diff": d2_mean,
            "b_wins": f"{b_wins}/{n}",
        },
    }

    ANALYSIS_PATH.write_text(
        json.dumps(analysis_result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"\n  分析結果を保存: {ANALYSIS_PATH}")

    return analysis_result


if __name__ == "__main__":
    run_analysis()
