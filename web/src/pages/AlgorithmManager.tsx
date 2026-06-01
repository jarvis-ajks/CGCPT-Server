import { useState, useEffect, useCallback } from 'react'
import {
  Cpu, Play, Clock, CheckCircle2, XCircle, Loader2,
  RefreshCw, Database, ChevronRight, Zap,
  ArrowRight, AlertTriangle, Server, Activity
} from 'lucide-react'

const BASE = '/CGCPT/api'

async function apiFetch(path: string, opts?: RequestInit) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  })
  return res.json()
}

interface Algorithm {
  id: string
  name: string
  description: string
  version: string
  algorithm_type: string
  entry_point: string
  input_schema: any
  output_schema: any
  default_config: any
}

interface TaskItem {
  task_id: string
  algorithm_id: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  progress: number
  progress_message: string | null
  error_message: string | null
  created_at: string | null
  started_at: string | null
  completed_at: string | null
}

const STATUS_CONFIG = {
  pending: { icon: Clock, color: 'text-yellow-400', bg: 'bg-yellow-400/10', label: '等待中' },
  running: { icon: Loader2, color: 'text-cyan-400', bg: 'bg-cyan-400/10', label: '运行中' },
  completed: { icon: CheckCircle2, color: 'text-emerald-400', bg: 'bg-emerald-400/10', label: '已完成' },
  failed: { icon: XCircle, color: 'text-red-400', bg: 'bg-red-400/10', label: '失败' },
  cancelled: { icon: AlertTriangle, color: 'text-gray-400', bg: 'bg-gray-400/10', label: '已取消' },
}

export default function AlgorithmManager() {
  const [algorithms, setAlgorithms] = useState<Algorithm[]>([])
  const [tasks, setTasks] = useState<TaskItem[]>([])
  const [dbStatus, setDbStatus] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [selectedAlgo, setSelectedAlgo] = useState<Algorithm | null>(null)
  const [inputData, setInputData] = useState('{}')
  const [submitting, setSubmitting] = useState(false)
  const [activeTab, setActiveTab] = useState<'algorithms' | 'tasks' | 'database'>('algorithms')

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const [algoRes, taskRes, dbRes] = await Promise.all([
        apiFetch('/algorithms'),
        apiFetch('/tasks?limit=30'),
        apiFetch('/db/status'),
      ])
      if (algoRes.success) setAlgorithms(algoRes.algorithms)
      if (taskRes.success) setTasks(taskRes.tasks)
      if (dbRes.success) setDbStatus(dbRes)
    } catch (e) {
      console.error('Refresh failed:', e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
    const interval = setInterval(refresh, 5000)
    return () => clearInterval(interval)
  }, [refresh])

  const handleSubmitTask = async () => {
    if (!selectedAlgo) return
    setSubmitting(true)
    try {
      let parsed = {}
      try { parsed = JSON.parse(inputData) } catch { parsed = {} }
      const merged = { ...selectedAlgo.default_config, ...parsed }
      const res = await apiFetch('/tasks', {
        method: 'POST',
        body: JSON.stringify({ algorithm_id: selectedAlgo.id, input_data: merged }),
      })
      if (res.success) {
        setSelectedAlgo(null)
        setInputData('{}')
        setTimeout(refresh, 1000)
      } else {
        alert('提交失败: ' + res.error)
      }
    } catch (e: any) {
      alert('提交失败: ' + e.message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleMigrate = async () => {
    if (!confirm('确认从文件系统迁移数据到数据库？已有数据不会重复导入。')) return
    try {
      const res = await apiFetch('/db/migrate', { method: 'POST' })
      if (res.success) {
        alert(`迁移完成！原型: ${res.imported_prototypes}, 材料: ${res.imported_materials}`)
        refresh()
      } else {
        alert('迁移失败: ' + res.error)
      }
    } catch (e: any) {
      alert('迁移失败: ' + e.message)
    }
  }

  const typeLabels: Record<string, string> = {
    training: '训练', prediction: '预测', generation: '生成',
    verification: '验证', import: '导入', general: '通用',
  }

  const typeColors: Record<string, string> = {
    training: 'bg-purple-500/20 text-purple-300',
    prediction: 'bg-cyan-500/20 text-cyan-300',
    generation: 'bg-emerald-500/20 text-emerald-300',
    verification: 'bg-amber-500/20 text-amber-300',
    import: 'bg-blue-500/20 text-blue-300',
    general: 'bg-gray-500/20 text-gray-300',
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Cpu className="w-7 h-7 text-cyan-400" />
            算法与任务管理
          </h1>
          <p className="text-gray-400 mt-1 text-sm">
            管理算法注册、提交计算任务、监控执行状态
          </p>
        </div>
        <button
          onClick={refresh}
          className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-sm flex items-center gap-2 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          刷新
        </button>
      </div>

      {dbStatus && (
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
          {[
            { label: '原型', value: dbStatus.prototypes ?? '-', icon: Database },
            { label: '材料', value: dbStatus.materials ?? '-', icon: Database },
            { label: '算法', value: dbStatus.algorithms ?? '-', icon: Cpu },
            { label: '模型', value: dbStatus.models ?? '-', icon: Zap },
            { label: '等待', value: dbStatus.tasks_pending ?? 0, icon: Clock },
            { label: '运行', value: dbStatus.tasks_running ?? 0, icon: Activity },
            { label: '完成', value: dbStatus.tasks_completed ?? 0, icon: CheckCircle2 },
          ].map(({ label, value, icon: Icon }) => (
            <div key={label} className="bg-gray-900/60 border border-gray-800 rounded-xl p-3">
              <div className="flex items-center gap-2 text-gray-400 text-xs mb-1">
                <Icon className="w-3.5 h-3.5" />
                {label}
              </div>
              <div className="text-xl font-bold text-white tabular-nums">{value}</div>
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-2 border-b border-gray-800 pb-1">
        {(['algorithms', 'tasks', 'database'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
              activeTab === tab
                ? 'text-cyan-400 bg-gray-900/60 border-b-2 border-cyan-400'
                : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            {tab === 'algorithms' ? '算法列表' : tab === 'tasks' ? '任务监控' : '数据库'}
          </button>
        ))}
      </div>

      {activeTab === 'algorithms' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-3">
            {algorithms.map(algo => (
              <div
                key={algo.id}
                onClick={() => {
                  setSelectedAlgo(algo)
                  setInputData(JSON.stringify(algo.default_config || {}, null, 2))
                }}
                className={`bg-gray-900/60 border rounded-xl p-4 cursor-pointer transition-all hover:bg-gray-900/80 ${
                  selectedAlgo?.id === algo.id ? 'border-cyan-500/50' : 'border-gray-800'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="text-white font-medium">{algo.name}</h3>
                      <span className={`px-2 py-0.5 rounded text-xs ${typeColors[algo.algorithm_type] || typeColors.general}`}>
                        {typeLabels[algo.algorithm_type] || algo.algorithm_type}
                      </span>
                      <span className="text-gray-500 text-xs">v{algo.version}</span>
                    </div>
                    <p className="text-gray-400 text-sm">{algo.description}</p>
                    <p className="text-gray-600 text-xs mt-1 font-mono">{algo.entry_point}</p>
                  </div>
                  <ChevronRight className="w-5 h-5 text-gray-600 shrink-0" />
                </div>
              </div>
            ))}
          </div>

          {selectedAlgo && (
            <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
              <h3 className="text-white font-semibold mb-3 flex items-center gap-2">
                <Play className="w-4 h-4 text-cyan-400" />
                执行: {selectedAlgo.name}
              </h3>

              {selectedAlgo.input_schema?.properties && (
                <div className="mb-4">
                  <h4 className="text-gray-400 text-xs font-medium mb-2">输入参数</h4>
                  <div className="space-y-1.5">
                    {Object.entries(selectedAlgo.input_schema.properties).map(([key, schema]: [string, any]) => (
                      <div key={key} className="flex items-center justify-between bg-gray-800/50 rounded px-3 py-1.5">
                        <span className="text-gray-300 text-xs font-mono">{key}</span>
                        <span className="text-gray-500 text-xs">{schema.description || schema.type}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="mb-4">
                <h4 className="text-gray-400 text-xs font-medium mb-2">参数配置 (JSON)</h4>
                <textarea
                  value={inputData}
                  onChange={(e) => setInputData(e.target.value)}
                  className="w-full h-40 bg-gray-800 border border-gray-700 rounded-lg p-3 text-sm text-gray-200 font-mono focus:border-cyan-500/50 focus:outline-none resize-none"
                  spellCheck={false}
                />
              </div>

              <button
                onClick={handleSubmitTask}
                disabled={submitting}
                className="w-full px-4 py-2.5 bg-cyan-600 hover:bg-cyan-700 text-white rounded-lg font-medium text-sm flex items-center justify-center gap-2 transition-colors disabled:opacity-40"
              >
                {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                提交任务
              </button>
            </div>
          )}
        </div>
      )}

      {activeTab === 'tasks' && (
        <div className="bg-gray-900/60 border border-gray-800 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-800/50">
                  <th className="text-left px-4 py-3 text-gray-400 font-medium">任务 ID</th>
                  <th className="text-left px-4 py-3 text-gray-400 font-medium">算法</th>
                  <th className="text-left px-4 py-3 text-gray-400 font-medium">状态</th>
                  <th className="text-left px-4 py-3 text-gray-400 font-medium">进度</th>
                  <th className="text-left px-4 py-3 text-gray-400 font-medium">创建时间</th>
                  <th className="text-left px-4 py-3 text-gray-400 font-medium">耗时</th>
                </tr>
              </thead>
              <tbody>
                {tasks.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="text-center py-8 text-gray-500">暂无任务</td>
                  </tr>
                ) : (
                  tasks.map(t => {
                    const sc = STATUS_CONFIG[t.status] || STATUS_CONFIG.pending
                    const StatusIcon = sc.icon
                    const duration = t.started_at && t.completed_at
                      ? ((new Date(t.completed_at).getTime() - new Date(t.started_at).getTime()) / 1000).toFixed(1) + 's'
                      : t.started_at
                        ? ((Date.now() - new Date(t.started_at).getTime()) / 1000).toFixed(1) + 's'
                        : '-'

                    return (
                      <tr key={t.task_id} className="border-t border-gray-800/50 hover:bg-gray-800/30">
                        <td className="px-4 py-2.5 text-gray-200 font-mono text-xs">{t.task_id}</td>
                        <td className="px-4 py-2.5 text-gray-300 text-xs">{t.algorithm_id}</td>
                        <td className="px-4 py-2.5">
                          <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs ${sc.bg} ${sc.color}`}>
                            <StatusIcon className={`w-3.5 h-3.5 ${t.status === 'running' ? 'animate-spin' : ''}`} />
                            {sc.label}
                          </span>
                        </td>
                        <td className="px-4 py-2.5">
                          <div className="flex items-center gap-2">
                            <div className="w-20 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                              <div
                                className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-emerald-400"
                                style={{ width: `${Math.min(t.progress * 100, 100)}%` }}
                              />
                            </div>
                            <span className="text-xs text-gray-400 tabular-nums">{(t.progress * 100).toFixed(0)}%</span>
                          </div>
                          {t.progress_message && (
                            <p className="text-xs text-gray-500 mt-0.5 truncate max-w-[200px]">{t.progress_message}</p>
                          )}
                        </td>
                        <td className="px-4 py-2.5 text-gray-400 text-xs">
                          {t.created_at ? new Date(t.created_at).toLocaleString('zh-CN') : '-'}
                        </td>
                        <td className="px-4 py-2.5 text-gray-400 text-xs tabular-nums">{duration}</td>
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'database' && (
        <div className="space-y-4">
          <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
            <h3 className="text-white font-semibold mb-3 flex items-center gap-2">
              <Server className="w-4 h-4 text-cyan-400" />
              数据库状态
            </h3>
            {dbStatus ? (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {[
                  { label: '原型', value: dbStatus.prototypes },
                  { label: '材料', value: dbStatus.materials },
                  { label: '算法', value: dbStatus.algorithms },
                  { label: '模型', value: dbStatus.models },
                ].map(({ label, value }) => (
                  <div key={label} className="bg-gray-800/50 rounded-lg p-3">
                    <div className="text-2xl font-bold text-white tabular-nums">{value ?? '-'}</div>
                    <div className="text-gray-400 text-xs mt-0.5">{label}</div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 text-sm">数据库未连接</p>
            )}
          </div>

          <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
            <h3 className="text-white font-semibold mb-3">数据迁移</h3>
            <p className="text-gray-400 text-sm mb-4">
              将文件系统中的 CIF 数据导入到 MySQL 数据库。已导入的数据不会重复导入。
            </p>
            <button
              onClick={handleMigrate}
              className="px-5 py-2.5 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium text-sm flex items-center gap-2 transition-colors"
            >
              <ArrowRight className="w-4 h-4" />
              从文件系统迁移
            </button>
          </div>

          <div className="bg-gray-900/60 border border-amber-500/20 rounded-xl p-5">
            <h3 className="text-amber-300 font-semibold mb-2 text-sm">外部算法对接指南</h3>
            <div className="text-gray-400 text-xs space-y-2">
              <p>任何 Python 算法都可以通过以下方式注册到系统中：</p>
              <pre className="bg-gray-800/80 rounded-lg p-3 overflow-x-auto text-gray-300">
{`# 1. 编写你的算法模块 (my_algorithm.py)
def run(param1, param2):
    result = do_something(param1, param2)
    return {"success": True, "data": result}

# 2. 注册到系统 (POST /api/algorithms)
{
  "id": "my_algo",
  "name": "我的算法",
  "description": "算法描述",
  "algorithm_type": "general",
  "entry_point": "my_algorithm.run",
  "input_schema": {
    "type": "object",
    "properties": {
      "param1": {"type": "string", "description": "参数1"},
      "param2": {"type": "number", "description": "参数2"}
    }
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "success": {"type": "boolean"},
      "data": {"type": "object"}
    }
  }
}

# 3. 提交任务 (POST /api/tasks)
{
  "algorithm_id": "my_algo",
  "input_data": {"param1": "value", "param2": 42}
}

# 4. 查询结果 (GET /api/tasks/{task_id})`}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
