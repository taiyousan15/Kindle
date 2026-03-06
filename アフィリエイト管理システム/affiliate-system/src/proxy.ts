import { NextRequest, NextResponse } from "next/server"

const PARTNER_PROTECTED = [
  "/partner/dashboard",
  "/partner/links",
  "/partner/conversions",
  "/partner/profile",
]

const ADMIN_PROTECTED = [
  "/affiliate",
]

const ADMIN_PUBLIC = [
  "/affiliate/login",
  "/affiliate/join",
]

export function proxy(req: NextRequest) {
  const { pathname } = req.nextUrl

  // Partner portal protection
  const isPartnerProtected = PARTNER_PROTECTED.some(p => pathname.startsWith(p))
  if (isPartnerProtected) {
    const partnerId = req.cookies.get("partner_id")?.value
    if (!partnerId) {
      const loginUrl = new URL("/partner/login", req.url)
      loginUrl.searchParams.set("redirect", pathname)
      return NextResponse.redirect(loginUrl)
    }
    return NextResponse.next()
  }

  // Admin portal protection
  const isAdminPublic = ADMIN_PUBLIC.some(p => pathname.startsWith(p))
  const isAdminProtected = !isAdminPublic && ADMIN_PROTECTED.some(p => pathname.startsWith(p))
  if (isAdminProtected) {
    const session = req.cookies.get("admin_session")?.value
    if (!session) {
      const loginUrl = new URL("/affiliate/login", req.url)
      loginUrl.searchParams.set("redirect", pathname)
      return NextResponse.redirect(loginUrl)
    }
  }

  return NextResponse.next()
}

export const config = {
  matcher: ["/partner/:path*", "/affiliate/:path*"],
}
