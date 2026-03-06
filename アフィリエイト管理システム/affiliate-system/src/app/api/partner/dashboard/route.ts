import { NextRequest, NextResponse } from "next/server"
import { prisma } from "@/lib/db"
import { getPartnerStats } from "@/lib/affiliate/service"
import { getRankLabel, getNextRankInfo } from "@/lib/affiliate/rank"

export async function GET(req: NextRequest) {
  try {
    const partnerId = req.cookies.get("partner_id")?.value
    if (!partnerId) return NextResponse.json({ error: "Unauthorized" }, { status: 401 })

    const partner = await prisma.partner.findUnique({
      where: { id: partnerId },
      include: { onboarding: true },
    })
    if (!partner) return NextResponse.json({ error: "Not found" }, { status: 404 })

    const stats = await getPartnerStats(partnerId)
    const nextRank = getNextRankInfo(partner.totalConversions)

    return NextResponse.json({
      partner: {
        id:             partner.id,
        name:           partner.name,
        email:          partner.email,
        code:           partner.code,
        rank:           partner.rank,
        rankLabel:      getRankLabel(partner.rank),
        commissionRate: partner.commissionRate,
        status:         partner.status,
      },
      stats,
      nextRank,
      onboarding: partner.onboarding,
    })
  } catch (error) {
    console.error("dashboard GET error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
