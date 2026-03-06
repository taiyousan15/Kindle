"use client";

import { useState } from "react";
import { BarChart3, AlertTriangle } from "lucide-react";

interface SalesEstimate {
  bsr: number;
  genre: string;
  daily_estimated: number;
  monthly_estimated: number;
  lower_bound: number;
  upper_bound: number;
  error_range_pct: number;
  note: string;
}

const GENRES = [
  "ビジネス・経済", "自己啓発", "コンピュータ・IT",
  "資格・検定", "語学", "健康・医学", "マンガ", "default",
];

export default function PredictionPage() {
  const [bsr, setBsr] = useState<string>("5000");
  const [genre, setGenre] = useState("ビジネス・経済");
  const [result, setResult] = useState<SalesEstimate | null>(null);
  const [loading, setLoading] = useState(false);

  const calculate = async () => {
    const bsrNum = parseInt(bsr, 10);
    if (!bsrNum || bsrNum < 1) return;

    setLoading(true);
    try {
      const res = await fetch(
        `/api/v1/prediction/bsr-to-sales?bsr=${bsrNum}&genre=${encodeURIComponent(genre)}`
      );
      if (res.ok) {
        setResult(await res.json());
      }
    } catch {
      // フォールバック: クライアントサイド計算
      setResult(clientSideEstimate(bsrNum, genre));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold text-white mb-6">📊 売上予測シミュレーター</h1>

      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mb-6">
        <div className="grid grid-cols-2 gap-4 mb-5">
          <div>
            <label className="block text-sm text-gray-400 mb-2">BSR（ベストセラーランキング）</label>
            <input
              type="number"
              value={bsr}
              onChange={(e) => setBsr(e.target.value)}
              min="1"
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-2">ジャンル</label>
            <select
              value={genre}
              onChange={(e) => setGenre(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500"
            >
              {GENRES.map((g) => (
                <option key={g} value={g}>{g}</option>
              ))}
            </select>
          </div>
        </div>

        <button
          onClick={calculate}
          disabled={loading}
          className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white py-3 rounded-xl font-medium transition-colors"
        >
          <BarChart3 className="w-4 h-4" />
          {loading ? "計算中..." : "推定販売数を計算"}
        </button>
      </div>

      {result && (
        <div className="space-y-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold text-white mb-5">
              BSR {result.bsr.toLocaleString()} の推定結果
            </h2>

            <div className="grid grid-cols-2 gap-6 mb-6">
              <div className="text-center bg-gray-800 rounded-xl p-5">
                <p className="text-gray-400 text-sm mb-1">推定月間販売数</p>
                <p className="text-4xl font-bold text-green-400">
                  {result.monthly_estimated}冊
                </p>
                <p className="text-gray-500 text-xs mt-2">
                  範囲: {result.lower_bound}〜{result.upper_bound}冊
                </p>
              </div>
              <div className="text-center bg-gray-800 rounded-xl p-5">
                <p className="text-gray-400 text-sm mb-1">推定日次販売数</p>
                <p className="text-4xl font-bold text-blue-400">
                  {result.daily_estimated}冊
                </p>
                <p className="text-gray-500 text-xs mt-2">±{result.error_range_pct}%誤差</p>
              </div>
            </div>

            {/* BSRクイックリファレンス */}
            <div className="space-y-2">
              <p className="text-xs font-semibold text-gray-400 mb-3">BSR参考値（{result.genre}ジャンル）</p>
              {[
                { bsr: 100, label: "超ベストセラー" },
                { bsr: 1000, label: "ベストセラー" },
                { bsr: 5000, label: "安定売上" },
                { bsr: 20000, label: "ニッチで稼働中" },
              ].map((ref) => {
                const est = clientSideEstimate(ref.bsr, genre);
                return (
                  <div key={ref.bsr} className="flex items-center justify-between text-sm">
                    <span className="text-gray-400">BSR {ref.bsr.toLocaleString()} ({ref.label})</span>
                    <span className="text-white font-medium">月{est.monthly_estimated}冊</span>
                  </div>
                );
              })}
            </div>

            <div className="mt-5 flex items-start gap-2 bg-yellow-900/20 border border-yellow-700/30 rounded-lg px-4 py-3">
              <AlertTriangle className="w-4 h-4 text-yellow-400 shrink-0 mt-0.5" />
              <p className="text-xs text-yellow-300">{result.note}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function clientSideEstimate(bsr: number, genre: string): SalesEstimate {
  const GENRE_COEFF: Record<string, number> = {
    "ビジネス・経済": 1.2, "自己啓発": 1.15, "コンピュータ・IT": 0.95,
    "マンガ": 1.3, default: 1.0,
  };
  const coeff = GENRE_COEFF[genre] ?? 1.0;

  let base = 0;
  if (bsr <= 100) base = 50 - bsr * 0.4;
  else if (bsr <= 1000) base = 10 - (bsr - 100) * 0.008;
  else if (bsr <= 10000) base = 2.8 - (bsr - 1000) * 0.0002;
  else if (bsr <= 100000) base = 0.95 - (bsr - 10000) * 0.000009;
  else base = Math.max(0.01, 0.15 - (bsr - 100000) * 0.0000001);

  const daily = Math.max(0, base * coeff);
  const monthly = Math.round(daily * 30);

  return {
    bsr,
    genre,
    daily_estimated: Math.round(daily * 10) / 10,
    monthly_estimated: monthly,
    lower_bound: Math.round(monthly * 0.8),
    upper_bound: Math.round(monthly * 1.2),
    error_range_pct: 20,
    note: "推定値（±20%誤差）/ 実測販売データ非公開のため",
  };
}
