# 🌾 KrishiBondhu - AI-Powered Farmer Assistant

> **A Voice-Enabled Intelligent Agricultural Assistant for Bangladeshi Farmers**

---

## 📋 Table of Contents

- [Project Overview](#project-overview)
- [Core Features](#core-features)
- [Technology Stack](#technology-stack)
- [Installation Guide](#installation-guide)
- [Quick Start](#quick-start)
- [API Documentation](#api-documentation)
- [Project Structure](#project-structure)
- [Development Guide](#development-guide)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## 🎯 Project Overview

**KrishiBondhu** is an intelligent, voice-enabled agricultural assistant designed to empower Bangladeshi farmers with real-time crop advisory and farming guidance. The system bridges the digital divide by supporting voice interaction in both Bengali and English, making advanced agricultural guidance accessible to all farmers regardless of literacy level.

### Vision
To revolutionize agricultural practices in Bangladesh by leveraging cutting-edge AI technology to provide instant, personalized farming guidance directly to farmers' fingertips.

### Mission
Enable farmers to make data-driven decisions about crop cultivation, disease management, and weather-based farming through a voice-interactive AI assistant.

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

### 2. **Agricultural Intelligence** 🌱
- **Crop Advisory**: Personalized recommendations based on crop type and location
- **Disease Diagnosis**: Identify crop diseases from audio descriptions
- **Weather Integration**: Real-time weather data for farming decisions
- **GPS-Based Insights**: Location-aware farming advice

### 3. **Multi-Turn Conversations** 💬
- **Conversation History**: Track all farmer interactions
- **Context Awareness**: System remembers previous conversations
- **Persistent Storage**: All conversations saved in database

### 4. **User-Friendly Interface** 🖥️
- **Basic, Clean Design**: Simple and intuitive UI
- **Responsive Layout**: Works on desktop and mobile devices
- **Real-time Feedback**: Immediate response display
- **Error Handling**: Graceful error messages

---

## 🛠️ Technology Stack

### Backend
- **Framework**: FastAPI (Python)
- **Async Processing**: AsyncIO with LangGraph
- **Database**: PostgreSQL with SQLAlchemy ORM
- **AI/ML**: Google Gemini API, gTTS, LangGraph

### Frontend
- **Framework**: React 18
- **Build Tool**: Vite
- **Styling**: CSS3 (Basic, minimal design)
- **API Client**: Fetch API

### DevOps
- **Containerization**: Docker
- **Orchestration**: Docker Compose
- **Database**: PostgreSQL

### External Services
- Google Gemini API (LLM & Voice)
- Open-Meteo API (Weather forecasting)
- gTTS (Text-to-speech)

---

## 📦 Installation Guide

### Prerequisites
- Python 3.9+
- Node.js 16+
- PostgreSQL 13+
- Docker & Docker Compose
- Google Gemini API Key

### Step 1: Clone Repository

```bash
git clone <repository-url> KrishiBondhu
cd KrishiBondhu
```

### Step 2: Setup Backend

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements-all.txt

# Create .env file
cat > .env << EOF
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/farmdb
UPLOAD_DIR=/tmp/uploads
GEMINI_API_KEY=your_google_gemini_api_key_here
DEBUG=true
EOF

# Setup database
docker compose up -d postgres
sleep 10
alembic upgrade head

# Start backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend will be available at: **http://localhost:8000**
API docs: **http://localhost:8000/docs**

### Step 3: Setup Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will be available at: **http://localhost:5173**

---

## 🚀 Quick Start

### Using Docker Compose

```bash
cd backend
docker compose up -d
cd ../frontend
npm install && npm run dev
```

Access:
- Frontend: http://localhost:5173
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Manual Setup

**Terminal 1 - Database:**
```bash
cd backend
docker compose up postgres
```

**Terminal 2 - Backend:**
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

**Terminal 3 - Frontend:**
```bash
cd frontend
npm run dev
```

### Test the Application

1. Open http://localhost:5173
2. Click "🎤 Voice" button
3. Click "Start Recording"
4. Speak: "My rice crop has yellow leaves"
5. Wait for response

---

## 📡 API Documentation

### Core Endpoints

#### 1. Upload Audio (Voice Query)

**POST** `/api/upload_audio`

Process voice query and return agricultural advice.

**Request:**
```bash
curl -X POST http://localhost:8000/api/upload_audio \
  -F "file=@voice.wav" \
  -F "user_id=farmer_001" \
  -F "lat=23.7" \
  -F "lon=90.4"
```

**Response:**
```json
{
  "transcript": "My rice crop has yellow leaves",
  "reply_text": "Yellow leaves indicate nitrogen deficiency...",
  "crop": "rice",
  "language": "en",
  "weather_forecast": {
    "temperature": 28.5,
    "humidity": 72
  },
  "tts_path": "/uploads/tts_12345.mp3",
  "gps": {"lat": 23.7, "lon": 90.4}
}
```

#### 2. Get Conversations

**GET** `/api/conversations`

Retrieve all conversations.

**Response:**
```json
[
  {
    "id": 1,
    "user_id": "farmer_001",
    "transcript": "How to grow rice?",
    "confidence": 0.95,
    "created_at": "2025-11-17T10:30:00Z"
  }
]
```

#### 3. Delete Conversation

**DELETE** `/api/conversations/{conversation_id}`

Remove specific conversation from history.

---

## 📁 Project Structure

```
KrishiBondhu/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── db.py                # Database config
│   │   ├── storage.py           # File storage
│   │   ├── api/
│   │   │   ├── routes.py        # API endpoints
│   │   │   └── utils.py         # Utilities
│   │   ├── models/
│   │   │   └── db_models.py     # Database models
│   │   └── farm_agent/
│   │       └── langgraph_app.py # Workflow engine
│   ├── requirements-all.txt
│   ├── docker-compose.yml
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Main component
│   │   ├── App.css              # Styles
│   │   └── components/
│   │       ├── Recorder.jsx     # Voice recorder
│   │       └── ConversationHistory.jsx
│   ├── package.json
│   └── vite.config.js
└── README.md
```

---

## 👨‍💻 Development Guide

### Adding New Routes

Edit `backend/app/api/routes.py`:

```python
@router.get("/crops")
async def get_crops():
    """Get list of supported crops"""
    return {"crops": ["rice", "tomato", "potato"]}
```

### Modifying Workflow

Edit `backend/app/farm_agent/langgraph_app.py` to change the LangGraph workflow logic.

### Database Migrations

```bash
# Create migration
alembic revision -m "description"

# Apply migration
alembic upgrade head
```

### Building Frontend

```bash
cd frontend
npm run build
```

---

## 🔧 Troubleshooting

### Database Connection Error

```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Restart PostgreSQL
docker compose down
docker compose up -d postgres
```

### Gemini API Key Invalid
- Verify API key in `.env`
- Check Gemini API is enabled
- Generate new key from Google Cloud Console

### Audio Upload Fails

```bash
# Check permissions
chmod 777 /tmp/uploads

# Verify gTTS
pip install --upgrade gtts
```

### TTS Not Generating

```bash
# Create upload directory
mkdir -p /tmp/uploads
chmod 777 /tmp/uploads

# Verify gTTS installation
pip install --upgrade gtts
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Google Gemini API**: LLM and speech capabilities
- **LangGraph**: Workflow orchestration
- **Open-Meteo**: Free weather API
- **FastAPI**: Python web framework
- **React**: Frontend framework

---

**Last Updated**: November 17, 2025
**Version**: 1.0.0 (Voice-Only)
**Status**: Active Development
