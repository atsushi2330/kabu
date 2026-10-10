"""コインテグレーションペアスキャナ."""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import combinations

import pandas as pd

from .cointegration import PairAnalysisResult, analyze_pair


SECTOR_PRESETS: dict[str, dict[str, str]] = {
    "banks": {
        "8306.T": "三菱UFJ",
        "8316.T": "みずほ",
        "8411.T": "みずほFG",
        "8308.T": "りそな",
        "7182.T": "ゆうちょ",
        "8354.T": "ふくおかFG",
    },
    "electronics": {
        "6981.T": "村田製作所",
        "6976.T": "太陽誘電",
        "6762.T": "TDK",
        "6971.T": "京セラ",
        "6758.T": "ソニーG",
        "8035.T": "東京エレクトロン",
    },
    "auto": {
        "7203.T": "トヨタ",
        "7267.T": "ホンダ",
        "7201.T": "日産",
        "7269.T": "スズキ",
        "5108.T": "ブリヂストン",
    },
}


@dataclass
class ScanRow:
    ticker_a: str
    ticker_b: str
    name_a: str
    name_b: str
    coint_pvalue: float
    adf_pvalue: float
    beta: float
    half_life: float
    z_crossings_per_year: float
    is_cointegrated: bool
    score: float


def _pair_score(result: PairAnalysisResult) -> float:
    """高いほど良いペア（0〜100）."""
    if not result.is_cointegrated:
        return 0.0

    coint_score = max(0.0, (0.05 - result.coint_pvalue) / 0.05) * 30
    adf_score = max(0.0, (0.05 - result.adf_pvalue) / 0.05) * 20

    hl = result.half_life
    if not math.isfinite(hl):
        hl_score = 0.0
    elif 5 <= hl <= 60:
        hl_score = 25.0
    elif hl < 5:
        hl_score = 10.0
    else:
        hl_score = max(0.0, 25.0 - (hl - 60) * 0.3)

    z_score = min(result.z_crossings_per_year, 20) / 20 * 25
    return round(coint_score + adf_score + hl_score + z_score, 1)


def scan_pairs(
    prices: pd.DataFrame,
    names: dict[str, str] | None = None,
) -> list[ScanRow]:
    """全 C(N,2) ペアを検定してスコア順に返す."""
    names = names or {}
    tickers = list(prices.columns)
    rows: list[ScanRow] = []

    for a, b in combinations(tickers, 2):
        pair_prices = prices[[a, b]].dropna()
        if len(pair_prices) < 60:
            continue
        try:
            result = analyze_pair(pair_prices)
        except Exception:
            continue

        rows.append(
            ScanRow(
                ticker_a=a,
                ticker_b=b,
                name_a=names.get(a, a),
                name_b=names.get(b, b),
                coint_pvalue=result.coint_pvalue,
                adf_pvalue=result.adf_pvalue,
                beta=result.beta,
                half_life=result.half_life,
                z_crossings_per_year=result.z_crossings_per_year,
                is_cointegrated=result.is_cointegrated,
                score=_pair_score(result),
            )
        )

    rows.sort(key=lambda r: (r.is_cointegrated, r.score, -r.coint_pvalue), reverse=True)
    return rows


def to_dataframe(rows: list[ScanRow]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "pair": f"{r.name_a} x {r.name_b}",
                "ticker_a": r.ticker_a,
                "ticker_b": r.ticker_b,
                "coint_p": r.coint_pvalue,
                "adf_p": r.adf_pvalue,
                "beta": r.beta,
                "half_life": r.half_life,
                "z_per_year": r.z_crossings_per_year,
                "valid": r.is_cointegrated,
                "score": r.score,
            }
            for r in rows
        ]
    )
