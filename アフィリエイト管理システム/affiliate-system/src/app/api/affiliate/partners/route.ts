import { NextRequest, NextResponse } from "next/server"
import { prisma } from "@/lib/db"
import { getRankLabel } from "@/lib/affiliate/rank"

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url)
    const status = searchParams.get("status")
    const q = searchParams.get("q")

    const partners = await prisma.partner.findMany({
      where: {
        tenantId: "default",
        ...(status ? { status: status as never } : {}),
        ...(q ? {
          OR: [
            { name:  { contains: q, mode: "insensitive" } },
            { email: { contains: q, mode: "insensitive" } },
            { code:  { contains: q, mode: "insensitive" } },
          ],
        } : {}),
      },
      include: {
        _count: { select: { conversions: true, links: true } },
        commissions: { where: { status: "APPROVED", paidAt: null }, select: { amount: true } },
      },
      orderBy: { createdAt: "desc" },
    })

    const enriched = partners.map(p => ({
      ...p,
      rankLabel:     getRankLabel(p.rank),
      pendingAmount: p.commissions.reduce((s, c) => s + c.amount, 0),
      commissions:   undefined,
    }))

    return NextResponse.json({ partners: enriched })
  } catch (error) {
    console.error("partners GET error:", error)
    return NextResponse.json({ partners: [] })
  }
}
