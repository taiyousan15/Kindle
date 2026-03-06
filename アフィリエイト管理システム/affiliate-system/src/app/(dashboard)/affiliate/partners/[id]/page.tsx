"use client"

import { useEffect, useState } from "react"
import { use } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { toast } from "sonner"
import { ArrowLeft } from "lucide-react"
import Link from "next/link"

interface PartnerDetail {
  id: string; name: string; email: string; code: string
  rank: string; rankLabel: string; commissionRate: number; status: string
  channel: string | null; bankName: string | null; bankBranch: string | null
  bankAccount: string | null; bankHolder: string | null
  totalConversions: number; pendingAmount: number; paidAmount: number
  conversions: {
    id: string; type: string; amount: number; commissionAmount: number
    status: string; createdAt: string; lp?: { name: string } | null
  }[]
}

const STATUS_COLORS: Record<string, string> = {
  ACTIVE: "bg-green-100 text-green-800",
  PENDING: "bg-yellow-100 text-yellow-800",
  SUSPENDED: "bg-red-100 text-red-800",
}
const RANK_COLORS: Record<string, string> = {
  VIP: "bg-purple-100 text-purple-800",
  PLATINUM: "bg-blue-100 text-blue-800",
  GOLD: "bg-yellow-100 text-yellow-800",
  SILVER: "bg-gray-100 text-gray-800",
  STANDARD: "bg-white text-gray-600 border",
}
const TYPE_LABEL: Record<string, string> = {
  LINE_OPTIN: "LINE登録", EMAIL_OPTIN: "メール登録", PURCHASE: "購入", TIER2: "Tier2",
}
const CONV_STATUS_COLORS: Record<string, string> = {
  PENDING: "bg-yellow-100 text-yellow-800",
  APPROVED: "bg-green-100 text-green-800",
  PAID: "bg-blue-100 text-blue-800",
  REJECTED: "bg-red-100 text-red-800",
}

export default function PartnerDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const [partner, setPartner] = useState<PartnerDetail | null>(null)
  const [statusLoading, setStatusLoading] = useState(false)

  useEffect(() => {
    fetch(`/api/affiliate/partners/${id}`)
      .then(r => r.json())
      .then(d => { if (d.partner) setPartner(d.partner) })
  }, [id])

  const updateStatus = async (status: string) => {
    if (!partner) return
    setStatusLoading(true)
    try {
      const res = await fetch(`/api/affiliate/partners/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      })
      const data = await res.json()
      if (data.success) {
        setPartner({ ...partner, status })
        toast.success("ステータスを更新しました")
      }
    } finally {
      setStatusLoading(false)
    }
  }

  if (!partner) return <div className="p-6 text-gray-400">読み込み中...</div>

  return (
    <div className="p-6 space-y-6 max-w-4xl">
      <div className="flex items-center gap-3">
        <Button asChild variant="ghost" size="sm">
          <Link href="/affiliate/partners"><ArrowLeft className="h-4 w-4 mr-1" />戻る</Link>
        </Button>
        <h1 className="text-2xl font-bold">{partner.name}</h1>
        <Badge className={STATUS_COLORS[partner.status] ?? ""}>{partner.status}</Badge>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Card>
          <CardHeader><CardTitle className="text-base">基本情報</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            <Row label="メール" value={partner.email} />
            <Row label="コード" value={<span className="font-mono">{partner.code}</span>} />
            <Row label="ランク" value={<Badge className={RANK_COLORS[partner.rank] ?? ""}>{partner.rankLabel}</Badge>} />
            <Row label="報酬率" value={`${partner.commissionRate}%`} />
            <Row label="チャンネル" value={partner.channel ?? "—"} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="text-base">振込先口座</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            <Row label="銀行" value={partner.bankName ?? "未登録"} />
            <Row label="支店" value={partner.bankBranch ?? "—"} />
            <Row label="口座番号" value={partner.bankAccount ?? "—"} />
            <Row label="口座名義" value={partner.bankHolder ?? "—"} />
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-xs text-gray-400 mb-1">総成約数</div>
            <div className="text-2xl font-bold">{partner.totalConversions}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-xs text-gray-400 mb-1">未払い報酬</div>
            <div className="text-2xl font-bold text-orange-500">¥{partner.pendingAmount.toLocaleString()}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-xs text-gray-400 mb-1">累計支払済み</div>
            <div className="text-2xl font-bold text-green-600">¥{partner.paidAmount.toLocaleString()}</div>
          </CardContent>
        </Card>
      </div>

      {/* ステータス変更 */}
      <Card>
        <CardHeader><CardTitle className="text-base">ステータス管理</CardTitle></CardHeader>
        <CardContent className="flex gap-2">
          {["ACTIVE", "PENDING", "SUSPENDED"].map(s => (
            <Button
              key={s}
              variant={partner.status === s ? "default" : "outline"}
              size="sm"
              disabled={statusLoading || partner.status === s}
              onClick={() => updateStatus(s)}
            >
              {s}
            </Button>
          ))}
        </CardContent>
      </Card>

      {/* 成約履歴 */}
      <Card>
        <CardHeader><CardTitle className="text-base">成約履歴</CardTitle></CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left">
                  {["日時", "種別", "LP", "報酬額", "状態"].map(h => (
                    <th key={h} className="pb-2 pr-4 font-medium text-gray-500">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {partner.conversions.map(c => (
                  <tr key={c.id} className="border-b last:border-0 hover:bg-gray-50">
                    <td className="py-2 pr-4 text-xs text-gray-400">
                      {new Date(c.createdAt).toLocaleDateString("ja-JP")}
                    </td>
                    <td className="py-2 pr-4">
                      <Badge variant="outline">{TYPE_LABEL[c.type] ?? c.type}</Badge>
                    </td>
                    <td className="py-2 pr-4 text-gray-600">{c.lp?.name ?? "—"}</td>
                    <td className="py-2 pr-4 font-semibold">¥{c.commissionAmount.toLocaleString()}</td>
                    <td className="py-2 pr-4">
                      <Badge className={CONV_STATUS_COLORS[c.status] ?? ""}>{c.status}</Badge>
                    </td>
                  </tr>
                ))}
                {partner.conversions.length === 0 && (
                  <tr><td colSpan={5} className="py-8 text-center text-gray-400">成約履歴なし</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between items-center">
      <span className="text-gray-500">{label}</span>
      <span>{value}</span>
    </div>
  )
}
