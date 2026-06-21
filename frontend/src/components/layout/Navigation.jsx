import { useTranslation } from 'react-i18next';
import { NavLink, useLocation } from 'react-router-dom';
import { LanguageSwitcher } from '../shared/LanguageSwitcher';
import { useAuth } from '../../contexts/AuthContext';

const PRIMARY_TABS = [
  { path: '/app/chat',      icon: '💬', labelBn: 'চ্যাট'  },
  { path: '/app/field',     icon: '🌾', labelBn: 'মাঠ'    },
  { path: '/app/market',    icon: '📈', labelBn: 'বাজার'  },
  { path: '/app/community', icon: '👥', labelBn: 'সমাজ'   },
  { path: '/app/profile',   icon: '👤', labelBn: 'আমি'    },
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
      field: 'nav.field', profile: 'nav.profile',
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
 * Mobile bottom tab navigation bar — exactly 5 primary tabs.
 */
export function BottomTabBar() {
  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-50 bg-surface/95 backdrop-blur-sm
                 border-t border-border"
      role="navigation"
      aria-label="Main navigation"
      style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
    >
      <div className="max-w-2xl mx-auto flex items-center justify-around py-1">
        {PRIMARY_TABS.map((tab) => (
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
            <span className="text-[10px] font-medium leading-tight">{tab.labelBn}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
