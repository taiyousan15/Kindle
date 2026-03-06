"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { toast } from "sonner"
import { Mail } from "lucide-react"

export default function PartnerLoginPage() {
  const [email, setEmail] = useState("")
  const [loading, setLoading] = useState(false)
  const [sent, setSent] = useState(false)

  const sendMagicLink = async () => {
    if (!email) { toast.error("メールアドレスを入力してください"); return }
    setLoading(true)
    try {
      const res = await fetch("/api/partner/auth/magic-link", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      })
      const data = await res.json()
      if (data.success) {
        setSent(true)
        toast.success("ログインリンクを送信しました")
      } else {
        toast.error(data.error ?? "送信に失敗しました")
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-blue-100">
            <Mail className="h-6 w-6 text-blue-600" />
          </div>
          <CardTitle className="text-xl">パートナーログイン</CardTitle>
          <p className="text-sm text-gray-500">メールアドレスを入力するとログインリンクを送信します</p>
        </CardHeader>
        <CardContent>
          {sent ? (
            <div className="text-center py-4 space-y-3">
              <div className="text-4xl">📬</div>
              <p className="font-medium">ログインリンクを送信しました</p>
              <p className="text-sm text-gray-500">
                <span className="font-mono">{email}</span> に届いたメールのリンクをクリックしてください
              </p>
              <Button variant="ghost" className="text-sm" onClick={() => setSent(false)}>
                別のメールで試す
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              <div>
                <label className="text-sm font-medium">メールアドレス</label>
                <Input
                  type="email"
                  placeholder="partner@example.com"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  onKeyDown={e => e.key === "Enter" && sendMagicLink()}
                />
              </div>
              <Button className="w-full" onClick={sendMagicLink} disabled={loading}>
                {loading ? "送信中..." : "ログインリンクを送信"}
              </Button>
              <p className="text-center text-xs text-gray-400">
                まだ登録していない方は{" "}
                <a href="/affiliate/join" className="text-blue-600 hover:underline">こちらから申し込み</a>
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
