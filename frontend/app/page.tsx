'use client'

import { useState, useEffect } from 'react'

export default function Home() {
  const [backendStatus, setBackendStatus] = useState<any>(null)
  const [query, setQuery] = useState('')
  const [response, setResponse] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    // Check backend health
    fetch('http://localhost:4000/health')
      .then(res => res.json())
      .then(data => setBackendStatus(data))
      .catch(err => console.error('Backend not reachable:', err))
  }, [])

  const handleQuery = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    
    try {
      const res = await fetch('http://localhost:4000/ai', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
      })
      const data = await res.json()
      setResponse(data.response)
    } catch (err) {
      setResponse('Error connecting to backend')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold mb-4">
            <span className="text-zcash-gold">ZULU</span>
            <span className="text-cyber-purple">.cash</span>
          </h1>
          <p className="text-gray-400 text-lg">
            Private AI Agent for Zcash Commerce
          </p>
          
          {/* Backend Status */}
          <div className="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-gray-800 rounded-full">
            <div className={`w-2 h-2 rounded-full ${backendStatus ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="text-sm">
              {backendStatus ? `Backend ${backendStatus.version} Connected` : 'Backend Offline'}
            </span>
          </div>
        </div>

        {/* AI Chat Interface */}
        <div className="bg-gray-900 rounded-2xl p-8 border border-gray-800">
          <h2 className="text-2xl font-bold mb-6 text-zcash-gold">
            🤖 Ask ZULU Anything
          </h2>
          
          <form onSubmit={handleQuery} className="space-y-4">
            <div>
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="How much did I spend this month?"
                className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:outline-none focus:border-zcash-gold text-white placeholder-gray-500"
                disabled={!backendStatus}
              />
            </div>
            
            <button
              type="submit"
              disabled={loading || !backendStatus || !query}
              className="w-full py-3 bg-gradient-to-r from-zcash-gold to-cyber-purple text-black font-bold rounded-lg hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
            >
              {loading ? 'Thinking...' : 'Ask ZULU'}
            </button>
          </form>

          {/* Response */}
          {response && (
            <div className="mt-6 p-4 bg-gray-800 rounded-lg border border-gray-700">
              <p className="text-gray-300">{response}</p>
            </div>
          )}
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8">
          <div className="bg-gray-900 p-6 rounded-xl border border-gray-800">
            <div className="text-3xl mb-2">🛡️</div>
            <h3 className="font-bold mb-2">Private AI</h3>
            <p className="text-sm text-gray-400">All processing happens locally on your device</p>
          </div>
          
          <div className="bg-gray-900 p-6 rounded-xl border border-gray-800">
            <div className="text-3xl mb-2">💰</div>
            <h3 className="font-bold mb-2">Shielded TX</h3>
            <p className="text-sm text-gray-400">Zcash z-address privacy by default</p>
          </div>
          
          <div className="bg-gray-900 p-6 rounded-xl border border-gray-800">
            <div className="text-3xl mb-2">🔁</div>
            <h3 className="font-bold mb-2">ZEC → USDC</h3>
            <p className="text-sm text-gray-400">Instant merchant settlement via NEAR</p>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-12 text-center text-gray-500 text-sm">
          <p>Built for Zypherpunk Hackathon • Open Source • MIT License</p>
          <p className="mt-2">
            <a href="https://github.com/edgeconsultinglabs/zulu.cash" target="_blank" className="text-cyber-purple hover:underline">
              GitHub
            </a>
            {' • '}
            <a href="https://zulu.cash" target="_blank" className="text-zcash-gold hover:underline">
              Website
            </a>
          </p>
        </div>
      </div>
    </main>
  )
}
