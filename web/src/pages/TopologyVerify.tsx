import { useState, useEffect, useMemo, useCallback } from 'react'
import { Link } from 'react-router-dom'
import {
  Shield, Search, X, CheckCircle, XCircle, Clock, AlertTriangle,
  ChevronLeft, ChevronRight, Filter, GitCompare, CheckSquare, Square,
  ArrowUpDown, Eye, RefreshCw
} from 'lucide-react'
import { fetchMaterials } from '../api/client'
import type { MaterialListItem } from '../types'

type VerifyStatus = 'all' | 'verified' | 'unverified' | 'pending'
type SortKey = 'formula' | 'topology' | 'space_group' | 'status'
type SortDir = 'asc' | 'desc'

const ELEMENT_COLORS: Record<string, string> = {
  H: '#ffffff', O: '#ff0d0d', F: '#90e050', N: '#3050f8', C: '#909090',
  B: '#ffb5b5', Si: '#f0c8a0', P: '#ff8000', S: '#ffff30', Cl: '#1ff01f',
  Li: '#cc80ff', Na: '#ab5cf2', K: '#8f40d4', Rb: '#702eb0', Cs: '#57178f',
  Be: '#c2ff00', Mg: '#8aff00', Ca: '#3dff00', Sr: '#00ff00', Ba: '#00c900',
  Ti: '#bfc2c7', V: '#a6a6ab', Cr: '#8a99c7', Mn: '#9c7ac7', Fe: '#e06633',
  Co: '#f090a0', Ni: '#50d050', Cu: '#c88033', Zn: '#7d80b0', Al: '#bfa6a6',
  Ga: '#c28f8f', In: '#a67573', Sn: '#668080', Pb: '#575961', Bi: '#9e4fb5',
}

function extractElements(formula: string): string[] {
  return formula.match(/[A-Z][a-z]?/g) || []
}

export default function TopologyVerify() {
  const [materials, setMaterials] = useState<MaterialListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [verifyStatus, setVerifyStatus] = useState<VerifyStatus>('all')
  const [sortKey, setSortKey] = useState<SortKey>('formula')
  const [sortDir, setSortDir] = useState<SortDir>('asc')
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [page, setPage] = useState(1)
  const [topologyFilter, setTopologyFilter] = useState('')
  const perPage = 20

  useEffect(() => {
    fetchMaterials({ page: '1', per_page: '500' })
      .then(data => setMaterials(data.materials || []))
      .catch(() => setMaterials([]))
      .finally(() => setLoading(false))
  }, [])

  const topologies = useMemo(() => {
    const set = new Set(materials.map(m => m.topology).filter(Boolean))
    return Array.from(set).sort()
  }, [materials])

  const filteredMaterials = useMemo(() => {
    let result = [...materials]

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      result = result.filter(m =>
        m.formula.toLowerCase().includes(q) ||
        m.space_group.toLowerCase().includes(q) ||
        m.topology?.toLowerCase().includes(q)
      )
    }

    if (topologyFilter) {
      result = result.filter(m => m.topology === topologyFilter)
    }

    switch (verifyStatus) {
      case 'verified': result = result.filter(m => m.verified); break
      case 'unverified': result = result.filter(m => !m.verified); break
    }

    result.sort((a, b) => {
      let cmp = 0
      switch (sortKey) {
        case 'formula': cmp = a.formula.localeCompare(b.formula); break
        case 'topology': cmp = (a.topology || '').localeCompare(b.topology || ''); break
        case 'space_group': cmp = a.space_group.localeCompare(b.space_group); break
        case 'status': cmp = Number(a.verified) - Number(b.verified); break
      }
      return sortDir === 'asc' ? cmp : -cmp
    })

    return result
  }, [materials, searchQuery, verifyStatus, topologyFilter, sortKey, sortDir])

  const stats = useMemo(() => ({
    total: materials.length,
    verified: materials.filter(m => m.verified).length,
    unverified: materials.filter(m => !m.verified).length,
    topologies: new Set(materials.map(m => m.topology).filter(Boolean)).size,
  }), [materials])

  const totalPages = Math.ceil(filteredMaterials.length / perPage)

  const toggleSelect = useCallback((id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }, [])

  const toggleSelectAll = useCallback(() => {
    const pageItems = filteredMaterials.slice((page - 1) * perPage, page * perPage)
    if (pageItems.every(m => selectedIds.has(m.material_id))) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(pageItems.map(m => m.material_id)))
    }
  }, [filteredMaterials, page, selectedIds])

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  const SortButton = ({ field, label }: { field: SortKey; label: string }) => (
    <button
      onClick={() => handleSort(field)}
      className={`flex items-center gap-1 text-xs font-medium transition-colors min-h-[36px] px-1 ${
        sortKey === field ? 'text-cyan-400' : 'text-gray-500 hover:text-gray-300'
      }`}
    >
      {label}
      <ArrowUpDown className="w-3 h-3" />
    </button>
  )

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-white flex items-center gap-2 sm:gap-3">
            <Shield className="w-6 h-6 sm:w-7 sm:h-7 text-cyan-400" />
            拓扑验证
          </h1>
          <p className="text-gray-400 mt-1 text-sm">
            查看和管理材料拓扑验证状态
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {selectedIds.size >= 2 && (
            <Link
              to={`/compare?ids=${Array.from(selectedIds).slice(0, 4).join(',')}`}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-cyan-500 text-white font-medium hover:bg-cyan-400 transition-colors text-sm"
            >
              <GitCompare className="w-4 h-4" />
              对比 ({selectedIds.size})
            </Link>
          )}
          <button
            onClick={() => {
              setLoading(true)
              fetchMaterials({ page: '1', per_page: '500' })
                .then(data => setMaterials(data.materials || []))
                .catch(() => setMaterials([]))
                .finally(() => setLoading(false))
            }}
            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-gray-300 hover:text-white hover:border-cyan-500/50 transition-colors text-sm"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            刷新
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4">
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-3 sm:p-4">
          <div className="flex items-center gap-2 sm:gap-3">
            <div className="p-1.5 sm:p-2 rounded-lg bg-cyan-500/10">
              <Eye className="w-4 h-4 sm:w-5 sm:h-5 text-cyan-400" />
            </div>
            <div>
              <p className="text-xs text-gray-500">材料总数</p>
              <p className="text-lg sm:text-xl font-bold text-white">{stats.total}</p>
            </div>
          </div>
        </div>
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-3 sm:p-4">
          <div className="flex items-center gap-2 sm:gap-3">
            <div className="p-1.5 sm:p-2 rounded-lg bg-emerald-500/10">
              <CheckCircle className="w-4 h-4 sm:w-5 sm:h-5 text-emerald-400" />
            </div>
            <div>
              <p className="text-xs text-gray-500">已验证</p>
              <p className="text-lg sm:text-xl font-bold text-emerald-400">{stats.verified}</p>
            </div>
          </div>
        </div>
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-3 sm:p-4">
          <div className="flex items-center gap-2 sm:gap-3">
            <div className="p-1.5 sm:p-2 rounded-lg bg-amber-500/10">
              <AlertTriangle className="w-4 h-4 sm:w-5 sm:h-5 text-amber-400" />
            </div>
            <div>
              <p className="text-xs text-gray-500">待验证</p>
              <p className="text-lg sm:text-xl font-bold text-amber-400">{stats.unverified}</p>
            </div>
          </div>
        </div>
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-3 sm:p-4">
          <div className="flex items-center gap-2 sm:gap-3">
            <div className="p-1.5 sm:p-2 rounded-lg bg-violet-500/10">
              <Shield className="w-4 h-4 sm:w-5 sm:h-5 text-violet-400" />
            </div>
            <div>
              <p className="text-xs text-gray-500">拓扑类型</p>
              <p className="text-lg sm:text-xl font-bold text-white">{stats.topologies}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
        <div className="flex items-center gap-1 bg-gray-800/50 border border-gray-700/50 rounded-lg p-1 self-start">
          {([
            { status: 'all' as VerifyStatus, label: '全部', icon: Eye },
            { status: 'verified' as VerifyStatus, label: '已验证', icon: CheckCircle },
            { status: 'unverified' as VerifyStatus, label: '待验证', icon: AlertTriangle },
          ]).map(({ status, label, icon: Icon }) => (
            <button
              key={status}
              onClick={() => { setVerifyStatus(status); setPage(1) }}
              className={`flex items-center gap-1.5 px-3 py-2 rounded text-xs font-medium transition-colors touch-manipulation ${
                verifyStatus === status
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
            onChange={(e) => { setSearchQuery(e.target.value); setPage(1) }}
            placeholder="搜索化学式、空间群、拓扑..."
            className="w-full bg-gray-800 border border-gray-700 rounded-lg pl-9 pr-9 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-cyan-500"
          />
          {searchQuery && (
            <button
              onClick={() => { setSearchQuery(''); setPage(1) }}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        <div className="flex items-center gap-2 self-start">
          <Filter className="w-4 h-4 text-gray-500" />
          <select
            value={topologyFilter}
            onChange={(e) => { setTopologyFilter(e.target.value); setPage(1) }}
            className="bg-gray-800 border border-gray-700 rounded-lg px-2 py-1.5 text-sm text-gray-200 focus:outline-none focus:border-cyan-500 max-w-[160px]"
          >
            <option value="">全部拓扑</option>
            {topologies.map(t => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="flex items-center gap-3 text-xs">
        <button
          onClick={toggleSelectAll}
          className="flex items-center gap-1.5 text-gray-400 hover:text-white transition-colors min-h-[36px]"
        >
          {(() => {
            const pageItems = filteredMaterials.slice((page - 1) * perPage, page * perPage)
            return pageItems.length > 0 && pageItems.every(m => selectedIds.has(m.material_id))
              ? <CheckSquare className="w-4 h-4 text-cyan-400" />
              : <Square className="w-4 h-4" />
          })()}
          全选当前页
        </button>
        <div className="flex items-center gap-2">
          <SortButton field="formula" label="化学式" />
          <SortButton field="topology" label="拓扑" />
          <SortButton field="space_group" label="空间群" />
          <SortButton field="status" label="状态" />
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : filteredMaterials.length === 0 ? (
        <div className="text-center py-20 text-gray-500">
          <Shield className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>没有匹配的材料</p>
          <p className="text-sm mt-2">尝试调整筛选条件</p>
        </div>
      ) : (
        <>
          <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-700/50">
                    <th className="px-2 py-1.5 sm:px-3 sm:py-3 w-10"></th>
                    <th className="text-left px-2 py-1.5 sm:px-3 sm:py-3 text-xs font-medium text-gray-400 uppercase tracking-wider">
                      化学式
                    </th>
                    <th className="text-left px-2 py-1.5 sm:px-3 sm:py-3 text-xs font-medium text-gray-400 uppercase tracking-wider hidden sm:table-cell">
                      元素
                    </th>
                    <th className="text-left px-2 py-1.5 sm:px-3 sm:py-3 text-xs font-medium text-gray-400 uppercase tracking-wider hidden md:table-cell">
                      空间群
                    </th>
                    <th className="text-left px-2 py-1.5 sm:px-3 sm:py-3 text-xs font-medium text-gray-400 uppercase tracking-wider hidden lg:table-cell">
                      拓扑
                    </th>
                    <th className="text-left px-2 py-1.5 sm:px-3 sm:py-3 text-xs font-medium text-gray-400 uppercase tracking-wider">
                      验证状态
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700/30">
                  {filteredMaterials.slice((page - 1) * perPage, page * perPage).map((m) => {
                    const els = extractElements(m.formula)
                    return (
                      <tr key={m.material_id} className="hover:bg-gray-700/20 transition-colors group">
                        <td className="px-2 py-1.5 sm:px-3 sm:py-3">
                          <button onClick={() => toggleSelect(m.material_id)} className="touch-icon-btn">
                            {selectedIds.has(m.material_id)
                              ? <CheckSquare className="w-4 h-4 text-cyan-400" />
                              : <Square className="w-4 h-4 text-gray-600 hover:text-gray-400" />
                            }
                          </button>
                        </td>
                        <td className="px-2 py-1.5 sm:px-3 sm:py-3">
                          <Link to={`/materials/${m.material_id}`} className="text-cyan-400 hover:text-cyan-300 font-medium text-sm">
                            {m.formula}
                          </Link>
                          <div className="sm:hidden text-xs text-gray-500 mt-0.5">{m.space_group}</div>
                        </td>
                        <td className="px-2 py-1.5 sm:px-3 sm:py-3 hidden sm:table-cell">
                          <div className="flex gap-1">
                            {els.slice(0, 5).map(el => (
                              <span
                                key={el}
                                className="w-6 h-6 sm:w-5 sm:h-5 rounded text-[10px] font-bold flex items-center justify-center"
                                style={{
                                  backgroundColor: (ELEMENT_COLORS[el] || '#888') + '25',
                                  color: ELEMENT_COLORS[el] || '#888'
                                }}
                              >
                                {el}
                              </span>
                            ))}
                            {els.length > 5 && <span className="text-xs text-gray-500 ml-1">+{els.length - 5}</span>}
                          </div>
                        </td>
                        <td className="px-2 py-1.5 sm:px-3 sm:py-3 text-gray-300 text-sm hidden md:table-cell">{m.space_group}</td>
                        <td className="px-2 py-1.5 sm:px-3 sm:py-3 text-gray-300 text-sm hidden lg:table-cell">{m.topology}</td>
                        <td className="px-2 py-1.5 sm:px-3 sm:py-3">
                          {m.verified ? (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-emerald-500/10 text-emerald-400">
                              <CheckCircle className="w-3 h-3" />
                              已验证
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-amber-500/10 text-amber-400">
                              <Clock className="w-3 h-3" />
                              待验证
                            </span>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="p-2.5 rounded-lg bg-gray-800 border border-gray-700 text-gray-300 hover:border-cyan-500/50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="text-sm text-gray-400">
                第 {page} 页 / 共 {totalPages} 页
              </span>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="p-2.5 rounded-lg bg-gray-800 border border-gray-700 text-gray-300 hover:border-cyan-500/50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </>
      )}

      <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-3 sm:p-5">
        <h3 className="text-xs sm:text-sm font-medium text-gray-400 mb-3 sm:mb-4 flex items-center gap-2">
          <Shield className="w-4 h-4 text-cyan-400" />
          验证进度
        </h3>
        <div className="space-y-3">
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs sm:text-sm text-gray-400">已验证比例</span>
              <span className="text-xs sm:text-sm font-medium text-white">
                {stats.total > 0 ? ((stats.verified / stats.total) * 100).toFixed(1) : 0}%
              </span>
            </div>
            <div className="h-2 bg-gray-900/50 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-cyan-500 to-emerald-500 rounded-full transition-all duration-500"
                style={{ width: `${stats.total > 0 ? (stats.verified / stats.total) * 100 : 0}%` }}
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:gap-4">
            <div className="flex items-center gap-2 p-2 sm:p-3 bg-gray-900/30 rounded-lg">
              <CheckCircle className="w-4 h-4 sm:w-5 sm:h-5 text-emerald-400 flex-shrink-0" />
              <div>
                <p className="text-sm sm:text-lg font-bold text-emerald-400">{stats.verified}</p>
                <p className="text-[10px] sm:text-xs text-gray-500">已验证</p>
              </div>
            </div>
            <div className="flex items-center gap-2 p-2 sm:p-3 bg-gray-900/30 rounded-lg">
              <XCircle className="w-4 h-4 sm:w-5 sm:h-5 text-amber-400 flex-shrink-0" />
              <div>
                <p className="text-sm sm:text-lg font-bold text-amber-400">{stats.unverified}</p>
                <p className="text-[10px] sm:text-xs text-gray-500">待验证</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
