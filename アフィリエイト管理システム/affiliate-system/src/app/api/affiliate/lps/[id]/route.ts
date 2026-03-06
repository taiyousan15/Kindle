import { NextRequest, NextResponse } from "next/server"
import { z } from "zod"
import { prisma } from "@/lib/db"

const updateSchema = z.object({
  name:        z.string().min(1).optional(),
  url:         z.string().url().optional(),
  description: z.string().optional(),
})

export async function PATCH(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params
    const data = updateSchema.parse(await req.json())
    await prisma.landingPage.update({ where: { id }, data })
    return NextResponse.json({ success: true })
  } catch (error) {
    if (error instanceof z.ZodError) return NextResponse.json({ success: false, errors: error.issues }, { status: 400 })
    console.error("lp PATCH error:", error)
    return NextResponse.json({ success: false }, { status: 500 })
  }
}

export async function DELETE(_req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params
    await prisma.landingPage.update({ where: { id }, data: { isActive: false } })
    return NextResponse.json({ success: true })
  } catch (error) {
    console.error("lp DELETE error:", error)
    return NextResponse.json({ success: false }, { status: 500 })
  }
}
