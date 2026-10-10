"""押し目買いバックテスト Web UI (Streamlit)."""

from __future__ import annotations

import io
from itertools import product

import pandas as pd
import streamlit as st

from src.fetch import fetch_ohlc
from src.plotly_charts import make_equity_chart, trades_to_dataframe
from src.presets import ALL_TICKERS, TICKER_PRESETS
from src.single_backtest import run_dip_buy_backtest

st.set_page_config(page_title="kabu 押し目買い BT", layout="wide", page_icon="📈")

st.title("📈 kabu — 押し目買いバックテスト")
st.caption("銘柄選択 → 条件設定 → バックテスト → グラフ閲覧")

with st.sidebar:
    st.header("銘柄")
    preset_group = st.selectbox("プリセット", ["カスタム"] + list(TICKER_PRESETS.keys()))
    if preset_group != "カスタム":
        preset_tickers = list(TICKER_PRESETS[preset_group].keys())
        selected = st.multiselect(
            "銘柄（複数可）",
            preset_tickers,
            default=preset_tickers[:2],
            format_func=lambda t: f"{TICKER_PRESETS[preset_group][t]} ({t})",
        )
    else:
        custom = st.text_input("ティッカー（カンマ区切り）", "8411.T,8308.T,7201.T")
        selected = [t.strip() for t in custom.split(",") if t.strip()]

    st.header("条件")
    entry_drop = st.slider("エントリー（前日比 -%）", 1, 10, 5)
    take_profit = st.slider("利確（+%）", 1, 15, 10)
    stop_loss = st.slider("損切（-%）", 1, 10, 3)
    years = st.slider("期間（年）", 1, 10, 5)
    capital = st.number_input("初期資金（円）", 100_000, 10_000_000, 1_000_000, step=100_000)

    st.header("モード")
    mode = st.radio("実行モード", ["単一条件", "パラメータ探索"], horizontal=True)

    if mode == "パラメータ探索":
        st.caption("1〜N% を1%刻みで全組み合わせ")
        sweep_max = st.selectbox("探索上限（%）", [5, 7, 10], index=2)
        min_trades = st.number_input("最小トレード数", 1, 50, 5)

    run = st.button("▶ 実行", type="primary", use_container_width=True)


def run_single(tickers: list[str]) -> None:
    if not tickers:
        st.warning("銘柄を1つ以上選んで")
        return

    summary_rows = []
    for ticker in tickers:
        name = ALL_TICKERS.get(ticker, ticker)
        with st.spinner(f"{name} 取得中..."):
            ohlc = fetch_ohlc(ticker, years=years)
            ohlc.attrs["ticker"] = ticker
            result = run_dip_buy_backtest(
                ohlc,
                entry_drop_pct=entry_drop,
                take_profit_pct=take_profit,
                stop_loss_pct=stop_loss,
                initial_capital=capital,
            )

        summary_rows.append(
            {
                "銘柄": name,
                "ticker": ticker,
                "リターン%": result.total_return_pct,
                "B&H%": result.buy_hold_return_pct,
                "勝率%": result.win_rate_pct,
                "トレード": result.num_trades,
                "最大DD%": result.max_drawdown_pct,
                "Sharpe": result.sharpe_ratio,
            }
        )

        st.subheader(f"{name} ({ticker})")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("リターン", f"{result.total_return_pct:+.1f}%")
        col2.metric("B&H", f"{result.buy_hold_return_pct:+.1f}%")
        col3.metric("勝率", f"{result.win_rate_pct:.1f}%")
        col4.metric("最大DD", f"{result.max_drawdown_pct:.1f}%")

        fig = make_equity_chart(ohlc, result, name)
        st.plotly_chart(fig, use_container_width=True)

        trades_df = trades_to_dataframe(result)
        with st.expander("トレード一覧"):
            st.dataframe(trades_df, use_container_width=True)
            csv = trades_df.to_csv(index=False).encode("utf-8-sig")
            st.download_button("CSVダウンロード", csv, f"trades_{ticker.replace('.', '_')}.csv")

    if len(summary_rows) > 1:
        st.subheader("比較サマリー")
        st.dataframe(pd.DataFrame(summary_rows), use_container_width=True)


def run_sweep(tickers: list[str]) -> None:
    if not tickers:
        st.warning("銘柄を1つ以上選んで")
        return

    grid = list(range(1, sweep_max + 1))
    total = len(grid) ** 3 * len(tickers)
    st.info(f"探索: {len(grid)}³ × {len(tickers)}銘柄 = {total:,} パターン")

    progress = st.progress(0)
    rows: list[dict] = []
    done = 0

    for ticker in tickers:
        name = ALL_TICKERS.get(ticker, ticker)
        ohlc = fetch_ohlc(ticker, years=years)
        ohlc.attrs["ticker"] = ticker
        close = ohlc["Close"].squeeze()
        bh = (float(close.iloc[-1]) / float(close.iloc[1]) - 1) * 100

        for e, tp, sl in product(grid, grid, grid):
            r = run_dip_buy_backtest(
                ohlc,
                entry_drop_pct=e,
                take_profit_pct=tp,
                stop_loss_pct=sl,
                initial_capital=capital,
            )
            rows.append(
                {
                    "銘柄": name,
                    "ticker": ticker,
                    "entry": e,
                    "tp": tp,
                    "sl": sl,
                    "return_pct": r.total_return_pct,
                    "bh_pct": bh,
                    "win_rate": r.win_rate_pct,
                    "trades": r.num_trades,
                    "max_dd": r.max_drawdown_pct,
                }
            )
            done += 1
            progress.progress(done / total)

    df = pd.DataFrame(rows)
    valid = df[df["trades"] >= min_trades]

    st.subheader("銘柄別 Top 10")
    for ticker in tickers:
        name = ALL_TICKERS.get(ticker, ticker)
        sub = valid[valid["ticker"] == ticker].nlargest(10, "return_pct")
        st.markdown(f"**{name}**")
        st.dataframe(sub, use_container_width=True)

    buf = io.StringIO()
    df.to_csv(buf, index=False)
    st.download_button(
        "全結果 CSV",
        buf.getvalue().encode("utf-8-sig"),
        "sweep_results.csv",
        use_container_width=True,
    )


if run:
    if mode == "単一条件":
        run_single(selected)
    else:
        run_sweep(selected)

else:
    st.markdown(
        """
        ### 使い方
        1. 左サイドバーで **銘柄** と **条件** を設定
        2. **▶ 実行** をクリック
        3. グラフは **ズーム・パン** 可能（Plotly）

        ### ルール
        - **買い**: 前日比が -N% 以下 → 終値で全額買い
        - **利確**: 買値から +X%（日中 High）
        - **損切**: 買値から -Y%（日中 Low、同日は損切優先）

        ### 公開について
        - **Streamlit Cloud**: この `app.py` をそのまま公開可能（無料）
        - **Vercel**: Streamlit 非対応 → `web/` フォルダの Next.js 版を使用
        """
    )
