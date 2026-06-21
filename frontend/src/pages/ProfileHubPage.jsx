import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const APP_VERSION = '1.0.0';

const PROFILE_LINKS = [
  { emoji: '🏪', labelBn: 'মার্কেটপ্লেস',   path: '/app/marketplace' },
  { emoji: '🔗', labelBn: 'ট্রেসেবিলিটি',   path: '/app/traceability' },
  { emoji: '💡', labelBn: 'পরামর্শ ও টিপস', path: '/app/tips' },
];

/**
 * ProfileHubPage — farmer profile card plus links to secondary features.
 */
export default function ProfileHubPage() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const district = localStorage.getItem('kb_district') || '—';
  const initials = user?.username?.charAt(0).toUpperCase() || '?';

  return (
    <div className="min-h-[calc(100vh-8rem)] flex flex-col gap-5">

      {/* ── Farmer profile card ── */}
      <div className="bg-surface rounded-2xl shadow-card border border-border p-5">
        <div className="flex items-center gap-4">
          {/* Avatar circle */}
          <div
            className="w-16 h-16 rounded-full bg-gradient-to-br from-primary to-accent
                       flex items-center justify-center text-2xl font-bold text-white
                       shadow-card flex-shrink-0"
          >
            {initials}
          </div>

          <div className="flex-1 min-w-0">
            <h2 className="text-base font-bold text-text-primary truncate">
              {user?.username || 'কৃষক'}
            </h2>
            <p className="text-sm text-text-secondary mt-0.5">
              📍 {district}
            </p>
            <p className="text-xs text-text-secondary mt-0.5">
              🌾 ধান, পাট, সবজি
            </p>
          </div>

          {/* Edit button */}
          <button
            id="profile-edit-btn"
            onClick={() => navigate('/onboarding?mode=login')}
            className="w-9 h-9 rounded-full bg-primary/10 flex items-center justify-center
                       text-primary hover:bg-primary/20 transition-all flex-shrink-0"
            title="প্রোফাইল সম্পাদনা"
            aria-label="প্রোফাইল সম্পাদনা"
          >
            ✏️
          </button>
        </div>
      </div>

      {/* ── Quick links ── */}
      <div className="bg-surface rounded-2xl shadow-card border border-border divide-y divide-border overflow-hidden">
        {PROFILE_LINKS.map((link) => (
          <button
            key={link.path}
            id={`profile-link-${link.path.split('/').pop()}`}
            onClick={() => navigate(link.path)}
            className="w-full flex items-center gap-4 px-5 py-4
                       hover:bg-primary/5 active:bg-primary/10 transition-all text-left"
          >
            <span className="text-2xl leading-none">{link.emoji}</span>
            <span className="text-sm font-medium text-text-primary">{link.labelBn}</span>
            <span className="ml-auto text-text-secondary text-sm">›</span>
          </button>
        ))}
      </div>

      {/* ── App info + logout ── */}
      <div className="bg-surface rounded-2xl shadow-card border border-border divide-y divide-border overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4">
          <span className="text-sm text-text-secondary">অ্যাপ সংস্করণ</span>
          <span className="text-sm font-medium text-text-primary">v{APP_VERSION}</span>
        </div>

        <button
          id="profile-logout-btn"
          onClick={logout}
          className="w-full flex items-center gap-4 px-5 py-4
                     hover:bg-danger-light/40 active:bg-danger-light transition-all text-left"
        >
          <span className="text-2xl leading-none">🚪</span>
          <span className="text-sm font-semibold text-danger">লগআউট</span>
        </button>
      </div>

    </div>
  );
}
