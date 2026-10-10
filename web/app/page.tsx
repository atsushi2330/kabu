import BacktestApp from "@/components/BacktestApp";

export default function Home() {
  return (
    <main>
      <h1>📈 kabu — 押し目買いバックテスト</h1>
      <p className="sub">銘柄選択 → 条件設定 → バックテスト → グラフ（Vercel 公開版）</p>
      <BacktestApp />
    </main>
  );
}
