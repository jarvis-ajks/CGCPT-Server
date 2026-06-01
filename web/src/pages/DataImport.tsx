import { useState, useCallback, useRef, useEffect } from 'react'
import {
  Upload, FileText, CheckCircle2, AlertTriangle, X,
  Database, Layers, Atom,
  Loader2, Trash2, Info, Sparkles
} from 'lucide-react'
import { previewImportFiles, importMaterials } from '../api/client'
import type { ImportPreviewResult, ImportItem } from '../api/client'

interface FileWithContent extends File {
  _content?: string
}

export default function DataImport() {
  const [files, setFiles] = useState<FileWithContent[]>([])
  const [previewResults, setPreviewResults] = useState<ImportPreviewResult[] | null>(null)
  const [importing, setImporting] = useState(false)
  const [importResult, setImportResult] = useState<{
    imported: number; skipped: number; errors: number; total: number
  } | null>(null)
  const [selectedTopology, setSelectedTopology] = useState('')
  const [topologies, setTopologies] = useState<string[]>([])
  const [dragOver, setDragOver] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [modifiedTopologies, setModifiedTopologies] = useState<Record<string, string>>({})
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (previewResults && previewResults.length > 0) {
      const tops = [...new Set(previewResults.map(r => r.suggested_topology).filter(Boolean))]
      if (!selectedTopology && tops[0]) setSelectedTopology(tops[0])
      const availTopos = (previewResults as any).available_topologies || []
      setTopologies(availTopos)
    }
  }, [previewResults])

  const handleFiles = useCallback((newFiles: FileList | File[]) => {
    const arr = Array.from(newFiles) as FileWithContent[]
    const cifOnly = arr.filter(f => f.name.toLowerCase().endsWith('.cif'))
    if (cifOnly.length !== arr.length) {
      alert(`已过滤 ${arr.length - cifOnly.length} 个非 CIF 文件`)
    }
    setFiles(prev => {
      const existingNames = new Set(prev.map(f => f.name))
      const unique = cifOnly.filter(f => !existingNames.has(f.name))
      return [...prev, ...unique]
    })
    setPreviewResults(null)
    setImportResult(null)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    handleFiles(e.dataTransfer.files)
  }, [handleFiles])

  const handlePreview = useCallback(async () => {
    if (files.length === 0) return
    try {
      const res = await previewImportFiles(files, selectedTopology || undefined)
      setPreviewResults(res.results)
      setModifiedTopologies({})
    } catch (err: any) {
        alert('预览失败: ' + err.message)
    }
  }, [files, selectedTopology])

  const handleImport = useCallback(async () => {
    if (!previewResults) return
    const validResults = previewResults.filter(r => !r.error && !r.existing)
    if (validResults.length === 0) {
      alert('没有可导入的有效文件')
      return
    }

    setImporting(true)
    try {
      const items: ImportItem[] = validResults.map(r => ({
        material_id: r.material_id,
        topology: modifiedTopologies[r.material_id] || r.assigned_topology,
        cif_content: '', 
        formula: r.formula,
        space_group: r.space_group,
        elements: r.elements,
      }))
      
      for (const item of items) {
        const f = files.find(ff => ff.name === previewResults.find(pr => pr.material_id === item.material_id)?.filename)
        if (f) {
          item.cif_content = await f.text()
        }
      }

      const res = await importMaterials(items)
      setImportResult({
        imported: res.imported?.length || 0,
        skipped: res.skipped?.length || 0,
        errors: res.errors?.length || 0,
        total: res.total_materials_now || 0,
      })

      if (res.imported?.length) {
        setPreviewResults(null)
        setFiles([])
      }
    } catch (err: any) {
      alert('导入失败: ' + err.message)
    } finally {
      setImporting(false)
    }
  }, [previewResults, files, modifiedTopologies])

  const removeFile = (name: string) => {
    setFiles(prev => prev.filter(f => f.name !== name))
    setPreviewResults(null)
  }

  const clearAll = () => {
    setFiles([])
    setPreviewResults(null)
    setImportResult(null)
    setModifiedTopologies({})
  }

  const getEffectiveTopology = (r: ImportPreviewResult) =>
    modifiedTopologies[r.material_id] || r.assigned_topology

  const parsedCount = previewResults?.filter(r => !r.error).length || 0
  const errorCount = previewResults?.filter(r => r.error).length || 0
  const existingCount = previewResults?.filter(r => r.existing && !r.error).length || 0
  const newCount = parsedCount - existingCount

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-3">
          <Database className="w-7 h-7 text-cyan-400" />
          数据导入
        </h1>
        <p className="text-gray-400 mt-1 text-sm">
          上传外部算法生成的 CIF 文件，自动解析结构并归类到拓扑原型数据库中
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div
            onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
              dragOver
                ? 'border-cyan-400 bg-cyan-400/10'
                : files.length > 0
                  ? 'border-gray-600 bg-gray-900/50 hover:border-gray-500'
                  : 'border-gray-700 bg-gray-900/30 hover:border-cyan-500/50 hover:bg-gray-900/50'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".cif"
              onChange={(e) => e.target.files && handleFiles(e.target.files)}
              className="hidden"
            />
            <Upload className={`w-12 h-12 mx-auto mb-4 ${dragOver ? 'text-cyan-400' : 'text-gray-500'}`} />
            <p className="text-gray-300 font-medium mb-1">
              拖拽 CIF 文件到此处，或点击选择文件
            </p>
            <p className="text-gray-500 text-sm">支持 .cif 格式，可批量上传</p>
            {files.length > 0 && (
              <p className="text-cyan-400 text-sm mt-3">
                已选择 {files.length} 个文件 ({(files.reduce((s, f) => s + f.size, 0) / 1024).toFixed(1)} KB)
              </p>
            )}
          </div>

          {files.length > 0 && (
            <div className="flex items-center gap-3">
              <button
                onClick={handlePreview}
                disabled={!files.length}
                className="px-5 py-2.5 bg-cyan-500 hover:bg-cyan-600 text-white rounded-lg font-medium text-sm flex items-center gap-2 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <Sparkles className="w-4 h-4" />
                解析并预览
              </button>
              {previewResults && (
                <button
                  onClick={handleImport}
                  disabled={importing || newCount === 0}
                  className="px-5 py-2.5 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium text-sm flex items-center gap-2 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {importing ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                  确认导入 ({newCount} 个新文件)
                </button>
              )}
              <button
                onClick={clearAll}
                className="px-4 py-2.5 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg font-medium text-sm flex items-center gap-2 transition-colors ml-auto"
              >
                <Trash2 className="w-4 h-4" />
                清空
              </button>
            </div>
          )}

          {previewResults && (
            <div className="bg-gray-900/60 border border-gray-800 rounded-xl overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between">
                <span className="text-sm font-medium text-gray-200">
                  预览结果
                  {parsedCount > 0 && <span className="text-cyan-400 ml-2">{parsedCount} 已解析</span>}
                  {errorCount > 0 && <span className="text-red-400 ml-2">{errorCount} 错误</span>}
                  {existingCount > 0 && <span className="text-yellow-400 ml-2">{existingCount} 已存在</span>}
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-800/50">
                      <th className="text-left px-4 py-3 text-gray-400 font-medium">材料 ID</th>
                      <th className="text-left px-4 py-3 text-gray-400 font-medium">化学式</th>
                      <th className="text-left px-4 py-3 text-gray-400 font-medium">空间群</th>
                      <th className="text-left px-4 py-3 text-gray-400 font-medium">元素</th>
                      <th className="text-left px-4 py-3 text-gray-400 font-medium">原子数</th>
                      <th className="text-left px-4 py-3 text-gray-400 font-medium">晶格 (Å)</th>
                      <th className="text-left px-4 py-3 text-gray-400 font-medium">拓扑分类</th>
                      <th className="text-left px-4 py-3 text-gray-400 font-medium">置信度</th>
                      <th className="text-left px-4 py-3 text-gray-400 font-medium">状态</th>
                    </tr>
                  </thead>
                  <tbody>
                    {previewResults.map((r, i) => (
                      <tr key={i} className="border-t border-gray-800/50 hover:bg-gray-800/30">
                        <td className="px-4 py-2.5 text-gray-200 font-mono text-xs">{r.material_id}</td>
                        <td className="px-4 py-2.5 text-white font-medium">{r.formula || '-'}</td>
                        <td className="px-4 py-2.5 text-gray-300 text-xs">{r.space_group || '-'}</td>
                        <td className="px-4 py-2.5">
                          <div className="flex gap-1 flex-wrap">
                            {r.elements.slice(0, 4).map(el => (
                              <span key={el} className="px-1.5 py-0.5 bg-gray-700 rounded text-xs text-gray-300">{el}</span>
                            ))}
                            {r.elements.length > 4 && <span className="text-xs text-gray-500">+{r.elements.length - 4}</span>}
                          </div>
                        </td>
                        <td className="px-4 py-2.5 text-gray-300 text-center tabular-nums">{r.n_atoms}</td>
                        <td className="px-4 py-2.5 text-gray-400 text-xs tabular-nums">
                          {r.lattice.a ? `${r.lattice.a.toFixed(2)}×${r.lattice.b?.toFixed(2)}×${r.lattice.c?.toFixed(2)}` : '-'}
                        </td>
                        <td className="px-4 py-2.5">
                          {r.error ? (
                            <span className="text-red-400 text-xs">{r.error}</span>
                          ) : editingId === r.material_id ? (
                            <select
                              value={modifiedTopologies[r.material_id] || r.assigned_topology}
                              onChange={(e) => setModifiedTopologies(prev => ({ ...prev, [r.material_id]: e.target.value }))}
                              onBlur={() => setEditingId(null)}
                              autoFocus
                              className="bg-gray-800 border border-cyan-500/50 rounded px-2 py-1 text-xs text-white w-full max-w-[280px]"
                            >
                              {topologies.map(t => (
                                <option key={t} value={t}>{t}</option>
                              ))}
                            </select>
                          ) : (
                            <button
                              onClick={() => setEditingId(r.material_id)}
                              className="text-cyan-400 hover:text-cyan-300 text-xs font-mono underline decoration-dotted cursor-pointer"
                            >
                              {getEffectiveTopology(r)}
                            </button>
                          )}
                        </td>
                        <td className="px-4 py-2.5">
                          {!r.error && (
                            <div className="flex items-center gap-1.5">
                              <div className="w-14 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                                <div
                                  className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-emerald-400"
                                  style={{ width: `${Math.min(r.confidence * 100, 100)}%` }}
                                />
                              </div>
                              <span className="text-xs text-gray-400 tabular-nums">{(r.confidence * 100).toFixed(0)}%</span>
                            </div>
                          )}
                        </td>
                        <td className="px-4 py-2.5">
                          {r.existing && !r.error ? (
                            <span className="inline-flex items-center gap-1 text-yellow-400 text-xs">
                              <AlertTriangle className="w-3.5 h-3.5" /> 已存在
                            </span>
                          ) : r.error ? (
                            <span className="inline-flex items-center gap-1 text-red-400 text-xs">
                              <X className="w-3.5 h-3.5" /> 错误
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-emerald-400 text-xs">
                              <CheckCircle2 className="w-3.5 h-3.5" /> 待导入
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {importResult && (
            <div className="bg-gray-900/80 border border-emerald-500/30 rounded-xl p-5">
              <div className="flex items-start gap-3">
                <CheckCircle2 className="w-6 h-6 text-emerald-400 mt-0.5 shrink-0" />
                <div>
                  <h3 className="text-white font-semibold mb-2">导入完成！</h3>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
                    <div className="bg-gray-800/50 rounded-lg p-3">
                      <div className="text-2xl font-bold text-emerald-400 tabular-nums">{importResult.imported}</div>
                      <div className="text-gray-400 text-xs mt-0.5">新导入</div>
                    </div>
                    <div className="bg-gray-800/50 rounded-lg p-3">
                      <div className="text-2xl font-bold text-yellow-400 tabular-nums">{importResult.skipped}</div>
                      <div className="text-gray-400 text-xs mt-0.5">跳过（重复）</div>
                    </div>
                    <div className="bg-gray-800/50 rounded-lg p-3">
                      <div className="text-2xl font-bold text-red-400 tabular-nums">{importResult.errors}</div>
                      <div className="text-gray-400 text-xs mt-0.5">错误</div>
                    </div>
                    <div className="bg-gray-800/50 rounded-lg p-3">
                      <div className="text-2xl font-bold text-cyan-400 tabular-nums">{importResult.total}</div>
                      <div className="text-gray-400 text-xs mt-0.5">总材料数</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="space-y-5">
          <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2 mb-3">
              <Layers className="w-4 h-4 text-cyan-400" />
              已选文件
            </h3>
            {files.length === 0 ? (
              <p className="text-gray-500 text-sm">暂无文件</p>
            ) : (
              <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
                {files.map((f, i) => (
                  <div key={i} className="flex items-center justify-between bg-gray-800/50 rounded-lg px-3 py-2 group">
                    <div className="flex items-center gap-2 min-w-0">
                      <FileText className="w-4 h-4 text-gray-400 shrink-0" />
                      <span className="text-sm text-gray-300 truncate">{f.name}</span>
                    </div>
                    <button
                      onClick={() => removeFile(f.name)}
                      className="opacity-0 group-hover:opacity-100 p-1 hover:text-red-400 text-gray-500 transition-all"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2 mb-3">
              <Info className="w-4 h-4 text-cyan-400" />
              导入说明
            </h3>
            <ul className="space-y-2.5 text-xs text-gray-400">
              <li className="flex gap-2">
                <span className="text-cyan-400 mt-0.5">•</span>
                <span>支持标准 CIF 格式文件，批量上传不限数量</span>
              </li>
              <li className="flex gap-2">
                <span className="text-cyan-400 mt-0.5">•</span>
                <span>系统会自动解析晶体结构，基于 O/X 元素比、层数、晶格特征进行拓扑分类</span>
              </li>
              <li className="flex gap-2">
                <span className="text-cyan-400 mt-0.5">•</span>
                <span>预览阶段可以手动修改每个材料的拓扑归属（点击拓扑名编辑）</span>
              </li>
              <li className="flex gap-2">
                <span className="text-cyan-400 mt-0.5">•</span>
                <span>已存在的材料 ID 会自动跳过，不会覆盖</span>
              </li>
              <li className="flex gap-2">
                <span className="text-cyan-400 mt-0.5">•</span>
                <span>导入后索引自动重建，所有页面实时更新</span>
              </li>
            </ul>
          </div>

          <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2 mb-3">
              <Atom className="w-4 h-4 text-purple-400" />
              自动分类规则
            </h3>
            <div className="space-y-2 text-xs">
              {[
                ['O/X ≈ 3:1 + ≥5层', 'XO₃-M7-XO₃-M7-XO₃-M7-XO₃', '85%'],
                ['O/X ≈ 3:1 + ≥7层', '含 T 层的扩展族系', '80%'],
                ['O/X ≈ 2:1 + ≥5层', '含 XO₂ 的族系', '75%'],
                ['六方对称 a≈b', '加分 +5%', '+5%'],
              ].map(([cond, topo, conf], i) => (
                <div key={i} className="flex items-center justify-between bg-gray-800/40 rounded px-3 py-2">
                  <span className="text-gray-400">{cond}</span>
                  <span className="text-gray-300 font-mono text-[11px]">{topo}</span>
                  <span className="text-cyan-400/70 w-10 text-right">{conf}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
