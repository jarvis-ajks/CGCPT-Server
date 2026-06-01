import { useState, useEffect, useMemo, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Clock, Trash2, ArrowLeft, History, Search, Heart, GitCompare,
  List, AlignLeft, BarChart3, Flame, X, ChevronDown, ChevronRight,
  Star, TrendingUp, CalendarDays, Layers, Sparkles
} from 'lucide-react'
import { fetchMaterials } from '../api/client'
import type { MaterialListItem } from '../types'

interface RecentItem {
  materialId: string
  formula: string
  spaceGroup: string
  topology: string
  viewedAt: number
}

interface FavoriteItem {
  materialId: string
  formula: string
  spaceGroup: string
  topology: string
  addedAt: number
  elements: string[]
  verified: boolean
}

type DateGroup = 'today' | 'yesterday' | 'week' | 'earlier'
type ViewMode = 'list' | 'timeline'

const DATE_GROUP_LABELS: Record<DateGroup, string> = {
  today: '今天',
  yesterday: '昨天',
  week: '最近7天',
  earlier: '更早',
}

const DATE_GROUP_ORDER: DateGroup[] = ['today', 'yesterday', 'week', 'earlier']

function loadRecentItems(): RecentItem[] {
  try {
    const data = localStorage.getItem('cgcpt_recent')
    return data ? JSON.parse(data) : []
  } catch {
    return []
  }
}

function saveRecentItems(items: RecentItem[]): void {
  localStorage.setItem('cgcpt_recent', JSON.stringify(items))
}

function loadFavorites(): FavoriteItem[] {
  try {
    const data = localStorage.getItem('cgcpt_favorites')
    return data ? JSON.parse(data) : []
  } catch {
    return []
  }
}

function saveFavorites(items: FavoriteItem[]): void {
  localStorage.setItem('cgcpt_favorites', JSON.stringify(items))
}

function getDateGroup(timestamp: number): DateGroup {
  const now = new Date()
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
  const yesterdayStart = todayStart - 86400000
  const weekStart = todayStart - 6 * 86400000

  if (timestamp >= todayStart) return 'today'
  if (timestamp >= yesterdayStart) return 'yesterday'
  if (timestamp >= weekStart) return 'week'
  return 'earlier'
}

function formatTimeAgo(timestamp: number): string {
  const now = Date.now()
  const diff = now - timestamp
  const seconds = Math.floor(diff / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)

  if (seconds < 60) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  if (hours < 24) return `${hours}小时前`
  if (days === 1) return '昨天'
  if (days < 7) return `${days}天前`
  if (days < 30) return `${Math.floor(days / 7)}周前`
  if (days < 365) return `${Math.floor(days / 30)}个月前`
  return `${Math.floor(days / 365)}年前`
}

function formatDate(timestamp: number): string {
  const date = new Date(timestamp)
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatHourMinute(timestamp: number): string {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function isFavorite(materialId: string, favorites: FavoriteItem[]): boolean {
  return favorites.some(f => f.materialId === materialId)
}

function addToFavorites(item: RecentItem, favorites: FavoriteItem[], setFavorites: (items: FavoriteItem[]) => void): void {
  if (isFavorite(item.materialId, favorites)) return
  const newFav: FavoriteItem = {
    materialId: item.materialId,
    formula: item.formula,
    spaceGroup: item.spaceGroup,
    topology: item.topology,
    addedAt: Date.now(),
    elements: [],
    verified: false,
  }
  const updated = [...favorites, newFav]
  setFavorites(updated)
  saveFavorites(updated)
}

function removeFromFavorites(materialId: string, favorites: FavoriteItem[], setFavorites: (items: FavoriteItem[]) => void): void {
  const updated = favorites.filter(f => f.materialId !== materialId)
  setFavorites(updated)
  saveFavorites(updated)
}

function getHeatmapData(items: RecentItem[]): { date: string; count: number; dayOfWeek: number }[] {
  const now = new Date()
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const result: { date: string; count: number; dayOfWeek: number }[] = []

  for (let i = 83; i >= 0; i--) {
    const dayStart = new Date(todayStart.getTime() - i * 86400000)
    const dayEnd = new Date(dayStart.getTime() + 86400000)
    const count = items.filter(item => {
      const t = item.viewedAt
      return t >= dayStart.getTime() && t < dayEnd.getTime()
    }).length
    result.push({
      date: dayStart.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }),
      count,
      dayOfWeek: dayStart.getDay(),
    })
  }
  return result
}

function getHeatmapColor(count: number): string {
  if (count === 0) return 'bg-gray-800'
  if (count <= 2) return 'bg-cyan-900/60'
  if (count <= 5) return 'bg-cyan-700/70'
  if (count <= 10) return 'bg-cyan-500/80'
  return 'bg-cyan-400'
}

export default function RecentBrowse() {
  const navigate = useNavigate()
  const [recentItems, setRecentItems] = useState<RecentItem[]>(loadRecentItems)
  const [favorites, setFavorites] = useState<FavoriteItem[]>(loadFavorites)
  const [searchQuery, setSearchQuery] = useState('')
  const [viewMode, setViewMode] = useState<ViewMode>('list')
  const [showClearConfirm, setShowClearConfirm] = useState(false)
  const [collapsedGroups, setCollapsedGroups] = useState<Set<DateGroup>>(new Set())
  const [recommendations, setRecommendations] = useState<MaterialListItem[]>([])
  const [recLoading, setRecLoading] = useState(false)

  useEffect(() => {
    const handleStorage = () => {
      setRecentItems(loadRecentItems())
      setFavorites(loadFavorites())
    }
    window.addEventListener('storage', handleStorage)
    return () => window.removeEventListener('storage', handleStorage)
  }, [])

  const sortedItems = useMemo(
    () => [...recentItems].sort((a, b) => b.viewedAt - a.viewedAt),
    [recentItems]
  )

  const filteredItems = useMemo(() => {
    if (!searchQuery.trim()) return sortedItems
    const q = searchQuery.trim().toLowerCase()
    return sortedItems.filter(
      item =>
        item.formula.toLowerCase().includes(q) ||
        item.spaceGroup.toLowerCase().includes(q) ||
        item.topology.toLowerCase().includes(q)
    )
  }, [sortedItems, searchQuery])

  const groupedItems = useMemo(() => {
    const groups: Record<DateGroup, RecentItem[]> = { today: [], yesterday: [], week: [], earlier: [] }
    filteredItems.forEach(item => {
      const group = getDateGroup(item.viewedAt)
      groups[group].push(item)
    })
    return groups
  }, [filteredItems])

  const stats = useMemo(() => {
    const now = new Date()
    const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
    const todayCount = recentItems.filter(item => item.viewedAt >= todayStart).length

    const freqMap: Record<string, { item: RecentItem; count: number }> = {}
    recentItems.forEach(item => {
      if (!freqMap[item.materialId]) {
        freqMap[item.materialId] = { item, count: 0 }
      }
      freqMap[item.materialId].count++
    })
    const mostViewed = Object.values(freqMap).sort((a, b) => b.count - a.count).slice(0, 3)

    const topologySet = new Set(recentItems.map(item => item.topology))

    return {
      total: recentItems.length,
      todayCount,
      uniqueMaterials: Object.keys(freqMap).length,
      mostViewed,
      uniqueTopologies: topologySet.size,
    }
  }, [recentItems])

  const heatmapData = useMemo(() => getHeatmapData(recentItems), [recentItems])

  useEffect(() => {
    if (recentItems.length === 0) return
    const topologies = [...new Set(recentItems.map(item => item.topology))].slice(0, 3)
    if (topologies.length === 0) return

    let cancelled = false
    setRecLoading(true)

    Promise.all(
      topologies.map(topo =>
        fetchMaterials({ topology: topo, per_page: '3' })
          .then(data => data.materials || [])
          .catch(() => [] as MaterialListItem[])
      )
    ).then(results => {
      if (cancelled) return
      const viewedIds = new Set(recentItems.map(item => item.materialId))
      const all = results.flat()
      const unique = all.filter(
        (m, i, arr) => arr.findIndex(x => x.material_id === m.material_id) === i && !viewedIds.has(m.material_id)
      )
      setRecommendations(unique.slice(0, 6))
      setRecLoading(false)
    })

    return () => { cancelled = true }
  }, [recentItems])

  const removeItem = useCallback((materialId: string) => {
    const updated = recentItems.filter(item => item.materialId !== materialId)
    setRecentItems(updated)
    saveRecentItems(updated)
  }, [recentItems])

  const clearAll = useCallback(() => {
    setRecentItems([])
    saveRecentItems([])
    setShowClearConfirm(false)
  }, [])

  const toggleFavorite = useCallback((item: RecentItem) => {
    if (isFavorite(item.materialId, favorites)) {
      removeFromFavorites(item.materialId, favorites, setFavorites)
    } else {
      addToFavorites(item, favorites, setFavorites)
    }
  }, [favorites])

  const toggleGroup = useCallback((group: DateGroup) => {
    setCollapsedGroups(prev => {
      const next = new Set(prev)
      if (next.has(group)) next.delete(group)
      else next.add(group)
      return next
    })
  }, [])

  const handleCompare = useCallback((materialId: string) => {
    navigate(`/compare?add=${encodeURIComponent(materialId)}`)
  }, [navigate])

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3 sm:gap-4">
          <button
            onClick={() => navigate('/materials')}
            className="p-2 rounded-lg bg-gray-800 border border-gray-700 text-gray-400 hover:text-white hover:border-cyan-500/50 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-white flex items-center gap-2 sm:gap-3">
              <Clock className="w-6 h-6 sm:w-7 sm:h-7 text-cyan-400" />
              最近浏览
            </h1>
            <p className="text-gray-400 mt-1 text-sm">
              共浏览 {stats.uniqueMaterials} 个材料，{stats.total} 条记录
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex bg-gray-800 border border-gray-700 rounded-lg overflow-hidden">
            <button
              onClick={() => setViewMode('list')}
              className={`p-2 rounded transition-colors min-w-[36px] min-h-[36px] flex items-center justify-center ${viewMode === 'list' ? 'bg-cyan-500/20 text-cyan-400' : 'text-gray-400 hover:text-white'}`}
              title="列表视图"
            >
              <List className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode('timeline')}
              className={`p-2 rounded transition-colors min-w-[36px] min-h-[36px] flex items-center justify-center ${viewMode === 'timeline' ? 'bg-cyan-500/20 text-cyan-400' : 'text-gray-400 hover:text-white'}`}
              title="时间线视图"
            >
              <AlignLeft className="w-4 h-4" />
            </button>
          </div>
          {recentItems.length > 0 && (
            <button
              onClick={() => setShowClearConfirm(true)}
              className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-gray-300 hover:text-white hover:border-red-500/50 transition-colors text-sm"
            >
              <Trash2 className="w-4 h-4" />
              清空全部
            </button>
          )}
        </div>
      </div>

      {showClearConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 max-w-md w-[90%] sm:w-full mx-4 shadow-2xl">
            <h3 className="text-lg font-semibold text-white mb-2">确认清空浏览记录</h3>
            <p className="text-gray-400 mb-6">此操作将删除所有浏览记录，且无法恢复。确定要继续吗？</p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowClearConfirm(false)}
                className="px-4 py-2 rounded-lg bg-gray-800 border border-gray-700 text-gray-300 hover:text-white transition-colors text-sm"
              >
                取消
              </button>
              <button
                onClick={clearAll}
                className="px-4 py-2 rounded-lg bg-red-500/20 border border-red-500/50 text-red-400 hover:bg-red-500/30 transition-colors text-sm font-medium"
              >
                确认清空
              </button>
            </div>
          </div>
        </div>
      )}

      {recentItems.length > 0 && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4">
            <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-3 sm:p-4">
              <div className="flex items-center gap-2 sm:gap-3">
                <div className="p-1.5 sm:p-2 rounded-lg bg-cyan-500/10">
                  <BarChart3 className="w-4 h-4 sm:w-5 sm:h-5 text-cyan-400" />
                </div>
                <div>
                  <p className="text-xs text-gray-500">总浏览数</p>
                  <p className="text-lg sm:text-xl font-bold text-white">{stats.total}</p>
                </div>
              </div>
            </div>
            <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-3 sm:p-4">
              <div className="flex items-center gap-2 sm:gap-3">
                <div className="p-1.5 sm:p-2 rounded-lg bg-emerald-500/10">
                  <CalendarDays className="w-4 h-4 sm:w-5 sm:h-5 text-emerald-400" />
                </div>
                <div>
                  <p className="text-xs text-gray-500">今日浏览</p>
                  <p className="text-lg sm:text-xl font-bold text-white">{stats.todayCount}</p>
                </div>
              </div>
            </div>
            <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-3 sm:p-4">
              <div className="flex items-center gap-2 sm:gap-3">
                <div className="p-1.5 sm:p-2 rounded-lg bg-violet-500/10">
                  <Layers className="w-4 h-4 sm:w-5 sm:h-5 text-violet-400" />
                </div>
                <div>
                  <p className="text-xs text-gray-500">不同材料</p>
                  <p className="text-lg sm:text-xl font-bold text-white">{stats.uniqueMaterials}</p>
                </div>
              </div>
            </div>
            <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-3 sm:p-4">
              <div className="flex items-center gap-2 sm:gap-3">
                <div className="p-1.5 sm:p-2 rounded-lg bg-amber-500/10">
                  <TrendingUp className="w-4 h-4 sm:w-5 sm:h-5 text-amber-400" />
                </div>
                <div>
                  <p className="text-xs text-gray-500">涉及拓扑</p>
                  <p className="text-lg sm:text-xl font-bold text-white">{stats.uniqueTopologies}</p>
                </div>
              </div>
            </div>
          </div>

          {stats.mostViewed.length > 0 && (
            <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-3 sm:p-5">
              <h3 className="text-xs sm:text-sm font-medium text-gray-400 mb-3 flex items-center gap-2">
                <Flame className="w-4 h-4 text-orange-400" />
                最常浏览
              </h3>
              <div className="flex flex-wrap gap-2 sm:gap-3">
                {stats.mostViewed.map(({ item, count }) => (
                  <button
                    key={item.materialId}
                    onClick={() => navigate(`/materials/${item.materialId}`)}
                    className="flex items-center gap-2 px-2.5 py-1.5 sm:px-3 sm:py-2 rounded-lg bg-gray-700/50 border border-gray-600/50 hover:border-cyan-500/50 transition-colors"
                  >
                    <span className="text-cyan-400 font-medium text-sm">{item.formula}</span>
                    <span className="text-xs text-gray-500 hidden sm:inline">{item.topology}</span>
                    <span className="text-xs px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-400 font-medium">
                      {count}次
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-3 sm:p-5">
            <h3 className="text-xs sm:text-sm font-medium text-gray-400 mb-3 flex items-center gap-2">
              <Star className="w-4 h-4 text-yellow-400" />
              浏览热力图
              <span className="text-xs text-gray-600 ml-2">近12周</span>
            </h3>
            <div className="overflow-x-auto">
              <div className="inline-flex flex-col gap-[2px] sm:gap-[3px] min-w-fit">
                {(() => {
                  const weeks: typeof heatmapData[] = []
                  for (let w = 0; w < 12; w++) {
                    weeks.push(heatmapData.slice(w * 7, (w + 1) * 7))
                  }
                  const rows: { cells: typeof heatmapData; label: string }[] = []
                  const dayLabels = ['日', '一', '二', '三', '四', '五', '六']
                  for (let d = 0; d < 7; d++) {
                    const cells = weeks.map(w => w[d]).filter(Boolean)
                    rows.push({ cells, label: dayLabels[d] })
                  }
                  return rows.map((row, ri) => (
                    <div key={ri} className="flex items-center gap-[2px] sm:gap-[3px]">
                      <span className="text-[8px] sm:text-[10px] text-gray-600 w-3 sm:w-4 text-right mr-0.5 sm:mr-1">{ri % 2 === 1 ? row.label : ''}</span>
                      {row.cells.map((cell, ci) => (
                        <div
                          key={ci}
                          className={`w-[10px] h-[10px] sm:w-[14px] sm:h-[14px] rounded-[2px] sm:rounded-[3px] ${getHeatmapColor(cell.count)} transition-colors`}
                          title={`${cell.date}: ${cell.count} 次浏览`}
                        />
                      ))}
                    </div>
                  ))
                })()}
              </div>
              <div className="flex items-center gap-1.5 sm:gap-2 mt-2 sm:mt-3">
                <span className="text-[10px] sm:text-xs text-gray-600">少</span>
                <div className="w-[10px] h-[10px] sm:w-[14px] sm:h-[14px] rounded-[2px] sm:rounded-[3px] bg-gray-800" />
                <div className="w-[10px] h-[10px] sm:w-[14px] sm:h-[14px] rounded-[2px] sm:rounded-[3px] bg-cyan-900/60" />
                <div className="w-[10px] h-[10px] sm:w-[14px] sm:h-[14px] rounded-[2px] sm:rounded-[3px] bg-cyan-700/70" />
                <div className="w-[10px] h-[10px] sm:w-[14px] sm:h-[14px] rounded-[2px] sm:rounded-[3px] bg-cyan-500/80" />
                <div className="w-[10px] h-[10px] sm:w-[14px] sm:h-[14px] rounded-[2px] sm:rounded-[3px] bg-cyan-400" />
                <span className="text-[10px] sm:text-xs text-gray-600">多</span>
              </div>
            </div>
          </div>
        </>
      )}

      {recentItems.length > 0 && (
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder="搜索化学式、空间群、拓扑..."
            className="w-full pl-10 pr-10 py-2.5 rounded-lg bg-gray-800 border border-gray-700 text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500/50 transition-colors text-sm"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      )}

      {recentItems.length === 0 ? (
        <div className="text-center py-20">
          <History className="w-16 h-16 mx-auto mb-4 text-gray-600" />
          <h2 className="text-xl font-medium text-gray-400 mb-2">暂无浏览记录</h2>
          <p className="text-gray-500 mb-6">浏览材料详情页后会自动记录在这里</p>
          <button
            onClick={() => navigate('/materials')}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-cyan-500 text-white font-medium hover:bg-cyan-400 transition-colors"
          >
            浏览材料库
          </button>
        </div>
      ) : filteredItems.length === 0 ? (
        <div className="text-center py-12">
          <Search className="w-12 h-12 mx-auto mb-3 text-gray-600" />
          <p className="text-gray-400">没有找到匹配的记录</p>
          <button
            onClick={() => setSearchQuery('')}
            className="mt-3 text-cyan-400 hover:text-cyan-300 text-sm transition-colors"
          >
            清除搜索条件
          </button>
        </div>
      ) : viewMode === 'list' ? (
        <div className="space-y-4">
          {DATE_GROUP_ORDER.map(group => {
            const items = groupedItems[group]
            if (items.length === 0) return null
            const isCollapsed = collapsedGroups.has(group)
            return (
              <div key={group} className="bg-gray-800/50 border border-gray-700/50 rounded-xl overflow-hidden">
                <button
                  onClick={() => toggleGroup(group)}
                  className="w-full flex items-center justify-between px-3 sm:px-5 py-2.5 sm:py-3 hover:bg-gray-700/20 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    {isCollapsed ? (
                      <ChevronRight className="w-4 h-4 text-gray-500" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-gray-500" />
                    )}
                    <span className="text-sm font-medium text-gray-300">{DATE_GROUP_LABELS[group]}</span>
                    <span className="text-xs text-gray-600">({items.length})</span>
                  </div>
                </button>
                {!isCollapsed && (
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="border-t border-b border-gray-700/50">
                          <th className="text-left px-3 sm:px-5 py-2 text-xs font-medium text-gray-500 uppercase tracking-wider">化学式</th>
                          <th className="text-left px-3 sm:px-5 py-2 text-xs font-medium text-gray-500 uppercase tracking-wider hidden sm:table-cell">空间群</th>
                          <th className="text-left px-3 sm:px-5 py-2 text-xs font-medium text-gray-500 uppercase tracking-wider hidden sm:table-cell">拓扑</th>
                          <th className="text-left px-3 sm:px-5 py-2 text-xs font-medium text-gray-500 uppercase tracking-wider">时间</th>
                          <th className="px-3 sm:px-5 py-2 text-xs font-medium text-gray-500 uppercase tracking-wider text-right">操作</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-700/30">
                        {items.map(item => {
                          const fav = isFavorite(item.materialId, favorites)
                          return (
                            <tr key={`${item.materialId}-${item.viewedAt}`} className="hover:bg-gray-700/20 transition-colors group">
                              <td className="px-3 sm:px-5 py-2 sm:py-3">
                                <button
                                  onClick={() => navigate(`/materials/${item.materialId}`)}
                                  className="text-cyan-400 hover:text-cyan-300 font-medium text-sm"
                                >
                                  {item.formula}
                                </button>
                                <div className="sm:hidden text-xs text-gray-500 mt-0.5">{item.spaceGroup} · {item.topology}</div>
                              </td>
                              <td className="px-3 sm:px-5 py-2 sm:py-3 text-gray-300 text-sm hidden sm:table-cell">{item.spaceGroup}</td>
                              <td className="px-3 sm:px-5 py-2 sm:py-3 text-gray-300 text-sm hidden sm:table-cell">{item.topology}</td>
                              <td className="px-3 sm:px-5 py-2 sm:py-3">
                                <span className="text-sm text-gray-400" title={formatDate(item.viewedAt)}>
                                  {group === 'today' ? formatHourMinute(item.viewedAt) : formatTimeAgo(item.viewedAt)}
                                </span>
                              </td>
                              <td className="px-3 sm:px-5 py-2 sm:py-3">
                                <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                  <button
                                    onClick={() => toggleFavorite(item)}
                                    className={`p-1.5 rounded-lg transition-colors ${fav ? 'text-rose-400 hover:bg-rose-500/10' : 'text-gray-500 hover:text-rose-400 hover:bg-rose-500/10'}`}
                                    title={fav ? '取消收藏' : '添加到收藏'}
                                  >
                                    <Heart className={`w-4 h-4 ${fav ? 'fill-current' : ''}`} />
                                  </button>
                                  <button
                                    onClick={() => handleCompare(item.materialId)}
                                    className="p-1.5 rounded-lg text-gray-500 hover:text-cyan-400 hover:bg-cyan-500/10 transition-colors"
                                    title="添加到对比"
                                  >
                                    <GitCompare className="w-4 h-4" />
                                  </button>
                                  <button
                                    onClick={() => removeItem(item.materialId)}
                                    className="p-1.5 rounded-lg text-gray-500 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                                    title="删除记录"
                                  >
                                    <Trash2 className="w-4 h-4" />
                                  </button>
                                </div>
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      ) : (
        <div className="space-y-4">
          {DATE_GROUP_ORDER.map(group => {
            const items = groupedItems[group]
            if (items.length === 0) return null
            const isCollapsed = collapsedGroups.has(group)
            return (
              <div key={group}>
                <button
                  onClick={() => toggleGroup(group)}
                  className="flex items-center gap-2 mb-3"
                >
                  {isCollapsed ? (
                    <ChevronRight className="w-4 h-4 text-gray-500" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-gray-500" />
                  )}
                  <span className="text-sm font-medium text-gray-300">{DATE_GROUP_LABELS[group]}</span>
                  <span className="text-xs text-gray-600">({items.length})</span>
                </button>
                {!isCollapsed && (
                  <div className="relative pl-4 sm:pl-6 border-l-2 border-gray-700/50 ml-2 space-y-3">
                    {items.map(item => {
                      const fav = isFavorite(item.materialId, favorites)
                      return (
                        <div key={`${item.materialId}-${item.viewedAt}`} className="relative group">
                          <div className="absolute -left-[21px] sm:-left-[25px] top-3 w-3 h-3 rounded-full bg-gray-700 border-2 border-gray-600 group-hover:border-cyan-400 transition-colors" />
                          <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-3 sm:p-4 hover:border-cyan-500/30 transition-colors">
                            <div className="flex items-start justify-between">
                              <div className="flex-1">
                                <button
                                  onClick={() => navigate(`/materials/${item.materialId}`)}
                                  className="text-cyan-400 hover:text-cyan-300 font-medium text-sm"
                                >
                                  {item.formula}
                                </button>
                                <div className="flex items-center gap-3 mt-1.5">
                                  <span className="text-xs text-gray-500">{item.spaceGroup}</span>
                                  <span className="text-xs text-gray-600">·</span>
                                  <span className="text-xs text-gray-500">{item.topology}</span>
                                </div>
                              </div>
                              <div className="flex items-center gap-2 sm:gap-3">
                                <span className="text-xs text-gray-500 hidden sm:inline" title={formatDate(item.viewedAt)}>
                                  {group === 'today' ? formatHourMinute(item.viewedAt) : formatTimeAgo(item.viewedAt)}
                                </span>
                                <div className="flex items-center gap-1">
                                  <button
                                    onClick={() => toggleFavorite(item)}
                                    className={`touch-icon-btn rounded-lg transition-colors ${fav ? 'text-rose-400 hover:bg-rose-500/10' : 'text-gray-500 hover:text-rose-400 hover:bg-rose-500/10'}`}
                                    title={fav ? '取消收藏' : '添加到收藏'}
                                  >
                                    <Heart className={`w-4 h-4 ${fav ? 'fill-current' : ''}`} />
                                  </button>
                                  <button
                                    onClick={() => handleCompare(item.materialId)}
                                    className="touch-icon-btn rounded-lg text-gray-500 hover:text-cyan-400 hover:bg-cyan-500/10 transition-colors"
                                    title="添加到对比"
                                  >
                                    <GitCompare className="w-4 h-4" />
                                  </button>
                                  <button
                                    onClick={() => removeItem(item.materialId)}
                                    className="touch-icon-btn rounded-lg text-gray-500 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                                    title="删除记录"
                                  >
                                    <Trash2 className="w-4 h-4" />
                                  </button>
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {recentItems.length > 0 && (recommendations.length > 0 || recLoading) && (
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-3 sm:p-5">
          <h3 className="text-xs sm:text-sm font-medium text-gray-400 mb-3 sm:mb-4 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-amber-400" />
            继续浏览推荐
            <span className="text-xs text-gray-600 hidden sm:inline">基于最近浏览的拓扑类型</span>
          </h3>
          {recLoading ? (
            <div className="flex items-center gap-2 text-gray-500 text-sm">
              <div className="w-4 h-4 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
              正在加载推荐...
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {recommendations.map(mat => (
                <button
                  key={mat.material_id}
                  onClick={() => navigate(`/materials/${mat.material_id}`)}
                  className="text-left bg-gray-700/30 border border-gray-600/30 rounded-lg p-3 hover:border-cyan-500/50 transition-colors group"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-cyan-400 font-medium text-sm group-hover:text-cyan-300 transition-colors">
                      {mat.formula}
                    </span>
                    {mat.verified && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        已验证
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 mt-1.5">
                    <span className="text-xs text-gray-500">{mat.space_group}</span>
                    <span className="text-xs text-gray-600">·</span>
                    <span className="text-xs text-gray-500">{mat.topology}</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
