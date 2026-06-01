import { useState, useEffect, type ComponentType } from 'react'
import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Atom,
  Hexagon,
  Network,
  FlaskConical,
  GitCompare,
  ShieldCheck,
  Search,
  Filter,
  Heart,
  Clock,
  Diamond,
  ChevronDown,
  Menu,
  X,
  Layers,
  Upload,
  Cpu,
} from 'lucide-react'
import { preloadRoute } from '../App'

interface FavoriteItem {
  materialId: string
  formula: string
  spaceGroup: string
  topology: string
  addedAt: number
  elements: string[]
  verified: boolean
}

interface RecentItem {
  materialId: string
  formula: string
  spaceGroup: string
  topology: string
  viewedAt: number
}

interface NavItem {
  to: string
  icon: ComponentType<{ className?: string }>
  label: string
  badge?: number
}

interface NavGroup {
  title: string
  items: NavItem[]
}

function readCount<T>(key: string): number {
  try {
    const raw = localStorage.getItem(key)
    if (!raw) return 0
    const parsed: T[] = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed.length : 0
  } catch {
    return 0
  }
}

const groups: NavGroup[] = [
  {
    title: '概览',
    items: [
      { to: '/', icon: LayoutDashboard, label: '仪表盘' },
    ],
  },
  {
    title: '数据浏览',
    items: [
      { to: '/materials', icon: Atom, label: '材料库' },
      { to: '/prototypes', icon: Hexagon, label: '拓扑原型' },
      { to: '/classify', icon: Network, label: '分类浏览' },
    ],
  },
  {
    title: '工具',
    items: [
      { to: '/generate', icon: FlaskConical, label: '结构生成器' },
      { to: '/compare', icon: GitCompare, label: '材料对比' },
      { to: '/verify', icon: ShieldCheck, label: '拓扑验证' },
      { to: '/stacking', icon: Layers, label: '堆垛识别' },
      { to: '/import', icon: Upload, label: '数据导入' },
      { to: '/algorithms', icon: Cpu, label: '算法管理' },
    ],
  },
  {
    title: '搜索',
    items: [
      { to: '/search', icon: Search, label: '搜索' },
      { to: '/advanced-search', icon: Filter, label: '高级搜索' },
    ],
  },
  {
    title: '个人',
    items: [
      { to: '/favorites', icon: Heart, label: '收藏' },
      { to: '/recent', icon: Clock, label: '最近浏览' },
    ],
  },
]

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({})
  const [favCount, setFavCount] = useState(0)
  const [recentCount, setRecentCount] = useState(0)

  useEffect(() => {
    setFavCount(readCount<FavoriteItem>('cgcpt_favorites'))
    setRecentCount(readCount<RecentItem>('cgcpt_recent'))
    const onStorage = () => {
      setFavCount(readCount<FavoriteItem>('cgcpt_favorites'))
      setRecentCount(readCount<RecentItem>('cgcpt_recent'))
    }
    window.addEventListener('storage', onStorage)
    return () => window.removeEventListener('storage', onStorage)
  }, [])

  const badges: Record<string, number> = {}
  if (favCount > 0) badges['/favorites'] = favCount
  if (recentCount > 0) badges['/recent'] = recentCount

  const toggle = (title: string) => {
    setCollapsed((prev) => ({ ...prev, [title]: !prev[title] }))
  }

  return (
    <>
      <div className="h-14 sm:h-16 flex items-center justify-between px-4 sm:px-5 border-b border-gray-800">
        <div className="flex items-center gap-2.5">
          <Diamond className="w-6 h-6 sm:w-7 sm:h-7 text-cyan-400" />
          <span className="text-base sm:text-lg font-semibold text-white tracking-tight">
            CGCPT
          </span>
        </div>
        {onNavigate && (
          <button
            onClick={onNavigate}
            className="lg:hidden p-2.5 text-gray-400 hover:text-white transition-colors touch-manipulation"
          >
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      <nav className="flex-1 py-2 sm:py-3 px-2.5 sm:px-3 overflow-y-auto">
        {groups.map((group) => (
          <div key={group.title} className="mb-1.5">
            <button
              type="button"
              onClick={() => toggle(group.title)}
              className="flex items-center gap-1 w-full px-3 py-2.5 text-xs font-medium text-gray-500 uppercase tracking-wider hover:text-gray-300 transition-colors touch-manipulation"
            >
              <ChevronDown
                className={`w-3 h-3 transition-transform ${
                  collapsed[group.title] ? '-rotate-90' : ''
                }`}
              />
              {group.title}
            </button>

            {!collapsed[group.title] && (
              <div className="space-y-0.5 mt-0.5">
                {group.items.map(({ to, icon: Icon, label }) => {
                  const badge = badges[to]
                  return (
                    <NavLink
                      key={to}
                      to={to}
                      end={to === '/'}
                      onClick={onNavigate}
                      onMouseEnter={() => preloadRoute(to)}
                      className={({ isActive }) =>
                        `flex items-center justify-between gap-3 px-3 py-2.5 sm:py-2 rounded-lg text-sm font-medium transition-colors touch-manipulation ${
                          isActive
                            ? 'bg-cyan-500/10 text-cyan-400'
                            : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/50'
                        }`
                      }
                    >
                      <span className="flex items-center gap-3">
                        <Icon className="w-4.5 h-4.5 shrink-0" />
                        {label}
                      </span>
                      {badge !== undefined && badge > 0 && (
                        <span className="min-w-[1.25rem] h-5 flex items-center justify-center rounded-full bg-cyan-500/20 text-cyan-400 text-xs font-semibold px-1.5">
                          {badge}
                        </span>
                      )}
                    </NavLink>
                  )
                })}
              </div>
            )}
          </div>
        ))}
      </nav>

      <div className="px-4 sm:px-5 py-2.5 sm:py-3 border-t border-gray-800">
        <p className="text-xs text-gray-600">CGCPT v1.0.0</p>
      </div>
    </>
  )
}

export default function Sidebar() {
  const [mobileOpen, setMobileOpen] = useState(false)

  useEffect(() => {
    if (mobileOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
    return () => { document.body.style.overflow = '' }
  }, [mobileOpen])

  return (
    <>
      <button
        onClick={() => setMobileOpen(true)}
        className="lg:hidden fixed top-2.5 left-2.5 z-40 p-2.5 bg-gray-900/90 border border-gray-700 rounded-lg text-gray-400 hover:text-white hover:border-cyan-500/50 transition-colors backdrop-blur-sm touch-manipulation"
        aria-label="打开菜单"
      >
        <Menu className="w-5 h-5" />
      </button>

      {mobileOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/60 z-40 backdrop-blur-sm"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <aside
        className={`fixed lg:static inset-y-0 left-0 z-50 w-64 bg-gray-950 border-r border-gray-800 flex flex-col transform transition-transform duration-300 lg:transform-none ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        <SidebarContent onNavigate={() => setMobileOpen(false)} />
      </aside>
    </>
  )
}
