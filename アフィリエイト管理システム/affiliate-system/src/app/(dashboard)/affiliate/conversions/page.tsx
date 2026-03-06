"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { toast } from "sonner"

interface Conversion {
  id: string; type: string; amount: number
  status: string; createdAt: string; orderId: string | null
  partner: { name: string; code: string } | null
  lp: { name: string } | null
}

const TYPE_LABEL: Record<string, string> = {
  LINE_OPTIN:        "LINE登録",
  EMAIL_OPTIN:       "メール登録",
  FRONTEND_PURCHASE: "購入（フロント）",
  BACKEND_PURCHASE:  "購入（バック）",
}
const STATUS_COLORS: Record<string, string> = {
  PENDING:  "bg-yellow-100 text-yellow-800",
  APPROVED: "bg-green-100 text-green-800",
  REJECTED: "bg-red-100 text-red-800",
  PAID:     "bg-blue-100 text-blue-800",
}

export default function AdminConversionsPage() {
  const [conversions, setConversions] = useState<Conversion[]>([])
  const [filter, setFilter] = useState("ALL")
  const [loading, setLoading] = useState(true)

  const load = (status = filter) => {
    setLoading(true)
    const url = `/api/affiliate/conversions${status !== "ALL" ? `?status=${status}` : ""}`
    fetch(url)
      .then(r => r.json())
      .then(d => setConversions(d.conversions ?? []))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [filter])

  const approve = async (id: string) => {
    const res = await fetch(`/api/affiliate/conversions/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: "APPROVED" }),
    })
    if ((await res.json()).success) {
      toast.success("承認しました")
      load()
    }
  }

  const reject = async (id: string) => {
    const res = await fetch(`/api/affiliate/conversions/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: "REJECTED" }),
    })
    if ((await res.json()).success) {
      toast.success("却下しました")
      load()
    }
  }

  const totalAmount = conversions.reduce((s, c) => s + c.amount, 0)

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">成約一覧</h1>
        <Select value={filter} onValueChange={v => setFilter(v)}>
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="ALL">すべて</SelectItem>
            <SelectItem value="PENDING">承認待ち</SelectItem>
            <SelectItem value="APPROVED">承認済み</SelectItem>
            <SelectItem value="REJECTED">却下</SelectItem>
            <SelectItem value="PAID">支払済み</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <Card><CardContent className="pt-6">
          <div className="text-xs text-gray-400 mb-1">総件数</div>
          <div className="text-2xl font-bold">{conversions.length}</div>
        </CardContent></Card>
        <Card><CardContent className="pt-6">
          <div className="text-xs text-gray-400 mb-1">承認待ち</div>
          <div className="text-2xl font-bold text-yellow-600">
            {conversions.filter(c => c.status === "PENDING").length}
          </div>
        </CardContent></Card>
        <Card><CardContent className="pt-6">
          <div className="text-xs text-gray-400 mb-1">LINE登録</div>
          <div className="text-2xl font-bold text-green-600">
            {conversions.filter(c => c.type === "LINE_OPTIN").length}
          </div>
        </CardContent></Card>
        <Card><CardContent className="pt-6">
          <div className="text-xs text-gray-400 mb-1">総売上金額</div>
          <div className="text-2xl font-bold">¥{totalAmount.toLocaleString()}</div>
        </CardContent></Card>
      </div>

      <Card>
        <CardHeader><CardTitle>成約一覧</CardTitle></CardHeader>
        <CardContent>
          {loading ? (
            <div className="py-8 text-center text-gray-400">読み込み中...</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left">
                    {["日時", "パートナー", "種別", "LP", "金額", "状態", "操作"].map(h => (
                      <th key={h} className="pb-2 pr-4 font-medium text-gray-500">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {conversions.map(c => (
                    <tr key={c.id} className="border-b last:border-0 hover:bg-gray-50">
                      <td className="py-3 pr-4 text-xs text-gray-400">
                        {new Date(c.createdAt).toLocaleDateString("ja-JP", {
                          month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit",
                        })}
                      </td>
                      <td className="py-3 pr-4">
                        <div className="font-medium">{c.partner?.name ?? "—"}</div>
                        <div className="text-xs text-gray-400 font-mono">{c.partner?.code}</div>
                      </td>
                      <td className="py-3 pr-4">
                        <Badge variant="outline">{TYPE_LABEL[c.type] ?? c.type}</Badge>
                      </td>
                      <td className="py-3 pr-4 text-gray-600">{c.lp?.name ?? "—"}</td>
                      <td className="py-3 pr-4 font-semibold">
                        {c.amount > 0 ? `¥${c.amount.toLocaleString()}` : "—"}
                      </td>
                      <td className="py-3 pr-4">
                        <Badge className={STATUS_COLORS[c.status] ?? ""}>{c.status}</Badge>
                      </td>
                      <td className="py-3 pr-4">
                        {c.status === "PENDING" && (
                          <div className="flex gap-1">
                            <Button size="sm" variant="outline" className="text-green-600 border-green-300 h-7 text-xs" onClick={() => approve(c.id)}>承認</Button>
                            <Button size="sm" variant="outline" className="text-red-500 border-red-300 h-7 text-xs" onClick={() => reject(c.id)}>却下</Button>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                  {conversions.length === 0 && (
                    <tr><td colSpan={7} className="py-10 text-center text-gray-400">成約データがありません</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
