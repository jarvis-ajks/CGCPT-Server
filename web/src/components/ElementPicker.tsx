import { useState, useEffect } from 'react'
import { X, Search } from 'lucide-react'

interface ElementPickerProps {
  value: string
  onChange: (element: string) => void
  label?: string
}

const ELEMENT_CATEGORIES = {
  'alkali': { name: '碱金属', color: 'bg-red-500/20 text-red-400 border-red-500/30' },
  'alkaline': { name: '碱土金属', color: 'bg-orange-500/20 text-orange-400 border-orange-500/30' },
  'transition': { name: '过渡金属', color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30' },
  'post-transition': { name: '后过渡金属', color: 'bg-green-500/20 text-green-400 border-green-500/30' },
  'metalloid': { name: '准金属', color: 'bg-teal-500/20 text-teal-400 border-teal-500/30' },
  'nonmetal': { name: '非金属', color: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30' },
  'halogen': { name: '卤素', color: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
  'noble': { name: '稀有气体', color: 'bg-purple-500/20 text-purple-400 border-purple-500/30' },
  'lanthanide': { name: '镧系', color: 'bg-pink-500/20 text-pink-400 border-pink-500/30' },
  'actinide': { name: '锕系', color: 'bg-rose-500/20 text-rose-400 border-rose-500/30' },
}

const ELEMENT_DATA: Record<string, { name: string; symbol: string; number: number; category: keyof typeof ELEMENT_CATEGORIES }> = {
  'H': { name: '氢', symbol: 'H', number: 1, category: 'nonmetal' },
  'He': { name: '氦', symbol: 'He', number: 2, category: 'noble' },
  'Li': { name: '锂', symbol: 'Li', number: 3, category: 'alkali' },
  'Be': { name: '铍', symbol: 'Be', number: 4, category: 'alkaline' },
  'B': { name: '硼', symbol: 'B', number: 5, category: 'metalloid' },
  'C': { name: '碳', symbol: 'C', number: 6, category: 'nonmetal' },
  'N': { name: '氮', symbol: 'N', number: 7, category: 'nonmetal' },
  'O': { name: '氧', symbol: 'O', number: 8, category: 'nonmetal' },
  'F': { name: '氟', symbol: 'F', number: 9, category: 'halogen' },
  'Ne': { name: '氖', symbol: 'Ne', number: 10, category: 'noble' },
  'Na': { name: '钠', symbol: 'Na', number: 11, category: 'alkali' },
  'Mg': { name: '镁', symbol: 'Mg', number: 12, category: 'alkaline' },
  'Al': { name: '铝', symbol: 'Al', number: 13, category: 'post-transition' },
  'Si': { name: '硅', symbol: 'Si', number: 14, category: 'metalloid' },
  'P': { name: '磷', symbol: 'P', number: 15, category: 'nonmetal' },
  'S': { name: '硫', symbol: 'S', number: 16, category: 'nonmetal' },
  'Cl': { name: '氯', symbol: 'Cl', number: 17, category: 'halogen' },
  'Ar': { name: '氩', symbol: 'Ar', number: 18, category: 'noble' },
  'K': { name: '钾', symbol: 'K', number: 19, category: 'alkali' },
  'Ca': { name: '钙', symbol: 'Ca', number: 20, category: 'alkaline' },
  'Sc': { name: '钪', symbol: 'Sc', number: 21, category: 'transition' },
  'Ti': { name: '钛', symbol: 'Ti', number: 22, category: 'transition' },
  'V': { name: '钒', symbol: 'V', number: 23, category: 'transition' },
  'Cr': { name: '铬', symbol: 'Cr', number: 24, category: 'transition' },
  'Mn': { name: '锰', symbol: 'Mn', number: 25, category: 'transition' },
  'Fe': { name: '铁', symbol: 'Fe', number: 26, category: 'transition' },
  'Co': { name: '钴', symbol: 'Co', number: 27, category: 'transition' },
  'Ni': { name: '镍', symbol: 'Ni', number: 28, category: 'transition' },
  'Cu': { name: '铜', symbol: 'Cu', number: 29, category: 'transition' },
  'Zn': { name: '锌', symbol: 'Zn', number: 30, category: 'transition' },
  'Ga': { name: '镓', symbol: 'Ga', number: 31, category: 'post-transition' },
  'Ge': { name: '锗', symbol: 'Ge', number: 32, category: 'metalloid' },
  'As': { name: '砷', symbol: 'As', number: 33, category: 'metalloid' },
  'Se': { name: '硒', symbol: 'Se', number: 34, category: 'nonmetal' },
  'Br': { name: '溴', symbol: 'Br', number: 35, category: 'halogen' },
  'Kr': { name: '氪', symbol: 'Kr', number: 36, category: 'noble' },
  'Rb': { name: '铷', symbol: 'Rb', number: 37, category: 'alkali' },
  'Sr': { name: '锶', symbol: 'Sr', number: 38, category: 'alkaline' },
  'Y': { name: '钇', symbol: 'Y', number: 39, category: 'transition' },
  'Zr': { name: '锆', symbol: 'Zr', number: 40, category: 'transition' },
  'Nb': { name: '铌', symbol: 'Nb', number: 41, category: 'transition' },
  'Mo': { name: '钼', symbol: 'Mo', number: 42, category: 'transition' },
  'Tc': { name: '锝', symbol: 'Tc', number: 43, category: 'transition' },
  'Ru': { name: '钌', symbol: 'Ru', number: 44, category: 'transition' },
  'Rh': { name: '铑', symbol: 'Rh', number: 45, category: 'transition' },
  'Pd': { name: '钯', symbol: 'Pd', number: 46, category: 'transition' },
  'Ag': { name: '银', symbol: 'Ag', number: 47, category: 'transition' },
  'Cd': { name: '镉', symbol: 'Cd', number: 48, category: 'transition' },
  'In': { name: '铟', symbol: 'In', number: 49, category: 'post-transition' },
  'Sn': { name: '锡', symbol: 'Sn', number: 50, category: 'post-transition' },
  'Sb': { name: '锑', symbol: 'Sb', number: 51, category: 'metalloid' },
  'Te': { name: '碲', symbol: 'Te', number: 52, category: 'metalloid' },
  'I': { name: '碘', symbol: 'I', number: 53, category: 'halogen' },
  'Xe': { name: '氙', symbol: 'Xe', number: 54, category: 'noble' },
  'Cs': { name: '铯', symbol: 'Cs', number: 55, category: 'alkali' },
  'Ba': { name: '钡', symbol: 'Ba', number: 56, category: 'alkaline' },
  'La': { name: '镧', symbol: 'La', number: 57, category: 'lanthanide' },
  'Ce': { name: '铈', symbol: 'Ce', number: 58, category: 'lanthanide' },
  'Pr': { name: '镨', symbol: 'Pr', number: 59, category: 'lanthanide' },
  'Nd': { name: '钕', symbol: 'Nd', number: 60, category: 'lanthanide' },
  'Pm': { name: '钷', symbol: 'Pm', number: 61, category: 'lanthanide' },
  'Sm': { name: '钐', symbol: 'Sm', number: 62, category: 'lanthanide' },
  'Eu': { name: '铕', symbol: 'Eu', number: 63, category: 'lanthanide' },
  'Gd': { name: '钆', symbol: 'Gd', number: 64, category: 'lanthanide' },
  'Tb': { name: '铽', symbol: 'Tb', number: 65, category: 'lanthanide' },
  'Dy': { name: '镝', symbol: 'Dy', number: 66, category: 'lanthanide' },
  'Ho': { name: '钬', symbol: 'Ho', number: 67, category: 'lanthanide' },
  'Er': { name: '铒', symbol: 'Er', number: 68, category: 'lanthanide' },
  'Tm': { name: '铥', symbol: 'Tm', number: 69, category: 'lanthanide' },
  'Yb': { name: '镱', symbol: 'Yb', number: 70, category: 'lanthanide' },
  'Lu': { name: '镥', symbol: 'Lu', number: 71, category: 'lanthanide' },
  'Hf': { name: '铪', symbol: 'Hf', number: 72, category: 'transition' },
  'Ta': { name: '钽', symbol: 'Ta', number: 73, category: 'transition' },
  'W': { name: '钨', symbol: 'W', number: 74, category: 'transition' },
  'Re': { name: '铼', symbol: 'Re', number: 75, category: 'transition' },
  'Os': { name: '锇', symbol: 'Os', number: 76, category: 'transition' },
  'Ir': { name: '铱', symbol: 'Ir', number: 77, category: 'transition' },
  'Pt': { name: '铂', symbol: 'Pt', number: 78, category: 'transition' },
  'Au': { name: '金', symbol: 'Au', number: 79, category: 'transition' },
  'Hg': { name: '汞', symbol: 'Hg', number: 80, category: 'transition' },
  'Tl': { name: '铊', symbol: 'Tl', number: 81, category: 'post-transition' },
  'Pb': { name: '铅', symbol: 'Pb', number: 82, category: 'post-transition' },
  'Bi': { name: '铋', symbol: 'Bi', number: 83, category: 'post-transition' },
  'Po': { name: '钋', symbol: 'Po', number: 84, category: 'metalloid' },
  'At': { name: '砹', symbol: 'At', number: 85, category: 'halogen' },
  'Rn': { name: '氡', symbol: 'Rn', number: 86, category: 'noble' },
  'Fr': { name: '钫', symbol: 'Fr', number: 87, category: 'alkali' },
  'Ra': { name: '镭', symbol: 'Ra', number: 88, category: 'alkaline' },
  'Ac': { name: '锕', symbol: 'Ac', number: 89, category: 'actinide' },
  'Th': { name: '钍', symbol: 'Th', number: 90, category: 'actinide' },
  'Pa': { name: '镤', symbol: 'Pa', number: 91, category: 'actinide' },
  'U': { name: '铀', symbol: 'U', number: 92, category: 'actinide' },
  'Np': { name: '镎', symbol: 'Np', number: 93, category: 'actinide' },
  'Pu': { name: '钚', symbol: 'Pu', number: 94, category: 'actinide' },
  'Am': { name: '镅', symbol: 'Am', number: 95, category: 'actinide' },
}

const COMMON_ELEMENTS = ['H', 'C', 'N', 'O', 'S', 'Fe', 'Cu', 'Zn', 'Na', 'K', 'Ca', 'Mg', 'Al', 'Si', 'P']

const PERIODIC_TABLE_LAYOUT = [
  ['H', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', 'He'],
  ['Li', 'Be', '', '', '', '', '', '', '', '', '', '', 'B', 'C', 'N', 'O', 'F', 'Ne'],
  ['Na', 'Mg', '', '', '', '', '', '', '', '', '', '', 'Al', 'Si', 'P', 'S', 'Cl', 'Ar'],
  ['K', 'Ca', 'Sc', 'Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn', 'Ga', 'Ge', 'As', 'Se', 'Br', 'Kr'],
  ['Rb', 'Sr', 'Y', 'Zr', 'Nb', 'Mo', 'Tc', 'Ru', 'Rh', 'Pd', 'Ag', 'Cd', 'In', 'Sn', 'Sb', 'Te', 'I', 'Xe'],
  ['Cs', 'Ba', 'La', 'Hf', 'Ta', 'W', 'Re', 'Os', 'Ir', 'Pt', 'Au', 'Hg', 'Tl', 'Pb', 'Bi', 'Po', 'At', 'Rn'],
  ['Fr', 'Ra', 'Ac', 'Rf', 'Db', 'Sg', 'Bh', 'Hs', 'Mt', 'Ds', 'Rg', 'Cn', 'Nh', 'Fl', 'Mc', 'Lv', 'Ts', 'Og'],
]

const LANTHANIDES = ['La', 'Ce', 'Pr', 'Nd', 'Pm', 'Sm', 'Eu', 'Gd', 'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb', 'Lu']
const ACTINIDES = ['Ac', 'Th', 'Pa', 'U', 'Np', 'Pu', 'Am', 'Cm', 'Bk', 'Cf', 'Es', 'Fm', 'Md', 'No', 'Lr']

export default function ElementPicker({ value: _value, onChange, label }: ElementPickerProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [recentElements, setRecentElements] = useState<string[]>([])

  useEffect(() => {
    try {
      const stored = localStorage.getItem('cgcpt_recent_elements')
      if (stored) {
        setRecentElements(JSON.parse(stored))
      }
    } catch {}
  }, [])

  const updateRecent = (element: string) => {
    const updated = [element, ...recentElements.filter(e => e !== element)].slice(0, 10)
    setRecentElements(updated)
    localStorage.setItem('cgcpt_recent_elements', JSON.stringify(updated))
  }

  const handleSelect = (element: string) => {
    updateRecent(element)
    onChange(element)
    setIsOpen(false)
    setSearch('')
  }

  const filteredElements = Object.values(ELEMENT_DATA).filter(el => {
    if (!search) return true
    return el.symbol.toLowerCase().includes(search.toLowerCase()) ||
           el.name.includes(search)
  })

  const getElementStyle = (symbol: string) => {
    const el = ELEMENT_DATA[symbol]
    if (!el) return 'bg-gray-800 text-gray-600'
    const cat = ELEMENT_CATEGORIES[el.category]
    return `${cat.color} border`
  }

  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className="w-full px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-gray-300 text-sm hover:border-cyan-500/50 transition-colors text-left"
      >
        {label || '选择元素'}
      </button>

      {isOpen && (
        <div className="fixed inset-0 bg-black/70 flex items-end sm:items-center justify-center z-50">
          <div className="bg-gray-900 border border-gray-700 rounded-t-2xl sm:rounded-2xl w-full sm:max-w-4xl max-h-[95vh] sm:max-h-[90vh] overflow-hidden">
            <div className="p-3 sm:p-4 border-b border-gray-800 flex items-center justify-between">
              <h3 className="text-base sm:text-lg font-medium text-white">选择元素</h3>
              <button
                onClick={() => { setIsOpen(false); setSearch('') }}
                className="p-2 text-gray-400 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-4 border-b border-gray-800">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="搜索元素符号或名称..."
                  className="w-full pl-10 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-200 placeholder-gray-500 focus:outline-none focus:border-cyan-500"
                  autoFocus
                />
              </div>
            </div>

            <div className="p-4 overflow-y-auto max-h-[calc(90vh-140px)]">
              {recentElements.length > 0 && !search && (
                <div className="mb-6">
                  <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
                    最近使用
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {recentElements.map(symbol => {
                      const el = ELEMENT_DATA[symbol]
                      if (!el) return null
                      return (
                        <button
                          key={symbol}
                          onClick={() => handleSelect(symbol)}
                          className={`px-3 py-2 rounded-lg border ${getElementStyle(symbol)} text-sm font-medium hover:opacity-80 transition-opacity`}
                        >
                          <div>{symbol}</div>
                          <div className="text-xs opacity-70">{el.name}</div>
                        </button>
                      )
                    })}
                  </div>
                </div>
              )}

              {!search && (
                <>
                  <div className="mb-4">
                    <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
                      常用元素
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {COMMON_ELEMENTS.map(symbol => {
                        const el = ELEMENT_DATA[symbol]
                        if (!el) return null
                        return (
                          <button
                            key={symbol}
                            onClick={() => handleSelect(symbol)}
                            className={`px-3 py-2 rounded-lg border ${getElementStyle(symbol)} text-sm font-medium hover:opacity-80 transition-opacity`}
                          >
                            <div>{symbol}</div>
                            <div className="text-xs opacity-70">{el.name}</div>
                          </button>
                        )
                      })}
                    </div>
                  </div>

                  <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
                    元素周期表
                  </h4>
                  <div className="overflow-x-auto -mx-2 px-2 pb-2">
                  <div className="space-y-0.5" style={{ minWidth: '500px' }}>
                    {PERIODIC_TABLE_LAYOUT.map((row, i) => (
                      <div key={i} className="flex gap-0.5">
                        {row.map((symbol, j) => {
                          if (!symbol) {
                            return <div key={j} className="w-7 h-7 sm:w-10 sm:h-10" />
                          }
                          const el = ELEMENT_DATA[symbol]
                          if (!el) {
                            return (
                              <button
                                key={j}
                                className="w-7 h-7 sm:w-10 sm:h-10 rounded bg-gray-800/50 text-gray-600 text-[8px] sm:text-xs flex flex-col items-center justify-center touch-manipulation"
                              >
                                {symbol}
                              </button>
                            )
                          }
                          return (
                            <button
                              key={j}
                              onClick={() => handleSelect(symbol)}
                              className={`w-7 h-7 sm:w-10 sm:h-10 rounded border ${getElementStyle(symbol)} text-[8px] sm:text-xs flex flex-col items-center justify-center hover:opacity-80 active:opacity-60 transition-opacity touch-manipulation`}
                            >
                              <span className="text-[6px] sm:text-[8px] opacity-60 leading-none">{el.number}</span>
                              <span className="font-bold leading-none">{symbol}</span>
                            </button>
                          )
                        })}
                      </div>
                    ))}
                  </div>
                  </div>

                  <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wider mt-4 mb-2">
                    镧系元素
                  </h4>
                  <div className="flex flex-wrap gap-1">
                    {LANTHANIDES.map(symbol => {
                      const el = ELEMENT_DATA[symbol]
                      if (!el) return null
                      return (
                        <button
                          key={symbol}
                          onClick={() => handleSelect(symbol)}
                          className={`w-7 h-7 sm:w-10 sm:h-10 rounded border ${getElementStyle(symbol)} text-[8px] sm:text-xs flex flex-col items-center justify-center hover:opacity-80 active:opacity-60 transition-opacity touch-manipulation`}
                        >
                          <span className="text-[6px] sm:text-[8px] opacity-60 leading-none">{el.number}</span>
                          <span className="font-bold leading-none">{symbol}</span>
                        </button>
                      )
                    })}
                  </div>

                  <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wider mt-4 mb-2">
                    锕系元素
                  </h4>
                  <div className="flex flex-wrap gap-1">
                    {ACTINIDES.map(symbol => {
                      const el = ELEMENT_DATA[symbol]
                      if (!el) return null
                      return (
                        <button
                          key={symbol}
                          onClick={() => handleSelect(symbol)}
                          className={`w-7 h-7 sm:w-10 sm:h-10 rounded border ${getElementStyle(symbol)} text-[8px] sm:text-xs flex flex-col items-center justify-center hover:opacity-80 active:opacity-60 transition-opacity touch-manipulation`}
                        >
                          <span className="text-[6px] sm:text-[8px] opacity-60 leading-none">{el.number}</span>
                          <span className="font-bold leading-none">{symbol}</span>
                        </button>
                      )
                    })}
                  </div>
                </>
              )}

              {search && (
                <div>
                  <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
                    搜索结果
                  </h4>
                  {filteredElements.length === 0 ? (
                    <p className="text-gray-500 text-sm">未找到匹配的元素</p>
                  ) : (
                    <div className="flex flex-wrap gap-2">
                      {filteredElements.map(el => (
                        <button
                          key={el.symbol}
                          onClick={() => handleSelect(el.symbol)}
                          className={`px-3 py-2 rounded-lg border ${getElementStyle(el.symbol)} text-sm font-medium hover:opacity-80 transition-opacity`}
                        >
                          <div>{el.symbol}</div>
                          <div className="text-xs opacity-70">{el.name}</div>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  )
}
