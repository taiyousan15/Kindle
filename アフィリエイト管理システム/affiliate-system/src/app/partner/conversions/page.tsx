"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

interface Commission {
  id: string
  type: string
  commissionAmount: number
  status: string
  tier: string | null
  createdAt: string
  lpName: string | null
}

const TYPE_LABEL: Record<string, string> = {
  LINE_OPTIN: "LINE登録",
  EMAIL_OPTIN: "メール登録",
  FRONTEND_PURCHASE: "購入（フロント）",
  BACKEND_PURCHASE: "購入（バック）",
}

const STATUS_COLORS: Record<string, string> = {
  PENDING: "bg-yellow-100 text-yellow-800",
  APPROVED: "bg-green-100 text-green-800",
  CANCELLED: "bg-red-100 text-red-800",
}

export default function PartnerConversionsPage() {
  const [conversions, setConversions] = useState<Commission[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch("/api/partner/conversions")
      .then(r => r.json())
      .then(d => setConversions(d.conversions ?? []))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="p-6 text-gray-400">読み込み中...</div>

  const totalPending = conversions
    .filter(c => c.status === "PENDING")
    .reduce((s, c) => s + c.commissionAmount, 0)

  const totalApproved = conversions
    .filter(c => c.status === "APPROVED")
    .reduce((s, c) => s + c.commissionAmount, 0)

  return (
    <div className="p-6 space-y-6 max-w-4xl">
      <h1 className="text-2xl font-bold">報酬履歴</h1>

      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-xs text-gray-400 mb-1">総件数</div>
            <div className="text-2xl font-bold">{conversions.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-xs text-gray-400 mb-1">未払い報酬</div>
            <div className="text-2xl font-bold text-orange-500">¥{totalPending.toLocaleString()}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-xs text-gray-400 mb-1">確定済み報酬</div>
            <div className="text-2xl font-bold text-green-600">¥{totalApproved.toLocaleString()}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle>報酬一覧</CardTitle></CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left">
                  {["日時", "種別", "LP", "Tier", "報酬額", "状態"].map(h => (
                    <th key={h} className="pb-2 pr-4 font-medium text-gray-500">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {conversions.map(c => (
                  <tr key={c.id} className="border-b last:border-0 hover:bg-gray-50">
                    <td className="py-3 pr-4 text-gray-500 text-xs">
                      {new Date(c.createdAt).toLocaleDateString("ja-JP", {
                        year: "numeric", month: "2-digit", day: "2-digit",
                      })}
                    </td>
                    <td className="py-3 pr-4">
                      <Badge variant="outline">{TYPE_LABEL[c.type] ?? c.type}</Badge>
                    </td>
                    <td className="py-3 pr-4 text-gray-600">{c.lpName ?? "—"}</td>
                    <td className="py-3 pr-4 text-gray-500">{c.tier ? `Tier${c.tier}` : "—"}</td>
                    <td className="py-3 pr-4 font-semibold">¥{c.commissionAmount.toLocaleString()}</td>
                    <td className="py-3 pr-4">
                      <Badge className={STATUS_COLORS[c.status] ?? ""}>{c.status}</Badge>
                    </td>
                  </tr>
                ))}
                {conversions.length === 0 && (
                  <tr><td colSpan={6} className="py-10 text-center text-gray-400">報酬履歴がまだありません</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
