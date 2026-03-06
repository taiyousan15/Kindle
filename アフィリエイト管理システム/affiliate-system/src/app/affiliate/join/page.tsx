"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { toast } from "sonner"
import { UserPlus } from "lucide-react"

export default function AffiliateJoinPage() {
  const [form, setForm] = useState({ name: "", email: "", channel: "" })
  const [loading, setLoading] = useState(false)
  const [done, setDone] = useState(false)

  const submit = async () => {
    if (!form.name || !form.email) { toast.error("名前とメールは必須です"); return }
    setLoading(true)
    try {
      const res = await fetch("/api/affiliate/join", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      })
      const data = await res.json()
      if (data.success) {
        setDone(true)
        toast.success("申し込みを受け付けました")
      } else {
        toast.error(data.error ?? "申し込みに失敗しました")
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-emerald-100 flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-green-100">
            <UserPlus className="h-6 w-6 text-green-600" />
          </div>
          <CardTitle className="text-xl">アフィリエイトパートナー登録</CardTitle>
          <p className="text-sm text-gray-500">登録後、メールでログインリンクをお送りします</p>
        </CardHeader>
        <CardContent>
          {done ? (
            <div className="text-center py-6 space-y-3">
              <div className="text-5xl">🎉</div>
              <p className="font-semibold text-lg">申し込みありがとうございます！</p>
              <p className="text-sm text-gray-500">
                審査完了後、<span className="font-mono">{form.email}</span> にログインリンクをお送りします。
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium">お名前 <span className="text-red-500">*</span></label>
                <Input
                  placeholder="山田 太郎"
                  value={form.name}
                  onChange={e => setForm({ ...form, name: e.target.value })}
                />
              </div>
              <div>
                <label className="text-sm font-medium">メールアドレス <span className="text-red-500">*</span></label>
                <Input
                  type="email"
                  placeholder="taro@example.com"
                  value={form.email}
                  onChange={e => setForm({ ...form, email: e.target.value })}
                />
              </div>
              <div>
                <label className="text-sm font-medium">主な紹介チャンネル（任意）</label>
                <Input
                  placeholder="例: Instagram / LINE / ブログ"
                  value={form.channel}
                  onChange={e => setForm({ ...form, channel: e.target.value })}
                />
              </div>
              <Button className="w-full bg-green-600 hover:bg-green-700" onClick={submit} disabled={loading}>
                {loading ? "送信中..." : "パートナー登録を申し込む"}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
