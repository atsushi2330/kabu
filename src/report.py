"""ターミナル向けテキストレポート."""

from __future__ import annotations

import math

from .cointegration import PairAnalysisResult


def format_report(result: PairAnalysisResult, pair_name: str | None = None) -> str:
    title = pair_name or f"{result.ticker_a} × {result.ticker_b}"
    def mark(passed: bool) -> str:
        return "OK" if passed else "NG"

    hl = (
        f"{result.half_life:.1f} 日"
        if math.isfinite(result.half_life)
        else "推定不可（平均回帰弱い）"
    )

    lines = [
        "",
        f"=== ペア分析: {title} ===",
        "",
        "[検定結果]",
        f"  Engle-Granger p-value : {result.coint_pvalue:.4f}  [{mark(result.coint_pvalue < 0.05)}] (< 0.05)",
        f"  ADF（スプレッド）      : {result.adf_pvalue:.4f}  [{mark(result.adf_pvalue < 0.05)}] (< 0.05)",
        "",
        "[関係式]",
        f"  {result.ticker_a} = {result.alpha:.2f} + {result.beta:.4f} × {result.ticker_b}",
        f"  スプレッド = {result.ticker_a} − α − β×{result.ticker_b}",
        "",
        "[復元力]",
        f"  半減期                 : {hl}",
        f"  |Z| > 2 の回数/年      : {result.z_crossings_per_year:.1f} 回",
        "",
        "[総合判定]",
        f"  {'[*] ペア候補として有効（要バックテスト）' if result.is_cointegrated else '[!] コインテグレーション弱い - 別ペアを検討'}",
        "",
    ]
    return "\n".join(lines)
