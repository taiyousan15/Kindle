import { NextRequest, NextResponse } from "next/server"

export async function POST(req: NextRequest) {
  try {
    const { password } = await req.json()
    const adminPassword = process.env.ADMIN_PASSWORD

    if (!adminPassword) {
      return NextResponse.json({ success: false, error: "Server misconfigured" }, { status: 500 })
    }

    if (password !== adminPassword) {
      return NextResponse.json({ success: false }, { status: 401 })
    }

    const res = NextResponse.json({ success: true })
    res.cookies.set("admin_session", "1", {
      httpOnly: true,
      secure:   process.env.NODE_ENV === "production",
      maxAge:   60 * 60 * 24 * 7,
      path:     "/",
      sameSite: "lax",
    })
    return res
  } catch {
    return NextResponse.json({ success: false }, { status: 500 })
  }
}
