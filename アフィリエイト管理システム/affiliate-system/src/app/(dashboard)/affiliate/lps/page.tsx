"use client"

import { useEffect, useState, useCallback } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { toast } from "sonner"
import { Pencil, Trash2 } from "lucide-react"
import Link from "next/link"

interface Lp {
  id: string; name: string; url: string; description?: string
  totalClicks: number; totalLineOptins: number; totalEmailOptins: number
  totalConversions: number; optinRate: string; isActive: boolean
}

export default function LpsPage() {
  const [lps, setLps] = useState<Lp[]>([])
  const [open, setOpen] = useState(false)
  const [editLp, setEditLp] = useState<Lp | null>(null)
  const [form, setForm] = useState({ name: "", url: "", description: "" })
  const [loading, setLoading] = useState(false)

  const load = useCallback(() => {
    fetch("/api/affiliate/lps").then(r => r.json()).then(d => setLps(d.lps ?? []))
  }, [])

  useEffect(() => { load() }, [load])

  const openCreate = () => { setEditLp(null); setForm({ name: "", url: "", description: "" }); setOpen(true) }
  const openEdit = (lp: Lp) => { setEditLp(lp); setForm({ name: lp.name, url: lp.url, description: lp.description ?? "" }); setOpen(true) }

  const handleSave = async () => {
    setLoading(true)
    try {
      const url = editLp ? `/api/affiliate/lps/${editLp.id}` : "/api/affiliate/lps"
      const method = editLp ? "PATCH" : "POST"
      const res = await fetch(url, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(form) })
      const data = await res.json()
      if (data.success) {
        toast.success(editLp ? "LPを更新しました" : "LPを登録しました")
        setOpen(false)
        load()
      } else {
        toast.error("操作に失敗しました")
      }
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (lp: Lp) => {
    if (!confirm(`「${lp.name}」を削除しますか？`)) return
    const res = await fetch(`/api/affiliate/lps/${lp.id}`, { method: "DELETE" })
    const data = await res.json()
    if (data.success) { toast.success("LPを削除しました"); load() }
    else toast.error("削除に失敗しました")
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">LP管理</h1>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button onClick={openCreate}>LPを追加</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>{editLp ? "LPを編集" : "新しいLPを登録"}</DialogTitle></DialogHeader>
            <div className="space-y-3 mt-2">
              <div>
                <label className="text-sm font-medium">LP名</label>
                <Input placeholder="例: LP-A 無料セミナー" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
              </div>
              <div>
                <label className="text-sm font-medium">URL</label>
                <Input placeholder="https://example.com/lp-a" value={form.url} onChange={e => setForm({ ...form, url: e.target.value })} />
              </div>
              <div>
                <label className="text-sm font-medium">説明（任意）</label>
                <Input placeholder="LPの説明" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} />
              </div>
              <Button className="w-full" onClick={handleSave} disabled={loading}>
                {loading ? "保存中..." : editLp ? "更新する" : "登録する"}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {lps.map(lp => (
          <Card key={lp.id} className="hover:shadow-md transition-shadow">
            <CardHeader>
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <CardTitle className="text-base">
                    <Link href={`/affiliate/lps/${lp.id}`} className="hover:underline text-blue-600">
                      {lp.name}
                    </Link>
                  </CardTitle>
                  <p className="text-xs text-gray-400 truncate mt-1">{lp.url}</p>
                </div>
                <div className="flex gap-1 shrink-0">
                  <Button size="sm" variant="ghost" className="h-7 w-7 p-0" onClick={() => openEdit(lp)}>
                    <Pencil className="h-3 w-3" />
                  </Button>
                  <Button size="sm" variant="ghost" className="h-7 w-7 p-0 text-red-500 hover:text-red-700" onClick={() => handleDelete(lp)}>
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <StatItem label="クリック数" value={lp.totalClicks.toLocaleString()} />
                <StatItem label="LINE登録" value={lp.totalLineOptins.toLocaleString()} color="text-green-600" />
                <StatItem label="メール登録" value={lp.totalEmailOptins.toLocaleString()} color="text-blue-600" />
                <StatItem label="オプトイン率" value={`${lp.optinRate}%`} color={Number(lp.optinRate) >= 10 ? "text-green-600" : "text-gray-600"} />
              </div>
              <div className="mt-3">
                <Button asChild variant="outline" size="sm" className="w-full">
                  <Link href={`/affiliate/lps/${lp.id}`}>紹介文テンプレート管理 →</Link>
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
        {lps.length === 0 && (
          <div className="col-span-3 text-center py-16 text-gray-400">LPがまだ登録されていません</div>
        )}
      </div>
    </div>
  )
}

function StatItem({ label, value, color = "text-gray-800" }: { label: string; value: string; color?: string }) {
  return (
    <div>
      <div className="text-xs text-gray-400">{label}</div>
      <div className={`font-semibold ${color}`}>{value}</div>
    </div>
  )
}
