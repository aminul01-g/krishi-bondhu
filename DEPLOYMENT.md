# Deployment Guide: KrishiBondhu

This guide will help you deploy KrishiBondhu with:
- **Frontend**: Vercel (Free tier)
- **Backend**: Railway (Free tier with $5 credit)
- **Database**: Railway PostgreSQL

---

## Prerequisites

1. **GitHub Account**: Push your code to GitHub first
2. **Vercel Account**: Sign up at https://vercel.com
3. **Railway Account**: Sign up at https://railway.app
4. **API Keys**: 
   - Google Gemini API key
   - Hugging Face API key (optional)

---

## Part 1: Deploy Backend to Railway

### Step 1: Create Railway Project

1. Go to https://railway.app
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Connect your GitHub account and select `krishi-bondhu` repository

### Step 2: Add PostgreSQL Database

1. In your Railway project, click **"+ New"**
2. Select **"Database"** → **"Add PostgreSQL"**
3. Railway will automatically create the database
4. Note: The `DATABASE_URL` environment variable is auto-configured

### Step 3: Configure Backend Service

1. Click on your backend service
2. Go to **"Settings"** → **"Environment Variables"**
3. Add the following variables:

```
GEMINI_API_KEY=your_gemini_api_key_here
HUGGINGFACE_API_KEY=your_hf_api_key_here
HUGGINGFACE_MODEL=meta-llama/Llama-3.2-3B-Instruct
LLM_PROVIDER=huggingface
STT_PROVIDER=gemini
TTS_PROVIDER=gtts
DEBUG=false
LOG_LEVEL=INFO
```

4. Railway will auto-detect your Dockerfile and deploy

### Step 4: Run Database Migrations

1. In Railway, go to your backend service
2. Click **"Deployments"** → Select latest deployment
3. Click **"View Logs"**
4. Once deployed, go to **"Settings"** → **"Networking"**
5. Note your backend URL (e.g., `https://krishi-bondhu-production.up.railway.app`)

To run migrations:
1. Install Railway CLI: `npm i -g @railway/cli`
2. Login: `railway login`
3. Link project: `railway link`
4. Run migrations: `railway run alembic upgrade head`

---

## Part 2: Deploy Frontend to Vercel

### Step 1: Update Frontend API URL

Before deploying, update your frontend to use the Railway backend URL:

**File**: `frontend/src/components/Recorder.jsx`, `Chatbot.jsx`, `ImageUpload.jsx`

Change:
```javascript
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'
```

To use environment variable in Vercel.

### Step 2: Create `.env.production` for Frontend

Create `frontend/.env.production`:
```
VITE_API_URL=https://your-backend.up.railway.app
```

### Step 3: Deploy to Vercel

1. Go to https://vercel.com/new
2. **Import Git Repository**: Select your `krishi-bondhu` repo
3. **Configure Project**:
   - **Framework Preset**: Vite
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`

4. **Environment Variables**:
   ```
   VITE_API_URL=https://your-backend.up.railway.app
   ```

5. Click **"Deploy"**

### Step 4: Configure Custom Domain (Optional)

1. In Vercel project settings → **"Domains"**
2. Add your custom domain
3. Update DNS records as instructed

---

## Part 3: Post-Deployment Configuration

### Update CORS in Backend

Update `backend/app/main.py` to allow your Vercel domain:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-app.vercel.app",
        "https://your-custom-domain.com",
        "http://localhost:5173"  # For local development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Commit and push changes - Railway will auto-deploy.

---

## Part 4: Verification

### Test Your Deployment

1. **Frontend**: Visit your Vercel URL
2. **Backend Health**: Visit `https://your-backend.railway.app/docs`
3. **Test Features**:
   - Voice recording
   - Image upload
   - Chat functionality
   - History management

### Monitor Logs

**Backend (Railway)**:
- Dashboard → Your Service → View Logs

**Frontend (Vercel)**:
- Dashboard → Your Project → Deployments → View Function Logs

---

## Troubleshooting

### Backend Issues

**Database Connection Error**:
```bash
# Check DATABASE_URL is set
railway variables

# Verify migrations ran
railway run alembic current
```

**API Key Errors**:
- Verify environment variables in Railway dashboard
- Check Gemini API quota at https://aistudio.google.com

### Frontend Issues

**API Not Connecting**:
- Verify `VITE_API_URL` matches Railway backend URL
- Check CORS settings in backend
- Use browser DevTools → Network tab to debug

**Build Failures**:
- Check `package.json` has all dependencies
- Verify Node version compatibility (use `engines` field)

---

## Cost Estimate

### Free Tier Limits

**Railway**:
- $5 free credit per month
- 500 hours of usage
- 512MB RAM, 1 vCPU
- Usually sufficient for ~5000-10000 requests/month

**Vercel**:
- 100GB bandwidth
- Unlimited sites
- Typically covers ~100,000 page views/month

**Gemini API**:
- Free tier: 20 requests/day
- Consider upgrading for production use

**HuggingFace**:
- Free tier: Rate-limited
- Serverless Inference API works well for moderate traffic

---

## Scaling Recommendations

### When to Upgrade

- **Railway**: Upgrade when you exceed 500 hours/month
- **Gemini**: Switch to paid tier or use HuggingFace exclusively
- **Database**: Enable connection pooling for high traffic

### Performance Optimization

1. **Enable Caching**:
   - Add Redis for session management
   - Cache common LLM responses

2. **Optimize Database**:
   - Add indexes on frequently queried columns
   - Enable query result caching

3. **Frontend CDN**:
   - Vercel automatically provides CDN
   - Optimize images and assets

---

## Environment Variables Summary

### Backend (Railway)
```
DATABASE_URL=<auto-configured by Railway>
GEMINI_API_KEY=<your key>
HUGGINGFACE_API_KEY=<your key>
HUGGINGFACE_MODEL=meta-llama/Llama-3.2-3B-Instruct
LLM_PROVIDER=huggingface
STT_PROVIDER=gemini
TTS_PROVIDER=gtts
PORT=<auto-configured by Railway>
DEBUG=false
```

### Frontend (Vercel)
```
VITE_API_URL=<your Railway backend URL>
```

---

## Next Steps After Deployment

1. **Set up monitoring**: Use Railway metrics + Vercel analytics
2. **Configure alerts**: Set up error notifications
3. **Enable authentication**: Add user login if needed
4. **Custom domain**: Point your domain to Vercel
5. **SSL certificates**: Automatically handled by both platforms

---

**Need Help?**
- Railway Docs: https://docs.railway.app
- Vercel Docs: https://vercel.com/docs
- Check deployment logs for specific errors
