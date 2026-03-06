import { NextRequest, NextResponse } from "next/server"
import { prisma } from "@/lib/db"
import { z } from "zod"

const patchSchema = z.object({
  status: z.enum(["APPROVED", "REJECTED", "PAID"]),
})

export async function PATCH(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params
    const body = await req.json()
    const { status } = patchSchema.parse(body)

    await prisma.affiliateConversion.update({
      where: { id },
      data: {
        status,
        ...(status === "APPROVED" ? { approvedAt: new Date() } : {}),
      },
    })

    // 承認時はコミッションも承認
    if (status === "APPROVED") {
      await prisma.affiliateCommission.updateMany({
        where: { conversionId: id },
        data: { status: "APPROVED" },
      })
    }

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error("conversion PATCH error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
