import { NextRequest, NextResponse } from "next/server"
import { z } from "zod"
import { prisma } from "@/lib/db"
import { nanoid } from "nanoid"

const schema = z.object({
  name:        z.string().min(1),
  email:       z.string().email(),
  channels:    z.array(z.string()).default([]),
  websiteUrl:  z.string().url().optional().or(z.literal("")),
  bio:         z.string().optional(),
  referredBy:  z.string().optional(),
})

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    const data = schema.parse(body)

    const existing = await prisma.partner.findFirst({
      where: { email: data.email, tenantId: "default" },
    })
    if (existing) {
      return NextResponse.json({ success: false, message: "このメールアドレスは既に登録されています" }, { status: 409 })
    }

    let referredById: string | undefined
    if (data.referredBy) {
      const referrer = await prisma.partner.findUnique({ where: { code: data.referredBy } })
      referredById = referrer?.id
    }

    const code = `${data.name.replace(/\s+/g, "").toLowerCase().slice(0, 8)}${nanoid(4)}`
    const partner = await prisma.partner.create({
      data: {
        tenantId:    "default",
        email:       data.email,
        name:        data.name,
        code,
        channels:    data.channels,
        websiteUrl:  data.websiteUrl || undefined,
        bio:         data.bio,
        referredById,
        onboarding: { create: {} },
      },
    })

    return NextResponse.json({ success: true, partnerId: partner.id, code: partner.code })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json({ success: false, errors: error.issues }, { status: 400 })
    }
    console.error("join error:", error)
    return NextResponse.json({ success: false }, { status: 500 })
  }
}
