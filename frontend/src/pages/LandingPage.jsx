import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { LanguageSwitcher } from '../components/shared/LanguageSwitcher';

const FEATURES = [
  { icon: '🗨️', key: 'feature_chat' },
  { icon: '📊', key: 'feature_market' },
  { icon: '🔬', key: 'feature_disease' },
  { icon: '🎙️', key: 'feature_voice' },
  { icon: '📒', key: 'feature_diary' },
  { icon: '⛈️', key: 'feature_weather' },
];

const STEPS = [
  { num: '১', icon: '❓', key: 'how_step1' },
  { num: '২', icon: '🤖', key: 'how_step2' },
  { num: '৩', icon: '✅', key: 'how_step3' },
];

/* A lightweight, brand-colored farm scene — no image asset needed, so it stays
   crisp at any size and loads instantly on low bandwidth. */
function HeroArt({ className = '' }) {
  return (
    <svg viewBox="0 0 400 320" className={className} role="img" aria-hidden="true" fill="none">
      <defs>
        <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#EAF4EC" />
          <stop offset="1" stopColor="#FFFFFF" />
        </linearGradient>
        <linearGradient id="hill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#40916C" />
          <stop offset="1" stopColor="#2D6A4F" />
        </linearGradient>
      </defs>
      <rect width="400" height="320" rx="24" fill="url(#sky)" />
      {/* sun */}
      <circle cx="312" cy="78" r="34" fill="#E9C46A" />
      <circle cx="312" cy="78" r="46" fill="#D4A017" opacity="0.18" />
      {/* rolling fields */}
      <path d="M0 236 Q120 196 210 226 T400 214 V320 H0 Z" fill="#B7E4C7" opacity="0.7" />
      <path d="M0 262 Q140 228 250 256 T400 246 V320 H0 Z" fill="url(#hill)" />
      {/* furrow lines */}
      {[276, 290, 304].map((y, i) => (
        <path key={y} d={`M${10 + i * 6} ${y} Q200 ${y - 18} ${390 - i * 6} ${y}`} stroke="#1B4332" strokeOpacity="0.25" strokeWidth="2" />
      ))}
      {/* young plants */}
      {[70, 150, 232, 314].map((x, i) => (
        <g key={x} transform={`translate(${x} ${250 - (i % 2) * 6})`}>
          <path d="M0 0 C-2 -22 -14 -28 -18 -34 C-8 -32 -2 -24 0 -14 C2 -24 8 -32 18 -34 C14 -28 2 -22 0 0Z" fill="#52B788" />
          <line x1="0" y1="0" x2="0" y2="-16" stroke="#2D6A4F" strokeWidth="2.5" />
        </g>
      ))}
      {/* floating advice bubble */}
      <g transform="translate(214 70)">
        <rect x="0" y="0" width="150" height="58" rx="16" fill="#FFFFFF" stroke="#E5E2DB" />
        <circle cx="26" cy="29" r="12" fill="#2D6A4F" />
        <text x="26" y="34" textAnchor="middle" fontSize="14" fill="#fff">🌱</text>
        <rect x="46" y="18" width="86" height="8" rx="4" fill="#B7E4C7" />
        <rect x="46" y="33" width="60" height="8" rx="4" fill="#E5E2DB" />
      </g>
    </svg>
  );
}

export default function LandingPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-bg">
      {/* Sticky top bar */}
      <header className="sticky top-0 z-30 backdrop-blur bg-bg/80 border-b border-border/60">
        <div className="max-w-6xl mx-auto flex items-center justify-between px-4 sm:px-6 py-3">
          <div className="flex items-center gap-2">
            <span className="text-2xl">🌾</span>
            <span className="text-lg font-bold text-primary-dark">{t('app.name')}</span>
          </div>
          <div className="flex items-center gap-3">
            <LanguageSwitcher compact />
            <button
              onClick={() => navigate('/onboarding?mode=login')}
              className="text-sm font-semibold text-primary hover:text-primary-dark transition-colors"
            >
              {t('landing.login')}
            </button>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 pt-10 pb-14 md:pt-16 md:pb-20
                          grid md:grid-cols-2 gap-10 md:gap-8 items-center">
        <div className="text-center md:text-left animate-fade-up">
          <span className="badge-success mb-4 animate-fade-in">✨ {t('landing.badge')}</span>
          <h1 className="text-4xl sm:text-5xl font-extrabold text-primary-dark leading-[1.1] mt-4 mb-4">
            {t('landing.hero_title')}
          </h1>
          <p className="text-text-secondary text-base sm:text-lg max-w-md mx-auto md:mx-0 mb-8 leading-relaxed">
            {t('landing.hero_subtitle')}
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center md:justify-start">
            <button
              onClick={() => navigate('/onboarding')}
              className="btn-primary text-lg px-8 py-4 shadow-elevated
                         hover:shadow-lg transform hover:-translate-y-0.5 transition-all"
            >
              {t('landing.cta')} →
            </button>
            <button
              onClick={() => navigate('/onboarding?mode=login')}
              className="btn-outline text-lg px-8 py-4"
            >
              {t('landing.hero_secondary_cta')}
            </button>
          </div>
          <p className="text-xs text-text-secondary mt-5">🔒 {t('landing.trusted_by')}</p>
        </div>

        <div className="animate-fade-up delay-2">
          <HeroArt className="w-full max-w-md mx-auto drop-shadow-xl" />
        </div>
      </section>

      {/* Stats band */}
      <section className="brand-gradient text-white">
        <div className="dot-texture">
          <div className="max-w-4xl mx-auto grid grid-cols-3 gap-4 px-4 sm:px-6 py-8 text-center">
            {[1, 2, 3].map((n) => (
              <div key={n}>
                <div className="text-2xl sm:text-4xl font-extrabold">{t(`landing.stat_${n}_value`)}</div>
                <div className="text-xs sm:text-sm text-white/80 mt-1">{t(`landing.stat_${n}_label`)}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 py-14 md:py-20">
        <div className="text-center max-w-xl mx-auto mb-10">
          <h2 className="text-2xl sm:text-3xl font-bold text-primary-dark mb-2">{t('landing.features_title')}</h2>
          <p className="text-text-secondary">{t('landing.features_subtitle')}</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {FEATURES.map((f) => (
            <div key={f.key} className="feature-card">
              <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center text-2xl mb-3">
                {f.icon}
              </div>
              <h3 className="text-base font-semibold text-text-primary mb-1">{t(`landing.${f.key}`)}</h3>
              <p className="text-sm text-text-secondary leading-relaxed">{t(`landing.${f.key}_desc`)}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="bg-surface border-y border-border">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-14 md:py-20">
          <h2 className="text-2xl sm:text-3xl font-bold text-center text-primary-dark mb-12">
            {t('landing.how_title')}
          </h2>
          <div className="grid md:grid-cols-3 gap-8 md:gap-6">
            {STEPS.map((s, i) => (
              <div key={s.key} className="relative text-center md:px-4">
                <div className="w-16 h-16 mx-auto rounded-2xl bg-gradient-to-br from-primary to-primary-light
                                text-white flex items-center justify-center text-2xl font-bold shadow-card mb-4">
                  {s.icon}
                </div>
                <div className="text-xs font-bold text-accent mb-1">{s.num}</div>
                <h3 className="font-semibold text-text-primary mb-1">{t(`landing.${s.key}`)}</h3>
                <p className="text-sm text-text-secondary leading-relaxed max-w-xs mx-auto">
                  {t(`landing.${s.key}_desc`)}
                </p>
                {i < STEPS.length - 1 && (
                  <div className="hidden md:block absolute top-8 -right-3 text-2xl text-border">→</div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Testimonial */}
      <section className="max-w-3xl mx-auto px-4 sm:px-6 py-14 md:py-20 text-center">
        <div className="text-5xl text-accent leading-none mb-4">“</div>
        <blockquote className="text-lg sm:text-xl font-medium text-text-primary leading-relaxed mb-6">
          {t('landing.testimonial_quote')}
        </blockquote>
        <div className="flex items-center justify-center gap-3">
          <div className="w-11 h-11 rounded-full bg-primary/15 flex items-center justify-center text-lg">🧑‍🌾</div>
          <div className="text-left">
            <div className="font-semibold text-text-primary text-sm">{t('landing.testimonial_author')}</div>
            <div className="text-xs text-text-secondary">{t('landing.testimonial_role')}</div>
          </div>
        </div>
      </section>

      {/* CTA band */}
      <section className="brand-gradient text-white">
        <div className="dot-texture">
          <div className="max-w-3xl mx-auto px-4 sm:px-6 py-14 md:py-16 text-center">
            <h2 className="text-2xl sm:text-3xl font-bold mb-2">{t('landing.cta_band_title')}</h2>
            <p className="text-white/80 mb-7 max-w-md mx-auto">{t('landing.cta_band_subtitle')}</p>
            <button
              onClick={() => navigate('/onboarding')}
              className="bg-white text-primary-dark font-bold text-lg px-9 py-4 rounded-btn shadow-elevated
                         hover:bg-accent-light hover:text-primary-dark transform hover:-translate-y-0.5 transition-all"
            >
              {t('landing.cta')} →
            </button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-primary-dark text-white/80 px-4 sm:px-6 py-10">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="text-center sm:text-left">
            <div className="flex items-center justify-center sm:justify-start gap-2 mb-1">
              <span className="text-xl">🌾</span>
              <span className="font-bold text-white">{t('app.name')}</span>
            </div>
            <p className="text-white/50 text-xs">{t('landing.footer_tagline')}</p>
          </div>
          <div className="text-center sm:text-right text-sm">
            <a href="tel:16123" className="inline-flex items-center gap-2 font-semibold text-white hover:text-accent-light">
              📞 {t('landing.footer_helpline')}: 16123
            </a>
            <p className="text-white/40 text-xs mt-2">© 2026 KrishiBondhu. {t('landing.footer_rights')}</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
