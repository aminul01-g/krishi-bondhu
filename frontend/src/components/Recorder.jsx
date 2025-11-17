import React, { useState, useRef, useEffect } from 'react'

const API_BASE = 'http://localhost:8000/api'

export default function Recorder({ onConversationComplete }) {
  const [recording, setRecording] = useState(false)
  const [processing, setProcessing] = useState(false)
  const [audioUrl, setAudioUrl] = useState(null)
  const [selectedImage, setSelectedImage] = useState(null)
  const [imagePreview, setImagePreview] = useState(null)
  const [gps, setGps] = useState({ lat: null, lon: null })
  const [gpsStatus, setGpsStatus] = useState('idle') // idle, getting, success, error
  const [response, setResponse] = useState(null)
  const [error, setError] = useState(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [isPaused, setIsPaused] = useState(false)
  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])
  const audioRef = useRef(null)
  const ttsAudioRef = useRef(null) // Separate ref for TTS audio
  const imageInputRef = useRef(null)

  // Get GPS location on component mount
  useEffect(() => {
    getCurrentLocation()
  }, [])

  const getCurrentLocation = () => {
    if (!navigator.geolocation) {
      setGpsStatus('error')
      setGps({ lat: 23.7, lon: 90.4 }) // Default to Dhaka, Bangladesh
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
        // Default to Dhaka, Bangladesh if GPS fails
        setGps({ lat: 23.7, lon: 90.4 })
      }
    )
  }

  const start = async () => {
    try {
      setError(null)
      setResponse(null)
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
        const url = URL.createObjectURL(blob)
        setAudioUrl(url)

        // Upload to backend
        const fd = new FormData()
        fd.append('file', blob, 'recording.webm')
        fd.append('user_id', `farmer_${Date.now()}`)
        if (gps.lat && gps.lon) {
          fd.append('lat', gps.lat)
          fd.append('lon', gps.lon)
        }
        // Add image if selected
        if (selectedImage) {
          fd.append('image', selectedImage)
        }

        try {
          const resp = await fetch(`${API_BASE}/upload_audio`, {
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
            if (data.reply_text) {
              setResponse(data)
              // Continue to play TTS if available
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
              if (onConversationComplete) {
                onConversationComplete()
              }
              setProcessing(false)
              return
            }
            throw new Error(data.error || `HTTP ${resp.status}: ${data.reply_text || 'Server error'}`)
          }
          
          // Check if there's an error in the response (but still show reply_text if available)
          if (data.error && !data.reply_text) {
            throw new Error(data.error)
          }
          
          setResponse(data)

          // Play TTS response if available
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

          // Notify parent component
          if (onConversationComplete) {
            onConversationComplete()
          }
          
          // Clear image after successful upload
          setSelectedImage(null)
          setImagePreview(null)
          if (imageInputRef.current) {
            imageInputRef.current.value = ''
          }
        } catch (err) {
          console.error('Upload error:', err)
          let errorMsg = err.message || 'Failed to process audio'
          if (errorMsg.includes('Failed to fetch') || errorMsg.includes('NetworkError')) {
            errorMsg = 'Unable to connect to the server. Please check your internet connection and ensure the backend is running.'
          }
          setError(errorMsg)
        } finally {
          setProcessing(false)
        }

        // Stop all tracks
        stream.getTracks().forEach(track => track.stop())
      }

      mr.start()
      setRecording(true)
    } catch (err) {
      console.error('Mic access error:', err)
      setError('Could not access microphone. Please check permissions.')
      alert('Could not access microphone. Please check permissions.')
    }
  }

  const handleImageSelect = (e) => {
    const file = e.target.files[0]
    if (file) {
      if (!file.type.startsWith('image/')) {
        setError('Please select an image file')
        return
      }
      setSelectedImage(file)
      setError(null)
      const reader = new FileReader()
      reader.onloadend = () => {
        setImagePreview(reader.result)
      }
      reader.readAsDataURL(file)
    }
  }

  const removeImage = () => {
    setSelectedImage(null)
    setImagePreview(null)
    if (imageInputRef.current) {
      imageInputRef.current.value = ''
    }
  }

  const stop = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop()
      setRecording(false)
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

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (ttsAudioRef.current) {
        ttsAudioRef.current.pause()
        ttsAudioRef.current = null
      }
    }
  }, [])

  const getGpsIcon = () => {
    switch (gpsStatus) {
      case 'getting': return '🔄'
      case 'success': return '✅'
      case 'error': return '⚠️'
      default: return '📍'
    }
  }

  return (
    <div className="recorder">
      {/* GPS Status */}
      <div className="gps-status">
        <span className="gps-icon">{getGpsIcon()}</span>
        <span className="gps-text">
          {gpsStatus === 'getting' && 'Getting location...'}
          {gpsStatus === 'success' && `Location: ${gps.lat?.toFixed(4)}, ${gps.lon?.toFixed(4)}`}
          {gpsStatus === 'error' && 'Using default location (Dhaka, BD)'}
          {gpsStatus === 'idle' && 'Location ready'}
        </span>
        {gpsStatus === 'error' && (
          <button onClick={getCurrentLocation} className="retry-gps-btn">
            Retry
          </button>
        )}
      </div>

      {/* Image Upload Option */}
      <div className="image-upload-option">
        <label className="image-upload-label">
          <input
            ref={imageInputRef}
            type="file"
            accept="image/*"
            onChange={handleImageSelect}
            style={{ display: 'none' }}
          />
          <span className="image-upload-btn">📷 Add Image (Optional)</span>
        </label>
        {imagePreview && (
          <div className="image-preview-small">
            <img src={imagePreview} alt="Preview" />
            <button onClick={removeImage} className="remove-image-btn">✕</button>
          </div>
        )}
      </div>

      {/* Recording Controls */}
      <div className="recorder-controls">
        <button
          onClick={start}
          disabled={recording || processing}
          className={`record-btn ${recording ? 'recording' : ''}`}
        >
          {recording ? (
            <>
              <span className="pulse-dot"></span>
              Recording...
            </>
          ) : (
            <>
              🎤 Start Recording
            </>
          )}
        </button>
        <button
          onClick={stop}
          disabled={!recording}
          className="stop-btn"
        >
          ⏹ Stop
        </button>
      </div>

      {/* Processing Indicator */}
      {processing && (
        <div className="processing-indicator">
          <div className="spinner"></div>
          <p>Processing your query... This may take a moment.</p>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="error-message">
          ⚠️ {error}
        </div>
      )}

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

      {/* Response Display */}
      {response && (
        <div className="response-display">
          <h3>Response</h3>
          
          {response.transcript && (
            <div className="response-item">
              <strong>Your Question:</strong>
              <p>{response.transcript}</p>
            </div>
          )}

          {response.reply_text && (
            <div className="response-item">
              <strong>AI Response:</strong>
              <p>{response.reply_text}</p>
            </div>
          )}

          {response.crop && (
            <div className="response-item">
              <strong>Detected Crop:</strong>
              <span className="badge">{response.crop}</span>
            </div>
          )}

          {response.language && (
            <div className="response-item">
              <strong>Language:</strong>
              <span className="badge">{response.language === 'bn' ? 'Bengali' : 'English'}</span>
            </div>
          )}

          {response.vision_result && response.vision_result.disease && (
            <div className="response-item">
              <strong>Vision Analysis:</strong>
              <p>
                {response.vision_result.disease} 
                {response.vision_result.confidence && (
                  <span className="confidence">
                    ({(response.vision_result.confidence * 100).toFixed(1)}% confidence)
                  </span>
                )}
              </p>
            </div>
          )}

          {response.weather_forecast && response.weather_forecast.hourly && (
            <div className="response-item">
              <strong>Weather:</strong>
              {response.weather_forecast.hourly.temperature_2m && (
                <p>
                  Temperature: {response.weather_forecast.hourly.temperature_2m[0]}°C
                </p>
              )}
            </div>
          )}

          {audioUrl && (
            <div className="response-item">
              <strong>Your Recording:</strong>
              <audio ref={audioRef} controls src={audioUrl} className="audio-player" />
            </div>
          )}
        </div>
      )}
    </div>
  )
}
