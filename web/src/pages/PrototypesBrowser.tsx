import { useEffect, useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { Hexagon, Search, X, ArrowUpDown, LayoutGrid, List, BarChart3, Layers, CheckSquare, Square, GitCompare } from 'lucide-react'
import { fetchPrototypes } from '../api/client'
import type { PrototypeListItem } from '../types'

const CRYSTAL_SYSTEMS = [
  { value: 'cubic', label: '立方' },
  { value: 'hexagonal', label: '六方' },
  { value: 'trigonal', label: '三方' },
  { value: 'tetragonal', label: '四方' },
  { value: 'orthorhombic', label: '正交' },
  { value: 'monoclinic', label: '单斜' },
  { value: 'triclinic', label: '三斜' },
]

type SortKey = 'raw_materials_count' | 'verified_materials_count' | 'space_group_number'
type SortDir = 'asc' | 'desc'
type ViewMode = 'card' | 'list'

export default function PrototypesBrowser() {
  const [prototypes, setPrototypes] = useState<PrototypeListItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedSystems, setSelectedSystems] = useState<string[]>([])
  const [sortKey, setSortKey] = useState<SortKey>('space_group_number')
  const [sortDir, setSortDir] = useState<SortDir>('asc')
  const [viewMode, setViewMode] = useState<ViewMode>('card')
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())

  useEffect(() => {
    fetchPrototypes()
      .then((res) => {
        setPrototypes(res.prototypes)
        setTotal(res.total)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const toggleSystem = (sys: string) => {
    setSelectedSystems(prev =>
      prev.includes(sys) ? prev.filter(s => s !== sys) : [...prev, sys]
    )
  }

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  const toggleSelect = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const filteredPrototypes = useMemo(() => {
    let result = [...prototypes]

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      result = result.filter(p =>
        p.prototype_id.toLowerCase().includes(q) ||
        p.ideal_space_group.toLowerCase().includes(q) ||
        String(p.space_group_number).includes(q)
      )
    }

    if (selectedSystems.length > 0) {
      result = result.filter(p => selectedSystems.includes(p.crystal_system))
    }

    result.sort((a, b) => {
      let cmp = 0
      switch (sortKey) {
        case 'raw_materials_count': cmp = a.raw_materials_count - b.raw_materials_count; break
        case 'verified_materials_count': cmp = a.verified_materials_count - b.verified_materials_count; break
        case 'space_group_number': cmp = a.space_group_number - b.space_group_number; break
      }
      return sortDir === 'asc' ? cmp : -cmp
    })

    return result
  }, [prototypes, searchQuery, selectedSystems, sortKey, sortDir])

  const stats = useMemo(() => {
    const totalRaw = prototypes.reduce((s, p) => s + p.raw_materials_count, 0)
    const totalVerified = prototypes.reduce((s, p) => s + p.verified_materials_count, 0)
    const totalReal = prototypes.reduce((s, p) => s + p.real_compounds_count, 0)
    const avgRate = prototypes.length > 0
      ? prototypes.reduce((s, p) => {
          const rate = p.raw_materials_count > 0 ? p.verified_materials_count / p.raw_materials_count : 0
          return s + rate
        }, 0) / prototypes.length * 100
      : 0
    return { totalRaw, totalVerified, totalReal, avgRate }
  }, [prototypes])

  const systemCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    prototypes.forEach(p => {
      counts[p.crystal_system] = (counts[p.crystal_system] || 0) + 1
    })
    return counts
  }, [prototypes])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      <div>
        <h1 className="text-base sm:text-lg font-bold text-white flex items-center gap-2 sm:gap-3">
          <Hexagon className="w-5 h-5 sm:w-7 sm:h-7 text-violet-400" />
          拓扑原型
        </h1>
        <p className="text-gray-400 mt-1">
          浏览晶体结构拓扑原型（共 {total} 个）
        </p>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-3 sm:p-4">
          <div className="flex items-center gap-2 mb-1">
            <Hexagon className="w-4 h-4 text-violet-400" />
            <p className="text-[10px] sm:text-xs text-gray-500">原型总数</p>
          </div>
          <p className="text-xl sm:text-2xl font-bold text-white">{total}</p>
        </div>
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-3 sm:p-4">
          <div className="flex items-center gap-2 mb-1">
            <Layers className="w-4 h-4 text-amber-400" />
            <p className="text-[10px] sm:text-xs text-gray-500">材料总数</p>
          </div>
          <p className="text-xl sm:text-2xl font-bold text-amber-400">{stats.totalRaw}</p>
        </div>
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-3 sm:p-4">
          <div className="flex items-center gap-2 mb-1">
            <BarChart3 className="w-4 h-4 text-emerald-400" />
            <p className="text-[10px] sm:text-xs text-gray-500">已验证材料</p>
          </div>
          <p className="text-xl sm:text-2xl font-bold text-emerald-400">{stats.totalVerified}</p>
        </div>
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-3 sm:p-4">
          <div className="flex items-center gap-2 mb-1">
            <BarChart3 className="w-4 h-4 text-cyan-400" />
            <p className="text-[10px] sm:text-xs text-gray-500">平均验证率</p>
          </div>
          <p className="text-xl sm:text-2xl font-bold text-cyan-400">{stats.avgRate.toFixed(1)}%</p>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
        <div className="w-full sm:flex-1 sm:min-w-[240px] relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="搜索原型编号、空间群..."
            className="w-full bg-gray-800 border border-gray-700 rounded-lg pl-9 pr-9 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-cyan-500"
          />
          {searchQuery && (
            <button onClick={() => setSearchQuery('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white">
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        <div className="flex items-center gap-1 w-full sm:w-auto overflow-x-auto scrollbar-none bg-gray-800/50 border border-gray-700/50 rounded-lg p-1">
          {CRYSTAL_SYSTEMS.map(cs => (
            <button
              key={cs.value}
              onClick={() => toggleSystem(cs.value)}
              className={`px-2.5 py-2 sm:py-1.5 rounded text-xs font-medium transition-colors whitespace-nowrap touch-manipulation ${
                selectedSystems.includes(cs.value)
                  ? 'bg-violet-500/20 text-violet-400'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              {cs.label}
              {systemCounts[cs.value] ? ` ${systemCounts[cs.value]}` : ''}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <span className="text-[10px] sm:text-xs text-gray-500">排序:</span>
          {([
            { key: 'space_group_number' as SortKey, label: '空间群' },
            { key: 'raw_materials_count' as SortKey, label: '材料数' },
            { key: 'verified_materials_count' as SortKey, label: '验证数' },
          ]).map(item => (
            <button
              key={item.key}
              onClick={() => handleSort(item.key)}
              className={`flex items-center gap-1 text-[10px] sm:text-xs font-medium transition-colors ${
                sortKey === item.key ? 'text-cyan-400' : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              {item.label}
              <ArrowUpDown className="w-3 h-3" />
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto justify-between sm:justify-start">
          <div className="flex items-center gap-1 bg-gray-800/50 border border-gray-700/50 rounded-lg p-0.5">
            <button
              onClick={() => setViewMode('card')}
              className={`p-2 rounded transition-colors min-w-[36px] min-h-[36px] flex items-center justify-center ${viewMode === 'card' ? 'bg-cyan-500/20 text-cyan-400' : 'text-gray-500 hover:text-white'}`}
            >
              <LayoutGrid className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-2 rounded transition-colors min-w-[36px] min-h-[36px] flex items-center justify-center ${viewMode === 'list' ? 'bg-cyan-500/20 text-cyan-400' : 'text-gray-500 hover:text-white'}`}
            >
              <List className="w-4 h-4" />
            </button>
          </div>

          {selectedIds.size >= 2 && (
            <Link
              to={`/compare?ids=${Array.from(selectedIds).join(',')}`}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-cyan-500 text-white font-medium hover:bg-cyan-400 transition-colors text-xs sm:text-sm"
            >
              <GitCompare className="w-4 h-4" />
              对比 ({selectedIds.size})
            </Link>
          )}
        </div>
      </div>

      {selectedSystems.length > 0 && (
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">已选晶系:</span>
          {selectedSystems.map(sys => (
            <button
              key={sys}
              onClick={() => toggleSystem(sys)}
              className="flex items-center gap-1 px-2 py-1 rounded bg-violet-500/20 text-violet-400 text-xs hover:bg-violet-500/30 transition-colors"
            >
              {CRYSTAL_SYSTEMS.find(c => c.value === sys)?.label || sys}
              <X className="w-3 h-3" />
            </button>
          ))}
          <button
            onClick={() => setSelectedSystems([])}
            className="text-xs text-gray-500 hover:text-white transition-colors"
          >
            清除
          </button>
        </div>
      )}

      {filteredPrototypes.length === 0 ? (
        <div className="text-center py-20 text-gray-500">
          <Hexagon className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>未找到匹配的原型</p>
        </div>
      ) : viewMode === 'card' ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
          {filteredPrototypes.map((p) => {
            const verifyRate = p.raw_materials_count > 0
              ? (p.verified_materials_count / p.raw_materials_count) * 100
              : 0
            return (
              <div
                key={p.id}
                className={`bg-gray-800/50 border rounded-xl p-3 sm:p-4 transition-all group ${
                  selectedIds.has(p.id)
                    ? 'border-cyan-500/50 bg-cyan-500/5'
                    : 'border-gray-700/50 hover:border-cyan-500/30'
                }`}
              >
                <div className="flex items-center justify-between mb-3">
                  <Link
                    to={`/prototypes/${p.id}`}
                    className="flex items-center gap-3 flex-1 min-w-0"
                  >
                    <Hexagon className="w-5 h-5 text-violet-400 flex-shrink-0" />
                    <span className="text-white font-medium group-hover:text-cyan-400 transition-colors text-sm truncate">
                      {p.prototype_id}
                    </span>
                  </Link>
                  <button onClick={() => toggleSelect(p.id)} className="flex-shrink-0 ml-2 touch-icon-btn">
                    {selectedIds.has(p.id)
                      ? <CheckSquare className="w-4 h-4 text-cyan-400" />
                      : <Square className="w-4 h-4 text-gray-600 hover:text-gray-400" />
                    }
                  </button>
                </div>

                <div className="flex items-center gap-2 mb-3">
                  <span className="px-2 py-0.5 rounded text-xs font-medium bg-violet-500/15 text-violet-400">
                    {p.crystal_system}
                  </span>
                  <span className="text-xs text-gray-400">
                    {p.ideal_space_group} (#{p.space_group_number})
                  </span>
                </div>

                <div className="space-y-2 text-sm mb-3">
                  <div className="flex justify-between">
                    <span className="text-gray-400">原始材料</span>
                    <span className="text-amber-400 font-medium">{p.raw_materials_count}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">已验证材料</span>
                    <span className="text-emerald-400 font-medium">{p.verified_materials_count}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">实际化合物</span>
                    <span className="text-violet-400 font-medium">{p.real_compounds_count}</span>
                  </div>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-gray-500">验证率</span>
                    <span className={`text-xs font-medium ${
                      verifyRate >= 80 ? 'text-emerald-400' : verifyRate >= 40 ? 'text-amber-400' : 'text-rose-400'
                    }`}>
                      {verifyRate.toFixed(1)}%
                    </span>
                  </div>
                  <div className="w-full h-2 sm:h-2.5 bg-gray-700/50 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${
                        verifyRate >= 80 ? 'bg-emerald-500' : verifyRate >= 40 ? 'bg-amber-500' : 'bg-rose-500'
                      }`}
                      style={{ width: `${Math.min(verifyRate, 100)}%` }}
                    />
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-700/50">
                <th className="px-3 py-3 w-10"></th>
                <th className="text-left px-3 py-3 text-xs font-medium text-gray-400 uppercase tracking-wider">
                  原型编号
                </th>
                <th className="text-left px-3 py-3 text-xs font-medium text-gray-400 uppercase tracking-wider">
                  晶系
                </th>
                <th className="text-left px-3 py-3 text-xs font-medium text-gray-400 uppercase tracking-wider">
                  空间群
                </th>
                <th className="text-left px-3 py-3 text-xs font-medium text-gray-400 uppercase tracking-wider">
                  原始材料
                </th>
                <th className="text-left px-3 py-3 text-xs font-medium text-gray-400 uppercase tracking-wider">
                  已验证
                </th>
                <th className="text-left px-3 py-3 text-xs font-medium text-gray-400 uppercase tracking-wider">
                  验证率
                </th>
                <th className="text-left px-3 py-3 text-xs font-medium text-gray-400 uppercase tracking-wider">
                  实际化合物
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700/30">
              {filteredPrototypes.map((p) => {
                const verifyRate = p.raw_materials_count > 0
                  ? (p.verified_materials_count / p.raw_materials_count) * 100
                  : 0
                return (
                  <tr key={p.id} className="hover:bg-gray-700/20 transition-colors">
                    <td className="px-3 py-3">
                      <button onClick={() => toggleSelect(p.id)} className="touch-icon-btn">
                        {selectedIds.has(p.id)
                          ? <CheckSquare className="w-4 h-4 text-cyan-400" />
                          : <Square className="w-4 h-4 text-gray-600 hover:text-gray-400" />
                        }
                      </button>
                    </td>
                    <td className="px-3 py-3">
                      <Link to={`/prototypes/${p.id}`} className="text-cyan-400 hover:text-cyan-300 font-medium text-sm">
                        {p.prototype_id}
                      </Link>
                    </td>
                    <td className="px-3 py-3">
                      <span className="px-2 py-0.5 rounded text-xs font-medium bg-violet-500/15 text-violet-400">
                        {p.crystal_system}
                      </span>
                    </td>
                    <td className="px-3 py-3 text-gray-300 text-sm">
                      {p.ideal_space_group} (#{p.space_group_number})
                    </td>
                    <td className="px-3 py-3 text-amber-400 text-sm font-medium">{p.raw_materials_count}</td>
                    <td className="px-3 py-3 text-emerald-400 text-sm font-medium">{p.verified_materials_count}</td>
                    <td className="px-3 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-2 sm:h-2.5 bg-gray-700/50 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              verifyRate >= 80 ? 'bg-emerald-500' : verifyRate >= 40 ? 'bg-amber-500' : 'bg-rose-500'
                            }`}
                            style={{ width: `${Math.min(verifyRate, 100)}%` }}
                          />
                        </div>
                        <span className={`text-xs font-medium ${
                          verifyRate >= 80 ? 'text-emerald-400' : verifyRate >= 40 ? 'text-amber-400' : 'text-rose-400'
                        }`}>
                          {verifyRate.toFixed(1)}%
                        </span>
                      </div>
                    </td>
                    <td className="px-3 py-3 text-violet-400 text-sm font-medium">{p.real_compounds_count}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      <div className="text-center text-xs text-gray-600">
        显示 {filteredPrototypes.length} / {total} 个原型
      </div>
    </div>
  )
}
