# KrishiBondhu Frontend

> AI-powered agricultural assistant for Bangladeshi farmers — Mobile-first, bilingual (বাংলা/English), PWA-enabled React frontend.

## Tech Stack

| Technology | Purpose |
|---|---|
| React 18 | UI framework |
| Vite 5 | Build tool & dev server |
| Tailwind CSS 3 | Utility-first styling |
| React Router 6 | Client-side routing |
| i18next | Bilingual support (BN/EN) |
| Chart.js | Price trend visualizations |
| vite-plugin-pwa | Progressive Web App |
| idb | IndexedDB for offline queue |

## Project Structure

```
frontend/
├── index.html                 # Entry HTML with SEO meta
├── vite.config.js             # Vite + PWA + API proxy config
├── tailwind.config.js         # Design tokens (colors, fonts, shadows)
├── postcss.config.js          # PostCSS with Tailwind + Autoprefixer
├── package.json               # Dependencies & scripts
├── public/                    # PWA icons & manifest
│   ├── pwa-192x192.png
│   ├── pwa-512x512.png
│   └── manifest.json
└── src/
    ├── main.jsx               # React entry point
    ├── App.jsx                # Router with lazy-loaded pages
    ├── index.css              # Tailwind base + component classes
    ├── utils/
    │   └── i18n.js            # i18next configuration
    ├── locales/
    │   ├── bn.json            # Bengali translations (~80 keys)
    │   └── en.json            # English translations
    ├── contexts/
    │   └── AuthContext.jsx    # JWT auth state management
    ├── hooks/
    │   ├── useApi.js          # Generic data-fetch with AbortController
    │   ├── useOffline.js      # Online/offline detection
    │   └── useGeolocation.js  # GPS coordinates
    ├── services/
    │   └── api.js             # Central API layer (34 endpoint wrappers)
    ├── components/
    │   ├── layout/
    │   │   ├── AppLayout.jsx  # TopBar + BottomTabs + Outlet
    │   │   └── Navigation.jsx # TopBar, BottomTabBar, More menu
    │   └── shared/
    │       ├── ErrorBoundary.jsx
    │       ├── LanguageSwitcher.jsx
    │       ├── LoadingStates.jsx   # Spinner, Skeleton, EmptyState
    │       └── OfflineBanner.jsx
    └── pages/
        ├── LandingPage.jsx        # Public hero + features + footer
        ├── OnboardingPage.jsx     # Register/Login with district
        ├── ChatPage.jsx           # AI chat with voice + image
        ├── MarketPage.jsx         # Crop prices & advice
        ├── DiaryPage.jsx          # Farm diary & P/L report
        ├── TipsPage.jsx           # Daily tips & pest alerts
        ├── EmergencyPage.jsx      # Damage reports & helpline
        ├── SoilPage.jsx           # Soil image analysis
        ├── WaterPage.jsx          # Irrigation advice
        ├── FinancePage.jsx        # Subsidies, credit, insurance
        ├── CommunityPage.jsx      # Q&A forum
        ├── MarketplacePage.jsx    # Dealers & product verify
        ├── PlannerPage.jsx        # Season crop planner
        ├── TraceabilityPage.jsx   # Harvest batch tracking
        └── SustainabilityPage.jsx # Carbon score & markets
```

## Quick Start

### Prerequisites
- Node.js >= 18
- Backend running at `http://localhost:8000`

### Development
```bash
cd frontend
npm install
npm run dev
```
App runs at `http://localhost:5173`. API calls are proxied to `:8000` via Vite config.

### Production Build
```bash
npm run build
```
Output: `dist/` — static files ready for Nginx or FastAPI static mount.

### Preview Build
```bash
npm run preview
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `VITE_API_BASE` | `''` (empty) | Backend API base URL. In dev, Vite proxy handles `/api` → `:8000`. In production, set to your API domain. |

## Key Design Decisions

### Mobile-First PWA
- Optimized for 5-6 inch smartphones (primary user: Bangladeshi farmers)
- Bottom tab navigation with expandable "More" drawer for 8 advanced features
- Service worker with NetworkFirst for API, CacheFirst for static assets
- Installable as PWA with proper icons and manifest

### Bilingual Architecture
- Bengali (`bn`) is the default language
- All UI text uses `i18next` translation keys — no hardcoded strings
- Language choice persisted in `localStorage`
- Font stack: `Noto Sans Bengali` → `Inter` → system fonts

### API Integration
- Single service layer (`services/api.js`) with 34 endpoint wrappers
- JWT auth via `Authorization: Bearer` header, auto-injected
- `useApi` hook handles loading/error/abort lifecycle
- Offline detection via `useOffline` hook

### Authentication Flow
1. User registers at `/onboarding` → `POST /api/auth/register`
2. Auto-login → `POST /api/auth/token` → JWT stored in `localStorage`
3. Protected routes check token, redirect to onboarding if missing
4. `GET /api/auth/me` validates token on app load

### Color Palette
- Primary: `#2D6A4F` (deep green — growth, agriculture)
- Accent: `#D4A017` (golden — harvest, prosperity)
- Danger: `#E63946` (red — emergency, alerts)
- Background: `#F7F5F0` (warm off-white — earthy, natural)
