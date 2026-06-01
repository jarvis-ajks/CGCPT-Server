import { Component, type ReactNode } from 'react'
import { AlertTriangle, RotateCcw } from 'lucide-react'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="text-center max-w-md">
            <AlertTriangle className="w-16 h-16 mx-auto mb-4 text-amber-400" />
            <h2 className="text-xl font-bold text-white mb-2">页面出现错误</h2>
            <p className="text-gray-400 mb-2">
              {this.state.error?.message || '发生了未知错误'}
            </p>
            <p className="text-gray-500 text-sm mb-6">
              请尝试刷新页面，如果问题持续存在请联系管理员。
            </p>
            <button
              onClick={this.handleReset}
              className="flex items-center gap-2 mx-auto px-5 py-2.5 bg-cyan-500 text-white rounded-lg font-medium hover:bg-cyan-400 transition-colors"
            >
              <RotateCcw className="w-4 h-4" />
              重试
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
