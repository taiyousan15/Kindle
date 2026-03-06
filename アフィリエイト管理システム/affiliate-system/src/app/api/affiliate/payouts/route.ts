import { NextRequest, NextResponse } from "next/server"
import { prisma } from "@/lib/db"
import { z } from "zod"

export async function GET() {
  try {
    // 未払いコミッションをパートナー別に集計
    const pendingCommissions = await prisma.affiliateCommission.findMany({
      where: { tenantId: "default", status: "APPROVED", paidAt: null },
      include: { partner: { select: { id: true, name: true, code: true, bankAccountInfo: true } } },
    })

    const partnerMap = new Map<string, {
      partnerId: string; partnerName: string; partnerCode: string
      bankInfo: string; pendingAmount: number; commissionIds: string[]
    }>()

    for (const c of pendingCommissions) {
      if (!c.partner) continue
      const bank = (c.partner.bankAccountInfo as Record<string, string> | null) ?? {}
      const bankInfo = bank.bankName
        ? `${bank.bankName} ${bank.bankBranch ?? ""} ${bank.bankAccount ?? ""} ${bank.bankHolder ?? ""}`.trim()
        : ""
      const existing = partnerMap.get(c.partnerId)
      if (existing) {
        existing.pendingAmount += c.amount
        existing.commissionIds.push(c.id)
      } else {
        partnerMap.set(c.partnerId, {
          partnerId:   c.partnerId,
          partnerName: c.partner.name,
          partnerCode: c.partner.code,
          bankInfo,
          pendingAmount: c.amount,
          commissionIds: [c.id],
        })
      }
    }

    const requests = [...partnerMap.values()].filter(r => r.pendingAmount > 0)

    const payouts = await prisma.affiliatePayout.findMany({
      where: { tenantId: "default" },
      include: { partner: { select: { name: true, code: true } } },
      orderBy: { createdAt: "desc" },
      take: 100,
    })

    return NextResponse.json({ requests, payouts })
  } catch (error) {
    console.error("payouts GET error:", error)
    return NextResponse.json({ requests: [], payouts: [] })
  }
}

const postSchema = z.object({
  partnerId:     z.string(),
  commissionIds: z.array(z.string()),
  amount:        z.number().positive(),
})

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    const { partnerId, commissionIds, amount } = postSchema.parse(body)

    await prisma.$transaction([
      prisma.affiliatePayout.create({
        data: {
          tenantId:  "default",
          partnerId,
          amount,
          status:    "COMPLETED",
          paidAt:    new Date(),
          paymentMethod: "bank_transfer",
        },
      }),
      prisma.affiliateCommission.updateMany({
        where: { id: { in: commissionIds } },
        data:  { status: "APPROVED", paidAt: new Date() },
      }),
    ])

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error("payouts POST error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
