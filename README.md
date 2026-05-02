---
title: KrishiBondhu
emoji: 👀
colorFrom: red
colorTo: blue
sdk: docker
pinned: false
license: mit
short_description: KrishiBondhu – AI-Powered Farmer Assistant built during BUBT
---

# KrishiBondhu - AI-Powered Agricultural Assistant 🌾

An intelligent, beautiful agricultural assistant designed specifically for farmers in Bangladesh. Providing real-time crop advice, disease diagnosis, community wisdom, marketplace intelligence, and emergency support in both Bengali and English through voice, text, and image inputs.

**🎨 Modern UI**: Glassmorphic design with smooth animations | **🤖 Multi-Agent AI**: Specialized CrewAI agents for precision guidance | **📱 PWA**: Works offline with auto-sync | **🌍 Hyperlocal**: GPS-powered, location-aware recommendations
---

## ✅ Project Status

| Component | Status | Details |
|-----------|--------|---------|
| **Backend** | ✅ Complete | 25 API routes, 3 agent systems, SQLAlchemy ORM, async PostgreSQL |
| **Frontend UI** | ✅ Complete | 9 integrated tools, glassmorphic design, PWA, responsive |
| **AI Models** | ✅ Complete | CrewAI crew, 6+ agents, local HF models, LangChain integration |
| **Database** | ⏳ Ready | PostgreSQL schema, pgvector, migrations prepared (defer deploy) |
| **Deployment** | 🚀 Ready | Docker Compose, Hugging Face Spaces, local development |

---
## � 9 Intelligent Tools

| Tool | Icon | Purpose |
|------|------|---------|
| **Voice Assistant** | 🎤 | Record farming questions, get instant audio responses |
| **Camera Diagnosis** | 📹 | Capture crop images for disease & pest identification |
| **AI Chat** | 💬 | Type questions in Bengali or English anytime |
| **Market Intelligence** | 📈 | Check real-time mandi prices and 7-day trends |
| **Farm Diary** | 📒 | Log expenses, yields, and field notes with voice |
| **Daily Tips** | 💡 | Get weather-aware alerts for your specific crops |
| **Soil Health** | 🌱 | Analyze soil needs and get fertilizer recommendations |
| **Irrigation Guide** | 💧 | Daily water management advice based on moisture data |
| **Finance Hub** | 💰 | Explore credits, subsidies, and crop insurance options |

---

## 🎨 Beautiful UI Showcase

KrishiBondhu features a **modern glassmorphic design** with:
- ✨ Smooth fade-in and slide animations on page load
- 🎨 Gradient text effects on headings  
- 🌊 Layered shadow system for depth perception
- 💫 Hover effects with subtle lift animations
- ⚡ Backdrop blur for frosted glass cards
- 📱 Full mobile responsiveness (480px to 4K)
- ♿ WCAG accessibility compliance

**Color Palette**:
- Primary: Emerald Green (`#10b981`) - Farm & growth
- Secondary: Cobalt Blue (`#1d4ed8`) - Trust & reliability
- Accent: Amber (`#f59e0b`) - Important alerts
- Backgrounds: Soft gradients with rgba transparency

---

## 🏗️ System Architecture & Agent Interaction

```mermaid
graph TD
    Farmer([Farmer])
    ReactPWA["React PWA (Vibrant UI)"]
    FastAPI[FastAPI Backend]
    IntentRouter[Intent Router Agent]
    DirectResponse[Direct Response]
    CrewAIManager[CrewAI Hierarchical Manager]
    Agronomist[Agronomist Agent]
    Pathologist[Plant Pathologist Agent]
    WeatherAgent[Weather Analyst Agent]
    MarketAgent[Market Analyst Agent]
    FarmManager[Farm Manager Agent]
    AlertAdvisor[Alert Advisor Agent]
    VisionPipeline[Local HF Vision Pipeline]
    WeatherData[External Weather Data]
    MarketData[DAM Market Data]
    Synthesis[Synthesis & DB Storage]

    Farmer -- Text/Voice/Image --> ReactPWA
    ReactPWA -- POST /api/chat --> FastAPI
    FastAPI -- IndexedDB Sync / WebSocket --> ReactPWA
    
    FastAPI --> IntentRouter
    IntentRouter -- Simple Query --> DirectResponse
    IntentRouter -- Complex Query --> CrewAIManager
    
    CrewAIManager --> Agronomist
    CrewAIManager --> Pathologist
    CrewAIManager --> WeatherAgent
    CrewAIManager --> MarketAgent
    CrewAIManager --> FarmManager
    CrewAIManager --> AlertAdvisor
    
    Agronomist --> Synthesis
    
    Pathologist -- Tool --> VisionPipeline
    VisionPipeline --> Synthesis
    Pathologist --> Synthesis
    
    WeatherAgent -- Tool --> WeatherData
    WeatherData --> Synthesis
    WeatherAgent --> Synthesis

    MarketAgent -- Tool --> MarketData
    MarketData --> Synthesis
    MarketAgent --> Synthesis

    FarmManager --> Synthesis
    AlertAdvisor --> Synthesis
    
    Synthesis --> FastAPI
    FastAPI -- Cached via TTLCache --> FastAPI
```

## Features

### 🎯 Core Interaction Modes
- **Multi-Modal Input**: Voice recording, text chat, image upload, and natural language
- **Bilingual Support**: Seamless Bengali and English language detection
- **Voice Interaction**: Speech-to-text and text-to-speech for hands-free operation
- **Vision Analysis**: AI-powered crop disease identification from images
- **Offline Support**: Progressive Web App (PWA) with IndexedDB sync

### 🌾 Farming Intelligence
- **Smart Crop Guidance**: Real-time agronomic advice tailored to your location
- **Disease Diagnosis**: Visual symptom analysis with treatment recommendations
- **Proactive Pest Alerts**: Automated weather-correlated notifications based on crop stages
- **Soil Health Advisor**: AI-powered soil analysis with personalized fertilizer recommendations
- **Water Management**: NASA POWER satellite moisture monitoring with daily irrigation advice
- **Weather Integration**: Location-based forecasts for farming decisions

### 💰 Business & Finance
- **Digital Farm Diary**: Voice-driven expense/yield logging with auto P&L aggregation
- **Smart Market Intelligence**: Real-time wholesale prices from nearby mandis + 7-day trends
- **Agri-Finance Navigator**: Government subsidy guides, credit readiness reports, insurance quotes
- **Price Forecasting**: Predictive market analysis for optimal selling times

### 🤝 Community & Emergency
- **Farmer Community Q&A**: Peer-to-peer knowledge sharing with expert escalation
- **Marketplace Dealer Network**: Connect with verified dealers, scan product barcodes
- **Emergency Support**: Insurance claim filing, disaster reporting, helpline access
- **Knowledge Embedding**: Vector-based semantic search for relevant farming solutions

### 🎨 User Experience  
- **Glassmorphic Design**: Modern frosted glass UI with smooth animations
- **Responsive Layout**: Mobile-first design optimized for field use  
- **Dark Mode Ready**: CSS variables for easy theme customization
- **Accessibility**: WCAG compliant with focus states and color contrast
- **Real-Time Status**: Live agent status indicator with offline mode support

### ⚡ Technical Excellence
- **Multi-Agent Engine**: CrewAI hierarchical process using 6+ specialized agents
- **Real-time GPS**: Automatic location detection for hyperlocal advice
- **Persistent History**: Conversation replay with metadata and confidence scores
- **Local AI Models**: Privacy-first with HuggingFace models (no data sent to cloud)
- **Docker Deployment**: Containerized for easy setup and cloud scaling

## 🚀 Deployment on Hugging Face Spaces

### Environment Variables Setup

For Hugging Face Spaces deployment, you need to set these environment variables in your Space settings:

1. Go to your Hugging Face Space → Settings → Variables and secrets
2. Add the following variables:

#### Required Variables:
```
GEMINI_API_KEY=your-gemini-api-key-here
LLM_PROVIDER=gemini
```

#### Optional Variables (for Hugging Face models):
```
HUGGINGFACE_API_KEY=your-huggingface-api-key-here
HUGGINGFACE_MODEL=microsoft/DialoGPT-medium
```

### Space Configuration

- **SDK**: Docker
- **Dockerfile**: Use the provided `Dockerfile` in the root directory
- **Hardware**: CPU Basic (Free) or GPU Basic (for faster inference)
- **Storage**: Persistent storage enabled

### Troubleshooting

If you see "technical difficulties" errors:

1. **Check API Keys**: Ensure `GEMINI_API_KEY` is set in Space variables
2. **Verify LLM Provider**: Make sure `LLM_PROVIDER=gemini` (Hugging Face models may have rate limits)
3. **Check Logs**: View Space logs for detailed error messages
4. **Basic Mode**: The app will work in basic mode with keyword-based responses even without API keys

### Basic Mode Features

When API keys are not configured, KrishiBondhu operates in basic mode with:
- Keyword-based responses for common crops (rice, wheat, potato)
- Basic farming advice for diseases and fertilizers
- Guidance to consult local agricultural services
- Full UI functionality (chat, image upload, voice recording)

## 🛠 Tech Stack

### **Frontend** - React 18 + Modern Design System
- **Framework**: Vite + React 18 with hot module reload
- **Styling**: Advanced CSS with glassmorphism, animations, and responsive layout
- **PWA**: Vite PWA Plugin with service workers for offline functionality
- **State Management**: React hooks (useState, useEffect, useRef)
- **API Communication**: Fetch with FormData for multipart uploads
- **Animations**: CSS keyframes for smooth fade-in, slide, and pulse effects
- **Accessibility**: Semantic HTML, WCAG contrast ratios, focus management

### **Backend** - FastAPI + CrewAI Intelligence
- **Framework**: FastAPI (async Python) with uvicorn ASGI server
- **Agent Engine**: CrewAI 1.14.4 for hierarchical multi-agent workflows
- **Database**: PostgreSQL 15 with pgvector + PostGIS extensions
- **ORM**: SQLAlchemy 2.0 (async) with Alembic migrations
- **Language Models**: LangChain + Groq integration with local HF fallbacks

### **AI/ML Services**
- **LLM**: LangChain-Groq (Groq API) + local HuggingFace models
- **Speech**: Mozilla Whisper large-v3 (Bengali native ASR)
- **Vision**: prof-freakenstein/plantnet-disease-detection (Plant pathology)
- **TTS**: gTTS (Google Text-to-Speech)
- **Embeddings**: Sentence transformers for semantic Q&A

### **Infrastructure**
- **Container**: Docker + Docker Compose for orchestration
- **Reverse Proxy**: Nginx-ready configuration
- **Deployment**: Supports Hugging Face Spaces, cloud, and on-premise
- **Database**: AsyncPG + pgvector for vector similarity search

## Prerequisites

- Docker & Docker Compose (recommended)
- OR Python 3.11+, Node.js 18+, PostgreSQL 15+
- API Keys:
  - Google Gemini API key (free tier available)
  - Hugging Face API key (optional, free tier available)

##  Quick Start

### 1. Clone Repository
```bash
git clone <repository-url>
cd krishi-bondhu
```

### 2. Configure Environment
Create a `.env` file in the root directory:

```bash
# Agent Model Configuration
HF_TOKEN=your_huggingface_key_here
PRIMARY_LLM_ID=AI71ai/Llama-agrillm-3.3-70B
FALLBACK_LLM_ID=FN-LLM-2B
INTERPRETER_LLM_ID=Tiger-Research/TigerLLM-1B

# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/farmdb

# Services
TTS_PROVIDER=gtts

# Application
DEBUG=true
LOG_LEVEL=INFO
```

### 3. Start with Docker (Recommended)
```bash
docker compose up -d
```

The application will be available at:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### 4. First-Time Setup

**Database Migration:**
```bash
docker compose exec backend alembic upgrade head
```

**Verify Services:**
```bash
# Check all containers are running
docker compose ps

# View backend logs
docker compose logs -f backend
```

##  Configuration

### Switching LLM Providers

To switch between Gemini and Hugging Face:

1. Edit `.env`:
```bash
# For Hugging Face (Free, no rate limits)
LLM_PROVIDER=huggingface

# For Gemini (Faster, better quality)
LLM_PROVIDER=gemini
```

2. Restart backend:
```bash
docker compose restart backend
```

### Specialized AI Models

KrishiBondhu utilizes a multi-agent architecture powered by highly specialized models:

**Language & Logic Models (Hugging Face):**
- **Agronomist Agent:** `AI71ai/Llama-agrillm-3.3-70B` (Primary expert reasoning)
- **Fallback / Low-VRAM Agent:** `FN-LLM-2B` (Lightweight fallback)
- **Interpreter / Router Agent:** `Tiger-Research/TigerLLM-1B` (Fast bilingual NLP)

**Vision & Audio Models:**
- **Disease Analyst (Vision):** `prof-freakenstein/plantnet-disease-detection` (97% accuracy on 38 classes)
- **Explainable AI (VLM):** `enalis/scold` (Vision-language embedding for symptom explanation)
- **Speech-to-Text:** `mozilla-ai/whisper-large-v3-bn` (Native Bengali 16kHz ASR pipeline)

**Google Gemini (Legacy/Fallback):**
- `models/gemini-2.5-flash` (Available as a high-speed fallback for basic mode)
##  Usage

### Web Interface
1. Open http://localhost:5173 in your browser
2. Grant microphone and location permissions when prompted
3. Choose interaction method:
   - **Voice Tab**: Record voice questions
   - **Chat Tab**: Type questions or view conversation history
   - **Vision Tab**: Upload crop/disease images

### Install as PWA
1. Click the install icon in your browser's address bar
2. Or use browser menu: "Install KrishiBondhu"
3. Launch from your home screen like a native app

### API Endpoints

**Core Chat & Analysis:**
```bash
curl -X POST http://localhost:8000/api/chat \
  -F "message=What is the best fertilizer for rice?" \
  -F "user_id=farmer_123"

curl -X POST http://localhost:8000/api/upload_image \
  -F "image=@/path/to/crop.jpg" \
  -F "question=What disease is this?" \
  -F "user_id=farmer_123"

curl -X POST http://localhost:8000/api/upload_audio \
  -F "file=@/path/to/recording.webm" \
  -F "user_id=farmer_123"
```

**Phase 3: Community, Marketplace & Emergency:**
```bash
# Community Q&A
curl -X POST http://localhost:8000/api/community/questions \
  -H "Content-Type: application/json" \
  -d '{"title": "Best rice variety?", "description": "For monsoon", "user_id": "farmer_123"}'

# Marketplace
curl -X POST http://localhost:8000/api/marketplace/search-dealers \
  -H "Content-Type: application/json" \
  -d '{"crop": "rice", "location": "Dhaka", "user_id": "farmer_123"}'

# Emergency Support
curl -X POST http://localhost:8000/api/emergency/report-damage \
  -H "Content-Type: application/json" \
  -d '{"crop": "rice", "damage_type": "flood", "user_id": "farmer_123"}'
```

**Farm Tools:**
```bash
curl -X GET "http://localhost:8000/api/market/prices?crop=rice&location=Dhaka"

curl -X GET "http://localhost:8000/api/soil/recommendations?user_id=farmer_123"

curl -X GET "http://localhost:8000/api/water/irrigation-schedule?user_id=farmer_123"

curl -X POST http://localhost:8000/api/finance/subsidy-finder \
  -H "Content-Type: application/json" \
  -d '{"crop": "rice", "location": "Dhaka"}'
```

##  Development

### Local Development (Without Docker)

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements-lock.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Database:**
```bash
# Start PostgreSQL locally or use Docker:
docker run -d -p 5432:5432 \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=farmdb \
  postgres:15
```

### Run Migrations
```bash
cd backend
alembic upgrade head
```

### Create New Migration
```bash
cd backend
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## 📁 Project Structure

```
krishi-bondhu/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── endpoints/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── alerts.py         # Daily alerts & tips
│   │   │   │   ├── community.py      # Phase 3: Q&A, escalation
│   │   │   │   ├── marketplace.py    # Phase 3: Dealers, scanning
│   │   │   │   ├── emergency.py      # Phase 3: Insurance, claims
│   │   │   │   ├── finance.py        # Finance & subsidy
│   │   │   │   ├── diary.py          # Farm diary logging
│   │   │   │   ├── soil.py           # Soil analysis
│   │   │   │   ├── water.py          # Irrigation guidance
│   │   │   │   ├── market.py         # Market prices
│   │   │   │   ├── routes.py         # Main router
│   │   │   │   └── utils.py          # Helpers
│   │   ├── config/
│   │   │   ├── agents.yaml           # Agent configuration
│   │   │   ├── tasks.yaml            # Task definitions
│   │   │   ├── finance_data.json     # Finance reference data
│   │   │   ├── llm_factory.py        # LLM provider factory
│   │   │   └── model_config.py       # Lazy-loaded model config
│   │   ├── models/
│   │   │   ├── db_models.py          # Core ORM models
│   │   │   ├── community_models.py   # Phase 3: Questions, Answers
│   │   │   ├── marketplace_models.py # Phase 3: Dealers, Products
│   │   │   ├── emergency_models.py   # Phase 3: Insurance, Claims
│   │   │   └── vision.py             # Vision model wrapper
│   │   ├── services/
│   │   │   ├── llm.py                # LLM service
│   │   │   ├── audio.py              # STT/TTS service
│   │   │   ├── weather.py            # Weather service
│   │   │   ├── community_service.py  # Phase 3: Q&A logic
│   │   │   ├── marketplace_service.py # Phase 3: Dealer logic
│   │   │   └── emergency_service.py   # Phase 3: Claims logic
│   │   ├── core/
│   │   │   └── prompts.py            # Agent prompts
│   │   ├── crews/
│   │   │   └── krishi_crew.py        # CrewAI orchestrator
│   │   ├── farm_agent/
│   │   │   └── langgraph_app.py      # LangGraph workflow
│   │   ├── tools/
│   │   │   ├── __init__.py
│   │   │   ├── alert_tool.py
│   │   │   ├── irrigation_tool.py
│   │   │   ├── market_tool.py
│   │   │   ├── soil_tool.py
│   │   │   ├── finance_tool.py
│   │   │   ├── vision_tool.py
│   │   │   └── weather_tool.py
│   │   ├── db.py                      # Database connection
│   │   ├── main.py                    # FastAPI app
│   │   └── storage.py                 # File storage
│   ├── alembic/
│   │   ├── versions/
│   │   │   ├── 0001_initial.py
│   │   │   ├── 0002_add_fields.py
│   │   │   ├── 0003_add_farm_diary.py
│   │   │   ├── 0004_add_tips.py
│   │   │   └── 0005_add_soil_test.py
│   │   └── env.py
│   ├── alembic.ini
│   ├── Dockerfile
│   ├── requirements-lock.txt
│   ├── requirements-heavy.txt
│   ├── pyproject.toml
│   ├── test_irrigation_tools.py
│   └── integration_tests.py
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Chatbot.jsx
│   │   │   ├── Recorder.jsx
│   │   │   ├── CameraCapture.jsx
│   │   │   ├── ImageUpload.jsx
│   │   │   ├── ConversationHistory.jsx
│   │   │   ├── MarketIntelligence.jsx
│   │   │   ├── FarmDiary.jsx
│   │   │   ├── DailyTips.jsx
│   │   │   ├── SoilHealth.jsx
│   │   │   ├── WaterIrrigation.jsx
│   │   │   └── FinanceHub.jsx
│   │   ├── hooks/
│   │   │   └── useAgentSocket.js      # WebSocket hook
│   │   ├── services/
│   │   │   ├── api.js                 # API client
│   │   │   └── offlineQueue.js        # Offline sync
│   │   ├── App.jsx                     # Main dashboard (9 tools)
│   │   ├── App.css                     # Glassmorphic design system
│   │   └── main.jsx
│   ├── public/
│   │   ├── manifest.webmanifest       # PWA config
│   │   └── icons/                     # App icons
│   ├── dev-dist/
│   │   ├── sw.js
│   │   └── workbox-*.js
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.js
│   └── index.html
├── docs/
│   ├── fine_tuning_guide.md
│   └── operations_manual.md
├── Dockerfile                          # Root container
├── docker-compose.yml                  # Full stack orchestration
├── example.env                         # Environment template
├── LICENSE
└── README.md
```

**Key Features by Directory:**
- 🎤 **Voice/Audio**: `services/audio.py`, `components/Recorder.jsx`
- 📸 **Vision**: `models/vision.py`, `components/CameraCapture.jsx`
- 💬 **Chat**: `components/Chatbot.jsx`, `services/llm.py`
- 📊 **Market**: `components/MarketIntelligence.jsx`, `tools/market_tool.py`
- 📒 **Diary**: `components/FarmDiary.jsx`, `endpoints/diary.py`
- 🤝 **Community** (Phase 3): `models/community_models.py`, `endpoints/community.py`
- 🏪 **Marketplace** (Phase 3): `models/marketplace_models.py`, `endpoints/marketplace.py`
- 🚨 **Emergency** (Phase 3): `models/emergency_models.py`, `endpoints/emergency.py`

---

### Rate Limit Errors (Gemini)
**Symptom:** "429 You exceeded your current quota"
**Solution:** Switch to Hugging Face in `.env`:
```bash
LLM_PROVIDER=huggingface
```

### Voice Recording Not Working
**Solution:** Ensure HTTPS or localhost, grant microphone permissions in browser settings

### Location Not Tracking
**Solution:** Grant location permissions, check GPS accuracy settings

### Database Connection Errors
**Solution:** Verify PostgreSQL is running:
```bash
docker compose ps postgres
docker compose logs postgres
```

### pgvector Module Not Found Error (Alembic)
**Symptom:** `ModuleNotFoundError: No module named 'pgvector'` when running `alembic upgrade head`
**Root Cause:** Phase 3 models require pgvector for vector similarity search, but the dependency wasn't in the old lock file
**Solution:**
1. Rebuild Docker images with updated dependencies:
```bash
docker compose build --no-cache backend
docker compose up -d
```

2. Or reinstall dependencies locally:
```bash
cd backend
pip install -r requirements-lock.txt
alembic upgrade head
```

3. If using Docker, ensure the container rebuilds:
```bash
docker compose down -v
docker compose up -d
```

### Frontend Can't Connect to Backend
**Solution:** Check CORS settings and API URL:
```bash
# frontend/.env
VITE_API_URL=http://localhost:8000
```

##  Security Notes

- Never commit `.env` file to version control
- Rotate API keys regularly
- Use environment-specific configurations for production
- Enable HTTPS for production deployments
- Review and restrict CORS origins in production



## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

**New Features Welcome!**
- Additional crop varieties and regions
- Multi-language support expansions
- Mobile app native wrappers
- Integration with government databases

## 📧 Support

For issues and questions:
- Open an issue on GitHub
- Check existing issues for solutions
- Review API documentation at http://localhost:8000/docs

## 🙏 Acknowledgments

- **CrewAI** for multi-agent workflow orchestration
- **Hugging Face** for the local model ecosystem and Transformers library
- **AI71, Tiger-Research, and Mozilla** for open-sourcing localized and highly capable foundation models
- **FastAPI and React** communities

---

**Made with ❤️ for farmers in Bangladesh**
