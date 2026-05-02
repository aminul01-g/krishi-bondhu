# Phase 2 – Technology Selection & Project Scaffolding
## KrishiBondhu: Three New Production-Grade Features

**Date:** May 2, 2026  
**Status:** Phase 2 – Technology finalization and project structure  
**Prepared by:** Senior SDLC Manager & Full-Stack AI Engineer

---

## Table of Contents
1. [Technology Stack Finalization](#technology-stack-finalization)
2. [New Dependencies & Rationale](#new-dependencies--rationale)
3. [Updated Project Structure](#updated-project-structure)
4. [Installation & Setup Guide](#installation--setup-guide)
5. [Configuration & Environment](#configuration--environment)
6. [Deployment Checklist](#deployment-checklist)

---

## Technology Stack Finalization

### Backend Core (No Changes)
- **FastAPI** — REST framework (existing)
- **SQLAlchemy 2.0 + async** — ORM (existing)
- **PostgreSQL** — Primary database (existing)
- **Alembic** — Database migrations (existing)
- **CrewAI** — Multi-agent orchestration (existing)
- **LangChain** — Tool framework (existing)

### NEW: PostgreSQL Extensions & Vector Databases

| Technology | Purpose | Version | Why This Choice |
|-----------|---------|---------|-----------------|
| **pgvector** | Vector storage for Q&A embeddings | 0.5.1+ | Native PostgreSQL extension, no external services, cost-effective, offline-cacheable |
| **PostGIS** | Geospatial queries for dealer location | 3.3+ | Standard for location-based search, integrates seamlessly with PostgreSQL |

**Setup Impact:**
```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS postgis;
```

---

### NEW: Embeddings & NLP

| Technology | Purpose | Version | Why This Choice |
|-----------|---------|---------|-----------------|
| **sentence-transformers** | Generate embeddings for Q&A semantic search | 2.3.1+ | Multilingual (Bengali + English), ~120MB model size, works offline, battle-tested |
| **transformers** (Hugging Face) | Tokenization & model infrastructure | 4.35.0+ | Dependency of sentence-transformers, supports multilingual models |
| **torch** (PyTorch) | Deep learning backbone | 2.1.0+ | Lightweight CPU version sufficient, no GPU required for embeddings |
| **numpy** | Numerical operations | 1.24.0+ | Required by sentence-transformers |

**Model Selected:**
- `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
  - Size: ~120MB (fits in memory + PWA cache)
  - Languages: 100+ (including Bengali)
  - Latency: <100ms per query on CPU
  - Accuracy: SOTA for cross-lingual similarity

**Installation & Caching:**
```python
# First run: downloads ~120MB from Hugging Face
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
# Subsequent runs: loads from ~/.cache/huggingface/

# For offline operation, cache in Docker image or application filesystem
```

---

### NEW: OCR & Image Processing

| Technology | Purpose | Version | Why This Choice |
|-----------|---------|---------|-----------------|
| **pytesseract** | Python wrapper for Tesseract OCR | 0.3.10+ | Lightweight, offline-capable, good Bengali support |
| **tesseract-ocr** | Binary OCR engine | 5.2.0+ | Best open-source OCR for product labels, multilingual |
| **opencv-python** | Image preprocessing for OCR | 4.8.0+ | Angle detection, contrast enhancement before OCR |
| **Pillow** (PIL) | Image manipulation | 10.0.0+ | Already used in project, handle base64 ↔ image conversion |

**Setup in Docker:**
```dockerfile
# Dockerfile addition
RUN apt-get update && apt-get install -y tesseract-ocr \
    libtesseract-dev && rm -rf /var/lib/apt/lists/*

# Language packs for Bengali
RUN apt-get install -y tesseract-ocr-ben
```

**Integration:**
```python
import pytesseract
from PIL import Image
import cv2

# Example: Extract text from product label image
image = Image.open(label_photo)
# Preprocess: rotate, contrast enhance
text = pytesseract.image_to_string(image, lang='eng+ben')
```

---

### NEW: Barcode & QR Scanning

| Technology | Purpose | Version | Why This Choice |
|-----------|---------|---------|-----------------|
| **pyzbar** | Python wrapper for barcode/QR decoding | 0.1.9+ | Lightweight, supports 20+ barcode formats (EAN, QR, etc.) |
| **zbar** (binary) | Barcode detection engine | 0.22+ | Highly optimized, works offline |
| **opencv-python** | Barcode pre-processing | 4.8.0+ | Already in use for label OCR |

**Frontend (Browser):**
```javascript
// Use jsQR or zbar.js for client-side QR scanning
// Sends base64 image or raw barcode string to backend
```

**Backend:**
```python
from pyzbar.pyzbar import decode
from PIL import Image
import base64

def scan_barcode(image_base64: str) -> str:
    image = Image.open(io.BytesIO(base64.b64decode(image_base64)))
    decoded_objects = decode(image)
    for obj in decoded_objects:
        return obj.data.decode('utf-8')  # Returns barcode text
```

**Setup in Docker:**
```dockerfile
RUN apt-get update && apt-get install -y libzbar0 libzbar-dev
```

---

### NEW: HTTP Client for External APIs

| Technology | Purpose | Version | Why This Choice |
|-----------|---------|---------|-----------------|
| **httpx** | Async HTTP client | 0.24.0+ | Modern, supports async/await, connection pooling, timeouts |
| **aiohttp** | Alternative async HTTP | 3.8.0+ | Also good, but httpx is more Pythonic |

**Usage in SMS/Email/Government APIs:**
```python
import httpx

async def call_government_api(barcode_text: str):
    """Call Bangladesh BSTI (mocked initially, real later)"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            "https://api.bsti.gov.bd/verify-barcode",  # Mock URL
            json={"barcode": barcode_text},
            headers={"Authorization": f"Bearer {API_KEY}"}
        )
        return response.json()
```

---

### NEW: SMS Service Abstraction

| Technology | Purpose | Version | Why This Choice |
|-----------|---------|---------|-----------------|
| **python-dotenv** | Load env variables for API keys | 1.0.0+ | Secure, already used in project |
| **Mock SMS Service** | Initial implementation | N/A | Custom sms_provider.py for local testing, swappable to Nexmo/Vonage |

**Design Pattern:**
```python
# sms_provider.py - abstraction layer
class SMSProvider:
    async def send(self, phone: str, message: str) -> Dict:
        """Send SMS via configured provider"""
        if os.getenv("SMS_PROVIDER") == "mock":
            return await MockSMSProvider.send(phone, message)
        elif os.getenv("SMS_PROVIDER") == "nexmo":
            return await NexmoSMSProvider.send(phone, message)
        # ... more providers
```

---

### NEW: Vector Search Optimization

| Technology | Purpose | Version | Why This Choice |
|-----------|---------|---------|-----------------|
| **pgvector** | In-database vector search | 0.5.1+ | <-- Listed above in extensions |
| **psycopg** | PostgreSQL async adapter | 3.1.0+ | Already used in project, supports pgvector queries |

**Query Example:**
```sql
-- pgvector similarity search
SELECT * FROM community_questions
WHERE 1 - (embedding <-> :query_embedding) > 0.7
ORDER BY embedding <-> :query_embedding ASC
LIMIT 5;
```

---

### NEW: Async Task Management

| Technology | Purpose | Version | Why This Choice |
|-----------|---------|---------|-----------------|
| **celery** | Background task queue | 5.3.0+ | For async SMS/email sending, report generation, image analysis |
| **redis** | Task broker (existing or new) | 7.0+ | Already used in project for caching, can be task broker |

**Optional for Phase 2:**
- For MVP: Use simple async tasks with `asyncio.create_task()`
- For Phase 3+: Set up Celery + Redis for scalability

---

## Updated Dependencies & Rationale

### New Packages to Install

```txt
# Vector Store & Geospatial
pgvector==0.5.1
postgis==3.3.0  # PostgreSQL extension (installed via apt, not pip)

# Embeddings & NLP
sentence-transformers==2.3.1
transformers==4.35.0
torch==2.1.0  # CPU-only version
numpy==1.24.3
scipy==1.11.0  # Required by sentence-transformers

# OCR & Barcode
pytesseract==0.3.10
opencv-python==4.8.1.78
pyzbar==0.1.9
Pillow==10.0.0  # Already in use

# HTTP & Async
httpx==0.24.1
aiohttp==3.8.5  # If needed for alternatives

# SMS Provider (custom, see below)
python-dotenv==1.0.0  # Already in use

# Database & ORM (already present)
# SQLAlchemy>=2.0.0
# psycopg[binary]>=3.1.0
# alembic>=1.12.0

# Optional: Background tasks
# celery==5.3.0
# redis==5.0.0  # If Celery needed
```

### Version Strategy
- **Conservative:** Stick with tested versions (above) for production
- **Upgrade path:** Document minor version bumps quarterly
- **Break-fix:** Test new versions on staging before production deployment

---

## Updated Project Structure

### Current Structure (Existing)
```
krishi-bondhu/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── db.py
│   │   ├── api/
│   │   │   ├── endpoints/
│   │   │   │   ├── alerts.py
│   │   │   │   ├── diary.py
│   │   │   │   ├── soil.py
│   │   │   │   ├── water.py
│   │   │   │   ├── market.py
│   │   │   │   ├── finance.py
│   │   │   │   └── __init__.py
│   │   │   └── utils.py
│   │   ├── agents/
│   │   ├── models/
│   │   ├── services/
│   │   ├── tools/
│   │   │   ├── __init__.py
│   │   │   ├── alert_tool.py
│   │   │   ├── soil_tool.py
│   │   │   ├── weather_tool.py
│   │   │   ├── market_tool.py
│   │   │   ├── finance_tool.py
│   │   │   └── irrigation_tool.py
│   │   └── config/
│   ├── alembic/
│   │   ├── versions/
│   │   └── env.py
│   └── requirements-lock.txt
├── frontend/
│   └── src/
│       └── components/
├── docker-compose.yml
└── README.md
```

### NEW Additions (Phase 2)

```
krishi-bondhu/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── endpoints/
│   │   │       ├── community.py          # NEW: Q&A endpoints
│   │   │       ├── marketplace.py        # NEW: Dealer + barcode endpoints
│   │   │       └── emergency.py          # NEW: Damage report + helpline endpoints
│   │   │
│   │   ├── agents/
│   │   │   └── agents.yaml               # UPDATED: Add 3 new agents
│   │   │
│   │   ├── tools/
│   │   │   ├── community_tools.py        # NEW: Search, escalate, moderate
│   │   │   ├── marketplace_tools.py      # NEW: Search dealers, verify barcode, OCR
│   │   │   ├── emergency_tools.py        # NEW: Assess damage, generate report, SMS, helpline
│   │   │   └── __init__.py               # UPDATED: Import new tools
│   │   │
│   │   ├── models/
│   │   │   ├── db_models.py              # UPDATED: Add 12 new tables
│   │   │   └── __init__.py
│   │   │
│   │   ├── services/
│   │   │   ├── sms_provider.py           # NEW: SMS abstraction layer (mock + Nexmo)
│   │   │   ├── ocr_service.py            # NEW: Tesseract wrapper
│   │   │   ├── barcode_service.py        # NEW: pyzbar wrapper
│   │   │   ├── embedding_service.py      # NEW: sentence-transformers wrapper
│   │   │   └── geospatial_service.py     # NEW: PostGIS queries
│   │   │
│   │   ├── utils/
│   │   │   ├── vector_utils.py           # NEW: pgvector helpers
│   │   │   ├── pdf_generator.py          # NEW: Damage report PDF
│   │   │   └── __init__.py
│   │   │
│   │   ├── config/
│   │   │   ├── community_qa_data.json    # NEW: Initial Q&A seed data
│   │   │   ├── dealers_seed.json         # NEW: Initial dealer data
│   │   │   ├── verified_products.json    # NEW: Sample verified products
│   │   │   └── model_config.py           # UPDATED: Embedding model config
│   │   │
│   │   └── llm/
│   │       └── provider.py               # UPDATED: If embedding model integration needed
│   │
│   ├── alembic/
│   │   └── versions/
│   │       ├── 0007_add_pgvector_postgis.py      # NEW: Extensions
│   │       ├── 0008_community_qa_tables.py       # NEW: Q&A schema
│   │       ├── 0009_marketplace_tables.py        # NEW: Dealer schema
│   │       └── 0010_emergency_tables.py          # NEW: Insurance schema
│   │
│   ├── tests/
│   │   ├── test_embedding_service.py     # NEW: Vector embedding tests
│   │   ├── test_barcode_scanning.py      # NEW: QR/barcode tests
│   │   ├── test_community_qa.py          # NEW: Q&A workflow tests
│   │   ├── test_marketplace.py           # NEW: Dealer search tests
│   │   ├── test_emergency.py             # NEW: Damage report tests
│   │   └── __init__.py
│   │
│   ├── docker/
│   │   └── Dockerfile                    # UPDATED: Add tesseract, zbar, pgvector
│   │
│   ├── requirements.txt                  # UPDATED: New packages
│   └── pyproject.toml                    # UPDATED: Version constraints
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Community/
│   │   │   │   ├── SearchQA.jsx          # NEW: Community search screen
│   │   │   │   ├── AskQuestion.jsx       # NEW: Question form
│   │   │   │   └── AnswerDetail.jsx      # NEW: Answer display + upvote
│   │   │   │
│   │   │   ├── Marketplace/
│   │   │   │   ├── SearchDealers.jsx     # NEW: Dealer search screen
│   │   │   │   ├── BarcodeScanner.jsx    # NEW: QR/barcode camera
│   │   │   │   └── LabelScanner.jsx      # NEW: Product label OCR
│   │   │   │
│   │   │   └── Emergency/
│   │   │       ├── ReportDamage.jsx      # NEW: Damage report form
│   │   │       ├── ReportHistory.jsx     # NEW: Claims status tracking
│   │   │       └── HelplineButton.jsx    # NEW: One-tap helpline call
│   │   │
│   │   ├── hooks/
│   │   │   ├── useEmbedding.js           # NEW: Vector search hook
│   │   │   ├── useBarcodeScanner.js      # NEW: Camera access hook
│   │   │   ├── useOfflineSync.js         # NEW: Damage reports sync
│   │   │   └── __init__.js
│   │   │
│   │   ├── services/
│   │   │   ├── communityApi.js           # NEW: Q&A API calls
│   │   │   ├── marketplaceApi.js         # NEW: Dealer + barcode API calls
│   │   │   ├── emergencyApi.js           # NEW: Damage report API calls
│   │   │   └── indexedDBCache.js         # UPDATED: Cache for Q&A + dealers + reports
│   │   │
│   │   ├── App.jsx                       # UPDATED: Add Community, Marketplace, Emergency routes
│   │   └── main.jsx
│   │
│   └── package.json                      # UPDATED: Add jsQR or zbar.js for barcode
│
├── .env.example                           # UPDATED: SMS provider keys, government API keys, helpline number
├── docker-compose.yml                     # UPDATED: Add pgvector + PostGIS setup
├── .dockerignore
└── README.md                              # UPDATED: Phase 2 documentation

```

---

## Installation & Setup Guide

### Step 1: Update Backend Dependencies

```bash
cd backend

# Backup current requirements
cp requirements-lock.txt requirements-lock.txt.backup

# Update requirements.txt with new packages (see below)
cat >> requirements.txt << 'EOF'

# Phase 2: New features - Vector Store & Embeddings
pgvector==0.5.1
sentence-transformers==2.3.1
transformers==4.35.0
torch==2.1.0  # CPU-only
numpy==1.24.3
scipy==1.11.0

# Phase 2: OCR & Barcode
pytesseract==0.3.10
opencv-python==4.8.1.78
pyzbar==0.1.9

# Phase 2: HTTP & Async
httpx==0.24.1
EOF

# Install dependencies
pip install -r requirements.txt

# Verify installations
python -c "import sentence_transformers; print('✅ sentence-transformers OK')"
python -c "import cv2; print('✅ opencv-python OK')"
python -c "import pyzbar; print('✅ pyzbar OK')"
python -c "import pytesseract; print('✅ pytesseract OK')"
```

### Step 2: Set Up PostgreSQL Extensions

```bash
# Connect to PostgreSQL
psql -U postgres -d krishi

# Enable extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;  # For text similarity (bonus)

# Verify
SELECT * FROM pg_extension WHERE extname IN ('vector', 'postgis');

# Output:
# +-----------+-------+
# | extname   | extver |
# +-----------+-------+
# | vector    | 0.5.1 |
# | postgis   | 3.3.0 |
# +-----------+-------+
```

### Step 3: Download Embedding Model

```bash
# First-time download (~120MB)
# Create cache script
cat > download_models.py << 'EOF'
from sentence_transformers import SentenceTransformer
import os

# Download to default cache
model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
print(f"✅ Model cached at: {os.path.expanduser('~/.cache/huggingface')}")

# Test embedding
test_sentence = "আমার ধানে পাতা দাগ পড়েছে"
embedding = model.encode(test_sentence)
print(f"✅ Embedding generated: shape {embedding.shape}")
EOF

python download_models.py
```

### Step 4: Install OCR & Barcode Dependencies

#### On Ubuntu/Debian (Docker):
```dockerfile
# Add to Dockerfile
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-ben \
    libzbar0 \
    libzbar-dev \
    && rm -rf /var/lib/apt/lists/*
```

#### On macOS:
```bash
brew install tesseract tesseract-lang
brew install zbar
```

#### On Windows:
```powershell
# Download Tesseract installer from:
# https://github.com/UB-Mannheim/tesseract/wiki
# Set environment variable:
# set TESSDATA_PREFIX=C:\Program Files\Tesseract-OCR\tessdata
```

### Step 5: Configure Environment Variables

```bash
# Copy and update .env
cp .env.example .env

# Add new variables (see section below)
cat >> .env << 'EOF'

# Phase 2: Vector Store
PGVECTOR_ENABLED=true

# Phase 2: Embedding Model
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

# Phase 2: SMS Service (mock or real)
SMS_PROVIDER=mock
NEXMO_API_KEY=${NEXMO_API_KEY_HERE}
NEXMO_API_SECRET=${NEXMO_API_SECRET_HERE}

# Phase 2: Government APIs (mocked initially)
GOVERNMENT_API_BARCODE=mock
BSTI_API_KEY=${BSTI_API_KEY_HERE}

# Phase 2: Emergency Services
HELPLINE_NUMBER=3331
HELPLINE_OPERATOR_PHONE=+8801700000000

# Phase 2: OCR Configuration
TESSERACT_CMD=/usr/bin/tesseract
TESSERACT_LANGUAGES=eng+ben

# Phase 2: AWS S3 (optional, for image storage)
AWS_S3_BUCKET=${AWS_S3_BUCKET_HERE}
AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID_HERE}
AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY_HERE}
EOF
```

### Step 6: Verify Installation

```bash
# Run verification script
python -c """
import sys
print('🔍 Verifying Phase 2 dependencies...')

try:
    import pgvector
    print('✅ pgvector')
except: 
    print('❌ pgvector')
    
try:
    import sentence_transformers
    print('✅ sentence-transformers')
except:
    print('❌ sentence-transformers')
    
try:
    import cv2
    print('✅ opencv-python')
except:
    print('❌ opencv-python')
    
try:
    import pytesseract
    print('✅ pytesseract')
except:
    print('❌ pytesseract')
    
try:
    import pyzbar
    print('✅ pyzbar')
except:
    print('❌ pyzbar')

print('\\n✅ Phase 2 dependencies ready!')
"""
```

---

## Configuration & Environment

### Backend Configuration Files to Create

#### 1. `backend/app/config/community_qa_data.json`
```json
{
  "seed_qa_pairs": [
    {
      "question": "টোমেটোতে লিফ কার্ল কেন হয় এবং এর সমাধান কি?",
      "question_en": "Why does tomato leaf curl occur and what is the solution?",
      "crop": "tomato",
      "stage": "flowering",
      "answer": "ভাইরাস দ্বারা সৃষ্ট এই রোগ। নিম তেল এবং মাল্টিভিট্যামিন স্প্রে করুন। আক্রান্ত গাছ তুলে ফেলুন।",
      "answer_en": "This virus-caused disease. Spray neem oil and multivitamin. Remove affected plants.",
      "answerer": "Dr. Karim (Extension Officer)",
      "upvotes": 42
    },
    {
      "question": "ধানের পাতা দাগ রোগের প্রতিরোধ ব্যবস্থা",
      "question_en": "Prevention measures for rice leaf spot disease",
      "crop": "rice",
      "stage": "vegetative",
      "answer": "বীজ শোধন করুন, আগাছা দূর করুন, জৈব সার ব্যবহার করুন।",
      "answer_en": "Treat seeds, remove weeds, use organic fertilizer.",
      "answerer": "Prof. Hasan (Soil Scientist)",
      "upvotes": 28
    }
    // ... 200+ Q&A pairs in actual implementation
  ]
}
```

#### 2. `backend/app/config/dealers_seed.json`
```json
{
  "seed_dealers": [
    {
      "name": "করিম এগ্রো সাপ্লাই",
      "phone": "+880171234567",
      "email": "karim.agro@example.com",
      "location": {"lat": 23.8103, "lon": 90.4125},
      "regions": ["Dhaka North"],
      "is_verified": true,
      "credentials": "BSTI Certified Dealer",
      "products": [
        {
          "product_name": "BARI ধান-২৮",
          "input_type": "seed",
          "crop": "rice",
          "batch": "BG-DAE-2024-001234",
          "price_bdt": 1200,
          "quantity": 50,
          "expiry": "2026-12-31"
        }
      ]
    }
    // ... 50+ dealers across Bangladesh
  ]
}
```

#### 3. `backend/app/config/verified_products.json`
```json
{
  "verified_products": [
    {
      "barcode": "EAN13-5901234123457",
      "product_name": "BARI ধান-২৮",
      "manufacturer": "BRRI (Bangladesh Rice Research Institute)",
      "batch": "BG-DAE-2024-001234",
      "active_ingredient": "N/A (Seed)",
      "npk_ratio": "N/A",
      "expiry": "2026-12-31",
      "government_registry": "DAE",
      "registered_at": "2024-01-15"
    },
    {
      "barcode": "EAN13-8901234567890",
      "product_name": "DAP সার",
      "manufacturer": "ACI Limited",
      "batch": "DAP-2024-567890",
      "active_ingredient": "Di-Ammonium Phosphate (18% N, 46% P2O5)",
      "npk_ratio": "18-46-0",
      "expiry": "2025-12-31",
      "government_registry": "BSTI",
      "registered_at": "2024-02-01"
    }
    // ... 200+ verified products
  ]
}
```

### Environment Variables (`backend/.env`)

```env
# PostgreSQL Vector & Geospatial
DATABASE_URL=postgresql://user:password@localhost:5432/krishi
PGVECTOR_ENABLED=true
PGVECTOR_SIMILARITY_THRESHOLD=0.7

# Embedding Model
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
EMBEDDING_BATCH_SIZE=32
EMBEDDING_CACHE_DIR=/app/models/embeddings

# SMS Service
SMS_PROVIDER=mock  # "mock" | "nexmo" | "vonage"
NEXMO_API_KEY=your_key_here
NEXMO_API_SECRET=your_secret_here

# Government APIs
GOVERNMENT_API_BARCODE=mock  # "mock" | "bsti_api"
BSTI_API_KEY=your_key_here
BSTI_API_ENDPOINT=https://api.bsti.gov.bd/verify-product

# Emergency Services
HELPLINE_NUMBER=3331
HELPLINE_OPERATOR_PHONE=+8801700000000

# OCR Configuration
TESSERACT_CMD=/usr/bin/tesseract
TESSERACT_LANGUAGES=eng+ben

# Geospatial
GEOSPATIAL_SEARCH_RADIUS_KM=15

# Optional: Image Storage
AWS_S3_BUCKET=krishi-bondhu-reports
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key_here
AWS_SECRET_ACCESS_KEY=your_secret_here

# Redis (optional for Celery tasks)
REDIS_URL=redis://localhost:6379

# Logging
LOG_LEVEL=DEBUG  # DEBUG | INFO | WARNING | ERROR
```

---

## Docker Configuration Updates

### Updated `backend/Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# System dependencies for Phase 2
RUN apt-get update && apt-get install -y \
    # OCR
    tesseract-ocr \
    tesseract-ocr-ben \
    libtesseract-dev \
    # Barcode
    libzbar0 \
    libzbar-dev \
    # PostgreSQL client
    postgresql-client \
    # PostGIS dependencies (if building from source)
    # libpq-dev \
    # Build tools
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app /app/app
COPY alembic /app/alembic

# Pre-download embedding model to speed up first run
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')"

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Updated `docker-compose.yml`

```yaml
version: '3.8'

services:
  postgres:
    image: postgis/postgis:16-3.3  # Updated for PostGIS support
    environment:
      POSTGRES_DB: krishi
      POSTGRES_USER: ${DB_USER:-krishi}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-krishi123}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      # Initialize pgvector extension
      - ./backend/docker/init-pgvector.sql:/docker-entrypoint-initdb.d/01-pgvector.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U krishi"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  backend:
    build:
      context: ./backend
      dockerfile: docker/Dockerfile
    environment:
      DATABASE_URL: postgresql://krishi:krishi123@postgres:5432/krishi
      REDIS_URL: redis://redis:6379
      SMS_PROVIDER: ${SMS_PROVIDER:-mock}
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app  # Hot reload during development
    command: >
      sh -c "alembic upgrade head &&
             uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "5173:5173"  # Vite dev server
    volumes:
      - ./frontend:/app
    environment:
      VITE_API_URL: http://localhost:8000

volumes:
  postgres_data:
  redis_data:

networks:
  default:
    name: krishi_network
```

### PostgreSQL Initialization Script (`backend/docker/init-pgvector.sql`)

```sql
-- This script runs automatically on first postgres startup
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Create initial indexes for performance
CREATE INDEX idx_vector_community_questions ON community_questions USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_geom_dealers ON dealers USING GIST (location_geom);

GRANT ALL PRIVILEGES ON DATABASE krishi TO krishi;
```

---

## Frontend Dependencies Updates

### `frontend/package.json` (New Dependencies)

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    
    // Phase 2: Barcode/QR scanning
    "jsqr": "^1.4.0",
    "html5-qrcode": "^2.3.3",
    
    // Phase 2: Offline capability (already present, update)
    "idb": "^7.1.1",
    
    // Phase 2: HTTP client (already present, but ensure latest)
    "axios": "^1.6.2",
    
    // Phase 2: Routing
    "react-router-dom": "^6.20.0"
  },
  "devDependencies": {
    "vite": "^5.0.0",
    "@vitejs/plugin-react": "^4.2.0"
  }
}
```

### Install Frontend Dependencies

```bash
cd frontend
npm install jsqr html5-qrcode idb axios react-router-dom
npm install  # Install all
```

---

## Project Scaffolding Checklist

### Backend Scaffolding

- [ ] Create new tool files:
  - `backend/app/tools/community_tools.py`
  - `backend/app/tools/marketplace_tools.py`
  - `backend/app/tools/emergency_tools.py`

- [ ] Create new endpoint files:
  - `backend/app/api/endpoints/community.py`
  - `backend/app/api/endpoints/marketplace.py`
  - `backend/app/api/endpoints/emergency.py`

- [ ] Create new service files:
  - `backend/app/services/sms_provider.py`
  - `backend/app/services/embedding_service.py`
  - `backend/app/services/ocr_service.py`
  - `backend/app/services/barcode_service.py`
  - `backend/app/services/geospatial_service.py`

- [ ] Create utility files:
  - `backend/app/utils/vector_utils.py`
  - `backend/app/utils/pdf_generator.py`

- [ ] Create config seed data:
  - `backend/app/config/community_qa_data.json`
  - `backend/app/config/dealers_seed.json`
  - `backend/app/config/verified_products.json`

- [ ] Create Alembic migrations:
  - `backend/alembic/versions/0007_add_pgvector_postgis.py`
  - `backend/alembic/versions/0008_community_qa_tables.py`
  - `backend/alembic/versions/0009_marketplace_tables.py`
  - `backend/alembic/versions/0010_emergency_tables.py`

- [ ] Create test files:
  - `backend/tests/test_embedding_service.py`
  - `backend/tests/test_community_qa.py`
  - `backend/tests/test_marketplace.py`
  - `backend/tests/test_emergency.py`

### Frontend Scaffolding

- [ ] Create component directories:
  - `frontend/src/components/Community/`
  - `frontend/src/components/Marketplace/`
  - `frontend/src/components/Emergency/`

- [ ] Create new components:
  - `Community/SearchQA.jsx`
  - `Community/AskQuestion.jsx`
  - `Marketplace/SearchDealers.jsx`
  - `Marketplace/BarcodeScanner.jsx`
  - `Emergency/ReportDamage.jsx`

- [ ] Create custom hooks:
  - `frontend/src/hooks/useEmbedding.js`
  - `frontend/src/hooks/useBarcodeScanner.js`
  - `frontend/src/hooks/useOfflineSync.js`

- [ ] Create API services:
  - `frontend/src/services/communityApi.js`
  - `frontend/src/services/marketplaceApi.js`
  - `frontend/src/services/emergencyApi.js`

### DevOps Scaffolding

- [ ] Update `docker-compose.yml` (postgis image, pgvector init)
- [ ] Create `backend/docker/init-pgvector.sql`
- [ ] Update `backend/Dockerfile` (tesseract, zbar)
- [ ] Update `.env.example` with Phase 2 variables

---

## Deployment Checklist

### Pre-Deployment Testing

```bash
# 1. PostgreSQL Extensions
psql -U krishi -d krishi -c "SELECT * FROM pg_extension WHERE extname IN ('vector', 'postgis');"

# 2. Python Dependencies
python -c "import sentence_transformers; import cv2; import pyzbar; import pytesseract; print('✅ All imports successful')"

# 3. Embedding Model
python << 'EOF'
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
test_embedding = model.encode("পরীক্ষা")
print(f"✅ Embedding shape: {test_embedding.shape}")
EOF

# 4. OCR Capability
python << 'EOF'
import pytesseract
from PIL import Image
print(f"✅ Tesseract version: {pytesseract.get_tesseract_version()}")
EOF

# 5. Barcode Scanning
python << 'EOF'
from pyzbar import pyzbar
print(f"✅ pyzbar version available: {pyzbar.__doc__}")
EOF
```

### Docker Build & Startup

```bash
# Build
docker-compose build

# Start services
docker-compose up -d

# Check health
docker-compose ps

# View logs
docker-compose logs -f backend

# Verify database extensions
docker-compose exec postgres psql -U krishi -d krishi -c "SELECT * FROM pg_extension;"

# Run migrations
docker-compose exec backend alembic upgrade head
```

### Load Seed Data

```bash
# Execute seeding script (to be created in Phase 3)
docker-compose exec backend python scripts/seed_data.py
```

---

## Summary & Next Steps

### Phase 2 Deliverables ✅
1. ✅ Technology stack finalized (pgvector + sentence-transformers + Tesseract)
2. ✅ New dependencies documented with rationale
3. ✅ Updated project structure with 15+ new files/directories
4. ✅ Installation & setup guide (step-by-step)
5. ✅ Environment configuration (all variables)
6. ✅ Docker updates (postgis image, pgvector init, tesseract install)
7. ✅ Deployment checklist

### Ready for Phase 3 ✅

**Phase 3 will implement:**
- Community Q&A agent + tools + endpoints
- Input Marketplace agent + tools + endpoints
- Emergency Response agent + tools + endpoints
- Database models (12 new tables via Alembic migrations)
- Seed data loading scripts
- API endpoints (11 total)

### Estimated Timeline
- Phase 3: 2-3 weeks (backend implementation)
- Phase 4: 1-2 weeks (frontend)
- Phase 5: 1 week (testing)
- Total: 4-6 weeks to full production deployment

---

**Document Generated:** May 2, 2026  
**Status:** ✅ Phase 2 Complete — Ready for Phase 3 Implementation  
**Next Action:** Approve tech stack and proceed with backend implementation
