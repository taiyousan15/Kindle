import Link from "next/link";
import { BookOpen, TrendingUp, Search, BarChart3, Image, Home } from "lucide-react";

const nav = [
  { href: "/", icon: Home, label: "ダッシュボード" },
  { href: "/keywords", icon: Search, label: "キーワード" },
  { href: "/genres", icon: TrendingUp, label: "ジャンル" },
  { href: "/title-analyzer", icon: BookOpen, label: "タイトル分析" },
  { href: "/covers", icon: Image, label: "表紙分析" },
  { href: "/prediction", icon: BarChart3, label: "売上予測" },
];

export function Sidebar() {
  return (
    <nav className="w-56 bg-gray-900 border-r border-gray-800 flex flex-col py-6 px-3 shrink-0">
      <div className="mb-8 px-3">
        <p className="text-xs font-bold text-blue-400 uppercase tracking-wider">
          Kindle Research
        </p>
      </div>
      <ul className="space-y-1">
        {nav.map((item) => (
          <li key={item.href}>
            <Link
              href={item.href}
              className="flex items-center gap-3 px-3 py-2 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 transition-colors text-sm"
            >
              <item.icon className="w-4 h-4 shrink-0" />
              {item.label}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
