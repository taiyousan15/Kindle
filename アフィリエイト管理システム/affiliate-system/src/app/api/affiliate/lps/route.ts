import { NextRequest, NextResponse } from "next/server"
import { z } from "zod"
import { prisma } from "@/lib/db"
import { getLpStats } from "@/lib/affiliate/service"
import { nanoid } from "nanoid"

const createSchema = z.object({
  name:        z.string().min(1),
  url:         z.string().url(),
  description: z.string().optional(),
})

export async function GET() {
  try {
    const stats = await getLpStats()
    return NextResponse.json({ lps: stats })
  } catch (error) {
    console.error("lps GET error:", error)
    return NextResponse.json({ lps: [] })
  }
}

export async function POST(req: NextRequest) {
  try {
    const data = createSchema.parse(await req.json())
    const lpCode = `lp${nanoid(6)}`
    const lp = await prisma.landingPage.create({
      data: { tenantId: "default", lpCode, ...data },
    })
    return NextResponse.json({ success: true, lp })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json({ success: false, errors: error.issues }, { status: 400 })
    }
    console.error("lp create error:", error)
    return NextResponse.json({ success: false }, { status: 500 })
  }
}
