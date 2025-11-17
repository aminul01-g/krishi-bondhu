import React, { useState, useRef, useEffect } from 'react'

const API_BASE = 'http://localhost:8000/api'

export default function Chatbot({ onMessageComplete }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: 'Hello! I\'m your farming assistant. Ask me anything about crops, diseases, farming techniques, or upload an image for analysis. I can help in both Bengali and English! 🌾'
    }
  ])
  const [input, setInput] = useState('')
  const [processing, setProcessing] = useState(false)
  const [gps, setGps] = useState({ lat: null, lon: null })
  const [gpsStatus, setGpsStatus] = useState('idle')
  const [selectedImage, setSelectedImage] = useState(null)
  const [imagePreview, setImagePreview] = useState(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [isPaused, setIsPaused] = useState(false)
  const ttsAudioRef = useRef(null)
  const messagesEndRef = useRef(null)
  const fileInputRef = useRef(null)

  useEffect(() => {
    getCurrentLocation()
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const getCurrentLocation = () => {
    if (!navigator.geolocation) {
      setGpsStatus('error')
      setGps({ lat: 23.7, lon: 90.4 })
      return
    }

    setGpsStatus('getting')
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setGps({
          lat: position.coords.latitude,
          lon: position.coords.longitude
        })
        setGpsStatus('success')
      },
      (err) => {
        console.error('GPS error:', err)
        setGpsStatus('error')
        setGps({ lat: 23.7, lon: 90.4 })
      }
    )
  }

  const handleImageSelect = (e) => {
    const file = e.target.files[0]
    if (file) {
      if (!file.type.startsWith('image/')) {
        alert('Please select an image file')
        return
      }
      setSelectedImage(file)
      const reader = new FileReader()
      reader.onloadend = () => {
        setImagePreview(reader.result)
      }
      reader.readAsDataURL(file)
    }
  }

  const handleSend = async () => {
    if (!input.trim() && !selectedImage) {
      return
    }

    const userMessage = input.trim() || (selectedImage ? 'Please analyze this image' : '')
    setMessages(prev => [...prev, { role: 'user', content: userMessage, image: imagePreview }])
    setInput('')
    setProcessing(true)

    const fd = new FormData()
    if (selectedImage) {
      fd.append('image', selectedImage)
    }
    fd.append('message', userMessage)
    fd.append('user_id', `farmer_${Date.now()}`)
    if (gps.lat && gps.lon) {
      fd.append('lat', gps.lat)
      fd.append('lon', gps.lon)
    }

    try {
      const resp = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        body: fd
      })

      let data
      try {
        data = await resp.json()
      } catch (jsonError) {
        throw new Error(`Server returned invalid response. Status: ${resp.status}`)
      }

      // Even if status is not OK, check if we have a reply_text
      if (!resp.ok) {
        // If we have a reply_text in error response, use it
        if (data.reply_text) {
          setMessages(prev => [...prev, { 
            role: 'assistant', 
            content: data.reply_text,
            metadata: data.metadata || {}
          }])
          setProcessing(false)
          return
        }
        throw new Error(data.error || `HTTP ${resp.status}: ${data.reply_text || 'Server error'}`)
      }
      
      // Check if there's an error in the response
      if (data.error && !data.reply_text) {
        throw new Error(data.error)
      }
      
      const assistantMessage = data.reply_text || 'I received your message, but could not generate a response.'

      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: assistantMessage,
        metadata: {
          crop: data.crop,
          vision_result: data.vision_result,
          weather_forecast: data.weather_forecast
        }
      }])

      // Play TTS if available
      if (data.tts_path) {
        const ttsResp = await fetch(
          `${API_BASE}/get_tts?path=${encodeURIComponent(data.tts_path)}`
        )
        if (ttsResp.ok) {
          const ttsBlob = await ttsResp.blob()
          const ttsUrl = URL.createObjectURL(ttsBlob)
          const audio = new Audio(ttsUrl)
          ttsAudioRef.current = audio
          setIsPlaying(true)
          setIsPaused(false)
          audio.onended = () => {
            setIsPlaying(false)
            setIsPaused(false)
          }
          audio.onerror = () => {
            setIsPlaying(false)
            setIsPaused(false)
          }
          audio.onpause = () => setIsPaused(true)
          audio.onplay = () => setIsPaused(false)
          audio.play().catch(err => {
            console.error('Audio play error:', err)
            setIsPlaying(false)
            setIsPaused(false)
          })
        }
      }

      // Clear image
      setSelectedImage(null)
      setImagePreview(null)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }

      if (onMessageComplete) {
        onMessageComplete()
      }
    } catch (err) {
      console.error('Chat error:', err)
      let errorMessage = 'An unknown error occurred. Please try again.'
      
      if (err.message) {
        errorMessage = err.message
        // Check for network errors
        if (err.message.includes('Failed to fetch') || err.message.includes('NetworkError')) {
          errorMessage = 'Unable to connect to the server. Please check your internet connection and ensure the backend is running.'
        }
      }
      
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Sorry, I encountered an error: ${errorMessage}. Please try again in a moment.`
      }])
    } finally {
      setProcessing(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const removeImage = () => {
    setSelectedImage(null)
    setImagePreview(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const toggleTTS = () => {
    if (ttsAudioRef.current) {
      if (isPaused || !isPlaying) {
        // Play or resume
        ttsAudioRef.current.play().catch(err => {
          console.error('Audio play error:', err)
          setIsPlaying(false)
          setIsPaused(false)
        })
        setIsPlaying(true)
        setIsPaused(false)
      } else {
        // Pause
        ttsAudioRef.current.pause()
        setIsPaused(true)
      }
    }
  }

  const stopTTS = () => {
    if (ttsAudioRef.current) {
      ttsAudioRef.current.pause()
      ttsAudioRef.current.currentTime = 0
      ttsAudioRef.current = null
      setIsPlaying(false)
      setIsPaused(false)
    }
  }

  useEffect(() => {
    return () => {
      if (ttsAudioRef.current) {
        ttsAudioRef.current.pause()
        ttsAudioRef.current = null
      }
    }
  }, [])

  return (
    <div className="chatbot">
      <div className="chat-messages">
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            <div className="message-content">
              {msg.image && (
                <img src={msg.image} alt="Uploaded" className="message-image" />
              )}
              <p>{msg.content}</p>
              {msg.metadata && (
                <div className="message-metadata">
                  {msg.metadata.crop && (
                    <span className="badge">🌾 {msg.metadata.crop}</span>
                  )}
                  {msg.metadata.vision_result?.disease && (
                    <span className="badge">
                      🔍 {msg.metadata.vision_result.disease}
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
        {processing && (
          <div className="message assistant">
            <div className="message-content">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-area">
        {/* TTS Control */}
        {ttsAudioRef.current && (
          <div className="tts-control">
            <button onClick={toggleTTS} className="play-pause-tts-btn">
              {isPaused ? '▶️' : '⏸️'}
            </button>
            <button onClick={stopTTS} className="stop-tts-btn" title="Stop and reset">
              ⏹
            </button>
            <span className="tts-status">
              {isPaused ? '⏸️ Paused' : '🔊 Playing response...'}
            </span>
          </div>
        )}
        {imagePreview && (
          <div className="image-preview-small">
            <img src={imagePreview} alt="Preview" />
            <button onClick={removeImage} className="remove-image-btn">✕</button>
          </div>
        )}
        <div className="chat-input-container">
          <button
            onClick={() => fileInputRef.current?.click()}
            className="attach-image-btn"
            title="Attach image"
          >
            📷
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleImageSelect}
            style={{ display: 'none' }}
          />
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your question here... (Bengali or English)"
            rows="1"
            className="chat-input"
            disabled={processing}
          />
          <button
            onClick={handleSend}
            disabled={processing || (!input.trim() && !selectedImage)}
            className="send-btn"
          >
            {processing ? '⏳' : '➤'}
          </button>
        </div>
        <div className="chat-hint">
          💡 Tip: You can attach images or ask questions in Bengali or English
        </div>
      </div>
    </div>
  )
}

