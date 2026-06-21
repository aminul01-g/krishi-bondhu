import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { AppLayout } from './components/layout/AppLayout';
import { LoadingScreen } from './components/shared/LoadingStates';
import { ErrorBoundary } from './components/shared/ErrorBoundary';

// Lazy-loaded pages for code splitting
const LandingPage = lazy(() => import('./pages/LandingPage'));
const OnboardingPage = lazy(() => import('./pages/OnboardingPage'));
const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const ChatPage = lazy(() => import('./pages/ChatPage'));
const MarketPage = lazy(() => import('./pages/MarketPage'));
const DiaryPage = lazy(() => import('./pages/DiaryPage'));
const TipsPage = lazy(() => import('./pages/TipsPage'));
const EmergencyPage = lazy(() => import('./pages/EmergencyPage'));
const SoilPage = lazy(() => import('./pages/SoilPage'));
const WaterPage = lazy(() => import('./pages/WaterPage'));
const FinancePage = lazy(() => import('./pages/FinancePage'));
const CommunityPage = lazy(() => import('./pages/CommunityPage'));
const MarketplacePage = lazy(() => import('./pages/MarketplacePage'));
const PlannerPage = lazy(() => import('./pages/PlannerPage'));
const TraceabilityPage = lazy(() => import('./pages/TraceabilityPage'));
const SustainabilityPage = lazy(() => import('./pages/SustainabilityPage'));
const FieldHubPage = lazy(() => import('./pages/FieldHubPage'));
const ProfileHubPage = lazy(() => import('./pages/ProfileHubPage'));

/**
 * Protected route wrapper — redirects to onboarding if not authenticated.
 */
function ProtectedRoute({ children }) {
  const { token, loading } = useAuth();
  if (loading) return <LoadingScreen />;
  if (!token) return <Navigate to="/onboarding" replace />;
  return children;
}

/**
 * Public route wrapper — redirects to app if already authenticated.
 */
function PublicRoute({ children }) {
  const { token, loading } = useAuth();
  if (loading) return <LoadingScreen />;
  if (token) return <Navigate to="/app/dashboard" replace />;
  return children;
}

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <AuthProvider>
          <Suspense fallback={<LoadingScreen />}>
            <Routes>
              {/* Public routes */}
              <Route path="/" element={<PublicRoute><LandingPage /></PublicRoute>} />
              <Route path="/onboarding" element={<PublicRoute><OnboardingPage /></PublicRoute>} />

              {/* Protected app routes */}
              <Route path="/app" element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
                <Route index element={<Navigate to="dashboard" replace />} />
                <Route path="dashboard" element={<DashboardPage />} />
                <Route path="chat" element={<ChatPage />} />
                <Route path="market" element={<MarketPage />} />
                <Route path="diary" element={<DiaryPage />} />
                <Route path="tips" element={<TipsPage />} />
                <Route path="emergency" element={<EmergencyPage />} />
                <Route path="soil" element={<SoilPage />} />
                <Route path="water" element={<WaterPage />} />
                <Route path="finance" element={<FinancePage />} />
                <Route path="community" element={<CommunityPage />} />
                <Route path="marketplace" element={<MarketplacePage />} />
                <Route path="planner" element={<PlannerPage />} />
                <Route path="traceability" element={<TraceabilityPage />} />
                <Route path="sustainability" element={<SustainabilityPage />} />
                <Route path="field" element={<FieldHubPage />} />
                <Route path="profile" element={<ProfileHubPage />} />
              </Route>

              {/* Catch-all */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </AuthProvider>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
