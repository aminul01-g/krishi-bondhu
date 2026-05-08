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

export default function LandingPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-bg">
      {/* Top bar */}
      <header className="flex items-center justify-between px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="text-2xl">🌾</span>
          <span className="text-lg font-bold text-primary-dark">{t('app.name')}</span>
        </div>
        <div className="flex items-center gap-2">
          <LanguageSwitcher compact />
          <button
            onClick={() => navigate('/onboarding?mode=login')}
            className="text-sm font-medium text-primary hover:underline"
          >
            {t('landing.login')}
          </button>
        </div>
      </header>

      {/* Hero */}
      <section className="px-6 pt-8 pb-12 text-center">
        <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-gradient-to-br from-primary to-accent
                        flex items-center justify-center text-4xl shadow-elevated">
          🌱
        </div>
        <h1 className="text-3xl font-bold text-primary-dark mb-3 leading-tight">
          {t('landing.hero_title')}
        </h1>
        <p className="text-text-secondary text-sm max-w-sm mx-auto mb-8 leading-relaxed">
          {t('landing.hero_subtitle')}
        </p>
        <button
          onClick={() => navigate('/onboarding')}
          className="btn-primary text-lg px-10 py-4 shadow-elevated
                     hover:shadow-lg transform hover:-translate-y-0.5 transition-all"
        >
          {t('landing.cta')} →
        </button>
      </section>

      {/* Features grid */}
      <section className="px-4 py-8 bg-surface">
        <div className="max-w-lg mx-auto grid grid-cols-2 gap-3">
          {FEATURES.map((f) => (
            <div key={f.key} className="card hover:shadow-elevated transition-shadow cursor-default">
              <div className="text-3xl mb-2">{f.icon}</div>
              <h3 className="text-sm font-semibold text-text-primary mb-1">
                {t(`landing.${f.key}`)}
              </h3>
              <p className="text-xs text-text-secondary leading-relaxed">
                {t(`landing.${f.key}_desc`)}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="px-6 py-10">
        <h2 className="text-xl font-bold text-center text-primary-dark mb-8">
          {t('landing.how_title')}
        </h2>
        <div className="max-w-sm mx-auto space-y-6">
          {STEPS.map((s, i) => (
            <div key={s.key} className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-full bg-primary text-white flex items-center
                              justify-center text-xl font-bold flex-shrink-0 shadow-card">
                {s.icon}
              </div>
              <div className="pt-1">
                <h3 className="font-semibold text-text-primary mb-0.5">
                  {t(`landing.${s.key}`)}
                </h3>
                <p className="text-sm text-text-secondary leading-relaxed">
                  {t(`landing.${s.key}_desc`)}
                </p>
              </div>
              {i < STEPS.length - 1 && (
                <div className="absolute left-[22px] mt-12 w-0.5 h-6 bg-border" />
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-primary-dark text-white/80 px-6 py-8 text-center text-sm">
        <div className="flex items-center justify-center gap-2 mb-3">
          <span className="text-xl">🌾</span>
          <span className="font-bold text-white">{t('app.name')}</span>
        </div>
        <p className="mb-2">📞 {t('landing.footer_helpline')}: 16123</p>
        <p className="text-white/50 text-xs">© 2026 KrishiBondhu. All rights reserved.</p>
      </footer>
    </div>
  );
}
