# 🚀 Professional Vercel Deployment Guide for KrishiBondhu

## Overview

KrishiBondhu is a **monorepo project** with:
- **Frontend**: React + Vite (static site)
- **Backend**: FastAPI Python (serverless function)

Both will be deployed to Vercel separately for optimal performance and scalability.

---

## Pre-Deployment Checklist

- [x] GitHub repository connected
- [ ] Vercel account created (free tier: https://vercel.com/signup)
- [ ] Environment variables documented
- [ ] Database service set up (PostgreSQL or SQLite)

---

## Step 1: Deploy Backend API

### 1.1 Create Backend Project on Vercel

1. Go to **https://vercel.com/dashboard**
2. Click **"Add New"** → **"Project"**
3. Select your GitHub repository: `https://github.com/aminul01-g/krishi-bondhu`
4. When prompted, select **"Monorepo"** setup
5. Set **Root Directory** to: `backend`
6. Project Name: `krishi-bondhu-api`
7. Click **"Create"**

### 1.2 Add Environment Variables

In Vercel Dashboard:
1. Go to **krishi-bondhu-api** project
2. Navigate to **Settings** → **Environment Variables**
3. Add the following variables:

**For Production (PostgreSQL):**
```
DATABASE_URL = postgresql+psycopg2://user:password@host:5432/krishi_bondhu
GEMINI_API_KEY = your_gemini_api_key_here
PYTHON_VERSION = 3.11
UPLOAD_DIR = /tmp/uploads
```

**For Testing/Demo (SQLite):**
```
DATABASE_URL = sqlite:///./farmdb.db
GEMINI_API_KEY = your_gemini_api_key_here
PYTHON_VERSION = 3.11
UPLOAD_DIR = /tmp/uploads
```

### 1.3 Configure Build Settings

1. In Vercel Dashboard, go to **krishi-bondhu-api** → **Settings** → **Build & Development Settings**
2. Verify:
   - **Framework Preset**: None (Python/FastAPI)
   - **Build Command**: (should be auto-detected from `vercel.json`)
   - **Output Directory**: (leave blank)
   - **Install Command**: (leave blank)

### 1.4 Deploy Backend

1. Click the **"Deploy"** button
2. Wait for deployment to complete (5-10 minutes)
3. Backend URL will be: `https://krishi-bondhu-api.vercel.app`
4. Test endpoint: `https://krishi-bondhu-api.vercel.app/api/conversations`

**Expected Response:**
```json
[]
```
(Empty array is OK - no conversations yet)

---

## Step 2: Deploy Frontend

### 2.1 Create Frontend Project on Vercel

1. Go to **https://vercel.com/dashboard**
2. Click **"Add New"** → **"Project"**
3. Select the same GitHub repository
4. Set **Root Directory** to: `frontend`
5. Project Name: `krishi-bondhu` (or `krishi-bondhu-web`)
6. Click **"Create"**

### 2.2 Add Environment Variables

In Vercel Dashboard for **krishi-bondhu** project:
1. Navigate to **Settings** → **Environment Variables**
2. Add:

```
VITE_API_URL = https://krishi-bondhu-api.vercel.app
```

**Note**: Frontend will use this to connect to backend API

### 2.3 Configure Build Settings

Vercel should auto-detect Vite, but verify:
1. **Framework**: Vite
2. **Build Command**: `npm run build`
3. **Output Directory**: `dist`
4. **Install Command**: `npm install`

### 2.4 Deploy Frontend

1. Click the **"Deploy"** button
2. Wait for deployment (3-5 minutes)
3. Frontend URL will be: `https://krishi-bondhu.vercel.app`

---

## Step 3: Verify Deployment

### 3.1 Test Backend API

```bash
curl https://krishi-bondhu-api.vercel.app/api/conversations
```

Expected: `[]` (or list of conversations)

### 3.2 Test Frontend

1. Open **https://krishi-bondhu.vercel.app** in browser
2. Verify:
   - ✅ Page loads without errors
   - ✅ Voice input works
   - ✅ Camera input works
   - ✅ Chat input works
   - ✅ Conversations list shows data

### 3.3 Check Network Tab

Open DevTools (F12) → **Network** tab:
1. Send a message
2. Verify API calls go to `https://krishi-bondhu-api.vercel.app/api/*`
3. Check response status is 200 OK

---

## Troubleshooting Common Errors

### ❌ 502 Bad Gateway - Function Invocation Failed

**Cause**: Backend crashed or failed to start

**Solution**:
```bash
# Check logs
vercel logs krishi-bondhu-api --tail

# Look for:
1. Python import errors → missing packages in requirements-all.txt
2. Database connection errors → invalid DATABASE_URL
3. API key errors → missing GEMINI_API_KEY
```

**Fix**:
1. Update environment variable
2. Redeploy: Click **"Deployments"** → select failed deployment → **"Redeploy"**

---

### ❌ 404 Not Found

**Cause**: Wrong API endpoint or route not found

**Solution**:
1. Verify endpoint exists: `GET /api/conversations`
2. Check `backend/vercel.json` routes configuration
3. Ensure backend is responding

---

### ❌ CORS Errors

**Error**: `Access to XMLHttpRequest blocked by CORS policy`

**Solution**: Already configured in `backend/app/main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production: list specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

For **production**, update to:
```python
allow_origins=[
    "https://krishi-bondhu.vercel.app",
    "https://yourdomain.com"
]
```

---

### ❌ Database Connection Error

**Error**: `postgresql connection refused` or `Database not available`

**Solution**:
1. Verify `DATABASE_URL` format: `postgresql+psycopg2://user:password@host:port/dbname`
2. Ensure database is accessible from Vercel (not localhost)
3. Check firewall/security rules allow Vercel IPs
4. Test connection:
   ```bash
   psql postgresql://user:password@host:port/dbname
   ```

---

### ❌ Timeout (504 Gateway Timeout)

**Error**: Function takes >30 seconds

**Cause**: Long-running operation (audio processing, AI inference)

**Solution**:
1. Optimize processing code (already optimized in langgraph_app.py)
2. Use Vercel's Pro plan for 60-second timeout
3. For very long operations, use webhooks/queue system

---

### ❌ Environment Variable Not Found

**Error**: `KeyError: 'GEMINI_API_KEY'` or similar

**Solution**:
1. Verify environment variable is set in Vercel Dashboard
2. Re-deploy after adding variables
3. Check variable is in correct project (not root project)

---

## Performance Optimization

### 1. Enable Response Caching

Update `backend/app/api/routes.py`:
```python
from fastapi.responses import JSONResponse

@router.get("/conversations")
async def get_conversations(db: AsyncSession = Depends(get_db)):
    # ... code ...
    return JSONResponse(
        conversations,
        headers={"Cache-Control": "max-age=300, s-maxage=600"}
    )
```

### 2. Database Connection Pooling

Already configured in `backend/app/db.py`:
```python
engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
)
```

### 3. Frontend Asset Optimization

Vite automatically:
- Minifies code
- Code splitting
- Lazy loading

Enable compression in Vercel:
1. Dashboard → **krishi-bondhu** → **Settings** → **Compression** → Enable

---

## Monitoring & Logging

### 1. View Real-Time Logs

```bash
# Backend logs
vercel logs krishi-bondhu-api --tail

# Frontend logs
vercel logs krishi-bondhu --tail
```

### 2. Set Up Error Tracking

Install Sentry for error monitoring:

```bash
pip install sentry-sdk
```

Update `backend/app/main.py`:
```python
import sentry_sdk

sentry_sdk.init(
    dsn="your_sentry_dsn_here",
    environment="production"
)
```

### 3. Performance Monitoring

Use Vercel Analytics:
1. Dashboard → Project → **Analytics**
2. Monitor:
   - Response times
   - Request count
   - Error rates
   - Deployment size

---

## Custom Domain Setup (Optional)

### 1. Update DNS

1. In Vercel Dashboard → **Project Settings** → **Domains**
2. Add custom domain: `api.krishibondhu.com`
3. Update DNS records (Vercel shows instructions)

### 2. Update Frontend Config

Update `frontend/src/components/*.jsx`:
```javascript
const API_BASE = 'https://api.krishibondhu.com/api'
```

Or use environment variable:
```javascript
const API_BASE = import.meta.env.VITE_API_URL + '/api'
```

---

## Production Checklist

Before going live:

- [ ] Backend deployed and responding ✅
- [ ] Frontend deployed and loading ✅
- [ ] Environment variables configured ✅
- [ ] CORS properly configured ✅
- [ ] Database connection tested ✅
- [ ] API endpoints returning data ✅
- [ ] Error handling working ✅
- [ ] SSL/HTTPS enabled (automatic) ✅
- [ ] Monitoring/logging set up ✅
- [ ] Backup strategy in place ✅

---

## Rollback Strategy

If something goes wrong:

1. Go to Vercel Dashboard → **Deployments** tab
2. Find the last working deployment
3. Click **"..." menu** → **"Redeploy"**
4. Previous version will be restored within 1-2 minutes

---

## Database Setup Guides

### PostgreSQL on Railway.app (Free Tier)

1. Go to https://railway.app
2. Click "New Project"
3. Add PostgreSQL
4. Copy connection string
5. Add to Vercel as `DATABASE_URL`

### PostgreSQL on Supabase (Free Tier)

1. Go to https://supabase.com
2. Create new project
3. Go to **Settings** → **Database** → **URI**
4. Copy and add to Vercel

### Managed PostgreSQL on AWS RDS

Contact DevOps team or use terraform to set up.

---

## Scaling & Performance Tips

1. **Database Connection Pooling**: Use PgBouncer for PostgreSQL
2. **CDN**: Vercel automatically uses Vercel Edge Network
3. **Rate Limiting**: Consider using Vercel Rate Limiting API
4. **Caching Strategy**: Implement Redis for session management

---

## Support & Resources

- **Vercel Docs**: https://vercel.com/docs
- **FastAPI Deployment**: https://fastapi.tiangolo.com/deployment/
- **Vite Deployment**: https://vitejs.dev/guide/static-deploy.html
- **Python Runtime**: https://vercel.com/docs/concepts/functions/serverless-functions/runtimes/python
- **Vercel Support**: https://vercel.com/support

---

## Need Help?

1. **Check Logs**: `vercel logs <project-name> --tail`
2. **Verify Configuration**: Check `vercel.json` in each folder
3. **Test Locally**: Run `npm run dev` in frontend and backend separately
4. **Contact Support**: https://vercel.com/support

---

## Quick Reference

| Component | URL | Status |
|-----------|-----|--------|
| **Frontend** | https://krishi-bondhu.vercel.app | 🟢 |
| **Backend API** | https://krishi-bondhu-api.vercel.app | 🟢 |
| **GitHub Repository** | https://github.com/aminul01-g/krishi-bondhu | 🟢 |

---

**Last Updated**: November 18, 2025
**Deployment Type**: Vercel (Monorepo)
**Environment**: Production
