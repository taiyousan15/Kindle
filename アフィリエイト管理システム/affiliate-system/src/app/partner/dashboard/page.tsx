"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { MousePointerClick, TrendingUp, Wallet, Star } from "lucide-react"
import Link from "next/link"

interface DashboardData {
  partner: {
    name: string; code: string; rank: string; rankLabel: string
    commissionRate: number; status: string
  }
  stats: {
    totalClicks: number; totalConversions: number
    totalLineOptins: number; totalEmailOptins: number
    optinRate: string; pendingAmount: number; paidAmount: number
  }
  nextRank: { nextRank: string | null; needed: number }
  onboarding: {
    profileComplete: boolean; channelSelected: boolean
    firstLinkCopied: boolean; firstConversion: boolean
    completionScore: number
  } | null
}

const RANK_COLORS: Record<string, string> = {
  VIP: "bg-purple-100 text-purple-800",
  PLATINUM: "bg-blue-100 text-blue-800",
  GOLD: "bg-yellow-100 text-yellow-800",
  SILVER: "bg-gray-100 text-gray-800",
  STANDARD: "bg-white text-gray-600 border",
}

export default function PartnerDashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null)

  useEffect(() => {
    fetch("/api/partner/dashboard").then(r => r.json()).then(setData)
  }, [])

  if (!data) {
    return <div className="p-6 text-gray-400">読み込み中...</div>
  }

  const { partner, stats, nextRank, onboarding } = data

  return (
    <div className="p-6 space-y-6 max-w-4xl">
      {/* ヘッダー */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{partner.name} さん</h1>
          <p className="text-gray-400 text-sm mt-1">パートナーコード: <span className="font-mono">{partner.code}</span></p>
        </div>
        <Badge className={RANK_COLORS[partner.rank] ?? ""}>
          <Star className="h-3 w-3 mr-1" />{partner.rankLabel} ({partner.commissionRate}%)
        </Badge>
      </div>

      {/* オンボーディング進捗 */}
      {onboarding && onboarding.completionScore < 4 && (
        <Card className="border-blue-200 bg-blue-50">
          <CardHeader><CardTitle className="text-blue-700 text-base">はじめてのステップ</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-2">
              <Step done={onboarding.profileComplete} label="プロフィールを完成させる" />
              <Step done={onboarding.channelSelected} label="紹介チャンネルを選択する" />
              <Step done={onboarding.firstLinkCopied} label="アフィリエイトリンクをコピーする" />
              <Step done={onboarding.firstConversion} label="最初のコンバージョンを達成する" />
            </div>
          </CardContent>
        </Card>
      )}

      {/* KPI */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard icon={<MousePointerClick className="h-5 w-5" />} label="クリック数" value={stats.totalClicks.toLocaleString()} />
        <KpiCard icon={<TrendingUp className="h-5 w-5 text-green-500" />} label="LINE登録数" value={stats.totalLineOptins.toLocaleString()} />
        <KpiCard icon={<TrendingUp className="h-5 w-5 text-blue-500" />} label="メール登録数" value={stats.totalEmailOptins.toLocaleString()} />
        <KpiCard icon={<TrendingUp className="h-5 w-5 text-purple-500" />} label="オプトイン率" value={`${stats.optinRate}%`} />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-xs text-gray-400 mb-1">未払い報酬</div>
            <div className="text-2xl font-bold text-orange-500">¥{stats.pendingAmount.toLocaleString()}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-xs text-gray-400 mb-1">累計受取済み</div>
            <div className="text-2xl font-bold text-green-600">¥{stats.paidAmount.toLocaleString()}</div>
          </CardContent>
        </Card>
      </div>

      {/* 次のランク */}
      {nextRank.nextRank && (
        <Card className="border-yellow-200 bg-yellow-50">
          <CardContent className="pt-6 text-sm text-yellow-800">
            次のランクまであと <span className="font-bold">{nextRank.needed}件</span> の成約で
            <span className="font-bold"> {nextRank.nextRank}</span> に昇格します
          </CardContent>
        </Card>
      )}

      {/* ナビ */}
      <div className="flex gap-3">
        <Button asChild><Link href="/partner/links">リンク・QRコード管理</Link></Button>
        <Button asChild variant="outline"><Link href="/partner/conversions">成約履歴</Link></Button>
        <Button asChild variant="outline"><Link href="/partner/profile">プロフィール</Link></Button>
      </div>
    </div>
  )
}

function KpiCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center gap-2 text-gray-400 mb-1">{icon}<span className="text-xs">{label}</span></div>
        <div className="text-xl font-bold">{value}</div>
      </CardContent>
    </Card>
  )
}

function Step({ done, label }: { done: boolean; label: string }) {
  return (
    <div className={`flex items-center gap-2 text-sm ${done ? "line-through text-gray-400" : "text-blue-800"}`}>
      <span>{done ? "✅" : "⬜"}</span>{label}
    </div>
  )
}
