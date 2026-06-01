import { useState, useRef, useCallback } from 'react'
import {
  Upload,
  Brain,
  BarChart3,
  Layers,
  Trash2,
  RefreshCw,
  FileText,
  ChevronDown,
  ChevronRight,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Loader2,
  Zap,
  Grid3X3,
  GitCompare,
} from 'lucide-react'

const API = '/CGCPT/api'

interface LayerInfo {
  z: number
  n_atoms: number
  elements: Record<string, number>
  has_oxygen: boolean
  x_to_o_ratio: number | null
  grid_x: number
  grid_y: number
  predicted_type: string
}

interface UploadResult {
  success: boolean
  filename?: string
  formula?: string
  space_group?: string
  lattice?: Record<string, number>
  n_atoms?: number
  features?: Record<string, number>
  layer_analysis?: LayerInfo[]
  cif_text?: string
  error?: string
}

interface TrainResult {
  success: boolean
  model_id?: string
  best_params?: Record<string, unknown>
  feature_importances?: [string, number][]
  classification_report?: Record<string, unknown>
  confusion_matrix?: { labels: string[]; matrix: number[][] }
  model_comparison?: Record<string, { name: string; best_acc: number; avg_acc: number; count: number }>
  n_iterations?: number
  n_configs_tested?: number
  n_total_samples?: number
  n_valid_samples?: number
  n_classes?: number
  class_distribution?: Record<string, number>
  test_ratio?: number
  error?: string
}

interface PredictResult {
  success: boolean
  predicted_topology?: string
  confidence?: number
  top_predictions?: [string, number][]
  features?: Record<string, number>
  layer_analysis?: LayerInfo[]
  error?: string
}

interface ModelInfo {
  model_id: string
  created: string
  test_accuracy: number
  n_samples: number
  n_classes: number
}

type TabKey = 'upload' | 'train' | 'predict'

const LAYER_TYPE_COLORS: Record<string, string> = {
  XO: '#3b82f6', XO2: '#8b5cf6', XO3: '#06b6d4', X: '#f59e0b',
  XBO3: '#10b981', BO3: '#84cc16', XB3O6: '#ec4899',
  M6: '#f97316', M7: '#ef4444', T: '#6366f1', unknown: '#6b7280',
}

const MODEL_TYPE_OPTIONS = [
  { value: 'auto', label: '自动对比', desc: '决策树+随机森林+KNN+梯度提升' },
  { value: 'dt', label: '决策树', desc: '经典决策树，可解释性强' },
  { value: 'rf', label: '随机森林', desc: '集成方法，鲁棒性好' },
  { value: 'knn', label: 'KNN', desc: '近邻分类，简单有效' },
  { value: 'gb', label: '梯度提升', desc: 'Boosting方法，精度高' },
]

function ConfusionMatrixView({ data }: { data: { labels: string[]; matrix: number[][] } }) {
  const maxVal = Math.max(...data.matrix.flat(), 1)
  return (
    <div className="overflow-x-auto scrollbar-none">
      <table className="border-collapse text-xs">
        <thead>
          <tr>
            <th className="p-1.5 text-gray-500" />
            {data.labels.map((l) => (
              <th key={l} className="p-1.5 text-gray-400 font-medium" style={{ writingMode: 'vertical-rl', maxWidth: 60 }}>
                <span className="truncate" title={l}>{l.split('-').slice(0, 3).join('-')}</span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.matrix.map((row, i) => (
            <tr key={i}>
              <td className="p-1.5 text-gray-400 font-medium text-right whitespace-nowrap" title={data.labels[i]}>
                {data.labels[i].split('-').slice(0, 3).join('-')}
              </td>
              {row.map((val, j) => {
                const isDiag = i === j
                const intensity = val / maxVal
                return (
                  <td
                    key={j}
                    className="p-1.5 text-center font-mono border border-gray-800/50 min-w-[36px]"
                    style={{
                      backgroundColor: isDiag
                        ? `rgba(6, 182, 212, ${0.15 + intensity * 0.55})`
                        : val > 0 ? `rgba(239, 68, 68, ${0.1 + intensity * 0.4})` : 'transparent',
                      color: val > 0 ? (isDiag ? '#06b6d4' : '#f87171') : '#374151',
                    }}
                  >
                    {val}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="text-[10px] text-gray-600 mt-2">行=真实标签 列=预测标签 · 青色对角线=正确分类 红色=误分类</p>
    </div>
  )
}

export default function StackingRecognizer() {
  const [activeTab, setActiveTab] = useState<TabKey>('upload')
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null)
  const [cifText, setCifText] = useState('')
  const [uploading, setUploading] = useState(false)
  const [training, setTraining] = useState(false)
  const [predicting, setPredicting] = useState(false)
  const [trainProgress, setTrainProgress] = useState<{
    phase: string
    iteration?: number
    n_iterations?: number
    config_idx?: number
    total_steps?: number
    current_model?: string
    current_type?: string
    current_acc?: number
    best_acc_so_far?: number
  } | null>(null)
  const [trainResult, setTrainResult] = useState<TrainResult | null>(null)
  const [predictResult, setPredictResult] = useState<PredictResult | null>(null)
  const [models, setModels] = useState<ModelInfo[]>([])
  const [selectedModel, setSelectedModel] = useState('')
  const [testRatio, setTestRatio] = useState(0.2)
  const [maxDepth, setMaxDepth] = useState<number | ''>('')
  const [modelType, setModelType] = useState('auto')
  const [nIterations, setNIterations] = useState(3)
  const [cvFolds, setCvFolds] = useState(5)
  const [expandedLayer, setExpandedLayer] = useState<number | null>(null)
  const [scanResult, setScanResult] = useState<{ n_samples: number } | null>(null)
  const [scanning, setScanning] = useState(false)
  const [showCmDetail, setShowCmDetail] = useState(false)
  const [batchPredicting, setBatchPredicting] = useState(false)
  const [batchResult, setBatchResult] = useState<{
    success: boolean
    model_id?: string
    n_predicted?: number
    match_count?: number
    mismatch_count?: number
    accuracy?: number
    results?: { filename: string; topology: string; predicted: string; confidence: number; match: boolean; formula: string }[]
    error?: string
  } | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const loadModels = useCallback(async () => {
    try {
      const res = await fetch(`${API}/stacking/models`)
      const data = await res.json()
      if (data.success) {
        setModels(data.models || [])
        if (data.models?.length > 0 && !selectedModel) {
          setSelectedModel(data.models[0].model_id)
        }
      }
    } catch {}
  }, [selectedModel])

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    setUploadResult(null)
    const formData = new FormData()
    formData.append('file', file)
    try {
      const res = await fetch(`${API}/stacking/upload`, { method: 'POST', body: formData })
      const data = await res.json()
      setUploadResult(data)
      if (data.success && data.cif_text) setCifText(data.cif_text)
    } catch (err) {
      setUploadResult({ success: false, error: '上传失败: ' + String(err) })
    } finally {
      setUploading(false)
    }
  }

  const handlePasteAnalyze = async () => {
    if (!cifText.trim()) return
    setUploading(true)
    setUploadResult(null)
    try {
      const res = await fetch(`${API}/stacking/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cif_text: cifText }),
      })
      setUploadResult(await res.json())
    } catch (err) {
      setUploadResult({ success: false, error: '分析失败: ' + String(err) })
    } finally {
      setUploading(false)
    }
  }

  const handleScan = async () => {
    setScanning(true)
    setScanResult(null)
    try {
      const res = await fetch(`${API}/stacking/scan`, { method: 'POST' })
      setScanResult(await res.json())
    } catch { setScanResult(null) }
    finally { setScanning(false) }
  }

  const handleTrain = async () => {
    setTraining(true)
    setTrainResult(null)
    setTrainProgress(null)
    try {
      const body: Record<string, unknown> = { test_ratio: testRatio, model_type: modelType, n_iterations: nIterations, cv_folds: cvFolds }
      if (maxDepth !== '') body.max_depth = maxDepth
      const res = await fetch(`${API}/stacking/train/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const reader = res.body?.getReader()
      if (!reader) throw new Error('无法读取流')
      const decoder = new TextDecoder()
      let buffer = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        let eventType = ''
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim()
          } else if (line.startsWith('data: ')) {
            const dataStr = line.slice(6)
            try {
              const data = JSON.parse(dataStr)
              if (eventType === 'progress') {
                setTrainProgress(data)
              } else if (eventType === 'result') {
                setTrainResult(data)
                if (data.success) loadModels()
              } else if (eventType === 'error') {
                setTrainResult({ success: false, error: data.error })
              }
            } catch {}
            eventType = ''
          }
        }
      }
    } catch (err) {
      setTrainResult({ success: false, error: '训练失败: ' + String(err) })
    } finally {
      setTraining(false)
      setTrainProgress(null)
    }
  }

  const handlePredict = async () => {
    if (!selectedModel || !cifText.trim()) return
    setPredicting(true)
    setPredictResult(null)
    try {
      const res = await fetch(`${API}/stacking/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_id: selectedModel, cif_text: cifText }),
      })
      setPredictResult(await res.json())
    } catch (err) {
      setPredictResult({ success: false, error: '预测失败: ' + String(err) })
    } finally {
      setPredicting(false)
    }
  }

  const handleDeleteModel = async (modelId: string) => {
    try {
      await fetch(`${API}/stacking/models/${modelId}`, { method: 'DELETE' })
      loadModels()
      if (selectedModel === modelId) setSelectedModel('')
    } catch {}
  }

  const handleBatchPredict = async () => {
    if (!selectedModel) return
    setBatchPredicting(true)
    setBatchResult(null)
    try {
      const res = await fetch(`${API}/stacking/batch_predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_id: selectedModel, limit: 200 }),
      })
      setBatchResult(await res.json())
    } catch (err) {
      setBatchResult({ success: false, error: '批量预测失败: ' + String(err) })
    } finally {
      setBatchPredicting(false)
    }
  }

  const tabs: { key: TabKey; label: string; icon: typeof Upload }[] = [
    { key: 'upload', label: '上传分析', icon: Upload },
    { key: 'train', label: '训练模型', icon: Brain },
    { key: 'predict', label: '预测识别', icon: Zap },
  ]

  return (
    <div className="space-y-4 sm:space-y-6">
      <div>
        <h1 className="text-xl sm:text-2xl font-bold text-white flex items-center gap-2">
          <Layers className="w-6 h-6 text-cyan-400" />
          堆垛特征识别
        </h1>
        <p className="text-sm text-gray-400 mt-1">上传CIF文件，使用机器学习算法自动识别晶体结构的堆垛特征</p>
      </div>

      <div className="flex gap-2 overflow-x-auto scrollbar-none">
        {tabs.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`flex items-center gap-2 px-3 py-2.5 sm:px-4 sm:py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap touch-manipulation ${
              activeTab === key ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30' : 'bg-gray-800 border border-gray-700 text-gray-400 hover:text-gray-200'
            }`}
          >
            <Icon className="w-4 h-4" />{label}
          </button>
        ))}
      </div>

      {activeTab === 'upload' && (
        <div className="space-y-4">
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-4 sm:p-6">
            <h2 className="text-lg font-semibold text-white mb-4">上传CIF文件</h2>
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="flex-1">
                <div onClick={() => fileInputRef.current?.click()} className="border-2 border-dashed border-gray-600 hover:border-cyan-500/50 rounded-xl p-8 text-center cursor-pointer transition-colors">
                  {uploading ? <Loader2 className="w-10 h-10 text-cyan-400 mx-auto animate-spin" /> : <Upload className="w-10 h-10 text-gray-500 mx-auto mb-2" />}
                  <p className="text-sm text-gray-400">{uploading ? '解析中...' : '点击上传CIF文件'}</p>
                  <p className="text-xs text-gray-600 mt-1">支持 .cif 格式</p>
                </div>
                <input ref={fileInputRef} type="file" accept=".cif" onChange={handleFileUpload} className="hidden" />
              </div>
              <div className="flex items-center text-gray-500 text-sm">或</div>
              <div className="flex-1">
                <textarea value={cifText} onChange={(e) => setCifText(e.target.value)} placeholder="粘贴CIF文本内容..." className="w-full h-40 bg-gray-800 border border-gray-700 rounded-xl px-3 py-2 text-sm text-gray-200 font-mono placeholder-gray-600 focus:outline-none focus:border-cyan-500 resize-none" />
                <button onClick={handlePasteAnalyze} disabled={uploading || !cifText.trim()} className="mt-2 w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 text-sm font-medium hover:bg-cyan-500/20 transition-colors disabled:opacity-50 min-h-[44px]">
                  {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileText className="w-4 h-4" />}分析CIF文本
                </button>
              </div>
            </div>
          </div>

          {uploadResult && !uploadResult.success && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 flex items-start gap-3">
              <XCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
              <div><p className="text-sm text-red-400 font-medium">解析失败</p><p className="text-xs text-red-400/70 mt-1">{uploadResult.error}</p></div>
            </div>
          )}

          {uploadResult && uploadResult.success && (
            <div className="space-y-4">
              <div className="bg-gray-900 border border-gray-700 rounded-xl p-4 sm:p-6">
                <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2"><CheckCircle2 className="w-5 h-5 text-emerald-400" />结构信息</h2>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {[{ label: '化学式', value: uploadResult.formula }, { label: '原子数', value: uploadResult.n_atoms }, { label: '空间群', value: uploadResult.space_group || 'P1' }, { label: '晶格 a', value: uploadResult.lattice?.a?.toFixed(3) + ' Å' }].map(({ label, value }) => (
                    <div key={label} className="bg-gray-800/50 rounded-lg p-3"><p className="text-xs text-gray-500">{label}</p><p className="text-sm font-medium text-white mt-1">{value}</p></div>
                  ))}
                </div>
              </div>

              {uploadResult.layer_analysis && uploadResult.layer_analysis.length > 0 && (
                <div className="bg-gray-900 border border-gray-700 rounded-xl p-4 sm:p-6">
                  <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2"><Layers className="w-5 h-5 text-violet-400" />层分析结果<span className="text-xs text-gray-500 font-normal">({uploadResult.layer_analysis.length} 层)</span></h2>
                  <div className="space-y-2">
                    {uploadResult.layer_analysis.map((layer, i) => (
                      <div key={i} className="bg-gray-800/50 rounded-lg overflow-hidden">
                        <button onClick={() => setExpandedLayer(expandedLayer === i ? null : i)} className="w-full flex items-center gap-3 p-3 text-left hover:bg-gray-700/30 transition-colors">
                          <span className="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold text-white" style={{ backgroundColor: LAYER_TYPE_COLORS[layer.predicted_type] || '#6b7280' }}>{layer.predicted_type.substring(0, 2)}</span>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2"><span className="text-sm font-medium text-white">第 {i + 1} 层</span><span className="px-2 py-0.5 rounded text-xs font-medium" style={{ backgroundColor: (LAYER_TYPE_COLORS[layer.predicted_type] || '#6b7280') + '25', color: LAYER_TYPE_COLORS[layer.predicted_type] || '#6b7280' }}>{layer.predicted_type}</span></div>
                            <p className="text-xs text-gray-500 mt-0.5">z={layer.z} · {layer.n_atoms}原子 · 网格 {layer.grid_x}×{layer.grid_y}</p>
                          </div>
                          {expandedLayer === i ? <ChevronDown className="w-4 h-4 text-gray-500" /> : <ChevronRight className="w-4 h-4 text-gray-500" />}
                        </button>
                        {expandedLayer === i && (
                          <div className="px-3 pb-3 pt-1 border-t border-gray-700/50">
                            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs">
                              <div><span className="text-gray-500">X:O比</span><span className="ml-2 text-gray-300">{layer.x_to_o_ratio === Infinity || layer.x_to_o_ratio === -Infinity ? '∞' : typeof layer.x_to_o_ratio === 'number' && Number.isFinite(layer.x_to_o_ratio) ? layer.x_to_o_ratio.toFixed(3) : '—'}</span></div>
                              <div><span className="text-gray-500">含氧</span><span className="ml-2 text-gray-300">{layer.has_oxygen ? '是' : '否'}</span></div>
                              <div className="col-span-2 sm:col-span-3"><span className="text-gray-500">元素组成</span><div className="flex flex-wrap gap-1 mt-1">{Object.entries(layer.elements).map(([el, cnt]) => (<span key={el} className="px-1.5 py-0.5 bg-gray-700/50 rounded text-gray-300">{el}×{cnt}</span>))}</div></div>
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {uploadResult.features && (
                <div className="bg-gray-900 border border-gray-700 rounded-xl p-4 sm:p-6">
                  <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2"><BarChart3 className="w-5 h-5 text-amber-400" />提取的特征</h2>
                  <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
                    {Object.entries(uploadResult.features).filter(([, v]) => typeof v === 'number').sort(([a], [b]) => a.localeCompare(b)).map(([key, value]) => (
                      <div key={key} className="bg-gray-800/50 rounded-lg p-2.5"><p className="text-[10px] text-gray-500 truncate">{key}</p><p className="text-xs font-mono text-gray-300 mt-0.5">{typeof value === 'number' ? Number.isInteger(value) ? value : value.toFixed(4) : String(value)}</p></div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {activeTab === 'train' && (
        <div className="space-y-4">
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-4 sm:p-6">
            <h2 className="text-lg font-semibold text-white mb-4">训练机器学习模型</h2>

            <div className="mb-4">
              <button onClick={handleScan} disabled={scanning} className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-violet-500/10 text-violet-400 border border-violet-500/30 text-sm font-medium hover:bg-violet-500/20 transition-colors disabled:opacity-50 min-h-[44px]">
                {scanning ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}扫描数据库CIF文件
              </button>
              {scanResult && <p className="text-sm text-gray-400 mt-2">找到 <span className="text-white font-medium">{scanResult.n_samples}</span> 个CIF样本</p>}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-xs text-gray-400 mb-1.5">测试集比例</label>
                <div className="flex items-center gap-3">
                  <input type="range" min={5} max={50} value={Math.round(testRatio * 100)} onChange={(e) => setTestRatio(Number(e.target.value) / 100)} className="flex-1 accent-cyan-500" />
                  <span className="text-sm text-white font-mono w-12 text-right">{Math.round(testRatio * 100)}%</span>
                </div>
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1.5">最大深度 (留空=自动)</label>
                <input type="number" value={maxDepth} onChange={(e) => setMaxDepth(e.target.value === '' ? '' : Number(e.target.value))} placeholder="自动" min={1} max={50} className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-cyan-500" />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1.5">模型类型</label>
                <select value={modelType} onChange={(e) => setModelType(e.target.value)} className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-cyan-500">
                  {MODEL_TYPE_OPTIONS.map((o) => (<option key={o.value} value={o.value}>{o.label} - {o.desc}</option>))}
                </select>
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1.5">迭代次数 (多随机种子)</label>
                <input type="number" value={nIterations} onChange={(e) => setNIterations(Number(e.target.value))} min={1} max={20} className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-cyan-500" />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1.5">交叉验证折数</label>
                <input type="number" value={cvFolds} onChange={(e) => setCvFolds(Number(e.target.value))} min={2} max={10} className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-cyan-500" />
              </div>
            </div>

            <button onClick={handleTrain} disabled={training} className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-cyan-500 text-white font-medium hover:bg-cyan-400 transition-colors disabled:opacity-50 min-h-[44px]">
              {training ? <><Loader2 className="w-5 h-5 animate-spin" />训练中...</> : <><Brain className="w-5 h-5" />开始训练</>}
            </button>

            {training && trainProgress && (
              <div className="mt-4 bg-gray-800/50 border border-gray-700/50 rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-400">
                    {trainProgress.phase === 'init' && '初始化训练...'}
                    {trainProgress.phase === 'training' && `迭代 ${trainProgress.iteration}/${trainProgress.n_iterations}`}
                    {trainProgress.phase === 'finalizing' && '生成最终模型...'}
                  </span>
                  <span className="text-cyan-400 font-mono">
                    {trainProgress.config_idx && trainProgress.total_steps
                      ? `${trainProgress.config_idx}/${trainProgress.total_steps}`
                      : ''}
                  </span>
                </div>
                <div className="w-full bg-gray-700/50 rounded-full h-2 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-violet-500 transition-all duration-300"
                    style={{ width: `${trainProgress.config_idx && trainProgress.total_steps ? Math.round((trainProgress.config_idx / trainProgress.total_steps) * 100) : 5}%` }}
                  />
                </div>
                {trainProgress.current_model && (
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-500 truncate">当前: {trainProgress.current_model}</span>
                    <span className="text-emerald-400 font-mono">
                      最佳: {((trainProgress.best_acc_so_far ?? 0) * 100).toFixed(1)}%
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>

          {trainResult && !trainResult.success && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 flex items-start gap-3">
              <XCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
              <div><p className="text-sm text-red-400 font-medium">训练失败</p><p className="text-xs text-red-400/70 mt-1">{trainResult.error}</p></div>
            </div>
          )}

          {trainResult && trainResult.success && (
            <div className="space-y-4">
              <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-4 flex items-start gap-3">
                <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm text-emerald-400 font-medium">训练成功!</p>
                  <p className="text-xs text-emerald-400/70 mt-1">模型ID: {trainResult.model_id} · 测试了 {trainResult.n_configs_tested} 种配置 · {trainResult.n_iterations} 轮迭代</p>
                </div>
              </div>

              <div className="bg-gray-900 border border-gray-700 rounded-xl p-4 sm:p-6">
                <h3 className="text-base font-semibold text-white mb-3">最优模型</h3>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {[
                    { label: '测试集准确率', value: `${((trainResult.best_params?.test_accuracy as number || 0) * 100).toFixed(1)}%`, highlight: true },
                    { label: '交叉验证', value: `${((trainResult.best_params?.cv_mean as number || 0) * 100).toFixed(1)}% ± ${((trainResult.best_params?.cv_std as number || 0) * 100).toFixed(1)}%` },
                    { label: '模型类型', value: trainResult.best_params?.model_name as string || '-' },
                    { label: '训练集准确率', value: `${((trainResult.best_params?.train_accuracy as number || 0) * 100).toFixed(1)}%` },
                    { label: '有效样本数', value: trainResult.n_valid_samples },
                    { label: '拓扑类别数', value: trainResult.n_classes },
                    { label: '训练/测试', value: `${trainResult.best_params?.n_train as number || 0}/${trainResult.best_params?.n_test as number || 0}` },
                    { label: '最优种子', value: String(trainResult.best_params?.seed ?? '-') },
                  ].map(({ label, value, highlight }) => (
                    <div key={label} className={`rounded-lg p-3 ${highlight ? 'bg-cyan-500/10 border border-cyan-500/20' : 'bg-gray-800/50'}`}>
                      <p className="text-xs text-gray-500">{label}</p>
                      <p className={`text-lg font-bold mt-1 ${highlight ? 'text-cyan-400' : 'text-white'}`}>{value}</p>
                    </div>
                  ))}
                </div>
              </div>

              {trainResult.model_comparison && Object.keys(trainResult.model_comparison).length > 1 && (
                <div className="bg-gray-900 border border-gray-700 rounded-xl p-4 sm:p-6">
                  <h3 className="text-base font-semibold text-white mb-3 flex items-center gap-2"><GitCompare className="w-5 h-5 text-violet-400" />模型对比</h3>
                  <div className="overflow-x-auto scrollbar-none">
                    <table className="w-full text-sm">
                      <thead><tr className="text-gray-500 text-xs"><th className="text-left p-2">模型</th><th className="text-right p-2">最佳准确率</th><th className="text-right p-2">平均准确率</th><th className="text-right p-2">测试次数</th></tr></thead>
                      <tbody>
                        {Object.entries(trainResult.model_comparison).sort(([, a], [, b]) => b.best_acc - a.best_acc).map(([type, info]) => (
                          <tr key={type} className="border-t border-gray-800"><td className="p-2 text-gray-300">{info.name}</td><td className="p-2 text-right font-mono text-cyan-400">{(info.best_acc * 100).toFixed(1)}%</td><td className="p-2 text-right font-mono text-gray-400">{(info.avg_acc * 100).toFixed(1)}%</td><td className="p-2 text-right text-gray-500">{info.count}</td></tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {trainResult.confusion_matrix && (
                <div className="bg-gray-900 border border-gray-700 rounded-xl p-4 sm:p-6">
                  <h3 className="text-base font-semibold text-white mb-3 flex items-center gap-2"><Grid3X3 className="w-5 h-5 text-amber-400" />混淆矩阵</h3>
                  {showCmDetail ? (
                    <ConfusionMatrixView data={trainResult.confusion_matrix} />
                  ) : (
                    <button onClick={() => setShowCmDetail(true)} className="text-sm text-cyan-400 hover:text-cyan-300 transition-colors">点击展开混淆矩阵</button>
                  )}
                </div>
              )}

              {trainResult.class_distribution && Object.keys(trainResult.class_distribution).length > 0 && (
                <div className="bg-gray-900 border border-gray-700 rounded-xl p-4 sm:p-6">
                  <h3 className="text-base font-semibold text-white mb-3">类别分布</h3>
                  <div className="space-y-2">
                    {Object.entries(trainResult.class_distribution).sort(([, a], [, b]) => b - a).map(([topo, count]) => {
                      const maxCount = Math.max(...Object.values(trainResult.class_distribution || {}))
                      return (
                        <div key={topo} className="flex items-center gap-2">
                          <span className="text-xs text-gray-400 w-40 sm:w-64 truncate" title={topo}>{topo}</span>
                          <div className="flex-1 bg-gray-800 rounded-full h-4 overflow-hidden"><div className="h-full bg-cyan-500/60 rounded-full" style={{ width: `${maxCount > 0 ? (count / maxCount) * 100 : 0}%` }} /></div>
                          <span className="text-xs text-gray-400 w-8 text-right">{count}</span>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}

              {trainResult.feature_importances && trainResult.feature_importances.length > 0 && (
                <div className="bg-gray-900 border border-gray-700 rounded-xl p-4 sm:p-6">
                  <h3 className="text-base font-semibold text-white mb-3">特征重要性 Top 10</h3>
                  <div className="space-y-2">
                    {trainResult.feature_importances.slice(0, 10).map(([name, imp]) => {
                      const maxImp = trainResult.feature_importances?.[0]?.[1] || 1
                      return (
                        <div key={name} className="flex items-center gap-2">
                          <span className="text-xs text-gray-400 w-32 sm:w-40 truncate">{name}</span>
                          <div className="flex-1 bg-gray-800 rounded-full h-3 overflow-hidden"><div className="h-full bg-violet-500/60 rounded-full" style={{ width: `${maxImp > 0 ? (imp / maxImp) * 100 : 0}%` }} /></div>
                          <span className="text-xs text-gray-400 w-16 text-right">{(imp * 100).toFixed(1)}%</span>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {activeTab === 'predict' && (
        <div className="space-y-4">
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-4 sm:p-6">
            <h2 className="text-lg font-semibold text-white mb-4">预测堆垛特征</h2>
            <div className="mb-4">
              <div className="flex items-center justify-between mb-2"><label className="text-xs text-gray-400">选择模型</label><button onClick={loadModels} className="text-xs text-cyan-400 hover:text-cyan-300 transition-colors">刷新列表</button></div>
              {models.length === 0 ? (
                <div className="bg-gray-800/50 rounded-lg p-4 text-center"><AlertCircle className="w-6 h-6 text-amber-400 mx-auto mb-2" /><p className="text-sm text-gray-400">暂无可用模型</p><p className="text-xs text-gray-600 mt-1">请先在"训练模型"页签训练一个模型</p></div>
              ) : (
                <div className="space-y-2">
                  {models.map((m) => (
                    <div key={m.model_id} onClick={() => setSelectedModel(m.model_id)} className={`flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-colors ${selectedModel === m.model_id ? 'bg-cyan-500/10 border border-cyan-500/30' : 'bg-gray-800/50 border border-transparent hover:bg-gray-700/50'}`}>
                      <div className="flex-1 min-w-0"><p className="text-sm text-white font-medium">{m.model_id}</p><p className="text-xs text-gray-500">{m.n_samples}样本 · {m.n_classes}类</p></div>
                      <div className="text-right"><p className="text-sm font-bold text-cyan-400">{(m.test_accuracy * 100).toFixed(1)}%</p><p className="text-xs text-gray-500">准确率</p></div>
                      <button onClick={(e) => { e.stopPropagation(); handleDeleteModel(m.model_id) }} className="touch-icon-btn text-gray-600 hover:text-red-400 transition-colors"><Trash2 className="w-4 h-4" /></button>
                    </div>
                  ))}
                </div>
              )}
            </div>
            {!cifText.trim() && <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3 mb-4"><p className="text-xs text-amber-400">请先在"上传分析"页签上传CIF文件或粘贴CIF文本</p></div>}
            <button onClick={handlePredict} disabled={predicting || !selectedModel || !cifText.trim()} className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-cyan-500 text-white font-medium hover:bg-cyan-400 transition-colors disabled:opacity-50 min-h-[44px]">
              {predicting ? <><Loader2 className="w-5 h-5 animate-spin" />预测中...</> : <><Zap className="w-5 h-5" />预测堆垛类型</>}
            </button>
          </div>

          {predictResult && !predictResult.success && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 flex items-start gap-3"><XCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" /><div><p className="text-sm text-red-400 font-medium">预测失败</p><p className="text-xs text-red-400/70 mt-1">{predictResult.error}</p></div></div>
          )}

          {predictResult && predictResult.success && (
            <div className="space-y-4">
              <div className="bg-cyan-500/10 border border-cyan-500/30 rounded-xl p-4 sm:p-6">
                <h3 className="text-base font-semibold text-white mb-3">预测结果</h3>
                <div className="flex items-center gap-4 mb-4">
                  <div className="bg-cyan-500/20 rounded-xl p-4 text-center min-w-[120px]"><p className="text-xs text-cyan-400/70">预测拓扑</p><p className="text-lg font-bold text-cyan-400 mt-1">{predictResult.predicted_topology}</p></div>
                  <div className="bg-gray-800/50 rounded-xl p-4 text-center min-w-[100px]"><p className="text-xs text-gray-500">置信度</p><p className="text-lg font-bold text-white mt-1">{((predictResult.confidence || 0) * 100).toFixed(1)}%</p></div>
                </div>
                {predictResult.top_predictions && predictResult.top_predictions.length > 0 && (
                  <div><p className="text-xs text-gray-400 mb-2">Top 预测</p><div className="space-y-1.5">
                    {predictResult.top_predictions.map(([topo, prob]) => {
                      const maxProb = predictResult.top_predictions?.[0]?.[1] || 1
                      return (<div key={topo} className="flex items-center gap-2"><span className="text-xs text-gray-400 w-48 sm:w-64 truncate">{topo}</span><div className="flex-1 bg-gray-800 rounded-full h-3 overflow-hidden"><div className="h-full bg-cyan-500/60 rounded-full" style={{ width: `${maxProb > 0 ? (prob / maxProb) * 100 : 0}%` }} /></div><span className="text-xs text-gray-400 w-14 text-right">{(prob * 100).toFixed(1)}%</span></div>)
                    })}
                  </div></div>
                )}
              </div>
              {predictResult.layer_analysis && predictResult.layer_analysis.length > 0 && (
                <div className="bg-gray-900 border border-gray-700 rounded-xl p-4 sm:p-6">
                  <h3 className="text-base font-semibold text-white mb-3">层分析</h3>
                  <div className="flex flex-wrap gap-2">
                    {predictResult.layer_analysis.map((layer, i) => (
                      <div key={i} className="flex items-center gap-2 bg-gray-800/50 rounded-lg px-3 py-2">
                        <span className="w-6 h-6 rounded flex items-center justify-center text-[10px] font-bold text-white" style={{ backgroundColor: LAYER_TYPE_COLORS[layer.predicted_type] || '#6b7280' }}>{layer.predicted_type.substring(0, 2)}</span>
                        <div><p className="text-xs font-medium text-white">{layer.predicted_type}</p><p className="text-[10px] text-gray-500">z={layer.z}</p></div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          <div className="bg-gray-900 border border-gray-700 rounded-xl p-4 sm:p-6 mt-4">
            <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
              <GitCompare className="w-5 h-5 text-violet-400" />
              数据库批量预测
            </h2>
            <p className="text-xs text-gray-500 mb-3">使用选定模型对数据库中的材料进行批量预测，验证模型泛化能力</p>
            <button onClick={handleBatchPredict} disabled={batchPredicting || !selectedModel} className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-violet-500 text-white font-medium hover:bg-violet-400 transition-colors disabled:opacity-50 min-h-[44px]">
              {batchPredicting ? <><Loader2 className="w-5 h-5 animate-spin" />批量预测中...</> : <><GitCompare className="w-5 h-5" />批量预测数据库材料</>}
            </button>
          </div>

          {batchResult && !batchResult.success && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 flex items-start gap-3"><XCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" /><div><p className="text-sm text-red-400 font-medium">批量预测失败</p><p className="text-xs text-red-400/70 mt-1">{batchResult.error}</p></div></div>
          )}

          {batchResult && batchResult.success && (
            <div className="space-y-4">
              <div className="bg-violet-500/10 border border-violet-500/30 rounded-xl p-4 sm:p-6">
                <h3 className="text-base font-semibold text-white mb-3">批量预测结果</h3>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
                  <div className="bg-gray-800/50 rounded-lg p-3 text-center"><p className="text-xs text-gray-500">预测总数</p><p className="text-lg font-bold text-white">{batchResult.n_predicted}</p></div>
                  <div className="bg-gray-800/50 rounded-lg p-3 text-center"><p className="text-xs text-gray-500">匹配数</p><p className="text-lg font-bold text-emerald-400">{batchResult.match_count}</p></div>
                  <div className="bg-gray-800/50 rounded-lg p-3 text-center"><p className="text-xs text-gray-500">不匹配数</p><p className="text-lg font-bold text-red-400">{batchResult.mismatch_count}</p></div>
                  <div className="bg-gray-800/50 rounded-lg p-3 text-center"><p className="text-xs text-gray-500">准确率</p><p className="text-lg font-bold text-cyan-400">{((batchResult.accuracy || 0) * 100).toFixed(1)}%</p></div>
                </div>
              </div>

              {batchResult.results && batchResult.results.length > 0 && (
                <div className="bg-gray-900 border border-gray-700 rounded-xl p-4 sm:p-6 overflow-x-auto">
                  <h3 className="text-base font-semibold text-white mb-3">预测详情</h3>
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-700">
                        <th className="text-left text-xs text-gray-400 py-2 px-2">文件名</th>
                        <th className="text-left text-xs text-gray-400 py-2 px-2">化学式</th>
                        <th className="text-left text-xs text-gray-400 py-2 px-2">真实拓扑</th>
                        <th className="text-left text-xs text-gray-400 py-2 px-2">预测拓扑</th>
                        <th className="text-left text-xs text-gray-400 py-2 px-2">置信度</th>
                        <th className="text-center text-xs text-gray-400 py-2 px-2">结果</th>
                      </tr>
                    </thead>
                    <tbody>
                      {batchResult.results.map((r, i) => (
                        <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                          <td className="py-2 px-2 text-xs text-gray-400 truncate max-w-[120px]" title={r.filename}>{r.filename}</td>
                          <td className="py-2 px-2 text-xs text-white font-mono">{r.formula}</td>
                          <td className="py-2 px-2 text-xs text-gray-300">{r.topology}</td>
                          <td className="py-2 px-2 text-xs text-white">{r.predicted}</td>
                          <td className="py-2 px-2 text-xs text-gray-400 font-mono">{(r.confidence * 100).toFixed(1)}%</td>
                          <td className="py-2 px-2 text-center">{r.match ? <CheckCircle2 className="w-4 h-4 text-emerald-400 inline" /> : <XCircle className="w-4 h-4 text-red-400 inline" />}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
