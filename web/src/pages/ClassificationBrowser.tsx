import { useState, useEffect, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { Network, Search, X, ChevronRight, ChevronDown, Atom, Layers, Filter, BarChart3, Eye } from 'lucide-react'
import { fetchMaterials } from '../api/client'
import type { MaterialListItem } from '../types'

type ViewMode = 'topology' | 'element' | 'crystal_system'

interface TopologyGroup {
  topology: string
  materials: MaterialListItem[]
  count: number
  verifiedCount: number
}

interface ElementGroup {
  element: string
  materials: MaterialListItem[]
  count: number
  verifiedCount: number
}

interface CrystalSystemGroup {
  system: string
  label: string
  materials: MaterialListItem[]
  count: number
  verifiedCount: number
}

const CRYSTAL_SYSTEM_KEYWORDS: Record<string, string[]> = {
  cubic: ['Fm-3m', 'Fm3m', 'Pm-3m', 'Pm3m', 'Im-3m', 'Im3m', 'Fd-3m', 'Fd3m', 'Pn-3m', 'Pn3m', 'Pm-3', 'Pm3', 'Ia-3', 'Pa-3'],
  hexagonal: ['P6/mmm', 'P63/mmc', 'P6_3/mmc', 'P6_3mc', 'P6_3cm', 'P6_3/mcm', 'P-6m2', 'P-62m', 'P6mm', 'P6/m', 'P6_3/m'],
  trigonal: ['R-3m', 'R3m', 'R-3c', 'R3c', 'R-3', 'R3', 'P3m1', 'P-3m1', 'P31m', 'P312', 'P321'],
  tetragonal: ['I4/mmm', 'P4/mmm', 'I4/mcm', 'P4_2/mnm', 'P4_2/nmc', 'P4mm', 'I4mm', 'P4/m', 'I4/m', 'P4_2/m', 'I-42m', 'P-4m2', 'P-421m'],
  orthorhombic: ['Pnma', 'Pbam', 'Pcmn', 'Cmcm', 'Fmmm', 'Immm', 'Pmmm', 'Pnnm', 'Cccm', 'Amm2', 'Pma2', 'Cmc2_1'],
  monoclinic: ['P2_1/c', 'P2_1/m', 'C2/c', 'C2/m', 'P2/c', 'P2/m', 'I2/m', 'Cc', 'P2_1', 'C2'],
  triclinic: ['P-1', 'P1'],
}

const CRYSTAL_SYSTEM_LABELS: Record<string, string> = {
  cubic: '立方晶系',
  hexagonal: '六方晶系',
  trigonal: '三方晶系',
  tetragonal: '四方晶系',
  orthorhombic: '正交晶系',
  monoclinic: '单斜晶系',
  triclinic: '三斜晶系',
}

const ELEMENT_COLORS: Record<string, string> = {
  H: '#ffffff', O: '#ff0d0d', F: '#90e050', N: '#3050f8', C: '#909090',
  B: '#ffb5b5', Si: '#f0c8a0', P: '#ff8000', S: '#ffff30', Cl: '#1ff01f',
  Li: '#cc80ff', Na: '#ab5cf2', K: '#8f40d4', Rb: '#702eb0', Cs: '#57178f',
  Be: '#c2ff00', Mg: '#8aff00', Ca: '#3dff00', Sr: '#00ff00', Ba: '#00c900',
  Ti: '#bfc2c7', V: '#a6a6ab', Cr: '#8a99c7', Mn: '#9c7ac7', Fe: '#e06633',
  Co: '#f090a0', Ni: '#50d050', Cu: '#c88033', Zn: '#7d80b0', Al: '#bfa6a6',
}

function extractElements(formula: string): string[] {
  return formula.match(/[A-Z][a-z]?/g) || []
}

function detectCrystalSystem(spaceGroup: string): string | null {
  for (const [system, keywords] of Object.entries(CRYSTAL_SYSTEM_KEYWORDS)) {
    if (keywords.some(kw => spaceGroup.includes(kw))) {
      return system
    }
  }
  return null
}

export default function ClassificationBrowser() {
  const [materials, setMaterials] = useState<MaterialListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [viewMode, setViewMode] = useState<ViewMode>('topology')
  const [searchQuery, setSearchQuery] = useState('')
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set())
  const [minCount, setMinCount] = useState(1)

  useEffect(() => {
    fetchMaterials({ page: '1', per_page: '500' })
      .then(data => setMaterials(data.materials || []))
      .catch(() => setMaterials([]))
      .finally(() => setLoading(false))
  }, [])

  const toggleGroup = (key: string) => {
    setExpandedGroups(prev => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  const topologyGroups = useMemo((): TopologyGroup[] => {
    const map = new Map<string, MaterialListItem[]>()
    materials.forEach(m => {
      const topo = m.topology || '未知'
      if (!map.has(topo)) map.set(topo, [])
      map.get(topo)!.push(m)
    })
    let groups = Array.from(map.entries()).map(([topology, mats]) => ({
      topology,
      materials: mats,
      count: mats.length,
      verifiedCount: mats.filter(m => m.verified).length,
    }))
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      groups = groups.filter(g => g.topology.toLowerCase().includes(q))
    }
    return groups
      .filter(g => g.count >= minCount)
      .sort((a, b) => b.count - a.count)
  }, [materials, searchQuery, minCount])

  const elementGroups = useMemo((): ElementGroup[] => {
    const map = new Map<string, MaterialListItem[]>()
    materials.forEach(m => {
      extractElements(m.formula).forEach(el => {
        if (!map.has(el)) map.set(el, [])
        map.get(el)!.push(m)
      })
    })
    let groups = Array.from(map.entries()).map(([element, mats]) => ({
      element,
      materials: mats,
      count: mats.length,
      verifiedCount: mats.filter(m => m.verified).length,
    }))
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      groups = groups.filter(g => g.element.toLowerCase().includes(q))
    }
    return groups
      .filter(g => g.count >= minCount)
      .sort((a, b) => b.count - a.count)
  }, [materials, searchQuery, minCount])

  const crystalSystemGroups = useMemo((): CrystalSystemGroup[] => {
    const map = new Map<string, MaterialListItem[]>()
    materials.forEach(m => {
      const system = detectCrystalSystem(m.space_group) || 'other'
      if (!map.has(system)) map.set(system, [])
      map.get(system)!.push(m)
    })
    let groups = Array.from(map.entries()).map(([system, mats]) => ({
      system,
      label: CRYSTAL_SYSTEM_LABELS[system] || '其他',
      materials: mats,
      count: mats.length,
      verifiedCount: mats.filter(m => m.verified).length,
    }))
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      groups = groups.filter(g => g.label.toLowerCase().includes(q) || g.system.toLowerCase().includes(q))
    }
    return groups
      .filter(g => g.count >= minCount)
      .sort((a, b) => b.count - a.count)
  }, [materials, searchQuery, minCount])

  const stats = useMemo(() => {
    const topologies = new Set(materials.map(m => m.topology).filter(Boolean))
    const elements = new Set(materials.flatMap(m => extractElements(m.formula)))
    return {
      totalMaterials: materials.length,
      totalTopologies: topologies.size,
      totalElements: elements.size,
      verifiedCount: materials.filter(m => m.verified).length,
    }
  }, [materials])

  const maxCount = useMemo(() => {
    switch (viewMode) {
      case 'topology': return topologyGroups[0]?.count || 1
      case 'element': return elementGroups[0]?.count || 1
      case 'crystal_system': return crystalSystemGroups[0]?.count || 1
    }
  }, [viewMode, topologyGroups, elementGroups, crystalSystemGroups])

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-white flex items-center gap-2 sm:gap-3">
            <Network className="w-6 h-6 sm:w-7 sm:h-7 text-cyan-400" />
            分类浏览
          </h1>
          <p className="text-gray-400 mt-1 text-sm">
            按拓扑、元素、晶系浏览材料库
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4">
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-3 sm:p-4">
          <div className="flex items-center gap-2 sm:gap-3">
            <div className="p-1.5 sm:p-2 rounded-lg bg-cyan-500/10">
              <Atom className="w-4 h-4 sm:w-5 sm:h-5 text-cyan-400" />
            </div>
            <div>
              <p className="text-xs text-gray-500">材料总数</p>
              <p className="text-lg sm:text-xl font-bold text-white">{stats.totalMaterials}</p>
            </div>
          </div>
        </div>
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-3 sm:p-4">
          <div className="flex items-center gap-2 sm:gap-3">
            <div className="p-1.5 sm:p-2 rounded-lg bg-violet-500/10">
              <Network className="w-4 h-4 sm:w-5 sm:h-5 text-violet-400" />
            </div>
            <div>
              <p className="text-xs text-gray-500">拓扑类型</p>
              <p className="text-lg sm:text-xl font-bold text-white">{stats.totalTopologies}</p>
            </div>
          </div>
        </div>
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-3 sm:p-4">
          <div className="flex items-center gap-2 sm:gap-3">
            <div className="p-1.5 sm:p-2 rounded-lg bg-amber-500/10">
              <Layers className="w-4 h-4 sm:w-5 sm:h-5 text-amber-400" />
            </div>
            <div>
              <p className="text-xs text-gray-500">元素种类</p>
              <p className="text-lg sm:text-xl font-bold text-white">{stats.totalElements}</p>
            </div>
          </div>
        </div>
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-3 sm:p-4">
          <div className="flex items-center gap-2 sm:gap-3">
            <div className="p-1.5 sm:p-2 rounded-lg bg-emerald-500/10">
              <Eye className="w-4 h-4 sm:w-5 sm:h-5 text-emerald-400" />
            </div>
            <div>
              <p className="text-xs text-gray-500">已验证</p>
              <p className="text-lg sm:text-xl font-bold text-white">{stats.verifiedCount}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
        <div className="flex items-center gap-1 bg-gray-800/50 border border-gray-700/50 rounded-lg p-1 self-start">
          {([
            { mode: 'topology' as ViewMode, label: '拓扑', icon: Network },
            { mode: 'element' as ViewMode, label: '元素', icon: Atom },
            { mode: 'crystal_system' as ViewMode, label: '晶系', icon: Layers },
          ]).map(({ mode, label, icon: Icon }) => (
            <button
              key={mode}
              onClick={() => setViewMode(mode)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                viewMode === mode
                  ? 'bg-cyan-500/20 text-cyan-400'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {label}
            </button>
          ))}
        </div>

        <div className="flex-1 relative min-w-0">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="搜索分类..."
            className="w-full bg-gray-800 border border-gray-700 rounded-lg pl-9 pr-9 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-cyan-500"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        <div className="flex items-center gap-2 self-start">
          <Filter className="w-4 h-4 text-gray-500" />
          <select
            value={minCount}
            onChange={(e) => setMinCount(Number(e.target.value))}
            className="bg-gray-800 border border-gray-700 rounded-lg px-2 py-1.5 text-sm text-gray-200 focus:outline-none focus:border-cyan-500"
          >
            <option value={1}>≥1 个材料</option>
            <option value={2}>≥2 个材料</option>
            <option value={5}>≥5 个材料</option>
            <option value={10}>≥10 个材料</option>
          </select>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : viewMode === 'topology' ? (
        <div className="space-y-2">
          {topologyGroups.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <Network className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>没有匹配的拓扑分类</p>
            </div>
          ) : topologyGroups.map(group => {
            const isExpanded = expandedGroups.has(group.topology)
            const barWidth = (group.count / maxCount) * 100
            return (
              <div key={group.topology} className="bg-gray-800/50 border border-gray-700/50 rounded-xl overflow-hidden">
                <button
                  onClick={() => toggleGroup(group.topology)}
                  className="w-full flex items-center gap-2 sm:gap-3 px-3 sm:px-5 py-2.5 sm:py-3 hover:bg-gray-700/20 transition-colors"
                >
                  {isExpanded ? (
                    <ChevronDown className="w-4 h-4 text-gray-500 flex-shrink-0" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-gray-500 flex-shrink-0" />
                  )}
                  <div className="flex-1 min-w-0 text-left">
                    <div className="flex items-center gap-2">
                      <span className="text-cyan-400 font-medium text-sm truncate">{group.topology}</span>
                      <span className="text-xs text-gray-500 flex-shrink-0">({group.count})</span>
                      {group.verifiedCount > 0 && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 flex-shrink-0">
                          {group.verifiedCount} 已验证
                        </span>
                      )}
                    </div>
                    <div className="mt-1.5 h-1.5 bg-gray-900/50 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-cyan-500/60 rounded-full transition-all duration-500"
                        style={{ width: `${barWidth}%` }}
                      />
                    </div>
                  </div>
                </button>
                {isExpanded && (
                  <div className="border-t border-gray-700/50">
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead>
                          <tr className="border-b border-gray-700/30">
                            <th className="text-left px-3 sm:px-5 py-2 text-xs font-medium text-gray-500">化学式</th>
                            <th className="text-left px-3 sm:px-5 py-2 text-xs font-medium text-gray-500 hidden sm:table-cell">空间群</th>
                            <th className="text-left px-3 sm:px-5 py-2 text-xs font-medium text-gray-500 hidden md:table-cell">元素</th>
                            <th className="px-3 sm:px-5 py-2 text-xs font-medium text-gray-500">状态</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-700/20">
                          {group.materials.slice(0, 20).map(m => (
                            <tr key={m.material_id} className="hover:bg-gray-700/20 transition-colors">
                              <td className="px-3 sm:px-5 py-2">
                                <Link to={`/materials/${m.material_id}`} className="text-cyan-400 hover:text-cyan-300 text-sm font-medium">
                                  {m.formula}
                                </Link>
                                <div className="sm:hidden text-xs text-gray-500 mt-0.5">{m.space_group}</div>
                              </td>
                              <td className="px-3 sm:px-5 py-2 text-gray-300 text-sm hidden sm:table-cell">{m.space_group}</td>
                              <td className="px-3 sm:px-5 py-2 hidden md:table-cell">
                                <div className="flex gap-1">
                                  {extractElements(m.formula).slice(0, 4).map(el => (
                                    <span
                                      key={el}
                                      className="w-5 h-5 rounded text-[10px] font-bold flex items-center justify-center"
                                      style={{
                                        backgroundColor: (ELEMENT_COLORS[el] || '#888') + '25',
                                        color: ELEMENT_COLORS[el] || '#888'
                                      }}
                                    >
                                      {el}
                                    </span>
                                  ))}
                                </div>
                              </td>
                              <td className="px-3 sm:px-5 py-2">
                                <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                                  m.verified ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'
                                }`}>
                                  {m.verified ? '已验证' : '原始'}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    {group.materials.length > 20 && (
                      <div className="px-3 sm:px-5 py-2 border-t border-gray-700/30 text-center">
                        <span className="text-xs text-gray-500">
                          显示前 20 个，共 {group.materials.length} 个材料
                        </span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      ) : viewMode === 'element' ? (
        <div className="space-y-2">
          {elementGroups.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <Atom className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>没有匹配的元素分类</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2 sm:gap-3">
              {elementGroups.map(group => {
                const isExpanded = expandedGroups.has(group.element)
                const barWidth = (group.count / maxCount) * 100
                return (
                  <div key={group.element} className="bg-gray-800/50 border border-gray-700/50 rounded-xl overflow-hidden">
                    <button
                      onClick={() => toggleGroup(group.element)}
                      className="w-full p-2 sm:p-3 hover:bg-gray-700/20 transition-colors"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span
                          className="w-8 h-8 sm:w-10 sm:h-10 rounded-lg text-sm sm:text-base font-bold flex items-center justify-center"
                          style={{
                            backgroundColor: (ELEMENT_COLORS[group.element] || '#888') + '25',
                            color: ELEMENT_COLORS[group.element] || '#888'
                          }}
                        >
                          {group.element}
                        </span>
                        <span className="text-xs text-gray-500">{group.count}</span>
                      </div>
                      <div className="h-1.5 bg-gray-900/50 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all duration-500"
                          style={{
                            width: `${barWidth}%`,
                            backgroundColor: (ELEMENT_COLORS[group.element] || '#888') + '80',
                          }}
                        />
                      </div>
                      {group.verifiedCount > 0 && (
                        <p className="text-[10px] text-emerald-400 mt-1">{group.verifiedCount} 已验证</p>
                      )}
                    </button>
                    {isExpanded && (
                      <div className="border-t border-gray-700/50 p-2 sm:p-3 space-y-1.5 max-h-48 overflow-y-auto">
                        {group.materials.slice(0, 10).map(m => (
                          <Link
                            key={m.material_id}
                            to={`/materials/${m.material_id}`}
                            className="flex items-center justify-between gap-1 text-xs hover:text-cyan-400 transition-colors"
                          >
                            <span className="text-gray-300 truncate">{m.formula}</span>
                            <span className={`flex-shrink-0 w-1.5 h-1.5 rounded-full ${m.verified ? 'bg-emerald-400' : 'bg-amber-400'}`} />
                          </Link>
                        ))}
                        {group.materials.length > 10 && (
                          <p className="text-[10px] text-gray-600 text-center">
                            +{group.materials.length - 10} 更多
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-2">
          {crystalSystemGroups.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <Layers className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>没有匹配的晶系分类</p>
            </div>
          ) : crystalSystemGroups.map(group => {
            const isExpanded = expandedGroups.has(group.system)
            const barWidth = (group.count / maxCount) * 100
            return (
              <div key={group.system} className="bg-gray-800/50 border border-gray-700/50 rounded-xl overflow-hidden">
                <button
                  onClick={() => toggleGroup(group.system)}
                  className="w-full flex items-center gap-2 sm:gap-3 px-3 sm:px-5 py-2.5 sm:py-3 hover:bg-gray-700/20 transition-colors"
                >
                  {isExpanded ? (
                    <ChevronDown className="w-4 h-4 text-gray-500 flex-shrink-0" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-gray-500 flex-shrink-0" />
                  )}
                  <div className="flex-1 min-w-0 text-left">
                    <div className="flex items-center gap-2">
                      <span className="text-white font-medium text-sm">{group.label}</span>
                      <span className="text-xs text-gray-500 flex-shrink-0">({group.count})</span>
                      {group.verifiedCount > 0 && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 flex-shrink-0">
                          {group.verifiedCount} 已验证
                        </span>
                      )}
                    </div>
                    <div className="mt-1.5 h-1.5 bg-gray-900/50 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-violet-500/60 rounded-full transition-all duration-500"
                        style={{ width: `${barWidth}%` }}
                      />
                    </div>
                  </div>
                </button>
                {isExpanded && (
                  <div className="border-t border-gray-700/50">
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead>
                          <tr className="border-b border-gray-700/30">
                            <th className="text-left px-3 sm:px-5 py-2 text-xs font-medium text-gray-500">化学式</th>
                            <th className="text-left px-3 sm:px-5 py-2 text-xs font-medium text-gray-500 hidden sm:table-cell">空间群</th>
                            <th className="text-left px-3 sm:px-5 py-2 text-xs font-medium text-gray-500 hidden md:table-cell">拓扑</th>
                            <th className="px-3 sm:px-5 py-2 text-xs font-medium text-gray-500">状态</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-700/20">
                          {group.materials.slice(0, 20).map(m => (
                            <tr key={m.material_id} className="hover:bg-gray-700/20 transition-colors">
                              <td className="px-3 sm:px-5 py-2">
                                <Link to={`/materials/${m.material_id}`} className="text-cyan-400 hover:text-cyan-300 text-sm font-medium">
                                  {m.formula}
                                </Link>
                                <div className="sm:hidden text-xs text-gray-500 mt-0.5">{m.space_group}</div>
                              </td>
                              <td className="px-3 sm:px-5 py-2 text-gray-300 text-sm hidden sm:table-cell">{m.space_group}</td>
                              <td className="px-3 sm:px-5 py-2 text-gray-300 text-sm hidden md:table-cell">{m.topology}</td>
                              <td className="px-3 sm:px-5 py-2">
                                <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                                  m.verified ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'
                                }`}>
                                  {m.verified ? '已验证' : '原始'}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    {group.materials.length > 20 && (
                      <div className="px-3 sm:px-5 py-2 border-t border-gray-700/30 text-center">
                        <span className="text-xs text-gray-500">
                          显示前 20 个，共 {group.materials.length} 个材料
                        </span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-3 sm:p-5">
        <h3 className="text-xs sm:text-sm font-medium text-gray-400 mb-3 flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-cyan-400" />
          分类统计
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4">
          <div className="text-center p-3 bg-gray-900/30 rounded-lg">
            <p className="text-2xl font-bold text-cyan-400">{topologyGroups.length}</p>
            <p className="text-xs text-gray-500 mt-1">拓扑类型</p>
          </div>
          <div className="text-center p-3 bg-gray-900/30 rounded-lg">
            <p className="text-2xl font-bold text-amber-400">{elementGroups.length}</p>
            <p className="text-xs text-gray-500 mt-1">元素种类</p>
          </div>
          <div className="text-center p-3 bg-gray-900/30 rounded-lg">
            <p className="text-2xl font-bold text-violet-400">{crystalSystemGroups.length}</p>
            <p className="text-xs text-gray-500 mt-1">晶系</p>
          </div>
        </div>
      </div>
    </div>
  )
}
