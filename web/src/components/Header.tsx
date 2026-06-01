import { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Search, Heart, FlaskConical, Network, Layers, Clock, X, ChevronDown } from 'lucide-react'

interface FavoriteItem {
  materialId: string
  formula: string
  spaceGroup: string
  topology: string
  addedAt: number
  elements: string[]
  verified: boolean
}

interface RecentItem {
  materialId: string
  formula: string
  spaceGroup: string
  topology: string
  viewedAt: number
}

type SearchType = 'formula' | 'topology' | 'space_group'

const SEARCH_TYPE_CONFIG: Record<SearchType, { label: string; shortLabel: string; icon: typeof FlaskConical; placeholder: string }> = {
  formula: { label: '化学式', shortLabel: '式', icon: FlaskConical, placeholder: '输入化学式搜索...' },
  topology: { label: '拓扑', shortLabel: '拓', icon: Network, placeholder: '输入拓扑名称...' },
  space_group: { label: '空间群', shortLabel: '群', icon: Layers, placeholder: '输入空间群搜索...' },
}

function loadRecentItems(): RecentItem[] {
  try {
    const data = localStorage.getItem('cgcpt_recent')
    return data ? JSON.parse(data) : []
  } catch {
    return []
  }
}

function loadSearchHistory(): string[] {
  try {
    const data = localStorage.getItem('cgcpt_search_history')
    return data ? JSON.parse(data) : []
  } catch {
    return []
  }
}

function saveSearchHistory(history: string[]): void {
  localStorage.setItem('cgcpt_search_history', JSON.stringify(history.slice(0, 20)))
}

function loadFavorites(): FavoriteItem[] {
  try {
    const data = localStorage.getItem('cgcpt_favorites')
    return data ? JSON.parse(data) : []
  } catch {
    return []
  }
}

export default function Header() {
  const [query, setQuery] = useState('')
  const [searchType, setSearchType] = useState<SearchType>('formula')
  const [isFocused, setIsFocused] = useState(false)
  const [showTypeMenu, setShowTypeMenu] = useState(false)
  const [recentItems] = useState<RecentItem[]>(loadRecentItems)
  const [searchHistory, setSearchHistory] = useState<string[]>(loadSearchHistory)
  const [favoritesCount, setFavoritesCount] = useState<number>(0)
  const navigate = useNavigate()
  const inputRef = useRef<HTMLInputElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    setFavoritesCount(loadFavorites().length)
    const handleStorage = () => {
      setFavoritesCount(loadFavorites().length)
      setSearchHistory(loadSearchHistory())
    }
    window.addEventListener('storage', handleStorage)
    return () => window.removeEventListener('storage', handleStorage)
  }, [])

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault()
        inputRef.current?.focus()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsFocused(false)
        setShowTypeMenu(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const suggestions = useMemo(() => {
    if (!query.trim()) return []
    const q = query.trim().toLowerCase()
    return recentItems
      .filter(item =>
        item.formula.toLowerCase().includes(q) ||
        item.spaceGroup.toLowerCase().includes(q) ||
        item.topology.toLowerCase().includes(q)
      )
      .slice(0, 5)
  }, [query, recentItems])

  const addToHistory = useCallback((value: string) => {
    const trimmed = value.trim()
    if (!trimmed) return
    const history = loadSearchHistory()
    const filtered = history.filter(h => h !== trimmed)
    const newHistory = [trimmed, ...filtered].slice(0, 20)
    saveSearchHistory(newHistory)
    setSearchHistory(newHistory)
  }, [])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (query.trim()) {
      addToHistory(query.trim())
      navigate(`/search?q=${encodeURIComponent(query.trim())}`)
      setIsFocused(false)
    }
  }

  const handleSuggestionClick = (item: RecentItem) => {
    navigate(`/materials/${item.materialId}`)
    setIsFocused(false)
  }

  const handleHistoryClick = (term: string) => {
    setQuery(term)
    addToHistory(term)
    navigate(`/search?q=${encodeURIComponent(term)}`)
    setIsFocused(false)
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setQuery(e.target.value)
    setShowTypeMenu(false)
  }

  const handleInputFocus = () => {
    setIsFocused(true)
  }

  const currentConfig = SEARCH_TYPE_CONFIG[searchType]
  const CurrentIcon = currentConfig.icon

  const showSuggestions = isFocused && query.trim() && suggestions.length > 0
  const showHistory = isFocused && !query.trim() && searchHistory.length > 0

  return (
    <header className="h-14 sm:h-16 bg-gray-950 border-b border-gray-800 flex items-center px-3 pl-12 lg:pl-6 gap-2 sm:gap-4">
      <div ref={containerRef} className="flex-1 max-w-xl relative">
        <form onSubmit={handleSubmit}>
          <div className="relative flex items-center">
            <div className="relative hidden sm:block">
              <button
                type="button"
                onClick={() => setShowTypeMenu(!showTypeMenu)}
                className="flex items-center gap-1.5 h-9 sm:h-10 pl-3 pr-2 bg-gray-900 border border-r-0 border-gray-700 rounded-l-lg text-xs text-gray-300 hover:text-white hover:border-cyan-500/50 transition-colors"
              >
                <CurrentIcon className="w-3.5 h-3.5 text-cyan-400" />
                <span>{currentConfig.label}</span>
                <ChevronDown className="w-3 h-3 text-gray-500" />
              </button>
              {showTypeMenu && (
                <div className="absolute top-full left-0 mt-1 bg-gray-800 border border-gray-700 rounded-lg shadow-xl z-50 overflow-hidden w-36">
                  {(Object.entries(SEARCH_TYPE_CONFIG) as [SearchType, typeof SEARCH_TYPE_CONFIG[SearchType]][]).map(([type, config]) => {
                    const Icon = config.icon
                    return (
                      <button
                        key={type}
                        type="button"
                        onClick={() => {
                          setSearchType(type)
                          setShowTypeMenu(false)
                          inputRef.current?.focus()
                        }}
                        className={`w-full flex items-center gap-2 px-3 py-2.5 text-sm transition-colors ${
                          searchType === type
                            ? 'bg-cyan-500/10 text-cyan-400'
                            : 'text-gray-300 hover:bg-gray-700/50 hover:text-white'
                        }`}
                      >
                        <Icon className="w-4 h-4" />
                        {config.label}
                      </button>
                    )
                  })}
                </div>
              )}
            </div>
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={handleInputChange}
                onFocus={handleInputFocus}
                placeholder={currentConfig.placeholder}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg sm:rounded-l-none sm:rounded-r-lg pl-10 pr-9 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-colors"
              />
              <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
                {query && (
                  <button
                    type="button"
                    onClick={() => setQuery('')}
                    className="p-1 text-gray-500 hover:text-white transition-colors"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>
          </div>
        </form>

        {showSuggestions && (
          <div className="absolute top-full left-0 right-0 mt-1 bg-gray-800 border border-gray-700 rounded-lg shadow-xl z-50 overflow-hidden">
            <div className="px-3 py-2 border-b border-gray-700/50">
              <span className="text-xs text-gray-500 flex items-center gap-1">
                <Search className="w-3 h-3" />
                搜索建议
              </span>
            </div>
            {suggestions.map(item => (
              <button
                key={item.materialId}
                type="button"
                onTouchStart={() => handleSuggestionClick(item)}
                onMouseDown={() => handleSuggestionClick(item)}
                className="w-full text-left px-3 py-2.5 hover:bg-gray-700/50 active:bg-gray-700/70 transition-colors flex items-center justify-between group"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <span className="text-sm text-cyan-400 font-medium truncate">{item.formula}</span>
                  <span className="text-xs text-gray-500 truncate">{item.spaceGroup}</span>
                </div>
                <span className="text-xs text-gray-600 flex-shrink-0 ml-2">{item.topology}</span>
              </button>
            ))}
          </div>
        )}

        {showHistory && (
          <div className="absolute top-full left-0 right-0 mt-1 bg-gray-800 border border-gray-700 rounded-lg shadow-xl z-50 overflow-hidden">
            <div className="flex items-center justify-between px-3 py-2 border-b border-gray-700/50">
              <span className="text-xs text-gray-500 flex items-center gap-1">
                <Clock className="w-3 h-3" />
                搜索历史
              </span>
              <button
                type="button"
                onTouchStart={() => {
                  saveSearchHistory([])
                  setSearchHistory([])
                }}
                onMouseDown={() => {
                  saveSearchHistory([])
                  setSearchHistory([])
                }}
                className="text-xs text-gray-500 hover:text-white transition-colors"
              >
                清除
              </button>
            </div>
            {searchHistory.slice(0, 10).map((term, i) => (
              <button
                key={`${term}-${i}`}
                type="button"
                onTouchStart={() => handleHistoryClick(term)}
                onMouseDown={() => handleHistoryClick(term)}
                className="w-full text-left px-3 py-2 text-sm text-gray-300 hover:bg-gray-700/50 active:bg-gray-700/70 transition-colors"
              >
                {term}
              </button>
            ))}
          </div>
        )}
      </div>

      <Link
        to="/favorites"
        className="flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 sm:py-2 rounded-lg bg-gray-900 border border-gray-700 text-gray-400 hover:text-rose-400 hover:border-rose-500/50 transition-colors relative"
      >
        <Heart className="w-4 h-4" />
        {favoritesCount > 0 && (
          <span className="text-xs font-medium text-rose-400">{favoritesCount}</span>
        )}
      </Link>
    </header>
  )
}
