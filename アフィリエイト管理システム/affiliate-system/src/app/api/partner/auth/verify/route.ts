import { NextRequest, NextResponse } from "next/server"
import { prisma } from "@/lib/db"

export async function GET(req: NextRequest) {
  const token = new URL(req.url).searchParams.get("token")
  const appUrl = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000"

  if (!token) return NextResponse.redirect(`${appUrl}/partner/login?error=invalid`)

  const partner = await prisma.partner.findUnique({
    where: { partnerAccessToken: token },
  })

  if (!partner || !partner.tokenExpiresAt || partner.tokenExpiresAt < new Date()) {
    return NextResponse.redirect(`${appUrl}/partner/login?error=expired`)
  }

  await prisma.partner.update({
    where: { id: partner.id },
    data: { partnerAccessToken: null, tokenExpiresAt: null },
  })

  const res = NextResponse.redirect(`${appUrl}/partner/dashboard`)
  res.cookies.set("partner_id", partner.id, {
    httpOnly: true,
    secure:   process.env.NODE_ENV === "production",
    maxAge:   60 * 60 * 24 * 7,
    path:     "/",
  })
  return res
}
