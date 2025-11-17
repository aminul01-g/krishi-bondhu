import React, { useState } from 'react'

const API_BASE = 'http://localhost:8000/api'

export default function ConversationHistory({ conversations, loading, onDelete }) {
  const [deletingId, setDeletingId] = useState(null)
  if (loading) {
    return (
      <div className="loading-state">
        <div className="spinner"></div>
        <p>Loading conversations...</p>
      </div>
    )
  }

  if (conversations.length === 0) {
    return (
      <div className="empty-state">
        <p>📭 No conversations yet.</p>
        <p className="empty-hint">Start by recording your first question!</p>
      </div>
    )
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown date'
    try {
      const date = new Date(dateString)
      return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
    } catch {
      return dateString
    }
  }

  const handleDelete = async (conversationId) => {
    if (!window.confirm('Are you sure you want to delete this conversation?')) {
      return
    }

    setDeletingId(conversationId)
    try {
      const response = await fetch(`${API_BASE}/conversations/${conversationId}`, {
        method: 'DELETE'
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to delete conversation')
      }

      // Notify parent to refresh conversations
      if (onDelete) {
        onDelete()
      }
    } catch (err) {
      console.error('Error deleting conversation:', err)
      alert(`Failed to delete conversation: ${err.message}`)
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="conversation-list">
      {conversations.map((conv) => (
        <div key={conv.id} className="conversation-card">
          <div className="conversation-header">
            <div className="conversation-meta">
              <span className="conversation-id">#{conv.id}</span>
              <span className="conversation-date">{formatDate(conv.created_at)}</span>
            </div>
            <div className="conversation-actions">
              {conv.confidence !== null && (
                <span className="confidence-badge">
                  {(conv.confidence * 100).toFixed(0)}% confidence
                </span>
              )}
              <button
                onClick={() => handleDelete(conv.id)}
                disabled={deletingId === conv.id}
                className="delete-btn"
                title="Delete conversation"
              >
                {deletingId === conv.id ? '⏳' : '🗑️'}
              </button>
            </div>
          </div>

          {conv.transcript && (
            <div className="conversation-item">
              <div className="item-label">👤 Your Question:</div>
              <div className="item-content">{conv.transcript}</div>
            </div>
          )}

          {conv.metadata && (
            <>
              {conv.metadata.crop && (
                <div className="conversation-item">
                  <div className="item-label">🌾 Crop:</div>
                  <div className="item-content">
                    <span className="badge">{conv.metadata.crop}</span>
                  </div>
                </div>
              )}

              {conv.metadata.language && (
                <div className="conversation-item">
                  <div className="item-label">🌐 Language:</div>
                  <div className="item-content">
                    <span className="badge">
                      {conv.metadata.language === 'bn' ? 'Bengali' : 'English'}
                    </span>
                  </div>
                </div>
              )}

              {conv.metadata.vision_result && conv.metadata.vision_result.disease && (
                <div className="conversation-item">
                  <div className="item-label">🔍 Vision Analysis:</div>
                  <div className="item-content">
                    {conv.metadata.vision_result.disease}
                    {conv.metadata.vision_result.confidence && (
                      <span className="confidence">
                        ({(conv.metadata.vision_result.confidence * 100).toFixed(1)}%)
                      </span>
                    )}
                  </div>
                </div>
              )}

              {conv.metadata.weather_forecast && (
                <div className="conversation-item">
                  <div className="item-label">🌤️ Weather:</div>
                  <div className="item-content">
                    {conv.metadata.weather_forecast.hourly?.temperature_2m?.[0] && (
                      <span>Temperature: {conv.metadata.weather_forecast.hourly.temperature_2m[0]}°C</span>
                    )}
                  </div>
                </div>
              )}

              {conv.metadata.gps && conv.metadata.gps.lat && (
                <div className="conversation-item">
                  <div className="item-label">📍 Location:</div>
                  <div className="item-content">
                    {conv.metadata.gps.lat.toFixed(4)}, {conv.metadata.gps.lon.toFixed(4)}
                  </div>
                </div>
              )}
            </>
          )}

          {conv.media_url && (
            <div className="conversation-item">
              <div className="item-label">🖼️ Image:</div>
              <div className="item-content">
                <a 
                  href={conv.media_url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="media-link"
                >
                  View Image
                </a>
              </div>
            </div>
          )}

          {conv.tts_path && (
            <div className="conversation-item">
              <div className="item-label">🔊 Audio Response:</div>
              <div className="item-content">
                <audio 
                  controls 
                  src={`http://localhost:8000/api/get_tts?path=${encodeURIComponent(conv.tts_path)}`}
                  className="audio-player"
                />
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

