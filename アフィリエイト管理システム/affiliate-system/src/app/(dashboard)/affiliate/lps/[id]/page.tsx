"use client"

import { useEffect, useState, useCallback } from "react"
import { use } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { toast } from "sonner"
import { Copy, Plus, Trash2, Pencil, ArrowLeft } from "lucide-react"
import Link from "next/link"

interface Template {
  id: string; title: string; body: string; medium?: string; sortOrder: number
}

const MEDIUMS = ["SNS", "LINE", "Kindle", "広告", "ブログ", "その他"]

export default function LpDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const [templates, setTemplates] = useState<Template[]>([])
  const [open, setOpen] = useState(false)
  const [editTemplate, setEditTemplate] = useState<Template | null>(null)
  const [form, setForm] = useState({ title: "", body: "", medium: "" })
  const [loading, setLoading] = useState(false)

  const load = useCallback(() => {
    fetch(`/api/affiliate/lps/${id}/templates`).then(r => r.json()).then(d => setTemplates(d.templates ?? []))
  }, [id])

  useEffect(() => { load() }, [load])

  const openCreate = () => { setEditTemplate(null); setForm({ title: "", body: "", medium: "" }); setOpen(true) }
  const openEdit = (t: Template) => { setEditTemplate(t); setForm({ title: t.title, body: t.body, medium: t.medium ?? "" }); setOpen(true) }

  const handleSave = async () => {
    setLoading(true)
    try {
      const url = editTemplate
        ? `/api/affiliate/lps/${id}/templates/${editTemplate.id}`
        : `/api/affiliate/lps/${id}/templates`
      const method = editTemplate ? "PATCH" : "POST"
      const res = await fetch(url, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(form) })
      const data = await res.json()
      if (data.success) {
        toast.success(editTemplate ? "テンプレートを更新しました" : "テンプレートを追加しました")
        setOpen(false)
        load()
      } else {
        toast.error("操作に失敗しました")
      }
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (t: Template) => {
    if (!confirm(`「${t.title}」を削除しますか？`)) return
    const res = await fetch(`/api/affiliate/lps/${id}/templates/${t.id}`, { method: "DELETE" })
    const data = await res.json()
    if (data.success) { toast.success("削除しました"); load() }
    else toast.error("削除に失敗しました")
  }

  const copy = (text: string) => { navigator.clipboard.writeText(text); toast.success("コピーしました") }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button asChild variant="ghost" size="sm">
            <Link href="/affiliate/lps"><ArrowLeft className="h-4 w-4 mr-1" />LP一覧</Link>
          </Button>
          <h1 className="text-2xl font-bold">紹介文テンプレート管理</h1>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button onClick={openCreate}><Plus className="h-4 w-4 mr-1" />テンプレートを追加</Button>
          </DialogTrigger>
          <DialogContent className="max-w-xl">
            <DialogHeader><DialogTitle>{editTemplate ? "テンプレートを編集" : "紹介文テンプレートを追加"}</DialogTitle></DialogHeader>
            <div className="space-y-3 mt-2">
              <div>
                <label className="text-sm font-medium">タイトル</label>
                <Input placeholder="例: SNS投稿用①" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} />
              </div>
              <div>
                <label className="text-sm font-medium">媒体</label>
                <Select value={form.medium || "none"} onValueChange={v => setForm({ ...form, medium: v === "none" ? "" : v })}>
                  <SelectTrigger><SelectValue placeholder="媒体を選択" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">指定なし</SelectItem>
                    {MEDIUMS.map(m => <SelectItem key={m} value={m}>{m}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-sm font-medium">紹介文</label>
                <textarea
                  className="w-full border rounded-md p-2 text-sm h-32 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="紹介文を入力してください..."
                  value={form.body}
                  onChange={e => setForm({ ...form, body: e.target.value })}
                />
              </div>
              <Button className="w-full" onClick={handleSave} disabled={loading}>
                {loading ? "保存中..." : editTemplate ? "更新する" : "追加する"}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <div className="space-y-4">
        {templates.map(t => (
          <Card key={t.id}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">{t.title}</CardTitle>
                <div className="flex items-center gap-2">
                  {t.medium && <Badge variant="outline">{t.medium}</Badge>}
                  <Button size="sm" variant="ghost" onClick={() => copy(t.body)}>
                    <Copy className="h-4 w-4" />
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => openEdit(t)}>
                    <Pencil className="h-4 w-4" />
                  </Button>
                  <Button size="sm" variant="ghost" className="text-red-500 hover:text-red-700" onClick={() => handleDelete(t)}>
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <pre className="text-sm bg-gray-50 p-3 rounded-md whitespace-pre-wrap font-sans leading-relaxed">
                {t.body}
              </pre>
            </CardContent>
          </Card>
        ))}
        {templates.length === 0 && (
          <div className="text-center py-16 text-gray-400">テンプレートがまだありません</div>
        )}
      </div>
    </div>
  )
}
