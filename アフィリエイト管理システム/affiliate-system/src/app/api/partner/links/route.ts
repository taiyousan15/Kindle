import { NextRequest, NextResponse } from "next/server"
import { prisma } from "@/lib/db"
import { generateLinkCode } from "@/lib/affiliate/service"
import QRCode from "qrcode"

export async function GET(req: NextRequest) {
  try {
    const partnerId = req.cookies.get("partner_id")?.value
    if (!partnerId) return NextResponse.json({ error: "Unauthorized" }, { status: 401 })

    const links = await prisma.affiliateLink.findMany({
      where: { partnerId, isActive: true },
      include: { lp: { include: { templates: { where: { isActive: true }, orderBy: { sortOrder: "asc" } } } } },
      orderBy: { createdAt: "desc" },
    })

    const appUrl = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3002"
    const enriched = links.map(link => ({
      ...link,
      trackingUrl: `${appUrl}/api/affiliate/track?ref=${link.linkCode}`,
      optinRate: link.clicks > 0
        ? (((link.lineOptins + link.emailOptins) / link.clicks) * 100).toFixed(1)
        : "0.0",
    }))

    return NextResponse.json({ links: enriched })
  } catch (error) {
    console.error("links GET error:", error)
    return NextResponse.json({ links: [] })
  }
}

export async function POST(req: NextRequest) {
  try {
    const partnerId = req.cookies.get("partner_id")?.value
    if (!partnerId) return NextResponse.json({ error: "Unauthorized" }, { status: 401 })

    const { lpId } = await req.json()
    const link = await generateLinkCode(partnerId, lpId)
    const appUrl = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3002"
    const trackingUrl = `${appUrl}/api/affiliate/track?ref=${link.linkCode}`
    const qrDataUrl = await QRCode.toDataURL(trackingUrl, { width: 300, margin: 2 })

    return NextResponse.json({ link, trackingUrl, qrDataUrl })
  } catch (error) {
    console.error("links POST error:", error)
    return NextResponse.json({ error: "Failed to generate link" }, { status: 500 })
  }
}
