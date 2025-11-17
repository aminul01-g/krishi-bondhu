import React, { useState, useRef, useEffect } from 'react'

const API_BASE = 'http://localhost:8000/api'

export default function CameraCapture({ onCaptureComplete }) {
  const [stream, setStream] = useState(null)
  const [capturedImage, setCapturedImage] = useState(null)
  const [processing, setProcessing] = useState(false)
  const [response, setResponse] = useState(null)
  const [error, setError] = useState(null)
  const [question, setQuestion] = useState('')
  const [gps, setGps] = useState({ lat: null, lon: null })
  const [gpsStatus, setGpsStatus] = useState('idle')
  const [isPlaying, setIsPlaying] = useState(false)
  const ttsAudioRef = useRef(null)
  const videoRef = useRef(null)
  const canvasRef = useRef(null)

  useEffect(() => {
    getCurrentLocation()
    return () => {
      // Cleanup: stop stream when component unmounts
      if (stream) {
        stream.getTracks().forEach(track => track.stop())
      }
    }
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

  const startCamera = async () => {
    try {
      setError(null)
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' } // Use back camera on mobile
      })
      setStream(mediaStream)
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream
      }
    } catch (err) {
      console.error('Camera error:', err)
      setError('Could not access camera. Please check permissions.')
    }
  }

  const stopCamera = () => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop())
      setStream(null)
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null
    }
    setCapturedImage(null)
  }

  const capturePhoto = () => {
    if (videoRef.current && canvasRef.current) {
      const video = videoRef.current
      const canvas = canvasRef.current
      const context = canvas.getContext('2d')

      canvas.width = video.videoWidth
      canvas.height = video.videoHeight
      context.drawImage(video, 0, 0)

      // Convert to blob
      canvas.toBlob((blob) => {
        if (blob) {
          const imageUrl = URL.createObjectURL(blob)
          setCapturedImage({ blob, url: imageUrl })
        }
      }, 'image/jpeg', 0.9)
    }
  }

  const handleUpload = async () => {
    if (!capturedImage) {
      setError('Please capture a photo first')
      return
    }

    setProcessing(true)
    setError(null)
    setResponse(null)

    const fd = new FormData()
    fd.append('image', capturedImage.blob, 'camera-capture.jpg')
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
          if (onCaptureComplete) {
            onCaptureComplete()
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

      if (onCaptureComplete) {
        onCaptureComplete()
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

  const handleRetake = () => {
    setCapturedImage(null)
    setResponse(null)
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
    <div className="camera-capture">
      {/* GPS Status */}
      <div className="gps-status">
        <span className="gps-icon">📍</span>
        <span className="gps-text">
          {gpsStatus === 'success' && `Location: ${gps.lat?.toFixed(4)}, ${gps.lon?.toFixed(4)}`}
          {gpsStatus === 'error' && 'Using default location'}
        </span>
      </div>

      {/* Camera View */}
      <div className="camera-section">
        {!stream && !capturedImage && (
          <div className="camera-placeholder">
            <span className="camera-icon">📷</span>
            <p>Click "Start Camera" to begin</p>
            <button onClick={startCamera} className="start-camera-btn">
              📹 Start Camera
            </button>
          </div>
        )}

        {stream && !capturedImage && (
          <div className="video-container">
            <video ref={videoRef} autoPlay playsInline className="camera-video" />
            <div className="camera-controls">
              <button onClick={capturePhoto} className="capture-btn">
                📸 Capture
              </button>
              <button onClick={stopCamera} className="stop-camera-btn">
                ⏹ Stop
              </button>
            </div>
          </div>
        )}

        {capturedImage && (
          <div className="captured-image-container">
            <img src={capturedImage.url} alt="Captured" className="captured-image" />
            <div className="capture-controls">
              <button onClick={handleRetake} className="retake-btn">
                🔄 Retake
              </button>
              <button
                onClick={handleUpload}
                disabled={processing}
                className="upload-btn"
              >
                {processing ? (
                  <>
                    <div className="spinner-small"></div>
                    Processing...
                  </>
                ) : (
                  <>
                    🔍 Analyze Photo
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        <canvas ref={canvasRef} style={{ display: 'none' }} />
      </div>

      {/* Optional Question */}
      {capturedImage && (
        <div className="question-input">
          <label htmlFor="camera-question">Optional: Describe your problem</label>
          <textarea
            id="camera-question"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g., This is my rice field, what disease is this?"
            rows="3"
          />
        </div>
      )}

      {/* Processing Indicator */}
      {processing && (
        <div className="processing-indicator">
          <div className="spinner"></div>
          <p>Analyzing your photo... This may take a moment.</p>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="error-message">
          ⚠️ {error}
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
        </div>
      )}
    </div>
  )
}

