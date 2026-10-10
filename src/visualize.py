"""ペア分析グラフ生成."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm

from .cointegration import PairAnalysisResult

plt.rcParams["font.family"] = ["Meiryo", "Yu Gothic", "MS Gothic", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def _normalize(series: pd.Series) -> pd.Series:
    return series / series.iloc[0] * 100


def plot_pair_analysis(
    prices: pd.DataFrame,
    result: PairAnalysisResult,
    output_path: Path,
    pair_name: str | None = None,
) -> Path:
    """4枚構成の分析グラフを PNG で保存."""
    a, b = result.ticker_a, result.ticker_b
    title = pair_name or f"{a} × {b}"

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f"ペア分析: {title}", fontsize=14, fontweight="bold")

    # 1. 正規化株価
    ax = axes[0, 0]
    ax.plot(prices.index, _normalize(prices[a]), label=a, linewidth=1.2)
    ax.plot(prices.index, _normalize(prices[b]), label=b, linewidth=1.2)
    ax.set_title("正規化株価（基準=100）")
    ax.set_ylabel("指数")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    # 2. 散布図 + 回帰線
    ax = axes[0, 1]
    ax.scatter(prices[b], prices[a], alpha=0.4, s=8, c="#599CE7")
    x_line = np.linspace(prices[b].min(), prices[b].max(), 100)
    y_line = result.alpha + result.beta * x_line
    ax.plot(x_line, y_line, color="#CF2D56", linewidth=2, label=f"β={result.beta:.3f}")
    ax.set_xlabel(b)
    ax.set_ylabel(a)
    ax.set_title("散布図 + 回帰線")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    # 3. スプレッド
    ax = axes[1, 0]
    ax.plot(result.spread.index, result.spread.values, color="#3685BF", linewidth=1)
    ax.axhline(0, color="gray", linestyle="--", linewidth=0.8)
    ax.fill_between(
        result.spread.index,
        result.spread.values,
        0,
        alpha=0.15,
        color="#3685BF",
    )
    ax.set_title(f"スプレッド S = {a} − α − β×{b}")
    ax.set_ylabel("スプレッド")
    ax.grid(True, alpha=0.3)

    # 4. Zスコア
    ax = axes[1, 1]
    ax.plot(result.zscore.index, result.zscore.values, color="#1F8A65", linewidth=1)
    ax.axhline(0, color="gray", linestyle="--", linewidth=0.8)
    ax.axhline(2, color="#CF2D56", linestyle=":", linewidth=1, label="+2σ")
    ax.axhline(-2, color="#CF2D56", linestyle=":", linewidth=1, label="−2σ")
    ax.fill_between(
        result.zscore.index,
        result.zscore.values,
        0,
        where=result.zscore.abs() > 2,
        alpha=0.25,
        color="#CF2D56",
        label="|Z|>2",
    )
    ax.set_title("Zスコア")
    ax.set_ylabel("Z")
    ax.legend(fontsize=8, loc="upper right")
    ax.grid(True, alpha=0.3)

    status = "有効" if result.is_cointegrated else "要再検討"
    hl = f"{result.half_life:.1f}日" if np.isfinite(result.half_life) else "∞"
    footer = (
        f"Engle-Granger p={result.coint_pvalue:.4f}  |  "
        f"ADF p={result.adf_pvalue:.4f}  |  "
        f"半減期={hl}  |  "
        f"|Z|>2: {result.z_crossings_per_year:.1f}回/年  |  "
        f"判定: {status}"
    )
    fig.text(0.5, 0.01, footer, ha="center", fontsize=10, color="#444")

    plt.tight_layout(rect=[0, 0.03, 1, 0.96])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path
