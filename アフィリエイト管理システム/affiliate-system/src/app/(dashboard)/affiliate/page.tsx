"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Users, TrendingUp, MousePointerClick, CreditCard, LayoutList, Search } from "lucide-react"
import Link from "next/link"

interface LpStat {
  id: string; name: string; url: string
  totalClicks: number; totalLineOptins: number; totalEmailOptins: number
  totalConversions: number; optinRate: string
}

interface Partner {
  id: string; name: string; email: string; code: string
  rank: string; rankLabel: string; status: string
  totalConversions: number; pendingAmount: number
  _count: { conversions: number; links: number }
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

export default function AffiliateDashboardPage() {
  const [lps, setLps] = useState<LpStat[]>([])
  const [partners, setPartners] = useState<Partner[]>([])
  const [q, setQ] = useState("")

  useEffect(() => {
    fetch("/api/affiliate/lps").then(r => r.json()).then(d => setLps(d.lps ?? []))
  }, [])

  useEffect(() => {
    const url = `/api/affiliate/partners?${q ? `q=${encodeURIComponent(q)}` : ""}`
    fetch(url).then(r => r.json()).then(d => setPartners(d.partners ?? []))
  }, [q])

  const totalClicks = lps.reduce((s, l) => s + l.totalClicks, 0)
  const totalLine   = lps.reduce((s, l) => s + l.totalLineOptins, 0)
  const totalEmail  = lps.reduce((s, l) => s + l.totalEmailOptins, 0)
  const avgOptin    = totalClicks > 0 ? (((totalLine + totalEmail) / totalClicks) * 100).toFixed(1) : "0.0"

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">アフィリエイト管理</h1>
        <div className="flex gap-2">
          <Button asChild variant="outline"><Link href="/affiliate/join">登録ページを見る</Link></Button>
          <Button asChild><Link href="/affiliate/lps">LP管理</Link></Button>
        </div>
      </div>

      {/* KPI カード */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard icon={<MousePointerClick className="h-5 w-5" />} label="総クリック数" value={totalClicks.toLocaleString()} />
        <KpiCard icon={<TrendingUp className="h-5 w-5 text-green-500" />} label="LINE登録数" value={totalLine.toLocaleString()} />
        <KpiCard icon={<TrendingUp className="h-5 w-5 text-blue-500" />} label="メール登録数" value={totalEmail.toLocaleString()} />
        <KpiCard icon={<LayoutList className="h-5 w-5 text-purple-500" />} label="平均オプトイン率" value={`${avgOptin}%`} />
      </div>

      <Tabs defaultValue="lps">
        <TabsList>
          <TabsTrigger value="lps">LP別成績</TabsTrigger>
          <TabsTrigger value="partners">パートナー一覧</TabsTrigger>
        </TabsList>

        <TabsContent value="lps" className="mt-4">
          <Card>
            <CardHeader><CardTitle>LP別トラッキング</CardTitle></CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left">
                      {["LP名", "クリック", "LINE登録", "メール登録", "オプトイン率"].map(h => (
                        <th key={h} className="pb-2 pr-4 font-medium text-gray-500">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {lps.map(lp => (
                      <tr key={lp.id} className="border-b last:border-0 hover:bg-gray-50">
                        <td className="py-3 pr-4 font-medium">
                          <Link href={`/affiliate/lps/${lp.id}`} className="hover:underline text-blue-600">{lp.name}</Link>
                        </td>
                        <td className="py-3 pr-4">{lp.totalClicks.toLocaleString()}</td>
                        <td className="py-3 pr-4 text-green-600 font-semibold">{lp.totalLineOptins.toLocaleString()}</td>
                        <td className="py-3 pr-4 text-blue-600 font-semibold">{lp.totalEmailOptins.toLocaleString()}</td>
                        <td className="py-3 pr-4">
                          <span className={`font-semibold ${Number(lp.optinRate) >= 10 ? "text-green-600" : "text-gray-600"}`}>
                            {lp.optinRate}%
                          </span>
                        </td>
                      </tr>
                    ))}
                    {lps.length === 0 && (
                      <tr><td colSpan={5} className="py-8 text-center text-gray-400">LPがまだ登録されていません</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="partners" className="mt-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>パートナー一覧</CardTitle>
                <div className="relative w-60">
                  <Search className="absolute left-2 top-2.5 h-4 w-4 text-gray-400" />
                  <Input placeholder="名前・メール・コード" className="pl-8" value={q} onChange={e => setQ(e.target.value)} />
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left">
                      {["パートナー", "コード", "ランク", "成約数", "未払い報酬", "状態"].map(h => (
                        <th key={h} className="pb-2 pr-4 font-medium text-gray-500">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {partners.map(p => (
                      <tr key={p.id} className="border-b last:border-0 hover:bg-gray-50">
                        <td className="py-3 pr-4">
                          <Link href={`/affiliate/partners/${p.id}`} className="hover:underline">
                            <div className="font-medium">{p.name}</div>
                            <div className="text-gray-400 text-xs">{p.email}</div>
                          </Link>
                        </td>
                        <td className="py-3 pr-4 font-mono text-xs">{p.code}</td>
                        <td className="py-3 pr-4">
                          <Badge className={RANK_COLORS[p.rank] ?? ""}>{p.rankLabel}</Badge>
                        </td>
                        <td className="py-3 pr-4">{p.totalConversions}</td>
                        <td className="py-3 pr-4">¥{p.pendingAmount.toLocaleString()}</td>
                        <td className="py-3 pr-4">
                          <Badge className={STATUS_COLORS[p.status] ?? ""}>{p.status}</Badge>
                        </td>
                      </tr>
                    ))}
                    {partners.length === 0 && (
                      <tr><td colSpan={6} className="py-8 text-center text-gray-400">パートナーがいません</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

function KpiCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center gap-2 text-gray-500 mb-1">{icon}<span className="text-xs">{label}</span></div>
        <div className="text-2xl font-bold">{value}</div>
      </CardContent>
    </Card>
  )
}
