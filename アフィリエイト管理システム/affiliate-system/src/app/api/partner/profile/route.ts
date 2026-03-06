import { NextRequest, NextResponse } from "next/server"
import { prisma } from "@/lib/db"
import { getRankLabel } from "@/lib/affiliate/rank"
import { z } from "zod"

export async function GET(req: NextRequest) {
  try {
    const partnerId = req.cookies.get("partner_id")?.value
    if (!partnerId) return NextResponse.json({ error: "Unauthorized" }, { status: 401 })

    const partner = await prisma.partner.findUnique({
      where: { id: partnerId },
      select: { name: true, email: true, channels: true, bankAccountInfo: true, rank: true },
    })
    if (!partner) return NextResponse.json({ error: "Not found" }, { status: 404 })

    const bank = (partner.bankAccountInfo as Record<string, string> | null) ?? {}

    return NextResponse.json({
      profile: {
        name: partner.name ?? "",
        email: partner.email,
        channel: partner.channels[0] ?? "",
        rankLabel: getRankLabel(partner.rank),
        bankName: bank.bankName ?? "",
        bankBranch: bank.bankBranch ?? "",
        bankAccount: bank.bankAccount ?? "",
        bankHolder: bank.bankHolder ?? "",
      },
    })
  } catch (error) {
    console.error("profile GET error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}

const updateSchema = z.object({
  name: z.string().min(1).optional(),
  channel: z.string().optional(),
  bankName: z.string().optional(),
  bankBranch: z.string().optional(),
  bankAccount: z.string().optional(),
  bankHolder: z.string().optional(),
})

export async function PATCH(req: NextRequest) {
  try {
    const partnerId = req.cookies.get("partner_id")?.value
    if (!partnerId) return NextResponse.json({ error: "Unauthorized" }, { status: 401 })

    const body = await req.json()
    const parsed = updateSchema.safeParse(body)
    if (!parsed.success) return NextResponse.json({ error: "Invalid input" }, { status: 400 })

    const { name, channel, bankName, bankBranch, bankAccount, bankHolder } = parsed.data

    const existing = await prisma.partner.findUnique({
      where: { id: partnerId },
      select: { bankAccountInfo: true },
    })
    const currentBank = (existing?.bankAccountInfo as Record<string, string> | null) ?? {}
    const newBank = { ...currentBank, ...{ bankName, bankBranch, bankAccount, bankHolder } }

    await prisma.partner.update({
      where: { id: partnerId },
      data: {
        ...(name ? { name } : {}),
        ...(channel !== undefined ? { channels: [channel].filter(Boolean) } : {}),
        bankAccountInfo: newBank,
      },
    })

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error("profile PATCH error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
