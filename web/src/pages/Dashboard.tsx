import { useState, useEffect, useCallback, useRef } from 'react'
import {
  Cpu, Play, Database, Activity, Trash2,
  CheckCircle2, AlertCircle, Clock,
  BarChart3, RefreshCw, Upload, Key,
  XCircle, Loader2, Plus, Eye,
  Zap, ShieldCheck, Star, LogIn, LogOut,
  Layers, TrendingUp, Target,
} from 'lucide-react'

const BASE = '/CGCPT/api'
const AUTH_KEY = 'cgcpt_auth_token'

async function apiFetch<T = unknown>(path: string, opts?: RequestInit): Promise<T> {
  const token = localStorage.getItem(AUTH_KEY)
  const headers: Record<string, string> = { ...(opts?.headers as Record<string, string> || {}) }
  if (token) headers['Authorization'] = `Bearer ${token}`
  if (!(opts?.body instanceof FormData)) headers['Content-Type'] = 'application/json'
  const res = await fetch(`${BASE}${path}`, { ...opts, headers })
  return res.json()
}

interface Algorithm {
  id: string; name: string; description: string; algorithm_type: string
  entry_point: string; input_schema: any; output_schema: any; default_config: any; is_active: boolean
}
interface TaskItem {
  task_id: string; algorithm_id: string; status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  progress: number; progress_message: string | null; error_message: string | null
  created_at: string | null; started_at: string | null; completed_at: string | null
}
interface MaterialItem {
  id: string; formula: string; space_group: string; topology_id: string
  is_verified: boolean; source: string; n_atoms: number; created_at: string | null
}
interface ModelItem {
  id: string; name: string; model_type: string; metrics: Record<string, any>
  feature_keys: string[] | null; file_path: string | null; is_active: boolean; created_at: string | null
}
interface Stats {
  materials: { total: number; verified: number; raw: number }
  prototypes: number; tasks: { pending: number; running: number; completed: number; failed: number; total: number }
  algorithms: number; models: number
}

const STATUS_CFG: Record<string, { icon: any; color: string; bg: string; label: string }> = {
  pending: { icon: Clock, color: 'text-yellow-400', bg: 'bg-yellow-400/10', label: '等待中' },
  running: { icon: Loader2, color: 'text-cyan-400', bg: 'bg-cyan-400/10', label: '运行中' },
  completed: { icon: CheckCircle2, color: 'text-emerald-400', bg: 'bg-emerald-400/10', label: '已完成' },
  failed: { icon: XCircle, color: 'text-red-400', bg: 'bg-red-400/10', label: '失败' },
  cancelled: { icon: AlertCircle, color: 'text-gray-400', bg: 'bg-gray-400/10', label: '已取消' },
}
const TYPE_COLORS: Record<string, string> = {
  training: 'bg-purple-500/20 text-purple-300', prediction: 'bg-cyan-500/20 text-cyan-300',
  generation: 'bg-orange-500/20 text-orange-300', validation: 'bg-green-500/20 text-green-300',
  verification: 'bg-green-500/20 text-green-300', import: 'bg-gray-500/20 text-gray-300',
}

function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_CFG[status] || STATUS_CFG.pending
  const Icon = cfg.icon
  return (
    <span className={`inline-flex items-center gap-1 px-1.5 sm:px-2 py-0.5 rounded text-[10px] sm:text-xs font-medium ${cfg.bg} ${cfg.color}`}>
      <Icon size={11} className={status === 'running' ? 'animate-spin' : ''} /> <span className="hidden sm:inline">{cfg.label}</span>
    </span>
  )
}
function TypeBadge({ type }: { type: string }) {
  const cls = TYPE_COLORS[type] || 'bg-gray-500/20 text-gray-300'
  return <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] sm:text-xs font-medium ${cls}`}>{type}</span>
}

type TabKey = 'dashboard' | 'algorithms' | 'tasks' | 'materials' | 'models' | 'stacking'

export default function Dashboard() {
  const [tab, setTab] = useState<TabKey>('dashboard')
  const [algorithms, setAlgorithms] = useState<Algorithm[]>([])
  const [tasks, setTasks] = useState<TaskItem[]>([])
  const [materials, setMaterials] = useState<MaterialItem[]>([])
  const [models, setModels] = useState<ModelItem[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(false)
  const [isAdmin, setIsAdmin] = useState(false)
  const [showLogin, setShowLogin] = useState(false)
  const [loginForm, setLoginForm] = useState({ username: '', password: '' })
  const [loginError, setLoginError] = useState('')

  const [showRegisterModal, setShowRegisterModal] = useState(false)
  const [showRunModal, setShowRunModal] = useState(false)
  const [showTaskDetail, setShowTaskDetail] = useState(false)
  const [selectedAlgo, setSelectedAlgo] = useState<Algorithm | null>(null)
  const [selectedTask, setSelectedTask] = useState<TaskItem | null>(null)
  const [regForm, setRegForm] = useState({ id: '', name: '', description: '', algorithm_type: 'prediction', entry_point: '' })
  const [runInput, setRunInput] = useState('')
  const [matPage, setMatPage] = useState(1)
  const [matTotal, setMatTotal] = useState(0)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)

  const [stackingModels, setStackingModels] = useState<any[]>([])
  const [training, setTraining] = useState(false)
  const [trainResult, setTrainResult] = useState<any>(null)
  const [predModes, setPredModes] = useState('XO3, M7, XO3, M7, XO3, XO3')
  const [predStack, setPredStack] = useState('ABC')
  const [predModelId, setPredModelId] = useState('')
  const [predicting, setPredicting] = useState(false)
  const [predResult, setPredResult] = useState<any>(null)
  const [selfImproving, setSelfImproving] = useState(false)
  const [improveResult, setImproveResult] = useState<any>(null)
  const [improveHistory, setImproveHistory] = useState<any[]>([])
  const [errorAnalysis, setErrorAnalysis] = useState<any>(null)

  const checkAuth = useCallback(async () => {
    const token = localStorage.getItem(AUTH_KEY)
    if (!token) { setIsAdmin(false); return }
    try {
      const data = await apiFetch<{ success: boolean }>('/auth/check')
      setIsAdmin(data.success)
    } catch { setIsAdmin(false) }
  }, [])

  const loadStats = useCallback(async () => {
    try { const data = await apiFetch<{ success: boolean } & Stats>('/db/stats'); if (data.success) setStats(data) } catch {}
  }, [])
  const loadAlgorithms = useCallback(async () => {
    try { const data = await apiFetch<{ success: boolean; algorithms: Algorithm[] }>('/algorithms'); if (data.success) setAlgorithms(data.algorithms) } catch {}
  }, [])
  const loadTasks = useCallback(async () => {
    try { const data = await apiFetch<{ success: boolean; tasks: TaskItem[] }>('/tasks?limit=50'); if (data.success) setTasks(data.tasks) } catch {}
  }, [])
  const loadMaterials = useCallback(async (page = 1) => {
    setLoading(true)
    try {
      const data = await apiFetch<{ success: boolean; materials: MaterialItem[]; total: number; page: number }>(`/db/materials?page=${page}&page_size=50`)
      if (data.success) { setMaterials(data.materials); setMatTotal(data.total); setMatPage(data.page) }
    } catch {} finally { setLoading(false) }
  }, [])
  const loadModels = useCallback(async () => {
    try { const data = await apiFetch<{ success: boolean; models: ModelItem[] }>('/models'); if (data.success) setModels(data.models) } catch {}
  }, [])
  const loadStackingModels = useCallback(async () => {
    try {
      const data = await apiFetch<{ success: boolean; models: any[] }>('/stacking/models')
      if (data.success) {
        setStackingModels(data.models)
        if (data.models.length > 0 && !predModelId) {
          const active = data.models.find((m: any) => m.is_active)
          setPredModelId(active?.id || data.models[0]?.id || '')
        }
      }
    } catch {}
  }, [])

  useEffect(() => { checkAuth(); loadStats(); loadAlgorithms(); loadTasks(); loadModels(); loadStackingModels() }, [checkAuth, loadStats, loadAlgorithms, loadTasks, loadModels, loadStackingModels])
  useEffect(() => { if (tab === 'materials') loadMaterials(1) }, [tab, loadMaterials])

  const handleLogin = async () => {
    setLoginError('')
    try {
      const data = await apiFetch<{ success: boolean; token?: string; error?: string }>('/auth/login', {
        method: 'POST', body: JSON.stringify(loginForm),
      })
      if (data.success && data.token) {
        localStorage.setItem(AUTH_KEY, data.token)
        setIsAdmin(true)
        setShowLogin(false)
        setLoginForm({ username: '', password: '' })
      } else {
        setLoginError(data.error || '登录失败')
      }
    } catch { setLoginError('网络错误') }
  }

  const handleLogout = () => {
    localStorage.removeItem(AUTH_KEY)
    setIsAdmin(false)
  }

  const handleRegister = async () => {
    try {
      const res = await apiFetch('/algorithms', { method: 'POST', body: JSON.stringify(regForm) })
      if ((res as any).success) { setShowRegisterModal(false); setRegForm({ id: '', name: '', description: '', algorithm_type: 'prediction', entry_point: '' }); loadAlgorithms() }
    } catch {}
  }

  const handleRun = async () => {
    if (!selectedAlgo) return
    try {
      let inputData = {}
      if (runInput.trim()) { try { inputData = JSON.parse(runInput) } catch { inputData = { raw_input: runInput } } }
      const res = await apiFetch('/tasks', { method: 'POST', body: JSON.stringify({ algorithm_id: selectedAlgo.id, input_data: inputData }) })
      if ((res as any).success) { setShowRunModal(false); setSelectedAlgo(null); setRunInput(''); loadTasks() }
    } catch {}
  }

  const handleDeleteMaterial = async (id: string) => {
    try { await apiFetch(`/db/materials/${id}`, { method: 'DELETE' }); loadMaterials(matPage); loadStats() } catch {}
  }

  const handleModelUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('name', file.name.replace('.pkl', ''))
      formData.append('model_type', 'decision_tree')
      const res = await apiFetch<{ success: boolean; error?: string }>('/models/upload', { method: 'POST', body: formData })
      if ((res as any).success) { loadModels(); loadStats() } else { alert((res as any).error || '上传失败') }
    } catch { alert('上传失败') } finally { setUploading(false); if (fileInputRef.current) fileInputRef.current.value = '' }
  }

  const handleDeleteModel = async (id: string) => {
    try { await apiFetch(`/models/${id}`, { method: 'DELETE' }); loadModels() } catch {}
  }

  const handleActivateModel = async (id: string) => {
    try { await apiFetch(`/models/${id}/activate`, { method: 'POST' }); loadModels() } catch {}
  }

  const refreshAll = () => { loadStats(); loadAlgorithms(); loadTasks(); loadModels(); loadStackingModels(); if (tab === 'materials') loadMaterials(matPage) }

  const handleTrainStacking = async () => {
    setTraining(true); setTrainResult(null)
    try {
      const data = await apiFetch<{ success: boolean; error?: string }>('/stacking/train', {
        method: 'POST', body: JSON.stringify({ test_ratio: 0.2, cv_folds: 5, max_sequences: 500 }),
      })
      if ((data as any).success) {
        setTrainResult(data)
        loadStackingModels()
        loadModels()
      } else {
        setTrainResult({ success: false, error: (data as any).error || '训练失败' })
      }
    } catch (e: any) { setTrainResult({ success: false, error: e.message || '网络错误' }) }
    finally { setTraining(false) }
  }

  const handlePredictStacking = async () => {
    if (!predModelId) return
    setPredicting(true); setPredResult(null)
    try {
      const modes = predModes.split(',').map(m => m.trim()).filter(Boolean)
      const data = await apiFetch<{ success: boolean }>('/stacking/predict', {
        method: 'POST', body: JSON.stringify({ model_id: predModelId, layer_modes: modes, stack_sequence: predStack }),
      })
      setPredResult(data)
    } catch (e: any) { setPredResult({ success: false, error: e.message || '网络错误' }) }
    finally { setPredicting(false) }
  }

  const handleSelfImprove = async () => {
    setSelfImproving(true); setImproveResult(null)
    try {
      const data = await apiFetch<{ success: boolean }>('/stacking/self_improve', {
        method: 'POST', body: JSON.stringify({ max_iterations: 3, max_sequences: 300, cv_folds: 3 }),
      })
      setImproveResult(data)
      loadStackingModels()
      loadImproveHistory()
    } catch (e: any) { setImproveResult({ success: false, error: e.message || '网络错误' }) }
    finally { setSelfImproving(false) }
  }

  const loadImproveHistory = useCallback(async () => {
    try {
      const data = await apiFetch<{ success: boolean; trajectory: any[] }>('/stacking/improvement_history')
      if (data.success) setImproveHistory(data.trajectory)
    } catch {}
  }, [])

  const handleErrorAnalysis = async (modelId: string) => {
    try {
      const data = await apiFetch<{ success: boolean }>(`/stacking/error_analysis/${modelId}`)
      setErrorAnalysis(data)
    } catch {}
  }

  useEffect(() => { loadImproveHistory() }, [loadImproveHistory])

  const tabs: { key: TabKey; label: string; shortLabel: string; icon: any }[] = [
    { key: 'dashboard', label: '仪表板', shortLabel: '概览', icon: BarChart3 },
    { key: 'stacking', label: '堆垛预测', shortLabel: '堆垛', icon: Layers },
    { key: 'algorithms', label: '算法', shortLabel: '算法', icon: Cpu },
    { key: 'tasks', label: '任务', shortLabel: '任务', icon: Activity },
    { key: 'materials', label: '材料', shortLabel: '材料', icon: Database },
    { key: 'models', label: '模型', shortLabel: '模型', icon: Zap },
  ]

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <div className="max-w-7xl mx-auto px-3 sm:px-4 py-4 sm:py-6 space-y-4 sm:space-y-6">
        <div className="flex items-center justify-between gap-2">
          <div className="min-w-0">
            <h1 className="text-lg sm:text-2xl font-bold text-white truncate">CGCPT Dashboard</h1>
            <p className="text-xs sm:text-sm text-gray-400 truncate">管理算法、任务、材料和模型</p>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            {isAdmin ? (
              <button onClick={handleLogout} className="flex items-center gap-1.5 px-2.5 py-1.5 rounded bg-gray-800 hover:bg-gray-700 text-xs sm:text-sm">
                <LogOut size={13} /> <span className="hidden sm:inline">登出</span>
              </button>
            ) : (
              <button onClick={() => setShowLogin(true)} className="flex items-center gap-1.5 px-2.5 py-1.5 rounded bg-cyan-600/20 text-cyan-400 hover:bg-cyan-600/30 text-xs sm:text-sm">
                <LogIn size={13} /> <span className="hidden sm:inline">管理员</span>
              </button>
            )}
            <button onClick={refreshAll} className="flex items-center gap-1.5 px-2.5 py-1.5 rounded bg-gray-800 hover:bg-gray-700 text-xs sm:text-sm">
              <RefreshCw size={13} />
            </button>
          </div>
        </div>

        <div className="flex gap-0.5 sm:gap-1 bg-gray-900 rounded-lg p-0.5 sm:p-1 overflow-x-auto">
          {tabs.map(t => (
            <button key={t.key} onClick={() => setTab(t.key)}
              className={`flex items-center gap-1 sm:gap-2 px-2.5 sm:px-4 py-1.5 sm:py-2 rounded-md text-xs sm:text-sm font-medium transition-colors whitespace-nowrap ${
                tab === t.key ? 'bg-cyan-600 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-800'
              }`}>
              <t.icon size={14} /> <span className="sm:hidden">{t.shortLabel}</span><span className="hidden sm:inline">{t.label}</span>
            </button>
          ))}
        </div>

        {tab === 'dashboard' && (
          <div className="space-y-4 sm:space-y-6">
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-4">
              <StatCard icon={Database} label="材料" value={stats?.materials.total ?? 0} sub={`${stats?.materials.verified ?? 0} 已验证`} color="text-emerald-400" />
              <StatCard icon={Cpu} label="算法" value={stats?.algorithms ?? 0} color="text-cyan-400" />
              <StatCard icon={CheckCircle2} label="完成" value={stats?.tasks.completed ?? 0} sub={`${stats?.tasks.running ?? 0} 运行中`} color="text-green-400" />
              <StatCard icon={Zap} label="模型" value={stats?.models ?? 0} color="text-purple-400" />
            </div>
            <div className="bg-gray-900 rounded-xl p-3 sm:p-4">
              <h2 className="text-sm sm:text-lg font-semibold mb-3">最近任务</h2>
              {tasks.length > 0 ? (
                <div className="space-y-1.5 sm:space-y-2">
                  {tasks.slice(0, 6).map(t => (
                    <div key={t.task_id} className="flex items-center justify-between p-2 sm:p-3 bg-gray-800/50 rounded-lg">
                      <div className="flex items-center gap-2 min-w-0">
                        <StatusBadge status={t.status} />
                        <span className="font-mono text-xs sm:text-sm text-gray-300 truncate">{t.algorithm_id}</span>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        {t.status === 'running' && (
                          <div className="w-16 sm:w-24 bg-gray-700 rounded-full h-1.5">
                            <div className="bg-cyan-400 h-1.5 rounded-full transition-all" style={{ width: `${Math.round(t.progress * 100)}%` }} />
                          </div>
                        )}
                        <button onClick={() => { setSelectedTask(t); setShowTaskDetail(true) }} className="text-gray-500 hover:text-white p-1">
                          <Eye size={13} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : <p className="text-gray-500 text-sm">暂无任务</p>}
            </div>
          </div>
        )}

        {tab === 'algorithms' && (
          <div className="space-y-3 sm:space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-sm sm:text-lg font-semibold">已注册算法</h2>
              {isAdmin && (
                <button onClick={() => setShowRegisterModal(true)} className="flex items-center gap-1.5 px-2.5 py-1.5 rounded bg-cyan-600 hover:bg-cyan-500 text-xs sm:text-sm font-medium">
                  <Plus size={13} /> 注册
                </button>
              )}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 sm:gap-4">
              {algorithms.map(algo => (
                <div key={algo.id} className="bg-gray-900 rounded-xl p-3 sm:p-4 border border-gray-800">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <Cpu size={16} className={algo.is_active ? 'text-emerald-400 flex-shrink-0' : 'text-gray-600 flex-shrink-0'} />
                      <span className="font-semibold text-sm truncate">{algo.name}</span>
                    </div>
                    <TypeBadge type={algo.algorithm_type} />
                  </div>
                  <p className="text-xs text-gray-400 mb-2 line-clamp-2">{algo.description}</p>
                  <p className="text-[10px] text-gray-600 font-mono mb-2 truncate">{algo.entry_point}</p>
                  <button onClick={() => { setSelectedAlgo(algo); setShowRunModal(true) }}
                    className="flex items-center gap-1.5 px-2.5 py-1.5 rounded bg-cyan-600/20 text-cyan-400 hover:bg-cyan-600/30 text-xs font-medium w-full justify-center">
                    <Play size={13} /> 执行
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {tab === 'tasks' && (
          <div className="space-y-3">
            <h2 className="text-sm sm:text-lg font-semibold">任务历史</h2>
            {tasks.length > 0 ? (
              <div className="bg-gray-900 rounded-xl divide-y divide-gray-800">
                {tasks.map(t => (
                  <div key={t.task_id} className="flex items-center justify-between p-3 sm:p-4 gap-2">
                    <div className="flex items-center gap-2 sm:gap-3 min-w-0">
                      <StatusBadge status={t.status} />
                      <div className="min-w-0">
                        <p className="font-mono text-xs sm:text-sm truncate">{t.algorithm_id}</p>
                        {t.error_message && <p className="text-[10px] sm:text-xs text-red-400 truncate">{t.error_message}</p>}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      {t.status === 'running' && (
                        <div className="w-16 sm:w-32 bg-gray-700 rounded-full h-1.5">
                          <div className="bg-cyan-400 h-1.5 rounded-full transition-all" style={{ width: `${Math.round(t.progress * 100)}%` }} />
                        </div>
                      )}
                      <button onClick={() => { setSelectedTask(t); setShowTaskDetail(true) }} className="text-gray-500 hover:text-white p-1">
                        <Eye size={13} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : <p className="text-gray-500 text-center py-8 text-sm">暂无任务</p>}
          </div>
        )}

        {tab === 'materials' && (
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <h2 className="text-sm sm:text-lg font-semibold">材料数据库</h2>
              <span className="text-xs text-gray-500">共 {matTotal} 条</span>
            </div>
            <div className="bg-gray-900 rounded-xl overflow-hidden">
              <div className="hidden sm:block">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-800 text-gray-400">
                      <th className="text-left px-4 py-3 font-medium">化学式</th>
                      <th className="text-left px-4 py-3 font-medium">空间群</th>
                      <th className="text-left px-4 py-3 font-medium">拓扑</th>
                      <th className="text-center px-4 py-3 font-medium">验证</th>
                      <th className="text-left px-4 py-3 font-medium">来源</th>
                      <th className="text-center px-4 py-3 font-medium">操作</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-800/50">
                    {materials.map(m => (
                      <tr key={m.id} className="hover:bg-gray-800/30 transition-colors">
                        <td className="px-4 py-2.5 font-mono">{m.formula}</td>
                        <td className="px-4 py-2.5 text-gray-400">{m.space_group}</td>
                        <td className="px-4 py-2.5 text-gray-400 font-mono text-xs">{m.topology_id}</td>
                        <td className="px-4 py-2.5 text-center">
                          {m.is_verified ? <CheckCircle2 size={16} className="text-emerald-400 inline" /> : <AlertCircle size={16} className="text-gray-600 inline" />}
                        </td>
                        <td className="px-4 py-2.5 text-gray-500 text-xs">{m.source}</td>
                        <td className="px-4 py-2.5 text-center">
                          <button onClick={() => handleDeleteMaterial(m.id)} className="text-gray-600 hover:text-red-400"><Trash2 size={14} /></button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="sm:hidden divide-y divide-gray-800/50">
                {materials.map(m => (
                  <div key={m.id} className="flex items-center justify-between p-3">
                    <div className="min-w-0">
                      <p className="font-mono text-sm font-medium truncate">{m.formula}</p>
                      <p className="text-xs text-gray-500 truncate">{m.space_group} · {m.topology_id}</p>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      {m.is_verified ? <CheckCircle2 size={14} className="text-emerald-400" /> : <AlertCircle size={14} className="text-gray-600" />}
                      <button onClick={() => handleDeleteMaterial(m.id)} className="text-gray-600 hover:text-red-400 p-1"><Trash2 size={13} /></button>
                    </div>
                  </div>
                ))}
              </div>
              {loading && <div className="text-center py-4 text-gray-500 text-sm">加载中...</div>}
              {!loading && materials.length === 0 && <div className="text-center py-8 text-gray-500 text-sm">暂无数据</div>}
            </div>
            {matTotal > 50 && (
              <div className="flex justify-center gap-2">
                <button onClick={() => loadMaterials(matPage - 1)} disabled={matPage <= 1} className="px-3 py-1 rounded bg-gray-800 hover:bg-gray-700 disabled:opacity-50 text-xs">上一页</button>
                <span className="px-2 py-1 text-xs text-gray-400">{matPage}</span>
                <button onClick={() => loadMaterials(matPage + 1)} disabled={matPage * 50 >= matTotal} className="px-3 py-1 rounded bg-gray-800 hover:bg-gray-700 disabled:opacity-50 text-xs">下一页</button>
              </div>
            )}
          </div>
        )}

        {tab === 'stacking' && (
          <div className="space-y-4 sm:space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm sm:text-base font-semibold flex items-center gap-2">
                    <TrendingUp size={16} className="text-cyan-400" /> 训练堆垛决策树
                  </h3>
                  <button onClick={handleTrainStacking} disabled={training}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-cyan-600 hover:bg-cyan-500 text-xs sm:text-sm font-medium disabled:opacity-50">
                    {training ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />}
                    {training ? '训练中...' : '开始训练'}
                  </button>
                </div>
                <div className="text-xs text-gray-400 space-y-1 mb-3">
                  <p>训练数据: LayeredXOGenerator 规则自动生成</p>
                  <p>预测目标: 每层堆垛标签 (A/B/C)</p>
                  <p>特征维度: 19维层上下文特征</p>
                </div>
                {trainResult && (
                  <div className={`rounded-lg p-3 text-xs ${trainResult.success ? 'bg-emerald-900/20 border border-emerald-700/30' : 'bg-red-900/20 border border-red-700/30'}`}>
                    {trainResult.success ? (
                      <div className="space-y-1">
                        <p className="text-emerald-300 font-semibold">训练成功!</p>
                        <p>模型ID: <span className="font-mono">{trainResult.model_id}</span></p>
                        <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 mt-1">
                          <p>测试准确率: <span className="text-emerald-300 font-bold">{(trainResult.best_params?.test_accuracy * 100)?.toFixed(2) || trainResult.best_params?.test_accuracy}%</span></p>
                          <p>训练准确率: <span className="text-white">{(trainResult.best_params?.train_accuracy * 100)?.toFixed(2) || trainResult.best_params?.train_accuracy}%</span></p>
                          <p>交叉验证: <span className="text-cyan-300">{(trainResult.best_params?.cv_mean * 100)?.toFixed(2) || trainResult.best_params?.cv_mean}% ± {(trainResult.best_params?.cv_std * 100)?.toFixed(2) || trainResult.best_params?.cv_std}%</span></p>
                          <p>过拟合: <span className={trainResult.best_params?.overfit > 0.1 ? 'text-yellow-300' : 'text-emerald-300'}>{(trainResult.best_params?.overfit * 100)?.toFixed(2) || trainResult.best_params?.overfit}%</span></p>
                        </div>
                        <p>训练样本: {trainResult.n_total_samples} | 参数组合: {trainResult.n_configs_tested}</p>
                        {trainResult.feature_importances?.slice(0, 5).map(([name, imp]: [string, number]) => (
                          <p key={name} className="text-gray-400">{name}: {typeof imp === 'number' ? (imp * 100).toFixed(1) : imp}%</p>
                        ))}
                      </div>
                    ) : (
                      <p className="text-red-300">{trainResult.error}</p>
                    )}
                  </div>
                )}
              </div>

              <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
                <h3 className="text-sm sm:text-base font-semibold flex items-center gap-2 mb-4">
                  <Target size={16} className="text-purple-400" /> 堆垛预测
                </h3>
                <div className="space-y-3">
                  <div>
                    <label className="text-xs text-gray-400 mb-1 block">选择模型</label>
                    <select value={predModelId} onChange={e => setPredModelId(e.target.value)}
                      className="w-full bg-gray-800 rounded px-3 py-2 text-sm border border-gray-700 outline-none">
                      {stackingModels.length > 0 ? stackingModels.map((m: any) => (
                        <option key={m.id} value={m.id}>{m.id} {m.is_active ? '(活跃)' : ''}</option>
                      )) : <option value="">暂无模型，请先训练</option>}
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-gray-400 mb-1 block">层模式序列 (逗号分隔)</label>
                    <input value={predModes} onChange={e => setPredModes(e.target.value)}
                      className="w-full bg-gray-800 rounded px-3 py-2 text-sm border border-gray-700 focus:border-cyan-500 outline-none font-mono"
                      placeholder="XO3, M7, XO3, M7, XO3, XO3" />
                    <p className="text-[10px] text-gray-600 mt-1">可用模式: XO, XO2, XO3, X, XBO3, BO3, XB3O6, M6, M7</p>
                  </div>
                  <div>
                    <label className="text-xs text-gray-400 mb-1 block">堆叠序列</label>
                    <input value={predStack} onChange={e => setPredStack(e.target.value)}
                      className="w-full bg-gray-800 rounded px-3 py-2 text-sm border border-gray-700 focus:border-cyan-500 outline-none font-mono"
                      placeholder="ABC" />
                  </div>
                  <button onClick={handlePredictStacking} disabled={predicting || !predModelId}
                    className="w-full flex items-center justify-center gap-1.5 px-3 py-2 rounded bg-purple-600 hover:bg-purple-500 text-sm font-medium disabled:opacity-50">
                    {predicting ? <Loader2 size={13} className="animate-spin" /> : <Target size={13} />}
                    {predicting ? '预测中...' : '预测堆垛'}
                  </button>
                </div>
                {predResult && predResult.success && (
                  <div className="mt-3 bg-gray-800/50 rounded-lg p-3 text-xs space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-gray-400">预测准确率</span>
                      <span className={`font-bold ${predResult.accuracy >= 0.8 ? 'text-emerald-300' : predResult.accuracy >= 0.5 ? 'text-yellow-300' : 'text-red-300'}`}>
                        {(predResult.accuracy * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-gray-400">正确/总数</span>
                      <span>{predResult.n_correct}/{predResult.n_total}</span>
                    </div>
                    <div className="border-t border-gray-700 pt-2 mt-2">
                      <p className="text-gray-400 mb-1">各层预测结果:</p>
                      <div className="space-y-0.5 max-h-40 overflow-y-auto">
                        {predResult.predictions?.map((p: any, i: number) => (
                          <div key={i} className="flex items-center justify-between">
                            <span className="text-gray-300">层{i}: {p.mode}</span>
                            <div className="flex items-center gap-2">
                              <span className="text-gray-500">规则: {p.rule_shift}</span>
                              <span className={`font-bold ${p.correct ? 'text-emerald-300' : 'text-red-300'}`}>预测: {p.predicted_shift}</span>
                              {p.confidence > 0 && <span className="text-gray-500">({(p.confidence * 100).toFixed(0)}%)</span>}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
                {predResult && !predResult.success && (
                  <div className="mt-3 bg-red-900/20 border border-red-700/30 rounded-lg p-3 text-xs text-red-300">
                    {predResult.error}
                  </div>
                )}
              </div>
            </div>

            <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
              <h3 className="text-sm sm:text-base font-semibold flex items-center gap-2 mb-3">
                <Layers size={16} className="text-orange-400" /> 已有堆垛模型
              </h3>
              {stackingModels.length > 0 ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                  {stackingModels.map((m: any) => (
                    <div key={m.id} className={`bg-gray-800/50 rounded-lg p-3 border ${m.is_active ? 'border-cyan-500/30' : 'border-gray-700/30'}`}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-mono text-xs truncate">{m.id}</span>
                        {m.is_active && <Star size={12} className="text-cyan-400" />}
                      </div>
                      <div className="text-[10px] text-gray-500 space-y-0.5">
                        <p>类型: {m.model_type || 'stacking_dt'}</p>
                        {m.metrics?.test_accuracy && <p>准确率: <span className="text-emerald-300">{(m.metrics.test_accuracy * 100).toFixed(2)}%</span></p>}
                        {m.metrics?.cv_mean && <p>CV: {(m.metrics.cv_mean * 100).toFixed(2)}%</p>}
                        {m.metrics?.n_total_samples && <p>样本: {m.metrics.n_total_samples}</p>}
                      </div>
                    </div>
                  ))}
                </div>
              ) : <p className="text-gray-500 text-sm text-center py-4">暂无模型，请先训练</p>}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm sm:text-base font-semibold flex items-center gap-2">
                    <TrendingUp size={16} className="text-emerald-400" /> 自我迭代优化
                  </h3>
                  <button onClick={handleSelfImprove} disabled={selfImproving}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-xs sm:text-sm font-medium disabled:opacity-50">
                    {selfImproving ? <Loader2 size={13} className="animate-spin" /> : <TrendingUp size={13} />}
                    {selfImproving ? '优化中...' : '启动迭代'}
                  </button>
                </div>
                <div className="text-xs text-gray-400 space-y-1 mb-3">
                  <p>每轮迭代: 误差分析 → 特征增强 → 难例挖掘 → 贝叶斯优化 → 集成融合</p>
                  <p>自动识别模型弱点，定向增强训练，持续提升准确率</p>
                </div>
                {improveResult && (
                  <div className={`rounded-lg p-3 text-xs ${improveResult.success ? 'bg-emerald-900/20 border border-emerald-700/30' : 'bg-red-900/20 border border-red-700/30'}`}>
                    {improveResult.success ? (
                      <div className="space-y-1">
                        <p className="text-emerald-300 font-semibold">迭代优化完成!</p>
                        <p>迭代轮数: {improveResult.n_iterations}</p>
                        <p>最佳准确率: <span className="text-emerald-300 font-bold">{((improveResult.best_iteration?.cv_mean || 0) * 100).toFixed(2)}%</span></p>
                        <p>总提升: <span className="text-cyan-300">{improveResult.total_improvement}%</span></p>
                        <p>最佳策略: {improveResult.best_iteration?.strategy}</p>
                        {improveResult.improvement_trajectory?.length > 0 && (
                          <div className="mt-2 border-t border-gray-700 pt-2">
                            <p className="text-gray-400 mb-1">提升轨迹:</p>
                            {improveResult.improvement_trajectory.map((t: any, i: number) => (
                              <div key={i} className="flex items-center justify-between">
                                <span className="text-gray-400">Iter {t.iteration}</span>
                                <span className="text-white">{((t.cv_mean || 0) * 100).toFixed(2)}%</span>
                                <span className="text-gray-500 text-[10px]">{t.strategy}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ) : (
                      <p className="text-red-300">{improveResult.error}</p>
                    )}
                  </div>
                )}
                {improveHistory.length > 0 && !improveResult && (
                  <div className="bg-gray-800/50 rounded-lg p-3 text-xs">
                    <p className="text-gray-400 mb-1">历史迭代记录 ({improveHistory.length} 轮):</p>
                    <div className="space-y-0.5 max-h-32 overflow-y-auto">
                      {improveHistory.map((h: any, i: number) => (
                        <div key={i} className="flex items-center justify-between">
                          <span className="text-gray-400">Iter {h.iteration}</span>
                          <span className="text-white">{((h.cv_mean || 0) * 100).toFixed(2)}%</span>
                          <span className="text-gray-500 text-[10px]">{h.strategy}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
                <h3 className="text-sm sm:text-base font-semibold flex items-center gap-2 mb-3">
                  <Activity size={16} className="text-orange-400" /> 误差分析
                </h3>
                <div className="space-y-2">
                  <select value={predModelId} onChange={e => setPredModelId(e.target.value)}
                    className="w-full bg-gray-800 rounded px-3 py-2 text-sm border border-gray-700 outline-none">
                    {stackingModels.length > 0 ? stackingModels.map((m: any) => (
                      <option key={m.id} value={m.id}>{m.id}</option>
                    )) : <option value="">暂无模型</option>}
                  </select>
                  <button onClick={() => predModelId && handleErrorAnalysis(predModelId)} disabled={!predModelId}
                    className="w-full flex items-center justify-center gap-1.5 px-3 py-2 rounded bg-orange-600 hover:bg-orange-500 text-sm font-medium disabled:opacity-50">
                    <Activity size={13} /> 分析误差
                  </button>
                </div>
                {errorAnalysis && !errorAnalysis.error && (
                  <div className="mt-3 bg-gray-800/50 rounded-lg p-3 text-xs space-y-2">
                    <div className="flex justify-between">
                      <span className="text-gray-400">总错误率</span>
                      <span className="text-orange-300 font-bold">{((errorAnalysis.error_rate || 0) * 100).toFixed(2)}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">错误样本</span>
                      <span>{errorAnalysis.total_errors}/{errorAnalysis.total_samples}</span>
                    </div>
                    {errorAnalysis.mode_error_rates && (
                      <div className="border-t border-gray-700 pt-2">
                        <p className="text-gray-400 mb-1">各层模式错误率:</p>
                        {Object.entries(errorAnalysis.mode_error_rates).slice(0, 6).map(([mode, rate]: [string, any]) => (
                          <div key={mode} className="flex justify-between">
                            <span className="text-gray-300">{mode}</span>
                            <span className={rate > 0.2 ? 'text-red-300' : 'text-gray-400'}>{(rate * 100).toFixed(1)}%</span>
                          </div>
                        ))}
                      </div>
                    )}
                    {errorAnalysis.hardest_modes && errorAnalysis.hardest_modes.length > 0 && (
                      <div>
                        <span className="text-gray-400">最难预测: </span>
                        <span className="text-red-300">{errorAnalysis.hardest_modes.join(', ')}</span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {tab === 'models' && (
          <div className="space-y-3 sm:space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-sm sm:text-lg font-semibold">决策树模型</h2>
              {isAdmin && (
                <button onClick={() => fileInputRef.current?.click()} disabled={uploading}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 rounded bg-cyan-600 hover:bg-cyan-500 text-xs sm:text-sm font-medium disabled:opacity-50">
                  {uploading ? <Loader2 size={13} className="animate-spin" /> : <Upload size={13} />}
                  {uploading ? '上传中...' : '上传模型'}
                </button>
              )}
              <input ref={fileInputRef} type="file" accept=".pkl,.joblib,.model" className="hidden" onChange={handleModelUpload} />
            </div>
            {!isAdmin && (
              <div className="bg-yellow-900/20 border border-yellow-700/30 rounded-lg p-3 flex items-center gap-2 text-xs text-yellow-300">
                <Key size={14} /> 上传模型需要管理员登录
                <button onClick={() => setShowLogin(true)} className="ml-auto px-2 py-1 rounded bg-yellow-700/30 hover:bg-yellow-700/50 text-yellow-200">登录</button>
              </div>
            )}
            {models.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 sm:gap-4">
                {models.map(m => (
                  <div key={m.id} className={`bg-gray-900 rounded-xl p-3 sm:p-4 border ${m.is_active ? 'border-cyan-500/30' : 'border-gray-800'}`}>
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <Zap size={16} className={m.is_active ? 'text-cyan-400 flex-shrink-0' : 'text-gray-600 flex-shrink-0'} />
                        <span className="font-semibold text-sm truncate">{m.name}</span>
                      </div>
                      {m.is_active && <Star size={14} className="text-cyan-400 flex-shrink-0" />}
                    </div>
                    <div className="text-xs text-gray-500 space-y-0.5 mb-3">
                      <p>类型: {m.model_type}</p>
                      {m.metrics?.n_features && <p>特征数: {m.metrics.n_features}</p>}
                      {m.metrics?.n_nodes && <p>节点数: {m.metrics.n_nodes}</p>}
                      {m.metrics?.n_classes && <p>分类数: {m.metrics.n_classes}</p>}
                      {m.metrics?.classes && <p className="truncate">类别: {m.metrics.classes.join(', ')}</p>}
                    </div>
                    <div className="flex gap-2">
                      {isAdmin && !m.is_active && (
                        <button onClick={() => handleActivateModel(m.id)} className="flex items-center gap-1 px-2 py-1 rounded bg-cyan-600/20 text-cyan-400 hover:bg-cyan-600/30 text-xs flex-1 justify-center">
                          <ShieldCheck size={12} /> 激活
                        </button>
                      )}
                      {isAdmin && (
                        <button onClick={() => handleDeleteModel(m.id)} className="flex items-center gap-1 px-2 py-1 rounded bg-red-600/20 text-red-400 hover:bg-red-600/30 text-xs">
                          <Trash2 size={12} />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : <p className="text-gray-500 text-center py-8 text-sm">暂无模型</p>}
          </div>
        )}
      </div>

      {showLogin && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={() => setShowLogin(false)}>
          <div className="bg-gray-900 rounded-xl p-5 sm:p-6 w-full max-w-sm border border-gray-800" onClick={e => e.stopPropagation()}>
            <h3 className="text-base sm:text-lg font-semibold mb-4 flex items-center gap-2"><Key size={18} className="text-cyan-400" /> 管理员登录</h3>
            {loginError && <p className="text-red-400 text-xs mb-3 bg-red-900/20 p-2 rounded">{loginError}</p>}
            <div className="space-y-3">
              <div>
                <label className="text-xs text-gray-400 mb-1 block">用户名</label>
                <input value={loginForm.username} onChange={e => setLoginForm({ ...loginForm, username: e.target.value })}
                  className="w-full bg-gray-800 rounded px-3 py-2 text-sm border border-gray-700 focus:border-cyan-500 outline-none" placeholder="admin" />
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">密码</label>
                <input type="password" value={loginForm.password} onChange={e => setLoginForm({ ...loginForm, password: e.target.value })}
                  className="w-full bg-gray-800 rounded px-3 py-2 text-sm border border-gray-700 focus:border-cyan-500 outline-none" placeholder="密码"
                  onKeyDown={e => e.key === 'Enter' && handleLogin()} />
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-5">
              <button onClick={() => { setShowLogin(false); setLoginError('') }} className="px-4 py-2 rounded bg-gray-800 hover:bg-gray-700 text-sm">取消</button>
              <button onClick={handleLogin} disabled={!loginForm.username || !loginForm.password}
                className="px-4 py-2 rounded bg-cyan-600 hover:bg-cyan-500 text-sm font-medium disabled:opacity-50">登录</button>
            </div>
          </div>
        </div>
      )}

      {showRegisterModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={() => setShowRegisterModal(false)}>
          <div className="bg-gray-900 rounded-xl p-5 sm:p-6 w-full max-w-lg border border-gray-800 max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <h3 className="text-base sm:text-lg font-semibold mb-4">注册新算法</h3>
            <div className="space-y-3">
              <div>
                <label className="text-xs text-gray-400 mb-1 block">算法 ID *</label>
                <input value={regForm.id} onChange={e => setRegForm({ ...regForm, id: e.target.value })} className="w-full bg-gray-800 rounded px-3 py-2 text-sm border border-gray-700 focus:border-cyan-500 outline-none" placeholder="my_custom_algo" />
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">名称 *</label>
                <input value={regForm.name} onChange={e => setRegForm({ ...regForm, name: e.target.value })} className="w-full bg-gray-800 rounded px-3 py-2 text-sm border border-gray-700 focus:border-cyan-500 outline-none" placeholder="我的算法" />
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">描述</label>
                <textarea value={regForm.description} onChange={e => setRegForm({ ...regForm, description: e.target.value })} className="w-full bg-gray-800 rounded px-3 py-2 text-sm border border-gray-700 focus:border-cyan-500 outline-none" rows={2} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">类型</label>
                  <select value={regForm.algorithm_type} onChange={e => setRegForm({ ...regForm, algorithm_type: e.target.value })} className="w-full bg-gray-800 rounded px-3 py-2 text-sm border border-gray-700 outline-none">
                    <option value="training">训练</option><option value="prediction">预测</option><option value="generation">生成</option><option value="validation">验证</option><option value="import">导入</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">入口点 *</label>
                  <input value={regForm.entry_point} onChange={e => setRegForm({ ...regForm, entry_point: e.target.value })} className="w-full bg-gray-800 rounded px-3 py-2 text-sm border border-gray-700 focus:border-cyan-500 outline-none" placeholder="module.function" />
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-5">
              <button onClick={() => setShowRegisterModal(false)} className="px-4 py-2 rounded bg-gray-800 hover:bg-gray-700 text-sm">取消</button>
              <button onClick={handleRegister} disabled={!regForm.id || !regForm.name || !regForm.entry_point} className="px-4 py-2 rounded bg-cyan-600 hover:bg-cyan-500 text-sm font-medium disabled:opacity-50">注册</button>
            </div>
          </div>
        </div>
      )}

      {showRunModal && selectedAlgo && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={() => setShowRunModal(false)}>
          <div className="bg-gray-900 rounded-xl p-5 sm:p-6 w-full max-w-lg border border-gray-800" onClick={e => e.stopPropagation()}>
            <h3 className="text-base sm:text-lg font-semibold mb-1">执行 {selectedAlgo.name}</h3>
            <p className="text-xs text-gray-500 mb-4">入口: {selectedAlgo.entry_point}</p>
            <div>
              <label className="text-xs text-gray-400 mb-1 block">参数 (JSON)</label>
              <textarea value={runInput} onChange={e => setRunInput(e.target.value)}
                className="w-full bg-gray-800 rounded px-3 py-2 text-sm border border-gray-700 focus:border-cyan-500 outline-none font-mono" rows={5} placeholder='{ "test_ratio": 0.2 }' />
            </div>
            <div className="flex justify-end gap-3 mt-4">
              <button onClick={() => setShowRunModal(false)} className="px-4 py-2 rounded bg-gray-800 hover:bg-gray-700 text-sm">取消</button>
              <button onClick={handleRun} className="flex items-center gap-2 px-4 py-2 rounded bg-cyan-600 hover:bg-cyan-500 text-sm font-medium">
                <Play size={14} /> 执行
              </button>
            </div>
          </div>
        </div>
      )}

      {showTaskDetail && selectedTask && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={() => setShowTaskDetail(false)}>
          <div className="bg-gray-900 rounded-xl p-5 sm:p-6 w-full max-w-lg border border-gray-800" onClick={e => e.stopPropagation()}>
            <h3 className="text-base sm:text-lg font-semibold mb-4">任务详情</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-gray-400">Task ID</span><span className="font-mono text-xs">{selectedTask.task_id}</span></div>
              <div className="flex justify-between"><span className="text-gray-400">算法</span><span className="font-mono text-xs">{selectedTask.algorithm_id}</span></div>
              <div className="flex justify-between items-center"><span className="text-gray-400">状态</span><StatusBadge status={selectedTask.status} /></div>
              <div className="flex justify-between"><span className="text-gray-400">进度</span><span>{Math.round(selectedTask.progress * 100)}%</span></div>
              {selectedTask.progress_message && <div className="flex justify-between"><span className="text-gray-400">消息</span><span className="text-gray-300 text-xs">{selectedTask.progress_message}</span></div>}
              {selectedTask.error_message && <div><span className="text-gray-400">错误</span><p className="mt-1 text-red-400 text-xs bg-red-900/20 p-2 rounded">{selectedTask.error_message}</p></div>}
              {selectedTask.created_at && <div className="flex justify-between"><span className="text-gray-400">创建</span><span className="text-xs">{new Date(selectedTask.created_at).toLocaleString()}</span></div>}
            </div>
            <div className="flex justify-end mt-5">
              <button onClick={() => setShowTaskDetail(false)} className="px-4 py-2 rounded bg-gray-800 hover:bg-gray-700 text-sm">关闭</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function StatCard({ icon: Icon, label, value, sub, color }: { icon: any; label: string; value: number; sub?: string; color: string }) {
  return (
    <div className="bg-gray-900 rounded-xl p-3 sm:p-4 border border-gray-800">
      <div className="flex items-center gap-2 mb-1.5">
        <Icon size={16} className={color} />
        <span className="text-xs sm:text-sm text-gray-400">{label}</span>
      </div>
      <div className="text-xl sm:text-2xl font-bold">{value}</div>
      {sub && <p className="text-[10px] sm:text-xs text-gray-500 mt-0.5">{sub}</p>}
    </div>
  )
}
