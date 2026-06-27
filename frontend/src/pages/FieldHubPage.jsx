import { useNavigate } from 'react-router-dom';
import { useEmergencyQueue } from '../hooks/useEmergencyQueue';

const FIELD_CARDS = [
  { emoji: '💧', labelBn: 'সেচ',        path: '/app/water' },
  { emoji: '🌱', labelBn: 'মাটি',       path: '/app/soil' },
  { emoji: '🚨', labelBn: 'জরুরি',      path: '/app/emergency', badgeKey: 'emergency' },
  { emoji: '📒', labelBn: 'ডায়েরি',    path: '/app/diary' },
  { emoji: '📅', labelBn: 'পরিকল্পনা', path: '/app/planner' },
  { emoji: '♻️', labelBn: 'টেকসই',     path: '/app/sustainability' },
];

/**
 * FieldHubPage — entry point for all farm-management tools.
 * Displays a 2×3 grid of large icon cards.
 */
export default function FieldHubPage() {
  const navigate = useNavigate();
  // Track offline-queued Emergency reports so a count badge can surface them.
  const { pendingCount } = useEmergencyQueue();

  return (
    <div className="min-h-[calc(100vh-8rem)] flex flex-col">
      {/* Section header */}
      <div className="mb-5">
        <p className="text-sm text-text-secondary">
          আপনার খামার পরিচালনার সমস্ত টুল এখানে পাবেন
        </p>
      </div>

      {/* 2-column grid of cards */}
      <div className="grid grid-cols-2 gap-4">
        {FIELD_CARDS.map((card) => {
          const badge =
            card.badgeKey === 'emergency' && pendingCount > 0 ? pendingCount : null;
          return (
          <button
            key={card.path}
            onClick={() => navigate(card.path)}
            className="relative flex flex-col items-center justify-center gap-3
                       bg-surface rounded-2xl px-4 py-7 shadow-card
                       hover:bg-primary/5 active:scale-95
                       transition-all duration-150 border border-border
                       focus:outline-none focus:ring-2 focus:ring-primary/40"
            aria-label={card.labelBn}
          >
            {badge != null && (
              <span
                className="absolute top-2 right-2 min-w-[22px] h-[22px] px-1
                           bg-danger text-white text-xs font-bold rounded-full
                           flex items-center justify-center shadow-card"
                aria-label={`${badge} টি স্থগিত রিপোর্ট`}
              >
                {badge}
              </span>
            )}
            <span style={{ fontSize: '3rem', lineHeight: 1 }} aria-hidden="true">
              {card.emoji}
            </span>
            <span className="text-base font-semibold text-text-primary text-center leading-snug">
              {card.labelBn}
            </span>
          </button>
          );
        })}
      </div>
    </div>
  );
}
