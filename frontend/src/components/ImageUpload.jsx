import React, { useState, useRef, useEffect } from 'react'

const API_BASE = 'http://localhost:8000/api'

export default function ImageUpload({ onUploadComplete }) {
  const [selectedImage, setSelectedImage] = useState(null)
  const [preview, setPreview] = useState(null)
  const [processing, setProcessing] = useState(false)
  const [response, setResponse] = useState(null)
  const [error, setError] = useState(null)
  const [question, setQuestion] = useState('')
  const [gps, setGps] = useState({ lat: null, lon: null })
  const [gpsStatus, setGpsStatus] = useState('idle')
  const [isPlaying, setIsPlaying] = useState(false)
  const ttsAudioRef = useRef(null)
  const fileInputRef = useRef(null)

  useEffect(() => {
    getCurrentLocation()
  }, [])

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
        setError('Please select an image file')
        return
      }
      setSelectedImage(file)
      setError(null)
      setResponse(null)
      
      // Create preview
      const reader = new FileReader()
      reader.onloadend = () => {
        setPreview(reader.result)
      }
      reader.readAsDataURL(file)
    }
  }

  const handleUpload = async () => {
    if (!selectedImage) {
      setError('Please select an image first')
      return
    }

    setProcessing(true)
    setError(null)
    setResponse(null)

    const fd = new FormData()
    fd.append('image', selectedImage)
    fd.append('user_id', `farmer_${Date.now()}`)
    if (gps.lat && gps.lon) {
      fd.append('lat', gps.lat)
      fd.append('lon', gps.lon)
    }
    if (question.trim()) {
      fd.append('question', question.trim())
    }

    try {
      const resp = await fetch(`${API_BASE}/upload_image`, {
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
              audio.onended = () => setIsPlaying(false)
              audio.onerror = () => setIsPlaying(false)
              audio.play().catch(err => {
                console.error('Audio play error:', err)
                setIsPlaying(false)
              })
            }
          }
          if (onUploadComplete) {
            onUploadComplete()
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
          audio.onended = () => setIsPlaying(false)
          audio.onerror = () => setIsPlaying(false)
          audio.play().catch(err => {
            console.error('Audio play error:', err)
            setIsPlaying(false)
          })
        }
      }

      if (onUploadComplete) {
        onUploadComplete()
      }
    } catch (err) {
      console.error('Upload error:', err)
      let errorMsg = err.message || 'Failed to process image'
      if (errorMsg.includes('Failed to fetch') || errorMsg.includes('NetworkError')) {
        errorMsg = 'Unable to connect to the server. Please check your internet connection and ensure the backend is running.'
      }
      setError(errorMsg)
    } finally {
      setProcessing(false)
    }
  }

  const handleClear = () => {
    setSelectedImage(null)
    setPreview(null)
    setQuestion('')
    setResponse(null)
    setError(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const stopTTS = () => {
    if (ttsAudioRef.current) {
      ttsAudioRef.current.pause()
      ttsAudioRef.current.currentTime = 0
      ttsAudioRef.current = null
      setIsPlaying(false)
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
    <div className="image-upload">
      {/* GPS Status */}
      <div className="gps-status">
        <span className="gps-icon">📍</span>
        <span className="gps-text">
          {gpsStatus === 'success' && `Location: ${gps.lat?.toFixed(4)}, ${gps.lon?.toFixed(4)}`}
          {gpsStatus === 'error' && 'Using default location'}
        </span>
      </div>

      {/* Image Selection */}
      <div className="upload-section">
        <div className="image-preview-container">
          {preview ? (
            <div className="image-preview">
              <img src={preview} alt="Preview" />
              <button onClick={handleClear} className="clear-btn">✕ Remove</button>
            </div>
          ) : (
            <div 
              className="image-drop-zone"
              onClick={() => fileInputRef.current?.click()}
            >
              <div className="drop-zone-content">
                <span className="drop-zone-icon">📷</span>
                <p>Click to select or drag an image here</p>
                <p className="drop-zone-hint">Supports JPG, PNG, WebP</p>
              </div>
            </div>
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleImageSelect}
            style={{ display: 'none' }}
          />
        </div>

        {/* Optional Question */}
        <div className="question-input">
          <label htmlFor="question">Optional: Describe your problem (Bengali or English)</label>
          <textarea
            id="question"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g., My rice crop has yellow spots on the leaves..."
            rows="3"
          />
        </div>

        {/* Upload Button */}
        <button
          onClick={handleUpload}
          disabled={!selectedImage || processing}
          className="upload-btn"
        >
          {processing ? (
            <>
              <div className="spinner-small"></div>
              Processing...
            </>
          ) : (
            <>
              🔍 Analyze Image
            </>
          )}
        </button>
      </div>

      {/* Processing Indicator */}
      {processing && (
        <div className="processing-indicator">
          <div className="spinner"></div>
          <p>Analyzing your image... This may take a moment.</p>
        </div>
      )}

      {/* TTS Control */}
      {isPlaying && (
        <div className="tts-control">
          <button onClick={stopTTS} className="stop-tts-btn">
            ⏹ Stop Audio
          </button>
          <span className="tts-status">🔊 Playing response...</span>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="error-message">
          ⚠️ {error}
        </div>
      )}

      {/* Response Display */}
      {response && (
        <div className="response-display">
          <h3>Analysis Result</h3>
          
          {response.reply_text && (
            <div className="response-item">
              <strong>AI Response:</strong>
              <p>{response.reply_text}</p>
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

          {response.crop && (
            <div className="response-item">
              <strong>Detected Crop:</strong>
              <span className="badge">{response.crop}</span>
            </div>
          )}

          {response.weather_forecast && response.weather_forecast.hourly && (
            <div className="response-item">
              <strong>Weather:</strong>
              {response.weather_forecast.hourly.temperature_2m && (
                <p>Temperature: {response.weather_forecast.hourly.temperature_2m[0]}°C</p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

