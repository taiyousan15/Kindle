import { NextRequest, NextResponse } from "next/server"
import { z } from "zod"
import { prisma } from "@/lib/db"
import { Resend } from "resend"
import { nanoid } from "nanoid"

const resend = new Resend(process.env.RESEND_API_KEY)
const schema = z.object({ email: z.string().email() })

export async function POST(req: NextRequest) {
  try {
    const { email } = schema.parse(await req.json())

    const partner = await prisma.partner.findFirst({
      where: { email, tenantId: "default", status: "ACTIVE" },
    })
    if (!partner) {
      return NextResponse.json({ success: false, message: "登録されていないメールアドレスです" }, { status: 404 })
    }

    const token = nanoid(32)
    const expiresAt = new Date(Date.now() + 1000 * 60 * 30) // 30分

    await prisma.partner.update({
      where: { id: partner.id },
      data: { partnerAccessToken: token, tokenExpiresAt: expiresAt },
    })

    const appUrl = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000"
    const link = `${appUrl}/api/partner/auth/verify?token=${token}`

    await resend.emails.send({
      from: process.env.RESEND_FROM_EMAIL ?? "noreply@example.com",
      to:   email,
      subject: "【アフィリエイト】ログインリンク",
      html: `
        <p>${partner.name} 様</p>
        <p>以下のリンクをクリックしてログインしてください（30分間有効）</p>
        <a href="${link}" style="display:inline-block;padding:12px 24px;background:#2563eb;color:white;border-radius:6px;text-decoration:none">ログインする</a>
        <p>このメールに心当たりがない場合は無視してください。</p>
      `,
    })

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error("magic-link error:", error)
    return NextResponse.json({ success: false }, { status: 500 })
  }
}
