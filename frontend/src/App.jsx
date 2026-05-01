import React, { useState, useEffect } from 'react'
import Recorder from './components/Recorder'
import CameraCapture from './components/CameraCapture'
import Chatbot from './components/Chatbot'
import ConversationHistory from './components/ConversationHistory'
import { API_BASE } from './api'
import { useAgentSocket } from './hooks/useAgentSocket'
import { flushQueue } from './services/offlineQueue'
import './App.css'

export default function App() {
  const [activeTab, setActiveTab] = useState('voice') // voice, image, camera, chat
  const [conversations, setConversations] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [isOffline, setIsOffline] = useState(!navigator.onLine)

  // Use the WebSocket hook (assuming backend runs on localhost:8000/api/ws/agent_status or dynamically based on API_BASE)
  const wsUrl = API_BASE.replace('http', 'ws') + '/ws/agent_status'
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
    // Refresh conversations every 10 seconds
    const interval = setInterval(fetchConversations, 10000)
    
    // Offline status listeners
    const handleOnline = () => {
      setIsOffline(false)
      flushQueue() // Flush IndexedDB when back online
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
    // Refresh conversations after a new one is created
    setTimeout(fetchConversations, 2000)
  }

  const tabs = [
    { id: 'voice', label: '🎤 Voice', icon: '🎤' },
    { id: 'camera', label: '📹 Camera', icon: '📹' },
    { id: 'chat', label: '💬 Chat', icon: '💬' }
  ]

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <h1>🌾 KrishiBondhu</h1>
          <p className="subtitle">Your intelligent farming assistant - Ask questions, share images, or chat anytime!</p>
          
          {/* Agent Status Indicator */}
          <div className="status-indicators">
             <span className={`ws-status ${isConnected ? 'connected' : 'disconnected'}`}>
               {isConnected ? `🟢 Connected: ${agentStatus}` : '🔴 Reconnecting...'}
             </span>
             {isOffline && <span className="offline-banner">⚠️ Offline Mode. Data will sync when connected.</span>}
          </div>
        </div>
      </header>

      <main className="app-main">
        <div className="container">
          {/* Tab Navigation */}
          <div className="tabs-container">
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
              >
                <span className="tab-icon">{tab.icon}</span>
                <span className="tab-label">{tab.label}</span>
              </button>
            ))}
          </div>

          <div className="main-content">
            {/* Main Content Area */}
            <section className="content-section">
              <div className="card">
                {activeTab === 'voice' && (
                  <>
                    <h2>🎤 Voice Assistant</h2>
                    <p className="section-description">
                      Record your voice question in Bengali or English. Ask about crop diseases,
                      farming advice, or weather conditions.
                    </p>
                    <Recorder onConversationComplete={handleNewConversation} />
                  </>
                )}

                {/* Image tab removed to avoid duplicate upload option while using chat */}

                {activeTab === 'camera' && (
                  <>
                    <h2>📹 Live Camera</h2>
                    <p className="section-description">
                      Use your device camera to capture and analyze crop problems in real-time.
                      Perfect for on-field diagnosis.
                    </p>
                    <CameraCapture onCaptureComplete={handleNewConversation} />
                  </>
                )}

                {activeTab === 'chat' && (
                  <>
                    <h2>💬 Chat Assistant</h2>
                    <p className="section-description">
                      Chat with our AI assistant anytime. Ask questions, get advice, or attach
                      images for analysis. Available 24/7!
                    </p>
                    <Chatbot onMessageComplete={handleNewConversation} />
                  </>
                )}
              </div>
            </section>

            {/* Conversation History Sidebar */}
            <section className="history-section">
              <div className="card">
                <div className="section-header">
                  <h2>📋 History</h2>
                  <button
                    onClick={fetchConversations}
                    className="refresh-btn"
                    disabled={loading}
                    title="Refresh conversations"
                  >
                    {loading ? '🔄' : '↻'}
                  </button>
                </div>
                {error && (
                  <div className="error-message">
                    ⚠️ {error}
                  </div>
                )}
                <ConversationHistory
                  conversations={conversations}
                  loading={loading}
                  onDelete={fetchConversations}
                />
              </div>
            </section>
          </div>
        </div>
      </main>

      <footer className="app-footer">
        <p>KrishiBondhu - Empowering farmers with AI technology 🌾🤖</p>
      </footer>
    </div>
  )
}