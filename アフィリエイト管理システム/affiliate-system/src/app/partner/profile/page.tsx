"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { toast } from "sonner"

interface Profile {
  name: string
  email: string
  channel: string
  bankName: string
  bankBranch: string
  bankAccount: string
  bankHolder: string
}

const CHANNELS = ["SNS（Instagram）", "SNS（Twitter/X）", "SNS（Facebook）", "LINE", "ブログ", "YouTube", "広告", "Kindle", "その他"]

export default function PartnerProfilePage() {
  const [form, setForm] = useState<Profile>({
    name: "", email: "", channel: "",
    bankName: "", bankBranch: "", bankAccount: "", bankHolder: "",
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    fetch("/api/partner/profile")
      .then(r => r.json())
      .then(d => { if (d.profile) setForm(d.profile) })
      .finally(() => setLoading(false))
  }, [])

  const save = async () => {
    setSaving(true)
    try {
      const res = await fetch("/api/partner/profile", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      })
      const data = await res.json()
      if (data.success) {
        toast.success("プロフィールを更新しました")
      } else {
        toast.error(data.error ?? "更新に失敗しました")
      }
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="p-6 text-gray-400">読み込み中...</div>

  const f = (key: keyof Profile) => ({
    value: form[key],
    onChange: (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [key]: e.target.value }),
  })

  return (
    <div className="p-6 space-y-6 max-w-2xl">
      <h1 className="text-2xl font-bold">プロフィール設定</h1>

      <Card>
        <CardHeader><CardTitle className="text-base">基本情報</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <div>
            <label className="text-sm font-medium">お名前</label>
            <Input {...f("name")} />
          </div>
          <div>
            <label className="text-sm font-medium">メールアドレス</label>
            <Input {...f("email")} type="email" disabled className="bg-gray-50" />
          </div>
          <div>
            <label className="text-sm font-medium">主な紹介チャンネル</label>
            <Select value={form.channel} onValueChange={v => setForm({ ...form, channel: v })}>
              <SelectTrigger><SelectValue placeholder="チャンネルを選択" /></SelectTrigger>
              <SelectContent>
                {CHANNELS.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle className="text-base">振込先口座</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-sm font-medium">銀行名</label>
              <Input placeholder="○○銀行" {...f("bankName")} />
            </div>
            <div>
              <label className="text-sm font-medium">支店名</label>
              <Input placeholder="本店" {...f("bankBranch")} />
            </div>
          </div>
          <div>
            <label className="text-sm font-medium">口座番号</label>
            <Input placeholder="1234567" {...f("bankAccount")} />
          </div>
          <div>
            <label className="text-sm font-medium">口座名義（カタカナ）</label>
            <Input placeholder="ヤマダ タロウ" {...f("bankHolder")} />
          </div>
        </CardContent>
      </Card>

      <Button className="w-full" onClick={save} disabled={saving}>
        {saving ? "保存中..." : "変更を保存"}
      </Button>
    </div>
  )
}
