import { useState, useEffect, useCallback, useMemo } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Plus, X, GitCompare, Search, Loader2, Trash2, Download, BarChart3, LayoutGrid, List } from 'lucide-react'
import { fetchMaterials, fetchMaterial } from '../api/client'
import CrystalViewer from '../components/three/CrystalViewer'
import type { Material, MaterialListItem } from '../types'

const ELEMENT_COLORS: Record<string, string> = {
  H: '#ffffff', O: '#ff0d0d', F: '#90e050', N: '#3050f8', C: '#909090',
  B: '#ffb5b5', Si: '#f0c8a0', P: '#ff8000', S: '#ffff30', Cl: '#1ff01f',
  Li: '#cc80ff', Na: '#ab5cf2', K: '#8f40d4', Rb: '#702eb0', Cs: '#57178f',
  Be: '#c2ff00', Mg: '#8aff00', Ca: '#3dff00', Sr: '#00ff00', Ba: '#00c900',
  Ti: '#bfc2c7', V: '#a6a6ab', Cr: '#8a99c7', Mn: '#9c7ac7', Fe: '#e06633',
  Co: '#f090a0', Ni: '#50d050', Cu: '#c88033', Zn: '#7d80b0', Al: '#bfa6a6',
  Ga: '#c28f8f', In: '#a67573', Sn: '#668080', Pb: '#575961', Bi: '#9e4fb5',
}

type SearchField = 'formula' | 'topology' | 'space_group'

function computeVolume(lattice: { a: number; b: number; c: number; alpha: number; beta: number; gamma: number }): number {
  const toRad = Math.PI / 180
  const a = lattice.a, b = lattice.b, c = lattice.c
  const al = lattice.alpha * toRad, be = lattice.beta * toRad, ga = lattice.gamma * toRad
  return a * b * c * Math.sqrt(1 - Math.cos(al) ** 2 - Math.cos(be) ** 2 - Math.cos(ga) ** 2 + 2 * Math.cos(al) * Math.cos(be) * Math.cos(ga))
}

function detectCrystalSystem(lattice: { a: number; b: number; c: number; alpha: number; beta: number; gamma: number }): string {
  const tol = 0.5
  const ltol = 0.01
  const { a, b, c, alpha, beta, gamma } = lattice
  const a90 = Math.abs(alpha - 90) < tol
  const b90 = Math.abs(beta - 90) < tol
  const g90 = Math.abs(gamma - 90) < tol
  const g120 = Math.abs(gamma - 120) < tol
  if (a90 && b90 && g90) {
    if (Math.abs(a - b) < ltol && Math.abs(b - c) < ltol) return '立方'
    if (Math.abs(a - b) < ltol) return '四方'
    return '正交'
  }
  if (a90 && b90 && g120) return '六方'
  if (a90 && g90 && Math.abs(beta - 120) < tol) return '六方'
  if (g90 && (a90 || b90)) return '单斜'
  return '三斜'
}

interface ComparisonProperty {
  key: string
  label: string
  format?: (v: unknown) => string
}

const COMPARISON_PROPERTIES: ComparisonProperty[] = [
  { key: 'formula', label: '化学式' },
  { key: 'space_group', label: '空间群' },
  { key: 'topology', label: '拓扑' },
  { key: 'crystal_system', label: '晶系' },
  { key: 'verified', label: '状态', format: (v) => v ? '已验证' : '原始' },
  { key: 'lattice_a', label: 'a (Å)' },
  { key: 'lattice_b', label: 'b (Å)' },
  { key: 'lattice_c', label: 'c (Å)' },
  { key: 'lattice_alpha', label: 'α (°)' },
  { key: 'lattice_beta', label: 'β (°)' },
  { key: 'lattice_gamma', label: 'γ (°)' },
  { key: 'volume', label: '晶胞体积 (Å³)' },
  { key: 'atom_count', label: '原子数' },
  { key: 'element_count', label: '元素种类' },
]

function extractMaterialProperties(material: Material) {
  const lattice = material.cif_data?.lattice
  const vol = lattice ? computeVolume(lattice) : null
  return {
    formula: material.formula,
    space_group: material.space_group,
    topology: material.topology,
    crystal_system: lattice ? detectCrystalSystem(lattice) : null,
    verified: material.verified,
    lattice_a: lattice?.a,
    lattice_b: lattice?.b,
    lattice_c: lattice?.c,
    lattice_alpha: lattice?.alpha,
    lattice_beta: lattice?.beta,
    lattice_gamma: lattice?.gamma,
    volume: vol,
    atom_count: material.cif_data?.atom_sites?.length,
    element_count: material.elements?.length,
  }
}

function formatPropertyValue(prop: ComparisonProperty, value: unknown): string {
  if (value === null || value === undefined) return '-'
  if (prop.format) return prop.format(value)
  if (typeof value === 'number') return value < 100 ? value.toFixed(4) : value.toFixed(2)
  return String(value)
}

export default function MaterialsCompare() {
  const [searchParams] = useSearchParams()
  const [selected, setSelected] = useState<Material[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [searchField, setSearchField] = useState<SearchField>('formula')
  const [available, setAvailable] = useState<MaterialListItem[]>([])
  const [loading, setLoading] = useState(false)
  const [searchLoading, setSearchLoading] = useState(false)
  const [viewMode, setViewMode] = useState<'card' | 'table'>('card')

  useEffect(() => {
    const ids = searchParams.get('ids')
    if (ids) {
      const idList = ids.split(',').slice(0, 4)
      idList.forEach(async (id) => {
        try {
          const material = await fetchMaterial(id)
          setSelected(prev => {
            if (prev.some(m => m.material_id === material.material_id)) return prev
            return [...prev, material]
          })
        } catch {}
      })
    }
  }, [searchParams])

  useEffect(() => {
    loadMaterials()
  }, [])

  const loadMaterials = async () => {
    setLoading(true)
    try {
      const data = await fetchMaterials({ page: '1', per_page: '200' })
      setAvailable(data.materials || [])
    } catch (err) {
      console.error('Failed to load materials:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = useCallback(async () => {
    if (!searchQuery.trim()) {
      loadMaterials()
      return
    }
    setSearchLoading(true)
    try {
      const data = await fetchMaterials({ page: '1', per_page: '200' })
      const q = searchQuery.toLowerCase()
      const filtered = (data.materials || []).filter(m => {
        switch (searchField) {
          case 'formula': return m.formula.toLowerCase().includes(q)
          case 'topology': return m.topology?.toLowerCase().includes(q)
          case 'space_group': return m.space_group.toLowerCase().includes(q)
          default: return m.formula.toLowerCase().includes(q)
        }
      })
      setAvailable(filtered)
    } catch (err) {
      console.error('Search failed:', err)
    } finally {
      setSearchLoading(false)
    }
  }, [searchQuery, searchField])

  const addMaterial = async (item: MaterialListItem) => {
    if (selected.length >= 4) return
    if (selected.some(m => m.material_id === item.material_id)) return
    try {
      const material = await fetchMaterial(item.material_id)
      setSelected(prev => [...prev, material])
    } catch (err) {
      console.error('Failed to load material:', err)
    }
  }

  const removeMaterial = (id: string) => {
    setSelected(prev => prev.filter(m => m.material_id !== id))
  }

  const clearAll = () => {
    setSelected([])
  }

  const exportComparison = () => {
    const lines: string[] = ['CGCPT 材料对比报告', '=' .repeat(60), '']
    selected.forEach(m => {
      const props = extractMaterialProperties(m)
      lines.push(`【${m.formula}】`)
      COMPARISON_PROPERTIES.forEach(prop => {
        const val = props[prop.key as keyof typeof props]
        lines.push(`  ${prop.label}: ${formatPropertyValue(prop, val)}`)
      })
      lines.push('')
    })
    const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `cgcpt_comparison_${new Date().toISOString().slice(0, 10)}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  const latticeBarData = useMemo(() => {
    if (selected.length < 2) return null
    const keys = ['lattice_a', 'lattice_b', 'lattice_c'] as const
    const labels = ['a', 'b', 'c']
    return keys.map((key, i) => {
      const values = selected.map(m => {
        const props = extractMaterialProperties(m)
        return props[key] as number | null
      }).filter((v): v is number => v !== null)
      const max = Math.max(...values, 0.01)
      return { key, label: labels[i], max, values }
    })
  }, [selected])

  const gridCols = selected.length <= 2 ? 'grid-cols-1 lg:grid-cols-2' : 'grid-cols-1 lg:grid-cols-2 xl:grid-cols-4'

  return (
    <div className="h-full flex flex-col lg:flex-row">
      <div className="w-full lg:w-80 bg-gray-900/50 border-b lg:border-b-0 lg:border-r border-gray-800 flex flex-col max-h-64 lg:max-h-none">
        <div className="p-3 sm:p-4 border-b border-gray-800">
          <div className="flex items-center gap-2 mb-3">
            <GitCompare className="w-5 h-5 text-cyan-400" />
            <h2 className="text-base sm:text-lg font-semibold text-white">选择材料</h2>
            <span className="text-xs text-gray-500 ml-auto">({selected.length}/4)</span>
          </div>
          <div className="flex gap-1 mb-2">
            {([['formula', '化学式'], ['topology', '拓扑'], ['space_group', '空间群']] as [SearchField, string][]).map(([field, label]) => (
              <button
                key={field}
                onClick={() => setSearchField(field)}
                className={`flex-1 px-2 py-1 rounded text-xs font-medium transition-colors ${
                  searchField === field
                    ? 'bg-cyan-500/20 text-cyan-400'
                    : 'text-gray-500 hover:text-gray-300'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          <div className="flex gap-2">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                placeholder={`按${searchField === 'formula' ? '化学式' : searchField === 'topology' ? '拓扑' : '空间群'}搜索...`}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg pl-9 pr-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-cyan-500"
              />
            </div>
            <button
              onClick={handleSearch}
              disabled={searchLoading}
              className="px-3 py-2 bg-cyan-500 text-white rounded-lg text-sm hover:bg-cyan-600 disabled:opacity-50 transition-colors"
            >
              {searchLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : '搜索'}
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-1">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 text-cyan-400 animate-spin" />
            </div>
          ) : available.length === 0 ? (
            <p className="text-center text-gray-500 py-8 text-sm">未找到材料</p>
          ) : (
            available.map((item) => {
              const isSelected = selected.some(m => m.material_id === item.material_id)
              return (
                <button
                  key={item.material_id}
                  onClick={() => !isSelected && addMaterial(item)}
                  disabled={isSelected || selected.length >= 4}
                  className={`w-full text-left rounded-lg p-2 sm:p-3 transition-all ${
                    isSelected
                      ? 'bg-cyan-500/10 border border-cyan-500/30 opacity-50'
                      : selected.length >= 4
                        ? 'bg-gray-800/50 opacity-50 cursor-not-allowed'
                        : 'bg-gray-800/50 border border-gray-700/50 hover:bg-gray-700/50 hover:border-cyan-500/30'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-white font-medium text-sm">{item.formula}</span>
                    {isSelected && <Plus className="w-4 h-4 text-cyan-400" />}
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs text-gray-400">{item.space_group}</span>
                    <span className="text-xs text-gray-600">·</span>
                    <span className="text-xs text-gray-400">{item.topology}</span>
                  </div>
                </button>
              )
            })
          )}
        </div>

        {selected.length > 0 && (
          <div className="p-3 border-t border-gray-800 space-y-2">
            <button
              onClick={exportComparison}
              className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-gray-800 text-gray-300 border border-gray-700 rounded-lg text-sm hover:border-cyan-500/50 transition-colors"
            >
              <Download className="w-4 h-4" />
              导出对比报告
            </button>
            <button
              onClick={clearAll}
              className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-red-500/10 text-red-400 border border-red-500/30 rounded-lg text-sm hover:bg-red-500/20 transition-colors"
            >
              <Trash2 className="w-4 h-4" />
              清除全部
            </button>
          </div>
        )}
      </div>

      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="p-3 sm:p-4 border-b border-gray-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <GitCompare className="w-5 h-5 text-cyan-400" />
            <h2 className="text-base sm:text-lg font-semibold text-white">材料对比</h2>
            {selected.length > 0 && (
              <span className="text-sm text-gray-500">({selected.length} 个材料)</span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {selected.length > 0 && (
              <div className="flex items-center gap-1 bg-gray-800/50 border border-gray-700/50 rounded-lg p-1">
                <button
                  onClick={() => setViewMode('card')}
                  className={`p-1.5 rounded transition-colors ${viewMode === 'card' ? 'bg-cyan-500/20 text-cyan-400' : 'text-gray-500 hover:text-white'}`}
                  title="卡片视图"
                >
                  <LayoutGrid className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setViewMode('table')}
                  className={`p-1.5 rounded transition-colors ${viewMode === 'table' ? 'bg-cyan-500/20 text-cyan-400' : 'text-gray-500 hover:text-white'}`}
                  title="表格视图"
                >
                  <List className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
        </div>

        {selected.length === 0 ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center text-gray-500">
              <GitCompare className="w-16 h-16 mx-auto mb-4 opacity-30" />
              <p className="text-lg mb-2">选择材料进行对比</p>
              <p className="text-sm">从左侧列表选择最多4个材料进行对比分析</p>
              <p className="text-xs text-gray-600 mt-2">支持按化学式、拓扑、空间群搜索</p>
            </div>
          </div>
        ) : (
          <div className="flex-1 overflow-auto p-3 sm:p-4 space-y-4 sm:space-y-6">
            {viewMode === 'card' && (
              <div className={`grid ${gridCols} gap-3 sm:gap-4`}>
                {selected.map((material) => (
                  <MaterialComparisonCard
                    key={material.material_id}
                    material={material}
                    onRemove={() => removeMaterial(material.material_id)}
                  />
                ))}
              </div>
            )}

            {latticeBarData && (
              <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-3 sm:p-5">
                <h3 className="text-base sm:text-lg font-semibold text-white mb-3 sm:mb-4 flex items-center gap-2">
                  <BarChart3 className="w-5 h-5 text-cyan-400" />
                  晶格参数对比
                </h3>
                <div className="space-y-4">
                  {latticeBarData.map(({ label, max, values }) => (
                    <div key={label}>
                      <div className="flex items-center gap-3 mb-1.5">
                        <span className="text-sm text-gray-400 w-8">{label}</span>
                        <div className="flex-1 flex gap-2">
                          {values.map((v, i) => (
                            <div key={i} className="flex-1">
                              <div className="h-6 bg-gray-900/50 rounded overflow-hidden">
                                <div
                                  className="h-full rounded transition-all duration-500"
                                  style={{
                                    width: `${(v / max) * 100}%`,
                                    backgroundColor: ['#06b6d4', '#22c55e', '#f59e0b', '#a855f7'][i % 4],
                                    opacity: 0.7,
                                  }}
                                />
                              </div>
                              <p className="text-xs text-gray-400 mt-0.5 font-mono">{v.toFixed(2)} Å</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="flex flex-wrap gap-3 sm:gap-4 mt-3 pt-3 border-t border-gray-700/50">
                  {selected.map((m, i) => (
                    <span key={m.material_id} className="flex items-center gap-1.5 text-xs text-gray-400">
                      <span className="w-3 h-3 rounded" style={{ backgroundColor: ['#06b6d4', '#22c55e', '#f59e0b', '#a855f7'][i % 4] }} />
                      {m.formula}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-3 sm:p-5">
              <h3 className="text-base sm:text-lg font-semibold text-white mb-3 sm:mb-4">属性对比表</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-700/50">
                      <th className="text-left px-2 py-1.5 sm:px-3 sm:py-2 text-gray-400 font-medium w-36">属性</th>
                      {selected.map((m) => (
                        <th key={m.material_id} className="text-left px-2 py-1.5 sm:px-3 sm:py-2 text-white font-medium">
                          {m.formula}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-700/30">
                    {COMPARISON_PROPERTIES.map((prop) => {
                      const values = selected.map(m => {
                        const props = extractMaterialProperties(m)
                        return props[prop.key as keyof typeof props] ?? null
                      })
                      const nonNull = values.filter(v => v !== null)
                      const allSame = nonNull.length > 1 && nonNull.every(v => v === nonNull[0])

                      return (
                        <tr key={prop.key} className={!allSame && nonNull.length > 1 ? 'bg-cyan-500/5' : ''}>
                          <td className="px-2 py-1.5 sm:px-3 sm:py-2 text-gray-400">{prop.label}</td>
                          {values.map((v, i) => (
                            <td
                              key={i}
                              className={`px-2 py-1.5 sm:px-3 sm:py-2 font-mono ${
                                !allSame && v !== null && v !== values[0] ? 'text-cyan-400 font-medium' : 'text-gray-200'
                              }`}
                            >
                              {formatPropertyValue(prop, v)}
                            </td>
                          ))}
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function MaterialComparisonCard({ material, onRemove }: { material: Material; onRemove: () => void }) {
  const lattice = material.cif_data?.lattice
  const atoms = material.cif_data?.atom_sites || []
  const crystalSystem = lattice ? detectCrystalSystem(lattice) : null
  const volume = lattice ? computeVolume(lattice) : null

  return (
    <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-3 sm:px-4 py-2 sm:py-3 bg-gray-900/50 border-b border-gray-700/50">
        <div>
          <h3 className="text-white font-semibold text-sm sm:text-base">{material.formula}</h3>
          <p className="text-xs text-gray-400">{material.space_group}</p>
        </div>
        <button
          onClick={onRemove}
          className="p-1.5 text-gray-500 hover:text-red-400 hover:bg-red-500/10 rounded transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="h-64 sm:h-96">
        {atoms.length > 0 && lattice ? (
          <CrystalViewer
            atoms={atoms}
            lattice={lattice}
            className="h-full w-full"
            showBonds
            showElementInfo
          />
        ) : (
          <div className="h-full flex items-center justify-center text-gray-500 text-sm">
            暂无结构数据
          </div>
        )}
      </div>

      <div className="p-3 sm:p-4 space-y-2 sm:space-y-3">
        <div className="flex items-center gap-1.5">
          <span className="text-xs text-gray-400 w-10">元素</span>
          <div className="flex gap-1">
            {material.elements?.map((el) => (
              <span
                key={el}
                className="w-6 h-6 rounded text-xs font-medium flex items-center justify-center"
                style={{
                  backgroundColor: (ELEMENT_COLORS[el] || '#888') + '30',
                  color: ELEMENT_COLORS[el] || '#888'
                }}
              >
                {el}
              </span>
            ))}
          </div>
        </div>

        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-400">拓扑</span>
          <span className="text-xs text-cyan-400 font-mono">{material.topology}</span>
        </div>

        {crystalSystem && (
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-400">晶系</span>
            <span className="text-xs text-white">{crystalSystem}</span>
          </div>
        )}

        {lattice && (
          <div className="grid grid-cols-3 gap-2 pt-2 border-t border-gray-700/50">
            <div className="text-center">
              <p className="text-xs text-gray-500">a</p>
              <p className="text-sm font-mono text-white">{lattice.a.toFixed(2)}</p>
            </div>
            <div className="text-center">
              <p className="text-xs text-gray-500">b</p>
              <p className="text-sm font-mono text-white">{lattice.b.toFixed(2)}</p>
            </div>
            <div className="text-center">
              <p className="text-xs text-gray-500">c</p>
              <p className="text-sm font-mono text-white">{lattice.c.toFixed(2)}</p>
            </div>
            <div className="text-center">
              <p className="text-xs text-gray-500">α</p>
              <p className="text-sm font-mono text-white">{lattice.alpha.toFixed(1)}°</p>
            </div>
            <div className="text-center">
              <p className="text-xs text-gray-500">β</p>
              <p className="text-sm font-mono text-white">{lattice.beta.toFixed(1)}°</p>
            </div>
            <div className="text-center">
              <p className="text-xs text-gray-500">γ</p>
              <p className="text-sm font-mono text-white">{lattice.gamma.toFixed(1)}°</p>
            </div>
          </div>
        )}

        {volume !== null && (
          <div className="flex items-center justify-between pt-2 border-t border-gray-700/50">
            <span className="text-xs text-gray-400">体积</span>
            <span className="text-xs text-white font-mono">{volume.toFixed(2)} Å³</span>
          </div>
        )}

        <div className="flex items-center justify-between pt-2">
          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs ${
            material.verified
              ? 'bg-emerald-500/10 text-emerald-400'
              : 'bg-amber-500/10 text-amber-400'
          }`}>
            {material.verified ? '已验证' : '原始'}
          </span>
          <Link
            to={`/materials/${material.material_id}`}
            className="text-xs text-cyan-400 hover:text-cyan-300"
          >
            详情 →
          </Link>
        </div>
      </div>
    </div>
  )
}
