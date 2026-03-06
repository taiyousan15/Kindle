import { NextRequest, NextResponse } from "next/server"
import { prisma } from "@/lib/db"
import { getRankLabel } from "@/lib/affiliate/rank"
import { z } from "zod"

export async function GET(_req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params

  const partner = await prisma.partner.findUnique({
    where: { id },
    include: {
      conversions: {
        orderBy: { createdAt: "desc" },
        take: 100,
      },
      commissions: {
        select: { amount: true, status: true, paidAt: true },
      },
    },
  })

  if (!partner) return NextResponse.json({ error: "Not found" }, { status: 404 })

  // LP名を一括取得
  const lpIds = [...new Set(partner.conversions.map(c => c.lpId).filter(Boolean))] as string[]
  const lps = lpIds.length
    ? await prisma.landingPage.findMany({ where: { id: { in: lpIds } }, select: { id: true, name: true } })
    : []
  const lpMap = Object.fromEntries(lps.map(l => [l.id, l.name]))

  const pendingAmount = partner.commissions
    .filter(c => c.status === "APPROVED" && !c.paidAt)
    .reduce((s, c) => s + c.amount, 0)

  const paidAmount = partner.commissions
    .filter(c => c.status === "APPROVED" && !!c.paidAt)
    .reduce((s, c) => s + c.amount, 0)

  const bank = (partner.bankAccountInfo as Record<string, string> | null) ?? {}

  return NextResponse.json({
    partner: {
      id: partner.id,
      name: partner.name,
      email: partner.email,
      code: partner.code,
      rank: partner.rank,
      rankLabel: getRankLabel(partner.rank),
      commissionRate: partner.commissionRate,
      status: partner.status,
      channel: partner.channels[0] ?? null,
      bankName: bank.bankName ?? null,
      bankBranch: bank.bankBranch ?? null,
      bankAccount: bank.bankAccount ?? null,
      bankHolder: bank.bankHolder ?? null,
      totalConversions: partner.totalConversions,
      pendingAmount,
      paidAmount,
      conversions: partner.conversions.map(c => ({
        id: c.id,
        type: c.type,
        amount: c.amount,
        commissionAmount: 0, // commission is in AffiliateCommission table
        status: c.status,
        createdAt: c.createdAt,
        lp: c.lpId ? { name: lpMap[c.lpId] ?? "—" } : null,
      })),
    },
  })
}

const patchSchema = z.object({
  status: z.enum(["ACTIVE", "PENDING", "SUSPENDED"]).optional(),
})

export async function PATCH(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const body = await req.json()
  const parsed = patchSchema.safeParse(body)
  if (!parsed.success) return NextResponse.json({ error: "Invalid input" }, { status: 400 })

  await prisma.partner.update({
    where: { id },
    data: parsed.data,
  })

  return NextResponse.json({ success: true })
}
