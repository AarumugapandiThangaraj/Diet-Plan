import React from 'react'

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    // eslint-disable-next-line no-console
    console.error('App crashed:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      const message = this.state.error ? String(this.state.error?.message || this.state.error) : 'Unknown error'
      return (
        <div style={{ padding: 24, fontFamily: 'Segoe UI, Tahoma, Geneva, Verdana, sans-serif' }}>
          <h1 style={{ margin: 0, fontSize: 20 }}>Diet Plan Studio failed to load</h1>
          <p style={{ marginTop: 10, color: '#4d6288' }}>Open DevTools → Console for full details.</p>
          <pre style={{ marginTop: 12, padding: 12, background: '#fff', border: '1px solid rgba(15,23,42,0.12)', borderRadius: 12, whiteSpace: 'pre-wrap' }}>{message}</pre>
        </div>
      )
    }

    return this.props.children
  }
}
