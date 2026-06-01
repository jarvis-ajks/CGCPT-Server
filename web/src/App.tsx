import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { lazy, Suspense } from 'react'
import Layout from './components/Layout'
import ErrorBoundary from './components/ErrorBoundary'

const Dashboard = lazy(() => import('./pages/Dashboard'))
const MaterialsBrowser = lazy(() => import('./pages/MaterialsBrowser'))
const MaterialDetail = lazy(() => import('./pages/MaterialDetail'))
const PrototypesBrowser = lazy(() => import('./pages/PrototypesBrowser'))
const PrototypeDetail = lazy(() => import('./pages/PrototypeDetail'))
const StructureGenerator = lazy(() => import('./pages/StructureGenerator'))
const MaterialsCompare = lazy(() => import('./pages/MaterialsCompare'))
const ClassificationBrowser = lazy(() => import('./pages/ClassificationBrowser'))
const SearchResults = lazy(() => import('./pages/SearchResults'))
const TopologyVerify = lazy(() => import('./pages/TopologyVerify'))
const Favorites = lazy(() => import('./pages/Favorites'))
const RecentBrowse = lazy(() => import('./pages/RecentBrowse'))
const AdvancedSearch = lazy(() => import('./pages/AdvancedSearch'))
const StackingRecognizer = lazy(() => import('./pages/StackingRecognizer'))
const DataImport = lazy(() => import('./pages/DataImport'))
const AlgorithmManager = lazy(() => import('./pages/AlgorithmManager'))
const NotFound = lazy(() => import('./pages/NotFound'))

const _preloadMap: Record<string, () => Promise<unknown>> = {
  '/materials': () => import('./pages/MaterialsBrowser'),
  '/prototypes': () => import('./pages/PrototypesBrowser'),
  '/generate': () => import('./pages/StructureGenerator'),
  '/stacking': () => import('./pages/StackingRecognizer'),
  '/classify': () => import('./pages/ClassificationBrowser'),
  '/compare': () => import('./pages/MaterialsCompare'),
  '/advanced-search': () => import('./pages/AdvancedSearch'),
  '/import': () => import('./pages/DataImport'),
  '/algorithms': () => import('./pages/AlgorithmManager'),
}

export function preloadRoute(path: string) {
  const loader = _preloadMap[path]
  if (loader) loader()
}

function PageLoader() {
  return (
    <div className="flex items-center justify-center h-96">
      <div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter basename="/CGCPT">
      <ErrorBoundary>
        <Suspense fallback={<PageLoader />}>
          <Routes>
            <Route element={<Layout />}>
              <Route path="/" element={<Dashboard />} />
              <Route path="/materials" element={<MaterialsBrowser />} />
              <Route path="/materials/:id" element={<MaterialDetail />} />
              <Route path="/prototypes" element={<PrototypesBrowser />} />
              <Route path="/prototypes/:id" element={<PrototypeDetail />} />
              <Route path="/generate" element={<StructureGenerator />} />
              <Route path="/compare" element={<MaterialsCompare />} />
              <Route path="/classify" element={<ClassificationBrowser />} />
              <Route path="/search" element={<SearchResults />} />
              <Route path="/verify" element={<TopologyVerify />} />
              <Route path="/favorites" element={<Favorites />} />
              <Route path="/recent" element={<RecentBrowse />} />
              <Route path="/advanced-search" element={<AdvancedSearch />} />
              <Route path="/stacking" element={<StackingRecognizer />} />
              <Route path="/import" element={<DataImport />} />
              <Route path="/algorithms" element={<AlgorithmManager />} />
              <Route path="*" element={<NotFound />} />
            </Route>
          </Routes>
        </Suspense>
      </ErrorBoundary>
    </BrowserRouter>
  )
}
