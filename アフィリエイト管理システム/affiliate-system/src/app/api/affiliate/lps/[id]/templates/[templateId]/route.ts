import { NextRequest, NextResponse } from "next/server"
import { z } from "zod"
import { prisma } from "@/lib/db"

const updateSchema = z.object({
  title:  z.string().min(1).optional(),
  body:   z.string().min(1).optional(),
  medium: z.string().optional(),
})

export async function PATCH(req: NextRequest, { params }: { params: Promise<{ templateId: string }> }) {
  try {
    const { templateId } = await params
    const data = updateSchema.parse(await req.json())
    await prisma.affiliateTemplate.update({ where: { id: templateId }, data })
    return NextResponse.json({ success: true })
  } catch (error) {
    if (error instanceof z.ZodError) return NextResponse.json({ success: false, errors: error.issues }, { status: 400 })
    console.error("template PATCH error:", error)
    return NextResponse.json({ success: false }, { status: 500 })
  }
}

export async function DELETE(_req: NextRequest, { params }: { params: Promise<{ templateId: string }> }) {
  try {
    const { templateId } = await params
    await prisma.affiliateTemplate.update({ where: { id: templateId }, data: { isActive: false } })
    return NextResponse.json({ success: true })
  } catch (error) {
    console.error("template DELETE error:", error)
    return NextResponse.json({ success: false }, { status: 500 })
  }
}
