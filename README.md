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

An intelligent agricultural assistant designed specifically for farmers in Bangladesh, providing real-time crop advice, disease diagnosis, and farming guidance in both Bengali and English through voice, text, and image inputs.

## 🏗️ System Architecture & Agent Interaction

```mermaid
graph TD
    Farmer([Farmer])
    ReactPWA[React PWA (Vibrant UI)]
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

### Core Capabilities
- **Multi-Modal Input**: Voice recording, text chat, and image upload
- **Bilingual Support**: Seamless Bengali and English language detection
- **Vision Analysis**: AI-powered crop disease identification from images
- **Voice Interaction**: Speech-to-text and text-to-speech for hands-free operation
- **Weather Integration**: Location-based weather data for farming decisions
- **Conversation History**: Persistent chat history across sessions
- **Smart Market Intelligence**: Real-time wholesale prices from nearby mandis with 7-day predictive trend advice
- **Digital Farm Diary**: Voice-driven logging of daily farming expenses and yields with automatic P&L aggregation
- **Proactive Pest Alerts**: Automated weather-correlated pest/disease risk notifications based on current crop stages

### Technical Features
- **Progressive Web App (PWA)**: Installable on mobile/desktop with offline capabilities
- **Multi-Agent Engine**: CrewAI hierarchical process using specialized local Hugging Face models
- **Real-time GPS**: Automatic location detection for localized advice
- **Responsive UI**: Mobile-first design optimized for field use
- **Docker Deployment**: Containerized for easy setup and scaling

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

## 🛠 Local Development

### Frontend
- **Framework**: React 18 + Vite
- **PWA**: Vite PWA Plugin with service workers
- **Styling**: Modern CSS with responsive design
- **API Communication**: Fetch API with FormData

### Backend
- **Framework**: FastAPI (Python)
- **Workflow Engine**: CrewAI for multi-agent reasoning
- **Database**: PostgreSQL with AsyncPG
- **ORM**: SQLAlchemy 2.0 (Async)
- **Migrations**: Alembic

### AI Services
- **LLM Providers**:
  - Local Hugging Face Models (BitsAndBytes 4-bit Quantization)
- **Speech-to-Text**: `mozilla-ai/whisper-large-v3-bn` (Local 16kHz inference)
- **Text-to-Speech**: Google TTS (gTTS)
- **Vision**: `prof-freakenstein/plantnet-disease-detection` (Local HF pipeline)

### Infrastructure
- **Container**: Docker + Docker Compose
- **Reverse Proxy**: Nginx-ready configuration
- **Deployment**: Supports cloud and on-premise

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

**Chat:**
```bash
curl -X POST http://localhost:8000/api/chat \
  -F "message=What is the best fertilizer for rice?" \
  -F "user_id=farmer_123"
```

**Image Analysis:**
```bash
curl -X POST http://localhost:8000/api/upload_image \
  -F "image=@/path/to/crop.jpg" \
  -F "question=What disease is this?" \
  -F "user_id=farmer_123"
```

**Voice Upload:**
```bash
curl -X POST http://localhost:8000/api/upload_audio \
  -F "file=@/path/to/recording.webm" \
  -F "user_id=farmer_123"
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
│   │   ├── api/           # API routes
│   │   ├── core/          # Prompts, config
│   │   ├── db/            # Database setup
│   │   ├── farm_agent/    # LangGraph workflow
│   │   ├── models/        # DB models
│   │   └── services/      # LLM, STT, TTS, Vision
│   ├── alembic/           # Database migrations
│   ├── Dockerfile
│   └── requirements-lock.txt
├── frontend/
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── public/            # PWA assets, icons
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── .env
└── README.md
```

##  Troubleshooting

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
