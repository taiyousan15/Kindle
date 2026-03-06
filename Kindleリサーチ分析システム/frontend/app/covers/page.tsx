"use client";

import { useState } from "react";
import { Image } from "lucide-react";

interface CoverItem {
  asin: string;
  image_url: string;
  primary_colors: string[];
  font_style: string | null;
  layout: string | null;
  mood: string | null;
  ctr_score: number | null;
}

interface AnalyzeResult {
  asin: string;
  primary_colors: string[];
  font_style: string;
  layout: string;
  mood: string;
  ctr_score: number;
  analysis_text: string;
}

const MOOD_LABELS: Record<string, string> = {
  professional: "プロフェッショナル",
  casual: "カジュアル",
  dramatic: "ドラマチック",
  minimalist: "ミニマル",
  academic: "アカデミック",
};

const LAYOUT_LABELS: Record<string, string> = {
  "text-dominant": "テキスト主体",
  "image-dominant": "画像主体",
  balanced: "バランス",
};

export default function CoversPage() {
  const [imageUrl, setImageUrl] = useState("");
  const [analyzeResult, setAnalyzeResult] = useState<AnalyzeResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const analyzeUrl = async () => {
    if (!imageUrl.trim()) return;
    setLoading(true);
    setError(null);

    try {
      const res = await fetch("/api/v1/covers/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image_url: imageUrl, asin: "CUSTOM" }),
      });

      if (res.ok) {
        setAnalyzeResult(await res.json());
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
    <div className="max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-white mb-6">🖼️ 表紙分析</h1>

      {/* 表紙URL分析 */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mb-6">
        <h2 className="font-semibold text-white mb-4">表紙URLを分析</h2>
        <p className="text-xs text-gray-500 mb-3">
          ※ Amazon Creators API経由で取得した表紙画像URLを入力してください（直接スクレイピング禁止）
        </p>
        <div className="flex gap-3">
          <input
            type="url"
            value={imageUrl}
            onChange={(e) => setImageUrl(e.target.value)}
            placeholder="https://m.media-amazon.com/images/..."
            className="flex-1 bg-gray-800 border border-gray-700 rounded-xl px-4 py-2 text-white placeholder-gray-500 text-sm focus:outline-none focus:border-blue-500"
          />
          <button
            onClick={analyzeUrl}
            disabled={loading}
            className="flex items-center gap-2 bg-orange-600 hover:bg-orange-500 disabled:opacity-50 text-white px-5 py-2 rounded-xl text-sm font-medium transition-colors"
          >
            <Image className="w-4 h-4" />
            {loading ? "分析中..." : "Claude Visionで分析"}
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-900/30 border border-red-700 rounded-xl p-4 mb-5 text-red-300 text-sm">
          {error}
        </div>
      )}

      {analyzeResult && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mb-6">
          <h3 className="font-semibold text-white mb-5">分析結果</h3>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-5">
            <div className="text-center bg-gray-800 rounded-xl p-4">
              <p className="text-gray-400 text-xs mb-1">CTRスコア</p>
              <p className={`text-3xl font-bold ${scoreColor(analyzeResult.ctr_score)}`}>
                {analyzeResult.ctr_score}
              </p>
            </div>
            <div className="text-center bg-gray-800 rounded-xl p-4">
              <p className="text-gray-400 text-xs mb-1">フォント</p>
              <p className="text-sm font-medium text-white">{analyzeResult.font_style}</p>
            </div>
            <div className="text-center bg-gray-800 rounded-xl p-4">
              <p className="text-gray-400 text-xs mb-1">レイアウト</p>
              <p className="text-sm font-medium text-white">
                {LAYOUT_LABELS[analyzeResult.layout] ?? analyzeResult.layout}
              </p>
            </div>
            <div className="text-center bg-gray-800 rounded-xl p-4">
              <p className="text-gray-400 text-xs mb-1">印象</p>
              <p className="text-sm font-medium text-white">
                {MOOD_LABELS[analyzeResult.mood] ?? analyzeResult.mood}
              </p>
            </div>
          </div>

          {/* カラーパレット */}
          {analyzeResult.primary_colors.length > 0 && (
            <div className="mb-5">
              <p className="text-gray-400 text-xs mb-2">主要カラー</p>
              <div className="flex gap-2">
                {analyzeResult.primary_colors.map((color) => (
                  <div key={color} className="flex items-center gap-1">
                    <div
                      className="w-6 h-6 rounded border border-gray-600"
                      style={{ backgroundColor: color }}
                    />
                    <span className="text-xs text-gray-400">{color}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <p className="text-sm text-gray-300 bg-gray-800 rounded-lg p-3">
            {analyzeResult.analysis_text}
          </p>
        </div>
      )}

      {/* 傾向ガイド */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <h3 className="font-semibold text-white mb-4">ジャンル別 表紙傾向ガイド</h3>
        <div className="space-y-3">
          {[
            { genre: "ビジネス・経済", colors: ["#1A1A2E", "#0F3460", "#FFFFFF"], mood: "professional", tip: "ネイビー系・白抜き文字・明朝体が定番" },
            { genre: "自己啓発", colors: ["#F5A623", "#FF6B35", "#FFFFFF"], mood: "dramatic", tip: "オレンジ・赤系。「変化」「成長」を視覚的に表現" },
            { genre: "コンピュータ・IT", colors: ["#00D4AA", "#1E1E2E", "#4A90D9"], mood: "academic", tip: "ダーク背景・技術的な図解・ゴシック体" },
            { genre: "マンガ", colors: ["#FF4757", "#2ED573", "#FFD700"], mood: "casual", tip: "明るい色・キャラクター中心・漫符使用" },
          ].map((item) => (
            <div key={item.genre} className="flex items-start gap-4 bg-gray-800 rounded-xl p-4">
              <div className="flex gap-1 shrink-0">
                {item.colors.map((c) => (
                  <div key={c} className="w-4 h-4 rounded" style={{ backgroundColor: c }} />
                ))}
              </div>
              <div>
                <p className="text-sm font-medium text-white">{item.genre}</p>
                <p className="text-xs text-gray-400 mt-1">{item.tip}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
