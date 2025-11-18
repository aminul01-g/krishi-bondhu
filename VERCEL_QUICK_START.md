# 🚀 VERCEL DEPLOYMENT - QUICK START

## What I've Prepared For You

✅ **Vercel Configuration Files Created**:
- `backend/vercel.json` - Backend API configuration
- `frontend/vite.config.js` - Frontend Vite configuration
- `backend/.python-version` - Python 3.11 specification
- `backend/index.py` - Vercel entry point

✅ **Environment Variable Support Added**:
- All frontend components now use `VITE_API_URL` environment variable
- Fallback to `http://localhost:8001/api` for local development
- Production ready with zero hardcoded values

✅ **Documentation**:
- `VERCEL_DEPLOYMENT_GUIDE.md` - Complete professional guide
- `DEPLOYMENT.md` - Overview and troubleshooting

---

## 3-Step Deployment Process

### Step 1: Connect Backend (5-10 minutes)

1. Go to https://vercel.com/dashboard
2. Click "Add New" → "Project"
3. Select your GitHub repo
4. Choose **Monorepo** setup
5. Root Directory: `backend`
6. Project Name: `krishi-bondhu-api`
7. Add Environment Variables:
   ```
   DATABASE_URL = sqlite:///./farmdb.db  (or PostgreSQL URL)
   GEMINI_API_KEY = your_api_key_here
   PYTHON_VERSION = 3.11
   UPLOAD_DIR = /tmp/uploads
   ```
8. Click **Deploy**
9. **Backend URL**: `https://krishi-bondhu-api.vercel.app`

---

### Step 2: Connect Frontend (3-5 minutes)

1. In Vercel Dashboard, click "Add New" → "Project"
2. Select same GitHub repo again
3. Choose **Monorepo** setup
4. Root Directory: `frontend`
5. Project Name: `krishi-bondhu`
6. Add Environment Variable:
   ```
   VITE_API_URL = https://krishi-bondhu-api.vercel.app
   ```
7. Click **Deploy**
8. **Frontend URL**: `https://krishi-bondhu.vercel.app`

---

### Step 3: Verify Deployment (2 minutes)

1. Test Backend:
   ```bash
   curl https://krishi-bondhu-api.vercel.app/api/conversations
   ```
   Expected: `[]` or list of conversations

2. Test Frontend:
   - Open: https://krishi-bondhu.vercel.app
   - Try: Voice input, Camera, Chat
   - Check: Network tab shows API calls to backend

---

## Troubleshooting Quick Links

| Error | Cause | Solution |
|-------|-------|----------|
| 502 Bad Gateway | Backend crashed | Check logs: `vercel logs krishi-bondhu-api --tail` |
| 404 Not Found | Wrong endpoint | Verify `/api/conversations` exists |
| CORS Error | Frontend can't reach backend | Check `VITE_API_URL` environment variable |
| Database Error | Invalid connection string | Verify `DATABASE_URL` format |
| Timeout | Function >30 seconds | Use Vercel Pro for 60s timeout |

---

## Environment Variables Needed

**Backend (krishi-bondhu-api)**:
```
DATABASE_URL = postgresql+psycopg2://user:password@host/dbname
              or
              sqlite:///./farmdb.db

GEMINI_API_KEY = your_gemini_api_key
PYTHON_VERSION = 3.11
UPLOAD_DIR = /tmp/uploads
```

**Frontend (krishi-bondhu)**:
```
VITE_API_URL = https://krishi-bondhu-api.vercel.app
```

---

## Database Options

### SQLite (Free, Testing):
```
DATABASE_URL = sqlite:///./farmdb.db
```

### PostgreSQL (Production):
**Option 1**: Railway.app
```
1. Go to railway.app
2. Create PostgreSQL database
3. Copy connection string to DATABASE_URL
```

**Option 2**: Supabase
```
1. Go to supabase.com
2. Create project → Get URI
3. Copy to DATABASE_URL
```

---

## What's Already Done ✅

- [x] Vercel configuration files created
- [x] Environment variables integrated
- [x] Frontend components updated for production
- [x] Database migration support added
- [x] CORS configured
- [x] Error handling implemented
- [x] GitHub push completed
- [x] Documentation created

## What You Need To Do

1. ⬜ Sign up for Vercel: https://vercel.com/signup
2. ⬜ Deploy Backend (follow Step 1 above)
3. ⬜ Deploy Frontend (follow Step 2 above)
4. ⬜ Test deployment (follow Step 3 above)

---

## Support

- Full guide: See `VERCEL_DEPLOYMENT_GUIDE.md`
- Troubleshooting: See `DEPLOYMENT.md`
- Questions: Check Vercel docs at https://vercel.com/docs

---

## Key Files Reference

```
krishi-bondhu/
├── backend/
│   ├── vercel.json          ← Backend config
│   ├── index.py             ← Entry point
│   ├── .python-version      ← Python 3.11
│   ├── app/main.py          ← FastAPI app
│   └── requirements-all.txt ← Dependencies
├── frontend/
│   ├── vercel.json          ← Frontend config
│   ├── vite.config.js       ← Vite config
│   ├── src/App.jsx          ← Updated with env vars
│   └── src/components/      ← Updated with env vars
├── VERCEL_DEPLOYMENT_GUIDE.md
├── DEPLOYMENT.md
└── README.md
```

---

**Your project is ready for professional Vercel deployment!** 🎉

Next: Follow the 3-Step Deployment Process above →
