import { NextRequest, NextResponse } from "next/server"
import { prisma } from "@/lib/db"

export async function GET(req: NextRequest) {
  try {
    const partnerId = req.cookies.get("partner_id")?.value
    if (!partnerId) return NextResponse.json({ error: "Unauthorized" }, { status: 401 })

    const { searchParams } = new URL(req.url)
    const page = Math.max(1, Number(searchParams.get("page") ?? 1))
    const limit = 50

    const commissions = await prisma.affiliateCommission.findMany({
      where: { partnerId },
      include: {
        conversion: { select: { type: true, lpId: true, createdAt: true } },
      },
      orderBy: { createdAt: "desc" },
      skip: (page - 1) * limit,
      take: limit,
    })

    const lpIds = [...new Set(commissions.map(c => c.conversion?.lpId).filter(Boolean))] as string[]
    const lps = lpIds.length
      ? await prisma.landingPage.findMany({ where: { id: { in: lpIds } }, select: { id: true, name: true } })
      : []
    const lpMap = Object.fromEntries(lps.map(l => [l.id, l.name]))

    const result = commissions.map(c => ({
      id: c.id,
      type: c.conversion?.type ?? "PURCHASE",
      commissionAmount: c.amount,
      status: c.status,
      tier: c.tier,
      createdAt: c.createdAt,
      lpName: c.conversion?.lpId ? (lpMap[c.conversion.lpId] ?? null) : null,
    }))

    return NextResponse.json({ conversions: result })
  } catch (error) {
    console.error("conversions GET error:", error)
    return NextResponse.json({ conversions: [] })
  }
}
