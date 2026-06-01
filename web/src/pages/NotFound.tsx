import { Link } from 'react-router-dom'
import { Atom, Home } from 'lucide-react'

export default function NotFound() {
  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="text-center">
        <div className="relative mb-8">
          <Atom className="w-24 h-24 mx-auto text-cyan-500/20 animate-spin" style={{ animationDuration: '8s' }} />
          <span className="absolute inset-0 flex items-center justify-center text-5xl font-bold text-cyan-400">
            404
          </span>
        </div>
        <h1 className="text-2xl font-bold text-white mb-2">页面未找到</h1>
        <p className="text-gray-400 mb-8 max-w-md mx-auto">
          您访问的页面不存在或已被移除。请检查URL是否正确，或返回首页浏览。
        </p>
        <div className="flex items-center justify-center gap-4">
          <Link
            to="/"
            className="flex items-center gap-2 px-5 py-2.5 bg-cyan-500 text-white rounded-lg font-medium hover:bg-cyan-400 transition-colors"
          >
            <Home className="w-4 h-4" />
            返回首页
          </Link>
          <Link
            to="/materials"
            className="flex items-center gap-2 px-5 py-2.5 bg-gray-800 border border-gray-700 text-gray-300 rounded-lg font-medium hover:border-cyan-500/50 transition-colors"
          >
            <Atom className="w-4 h-4" />
            浏览材料库
          </Link>
        </div>
      </div>
    </div>
  )
}
