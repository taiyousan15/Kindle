"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { toast } from "sonner"

interface PayoutRequest {
  id: string
  partnerId: string
  partnerName: string
  partnerCode: string
  bankInfo: string
  pendingAmount: number
  commissionIds: string[]
}

interface Payout {
  id: string; amount: number; status: string; createdAt: string; paidAt: string | null
  partner: { name: string; code: string } | null
}

export default function AdminPayoutsPage() {
  const [requests, setRequests] = useState<PayoutRequest[]>([])
  const [payouts, setPayouts] = useState<Payout[]>([])
  const [paying, setPaying] = useState<string | null>(null)

  const load = () => {
    fetch("/api/affiliate/payouts").then(r => r.json()).then(d => {
      setRequests(d.requests ?? [])
      setPayouts(d.payouts ?? [])
    })
  }

  useEffect(() => { load() }, [])

  const markPaid = async (partnerId: string, commissionIds: string[], amount: number) => {
    setPaying(partnerId)
    try {
      const res = await fetch("/api/affiliate/payouts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ partnerId, commissionIds, amount }),
      })
      const data = await res.json()
      if (data.success) {
        toast.success("支払い済みにしました")
        load()
      } else {
        toast.error(data.error ?? "エラーが発生しました")
      }
    } finally {
      setPaying(null)
    }
  }

  const STATUS_COLORS: Record<string, string> = {
    PENDING:    "bg-yellow-100 text-yellow-800",
    PROCESSING: "bg-blue-100 text-blue-800",
    COMPLETED:  "bg-green-100 text-green-800",
    FAILED:     "bg-red-100 text-red-800",
  }

  const totalPending = requests.reduce((s, r) => s + r.pendingAmount, 0)

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">報酬支払い管理</h1>

      <div className="grid grid-cols-3 gap-4">
        <Card><CardContent className="pt-6">
          <div className="text-xs text-gray-400 mb-1">支払い待ちパートナー数</div>
          <div className="text-2xl font-bold">{requests.length}</div>
        </CardContent></Card>
        <Card><CardContent className="pt-6">
          <div className="text-xs text-gray-400 mb-1">未払い総額</div>
          <div className="text-2xl font-bold text-orange-500">¥{totalPending.toLocaleString()}</div>
        </CardContent></Card>
        <Card><CardContent className="pt-6">
          <div className="text-xs text-gray-400 mb-1">支払い履歴件数</div>
          <div className="text-2xl font-bold text-green-600">{payouts.length}</div>
        </CardContent></Card>
      </div>

      {/* 未払い一覧 */}
      <Card>
        <CardHeader><CardTitle>未払い報酬一覧</CardTitle></CardHeader>
        <CardContent>
          {requests.length === 0 ? (
            <div className="py-8 text-center text-gray-400">未払い報酬はありません</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left">
                    {["パートナー", "コード", "振込先", "未払い金額", "操作"].map(h => (
                      <th key={h} className="pb-2 pr-4 font-medium text-gray-500">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {requests.map(r => (
                    <tr key={r.partnerId} className="border-b last:border-0 hover:bg-gray-50">
                      <td className="py-3 pr-4 font-medium">{r.partnerName}</td>
                      <td className="py-3 pr-4 font-mono text-xs">{r.partnerCode}</td>
                      <td className="py-3 pr-4 text-xs text-gray-500">{r.bankInfo || "未登録"}</td>
                      <td className="py-3 pr-4 font-bold text-orange-600">
                        ¥{r.pendingAmount.toLocaleString()}
                      </td>
                      <td className="py-3 pr-4">
                        <Button
                          size="sm"
                          disabled={paying === r.partnerId}
                          onClick={() => markPaid(r.partnerId, r.commissionIds, r.pendingAmount)}
                        >
                          {paying === r.partnerId ? "処理中..." : "支払済みにする"}
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 支払い履歴 */}
      <Card>
        <CardHeader><CardTitle>支払い履歴</CardTitle></CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left">
                  {["日時", "パートナー", "金額", "状態", "支払日"].map(h => (
                    <th key={h} className="pb-2 pr-4 font-medium text-gray-500">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {payouts.map(p => (
                  <tr key={p.id} className="border-b last:border-0 hover:bg-gray-50">
                    <td className="py-3 pr-4 text-xs text-gray-400">
                      {new Date(p.createdAt).toLocaleDateString("ja-JP")}
                    </td>
                    <td className="py-3 pr-4">
                      <div className="font-medium">{p.partner?.name ?? "—"}</div>
                      <div className="text-xs font-mono text-gray-400">{p.partner?.code}</div>
                    </td>
                    <td className="py-3 pr-4 font-semibold">¥{p.amount.toLocaleString()}</td>
                    <td className="py-3 pr-4">
                      <Badge className={STATUS_COLORS[p.status] ?? ""}>{p.status}</Badge>
                    </td>
                    <td className="py-3 pr-4 text-xs text-gray-500">
                      {p.paidAt ? new Date(p.paidAt).toLocaleDateString("ja-JP") : "—"}
                    </td>
                  </tr>
                ))}
                {payouts.length === 0 && (
                  <tr><td colSpan={5} className="py-8 text-center text-gray-400">支払い履歴がありません</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
