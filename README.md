# KrishiBondhu - AI-Powered Agricultural Assistant 🌾

An intelligent agricultural assistant designed specifically for farmers in Bangladesh, providing real-time crop advice, disease diagnosis, and farming guidance in both Bengali and English through voice, text, and image inputs.

## 🚀 Features

### Core Capabilities
- **Multi-Modal Input**: Voice recording, text chat, and image upload
- **Bilingual Support**: Seamless Bengali and English language detection
- **Vision Analysis**: AI-powered crop disease identification from images
- **Voice Interaction**: Speech-to-text and text-to-speech for hands-free operation
- **Weather Integration**: Location-based weather data for farming decisions
- **Conversation History**: Persistent chat history across sessions

### Technical Features
- **Progressive Web App (PWA)**: Installable on mobile/desktop with offline capabilities
- **Multi-LLM Support**: Switch between Google Gemini and Hugging Face models
- **Real-time GPS**: Automatic location detection for localized advice
- **Responsive UI**: Mobile-first design optimized for field use
- **Docker Deployment**: Containerized for easy setup and scaling

## 🛠️ Tech Stack

### Frontend
- **Framework**: React 18 + Vite
- **PWA**: Vite PWA Plugin with service workers
- **Styling**: Modern CSS with responsive design
- **API Communication**: Fetch API with FormData

### Backend
- **Framework**: FastAPI (Python)
- **Workflow Engine**: LangGraph for multi-step reasoning
- **Database**: PostgreSQL with AsyncPG
- **ORM**: SQLAlchemy 2.0 (Async)
- **Migrations**: Alembic

### AI Services
- **LLM Providers**:
  - Google Gemini API (gemini-2.5-flash)
  - Hugging Face Inference API (meta-llama/Llama-3.2-3B-Instruct)
- **Speech-to-Text**: Google Gemini Audio API
- **Text-to-Speech**: Google TTS (gTTS)
- **Vision**: Google Gemini Vision API

### Infrastructure
- **Container**: Docker + Docker Compose
- **Reverse Proxy**: Nginx-ready configuration
- **Deployment**: Supports cloud and on-premise

## 📋 Prerequisites

- Docker & Docker Compose (recommended)
- OR Python 3.11+, Node.js 18+, PostgreSQL 15+
- API Keys:
  - Google Gemini API key (free tier available)
  - Hugging Face API key (optional, free tier available)

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone <repository-url>
cd krishi-bondhu
```

### 2. Configure Environment
Create a `.env` file in the root directory:

```bash
# LLM Configuration
LLM_PROVIDER=huggingface          # or 'gemini'
GEMINI_API_KEY=your_gemini_key_here
HUGGINGFACE_API_KEY=your_hf_key_here
HUGGINGFACE_MODEL=meta-llama/Llama-3.2-3B-Instruct

# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/farmdb

# Services
STT_PROVIDER=gemini
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

## 🔧 Configuration

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

### Available Models

**Hugging Face (Recommended for free tier):**
- `meta-llama/Llama-3.2-3B-Instruct` (default, fast & reliable)
- Other models available on HF Serverless Inference

**Google Gemini:**
- `models/gemini-2.5-flash` (default)
- Rate limit: 20 requests/day on free tier

## 📱 Usage

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

## 🏗️ Development

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

## 🐛 Troubleshooting

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

## 🔒 Security Notes

- Never commit `.env` file to version control
- Rotate API keys regularly
- Use environment-specific configurations for production
- Enable HTTPS for production deployments
- Review and restrict CORS origins in production

## 📝 License

[Add your license here]

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

- Google Gemini API for LLM and Vision capabilities
- Hugging Face for free-tier model hosting
- LangGraph for workflow orchestration
- FastAPI and React communities

---

**Made with ❤️ for farmers in Bangladesh**
