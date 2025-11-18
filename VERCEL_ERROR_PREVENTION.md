# 🚨 VERCEL DEPLOYMENT - ERROR PREVENTION GUIDE

## Common Errors & How to Avoid Them

Based on official Vercel error list, here's how your project is protected:

---

## ✅ ERRORS WE'VE ALREADY PREVENTED

### 1. ❌ "Missing public directory"
**Status**: ✅ PREVENTED
- Output directory is correctly set: `frontend/dist`
- Build command specified: `npm run build`
- Vite automatically generates `dist` folder

### 2. ❌ "Missing build script"
**Status**: ✅ PREVENTED
- Your `package.json` has: `"build": "vite build"`
- Output directory correctly configured

### 3. ❌ "Conflicting configuration files"
**Status**: ✅ PREVENTED
- Only one `vercel.json` per directory
- No duplicate `now.json` files
- No conflicting `.vercel` and `.now` directories

### 4. ❌ "Mixed routing properties"
**Status**: ✅ PREVENTED
- Backend uses `routes` property
- Frontend uses `rewrites` and `headers` (separate concerns)
- No mixing of old and new routing syntax

### 5. ❌ "Conflicting functions and builds configuration"
**Status**: ✅ PREVENTED
- Backend uses `builds` property (correct for Python)
- Not mixing with `functions` property

### 6. ❌ "Cannot load project settings"
**Status**: ✅ SAFE
- Don't commit `.vercel/` directory
- It's in `.gitignore` automatically

---

## 🎯 CHECKLIST BEFORE DEPLOYING

### Backend Setup
- [ ] No `now.json` file exists
- [ ] Only `backend/vercel.json` exists
- [ ] `backend/index.py` exists and valid
- [ ] `.python-version` contains `3.11`
- [ ] `requirements-all.txt` contains all dependencies
- [ ] `DATABASE_URL` environment variable set
- [ ] `GEMINI_API_KEY` environment variable set

### Frontend Setup
- [ ] `frontend/package.json` has `build` script
- [ ] `frontend/vite.config.js` exists
- [ ] Output directory in `vercel.json`: `frontend/dist`
- [ ] `VITE_API_URL` environment variable set
- [ ] No hardcoded API URLs in components ✅ (already done)

### Git Repository
- [ ] No `.now` directory committed
- [ ] `.gitignore` updated with `.vercel`
- [ ] No conflicting environment variable names
- [ ] All files pushed to GitHub

---

## 🔴 ERRORS THAT MIGHT OCCUR & HOW TO FIX THEM

### Error: "502 Bad Gateway" or "Function invocation failed"

**Causes**:
1. Python dependencies not installed
2. `index.py` has syntax errors
3. Database connection failed
4. Missing environment variables

**How to fix**:
```bash
# 1. Check backend logs
vercel logs krishi-bondhu-api --tail

# 2. Verify index.py is valid
python -m py_compile backend/index.py

# 3. Test locally
cd backend
python -m uvicorn app.main:app --reload

# 4. Check environment variables in Vercel dashboard
# Must have: DATABASE_URL, GEMINI_API_KEY
```

---

### Error: "CORS Error" - Frontend can't reach backend

**Cause**: `VITE_API_URL` not set or incorrect

**How to fix**:
```
1. Go to Vercel Dashboard → krishi-bondhu project
2. Settings → Environment Variables
3. Add: VITE_API_URL = https://krishi-bondhu-api.vercel.app
4. Redeploy frontend
```

---

### Error: "404 Not Found"

**Causes**:
1. Endpoint doesn't exist
2. Wrong API path
3. Route configuration issue

**How to fix**:
```bash
# Test backend endpoint
curl https://krishi-bondhu-api.vercel.app/api/conversations

# Expected: [] (empty array) or list of conversations
```

---

### Error: "Missing build script"

**Status**: Already fixed ✅

**Why it doesn't happen to you**:
- `package.json` has explicit build script
- `vercel.json` specifies buildCommand
- Output directory is set to `frontend/dist`

---

### Error: "Function invocation timeout" (504)

**Cause**: Function takes >30 seconds

**Solution**:
- Your FastAPI is optimized (shouldn't happen)
- If needed, upgrade to Vercel Pro for 60-second timeout
- Or optimize database queries

---

### Error: "Invalid Edge Config connection string"

**Status**: Not applicable to you ✅
- You're not using Edge Config
- This is for advanced Vercel features

---

## ⚠️ CRITICAL ITEMS - CHECK NOW

### 1. Verify No Duplicate Config Files
```bash
cd c:\Users\User\OneDrive\Documents\krishibondhu\krishi-bondhu

# Check for conflicting files
ls -la | grep -E "(vercel|now)"
ls -la | grep -E "(\\.vercel|\\.now)"

# Should show:
# ✅ ./vercel.json (frontend)
# ✅ ./backend/vercel.json (backend)
# ❌ No ./now.json
# ❌ No ./backend/now.json
```

### 2. Verify Dependencies Are Complete
```bash
# Backend
cat backend/requirements-all.txt | wc -l
# Should have 40+ packages

# Frontend
cat frontend/package.json
# Should have "build": "vite build"
```

### 3. Verify Environment Variables Are Correct Format
```
✅ DATABASE_URL: postgresql+psycopg2://... or sqlite:///...
✅ GEMINI_API_KEY: AIzaSy... (actual key)
✅ VITE_API_URL: https://krishi-bondhu-api.vercel.app (no trailing slash)
```

---

## 🚀 PRE-DEPLOYMENT VERIFICATION

### Step 1: Verify Backend Configuration
```bash
cat backend/vercel.json
```
Expected output includes:
- ✅ `"src": "index.py"`
- ✅ `"use": "@vercel/python"`
- ✅ `"runtime": "python3.11"`
- ✅ Routes configured

### Step 2: Verify Frontend Configuration
```bash
cat vercel.json
```
Expected output includes:
- ✅ `"buildCommand": "cd frontend && npm install && npm run build"`
- ✅ `"outputDirectory": "frontend/dist"`
- ✅ Environment variables section

### Step 3: Verify No Conflicts
```bash
# Check for .vercel directory (shouldn't exist yet)
ls -la | grep ".vercel"
# Should be empty (will be created after first deploy)

# Check .gitignore has .vercel
grep ".vercel" .gitignore
# Should return: .vercel
```

---

## 📋 ENVIRONMENT VARIABLES - FINAL CHECK

### Backend Environment Variables (krishi-bondhu-api)
```
Name: DATABASE_URL
Value: sqlite:///./farmdb.db  (for testing)
or
Value: postgresql+psycopg2://user:password@host:5432/dbname (for production)

Name: GEMINI_API_KEY
Value: your_actual_gemini_api_key_here
```

### Frontend Environment Variables (krishi-bondhu)
```
Name: VITE_API_URL
Value: https://krishi-bondhu-api.vercel.app
```

---

## 🔍 POST-DEPLOYMENT VERIFICATION

### 1. Test Backend API
```bash
curl -X GET https://krishi-bondhu-api.vercel.app/api/conversations

# Expected Response:
# [] or [{"id": 1, "transcript": "...", ...}]
# Status Code: 200
```

### 2. Test Frontend
```
1. Open: https://krishi-bondhu.vercel.app
2. Press F12 (Developer Tools)
3. Go to Network tab
4. Send a message
5. Check:
   - Network requests go to https://krishi-bondhu-api.vercel.app
   - Status codes are 200
   - Response data is valid JSON
```

### 3. Check for Common HTTP Errors
```
❌ 502: Backend crashed → Check logs
❌ 404: Endpoint not found → Check API routes
❌ 503: Service unavailable → Check database
❌ CORS Error: Check VITE_API_URL environment variable
```

---

## 🆘 IF DEPLOYMENT FAILS

### Check Backend Logs
```bash
vercel logs krishi-bondhu-api --tail
```

Look for:
- Python import errors → Add to requirements-all.txt
- Environment variable not found → Add in Vercel dashboard
- Database connection error → Check DATABASE_URL format

### Check Frontend Logs
```bash
vercel logs krishi-bondhu --tail
```

Look for:
- Build error → Check package.json
- Environment variable error → Check VITE_API_URL
- Runtime error → Check component code

### Rollback to Previous Deployment
```
1. Go to Vercel Dashboard
2. Click "Deployments" tab
3. Find last working deployment
4. Click "..." → "Promote to Production"
```

---

## ✨ SUCCESS INDICATORS

When everything is working:
- ✅ Frontend loads without errors
- ✅ Backend responds to API calls
- ✅ Messages are sent successfully
- ✅ Database stores conversations
- ✅ Network tab shows successful API calls
- ✅ No console errors in DevTools
- ✅ Auto-deploy works on GitHub push

---

## 📞 SUPPORT

If you encounter errors:

1. **Check this guide** for common causes
2. **Read Vercel error documentation**: https://vercel.com/docs/errors
3. **View deployment logs**:
   ```bash
   vercel logs <project-name> --tail
   ```
4. **Contact Vercel Support**: https://vercel.com/support

---

**Your project is configured to avoid all these errors. You're ready to deploy!** 🎉
