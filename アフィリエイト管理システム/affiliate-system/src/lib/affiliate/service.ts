import { prisma } from "@/lib/db"
import { ConversionType, AffiliateStatus, CommissionStatus } from "@prisma/client"
import { calculateRank } from "./rank"
import { nanoid } from "nanoid"

const TENANT_ID = "default"
const TIER2_RATE = 0.3 // Tier2はTier1報酬の30%

export async function recordClick(linkCode: string, meta: {
  ipAddress?: string
  userAgent?: string
  referrer?: string
}) {
  const link = await prisma.affiliateLink.findUnique({
    where: { linkCode },
    include: { lp: true },
  })
  if (!link || !link.isActive) return null

  await prisma.$transaction([
    prisma.affiliateClick.create({
      data: {
        tenantId:  TENANT_ID,
        linkId:    link.id,
        partnerId: link.partnerId,
        lpId:      link.lpId ?? undefined,
        ipAddress: meta.ipAddress,
        userAgent: meta.userAgent,
        referrer:  meta.referrer,
      },
    }),
    prisma.affiliateLink.update({
      where: { id: link.id },
      data: { clicks: { increment: 1 } },
    }),
  ])

  return link
}

export async function recordConversion(params: {
  linkCode?: string
  lineUserId?: string
  type: ConversionType
  amount?: number
  orderId?: string
}) {
  const { linkCode, lineUserId, type, amount = 0, orderId } = params

  let link = null
  let partnerId: string | null = null
  let lpId: string | null = null

  if (linkCode) {
    link = await prisma.affiliateLink.findUnique({
      where: { linkCode },
      include: { partner: true },
    })
    if (link) {
      partnerId = link.partnerId
      lpId = link.lpId ?? null
    }
  }

  // lineUserIdで遡ってパートナーを特定
  if (!partnerId && lineUserId) {
    const prev = await prisma.affiliateConversion.findFirst({
      where: { lineUserId, type: ConversionType.LINE_OPTIN },
      orderBy: { createdAt: "desc" },
    })
    if (prev) {
      partnerId = prev.partnerId
      lpId = prev.lpId ?? null
    }
  }

  if (!partnerId) return null

  const partner = await prisma.partner.findUnique({ where: { id: partnerId } })
  if (!partner) return null

  const { rate } = calculateRank(partner.totalConversions)
  const commissionAmount = Math.floor(amount * rate / 100)

  const coolingDays = partner.coolingPeriodDays
  const payableAt = new Date()
  payableAt.setDate(payableAt.getDate() + coolingDays)

  const result = await prisma.$transaction(async (tx) => {
    const conversion = await tx.affiliateConversion.create({
      data: {
        tenantId:  TENANT_ID,
        partnerId,
        linkId:    link?.id ?? undefined,
        lpId:      lpId ?? undefined,
        lineUserId,
        type,
        amount,
        orderId,
        payableAt,
      },
    })

    const commission = await tx.affiliateCommission.create({
      data: {
        tenantId:    TENANT_ID,
        partnerId,
        conversionId: conversion.id,
        amount:      commissionAmount,
        percentage:  rate,
        type:        type === "LINE_OPTIN" || type === "EMAIL_OPTIN" ? "OPTIN" : type === "FRONTEND_PURCHASE" ? "FRONTEND" : "BACKEND",
        tier:        "1",
      },
    })

    // リンクカウンター更新
    if (link) {
      await tx.affiliateLink.update({
        where: { id: link.id },
        data: {
          conversions: { increment: 1 },
          revenue:     { increment: amount },
          ...(type === "LINE_OPTIN"   ? { lineOptins:  { increment: 1 } } : {}),
          ...(type === "EMAIL_OPTIN"  ? { emailOptins: { increment: 1 } } : {}),
        },
      })
    }

    // パートナーの成約数更新＆ランク自動昇格
    const updatedPartner = await tx.partner.update({
      where: { id: partnerId! },
      data: { totalConversions: { increment: 1 } },
    })
    const { rank, rate: newRate } = calculateRank(updatedPartner.totalConversions)
    if (rank !== updatedPartner.rank) {
      await tx.partner.update({
        where: { id: partnerId! },
        data: { rank, commissionRate: newRate },
      })
    }

    // Tier2 報酬（紹介者への報酬）
    if (partner.referredById) {
      const tier2Amount = Math.floor(commissionAmount * TIER2_RATE)
      if (tier2Amount > 0) {
        await tx.affiliateCommission.create({
          data: {
            tenantId:    TENANT_ID,
            partnerId:   partner.referredById,
            conversionId: conversion.id,
            amount:      tier2Amount,
            percentage:  Math.floor(rate * TIER2_RATE),
            type:        commission.type,
            tier:        "2",
          },
        })
      }
    }

    return conversion
  })

  return result
}

export async function generateLinkCode(partnerId: string, lpId?: string) {
  const partner = await prisma.partner.findUnique({ where: { id: partnerId } })
  if (!partner) throw new Error("Partner not found")

  const lpCode = lpId
    ? (await prisma.landingPage.findUnique({ where: { id: lpId } }))?.lpCode ?? ""
    : ""

  const linkCode = `${partner.code}${lpCode ? `-${lpCode}` : ""}-${nanoid(6)}`

  const baseUrl = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000"
  const url = lpId
    ? (await prisma.landingPage.findUnique({ where: { id: lpId } }))?.url ?? baseUrl
    : baseUrl

  return prisma.affiliateLink.create({
    data: {
      tenantId: TENANT_ID,
      partnerId,
      lpId,
      url,
      linkCode,
    },
  })
}

export async function getPartnerStats(partnerId: string) {
  const [links, conversions, commissions, payouts] = await Promise.all([
    prisma.affiliateLink.findMany({ where: { partnerId } }),
    prisma.affiliateConversion.findMany({ where: { partnerId } }),
    prisma.affiliateCommission.findMany({ where: { partnerId } }),
    prisma.affiliatePayout.findMany({ where: { partnerId } }).catch(() => []),
  ])

  const totalClicks      = links.reduce((s: number, l) => s + l.clicks, 0)
  const totalConversions = conversions.length
  const totalLineOptins  = conversions.filter(c => c.type === "LINE_OPTIN").length
  const totalEmailOptins = conversions.filter(c => c.type === "EMAIL_OPTIN").length
  const optinRate        = totalClicks > 0 ? ((totalLineOptins + totalEmailOptins) / totalClicks * 100).toFixed(1) : "0.0"
  const pendingAmount    = commissions.filter(c => c.status === CommissionStatus.APPROVED && !c.paidAt).reduce((s: number, c) => s + c.amount, 0)
  const paidAmount       = commissions.filter(c => c.status === CommissionStatus.APPROVED && !!c.paidAt).reduce((s: number, c) => s + c.amount, 0)

  return {
    totalClicks,
    totalConversions,
    totalLineOptins,
    totalEmailOptins,
    optinRate,
    pendingAmount,
    paidAmount,
  }
}

export async function getLpStats(tenantId = TENANT_ID) {
  const lps = await prisma.landingPage.findMany({
    where: { tenantId, isActive: true },
    include: { links: true },
  })

  return lps.map(lp => {
    const totalClicks      = lp.links.reduce((s, l) => s + l.clicks, 0)
    const totalLineOptins  = lp.links.reduce((s, l) => s + l.lineOptins, 0)
    const totalEmailOptins = lp.links.reduce((s, l) => s + l.emailOptins, 0)
    const totalConversions = totalLineOptins + totalEmailOptins
    const optinRate        = totalClicks > 0 ? (totalConversions / totalClicks * 100).toFixed(1) : "0.0"

    return {
      ...lp,
      totalClicks,
      totalLineOptins,
      totalEmailOptins,
      totalConversions,
      optinRate,
    }
  })
}
