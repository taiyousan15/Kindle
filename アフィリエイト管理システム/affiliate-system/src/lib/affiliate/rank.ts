import { PartnerRank } from "@prisma/client"

const RANK_THRESHOLDS = [
  { rank: PartnerRank.VIP,      minConversions: 300, rate: 20 },
  { rank: PartnerRank.PLATINUM, minConversions: 100, rate: 18 },
  { rank: PartnerRank.GOLD,     minConversions: 30,  rate: 15 },
  { rank: PartnerRank.SILVER,   minConversions: 10,  rate: 12 },
  { rank: PartnerRank.STANDARD, minConversions: 0,   rate: 10 },
] as const

export function calculateRank(totalConversions: number): {
  rank: PartnerRank
  rate: number
} {
  for (const threshold of RANK_THRESHOLDS) {
    if (totalConversions >= threshold.minConversions) {
      return { rank: threshold.rank, rate: threshold.rate }
    }
  }
  return { rank: PartnerRank.STANDARD, rate: 10 }
}

export function getRankLabel(rank: PartnerRank): string {
  const labels: Record<PartnerRank, string> = {
    STANDARD: "スタンダード",
    SILVER:   "シルバー",
    GOLD:     "ゴールド",
    PLATINUM: "プラチナ",
    VIP:      "VIP",
  }
  return labels[rank]
}

export function getNextRankInfo(totalConversions: number): {
  nextRank: PartnerRank | null
  needed: number
} {
  const reversed = [...RANK_THRESHOLDS].reverse()
  for (const threshold of reversed) {
    if (totalConversions < threshold.minConversions) {
      return {
        nextRank: threshold.rank,
        needed: threshold.minConversions - totalConversions,
      }
    }
  }
  return { nextRank: null, needed: 0 }
}
