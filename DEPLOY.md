# デプロイ手順

## 1. Streamlit（ローカル / Streamlit Cloud）

```bash
pip install -r requirements.txt
streamlit run app.py
```

### Streamlit Cloud（無料公開）

1. GitHub にリポジトリを push
2. https://streamlit.io/cloud で New app
3. Main file: `app.py`
4. パラメータ探索（1000通り）も利用可能

---

## 2. Vercel（Next.js 版）

**Streamlit は Vercel 非対応。** `web/` フォルダの Next.js アプリを使用。

```bash
cd web
npm install
npm run dev    # http://localhost:3000
```

### Vercel デプロイ

1. GitHub に push
2. https://vercel.com → Import Project
3. **Root Directory: `web`** を指定
4. Deploy

または CLI:

```bash
cd web
npx vercel
```

### Vercel の制限

| 機能 | 対応 |
|------|------|
| 銘柄選択・条件入力・バックテスト | ✅ |
| Plotly グラフ（ズーム可） | ✅ |
| 1000通りスイープ | ❌（タイムアウト）→ Streamlit 版を使用 |

---

## 機能比較

| | Streamlit (`app.py`) | Next.js (`web/`) |
|--|---------------------|------------------|
| 公開先 | Streamlit Cloud | **Vercel** |
| パラメータ探索 | ✅ | ❌ |
| ズームグラフ | ✅ Plotly | ✅ Plotly |
| セットアップ | `pip install` | `npm install` |
