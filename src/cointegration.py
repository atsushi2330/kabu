"""2銘柄ペアのコインテグレーション分析."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller, coint


@dataclass
class PairAnalysisResult:
    ticker_a: str
    ticker_b: str
    alpha: float
    beta: float
    spread: pd.Series
    zscore: pd.Series
    coint_pvalue: float
    adf_pvalue: float
    half_life: float
    z_crossings_per_year: float
    is_cointegrated: bool


def _ou_half_life(spread: pd.Series) -> float:
    """OU過程から半減期（日数）を推定."""
    lagged = spread.shift(1).dropna()
    delta = spread.diff().dropna()
    aligned = pd.concat([lagged, delta], axis=1).dropna()
    aligned.columns = ["lag", "delta"]

    if len(aligned) < 10:
        return float("nan")

    x = sm.add_constant(aligned["lag"])
    model = sm.OLS(aligned["delta"], x).fit()
    theta = -model.params["lag"]

    if theta <= 0:
        return float("inf")

    return float(np.log(2) / theta)


def analyze_pair(prices: pd.DataFrame) -> PairAnalysisResult:
    """Engle-Granger 手順でペア分析."""
    if prices.shape[1] != 2:
        raise ValueError("2列の価格 DataFrame が必要です")

    ticker_a, ticker_b = prices.columns[0], prices.columns[1]
    y = prices[ticker_a]
    x = sm.add_constant(prices[ticker_b])

    ols = sm.OLS(y, x).fit()
    alpha = float(ols.params["const"])
    beta = float(ols.params[ticker_b])
    spread = y - alpha - beta * prices[ticker_b]
    spread.name = "spread"

    zscore = (spread - spread.mean()) / spread.std()
    zscore.name = "zscore"

    _, coint_pvalue, _ = coint(prices[ticker_a], prices[ticker_b])
    adf_pvalue = float(adfuller(spread, result_object=True).pvalue)
    half_life = _ou_half_life(spread)

    years = len(spread) / 252
    z_crossings = int((zscore.abs() > 2).sum())
    z_crossings_per_year = z_crossings / years if years > 0 else 0.0

    is_cointegrated = coint_pvalue < 0.05 and adf_pvalue < 0.05

    return PairAnalysisResult(
        ticker_a=ticker_a,
        ticker_b=ticker_b,
        alpha=alpha,
        beta=beta,
        spread=spread,
        zscore=zscore,
        coint_pvalue=float(coint_pvalue),
        adf_pvalue=adf_pvalue,
        half_life=half_life,
        z_crossings_per_year=z_crossings_per_year,
        is_cointegrated=is_cointegrated,
    )
