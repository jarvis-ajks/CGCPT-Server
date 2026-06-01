import { useState, useCallback, lazy, Suspense } from 'react'
import { FlaskConical, Plus, Trash2, History, Save, Layers, Atom, Network, Download, Copy, GripVertical, X } from 'lucide-react'
import { generateStructure, generateFull, fetchLayerData, fetchCoordination } from '../api/client'
import type { GenerateParams, GenerateResult, GenerateFullResult, LayerData, CoordinationEnvironment } from '../types'

const CrystalViewer = lazy(() => import('../components/three/CrystalViewer'))

const LAYER_MODES = ['XO', 'XO2', 'XO3', 'M6', 'M7', 'X', 'XBO3', 'BO3', 'XB3O6']

const LAYER_MODE_DESCRIPTIONS: Record<string, string> = {
  XO: '单层X与O交替',
  XO2: '双层X与O交替',
  XO3: '三层X与O交替',
  M6: '6配位M位层',
  M7: '7配位M位层',
  X: '单层X',
  XBO3: 'X-BO3层',
  BO3: 'BO3层',
  XB3O6: 'XB3O6层',
}

const PRESETS = [
  {
    name: '钙钛矿 ABO3',
    layers: [
      { mode: 'XO', angle: 0, dx: 0, dy: 0 },
      { mode: 'M6', angle: 0, dx: 0, dy: 0 },
      { mode: 'XO', angle: 120, dx: 0, dy: 0 },
      { mode: 'M6', angle: 0, dx: 0, dy: 0 },
      { mode: 'XO', angle: 240, dx: 0, dy: 0 },
    ],
    stackSequence: 'ABC',
    xElement: 'Ba',
    oElement: 'O',
    mElement: 'Ti',
    tElement: 'Si',
    enableT: false,
    enableB: false,
  },
  {
    name: '层状氧化物',
    layers: [
      { mode: 'XO', angle: 0, dx: 0, dy: 0 },
      { mode: 'M6', angle: 0, dx: 0, dy: 0 },
      { mode: 'XO', angle: 0, dx: 0, dy: 0 },
    ],
    stackSequence: 'A',
    xElement: 'Na',
    oElement: 'O',
    mElement: 'Mn',
    tElement: 'Si',
    enableT: false,
    enableB: false,
  },
  {
    name: '尖晶石结构',
    layers: [
      { mode: 'XO', angle: 0, dx: 0, dy: 0 },
      { mode: 'M6', angle: 0, dx: 0, dy: 0 },
      { mode: 'XO', angle: 120, dx: 0, dy: 0 },
      { mode: 'M6', angle: 60, dx: 0, dy: 0 },
      { mode: 'XO', angle: 240, dx: 0, dy: 0 },
      { mode: 'M6', angle: 0, dx: 0, dy: 0 },
    ],
    stackSequence: 'ABC',
    xElement: 'Mg',
    oElement: 'O',
    mElement: 'Al',
    tElement: 'Si',
    enableT: false,
    enableB: false,
  },
  {
    name: '石榴石结构',
    layers: [
      { mode: 'XO', angle: 0, dx: 0, dy: 0 },
      { mode: 'M6', angle: 0, dx: 0, dy: 0 },
      { mode: 'XO', angle: 120, dx: 0, dy: 0 },
      { mode: 'M6', angle: 0, dx: 0, dy: 0 },
      { mode: 'XO', angle: 240, dx: 0, dy: 0 },
      { mode: 'M6', angle: 0, dx: 0, dy: 0 },
    ],
    stackSequence: 'ABC',
    xElement: 'Ca',
    oElement: 'O',
    mElement: 'Fe',
    tElement: 'Si',
    enableT: true,
    enableB: false,
  },
  {
    name: '沸石类',
    layers: [
      { mode: 'XO', angle: 0, dx: 0, dy: 0 },
      { mode: 'M6', angle: 0, dx: 0, dy: 0 },
      { mode: 'XO', angle: 90, dx: 0, dy: 0 },
      { mode: 'M6', angle: 45, dx: 0, dy: 0 },
      { mode: 'XO', angle: 180, dx: 0, dy: 0 },
      { mode: 'M6', angle: 0, dx: 0, dy: 0 },
    ],
    stackSequence: 'ABC',
    xElement: 'Na',
    oElement: 'O',
    mElement: 'Al',
    tElement: 'Si',
    enableT: false,
    enableB: false,
  },
  {
    name: '钙钛矿 SrTiO3',
    layers: [
      { mode: 'XO', angle: 0, dx: 0, dy: 0 },
      { mode: 'M6', angle: 0, dx: 0, dy: 0 },
      { mode: 'XO', angle: 120, dx: 0, dy: 0 },
      { mode: 'M6', angle: 0, dx: 0, dy: 0 },
      { mode: 'XO', angle: 240, dx: 0, dy: 0 },
    ],
    stackSequence: 'ABC',
    xElement: 'Sr',
    oElement: 'O',
    mElement: 'Ti',
    tElement: 'Si',
    enableT: false,
    enableB: false,
  },
  {
    name: '钙钛矿 CaTiO3',
    layers: [
      { mode: 'XO', angle: 0, dx: 0, dy: 0 },
      { mode: 'M6', angle: 0, dx: 0, dy: 0 },
      { mode: 'XO', angle: 120, dx: 0, dy: 0 },
      { mode: 'M6', angle: 0, dx: 0, dy: 0 },
      { mode: 'XO', angle: 240, dx: 0, dy: 0 },
    ],
    stackSequence: 'ABC',
    xElement: 'Ca',
    oElement: 'O',
    mElement: 'Ti',
    tElement: 'Si',
    enableT: false,
    enableB: false,
  },
  {
    name: 'Layered Nickelate',
    layers: [
      { mode: 'XO', angle: 0, dx: 0, dy: 0 },
      { mode: 'M6', angle: 0, dx: 0, dy: 0 },
      { mode: 'XO', angle: 0, dx: 0, dy: 0 },
      { mode: 'M6', angle: 0, dx: 0, dy: 0 },
      { mode: 'XO', angle: 0, dx: 0, dy: 0 },
    ],
    stackSequence: 'AAAA',
    xElement: 'La',
    oElement: 'O',
    mElement: 'Ni',
    tElement: 'Si',
    enableT: false,
    enableB: false,
  },
  {
    name: 'Layered Cobaltite',
    layers: [
      { mode: 'XO', angle: 0, dx: 0, dy: 0 },
      { mode: 'M6', angle: 0, dx: 0, dy: 0 },
      { mode: 'XO', angle: 0, dx: 0, dy: 0 },
      { mode: 'M6', angle: 0, dx: 0, dy: 0 },
      { mode: 'XO', angle: 0, dx: 0, dy: 0 },
    ],
    stackSequence: 'AAAA',
    xElement: 'Na',
    oElement: 'O',
    mElement: 'Co',
    tElement: 'Si',
    enableT: false,
    enableB: false,
  },
  {
    name: 'Custom',
    layers: [
      { mode: 'XO', angle: 0, dx: 0, dy: 0 },
    ],
    stackSequence: 'A',
    xElement: 'Ba',
    oElement: 'O',
    mElement: 'Ti',
    tElement: 'Si',
    enableT: false,
    enableB: false,
  },
]

const QUICK_LAYER_INSERTIONS = [
  { label: '+XO', modes: ['XO'] },
  { label: '+M6', modes: ['M6'] },
  { label: '+XO+M6', modes: ['XO', 'M6'] },
  { label: '+XO3+M6', modes: ['XO3', 'M6'] },
  { label: '+XBO3', modes: ['XBO3'] },
  { label: '+BO3', modes: ['BO3'] },
]

interface LayerEntry {
  mode: string
  angle: number
  dx: number
  dy: number
}

interface HistoryEntry {
  timestamp: number
  params: GenerateParams
  result: GenerateResult
}

interface ValidationWarning {
  field: string
  message: string
  severity: 'warning' | 'error'
}

const STORAGE_KEY = 'cgcpt-generate-history'

function loadHistory(): HistoryEntry[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function saveHistory(entries: HistoryEntry[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(entries.slice(0, 50)))
}

const ELEMENT_COLORS: Record<string, string> = {
  H: '#ffffff', O: '#ff0d0d', F: '#90e050', N: '#3050f8', C: '#909090',
  B: '#ffb5b5', Si: '#f0c8a0', P: '#ff8000', S: '#ffff30', Cl: '#1ff01f',
  Li: '#cc80ff', Na: '#ab5cf2', K: '#8f40d4', Rb: '#702eb0', Cs: '#57178f',
  Be: '#c2ff00', Mg: '#8aff00', Ca: '#3dff00', Sr: '#00ff00', Ba: '#00c900',
  Ti: '#bfc2c7', V: '#a6a6ab', Cr: '#8a99c7', Mn: '#9c7ac7', Fe: '#e06633',
  Co: '#f090a0', Ni: '#50d050', Cu: '#c88033', Zn: '#7d80b0', Al: '#bfa6a6',
}

const ELEMENT_CATEGORIES: Record<string, { color: string; elements: string[] }> = {
  'alkali': { color: '#ff6b6b', elements: ['Li', 'Na', 'K', 'Rb', 'Cs', 'Fr'] },
  'alkaline': { color: '#ffa94d', elements: ['Be', 'Mg', 'Ca', 'Sr', 'Ba', 'Ra'] },
  'transition': { color: '#74c0fc', elements: ['Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn', 'Sc', 'Y', 'Zr', 'Nb', 'Mo', 'Tc', 'Ru', 'Rh', 'Pd', 'Ag', 'Cd', 'Hf', 'Ta', 'W', 'Re', 'Os', 'Ir', 'Pt', 'Au', 'Hg', 'Rf', 'Db', 'Sg', 'Bh', 'Hs', 'Mt', 'Ds', 'Rg', 'Cn'] },
  'post-transition': { color: '#69db7c', elements: ['Al', 'Ga', 'In', 'Sn', 'Tl', 'Pb', 'Bi', 'Po', 'Nh', 'Fl', 'Mc', 'Lv'] },
  'metalloid': { color: '#da77f2', elements: ['B', 'Si', 'Ge', 'As', 'Sb', 'Te', 'At'] },
  'nonmetal': { color: '#ffd43b', elements: ['H', 'C', 'N', 'O', 'P', 'S', 'Se'] },
  'halogen': { color: '#38d9a9', elements: ['F', 'Cl', 'Br', 'I', 'At', 'Ts'] },
  'noble': { color: '#e599f7', elements: ['He', 'Ne', 'Ar', 'Kr', 'Xe', 'Rn', 'Og'] },
  'lanthanide': { color: '#ff8787', elements: ['La', 'Ce', 'Pr', 'Nd', 'Pm', 'Sm', 'Eu', 'Gd', 'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb', 'Lu'] },
  'actinide': { color: '#ff922b', elements: ['Ac', 'Th', 'Pa', 'U', 'Np', 'Pu', 'Am', 'Cm', 'Bk', 'Cf', 'Es', 'Fm', 'Md', 'No', 'Lr'] },
}

const COMMON_ELEMENTS = ['Ba', 'Ca', 'Sr', 'Na', 'K', 'O', 'Ti', 'Mn', 'Fe', 'Si', 'Al', 'Mg', 'Co', 'Ni', 'La']

const ALL_ELEMENTS = [
  'H', 'He', 'Li', 'Be', 'B', 'C', 'N', 'O', 'F', 'Ne',
  'Na', 'Mg', 'Al', 'Si', 'P', 'S', 'Cl', 'Ar', 'K', 'Ca',
  'Sc', 'Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn',
  'Ga', 'Ge', 'As', 'Se', 'Br', 'Kr', 'Rb', 'Sr', 'Y', 'Zr',
  'Nb', 'Mo', 'Tc', 'Ru', 'Rh', 'Pd', 'Ag', 'Cd', 'In', 'Sn',
  'Sb', 'Te', 'I', 'Xe', 'Cs', 'Ba', 'La', 'Ce', 'Pr', 'Nd',
  'Pm', 'Sm', 'Eu', 'Gd', 'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb',
  'Lu', 'Hf', 'Ta', 'W', 'Re', 'Os', 'Ir', 'Pt', 'Au', 'Hg',
]

function ElementPickerPopup({ value, onChange, onClose }: { value: string; onChange: (v: string) => void; onClose: () => void }) {
  const [filter, setFilter] = useState('')

  const getElementColor = (el: string) => {
    for (const cat of Object.values(ELEMENT_CATEGORIES)) {
      if (cat.elements.includes(el)) return cat.color
    }
    return '#888'
  }

  const filteredElements = filter
    ? ALL_ELEMENTS.filter(el => el.toLowerCase().includes(filter.toLowerCase()))
    : COMMON_ELEMENTS

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-3 sm:p-4 w-full sm:w-[500px] max-h-[90vh] sm:max-h-[80vh] overflow-y-auto mx-2 sm:mx-0" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-white font-semibold">选择元素</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        <input
          type="text"
          placeholder="搜索元素..."
          value={filter}
          onChange={e => setFilter(e.target.value)}
          className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm mb-3 focus:outline-none focus:border-cyan-500"
          autoFocus
        />

        {!filter && (
          <div className="mb-3">
            <p className="text-xs text-gray-500 mb-2">常用元素</p>
            <div className="flex flex-wrap gap-1.5">
              {COMMON_ELEMENTS.map(el => (
                <button
                  key={el}
                  onClick={() => { onChange(el); onClose() }}
                  className={`w-10 h-10 rounded-lg text-sm font-medium transition-all touch-manipulation ${
                    value === el ? 'ring-2 ring-cyan-400 scale-110' : 'hover:scale-105'
                  }`}
                  style={{ backgroundColor: getElementColor(el) + '40', color: getElementColor(el) }}
                >
                  {el}
                </button>
              ))}
            </div>
          </div>
        )}

        <div>
          <p className="text-xs text-gray-500 mb-2">{filter ? '搜索结果' : '全部元素'}</p>
          <div className="grid grid-cols-10 gap-0.5 sm:gap-1">
            {filteredElements.map(el => (
              <button
                key={el}
                onClick={() => { onChange(el); onClose() }}
                className={`w-8 h-8 sm:w-8 sm:h-8 rounded text-[9px] sm:text-xs font-medium transition-all touch-manipulation ${
                  value === el ? 'ring-2 ring-cyan-400 scale-110' : 'hover:scale-105'
                }`}
                style={{ backgroundColor: getElementColor(el) + '40', color: getElementColor(el) }}
              >
                {el}
              </button>
            ))}
          </div>
        </div>

        <div className="mt-3 pt-3 border-t border-gray-700">
          <div className="flex flex-wrap gap-2">
            {Object.entries(ELEMENT_CATEGORIES).map(([cat, data]) => (
              <div key={cat} className="flex items-center gap-1">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: data.color }} />
                <span className="text-xs text-gray-400 capitalize">{cat}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

function ElementSelector({ value, onChange, label }: { value: string; onChange: (v: string) => void; label: string }) {
  const [showPopup, setShowPopup] = useState(false)

  const getElementColor = (el: string) => {
    for (const cat of Object.values(ELEMENT_CATEGORIES)) {
      if (cat.elements.includes(el)) return cat.color
    }
    return '#888'
  }

  return (
    <div>
      <label className="text-xs text-gray-400 uppercase tracking-wider mb-1 block">{label}</label>
      <div className="relative">
        <button
          onClick={() => setShowPopup(true)}
          className="w-full flex items-center gap-2 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 hover:border-cyan-500/50 transition-colors"
        >
          <span
            className="w-6 h-6 rounded text-xs font-medium flex items-center justify-center"
            style={{ backgroundColor: getElementColor(value) + '40', color: getElementColor(value) }}
          >
            {value}
          </span>
          <span>{value}</span>
        </button>
      </div>
      {showPopup && <ElementPickerPopup value={value} onChange={onChange} onClose={() => setShowPopup(false)} />}
    </div>
  )
}

function LayerProjectionSVG({ layer }: { layer: LayerData }) {
  const size = 280
  const padding = 20
  const maxGrid = Math.max(layer.grid_x, layer.grid_y, 1)
  const scale = (size - padding * 2) / maxGrid

  return (
    <div className="bg-gray-900 rounded-lg p-3">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-gray-400 font-mono">{layer.mode} · {layer.shift}</span>
        <span className="text-xs text-gray-500">z={layer.z.toFixed(2)} θ={layer.theta.toFixed(0)}°</span>
      </div>
      <svg width={size} height={size} className="bg-gray-950 rounded">
        {Array.from({ length: Math.floor(layer.grid_x) + 1 }, (_, i) => (
          <line key={`vx${i}`} x1={padding + i * scale} y1={padding} x2={padding + i * scale} y2={size - padding} stroke="#1f2937" strokeWidth={0.5} />
        ))}
        {Array.from({ length: Math.floor(layer.grid_y) + 1 }, (_, i) => (
          <line key={`hy${i}`} x1={padding} y1={padding + i * scale} x2={size - padding} y2={padding + i * scale} stroke="#1f2937" strokeWidth={0.5} />
        ))}
        {layer.atoms.map((atom, i) => {
          const cx = padding + atom.fx * scale
          const cy = padding + atom.fy * scale
          const color = ELEMENT_COLORS[atom.element] || '#ff69b4'
          return (
            <g key={i}>
              <circle cx={cx} cy={cy} r={5} fill={color} opacity={0.8} />
              <text x={cx} y={cy - 7} textAnchor="middle" fill={color} fontSize={8} fontFamily="monospace">
                {atom.element}
              </text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}

type TabKey = 'basic' | 'full' | 'layers' | 'coordination'

function validateParams(params: GenerateParams, _warnings: ValidationWarning[]): ValidationWarning[] {
  const newWarnings: ValidationWarning[] = []

  if (params.target_xo_distance < 1.5 || params.target_xo_distance > 4.0) {
    newWarnings.push({
      field: 'target_xo_distance',
      message: `X-O距离 ${params.target_xo_distance} Å 超出建议范围 (1.5-4.0 Å)`,
      severity: 'warning',
    })
  }

  if (params.nx < 1 || params.ny < 1) {
    newWarnings.push({
      field: 'nx',
      message: 'NX 和 NY 必须为正整数',
      severity: 'error',
    })
  }

  if (params.layer_modes.length === 0) {
    newWarnings.push({
      field: 'layers',
      message: '至少需要一层配置',
      severity: 'error',
    })
  }

  if (params.layer_modes.filter(m => ['XO', 'XO2', 'XO3', 'X', 'XBO3', 'BO3', 'XB3O6'].includes(m)).length === 0) {
    newWarnings.push({
      field: 'layers',
      message: '配置中至少需要一种X或O相关的层模式',
      severity: 'warning',
    })
  }

  return newWarnings
}

function generateCIFString(result: GenerateResult): string {
  const lattice = result.lattice
  const atoms = result.atom_sites

  const lines = [
    'data_cgcpt_structure',
    `# Generated by CGCPT Structure Generator
# Formula: ${result.formula}
# Space Group: ${result.space_group.symbol} (#${result.space_group.number})
# Crystal System: ${result.space_group.crystal_system}
`,
    `_symmetry_space_group_name_H-M    '${result.space_group.symbol}'`,
    `_symmetry_Int_Tables_number       ${result.space_group.number}`,
    '_symmetry_space_group_name_Hall   ?',
    '_chemical_name_common             ?',
    `_chemical_formula_structural      '${result.formula}'`,
    `_cell_length_a                    ${lattice.a.toFixed(6)}`,
    `_cell_length_b                    ${lattice.b.toFixed(6)}`,
    `_cell_length_c                    ${lattice.c.toFixed(6)}`,
    `_cell_angle_alpha                 ${lattice.alpha.toFixed(6)}`,
    `_cell_angle_beta                  ${lattice.beta.toFixed(6)}`,
    `_cell_angle_gamma                 ${lattice.gamma.toFixed(6)}`,
    '_cell_volume                      ?',
    '_exptl_absorpt_process_details    ?',
    '',
    'loop_',
    '_atom_site_label',
    '_atom_site_type_symbol',
    '_atom_site_fract_x',
    '_atom_site_fract_y',
    '_atom_site_fract_z',
    '_atom_site_occupancy',
    '_atom_site_adp_type',
    '_atom_site_U_iso_or_equiv',
  ]

  atoms.forEach((atom, i) => {
    lines.push(
      `${atom.element}${i + 1}  ${atom.element}  ${atom.x.toFixed(6)}  ${atom.y.toFixed(6)}  ${atom.z.toFixed(6)}  1.0  Biso  0.025`
    )
  })

  lines.push('')
  lines.push('# End of CIF')

  return lines.join('\n')
}

export default function StructureGenerator() {
  const [activeTab, setActiveTab] = useState<TabKey>('basic')
  const [xElement, setXElement] = useState('Ba')
  const [oElement, setOElement] = useState('O')
  const [mElement, setMElement] = useState('Mg')
  const [tElement, setTElement] = useState('Si')
  const [bElement, setBElement] = useState('B')
  const [targetXoDistance, setTargetXoDistance] = useState(2.77648)
  const [nx, setNx] = useState(3)
  const [ny, setNy] = useState(3)
  const [stackSequence, setStackSequence] = useState('ABC')
  const [enableT, setEnableT] = useState(false)
  const [enableB, setEnableB] = useState(false)
  const [allowNonNeutral, setAllowNonNeutral] = useState(false)
  const [layers, setLayers] = useState<LayerEntry[]>([
    { mode: 'XO', angle: 0, dx: 0, dy: 0 },
    { mode: 'M6', angle: 0, dx: 0, dy: 0 },
    { mode: 'XO', angle: 120, dx: 0, dy: 0 },
    { mode: 'M6', angle: 0, dx: 0, dy: 0 },
    { mode: 'XO', angle: 240, dx: 0, dy: 0 },
  ])
  const [draggedLayer, setDraggedLayer] = useState<number | null>(null)
  const [hoveredLayerMode, setHoveredLayerMode] = useState<string | null>(null)

  const [result, setResult] = useState<GenerateResult | null>(null)
  const [fullResult, setFullResult] = useState<GenerateFullResult | null>(null)
  const [layerData, setLayerData] = useState<LayerData[] | null>(null)
  const [coordEnvs, setCoordEnvs] = useState<CoordinationEnvironment[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [warnings, setWarnings] = useState<ValidationWarning[]>([])
  const [generating, setGenerating] = useState(false)
  const [history, setHistory] = useState<HistoryEntry[]>(loadHistory)
  const [showHistory, setShowHistory] = useState(false)
  const [copiedCIF, setCopiedCIF] = useState(false)

  const buildParams = useCallback((): GenerateParams => ({
    x_element: xElement,
    o_element: oElement,
    m_element: mElement,
    t_element: tElement,
    b_element: bElement,
    target_xo_distance: targetXoDistance,
    nx,
    ny,
    layer_modes: layers.map((l) => l.mode),
    layer_alphas: layers.filter((l) => ['XO', 'XO2', 'XO3', 'X', 'XBO3', 'BO3', 'XB3O6'].includes(l.mode)).map(() => 1),
    stack_sequence: stackSequence,
    layer_angles: layers.map((l) => l.angle),
    layer_dxs: layers.map((l) => l.dx),
    layer_dys: layers.map((l) => l.dy),
    enable_t: enableT,
    enable_b: enableB,
    allow_non_neutral: allowNonNeutral,
  }), [xElement, oElement, mElement, tElement, bElement, targetXoDistance, nx, ny, layers, stackSequence, enableT, enableB, allowNonNeutral])

  const addLayer = () => {
    setLayers([...layers, { mode: 'XO', angle: 0, dx: 0, dy: 0 }])
  }

  const removeLayer = (index: number) => {
    setLayers(layers.filter((_, i) => i !== index))
  }

  const duplicateLayer = (index: number) => {
    const newLayers = [...layers]
    newLayers.splice(index + 1, 0, { ...layers[index] })
    setLayers(newLayers)
  }

  const updateLayer = (index: number, field: keyof LayerEntry, value: string | number) => {
    const updated = [...layers]
    updated[index] = { ...updated[index], [field]: value }
    setLayers(updated)
  }

  const insertLayers = (modeList: string[]) => {
    const newLayers = modeList.map(mode => ({ mode, angle: 0, dx: 0, dy: 0 }))
    setLayers([...layers, ...newLayers])
  }

  const handleDragStart = (index: number) => {
    setDraggedLayer(index)
  }

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault()
    if (draggedLayer === null || draggedLayer === index) return

    const newLayers = [...layers]
    const draggedItem = newLayers[draggedLayer]
    newLayers.splice(draggedLayer, 1)
    newLayers.splice(index, 0, draggedItem)
    setLayers(newLayers)
    setDraggedLayer(index)
  }

  const handleDragEnd = () => {
    setDraggedLayer(null)
  }

  const handleGenerate = useCallback(async () => {
    const params = buildParams()
    const validationWarnings = validateParams(params, [])
    setWarnings(validationWarnings)

    const hasErrors = validationWarnings.some(w => w.severity === 'error')
    if (hasErrors) {
      setError('请修正参数错误后再试')
      return
    }

    setGenerating(true)
    setError(null)
    setResult(null)
    try {
      const res = await generateStructure(params)
      setResult(res)
    } catch (err) {
      setError(err instanceof Error ? err.message : '生成失败')
    } finally {
      setGenerating(false)
    }
  }, [buildParams])

  const handleFullAnalysis = useCallback(async () => {
    setGenerating(true)
    setError(null)
    setFullResult(null)
    const params = buildParams()
    try {
      const res = await generateFull(params)
      setFullResult(res)
    } catch (err) {
      setError(err instanceof Error ? err.message : '完整分析失败')
    } finally {
      setGenerating(false)
    }
  }, [buildParams])

  const handleLayerProjection = useCallback(async () => {
    setGenerating(true)
    setError(null)
    setLayerData(null)
    const params = buildParams()
    try {
      const res = await fetchLayerData(params)
      setLayerData(res.layer_data)
    } catch (err) {
      setError(err instanceof Error ? err.message : '层投影失败')
    } finally {
      setGenerating(false)
    }
  }, [buildParams])

  const handleCoordination = useCallback(async () => {
    setGenerating(true)
    setError(null)
    setCoordEnvs(null)
    const params = buildParams()
    try {
      const res = await fetchCoordination(params)
      setCoordEnvs(res.environments)
    } catch (err) {
      setError(err instanceof Error ? err.message : '配位环境分析失败')
    } finally {
      setGenerating(false)
    }
  }, [buildParams])

  const handleSave = () => {
    if (!result) return
    const params = buildParams()
    const entry: HistoryEntry = { timestamp: Date.now(), params, result }
    const updated = [entry, ...history].slice(0, 50)
    setHistory(updated)
    saveHistory(updated)
  }

  const loadFromHistory = (entry: HistoryEntry) => {
    const p = entry.params
    setXElement(p.x_element)
    setOElement(p.o_element)
    setMElement(p.m_element)
    setTElement(p.t_element)
    setBElement(p.b_element)
    setTargetXoDistance(p.target_xo_distance)
    setNx(p.nx)
    setNy(p.ny)
    setStackSequence(p.stack_sequence)
    setEnableT(p.enable_t)
    setEnableB(p.enable_b)
    setAllowNonNeutral(p.allow_non_neutral)
    setLayers(p.layer_modes.map((mode, i) => ({
      mode,
      angle: p.layer_angles[i] ?? 0,
      dx: p.layer_dxs[i] ?? 0,
      dy: p.layer_dys[i] ?? 0,
    })))
    setResult(entry.result)
    setShowHistory(false)
  }

  const clearHistory = () => {
    setHistory([])
    localStorage.removeItem(STORAGE_KEY)
  }

  const applyPreset = (preset: typeof PRESETS[number]) => {
    setXElement(preset.xElement)
    setOElement(preset.oElement)
    setMElement(preset.mElement)
    setTElement(preset.tElement)
    setEnableT(preset.enableT)
    setEnableB(preset.enableB)
    setStackSequence(preset.stackSequence)
    setLayers(preset.layers.map(l => ({ ...l })))
    setWarnings([])
    setError(null)
  }

  const handleExportCIF = () => {
    if (!result) return
    const cifString = generateCIFString(result)
    const blob = new Blob([cifString], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${result.formula.replace(/[^a-zA-Z0-9]/g, '_')}.cif`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const handleCopyCIF = () => {
    if (!result) return
    const cifString = generateCIFString(result)
    navigator.clipboard.writeText(cifString)
    setCopiedCIF(true)
    setTimeout(() => setCopiedCIF(false), 2000)
  }

  const inputCls = 'bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-cyan-500 w-full'
  const labelCls = 'text-xs text-gray-400 uppercase tracking-wider mb-1 block'

  const tabs: { key: TabKey; label: string; icon: typeof FlaskConical }[] = [
    { key: 'basic', label: '基本生成', icon: FlaskConical },
    { key: 'full', label: '完整分析', icon: Network },
    { key: 'layers', label: '层投影', icon: Layers },
    { key: 'coordination', label: '配位环境', icon: Atom },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">结构生成器</h1>
          <p className="text-gray-400 mt-1">通过层参数生成晶体结构</p>
        </div>
        <button
          onClick={() => setShowHistory(!showHistory)}
          className="flex items-center gap-2 px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-300 hover:border-cyan-500/50 transition-colors"
        >
          <History className="w-4 h-4" />
          历史记录（{history.length}）
        </button>
      </div>

      {showHistory && history.length > 0 && (
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-white">生成历史</h3>
            <button onClick={clearHistory} className="text-xs text-red-400 hover:text-red-300">清空全部</button>
          </div>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {history.map((entry, i) => (
              <button
                key={i}
                onClick={() => loadFromHistory(entry)}
                className="w-full text-left bg-gray-900/50 rounded-lg p-3 hover:bg-gray-700/30 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <span className="text-white font-medium text-sm">{entry.result.formula}</span>
                  <span className="text-gray-500 text-xs">{new Date(entry.timestamp).toLocaleString()}</span>
                </div>
                <div className="text-xs text-gray-400 mt-1">
                  {entry.params.x_element}-{entry.params.o_element} · {entry.params.stack_sequence} · {entry.params.layer_modes.join('/')}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="flex gap-2 overflow-x-auto scrollbar-none">
        {tabs.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`flex items-center gap-2 px-3 py-2.5 sm:px-4 sm:py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap touch-manipulation ${
              activeTab === key
                ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30'
                : 'bg-gray-800 border border-gray-700 text-gray-400 hover:text-gray-200'
            }`}
          >
            <Icon className="w-4 h-4" />
            {label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
        <div className="space-y-4">
          <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-5">
            <h2 className="text-lg font-semibold text-white mb-4">预设配置</h2>
            <div className="flex flex-wrap gap-2">
              {PRESETS.map((preset) => (
                <button
                  key={preset.name}
                  onClick={() => applyPreset(preset)}
                  className="px-3 py-2 sm:px-3 sm:py-1.5 bg-violet-500/10 text-violet-400 border border-violet-500/20 rounded-lg text-xs hover:bg-violet-500/20 transition-colors min-h-[36px] sm:min-h-0"
                >
                  {preset.name}
                </button>
              ))}
            </div>
          </div>

          <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-5">
            <h2 className="text-lg font-semibold text-white mb-4">元素选择</h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
              <ElementSelector value={xElement} onChange={setXElement} label="X 元素" />
              <ElementSelector value={oElement} onChange={setOElement} label="O 元素" />
              <ElementSelector value={mElement} onChange={setMElement} label="M 元素" />
              <ElementSelector value={tElement} onChange={setTElement} label="T 元素" />
              <ElementSelector value={bElement} onChange={setBElement} label="B 元素" />
              <div>
                <label className={labelCls}>X-O 距离 (Å)</label>
                <input type="number" step="0.001" value={targetXoDistance} onChange={(e) => setTargetXoDistance(parseFloat(e.target.value) || 0)} className={inputCls} />
              </div>
            </div>
          </div>

          <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-5">
            <h2 className="text-lg font-semibold text-white mb-4">网格与堆叠</h2>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className={labelCls}>NX</label>
                <input type="number" value={nx} onChange={(e) => setNx(parseInt(e.target.value) || 1)} className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>NY</label>
                <input type="number" value={ny} onChange={(e) => setNy(parseInt(e.target.value) || 1)} className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>堆叠序列</label>
                <input value={stackSequence} onChange={(e) => setStackSequence(e.target.value)} className={inputCls} />
              </div>
            </div>
            <div className="mt-3 flex flex-wrap gap-4">
              <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer min-h-[36px]">
                <input
                  type="checkbox"
                  checked={enableT}
                  onChange={(e) => setEnableT(e.target.checked)}
                  className="w-5 h-5 rounded border-gray-600 bg-gray-800 text-cyan-500 focus:ring-cyan-500"
                />
                启用T层系
              </label>
              <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer min-h-[36px]">
                <input
                  type="checkbox"
                  checked={enableB}
                  onChange={(e) => setEnableB(e.target.checked)}
                  className="w-5 h-5 rounded border-gray-600 bg-gray-800 text-cyan-500 focus:ring-cyan-500"
                />
                启用B层系
              </label>
              <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer min-h-[36px]">
                <input
                  type="checkbox"
                  checked={allowNonNeutral}
                  onChange={(e) => setAllowNonNeutral(e.target.checked)}
                  className="w-5 h-5 rounded border-gray-600 bg-gray-800 text-cyan-500 focus:ring-cyan-500"
                />
                允许非电中性
              </label>
            </div>
          </div>

          <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-white">层配置</h2>
              <button onClick={addLayer} className="flex items-center gap-1 px-3 py-1.5 bg-cyan-500/10 text-cyan-400 rounded-lg text-sm hover:bg-cyan-500/20 transition-colors">
                <Plus className="w-4 h-4" />
                添加层
              </button>
            </div>

            <div className="mb-3">
              <p className="text-xs text-gray-500 mb-2">快速插入</p>
              <div className="flex flex-wrap gap-1.5">
                {QUICK_LAYER_INSERTIONS.map((insertion) => (
                  <button
                    key={insertion.label}
                    onClick={() => insertLayers(insertion.modes)}
                    className="px-3 py-2 sm:px-2 sm:py-1 bg-gray-700/50 text-gray-400 rounded text-xs hover:bg-gray-700 hover:text-gray-200 transition-colors min-h-[36px] sm:min-h-0"
                  >
                    {insertion.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="space-y-2">
              {layers.map((layer, i) => (
                <div
                  key={i}
                  draggable
                  onDragStart={() => handleDragStart(i)}
                  onDragOver={(e) => handleDragOver(e, i)}
                  onDragEnd={handleDragEnd}
                  className={`flex flex-wrap items-center gap-2 bg-gray-900/50 rounded-lg p-2 transition-all ${
                    draggedLayer === i ? 'opacity-50' : ''
                  }`}
                >
                  <div className="cursor-grab text-gray-600 hover:text-gray-400">
                    <GripVertical className="w-4 h-4" />
                  </div>
                  <div className="relative">
                    <select
                      value={layer.mode}
                      onChange={(e) => updateLayer(i, 'mode', e.target.value)}
                      onMouseEnter={() => setHoveredLayerMode(layer.mode)}
                      onMouseLeave={() => setHoveredLayerMode(null)}
                      className="bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-sm text-gray-200 focus:outline-none focus:border-cyan-500"
                    >
                      {LAYER_MODES.map((m) => (
                        <option key={m} value={m}>{m}</option>
                      ))}
                    </select>
                    {hoveredLayerMode === layer.mode && (
                      <div className="absolute top-full left-0 mt-1 px-2 py-1 bg-gray-900 border border-gray-700 rounded text-xs text-gray-300 whitespace-nowrap z-10">
                        {LAYER_MODE_DESCRIPTIONS[layer.mode]}
                      </div>
                    )}
                  </div>
                  <input
                    type="number"
                    value={layer.angle}
                    onChange={(e) => updateLayer(i, 'angle', parseFloat(e.target.value) || 0)}
                    placeholder="角度"
                    className="bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-sm text-gray-200 w-full sm:w-20 focus:outline-none focus:border-cyan-500"
                  />
                  <input
                    type="number"
                    step="0.01"
                    value={layer.dx}
                    onChange={(e) => updateLayer(i, 'dx', parseFloat(e.target.value) || 0)}
                    placeholder="dx"
                    className="bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-sm text-gray-200 w-full sm:w-20 focus:outline-none focus:border-cyan-500"
                  />
                  <input
                    type="number"
                    step="0.01"
                    value={layer.dy}
                    onChange={(e) => updateLayer(i, 'dy', parseFloat(e.target.value) || 0)}
                    placeholder="dy"
                    className="bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-sm text-gray-200 w-full sm:w-20 focus:outline-none focus:border-cyan-500"
                  />
                  <button onClick={() => duplicateLayer(i)} className="touch-icon-btn text-gray-500 hover:text-cyan-400 transition-colors" title="复制层">
                    <Copy className="w-4 h-4" />
                  </button>
                  <button onClick={() => removeLayer(i)} className="touch-icon-btn text-red-400 hover:text-red-300 transition-colors">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          </div>

          {warnings.length > 0 && (
            <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4">
              <h3 className="text-amber-400 text-sm font-semibold mb-2">参数警告</h3>
              <ul className="space-y-1">
                {warnings.map((w, i) => (
                  <li key={i} className={`text-xs ${w.severity === 'error' ? 'text-red-400' : 'text-amber-300'}`}>
                    • {w.message}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="flex gap-3">
            {activeTab === 'basic' && (
              <button
                onClick={handleGenerate}
                disabled={generating}
                className="flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-cyan-500 text-white rounded-xl font-medium hover:bg-cyan-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <FlaskConical className="w-5 h-5" />
                {generating ? '生成中...' : '生成结构'}
              </button>
            )}
            {activeTab === 'full' && (
              <button
                onClick={handleFullAnalysis}
                disabled={generating}
                className="flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-violet-500 text-white rounded-xl font-medium hover:bg-violet-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <Network className="w-5 h-5" />
                {generating ? '分析中...' : '完整分析'}
              </button>
            )}
            {activeTab === 'layers' && (
              <button
                onClick={handleLayerProjection}
                disabled={generating}
                className="flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-emerald-500 text-white rounded-xl font-medium hover:bg-emerald-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <Layers className="w-5 h-5" />
                {generating ? '计算中...' : '层投影分析'}
              </button>
            )}
            {activeTab === 'coordination' && (
              <button
                onClick={handleCoordination}
                disabled={generating}
                className="flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-amber-500 text-white rounded-xl font-medium hover:bg-amber-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <Atom className="w-5 h-5" />
                {generating ? '分析中...' : '配位环境分析'}
              </button>
            )}
            {result && activeTab === 'basic' && (
              <>
                <button
                  onClick={handleSave}
                  className="flex items-center gap-2 px-4 py-3 bg-gray-800 border border-gray-700 text-gray-300 rounded-xl hover:border-cyan-500/50 transition-colors"
                >
                  <Save className="w-5 h-5" />
                  保存
                </button>
                <button
                  onClick={handleExportCIF}
                  className="flex items-center gap-2 px-4 py-3 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 rounded-xl hover:bg-emerald-500/20 transition-colors"
                >
                  <Download className="w-5 h-5" />
                  导出CIF
                </button>
                <button
                  onClick={handleCopyCIF}
                  className="flex items-center gap-2 px-4 py-3 bg-gray-800 border border-gray-700 text-gray-300 rounded-xl hover:border-cyan-500/50 transition-colors"
                >
                  <Copy className="w-5 h-5" />
                  {copiedCIF ? '已复制!' : '复制CIF'}
                </button>
              </>
            )}
          </div>

          {error && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400 text-sm">
              {error}
            </div>
          )}
        </div>

        <div className="space-y-4">
          {activeTab === 'basic' && (result ? (
            <>
              <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-5">
                <h2 className="text-lg font-semibold text-white mb-4">三维预览</h2>
                <Suspense fallback={<div className="h-96 bg-gray-900 rounded-lg flex items-center justify-center"><div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" /></div>}>
                <CrystalViewer
                  atoms={result.atom_sites}
                  lattice={result.lattice}
                  className="h-96"
                  showBonds
                />
                </Suspense>
              </div>
              <StructureInfoPanel result={result} />
            </>
          ) : (
            <EmptyPlaceholder icon={FlaskConical} text="配置参数并生成结构" />
          ))}

          {activeTab === 'full' && (fullResult ? (
            <>
              <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-5">
                <h2 className="text-lg font-semibold text-white mb-4">三维结构</h2>
                <Suspense fallback={<div className="h-96 bg-gray-900 rounded-lg flex items-center justify-center"><div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" /></div>}>
                <CrystalViewer
                  atoms={fullResult.structure.atom_sites}
                  lattice={fullResult.structure.lattice}
                  className="h-96"
                  showBonds
                  initialMode="polyhedral"
                />
                </Suspense>
              </div>

              <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-5">
                <h2 className="text-lg font-semibold text-white mb-3">原胞分析</h2>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-400">化学式</span>
                    <span className="text-white font-medium">{fullResult.primitive.formula}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">空间群</span>
                    <span className="text-white">{fullResult.primitive.space_group} (#{fullResult.primitive.space_group_number})</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">电中性</span>
                    <span className={fullResult.primitive.is_neutral ? 'text-emerald-400' : 'text-amber-400'}>
                      {fullResult.primitive.is_neutral ? '是' : '否'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">原子数</span>
                    <span className="text-white">{fullResult.primitive.atom_sites.length}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">独立位点</span>
                    <span className="text-white">{fullResult.primitive.unique_sites.length}</span>
                  </div>
                </div>
              </div>

              {Object.keys(fullResult.wyckoff_signature).length > 0 && (
                <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-5">
                  <h2 className="text-lg font-semibold text-white mb-3">Wyckoff 签名</h2>
                  <div className="space-y-1 text-sm">
                    {Object.entries(fullResult.wyckoff_signature).map(([key, value]) => (
                      <div key={key} className="flex justify-between">
                        <span className="text-gray-400">{key}</span>
                        <span className="text-white font-mono">{value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {fullResult.coordination.environments.length > 0 && (
                <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-5">
                  <h2 className="text-lg font-semibold text-white mb-3">配位环境</h2>
                  <div className="space-y-3">
                    {fullResult.coordination.environments.map((env, i) => (
                      <div key={i} className="bg-gray-900/50 rounded-lg p-3">
                        <div className="flex items-center justify-between">
                          <span className="text-white font-medium">{env.center.element}</span>
                          <span className="text-cyan-400 text-xs">CN={env.cn}</span>
                        </div>
                        <div className="mt-1 text-xs text-gray-400">
                          配位原子: {env.neighbors.map(n => n.element).join(', ')}
                        </div>
                        <div className="mt-1 text-xs text-gray-500">
                          距离: {env.neighbors.map(n => n.distance.toFixed(3)).join(', ')} Å
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-5">
                <h2 className="text-lg font-semibold text-white mb-3">原型档案</h2>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-400">原型编号</span>
                    <span className="text-cyan-400 font-mono">{fullResult.prototype.topology_theory.prototype_id}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">理想空间群</span>
                    <span className="text-white">{fullResult.prototype.prototype_crystallography.ideal_space_group}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">晶系</span>
                    <span className="text-white">{fullResult.prototype.prototype_crystallography.crystal_system}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">参考网格</span>
                    <span className="text-white font-mono">{fullResult.prototype.topology_theory.reference_grid}</span>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <EmptyPlaceholder icon={Network} text={'点击「完整分析」获取完整结果'} />
          ))}

          {activeTab === 'layers' && (layerData ? (
            <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-5">
              <h2 className="text-lg font-semibold text-white mb-4">层投影（共 {layerData.length} 层）</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {layerData.map((layer, i) => (
                  <LayerProjectionSVG key={i} layer={layer} />
                ))}
              </div>
            </div>
          ) : (
            <EmptyPlaceholder icon={Layers} text={'点击「层投影分析」查看各层原子分布'} />
          ))}

          {activeTab === 'coordination' && (coordEnvs ? (
            <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-5">
              <h2 className="text-lg font-semibold text-white mb-4">配位环境（共 {coordEnvs.length} 个）</h2>
              <div className="space-y-4">
                {coordEnvs.map((env, i) => (
                  <div key={i} className="bg-gray-900/50 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <span className="text-lg font-bold" style={{ color: ELEMENT_COLORS[env.center.element] || '#fff' }}>
                          {env.center.element}
                        </span>
                        <span className="text-gray-400 text-sm">配位数: {env.cn}</span>
                      </div>
                      <span className="text-xs text-gray-500">
                        ({env.center.x.toFixed(3)}, {env.center.y.toFixed(3)}, {env.center.z.toFixed(3)})
                      </span>
                    </div>
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs">
                        <thead>
                          <tr className="border-b border-gray-700/50">
                            <th className="text-left px-2 py-1 text-gray-500">元素</th>
                            <th className="text-left px-2 py-1 text-gray-500">dx</th>
                            <th className="text-left px-2 py-1 text-gray-500">dy</th>
                            <th className="text-left px-2 py-1 text-gray-500">dz</th>
                            <th className="text-left px-2 py-1 text-gray-500">距离</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-700/20">
                          {env.neighbors.map((n, j) => (
                            <tr key={j}>
                              <td className="px-2 py-1" style={{ color: ELEMENT_COLORS[n.element] || '#fff' }}>{n.element}</td>
                              <td className="px-2 py-1 text-gray-400 font-mono">{n.dx.toFixed(4)}</td>
                              <td className="px-2 py-1 text-gray-400 font-mono">{n.dy.toFixed(4)}</td>
                              <td className="px-2 py-1 text-gray-400 font-mono">{n.dz.toFixed(4)}</td>
                              <td className="px-2 py-1 text-cyan-400 font-mono">{n.distance.toFixed(4)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <EmptyPlaceholder icon={Atom} text={'点击「配位环境分析」查看配位信息'} />
          ))}
        </div>
      </div>
    </div>
  )
}

function StructureInfoPanel({ result }: { result: GenerateResult }) {
  return (
    <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-5">
      <h2 className="text-lg font-semibold text-white mb-3">生成结果</h2>
      <div className="space-y-2 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-400">化学式</span>
          <span className="text-white font-medium">{result.formula}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">空间群</span>
          <span className="text-white">{result.space_group.symbol} (#{result.space_group.number})</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">晶系</span>
          <span className="text-white">{result.space_group.crystal_system}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">总原子数</span>
          <span className="text-white">{result.atom_sites.length}</span>
        </div>
      </div>

      <div className="mt-4 pt-3 border-t border-gray-700/50">
        <span className="text-gray-400 text-sm">原子计数</span>
        <div className="grid grid-cols-5 gap-2 mt-2">
          <div className="bg-gray-900/50 rounded-lg p-2 text-center">
            <p className="text-xs text-gray-500">X</p>
            <p className="text-sm font-mono text-cyan-400">{result.atom_counts.x_count}</p>
          </div>
          <div className="bg-gray-900/50 rounded-lg p-2 text-center">
            <p className="text-xs text-gray-500">O</p>
            <p className="text-sm font-mono text-red-400">{result.atom_counts.o_count}</p>
          </div>
          <div className="bg-gray-900/50 rounded-lg p-2 text-center">
            <p className="text-xs text-gray-500">M</p>
            <p className="text-sm font-mono text-emerald-400">{result.atom_counts.m_count}</p>
          </div>
          <div className="bg-gray-900/50 rounded-lg p-2 text-center">
            <p className="text-xs text-gray-500">T</p>
            <p className="text-sm font-mono text-violet-400">{result.atom_counts.t_count}</p>
          </div>
          <div className="bg-gray-900/50 rounded-lg p-2 text-center">
            <p className="text-xs text-gray-500">B</p>
            <p className="text-sm font-mono text-amber-400">{result.atom_counts.b_count}</p>
          </div>
        </div>
      </div>

      <div className="mt-4 pt-3 border-t border-gray-700/50">
        <span className="text-gray-400 text-sm">晶格参数</span>
        <div className="grid grid-cols-3 gap-2 mt-2">
          {(['a', 'b', 'c', 'alpha', 'beta', 'gamma'] as const).map((key) => (
            <div key={key} className="bg-gray-900/50 rounded-lg p-2">
              <p className="text-xs text-gray-500 uppercase">{key}</p>
              <p className="text-sm font-mono text-white">
                {result.lattice[key].toFixed(4)}
                {['alpha', 'beta', 'gamma'].includes(key) ? '°' : ' Å'}
              </p>
            </div>
          ))}
        </div>
      </div>

      {result.topology.expanded_modes.length > 0 && (
        <div className="mt-4 pt-3 border-t border-gray-700/50">
          <span className="text-gray-400 text-sm">展开模式</span>
          <div className="flex flex-wrap gap-1.5 mt-2">
            {result.topology.expanded_modes.map((m, i) => (
              <span key={i} className="bg-violet-500/10 text-violet-400 px-2 py-0.5 rounded text-xs font-mono">
                {m}
              </span>
            ))}
          </div>
        </div>
      )}

      {result.topology.expanded_shifts.length > 0 && (
        <div className="mt-3">
          <span className="text-gray-400 text-sm">展开位移</span>
          <div className="flex flex-wrap gap-1.5 mt-2">
            {result.topology.expanded_shifts.map((s, i) => (
              <span key={i} className="bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded text-xs font-mono">
                {s}
              </span>
            ))}
          </div>
        </div>
      )}

      {result.topology && (
        <div className="mt-3">
          <span className="text-gray-400 text-sm">拓扑信息</span>
          <div className="mt-1 text-sm space-y-1">
            <div className="flex justify-between">
              <span className="text-gray-500">参考网格</span>
              <span className="text-cyan-400">{result.topology.reference_grid}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">基础长度</span>
              <span className="text-white">{result.topology.base_length.toFixed(4)} Å</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">精确标志</span>
              <span className={result.topology.exact_flag ? 'text-emerald-400' : 'text-amber-400'}>
                {result.topology.exact_flag ? '是' : '否'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">堆叠序列</span>
              <span className="text-white font-mono">{result.topology.main_shift_sequence.join(' → ')}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function EmptyPlaceholder({ icon: Icon, text }: { icon: typeof FlaskConical; text: string }) {
  return (
    <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-5 h-96 flex items-center justify-center">
      <div className="text-center text-gray-500">
        <Icon className="w-12 h-12 mx-auto mb-3 opacity-30" />
        <p>{text}</p>
      </div>
    </div>
  )
}
