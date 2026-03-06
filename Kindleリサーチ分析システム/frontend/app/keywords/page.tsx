"use client";

import { useState } from "react";
import { Search, Star } from "lucide-react";

interface SearchVolumeData {
  estimated: number;
  confidence: 1 | 2 | 3;
  note: string;
  merchant_words?: number;
  autocomplete_score?: number;
}

interface KeywordResult {
  keyword: string;
  search_volume: SearchVolumeData;
  competition: string | null;
  book_count: number | null;
  avg_bsr: number | null;
  trend: string | null;
  related_keywords: string[];
}

interface SuggestionsData {
  keyword: string;
  suggestions: string[];
  autocomplete_score: number;
  note: string;
}

export default function KeywordsPage() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<KeywordResult | null>(null);
  const [suggestions, setSuggestions] = useState<SuggestionsData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const analyze = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);

    try {
      const [analysisRes, suggestRes] = await Promise.all([
        fetch(`/api/v1/keywords/${encodeURIComponent(query)}/analysis`),
        fetch(`/api/v1/keywords/suggestions?seed=${encodeURIComponent(query)}`),
      ]);

      if (analysisRes.ok) {
        setResult(await analysisRes.json());
      }
      if (suggestRes.ok) {
        setSuggestions(await suggestRes.json());
      }
    } catch (e) {
      setError("APIサーバーに接続できません。バックエンドが起動しているか確認してください。");
    } finally {
      setLoading(false);
    }
  };

  const competitionColor = (c: string | null) => {
    if (c === "low") return "text-green-400";
    if (c === "medium") return "text-yellow-400";
    if (c === "high") return "text-red-400";
    return "text-gray-400";
  };

  const trendLabel = (t: string | null) => {
    if (t === "rising") return "📈 上昇中";
    if (t === "declining") return "📉 下降中";
    return "➡️ 安定";
  };

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-white mb-6">🔍 キーワード分析</h1>

      {/* 検索ボックス */}
      <div className="flex gap-3 mb-8">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && analyze()}
          placeholder="例: AI活用, NISA, 防災..."
          className="flex-1 bg-gray-900 border border-gray-700 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
        />
        <button
          onClick={analyze}
          disabled={loading}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-6 py-3 rounded-xl font-medium transition-colors"
        >
          <Search className="w-4 h-4" />
          {loading ? "分析中..." : "分析"}
        </button>
      </div>

      {error && (
        <div className="bg-red-900/30 border border-red-700 rounded-xl p-4 mb-6 text-red-300 text-sm">
          {error}
        </div>
      )}

      {/* 分析結果 */}
      {result && (
        <div className="space-y-5">
          {/* 検索ボリュームカード */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold text-white mb-4">
              「{result.keyword}」 の分析結果
            </h2>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
              <div>
                <p className="text-gray-400 text-xs mb-1">推定月間検索数</p>
                <p className="text-2xl font-bold text-blue-400">
                  {result.search_volume.estimated.toLocaleString()}
                </p>
                <div className="flex items-center gap-1 mt-1">
                  {Array.from({ length: result.search_volume.confidence }).map((_, i) => (
                    <Star key={i} className="w-3 h-3 text-yellow-400 fill-yellow-400" />
                  ))}
                  {Array.from({ length: 3 - result.search_volume.confidence }).map((_, i) => (
                    <Star key={i} className="w-3 h-3 text-gray-600" />
                  ))}
                </div>
              </div>
              <div>
                <p className="text-gray-400 text-xs mb-1">競合度</p>
                <p className={`text-xl font-bold ${competitionColor(result.competition)}`}>
                  {result.competition === "low" ? "低" : result.competition === "medium" ? "中" : result.competition === "high" ? "高" : "—"}
                </p>
              </div>
              <div>
                <p className="text-gray-400 text-xs mb-1">登録書籍数</p>
                <p className="text-xl font-bold text-white">
                  {result.book_count?.toLocaleString() ?? "—"}
                </p>
              </div>
              <div>
                <p className="text-gray-400 text-xs mb-1">トレンド</p>
                <p className="text-xl font-bold text-white">{trendLabel(result.trend)}</p>
              </div>
            </div>

            <p className="text-xs text-gray-500 bg-gray-800 rounded px-3 py-2">
              ⚠️ {result.search_volume.note}
            </p>
          </div>

          {/* 関連キーワード */}
          {result.related_keywords.length > 0 && (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
              <h3 className="text-sm font-semibold text-gray-300 mb-3">関連キーワード</h3>
              <div className="flex flex-wrap gap-2">
                {result.related_keywords.map((kw) => (
                  <button
                    key={kw}
                    onClick={() => { setQuery(kw); }}
                    className="px-3 py-1 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-full text-sm transition-colors"
                  >
                    {kw}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Autocomplete候補 */}
      {suggestions && suggestions.suggestions.length > 0 && (
        <div className="mt-5 bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h3 className="text-sm font-semibold text-gray-300 mb-3">
            Amazon検索候補（需要シグナル）
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {suggestions.suggestions.map((s) => (
              <button
                key={s}
                onClick={() => { setQuery(s); }}
                className="text-left px-3 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-sm transition-colors"
              >
                🔍 {s}
              </button>
            ))}
          </div>
          <p className="text-xs text-gray-500 mt-3">{suggestions.note}</p>
        </div>
      )}
    </div>
  );
}
