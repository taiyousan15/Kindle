"use client";

import { useState } from "react";
import { BookOpen, Star } from "lucide-react";

interface TitleResult {
  original_title: string;
  score: number;
  length_chars: number;
  has_number: boolean;
  has_benefit: boolean;
  has_target: boolean;
  structure: string;
  improvements: string[];
  generated_titles: string[];
  analysis: string;
}

const GENRES = [
  "ビジネス・経済", "自己啓発", "コンピュータ・IT",
  "資格・検定", "語学", "健康・医学", "一般",
];

export default function TitleAnalyzerPage() {
  const [title, setTitle] = useState("");
  const [genre, setGenre] = useState("ビジネス・経済");
  const [result, setResult] = useState<TitleResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const analyze = async () => {
    if (!title.trim()) return;
    setLoading(true);
    setError(null);

    try {
      const res = await fetch("/api/v1/title/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, genre, bestseller_titles: [] }),
      });

      if (res.ok) {
        setResult(await res.json());
      } else {
        setError("分析に失敗しました。");
      }
    } catch {
      setError("APIサーバーに接続できません。");
    } finally {
      setLoading(false);
    }
  };

  const scoreColor = (score: number) =>
    score >= 70 ? "text-green-400" : score >= 50 ? "text-yellow-400" : "text-red-400";

  return (
    <div className="max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold text-white mb-6">📖 タイトル分析 & 生成</h1>

      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mb-6">
        <div className="mb-4">
          <label className="block text-sm text-gray-400 mb-2">タイトル案</label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && analyze()}
            placeholder="例: ChatGPTを使って月10万円稼ぐ方法"
            className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
          />
        </div>
        <div className="mb-5">
          <label className="block text-sm text-gray-400 mb-2">ジャンル</label>
          <select
            value={genre}
            onChange={(e) => setGenre(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:outline-none"
          >
            {GENRES.map((g) => <option key={g} value={g}>{g}</option>)}
          </select>
        </div>
        <button
          onClick={analyze}
          disabled={loading}
          className="w-full flex items-center justify-center gap-2 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white py-3 rounded-xl font-medium transition-colors"
        >
          <BookOpen className="w-4 h-4" />
          {loading ? "AI分析中..." : "タイトルを分析"}
        </button>
      </div>

      {error && (
        <div className="bg-red-900/30 border border-red-700 rounded-xl p-4 mb-5 text-red-300 text-sm">
          {error}
        </div>
      )}

      {result && (
        <div className="space-y-5">
          {/* スコアカード */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
            <div className="flex items-center justify-between mb-5">
              <h2 className="font-semibold text-white">「{result.original_title}」</h2>
              <div className="text-center">
                <p className={`text-4xl font-bold ${scoreColor(result.score)}`}>
                  {result.score}
                </p>
                <p className="text-gray-500 text-xs">/ 100</p>
              </div>
            </div>

            {/* スコアバー */}
            <div className="score-bar mb-5">
              <div
                className={`score-fill ${result.score >= 70 ? "bg-green-500" : result.score >= 50 ? "bg-yellow-500" : "bg-red-500"}`}
                style={{ width: `${result.score}%` }}
              />
            </div>

            {/* チェック項目 */}
            <div className="grid grid-cols-3 gap-3 mb-5">
              {[
                { label: "数字を含む", ok: result.has_number },
                { label: "ベネフィット明示", ok: result.has_benefit },
                { label: "ターゲット明示", ok: result.has_target },
              ].map((item) => (
                <div
                  key={item.label}
                  className={`text-center p-3 rounded-lg text-sm ${
                    item.ok ? "bg-green-900/30 text-green-300" : "bg-gray-800 text-gray-500"
                  }`}
                >
                  {item.ok ? "✓" : "✗"} {item.label}
                </div>
              ))}
            </div>

            <p className="text-sm text-gray-300 bg-gray-800 rounded-lg p-3">{result.analysis}</p>
          </div>

          {/* 改善案 */}
          {result.improvements.length > 0 && (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
              <h3 className="font-semibold text-white mb-3">改善提案</h3>
              <ul className="space-y-2">
                {result.improvements.map((imp, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-gray-300">
                    <span className="text-blue-400 shrink-0">→</span>
                    {imp}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* 生成タイトル候補 */}
          {result.generated_titles.length > 0 && (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
              <h3 className="font-semibold text-white mb-3">AIが提案するタイトル候補</h3>
              <div className="space-y-2">
                {result.generated_titles.map((t, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-3 bg-gray-800 rounded-lg px-4 py-3"
                  >
                    <Star className="w-3 h-3 text-yellow-400 shrink-0" />
                    <p className="text-white text-sm">{t}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
