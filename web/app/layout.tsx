import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "kabu — 押し目買い BT",
  description: "単一銘柄 押し目買いバックテスト",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ja">
      <body>{children}</body>
    </html>
  );
}
