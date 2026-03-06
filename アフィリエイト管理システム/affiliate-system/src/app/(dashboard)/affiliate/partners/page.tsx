"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Search } from "lucide-react"
import Link from "next/link"

interface Partner {
  id: string; name: string; email: string; code: string
  rank: string; rankLabel: string; status: string
  totalConversions: number; pendingAmount: number
  _count: { conversions: number; links: number }
}

const STATUS_COLORS: Record<string, string> = {
  ACTIVE:    "bg-green-100 text-green-800",
  PENDING:   "bg-yellow-100 text-yellow-800",
  SUSPENDED: "bg-red-100 text-red-800",
}
const RANK_COLORS: Record<string, string> = {
  VIP:      "bg-purple-100 text-purple-800",
  PLATINUM: "bg-blue-100 text-blue-800",
  GOLD:     "bg-yellow-100 text-yellow-800",
  SILVER:   "bg-gray-100 text-gray-800",
  STANDARD: "bg-white text-gray-600 border",
}

export default function PartnersPage() {
  const [partners, setPartners] = useState<Partner[]>([])
  const [q, setQ] = useState("")
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    const url = `/api/affiliate/partners${q ? `?q=${encodeURIComponent(q)}` : ""}`
    fetch(url)
      .then(r => r.json())
      .then(d => setPartners(d.partners ?? []))
      .finally(() => setLoading(false))
  }, [q])

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">パートナー一覧</h1>
        <div className="relative w-64">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-gray-400" />
          <Input
            placeholder="名前・メール・コード"
            className="pl-8"
            value={q}
            onChange={e => setQ(e.target.value)}
          />
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-2">
        <Card>
          <CardContent className="pt-6">
            <div className="text-xs text-gray-400 mb-1">総パートナー数</div>
            <div className="text-2xl font-bold">{partners.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-xs text-gray-400 mb-1">アクティブ</div>
            <div className="text-2xl font-bold text-green-600">
              {partners.filter(p => p.status === "ACTIVE").length}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-xs text-gray-400 mb-1">審査待ち</div>
            <div className="text-2xl font-bold text-yellow-600">
              {partners.filter(p => p.status === "PENDING").length}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle>パートナー一覧</CardTitle></CardHeader>
        <CardContent>
          {loading ? (
            <div className="py-8 text-center text-gray-400">読み込み中...</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left">
                    {["パートナー", "コード", "ランク", "成約数", "未払い報酬", "リンク数", "状態", ""].map(h => (
                      <th key={h} className="pb-2 pr-4 font-medium text-gray-500">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {partners.map(p => (
                    <tr key={p.id} className="border-b last:border-0 hover:bg-gray-50">
                      <td className="py-3 pr-4">
                        <div className="font-medium">{p.name}</div>
                        <div className="text-gray-400 text-xs">{p.email}</div>
                      </td>
                      <td className="py-3 pr-4 font-mono text-xs">{p.code}</td>
                      <td className="py-3 pr-4">
                        <Badge className={RANK_COLORS[p.rank] ?? ""}>{p.rankLabel}</Badge>
                      </td>
                      <td className="py-3 pr-4">{p.totalConversions}</td>
                      <td className="py-3 pr-4">¥{p.pendingAmount.toLocaleString()}</td>
                      <td className="py-3 pr-4">{p._count.links}</td>
                      <td className="py-3 pr-4">
                        <Badge className={STATUS_COLORS[p.status] ?? ""}>{p.status}</Badge>
                      </td>
                      <td className="py-3">
                        <Button asChild variant="ghost" size="sm">
                          <Link href={`/affiliate/partners/${p.id}`}>詳細</Link>
                        </Button>
                      </td>
                    </tr>
                  ))}
                  {partners.length === 0 && (
                    <tr>
                      <td colSpan={8} className="py-10 text-center text-gray-400">
                        パートナーがいません
                      </td>
                    </tr>
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
