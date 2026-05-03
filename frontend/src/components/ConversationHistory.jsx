import React, { useState } from 'react'
import { API_BASE } from '../api'

export default function ConversationHistory({ conversations, loading, onDelete }) {
  const [deletingId, setDeletingId] = useState(null)
  
  if (loading && conversations.length === 0) {
    return (
      <div className="loading-state" style={{ padding: '2rem', textAlign: 'center' }}>
        <div className="spinner" style={{ border: '4px solid rgba(0,0,0,0.1)', borderTop: '4px solid #10b981', borderRadius: '50%', width: '40px', height: '40px', animation: 'spin 1s linear infinite', margin: '0 auto 1rem' }}></div>
        <p style={{ color: '#6b7280', fontSize: '0.9rem' }}>Fetching history...</p>
      </div>
    )
  }

  if (conversations.length === 0) {
    return (
      <div className="empty-state" style={{ padding: '3rem 1.5rem', textAlign: 'center', background: 'white', borderRadius: '24px', border: '1px solid #f1f5f9' }}>
        <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📬</div>
        <p style={{ fontWeight: 800, color: '#1e293b', marginBottom: '0.5rem' }}>No conversations yet</p>
        <p style={{ color: '#64748b', fontSize: '0.85rem' }}>Ask your first farming question to see it here.</p>
      </div>
    )
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown date'
    try {
      const date = new Date(dateString)
      return date.toLocaleString('en-US', {
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
    if (!window.confirm('Are you sure you want to delete this conversation?')) return;
    setDeletingId(conversationId)
    try {
      const response = await fetch(`${API_BASE}/conversations/${conversationId}`, {
        method: 'DELETE'
      })
      if (!response.ok) throw new Error('Failed to delete');
      if (onDelete) onDelete();
    } catch (err) {
      console.error(err);
      alert('Failed to delete conversation.');
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="conversation-list" style={{ display: 'grid', gap: '1rem' }}>
      {conversations.map((conv) => (
        <div key={conv.id} className="conversation-card" style={{ background: 'white', borderRadius: '20px', padding: '1.25rem', border: '1px solid #e2e8f0', transition: 'all 0.2s' }}>
          <div className="conversation-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
            <div className="conversation-meta">
              <div style={{ fontSize: '0.75rem', fontWeight: 800, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Session #{conv.id.substring(0, 6)}</div>
              <div style={{ fontSize: '0.85rem', color: '#64748b', fontWeight: 500 }}>{formatDate(conv.created_at)}</div>
            </div>
            <button
              onClick={() => handleDelete(conv.id)}
              disabled={deletingId === conv.id}
              style={{ background: '#fee2e2', border: 'none', color: '#991b1b', width: '32px', height: '32px', borderRadius: '10px', cursor: 'pointer', display: 'grid', placeItems: 'center', transition: 'all 0.2s' }}
            >
              {deletingId === conv.id ? '⏳' : '🗑️'}
            </button>
          </div>

          <div style={{ display: 'grid', gap: '0.75rem' }}>
            {conv.transcript && (
              <div className="conversation-item">
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginBottom: '0.25rem' }}>
                  <span style={{ fontSize: '1rem' }}>👤</span>
                  <span style={{ fontSize: '0.7rem', fontWeight: 800, color: '#64748b', textTransform: 'uppercase' }}>Farmer</span>
                </div>
                <div style={{ fontSize: '0.95rem', color: '#1e293b', fontWeight: 500, paddingLeft: '1.75rem' }}>{conv.transcript}</div>
              </div>
            )}

            {conv.metadata && conv.metadata.reply_text && (
              <div className="conversation-item" style={{ background: '#f0fdf4', padding: '1rem', borderRadius: '14px', border: '1px solid #dcfce7' }}>
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginBottom: '0.5rem' }}>
                  <span style={{ fontSize: '1rem' }}>🤖</span>
                  <span style={{ fontSize: '0.7rem', fontWeight: 800, color: '#059669', textTransform: 'uppercase' }}>Krishi AI</span>
                </div>
                <div style={{ fontSize: '0.95rem', color: '#064e3b', lineHeight: 1.6, fontWeight: 500 }}>{conv.metadata.reply_text}</div>
              </div>
            )}
            
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '0.5rem' }}>
              {conv.metadata?.crop && <span style={{ background: '#dcfce7', color: '#166534', padding: '0.25rem 0.75rem', borderRadius: '99px', fontSize: '0.75rem', fontWeight: 700 }}>🌾 {conv.metadata.crop}</span>}
              {conv.metadata?.language && <span style={{ background: '#f1f5f9', color: '#475569', padding: '0.25rem 0.75rem', borderRadius: '99px', fontSize: '0.75rem', fontWeight: 700 }}>🌐 {conv.metadata.language === 'bn' ? 'Bengali' : 'English'}</span>}
              {conv.confidence && <span style={{ background: '#eff6ff', color: '#1e40af', padding: '0.25rem 0.75rem', borderRadius: '99px', fontSize: '0.75rem', fontWeight: 700 }}>🎯 {(conv.confidence * 100).toFixed(0)}% Match</span>}
            </div>

            {conv.media_url && (
              <div style={{ marginTop: '0.5rem' }}>
                <a href={conv.media_url} target="_blank" rel="noreferrer" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', color: '#3b82f6', fontSize: '0.85rem', fontWeight: 700, textDecoration: 'none' }}>
                  <span>🖼️</span> View Attached Image
                </a>
              </div>
            )}

            {conv.tts_path && (
              <div style={{ marginTop: '0.5rem' }}>
                <audio controls src={`${API_BASE}/get_tts?path=${encodeURIComponent(conv.tts_path)}`} style={{ width: '100%', height: '32px' }} />
              </div>
            )}
          </div>
        </div>
      ))}
      <style>{`
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .conversation-card:hover { transform: translateY(-3px); box-shadow: 0 10px 20px rgba(0,0,0,0.05); border-color: #10b981; }
      `}</style>
    </div>
  )
}
