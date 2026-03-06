import { BookOpen, TrendingUp, Search, BarChart3, Image, Zap } from "lucide-react";
import Link from "next/link";

const features = [
  {
    icon: Search,
    title: "キーワード分析",
    desc: "推定月間検索ボリューム・競合度・関連キーワードを瞬時に表示",
    href: "/keywords",
    color: "text-blue-400",
    bg: "bg-blue-500/10",
  },
  {
    icon: TrendingUp,
    title: "ジャンルトレンド",
    desc: "今日・1週間・30日・半年の時間軸でジャンルの勢いを把握",
    href: "/genres",
    color: "text-green-400",
    bg: "bg-green-500/10",
  },
  {
    icon: BookOpen,
    title: "タイトル分析",
    desc: "AIがタイトルをスコアリングして改善案を最大5パターン提案",
    href: "/title-analyzer",
    color: "text-purple-400",
    bg: "bg-purple-500/10",
  },
  {
    icon: Image,
    title: "表紙傾向分析",
    desc: "売れているジャンルの配色・フォント・構図をギャラリーで確認",
    href: "/covers",
    color: "text-orange-400",
    bg: "bg-orange-500/10",
  },
  {
    icon: BarChart3,
    title: "売上予測",
    desc: "BSR→推定月間販売数を変換。目標BSRの達成シミュレーション",
    href: "/prediction",
    color: "text-red-400",
    bg: "bg-red-500/10",
  },
  {
    icon: Zap,
    title: "AI提案",
    desc: "ターゲット層・ニッチジャンル・タイトル生成をAIが一括提案",
    href: "/keywords",
    color: "text-yellow-400",
    bg: "bg-yellow-500/10",
  },
];

export default function DashboardPage() {
  return (
    <div className="max-w-6xl mx-auto">
      {/* ヘッダー */}
      <div className="mb-10">
        <h1 className="text-3xl font-bold text-white mb-2">
          📚 Kindleリサーチ分析システム
        </h1>
        <p className="text-gray-400">
          Amazon Kindle日本市場専用リサーチツール。売れる本を科学的に設計する。
        </p>
      </div>

      {/* 市場概要 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
        {[
          { label: "日本電子書籍市場", value: "6,703億円", sub: "2024年実績" },
          { label: "年間成長率", value: "+3.9%", sub: "前年比" },
          { label: "Kindle市場シェア", value: "28.6%", sub: "購入先1位" },
          { label: "競合ツール", value: "0件", sub: "日本語専用（ブルーオーシャン）" },
        ].map((stat) => (
          <div key={stat.label} className="bg-gray-900 rounded-xl p-4 border border-gray-800">
            <p className="text-gray-400 text-xs mb-1">{stat.label}</p>
            <p className="text-2xl font-bold text-white">{stat.value}</p>
            <p className="text-gray-500 text-xs mt-1">{stat.sub}</p>
          </div>
        ))}
      </div>

      {/* 機能カード */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {features.map((f) => (
          <Link
            key={f.href + f.title}
            href={f.href}
            className="group bg-gray-900 border border-gray-800 rounded-xl p-6 hover:border-gray-600 transition-all duration-200"
          >
            <div className={`inline-flex p-3 rounded-lg ${f.bg} mb-4`}>
              <f.icon className={`w-6 h-6 ${f.color}`} />
            </div>
            <h2 className="text-lg font-semibold text-white mb-2 group-hover:text-blue-300 transition-colors">
              {f.title}
            </h2>
            <p className="text-gray-400 text-sm leading-relaxed">{f.desc}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
