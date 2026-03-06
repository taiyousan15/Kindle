"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { toast } from "sonner"
import { Copy, Download, QrCode, Plus } from "lucide-react"
import Image from "next/image"

interface Lp { id: string; name: string }
interface Template { id: string; title: string; body: string; medium?: string }
interface Link {
  id: string; linkCode: string; trackingUrl: string
  clicks: number; lineOptins: number; emailOptins: number; optinRate: string
  lp?: { id: string; name: string; templates: Template[] }
}

export default function PartnerLinksPage() {
  const [links, setLinks] = useState<Link[]>([])
  const [lps, setLps] = useState<Lp[]>([])
  const [selectedLp, setSelectedLp] = useState("")
  const [qrMap, setQrMap] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(false)

  const loadLinks = () => fetch("/api/partner/links").then(r => r.json()).then(d => setLinks(d.links ?? []))
  const loadLps   = () => fetch("/api/affiliate/lps").then(r => r.json()).then(d => setLps(d.lps ?? []))

  useEffect(() => { loadLinks(); loadLps() }, [])

  const generateLink = async () => {
    setLoading(true)
    try {
      const res = await fetch("/api/partner/links", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lpId: selectedLp && selectedLp !== "none" ? selectedLp : undefined }),
      })
      const data = await res.json()
      if (data.link) {
        toast.success("リンクを生成しました")
        setQrMap(prev => ({ ...prev, [data.link.id]: data.qrDataUrl }))
        loadLinks()
      }
    } finally {
      setLoading(false)
    }
  }

  const copy = (text: string, label = "コピーしました") => {
    navigator.clipboard.writeText(text)
    toast.success(label)
  }

  const downloadQr = (linkId: string, linkCode: string) => {
    const dataUrl = qrMap[linkId]
    if (!dataUrl) { toast.error("QRコードを再生成してください"); return }
    const a = document.createElement("a")
    a.href = dataUrl
    a.download = `qr_${linkCode}.png`
    a.click()
  }

  const showQr = async (link: Link) => {
    if (qrMap[link.id]) return
    const res = await fetch("/api/partner/links", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lpId: link.lp?.id }),
    })
    const data = await res.json()
    if (data.qrDataUrl) setQrMap(prev => ({ ...prev, [link.id]: data.qrDataUrl }))
  }

  return (
    <div className="p-6 space-y-6 max-w-4xl">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">リンク・QRコード管理</h1>
        <div className="flex items-center gap-2">
          <Select value={selectedLp} onValueChange={setSelectedLp}>
            <SelectTrigger className="w-48">
              <SelectValue placeholder="LPを選択（任意）" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">LP指定なし</SelectItem>
              {lps.map(lp => <SelectItem key={lp.id} value={lp.id}>{lp.name}</SelectItem>)}
            </SelectContent>
          </Select>
          <Button onClick={generateLink} disabled={loading}>
            <Plus className="h-4 w-4 mr-1" />{loading ? "生成中..." : "リンクを生成"}
          </Button>
        </div>
      </div>

      <div className="space-y-4">
        {links.map(link => (
          <Card key={link.id}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">
                  {link.lp ? link.lp.name : "LP指定なし"}
                </CardTitle>
                <div className="flex gap-2 text-sm text-gray-500">
                  <span>クリック: {link.clicks}</span>
                  <span>LINE: {link.lineOptins}</span>
                  <span>メール: {link.emailOptins}</span>
                  <span className="text-green-600 font-semibold">率: {link.optinRate}%</span>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {/* トラッキングURL */}
              <div className="flex items-center gap-2 bg-gray-50 p-2 rounded-md">
                <span className="text-xs text-gray-400 w-20 shrink-0">リンク</span>
                <span className="text-sm font-mono truncate flex-1">{link.trackingUrl}</span>
                <Button size="sm" variant="ghost" onClick={() => copy(link.trackingUrl)}>
                  <Copy className="h-4 w-4" />
                </Button>
              </div>

              {/* QRコード */}
              <div className="flex items-center gap-3">
                <Button size="sm" variant="outline" onClick={() => showQr(link)}>
                  <QrCode className="h-4 w-4 mr-1" />QRを表示
                </Button>
                {qrMap[link.id] && (
                  <>
                    <Image src={qrMap[link.id]} alt="QR" width={80} height={80} className="rounded border" />
                    <Button size="sm" variant="outline" onClick={() => downloadQr(link.id, link.linkCode)}>
                      <Download className="h-4 w-4 mr-1" />DL
                    </Button>
                  </>
                )}
              </div>

              {/* 紹介文テンプレート */}
              {link.lp && link.lp.templates.length > 0 && (
                <div>
                  <p className="text-xs text-gray-400 mb-2">紹介文テンプレート（クリックでコピー）</p>
                  <div className="space-y-2">
                    {link.lp.templates.map(t => (
                      <div
                        key={t.id}
                        className="border rounded-md p-3 cursor-pointer hover:bg-blue-50 transition-colors"
                        onClick={() => copy(`${t.body}\n\n${link.trackingUrl}`, "紹介文+リンクをコピーしました")}
                      >
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-medium">{t.title}</span>
                          {t.medium && <Badge variant="outline" className="text-xs">{t.medium}</Badge>}
                        </div>
                        <p className="text-sm text-gray-600 line-clamp-2">{t.body}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
        {links.length === 0 && (
          <div className="text-center py-16 text-gray-400">リンクがまだありません。上のボタンから生成してください。</div>
        )}
      </div>
    </div>
  )
}
