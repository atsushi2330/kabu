"""銘柄プリセット."""

TICKER_PRESETS: dict[str, dict[str, str]] = {
    "銀行": {
        "8411.T": "みずほFG",
        "8308.T": "りそなHD",
        "8306.T": "三菱UFJ",
        "8316.T": "みずほ",
        "7182.T": "ゆうちょ",
    },
    "自動車": {
        "7201.T": "日産",
        "7203.T": "トヨタ",
        "7267.T": "ホンダ",
        "7269.T": "スズキ",
    },
    "電子": {
        "6981.T": "村田",
        "6971.T": "京セラ",
        "6758.T": "ソニーG",
        "8035.T": "東京エレクトロン",
    },
}

ALL_TICKERS: dict[str, str] = {}
for group in TICKER_PRESETS.values():
    ALL_TICKERS.update(group)
