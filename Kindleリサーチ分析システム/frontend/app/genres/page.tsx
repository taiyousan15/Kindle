"use client";

import { useState } from "react";
import { TrendingUp } from "lucide-react";

const GENRES = [
  "ビジネス・経済", "自己啓発", "コンピュータ・IT",
  "資格・検定", "語学", "趣味・実用", "健康・医学", "マンガ",
];

type Period = "daily" | "weekly" | "monthly" | "halfyear";

const PERIOD_LABELS: Record<Period, string> = {
  daily: "今日",
  weekly: "1週間",
  monthly: "30日",
  halfyear: "半年",
};

interface GenreTrend {
  genre: string;
  period: string;
  avg_bsr: number | null;
  trend_score: number | null;
  top_keywords: string[];
  book_count: number | null;
}

export default function GenresPage() {
  const [selectedGenre, setSelectedGenre] = useState("ビジネス・経済");
  const [period, setPeriod] = useState<Period>("monthly");
  const [trends, setTrends] = useState<GenreTrend[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchTrends = async (genre: string, p: Period) => {
    setLoading(true);
    try {
      const res = await fetch(
        `/api/v1/genres/${encodeURIComponent(genre)}/trend?period=${p}`
      );
      if (res.ok) {
        setTrends(await res.json());
      } else {
        setTrends([]);
      }
    } catch {
      setTrends([]);
    } finally {
      setLoading(false);
    }
  };

  const handleGenreSelect = (genre: string) => {
    setSelectedGenre(genre);
    fetchTrends(genre, period);
  };

  const handlePeriodChange = (p: Period) => {
    setPeriod(p);
    fetchTrends(selectedGenre, p);
  };

  const latest = trends[0];

  return (
    <div className="max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold text-white mb-6">📈 ジャンルトレンド</h1>

      {/* ジャンル選択 */}
      <div className="flex flex-wrap gap-2 mb-5">
        {GENRES.map((g) => (
          <button
            key={g}
            onClick={() => handleGenreSelect(g)}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
              selectedGenre === g
                ? "bg-blue-600 text-white"
                : "bg-gray-800 text-gray-400 hover:bg-gray-700"
            }`}
          >
            {g}
          </button>
        ))}
      </div>

      {/* 期間選択 */}
      <div className="flex gap-2 mb-6">
        {(Object.keys(PERIOD_LABELS) as Period[]).map((p) => (
          <button
            key={p}
            onClick={() => handlePeriodChange(p)}
            className={`px-4 py-2 rounded-lg text-sm transition-colors ${
              period === p
                ? "bg-green-600 text-white"
                : "bg-gray-800 text-gray-400 hover:bg-gray-700"
            }`}
          >
            {PERIOD_LABELS[p]}
          </button>
        ))}
      </div>

      {loading && (
        <div className="flex items-center gap-3 text-gray-400 py-10">
          <TrendingUp className="w-5 h-5 animate-pulse" />
          データを取得中...
        </div>
      )}

      {!loading && latest && (
        <div className="space-y-5">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-semibold text-white">{latest.genre}</h2>
              {latest.trend_score != null && (
                <div className="text-center">
                  <p className="text-3xl font-bold text-green-400">
                    {(latest.trend_score * 100).toFixed(0)}
                  </p>
                  <p className="text-gray-500 text-xs">TrendScore</p>
                </div>
              )}
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div>
                <p className="text-gray-400 text-xs mb-1">平均BSR</p>
                <p className="text-xl font-bold text-white">
                  {latest.avg_bsr?.toLocaleString() ?? "—"}
                </p>
              </div>
              <div>
                <p className="text-gray-400 text-xs mb-1">期間</p>
                <p className="text-xl font-bold text-white">{PERIOD_LABELS[period]}</p>
              </div>
              <div>
                <p className="text-gray-400 text-xs mb-1">登録書籍数</p>
                <p className="text-xl font-bold text-white">
                  {latest.book_count?.toLocaleString() ?? "—"}
                </p>
              </div>
            </div>

            {latest.top_keywords.length > 0 && (
              <div className="mt-5">
                <p className="text-gray-400 text-xs mb-2">急上昇キーワード</p>
                <div className="flex flex-wrap gap-2">
                  {latest.top_keywords.map((kw) => (
                    <span key={kw} className="px-3 py-1 bg-green-900/30 text-green-300 rounded-full text-xs">
                      🔥 {kw}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {!loading && trends.length === 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-10 text-center text-gray-500">
          <TrendingUp className="w-8 h-8 mx-auto mb-3 opacity-30" />
          <p>データがありません。バックエンドを起動してからジャンルを選択してください。</p>
        </div>
      )}
    </div>
  );
}
