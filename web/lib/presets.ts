export const TICKER_PRESETS: Record<string, Record<string, string>> = {
  銀行: {
    "8411.T": "みずほFG",
    "8308.T": "りそなHD",
    "8306.T": "三菱UFJ",
    "7182.T": "ゆうちょ",
  },
  自動車: {
    "7201.T": "日産",
    "7203.T": "トヨタ",
    "7267.T": "ホンダ",
  },
  電子: {
    "6981.T": "村田",
    "6971.T": "京セラ",
    "6758.T": "ソニーG",
  },
};

export const ALL_TICKERS: Record<string, string> = Object.assign(
  {},
  ...Object.values(TICKER_PRESETS),
);
