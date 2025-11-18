# KrishiBondhu - Vercel Deployment Guide

## Professional Deployment Strategy

This project is a **monorepo** with:
- **Frontend**: React + Vite (deployed to Vercel)
- **Backend**: FastAPI Python (deployed to Vercel with Python Runtime)

### Prerequisites
1. GitHub account with the repository connected
2. Vercel account (free tier supports this)
3. Environment variables configured

---

## Deployment Steps

### Step 1: Deploy Backend API

#### 1a. Create Backend Project
1. Go to [vercel.com](https://vercel.com)
2. Click "Add New" → "Project"
3. Select your GitHub repository
4. Choose "As a monorepo"
5. Set the Root Directory to `backend`
6. Name it: `krishi-bondhu-api`

#### 1b. Configure Environment Variables
In Vercel dashboard → Project Settings → Environment Variables, add:

```
DATABASE_URL = postgresql+psycopg2://user:password@host/dbname
GEMINI_API_KEY = your_gemini_api_key_here
PYTHON_VERSION = 3.11
```

**For Development/Testing:**
```
DATABASE_URL = sqlite:///./farmdb.db
GEMINI_API_KEY = your_gemini_key
```

#### 1c. Configure Build Settings
- **Build Command**: `pip install -r requirements-all.txt`
- **Output Directory**: (leave empty)
- **Install Command**: (leave empty)

#### 1d. Deploy
Click "Deploy" and wait for completion. Your backend will be at:
```
https://krishi-bondhu-api.vercel.app
```

---

### Step 2: Deploy Frontend

#### 2a. Create Frontend Project
1. Click "Add New" → "Project" in Vercel
2. Select your GitHub repository again
3. Set Root Directory to `frontend`
4. Name it: `krishi-bondhu`

#### 2b. Configure Environment Variables
```
VITE_API_URL = https://krishi-bondhu-api.vercel.app
```

#### 2c. Configure Build Settings
- **Framework**: Vite
- **Build Command**: `npm run build`
- **Output Directory**: `dist`
- **Install Command**: `npm install`

#### 2d. Deploy
Click "Deploy". Your frontend will be at:
```
https://krishi-bondhu.vercel.app
```

---

## Post-Deployment Configuration

### 1. Update Frontend API Endpoint
After deployment, update the API base URL in frontend components to use the backend URL.

File: `frontend/src/components/*.jsx`
```javascript
const API_BASE = process.env.VITE_API_URL + '/api'
// or
const API_BASE = 'https://krishi-bondhu-api.vercel.app/api'
```

### 2. Enable CORS
The backend already has CORS enabled for all origins. For production, update:

File: `backend/app/main.py`
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://krishi-bondhu.vercel.app",
        "http://localhost:5173",
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 3. Database Setup

#### Option A: Using PostgreSQL (Recommended for Production)
1. Set up PostgreSQL database (e.g., via Railway, Supabase, or PlanetScale)
2. Update `DATABASE_URL` environment variable
3. Run migrations via Vercel CLI:
   ```bash
   vercel env pull
   python -m alembic upgrade head
   ```

#### Option B: Using SQLite (Development)
- Database file will be created automatically at `./farmdb.db`
- Note: File-based databases may not persist on Vercel's ephemeral filesystem

---

## Troubleshooting Common Errors

### 502 - FUNCTION_INVOCATION_FAILED
**Cause**: Backend failed to start
**Solution**:
1. Check logs: `vercel logs krishi-bondhu-api`
2. Verify all dependencies in `requirements-all.txt`
3. Ensure Python version is 3.11 or compatible

### 404 - NOT_FOUND
**Cause**: Route not found
**Solution**:
1. Verify API endpoints exist: `GET /api/conversations`
2. Check `vercel.json` rewrites configuration

### 500 - INTERNAL_FUNCTION_INVOCATION_FAILED
**Cause**: Database connection error
**Solution**:
1. Verify `DATABASE_URL` environment variable is set
2. Check database connection string format
3. Ensure database is accessible from Vercel's servers

### CORS Errors
**Solution**: Update allowed origins in `backend/app/main.py`

---

## Performance Optimization

### 1. Database Connection Pooling
Add to `backend/app/db.py`:
```python
engine = create_async_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True
)
```

### 2. Frontend Asset Optimization
- Vite automatically optimizes assets
- Enable gzip compression in Vercel

### 3. API Response Caching
Add to relevant endpoints:
```python
from fastapi.responses import JSONResponse

@router.get("/conversations")
async def get_conversations(db: AsyncSession = Depends(get_db)):
    # ... your code
    return JSONResponse(conversations, headers={"Cache-Control": "max-age=300"})
```

---

## Monitoring & Debugging

### View Logs
```bash
vercel logs krishi-bondhu-api --tail
vercel logs krishi-bondhu --tail
```

### Real-time Monitoring
- Use Vercel Dashboard for deployment status
- Check Application Performance Monitoring (APM)

### Set Up Error Tracking
Consider integrating Sentry for error tracking:
```bash
pip install sentry-sdk
```

---

## Production Checklist

- [ ] Backend deployed and responding at `/api/health`
- [ ] Frontend deployed and loading
- [ ] Environment variables configured
- [ ] CORS properly configured
- [ ] Database connection tested
- [ ] API endpoints returning correct data
- [ ] Error handling working
- [ ] SSL/HTTPS enabled (automatic with Vercel)
- [ ] Custom domain configured (optional)
- [ ] Monitoring and logging set up

---

## Custom Domain Setup (Optional)

1. In Vercel Dashboard → Project Settings → Domains
2. Add your custom domain
3. Update DNS records (Vercel provides instructions)
4. Update CORS allowed origins with new domain

---

## Rollback Strategy

If deployment fails:
1. Go to Vercel Dashboard → Project
2. Click "Deployments"
3. Select previous working deployment
4. Click "Redeploy"

---

## Support & Resources

- [Vercel Docs](https://vercel.com/docs)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/concepts/)
- [React + Vite Deployment](https://vitejs.dev/guide/static-deploy.html)

