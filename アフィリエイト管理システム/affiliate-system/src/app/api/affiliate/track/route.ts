import { NextRequest, NextResponse } from "next/server"
import { recordClick } from "@/lib/affiliate/service"

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url)
  const code = searchParams.get("ref")

  if (!code) {
    return NextResponse.redirect(process.env.NEXT_PUBLIC_APP_URL ?? "/")
  }

  const link = await recordClick(code, {
    ipAddress: req.headers.get("x-forwarded-for") ?? req.headers.get("x-real-ip") ?? undefined,
    userAgent: req.headers.get("user-agent") ?? undefined,
    referrer:  req.headers.get("referer") ?? undefined,
  })

  const destination = link?.url ?? process.env.NEXT_PUBLIC_APP_URL ?? "/"
  const res = NextResponse.redirect(destination)
  res.cookies.set("aff_ref", code, { maxAge: 60 * 60 * 24 * 30, path: "/" })
  return res
}
