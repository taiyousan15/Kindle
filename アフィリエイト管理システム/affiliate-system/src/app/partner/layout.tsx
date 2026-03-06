"use client"

import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { LayoutDashboard, Link2, History, User, LogOut } from "lucide-react"
import { toast } from "sonner"

const NAV = [
  { href: "/partner/dashboard", label: "ダッシュボード", icon: LayoutDashboard },
  { href: "/partner/links", label: "リンク・QR", icon: Link2 },
  { href: "/partner/conversions", label: "成約履歴", icon: History },
  { href: "/partner/profile", label: "プロフィール", icon: User },
]

export default function PartnerLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()

  const isLoginPage = pathname === "/partner/login"
  if (isLoginPage) return <>{children}</>

  const logout = async () => {
    await fetch("/api/partner/auth/logout", { method: "POST" })
    toast.success("ログアウトしました")
    router.push("/partner/login")
  }

  return (
    <div className="flex min-h-screen">
      <aside className="w-52 shrink-0 bg-white border-r flex flex-col">
        <div className="px-4 py-5 border-b">
          <span className="text-sm font-bold text-blue-600">パートナーポータル</span>
        </div>
        <nav className="flex-1 py-4 space-y-1 px-2">
          {NAV.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || pathname.startsWith(href)
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors ${
                  active ? "bg-blue-50 text-blue-700 font-medium" : "text-gray-600 hover:bg-gray-50"
                }`}
              >
                <Icon className="h-4 w-4 shrink-0" />
                {label}
              </Link>
            )
          })}
        </nav>
        <div className="px-4 py-4 border-t">
          <button
            onClick={logout}
            className="flex items-center gap-2 text-xs text-gray-400 hover:text-red-500 transition-colors"
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
