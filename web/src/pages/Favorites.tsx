import { useState, useMemo, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Heart, Trash2, Atom, Search, ArrowUpDown, CheckSquare, Square, GitCompare, Download, X } from 'lucide-react'

interface FavoriteItem {
  materialId: string
  formula: string
  spaceGroup: string
  topology: string
  addedAt: number
  elements: string[]
  verified: boolean
}

const ELEMENT_COLORS: Record<string, string> = {
  H: '#ffffff', O: '#ff0d0d', F: '#90e050', N: '#3050f8', C: '#909090',
  B: '#ffb5b5', Si: '#f0c8a0', P: '#ff8000', S: '#ffff30', Cl: '#1ff01f',
  Li: '#cc80ff', Na: '#ab5cf2', K: '#8f40d4', Rb: '#702eb0', Cs: '#57178f',
  Be: '#c2ff00', Mg: '#8aff00', Ca: '#3dff00', Sr: '#00ff00', Ba: '#00c900',
  Ti: '#bfc2c7', V: '#a6a6ab', Cr: '#8a99c7', Mn: '#9c7ac7', Fe: '#e06633',
  Co: '#f090a0', Ni: '#50d050', Cu: '#c88033', Zn: '#7d80b0', Al: '#bfa6a6',
  Ga: '#c28f8f', In: '#a67573', Sn: '#668080', Pb: '#575961', Bi: '#9e4fb5',
}

type SortKey = 'addedAt' | 'formula' | 'spaceGroup'
type SortDir = 'asc' | 'desc'
type FilterStatus = 'all' | 'verified' | 'raw'

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

export default function Favorites() {
  const [favorites, setFavorites] = useState<FavoriteItem[]>(loadFavorites)
  const [searchQuery, setSearchQuery] = useState('')
  const [sortKey, setSortKey] = useState<SortKey>('addedAt')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const [filterStatus, setFilterStatus] = useState<FilterStatus>('all')
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [showClearConfirm, setShowClearConfirm] = useState(false)
  const navigate = useNavigate()

  const removeFavorite = useCallback((materialId: string) => {
    const updated = favorites.filter(f => f.materialId !== materialId)
    setFavorites(updated)
    saveFavorites(updated)
    setSelectedIds(prev => {
      const next = new Set(prev)
      next.delete(materialId)
      return next
    })
  }, [favorites])

  const clearAll = () => {
    setFavorites([])
    saveFavorites([])
    setSelectedIds(new Set())
    setShowClearConfirm(false)
  }

  const toggleSelect = (materialId: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(materialId)) next.delete(materialId)
      else next.add(materialId)
      return next
    })
  }

  const toggleSelectAll = () => {
    if (selectedIds.size === filteredFavorites.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(filteredFavorites.map(f => f.materialId)))
    }
  }

  const batchDelete = () => {
    const updated = favorites.filter(f => !selectedIds.has(f.materialId))
    setFavorites(updated)
    saveFavorites(updated)
    setSelectedIds(new Set())
  }

  const handleCompare = () => {
    const ids = Array.from(selectedIds).slice(0, 4)
    if (ids.length < 2) return
    navigate(`/compare?ids=${ids.join(',')}`)
  }

  const exportFavorites = () => {
    const data = favorites.map(f => ({
      材料编号: f.materialId,
      化学式: f.formula,
      空间群: f.spaceGroup,
      拓扑: f.topology,
      元素: f.elements?.join(', ') || '',
      验证状态: f.verified ? '已验证' : '原始',
      收藏时间: new Date(f.addedAt).toLocaleString('zh-CN'),
    }))
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `cgcpt_favorites_${new Date().toISOString().slice(0, 10)}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  const filteredFavorites = useMemo(() => {
    let result = [...favorites]

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      result = result.filter(f =>
        f.formula.toLowerCase().includes(q) ||
        f.spaceGroup.toLowerCase().includes(q) ||
        f.topology.toLowerCase().includes(q)
      )
    }

    if (filterStatus === 'verified') result = result.filter(f => f.verified)
    if (filterStatus === 'raw') result = result.filter(f => !f.verified)

    result.sort((a, b) => {
      let cmp = 0
      switch (sortKey) {
        case 'addedAt': cmp = a.addedAt - b.addedAt; break
        case 'formula': cmp = a.formula.localeCompare(b.formula); break
        case 'spaceGroup': cmp = a.spaceGroup.localeCompare(b.spaceGroup); break
      }
      return sortDir === 'asc' ? cmp : -cmp
    })

    return result
  }, [favorites, searchQuery, filterStatus, sortKey, sortDir])

  const stats = useMemo(() => ({
    total: favorites.length,
    verified: favorites.filter(f => f.verified).length,
    elementDist: Object.entries(
      favorites.reduce<Record<string, number>>((acc, f) => {
        (f.elements || []).forEach(el => { acc[el] = (acc[el] || 0) + 1 })
        return acc
      }, {})
    ).sort((a, b) => b[1] - a[1]).slice(0, 8),
  }), [favorites])

  const formatDate = (timestamp: number) => {
    return new Date(timestamp).toLocaleDateString('zh-CN', {
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
    })
  }

  const SortButton = ({ field, label }: { field: SortKey; label: string }) => (
    <button
      onClick={() => handleSort(field)}
      className={`flex items-center gap-1 text-xs font-medium transition-colors ${
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
          <h1 className="text-xl sm:text-2xl font-bold text-white flex items-center gap-3">
            <Heart className="w-6 h-6 sm:w-7 sm:h-7 text-rose-400" />
            我的收藏
          </h1>
          <p className="text-gray-400 mt-1 text-sm">已收藏 {favorites.length} 个材料</p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {selectedIds.size > 0 && (
            <>
              <button
                onClick={handleCompare}
                disabled={selectedIds.size < 2}
                className="flex items-center gap-1.5 px-2.5 py-1.5 sm:px-3 sm:py-2 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 text-sm hover:bg-cyan-500/20 disabled:opacity-40 transition-colors"
              >
                <GitCompare className="w-4 h-4" />
                对比 ({selectedIds.size})
              </button>
              <button
                onClick={batchDelete}
                className="flex items-center gap-1.5 px-2.5 py-1.5 sm:px-3 sm:py-2 rounded-lg bg-red-500/10 text-red-400 border border-red-500/30 text-sm hover:bg-red-500/20 transition-colors"
              >
                <Trash2 className="w-4 h-4" />
                删除选中
              </button>
            </>
          )}
          <button
            onClick={exportFavorites}
            disabled={favorites.length === 0}
            className="flex items-center gap-1.5 px-2.5 py-1.5 sm:px-3 sm:py-2 rounded-lg bg-gray-800 border border-gray-700 text-gray-300 text-sm hover:border-cyan-500/50 disabled:opacity-40 transition-colors"
          >
            <Download className="w-4 h-4" />
            导出
          </button>
          {favorites.length > 0 && (
            <button
              onClick={() => setShowClearConfirm(true)}
              className="flex items-center gap-1.5 px-2.5 py-1.5 sm:px-3 sm:py-2 rounded-lg bg-gray-800 border border-gray-700 text-gray-300 text-sm hover:border-red-500/50 transition-colors"
            >
              <Trash2 className="w-4 h-4" />
              清空
            </button>
          )}
        </div>
      </div>

      {stats.total > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4">
          <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-3 sm:p-4">
            <p className="text-xs text-gray-500">收藏总数</p>
            <p className="text-xl sm:text-2xl font-bold text-white mt-1">{stats.total}</p>
          </div>
          <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-3 sm:p-4">
            <p className="text-xs text-gray-500">已验证</p>
            <p className="text-xl sm:text-2xl font-bold text-emerald-400 mt-1">{stats.verified}</p>
            <p className="text-xs text-gray-500 mt-0.5">占比 {stats.total > 0 ? ((stats.verified / stats.total) * 100).toFixed(0) : 0}%</p>
          </div>
          <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-3 sm:p-4">
            <p className="text-xs text-gray-500">元素分布</p>
            <div className="flex flex-wrap gap-1.5 mt-2">
              {stats.elementDist.map(([el, count]) => (
                <span
                  key={el}
                  className="px-1.5 py-0.5 rounded text-xs font-medium"
                  style={{
                    backgroundColor: (ELEMENT_COLORS[el] || '#888') + '25',
                    color: ELEMENT_COLORS[el] || '#888'
                  }}
                >
                  {el} {count}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      {favorites.length > 0 && (
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 flex-wrap">
          <div className="flex-1 relative min-w-0 sm:min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="搜索化学式、空间群、拓扑..."
              className="w-full bg-gray-800 border border-gray-700 rounded-lg pl-9 pr-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-cyan-500"
            />
            {searchQuery && (
              <button onClick={() => setSearchQuery('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <div className="flex items-center gap-1 bg-gray-800/50 border border-gray-700/50 rounded-lg p-1">
              {([['all', '全部'], ['verified', '已验证'], ['raw', '原始']] as const).map(([val, label]) => (
                <button
                  key={val}
                  onClick={() => setFilterStatus(val)}
                  className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                    filterStatus === val
                      ? 'bg-cyan-500/20 text-cyan-400'
                      : 'text-gray-400 hover:text-white'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-2">
              <SortButton field="addedAt" label="时间" />
              <SortButton field="formula" label="化学式" />
              <SortButton field="spaceGroup" label="空间群" />
            </div>
            <button
              onClick={toggleSelectAll}
              className="flex items-center gap-1 text-xs text-gray-400 hover:text-white transition-colors"
            >
              {selectedIds.size === filteredFavorites.length && filteredFavorites.length > 0
                ? <CheckSquare className="w-4 h-4 text-cyan-400" />
                : <Square className="w-4 h-4" />
              }
              全选
            </button>
          </div>
        </div>
      )}

      {favorites.length === 0 ? (
        <div className="text-center py-20">
          <Heart className="w-16 h-16 mx-auto mb-4 text-gray-600" />
          <h2 className="text-xl font-medium text-gray-400 mb-2">暂无收藏</h2>
          <p className="text-gray-500 mb-6">浏览材料详情页，点击收藏按钮将材料添加到这里</p>
          <Link
            to="/materials"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-cyan-500 text-white font-medium hover:bg-cyan-400 transition-colors"
          >
            <Atom className="w-4 h-4" />
            浏览材料库
          </Link>
        </div>
      ) : filteredFavorites.length === 0 ? (
        <div className="text-center py-12">
          <Search className="w-12 h-12 mx-auto mb-3 text-gray-600" />
          <p className="text-gray-400">没有匹配的收藏材料</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
          {filteredFavorites.map((item) => (
            <div
              key={item.materialId}
              className={`bg-gray-800/50 border rounded-xl p-3 sm:p-5 transition-all group ${
                selectedIds.has(item.materialId)
                  ? 'border-cyan-500/50 bg-cyan-500/5'
                  : 'border-gray-700/50 hover:border-cyan-500/30'
              }`}
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-start gap-3 flex-1 min-w-0">
                  <button
                    onClick={() => toggleSelect(item.materialId)}
                    className="mt-1 flex-shrink-0"
                  >
                    {selectedIds.has(item.materialId)
                      ? <CheckSquare className="w-4 h-4 text-cyan-400" />
                      : <Square className="w-4 h-4 text-gray-600 hover:text-gray-400" />
                    }
                  </button>
                  <Link
                    to={`/materials/${item.materialId}`}
                    className="flex-1 min-w-0"
                  >
                    <h3 className="text-base sm:text-lg font-semibold text-white group-hover:text-cyan-400 transition-colors truncate">
                      {item.formula}
                    </h3>
                    <p className="text-sm text-gray-400 mt-0.5">{item.spaceGroup}</p>
                  </Link>
                </div>
                <button
                  onClick={() => removeFavorite(item.materialId)}
                  className="p-2 rounded-lg text-gray-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors flex-shrink-0"
                  title="取消收藏"
                >
                  <Heart className="w-4 h-4 fill-current" />
                </button>
              </div>

              {item.elements && item.elements.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mb-3">
                  {item.elements.map(el => (
                    <span
                      key={el}
                      className="w-7 h-7 rounded text-xs font-bold flex items-center justify-center"
                      style={{
                        backgroundColor: (ELEMENT_COLORS[el] || '#888') + '25',
                        color: ELEMENT_COLORS[el] || '#888'
                      }}
                    >
                      {el}
                    </span>
                  ))}
                </div>
              )}

              <div className="flex items-center justify-between pt-3 border-t border-gray-700/50">
                <div className="flex items-center gap-2">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                    item.verified
                      ? 'bg-emerald-500/10 text-emerald-400'
                      : 'bg-amber-500/10 text-amber-400'
                  }`}>
                    {item.verified ? '已验证' : '原始'}
                  </span>
                  <span className="text-xs text-gray-500">
                    {item.topology}
                  </span>
                </div>
                <span className="text-xs text-gray-600">
                  {formatDate(item.addedAt)}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {showClearConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 w-[90%] max-w-sm sm:w-96">
            <h3 className="text-lg font-medium text-white mb-2">确认清空收藏</h3>
            <p className="text-sm text-gray-400 mb-6">此操作将删除所有 {favorites.length} 个收藏材料，且不可恢复。</p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowClearConfirm(false)}
                className="flex-1 px-4 py-2 rounded-lg bg-gray-700 text-gray-300 hover:bg-gray-600 transition-colors"
              >
                取消
              </button>
              <button
                onClick={clearAll}
                className="flex-1 px-4 py-2 rounded-lg bg-red-500 text-white font-medium hover:bg-red-400 transition-colors"
              >
                确认清空
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
