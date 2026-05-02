import React, { useState, useRef, useEffect } from 'react'
import { API_BASE } from '../api'
import { saveToQueue } from '../services/offlineQueue'

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
  const [recording, setRecording] = useState(false)
  const [showCamera, setShowCamera] = useState(false)
  const [cameraStream, setCameraStream] = useState(null)
  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])
  const videoRef = useRef(null)
  const canvasRef = useRef(null)

  useEffect(() => {
    getCurrentLocation()
    // Initialize or retrieve user_id
    let storedUserId = localStorage.getItem('krishi_user_id')
    if (!storedUserId) {
      storedUserId = `farmer_${Date.now()}`
      localStorage.setItem('krishi_user_id', storedUserId)
    }
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
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
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


  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mr = new MediaRecorder(stream)
      mediaRecorderRef.current = mr
      chunksRef.current = []

      mr.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }

      mr.onstop = async () => {
        setProcessing(true)
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        
        setMessages(prev => [...prev, { role: 'user', content: '🎤 [Voice Message]', image: imagePreview }])
        
        const fd = new FormData()
        fd.append('file', blob, 'recording.webm')
        const userId = localStorage.getItem('krishi_user_id') || `farmer_${Date.now()}`
        fd.append('user_id', userId)
        if (gps.lat && gps.lon) {
          fd.append('lat', gps.lat)
          fd.append('lon', gps.lon)
        }
        if (selectedImage) {
          fd.append('image', selectedImage)
        }

        if (!navigator.onLine) {
          try {
            await saveToQueue(`${API_BASE}/upload_audio`, fd)
            setMessages(prev => [...prev, {
              role: 'assistant',
              content: 'You are currently offline. Your audio has been saved and will be answered when you reconnect.'
            }])
          } catch (err) {
            console.error('Failed to queue offline audio', err)
          } finally {
            setProcessing(false)
            setSelectedImage(null)
            setImagePreview(null)
            stream.getTracks().forEach(track => track.stop())
          }
          return
        }

        try {
          const resp = await fetch(`${API_BASE}/upload_audio`, {
            method: 'POST',
            body: fd
          })
          
          let data = await resp.json()
          
          if (!resp.ok && !data.reply_text) {
             throw new Error(data.error || 'Server error')
          }
          
          const assistantMessage = data.reply_text || 'I received your audio, but could not generate a response.'
          
          setMessages(prev => [...prev, {
            role: 'assistant',
            content: assistantMessage,
            metadata: {
              crop: data.crop,
              vision_result: data.vision_result,
              weather_forecast: data.weather_forecast,
              transcript: data.transcript
            }
          }])

          if (data.tts_path) {
            const ttsResp = await fetch(`${API_BASE}/get_tts?path=${encodeURIComponent(data.tts_path)}`)
            if (ttsResp.ok) {
              const ttsBlob = await ttsResp.blob()
              const audio = new Audio(URL.createObjectURL(ttsBlob))
              ttsAudioRef.current = audio
              setIsPlaying(true)
              setIsPaused(false)
              audio.onended = () => { setIsPlaying(false); setIsPaused(false) }
              audio.onerror = () => { setIsPlaying(false); setIsPaused(false) }
              audio.onpause = () => setIsPaused(true)
              audio.onplay = () => setIsPaused(false)
              audio.play().catch(err => {
                console.error('Audio play error:', err)
                setIsPlaying(false)
                setIsPaused(false)
              })
            }
          }

          if (onMessageComplete) onMessageComplete()

        } catch(err) {
            console.error(err)
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: `Sorry, I encountered an error. Please try again.`
            }])
        } finally {
            setProcessing(false)
            setSelectedImage(null)
            setImagePreview(null)
            stream.getTracks().forEach(track => track.stop())
        }
      }
      
      mr.start()
      setRecording(true)
    } catch (err) {
      alert('Could not access microphone.')
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop()
      setRecording(false)
    }
  }

  const startCamera = async () => {
    try {
      setShowCamera(true)
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' }
      })
      setCameraStream(mediaStream)
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream
      }
    } catch (err) {
      alert('Could not access camera.')
      setShowCamera(false)
    }
  }

  const stopCamera = () => {
    if (cameraStream) {
      cameraStream.getTracks().forEach(track => track.stop())
      setCameraStream(null)
    }
    setShowCamera(false)
  }

  const capturePhoto = () => {
    if (videoRef.current && canvasRef.current) {
      const video = videoRef.current
      const canvas = canvasRef.current
      const context = canvas.getContext('2d')
      canvas.width = video.videoWidth
      canvas.height = video.videoHeight
      context.drawImage(video, 0, 0)
      canvas.toBlob((blob) => {
        if (blob) {
          const file = new File([blob], "camera-capture.jpg", { type: "image/jpeg" })
          setSelectedImage(file)
          setImagePreview(URL.createObjectURL(blob))
          stopCamera()
        }
      }, 'image/jpeg', 0.9)
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
    const userId = localStorage.getItem('krishi_user_id') || `farmer_${Date.now()}`
    fd.append('user_id', userId)
    if (gps.lat && gps.lon) {
      fd.append('lat', gps.lat)
      fd.append('lon', gps.lon)
    }

    if (!navigator.onLine) {
      try {
        await saveToQueue(`${API_BASE}/chat`, fd)
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: 'You are currently offline. Your message has been saved and will be answered automatically when you reconnect.'
        }])
      } catch (err) {
        console.error('Failed to queue offline message', err)
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: 'Sorry, your device is offline and we failed to save the message locally. Please try again when online.'
        }])
      } finally {
        setProcessing(false)
        setSelectedImage(null)
        setImagePreview(null)
        if (fileInputRef.current) fileInputRef.current.value = ''
      }
      return
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
      if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop())
      }
    }
  }, [])

  return (
    <div className="chatbot" style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: '500px' }}>
      <div className="chat-messages" style={{ flex: 1, overflowY: 'auto', padding: '1rem', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`} style={{ alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start', maxWidth: '85%' }}>
            <div className="message-content" style={{ 
              background: msg.role === 'user' ? 'var(--primary)' : '#f1f5f9', 
              color: msg.role === 'user' ? 'white' : 'var(--text-main)',
              padding: '1.25rem 1.5rem',
              borderRadius: msg.role === 'user' ? '24px 24px 4px 24px' : '24px 24px 24px 4px',
              boxShadow: 'var(--shadow-sm)',
              position: 'relative'
            }}>
              {msg.image && (
                <img src={msg.image} alt="Uploaded" className="message-image" style={{ width: '100%', borderRadius: '12px', marginBottom: '0.75rem', display: 'block' }} />
              )}
              <p style={{ margin: 0, lineHeight: 1.6, fontSize: '1.05rem', fontWeight: 500 }}>{msg.content}</p>
              {msg.metadata && (
                <div className="message-metadata" style={{ marginTop: '1rem', display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                  {msg.metadata.crop && (
                    <span className="badge" style={{ background: 'rgba(255,255,255,0.2)', color: msg.role === 'user' ? 'white' : 'var(--primary)', padding: '0.2rem 0.6rem', borderRadius: '99px', fontSize: '0.75rem', fontWeight: 800 }}>🌾 {msg.metadata.crop}</span>
                  )}
                  {msg.metadata.vision_result?.disease && (
                    <span className="badge" style={{ background: 'rgba(255,255,255,0.2)', color: msg.role === 'user' ? 'white' : 'var(--primary)', padding: '0.2rem 0.6rem', borderRadius: '99px', fontSize: '0.75rem', fontWeight: 800 }}>🔍 {msg.metadata.vision_result.disease}</span>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
        {processing && (
          <div className="message assistant" style={{ alignSelf: 'flex-start' }}>
            <div className="message-content" style={{ background: '#f1f5f9', padding: '1rem 1.5rem', borderRadius: '24px 24px 24px 4px' }}>
              <div className="typing-indicator" style={{ display: 'flex', gap: '4px' }}>
                <span style={{ width: '8px', height: '8px', background: '#94a3b8', borderRadius: '50%', animation: 'pulse 1.5s infinite' }}></span>
                <span style={{ width: '8px', height: '8px', background: '#94a3b8', borderRadius: '50%', animation: 'pulse 1.5s infinite 0.2s' }}></span>
                <span style={{ width: '8px', height: '8px', background: '#94a3b8', borderRadius: '50%', animation: 'pulse 1.5s infinite 0.4s' }}></span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-area" style={{ borderTop: '1px solid #e2e8f0', padding: '1.5rem', background: '#f8fafc', borderRadius: '0 0 32px 32px' }}>
        {ttsAudioRef.current && (
          <div className="tts-control" style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '1rem', background: 'white', padding: '0.75rem 1rem', borderRadius: '12px', border: '1px solid #e2e8f0' }}>
            <button onClick={toggleTTS} style={{ background: 'var(--primary-soft)', border: 'none', color: 'var(--primary-dark)', padding: '0.5rem 1rem', borderRadius: '8px', fontWeight: 700 }}>
              {isPaused ? '▶️ Resume' : '⏸️ Pause'}
            </button>
            <button onClick={stopTTS} style={{ background: '#fee2e2', border: 'none', color: '#991b1b', padding: '0.5rem 1rem', borderRadius: '8px', fontWeight: 700 }}>⏹ Stop</button>
            <span style={{ fontSize: '0.85rem', color: '#64748b', fontWeight: 600 }}>🔊 Voice response playing...</span>
          </div>
        )}

        {imagePreview && (
          <div className="image-preview-small" style={{ marginBottom: '1rem', position: 'relative', display: 'inline-block' }}>
            <img src={imagePreview} alt="Preview" style={{ width: '80px', height: '80px', borderRadius: '12px', objectFit: 'cover', border: '2px solid var(--primary)' }} />
            <button onClick={removeImage} style={{ position: 'absolute', top: '-8px', right: '-8px', background: 'var(--danger)', color: 'white', border: 'none', borderRadius: '50%', width: '24px', height: '24px', cursor: 'pointer' }}>✕</button>
          </div>
        )}

        {showCamera && (
          <div className="camera-inline-container" style={{ marginBottom: '1rem', background: 'black', borderRadius: '20px', overflow: 'hidden', position: 'relative' }}>
            <video ref={videoRef} autoPlay playsInline style={{ width: '100%', display: 'block' }} />
            <div style={{ position: 'absolute', bottom: '1rem', left: '0', right: '0', display: 'flex', justifyContent: 'center', gap: '1rem' }}>
              <button onClick={capturePhoto} style={{ background: 'white', color: 'black', padding: '0.75rem 1.5rem', borderRadius: '99px', fontWeight: 700, border: 'none' }}>📸 Take Photo</button>
              <button onClick={stopCamera} style={{ background: 'rgba(255,255,255,0.2)', color: 'white', padding: '0.75rem 1.5rem', borderRadius: '99px', fontWeight: 700, border: 'none', backdropFilter: 'blur(10px)' }}>Cancel</button>
            </div>
            <canvas ref={canvasRef} style={{ display: 'none' }} />
          </div>
        )}

        <div className="chat-input-container" style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-end' }}>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button onClick={startCamera} style={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: '12px', width: '44px', height: '44px', display: 'grid', placeItems: 'center', fontSize: '1.2rem' }} title="Camera">📸</button>
            <button onClick={() => fileInputRef.current?.click()} style={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: '12px', width: '44px', height: '44px', display: 'grid', placeItems: 'center', fontSize: '1.2rem' }} title="Attach">📎</button>
          </div>
          
          <input ref={fileInputRef} type="file" accept="image/*" onChange={handleImageSelect} style={{ display: 'none' }} />
          
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your question..."
            style={{ flex: 1, padding: '0.85rem 1.25rem', borderRadius: '16px', border: '1px solid #e2e8f0', resize: 'none', fontSize: '1rem', outline: 'none', background: 'white' }}
            disabled={processing || recording}
            rows="1"
          />

          {recording ? (
            <button onClick={stopRecording} style={{ background: '#ef4444', color: 'white', border: 'none', borderRadius: '12px', width: '44px', height: '44px', display: 'grid', placeItems: 'center', animation: 'pulse 1.5s infinite' }}>⏹</button>
          ) : (
            <button onClick={startRecording} disabled={processing || input.trim()} style={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: '12px', width: '44px', height: '44px', display: 'grid', placeItems: 'center', fontSize: '1.2rem' }}>🎤</button>
          )}

          <button onClick={handleSend} disabled={processing || recording || (!input.trim() && !selectedImage)} style={{ background: 'var(--primary)', color: 'white', border: 'none', borderRadius: '12px', width: '44px', height: '44px', display: 'grid', placeItems: 'center', fontSize: '1.2rem', boxShadow: '0 4px 10px rgba(16, 185, 129, 0.2)' }}>
            {processing ? '⏳' : '➤'}
          </button>
        </div>
      </div>
    </div>
  )
}
