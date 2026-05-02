import React, { useState, useEffect } from 'react'
import Chatbot from './components/Chatbot'
import ConversationHistory from './components/ConversationHistory'
import MarketIntelligence from './components/MarketIntelligence'
import FarmDiary from './components/FarmDiary'
import DailyTips from './components/DailyTips'
import SoilHealth from './components/SoilHealth'
import WaterIrrigation from './components/WaterIrrigation'
import FinanceHub from './components/FinanceHub'
import CommunityQA from './components/CommunityQA'
import Marketplace from './components/Marketplace'
import EmergencySupport from './components/EmergencySupport'
import LandingPage from './components/LandingPage'
import { API_BASE } from './api'
import { useAgentSocket } from './hooks/useAgentSocket'
import { flushQueue } from './services/offlineQueue'
import './App.css'

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('krishi_auth_token'))
  const [activeTab, setActiveTab] = useState('chat')
  const [conversations, setConversations] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [isOffline, setIsOffline] = useState(!navigator.onLine)

  const wsUrl = (() => {
    if (API_BASE.startsWith('http')) {
      return API_BASE.replace('http', 'ws') + '/ws/agent_status'
    }
    // Handle relative paths (e.g., on Hugging Face Spaces)
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    // If API_BASE is '/api', this becomes 'wss://.../api/ws/agent_status'
    return `${protocol}//${host}${API_BASE}/ws/agent_status`
  })()

  const { status: agentStatus, isConnected } = useAgentSocket(wsUrl)

  const fetchConversations = async () => {
    try {
      setLoading(true)
      const response = await fetch(`${API_BASE}/conversations`)
      if (!response.ok) throw new Error('Failed to fetch conversations')
      const data = await response.json()
      setConversations(data)
      setError(null)
    } catch (err) {
      console.error('Error fetching conversations:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchConversations()
    const interval = setInterval(fetchConversations, 10000)

    const handleOnline = () => {
      setIsOffline(false)
      flushQueue()
      fetchConversations()
    }
    const handleOffline = () => setIsOffline(true)

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      clearInterval(interval)
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  const handleNewConversation = () => {
    setTimeout(fetchConversations, 2000)
  }

  const tabs = [
    { id: 'chat', label: 'AI Chat', icon: '💬' },
    { id: 'market', label: 'Market Intelligence', icon: '📈' },
    { id: 'diary', label: 'Farm Diary', icon: '📒' },
    { id: 'tips', label: 'Daily Tips', icon: '💡' },
    { id: 'soil', label: 'Soil Health', icon: '🌱' },
    { id: 'water', label: 'Irrigation', icon: '💧' },
    { id: 'finance', label: 'Finance Hub', icon: '💰' },
    { id: 'community', label: 'Community Q&A', icon: '👥' },
    { id: 'marketplace', label: 'Marketplace', icon: '🛒' },
    { id: 'emergency', label: 'Emergency', icon: '🚨' }
  ]

  const handleLogout = () => {
    localStorage.removeItem('krishi_auth_token')
    setIsAuthenticated(false)
  }

  if (!isAuthenticated) {
    return <LandingPage onAuthSuccess={() => setIsAuthenticated(true)} />
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-inner">
          <div className="brand-block">
            <div className="brand-mark">🌾</div>
            <div className="brand-text">
              <h1>KrishiBondhu</h1>
              <p className="subtitle">Your intelligent farming companion for crop care, finance, soil, irrigation, and markets.</p>
            </div>
          </div>

          <div className="header-status">
            <span className={`status-pill ${isConnected ? 'online' : 'offline'}`}>
              {isConnected ? `🟢 ${agentStatus || 'Agent ready'}` : '🔴 Reconnecting...'}
            </span>
            {isOffline && <span className="offline-banner">Offline mode enabled — actions will sync when you're back online.</span>}
            <button className="logout-btn" onClick={handleLogout}>Log out</button>
          </div>
        </div>

        <div className="hero-panel">
          <div className="hero-copy">
            <h2>Ask, analyze, and act with confidence from one farming dashboard.</h2>
            <p>Voice, camera, chat, market data, farm finance, soil health and irrigation advice—all designed for the modern farmer.</p>
            <div className="hero-actions">
              <button className={`hero-action ${activeTab === 'chat' ? 'active' : ''}`} onClick={() => setActiveTab('chat')}>Start Chat</button>
              <button className={`hero-action ${activeTab === 'market' ? 'active' : ''}`} onClick={() => setActiveTab('market')}>Check Markets</button>
            </div>
          </div>
          <div className="hero-stats">
            <div className="stat-card">
              <strong>12</strong>
              <span>Smart tools</span>
            </div>
            <div className="stat-card">
              <strong>Offline</strong>
              <span>Queue support</span>
            </div>
            <div className="stat-card">
              <strong>24/7</strong>
              <span>AI guidance</span>
            </div>
          </div>
        </div>
      </header>

      <main className="app-main">
        <div className="container">
          <div className="layout-grid">
            <aside className="side-panel">
              <div className="panel-card glassmorphism">
                <div className="panel-title">Toolset</div>
                <p className="panel-copy">One tap access to every KrishiBondhu capability.</p>
                <div className="tab-list">
                  {tabs.map(tab => (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
                    >
                      <span>{tab.icon}</span>
                      {tab.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="panel-card glassmorphism quick-guide">
                <h3>How to use</h3>
                <ul>
                  <li>📷 Capture crop images for instant diagnosis</li>
                  <li>💬 Chat in Bengali or English</li>
                  <li>📝 Save entries in the Farm Diary</li>
                  <li>📈 Compare market advice before selling</li>
                </ul>
              </div>
            </aside>

            <section className="content-area">
              <div className="content-card glassmorphism">


                {activeTab === 'chat' && (
                  <>
                    <h2>💬 AI Chat Assistant</h2>
                    <p className="section-description">Ask a farming question anytime — in Bengali or English.</p>
                    <Chatbot onMessageComplete={handleNewConversation} />
                  </>
                )}

                {activeTab === 'market' && (
                  <>
                    <h2>📈 Market Intelligence</h2>
                    <p className="section-description">Receive crop-specific pricing and selling strategy advice.</p>
                    <MarketIntelligence />
                  </>
                )}

                {activeTab === 'diary' && (
                  <>
                    <h2>📒 Farm Diary</h2>
                    <p className="section-description">Log expenses, income, and field notes in one place.</p>
                    <FarmDiary />
                  </>
                )}

                {activeTab === 'tips' && (
                  <>
                    <h2>💡 Daily Tips & Alerts</h2>
                    <p className="section-description">Get weather-aware pest alerts and daily crop care guidance.</p>
                    <DailyTips />
                  </>
                )}

                {activeTab === 'soil' && (
                  <>
                    <h2>🌱 Soil Health Advisor</h2>
                    <p className="section-description">Analyze soil needs and improve crop nutrition.</p>
                    <SoilHealth userId="user_123" />
                  </>
                )}

                {activeTab === 'water' && (
                  <>
                    <h2>💧 Irrigation Guidance</h2>
                    <p className="section-description">Get daily water-use recommendations based on local moisture data.</p>
                    <WaterIrrigation userId="user_123" />
                  </>
                )}

                {activeTab === 'finance' && (
                  <>
                    <h2>💰 Finance Hub</h2>
                    <p className="section-description">Explore credit, subsidies, and crop finance options.</p>
                    <FinanceHub userId="user_123" />
                  </>
                )}

                {activeTab === 'community' && (
                  <>
                    <h2>👥 Community Q&A</h2>
                    <p className="section-description">Ask questions, share knowledge, and consult local experts.</p>
                    <CommunityQA />
                  </>
                )}

                {activeTab === 'marketplace' && (
                  <>
                    <h2>🛒 Input Marketplace</h2>
                    <p className="section-description">Find authentic dealers and verify seeds or fertilizers.</p>
                    <Marketplace />
                  </>
                )}

                {activeTab === 'emergency' && (
                  <>
                    <h2>🚨 Emergency Response</h2>
                    <p className="section-description">Report crop damage for insurance or contact national helplines.</p>
                    <EmergencySupport />
                  </>
                )}
              </div>
            </section>

            <aside className="history-panel">
              <div className="panel-card glassmorphism history-card">
                <div className="history-header">
                  <div>
                    <h2>Conversation History</h2>
                    <p>Review and manage your recent interactions.</p>
                  </div>
                  <button className="refresh-btn" onClick={fetchConversations} disabled={loading}>
                    {loading ? 'Refreshing…' : 'Refresh'}
                  </button>
                </div>
                {error && <div className="error-message">{error}</div>}
                <ConversationHistory
                  conversations={conversations}
                  loading={loading}
                  onDelete={fetchConversations}
                />
              </div>
            </aside>
          </div>
        </div>
      </main>

      <footer className="app-footer">
        <p>KrishiBondhu — Intelligent agriculture for every farmer.</p>
      </footer>
    </div>
  )
}
