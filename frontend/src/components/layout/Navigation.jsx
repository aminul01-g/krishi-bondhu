import { useTranslation } from 'react-i18next';
import { NavLink, useLocation } from 'react-router-dom';
import { useState } from 'react';
import { LanguageSwitcher } from '../shared/LanguageSwitcher';
import { useAuth } from '../../contexts/AuthContext';

const TABS = [
  { path: '/app/chat', icon: '🗨️', key: 'nav.chat' },
  { path: '/app/market', icon: '🌾', key: 'nav.market' },
  { path: '/app/diary', icon: '📒', key: 'nav.diary' },
  { path: '/app/tips', icon: '💡', key: 'nav.tips' },
  { path: '/app/emergency', icon: '🏥', key: 'nav.emergency' },
];

const MORE_ITEMS = [
  { path: '/app/soil', icon: '🔬', key: 'nav.soil' },
  { path: '/app/water', icon: '💧', key: 'nav.water' },
  { path: '/app/finance', icon: '💰', key: 'nav.finance' },
  { path: '/app/community', icon: '🤝', key: 'nav.community' },
  { path: '/app/marketplace', icon: '🏪', key: 'nav.marketplace' },
  { path: '/app/planner', icon: '📋', key: 'nav.planner' },
  { path: '/app/traceability', icon: '🔗', key: 'nav.traceability' },
  { path: '/app/sustainability', icon: '🌿', key: 'nav.sustainability' },
];

/**
 * Top header bar with app name, language toggle, and profile info.
 */
export function TopBar() {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const location = useLocation();

  const getCurrentTitle = () => {
    const path = location.pathname.split('/').pop();
    const titleMap = {
      chat: 'chat.title', market: 'market.title', diary: 'diary.title',
      tips: 'tips.title', emergency: 'emergency.title', soil: 'nav.soil',
      water: 'nav.water', finance: 'nav.finance', community: 'nav.community',
      marketplace: 'nav.marketplace', planner: 'nav.planner',
      traceability: 'nav.traceability', sustainability: 'nav.sustainability',
    };
    return t(titleMap[path] || 'app.name');
  };

  return (
    <header className="sticky top-0 z-40 bg-surface/95 backdrop-blur-sm border-b border-border">
      <div className="max-w-2xl mx-auto flex items-center justify-between px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="text-2xl">🌾</span>
          <h1 className="text-lg font-bold text-primary-dark truncate">
            {getCurrentTitle()}
          </h1>
        </div>
        <div className="flex items-center gap-2">
          <LanguageSwitcher compact />
          {user && (
            <button
              onClick={logout}
              className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center
                         text-sm font-bold text-primary hover:bg-primary/20 transition-all"
              title={user.username}
              aria-label="Logout"
            >
              {user.username?.charAt(0).toUpperCase() || '?'}
            </button>
          )}
        </div>
      </div>
    </header>
  );
}

/**
 * Mobile bottom tab navigation bar with expandable "More" menu.
 */
export function BottomTabBar() {
  const { t } = useTranslation();
  const [showMore, setShowMore] = useState(false);
  const location = useLocation();

  // Highlight "More" if current route is in the MORE_ITEMS
  const isMoreActive = MORE_ITEMS.some((item) => location.pathname.startsWith(item.path));

  return (
    <>
      {/* More menu overlay */}
      {showMore && (
        <div className="fixed inset-0 z-40" onClick={() => setShowMore(false)}>
          <div className="absolute inset-0 bg-black/30 backdrop-blur-[2px]" />
          <div
            className="absolute bottom-16 left-2 right-2 max-w-2xl mx-auto
                       bg-surface rounded-card shadow-elevated p-3
                       animate-in slide-in-from-bottom-5 duration-200"
            onClick={(e) => e.stopPropagation()}
          >
            <p className="text-xs font-semibold text-text-secondary uppercase tracking-wide px-2 mb-2">
              {t('nav.more')}
            </p>
            <div className="grid grid-cols-4 gap-1">
              {MORE_ITEMS.map((item) => (
                <NavLink
                  key={item.path}
                  to={item.path}
                  onClick={() => setShowMore(false)}
                  className={({ isActive }) =>
                    `flex flex-col items-center gap-1 py-3 px-1 rounded-lg transition-all
                     ${isActive
                       ? 'bg-primary/10 text-primary'
                       : 'text-text-secondary hover:bg-bg hover:text-primary'}`
                  }
                >
                  <span className="text-2xl leading-none">{item.icon}</span>
                  <span className="text-[10px] font-medium leading-tight text-center">
                    {t(item.key)}
                  </span>
                </NavLink>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Bottom tab bar */}
      <nav
        className="fixed bottom-0 left-0 right-0 z-50 bg-surface/95 backdrop-blur-sm
                   border-t border-border"
        role="navigation"
        aria-label="Main navigation"
        style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
      >
        <div className="max-w-2xl mx-auto flex items-center justify-around py-1">
          {TABS.map((tab) => (
            <NavLink
              key={tab.path}
              to={tab.path}
              className={({ isActive }) =>
                `flex flex-col items-center gap-0.5 py-2 px-3 rounded-lg transition-all min-w-[52px]
                 ${isActive
                   ? 'text-primary bg-primary/10'
                   : 'text-text-secondary hover:text-primary'}`
              }
            >
              <span className="text-xl leading-none">{tab.icon}</span>
              <span className="text-[10px] font-medium leading-tight">{t(tab.key)}</span>
            </NavLink>
          ))}

          {/* More button */}
          <button
            onClick={() => setShowMore(!showMore)}
            className={`flex flex-col items-center gap-0.5 py-2 px-3 rounded-lg transition-all min-w-[52px]
              ${isMoreActive || showMore
                ? 'text-primary bg-primary/10'
                : 'text-text-secondary hover:text-primary'}`}
          >
            <span className="text-xl leading-none">☰</span>
            <span className="text-[10px] font-medium leading-tight">{t('nav.more')}</span>
          </button>
        </div>
      </nav>
    </>
  );
}
