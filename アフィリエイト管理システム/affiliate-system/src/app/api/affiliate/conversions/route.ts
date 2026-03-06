import { NextRequest, NextResponse } from "next/server"
import { z } from "zod"
import { prisma } from "@/lib/db"
import { recordConversion } from "@/lib/affiliate/service"

const schema = z.object({
  type:       z.enum(["LINE_OPTIN", "EMAIL_OPTIN", "FRONTEND_PURCHASE", "BACKEND_PURCHASE"]),
  linkCode:   z.string().optional(),
  lineUserId: z.string().optional(),
  amount:     z.number().default(0),
  orderId:    z.string().optional(),
})

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url)
    const status = searchParams.get("status")
    const type   = searchParams.get("type")

    const conversions = await prisma.affiliateConversion.findMany({
      where: {
        tenantId: "default",
        ...(status && status !== "ALL" ? { status: status as never } : {}),
        ...(type ? { type: type as never } : {}),
      },
      include: {
        partner: { select: { name: true, code: true } },
      },
      orderBy: { createdAt: "desc" },
      take: 200,
    })

    // LP名を一括取得
    const lpIds = [...new Set(conversions.map(c => c.lpId).filter(Boolean))] as string[]
    const lps = lpIds.length
      ? await prisma.landingPage.findMany({ where: { id: { in: lpIds } }, select: { id: true, name: true } })
      : []
    const lpMap = Object.fromEntries(lps.map(l => [l.id, l.name]))

    const result = conversions.map(c => ({
      ...c,
      lp: c.lpId ? { name: lpMap[c.lpId] ?? "—" } : null,
    }))

    return NextResponse.json({ conversions: result })
  } catch (error) {
    console.error("conversions GET error:", error)
    return NextResponse.json({ conversions: [] })
  }
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    const cookieRef = req.cookies.get("aff_ref")?.value
    const data = schema.parse({ ...body, linkCode: body.linkCode ?? cookieRef })

    const conversion = await recordConversion(data)
    if (!conversion) {
      return NextResponse.json({ success: false, message: "トラッキングコードが見つかりません" }, { status: 404 })
    }
    return NextResponse.json({ success: true, conversionId: conversion.id })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json({ success: false, errors: error.issues }, { status: 400 })
    }
    console.error("conversion POST error:", error)
    return NextResponse.json({ success: false }, { status: 500 })
  }
}
