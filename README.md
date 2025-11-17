# 🌾 KrishiBondhu - AI-Powered Farmer Assistant

> **A Voice-Enabled Intelligent Agricultural Assistant for Bangladeshi Farmers**

---

## 📋 Table of Contents

- [Project Overview](#project-overview)
- [Core Features](#core-features)
- [Technology Stack](#technology-stack)
- [Architecture](#architecture)
- [Installation Guide](#installation-guide)
- [Quick Start](#quick-start)
- [API Documentation](#api-documentation)
- [Project Structure](#project-structure)
- [Development Guide](#development-guide)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## 🎯 Project Overview

**KrishiBondhu** is an intelligent, voice-enabled agricultural assistant designed to empower Bangladeshi farmers with real-time crop advisory and disease diagnosis. The system bridges the digital divide by supporting voice interaction in both Bengali and English, making advanced agricultural guidance accessible to all farmers regardless of literacy level.

### Vision
To revolutionize agricultural practices in Bangladesh by leveraging cutting-edge AI technology to provide instant, personalized farming guidance directly to farmers' fingertips.

### Mission
Enable farmers to make data-driven decisions about crop cultivation, disease management, pest control, and weather-based farming through a voice-interactive AI assistant.

### Target Users
- Smallholder farmers in rural Bangladesh
- Agricultural extension workers
- Agribusiness professionals
- Educational institutions

---

## ✨ Core Features

### 1. **Voice-Enabled Interface** 🎤
- **Multilingual Support**: Bengali (বাংলা) and English
- **Speech-to-Text (STT)**: Real-time audio transcription using Google Gemini API
- **Text-to-Speech (TTS)**: Natural-sounding responses using gTTS
- **Accent Recognition**: Optimized for Bangladeshi Bengali dialect

### 2. **Computer Vision Analysis** 📸
- **Crop Disease Detection**: YOLOv8-based vision model for identifying diseases, pests, and deficiencies
- **Image Upload Support**: Direct image analysis for crop health assessment
- **Confidence Scoring**: Quantified analysis results for diagnostic accuracy
- **Multi-format Support**: JPG, PNG, WEBP image formats

### 3. **Intelligent Agricultural Advisory** 🤖
- **Context-Aware Responses**: LangGraph-based workflow for comprehensive analysis
- **Crop Database**: Recognition of 50+ crop types (rice, tomato, potato, wheat, etc.)
- **Disease & Pest Library**: Extensive knowledge base for common agricultural problems
- **Personalized Recommendations**: Tailored solutions based on crop, location, and season

### 4. **Real-Time Weather Integration** 🌤️
- **Location-Based Forecasting**: GPS-integrated weather data via Open-Meteo API
- **Agricultural Alerts**: Weather-based farming recommendations
- **Humidity & Temperature Monitoring**: Critical for disease prediction
- **Precipitation Data**: Irrigation and pest management insights

### 5. **Conversation History Management** 📚
- **Persistent Storage**: PostgreSQL-backed conversation history
- **Metadata Tracking**: Crop type, location, language, and analysis results
- **Quick Reference**: Access previous farming queries and solutions
- **User Profiles**: Personalized farmer profiles and activity tracking

### 6. **Multi-Modal Input Support** 🖼️
- **Audio Input**: Voice queries in Bengali or English
- **Image Input**: Crop photos for disease diagnosis
- **Text Input**: Written queries via chat interface
- **Camera Capture**: Real-time camera feed analysis (Progressive Web App)

---

## 🛠️ Technology Stack

### Backend
| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Framework** | FastAPI 0.104.1 | REST API development |
| **Async Runtime** | Uvicorn 0.24.0 | ASGI server |
| **Database** | PostgreSQL 15+ | Conversation persistence |
| **ORM** | SQLAlchemy 2.0 | Async database operations |
| **Workflow Engine** | LangGraph 0.0.38 | Multi-node processing pipeline |
| **LLM** | Google Gemini 2.5 Flash | NLP & multimodal AI |
| **Speech** | Google Cloud Speech / gTTS | STT & TTS services |
| **Computer Vision** | YOLOv8 / Ultralytics | Object detection |
| **Image Processing** | Pillow, OpenCV | Image manipulation |
| **API Client** | Requests 2.31 | HTTP requests |

### Frontend
| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Framework** | React 18.2.0 | UI framework |
| **Build Tool** | Vite 5.1.0 | Fast module bundler |
| **Styling** | CSS3 | Responsive design |
| **APIs** | Fetch API | HTTP client |
| **PWA** | Service Workers | Progressive Web App support |

### Infrastructure
| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Containerization** | Docker & Docker Compose | Service orchestration |
| **Database Service** | PostgreSQL Container | Managed database |
| **Web Server** | Uvicorn + FastAPI | Production API server |

### External Services
- **Google Gemini API**: Advanced LLM capabilities
- **Open-Meteo API**: Weather forecasting (free, no API key)
- **Google Cloud Speech**: Speech recognition
- **gTTS**: Text-to-speech conversion

---

## 🏗️ Architecture

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React PWA)                    │
│  ┌──────────────┬──────────────┬──────────────┐             │
│  │ Voice Input  │ Image Upload │ Chat/Text    │             │
│  └──────────────┴──────────────┴──────────────┘             │
│                          │                                    │
└──────────────────────────┼────────────────────────────────────┘
                           │ HTTP/REST
┌──────────────────────────┼────────────────────────────────────┐
│              FastAPI Backend (Python)                         │
│                                                               │
│  ┌─────────────────────────────────────────────────┐        │
│  │  API Routes (/api/upload_audio, /api/conversations)│     │
│  └─────────────────────────────────────────────────┘        │
│                        │                                      │
│  ┌─────────────────────────────────────────────────┐        │
│  │     LangGraph Workflow Engine (Async)           │        │
│  │  ┌─────────────────────────────────────────┐    │        │
│  │  │ START → STT → INTENT → VISION → WEATHER │    │        │
│  │  │           ↓                              │    │        │
│  │  │        REASONING → TTS → DATABASE → END │    │        │
│  │  └─────────────────────────────────────────┘    │        │
│  └─────────────────────────────────────────────────┘        │
│                        │                                      │
│   ┌────────────────────┼────────────────────┐               │
│   │                    │                    │               │
└───┼────────────────────┼────────────────────┼───────────────┘
    │                    │                    │
    ▼                    ▼                    ▼
┌─────────────┐  ┌──────────────┐  ┌──────────────────┐
│ PostgreSQL  │  │ Google Gemini│  │ Open-Meteo API   │
│ Database    │  │ LLM + Vision │  │ Weather Service  │
└─────────────┘  └──────────────┘  └──────────────────┘
```

### LangGraph Workflow Pipeline

```
INPUT (Audio/Image/Text)
    │
    ├──► STT Node: Speech-to-Text
    │    └─► Gemini Transcription + Language Detection
    │
    ├──► INTENT Node: Extract Crop & Symptoms
    │    └─► JSON parsing (crop, symptoms, need_image)
    │
    ├──► VISION Node: Image Analysis (if image provided)
    │    └─► YOLOv8 disease detection + Gemini multimodal
    │
    ├──► WEATHER Node: Fetch Location-Based Weather
    │    └─► Open-Meteo API + GPS coordinates
    │
    ├──► REASONING Node: Generate Expert Advice
    │    └─► Gemini LLM with agricultural system prompt
    │
    ├──► TTS Node: Convert Response to Audio
    │    └─► gTTS audio generation (Bengali/English)
    │
    ├──► DATABASE Node: Persist Conversation
    │    └─► PostgreSQL storage with metadata
    │
    └──► OUTPUT (Text + Audio + Metadata)
```

### Database Schema

```sql
-- Users Table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    external_id VARCHAR(255) UNIQUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Conversations Table
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    transcript TEXT,
    tts_path VARCHAR(255),
    media_url VARCHAR(255),
    confidence FLOAT,
    meta_data JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 📦 Installation Guide

### Prerequisites

- **Python**: 3.9+ (3.11 recommended)
- **Node.js**: 16+ with npm
- **Docker**: 20.10+ and Docker Compose
- **Git**: Latest version
- **PostgreSQL**: 13+ (via Docker)
- **API Keys**: Google Gemini API key
- **Disk Space**: 2GB+ (includes ML models)
- **RAM**: 4GB minimum, 8GB recommended

### Step 1: Clone Repository

```bash
cd /home/aminul/Documents/p
git clone <repository-url> KrishiBondhu
cd KrishiBondhu
```

### Step 2: Setup Backend

#### 2.1 Create Virtual Environment

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### 2.2 Install Dependencies

```bash
pip install -r requirements-all.txt
```

#### 2.3 Configure Environment Variables

Create `.env` file in `backend/` directory:

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/farmdb
UPLOAD_DIR=/tmp/uploads

# Google Gemini API
GEMINI_API_KEY=your_google_gemini_api_key_here

# Optional: Other LLM providers (if using)
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# Server
HOST=0.0.0.0
PORT=8000
DEBUG=true
```

#### 2.4 Setup Database

```bash
# Start PostgreSQL via Docker
docker compose up -d postgres

# Wait 10 seconds for PostgreSQL to initialize
sleep 10

# Run migrations
alembic upgrade head
```

#### 2.5 Start Backend Server

```bash
# In backend directory with venv activated
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend will be available at: **http://localhost:8000**
API docs: **http://localhost:8000/docs**

### Step 3: Setup Frontend

#### 3.1 Install Dependencies

```bash
cd frontend
npm install
```

#### 3.2 Configure API Endpoint

Check `frontend/src/App.jsx` - ensure API_BASE points to your backend:

```javascript
const API_BASE = 'http://localhost:8000/api'
```

#### 3.3 Start Frontend Development Server

```bash
npm run dev
```

Frontend will be available at: **http://localhost:5173**

### Step 4: Verify Installation

1. **Backend Health**: Visit http://localhost:8000/docs
2. **Frontend Access**: Visit http://localhost:5173
3. **Database**: Check PostgreSQL connection

---

## 🚀 Quick Start

### Running All Services (Docker Compose)

```bash
cd backend
docker compose up -d
```

This starts:
- PostgreSQL database (port 5432)
- Backend API (port 8000)
- Frontend (port 5173)

### Manual Service Startup

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

**Terminal 3 - Database:**
```bash
cd backend
docker compose up postgres
```

### First Test

1. Open http://localhost:5173 in browser
2. Click "🎤 Voice" tab
3. Click "Start Recording"
4. Speak: *"My rice crop has yellow leaves"* (or Bengali equivalent)
5. Wait for processing and response

---

## 📡 API Documentation

### Core Endpoints

#### 1. Upload Audio & Process

**POST** `/api/upload_audio`

Process voice query and return agricultural advice.

**Request:**
```bash
curl -X POST http://localhost:8000/api/upload_audio \
  -F "file=@voice_query.webm" \
  -F "user_id=farmer_001" \
  -F "lat=23.7" \
  -F "lon=90.4" \
  -F "image=@crop_photo.jpg"  # Optional
```

**Response:**
```json
{
  "transcript": "My rice crop has yellow leaves",
  "reply_text": "Yellow leaves in rice often indicate nitrogen deficiency...",
  "crop": "rice",
  "language": "en",
  "vision_result": {
    "disease": "leaf_spot",
    "confidence": 0.87
  },
  "weather_forecast": {
    "temperature": 28.5,
    "humidity": 72,
    "precipitation": 0
  },
  "tts_path": "/tmp/uploads/audio_response.mp3",
  "user_id": "farmer_001",
  "gps": { "lat": 23.7, "lon": 90.4 }
}
```

#### 2. Upload Image for Analysis

**POST** `/api/upload_image`

Analyze crop image for diseases and pests.

**Request:**
```bash
curl -X POST http://localhost:8000/api/upload_image \
  -F "image=@crop_disease.jpg" \
  -F "user_id=farmer_001" \
  -F "lat=23.7" \
  -F "lon=90.4" \
  -F "question=What disease is this?"
```

#### 3. Fetch Conversation History

**GET** `/api/conversations`

Retrieve all previous farmer conversations.

**Response:**
```json
[
  {
    "id": 1,
    "user_id": 1,
    "transcript": "How to grow tomatoes?",
    "confidence": 0.92,
    "metadata": {
      "crop": "tomato",
      "language": "en"
    },
    "created_at": "2024-11-17T10:30:00"
  }
]
```

#### 4. Delete Conversation

**DELETE** `/api/conversations/{conversation_id}`

Remove specific conversation from history.

---

## 📁 Project Structure

```
KrishiBondhu/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app entry point
│   │   ├── db.py                   # Database configuration
│   │   ├── storage.py              # File storage utilities
│   │   ├── api/
│   │   │   ├── routes.py           # REST endpoints
│   │   │   ├── utils.py            # Helper functions
│   │   │   └── __init__.py
│   │   ├── models/
│   │   │   ├── db_models.py        # SQLAlchemy models
│   │   │   ├── vision.py           # YOLOv8 vision model
│   │   │   └── __init__.py
│   │   ├── farm_agent/
│   │   │   ├── langgraph_app.py    # Main workflow engine (1362 lines)
│   │   │   └── __init__.py
│   │   ├── llm/
│   │   │   └── __init__.py
│   │   └── __init__.py
│   ├── alembic/
│   │   ├── env.py                  # Migration environment
│   │   ├── alembic.ini             # Alembic config
│   │   └── versions/               # Database migrations
│   ├── requirements-all.txt        # Python dependencies
│   ├── docker-compose.yml          # Service orchestration
│   ├── alembic.ini                 # Database migrations
│   ├── setup_database.sh           # DB initialization script
│   ├── start_server.sh             # Backend startup script
│   ├── test_audio_upload.py        # Audio testing
│   ├── test_gemini_*.py            # LLM testing scripts
│   └── README.MD
├── frontend/
│   ├── src/
│   │   ├── App.jsx                 # Main React component
│   │   ├── App.css                 # Global styles
│   │   ├── main.jsx                # React entry point
│   │   └── components/
│   │   │   ├── Recorder.jsx        # Audio recorder
│   │   │   ├── CameraCapture.jsx   # Camera interface
│   │   │   ├── Chatbot.jsx         # Chat interface
│   │   │   └── ConversationHistory.jsx  # History panel
│   ├── public/                     # Static assets
│   ├── vite.config.js              # Vite configuration
│   ├── package.json                # Node.js dependencies
│   ├── index.html                  # HTML template
│   └── README.md
├── LICENSE
├── README.md                       # This file
└── RUN_PROJECT.md                  # Quick run guide
```

---

## 👨‍💻 Development Guide

### Adding New Crops

Edit `backend/app/farm_agent/langgraph_app.py` - search for `bengali_indicators`:

```python
bengali_indicators = [
    # Existing crops...
    "নতুন_ফসল",  # New crop in Bengali
    "new_crop",   # New crop in English
]
```

### Extending Vision Model

Replace YOLOv8 with custom model in `backend/app/models/vision.py`:

```python
def run_vision_classifier(image_path: str) -> dict:
    # Load your custom model
    model = load_custom_model()
    
    # Run inference
    results = model.predict(image_path)
    
    return {
        "disease": results["disease_name"],
        "confidence": results["confidence"],
        "treatment": results["recommended_treatment"]
    }
```

### Adding New API Routes

Create new route in `backend/app/api/routes.py`:

```python
@router.get("/crops")
async def get_crops():
    """Get list of supported crops"""
    return {"crops": ["rice", "tomato", "potato", ...]}
```

### Running Tests

```bash
cd backend
pytest -v

# Test specific module
pytest tests/test_vision.py -v

# Test with coverage
pytest --cov=app tests/
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. Database Connection Error
**Error**: `FATAL: Ident authentication failed`

**Solution**:
```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Restart PostgreSQL
docker compose down
docker compose up -d postgres
```

#### 2. Gemini API Key Invalid
**Error**: `401 Unauthorized`

**Solution**:
- Verify API key in `.env`
- Check key has Gemini API enabled
- Generate new key from Google Cloud Console

#### 3. Audio Upload Fails
**Error**: `413 Payload Too Large`

**Solution**:
```python
# Increase FastAPI size limit in backend/app/main.py
app = FastAPI(
    max_upload_size=50_000_000  # 50MB
)
```

#### 4. TTS Not Generating
**Error**: `TTS file not found`

**Solution**:
```bash
# Check upload directory permissions
chmod 777 /tmp/uploads

# Verify gTTS installation
pip install --upgrade gtts
```

#### 5. Vision Model Won't Load
**Error**: `weights_only error`

**Solution**:
```bash
# Update PyTorch
pip install --upgrade torch torchvision

# Update Ultralytics
pip install --upgrade ultralytics
```

---

## 📊 Performance Metrics

### Expected Response Times

| Operation | Time | Notes |
|-----------|------|-------|
| Audio Upload | 1-2s | Depends on audio length |
| STT Processing | 3-5s | Gemini transcription |
| Vision Analysis | 2-4s | YOLOv8 inference |
| LLM Response | 3-8s | Gemini generation |
| TTS Generation | 2-4s | gTTS audio synthesis |
| **Total E2E** | 12-25s | End-to-end processing |

### Resource Requirements

- **CPU**: 2+ cores recommended
- **RAM**: 4GB minimum (8GB+ for vision)
- **Storage**: 2GB (includes models)
- **Network**: 2Mbps+ upload speed

---

## 🌐 Deployment

### Docker Deployment

```bash
# Build image
docker build -t krishibondhu:latest backend/

# Run container
docker run -p 8000:8000 \
  -e GEMINI_API_KEY=$GEMINI_API_KEY \
  -e DATABASE_URL="postgresql://..." \
  krishibondhu:latest
```

### Cloud Deployment (AWS, GCP, Azure)

Refer to `DEPLOYMENT.md` for cloud-specific instructions.

---

## 🤝 Contributing

### Development Workflow

1. Fork the repository
2. Create feature branch: `git checkout -b feature/your-feature`
3. Make changes and test
4. Commit: `git commit -m "Add feature"`
5. Push: `git push origin feature/your-feature`
6. Create Pull Request

### Code Standards

- **Python**: PEP 8, use Black for formatting
- **JavaScript**: ESLint configured
- **Comments**: Clear, concise documentation
- **Tests**: Minimum 80% coverage

---

## 📄 License

This project is licensed under the [LICENSE](./LICENSE) file.

---

## 📞 Support & Contact

- **Issues**: Create GitHub issue with detailed description
- **Discussions**: Use GitHub Discussions for questions
- **Email**: 
- **Documentation**: 

---

## 🙏 Acknowledgments

- **Google Gemini API**: LLM and vision capabilities
- **Ultralytics YOLOv8**: Object detection framework
- **LangGraph**: Workflow orchestration
- **Open-Meteo**: Free weather API
- **Contributors**: 

---

**Last Updated**: November 17, 2024
**Version**: 1.0.0
**Status**: Active Development
