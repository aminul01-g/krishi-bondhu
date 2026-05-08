import { Outlet } from 'react-router-dom';
import { TopBar, BottomTabBar } from './Navigation';
import { OfflineBanner } from '../shared/OfflineBanner';
import { ErrorBoundary } from '../shared/ErrorBoundary';

/**
 * Main app layout with top bar, bottom tabs, and page outlet.
 */
export function AppLayout() {
  return (
    <div className="min-h-screen bg-bg">
      <OfflineBanner />
      <TopBar />
      <main className="page-container">
        <ErrorBoundary>
          <Outlet />
        </ErrorBoundary>
      </main>
      <BottomTabBar />
    </div>
  );
}
