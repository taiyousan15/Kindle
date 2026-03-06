"use client"

import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { LayoutDashboard, Users, LayoutList, FileText, CreditCard, LogOut } from "lucide-react"

const NAV = [
  { href: "/affiliate", label: "ダッシュボード", icon: LayoutDashboard },
  { href: "/affiliate/lps", label: "LP管理", icon: LayoutList },
  { href: "/affiliate/partners", label: "パートナー", icon: Users },
  { href: "/affiliate/conversions", label: "成約一覧", icon: FileText },
  { href: "/affiliate/payouts", label: "報酬支払い", icon: CreditCard },
]

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()

  const handleLogout = async () => {
    await fetch("/api/affiliate/auth/logout", { method: "POST" })
    router.push("/affiliate/login")
  }

  return (
    <div className="flex min-h-screen">
      <aside className="w-56 shrink-0 bg-gray-900 text-white flex flex-col">
        <div className="px-4 py-5 border-b border-gray-700">
          <span className="text-sm font-bold tracking-wide">ASP 管理画面</span>
        </div>
        <nav className="flex-1 py-4 space-y-1 px-2">
          {NAV.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || (href !== "/affiliate" && pathname.startsWith(href))
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors ${
                  active ? "bg-blue-600 text-white" : "text-gray-300 hover:bg-gray-800"
                }`}
              >
                <Icon className="h-4 w-4 shrink-0" />
                {label}
              </Link>
            )
          })}
        </nav>
        <div className="px-4 py-4 border-t border-gray-700 space-y-2">
          <Link href="/affiliate/join" className="block text-xs text-gray-400 hover:text-white">
            パートナー登録ページ →
          </Link>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 text-xs text-gray-400 hover:text-white"
          >
            <LogOut className="h-3 w-3" />
            ログアウト
          </button>
        </div>
      </aside>

      <main className="flex-1 bg-gray-50 min-h-screen overflow-auto">
        {children}
      </main>
    </div>
  )
}
