# KrishiBondhu Production Deployment Guide

This document provides the necessary steps to deploy KrishiBondhu in a production environment, focusing on the critical system-level dependencies required for AI Vision and Geospatial Intelligence.

## 🛠 System Requirements

### 1. Database: PostgreSQL with PostGIS
KrishiBondhu requires PostgreSQL with the PostGIS extension for distance-based expert matching and location-aware services.

**Installation (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install -y postgresql postgresql-contrib postgis
```

**Database Initialization:**
After starting PostgreSQL, run the following as the superuser:
```sql
CREATE DATABASE farmdb;
\c farmdb;
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;
```

### 2. AI Vision: Tesseract OCR
The label scanning feature depends on the Tesseract OCR engine.

**Installation:**
```bash
sudo apt-get install -y tesseract-ocr
# Install Bengali and English language packs for multi-lingual support
sudo apt-get install -y tesseract-ocr-ben tesseract-ocr-eng
```

**Environment Variables:**
Ensure the following are set in your `.env` file:
- `TESSERACT_CMD=/usr/bin/tesseract`
- `TESSERACT_LANGUAGES=eng+ben`

### 3. Barcode Scanning: ZBar
Product authenticity verification requires the ZBar library for decoding barcodes and QR codes.

**Installation:**
```bash
sudo apt-get install -y libzbar0
```

---

## 🚀 Deployment Steps

### Option A: Docker Compose (Recommended)
The project includes a `docker-compose.yml` that orchestrates the API and Database.

1. **Configure Environment**: Update `.env` with production API keys (Gemini/Groq).
2. **Launch**:
   ```bash
   docker-compose up -d --build
   ```
3. **Initialize Data**: Run the expert seeding script to enable geospatial matching:
   ```bash
   docker exec -it krishi-backend python3 backend/scripts/seed_experts.py
   ```

### Option B: Manual Linux Deployment
1. **Backend Setup**:
   ```bash
   cd backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Frontend Build**:
   ```bash
   cd frontend
   npm install
   npm run build
   ```
3. **Run Server**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

## 🧪 Verification Checklist
- [ ] **DB**: Run `SELECT postgis_full_version();` to verify PostGIS.
- [ ] **OCR**: Upload a fertilizer label to the Chatbot; verify the agent extracts NPK ratios.
- [ ] **Barcode**: Scan a product barcode in the Marketplace; verify it hits the `/api/marketplace/scan` endpoint.
- [ ] **Experts**: In Community QA, click "Connect with Expert" and verify a record is created in the `escalation_queue` table.
