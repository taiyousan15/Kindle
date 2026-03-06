import { NextRequest, NextResponse } from "next/server"
import { z } from "zod"
import { prisma } from "@/lib/db"

const schema = z.object({
  title:  z.string().min(1),
  body:   z.string().min(1),
  medium: z.string().optional(),
})

export async function GET(_req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const templates = await prisma.affiliateTemplate.findMany({
    where: { lpId: id, isActive: true },
    orderBy: { sortOrder: "asc" },
  })
  return NextResponse.json({ templates })
}

export async function POST(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params
    const data = schema.parse(await req.json())
    const template = await prisma.affiliateTemplate.create({
      data: { tenantId: "default", lpId: id, ...data },
    })
    return NextResponse.json({ success: true, template })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json({ success: false, errors: error.issues }, { status: 400 })
    }
    console.error("template create error:", error)
    return NextResponse.json({ success: false }, { status: 500 })
  }
}
