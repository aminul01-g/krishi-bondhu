import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { register, login } from '../services/api';
import { Spinner } from '../components/shared/LoadingStates';
import { LanguageSwitcher } from '../components/shared/LanguageSwitcher';

const DISTRICTS = [
  'ঢাকা', 'চট্টগ্রাম', 'রাজশাহী', 'খুলনা', 'বরিশাল', 'সিলেট', 'রংপুর', 'ময়মনসিংহ',
  'কুমিল্লা', 'গাজীপুর', 'নারায়ণগঞ্জ', 'টাঙ্গাইল', 'কিশোরগঞ্জ', 'মানিকগঞ্জ', 'নরসিংদী',
  'ফরিদপুর', 'যশোর', 'সাতক্ষীরা', 'বগুড়া', 'দিনাজপুর', 'পাবনা', 'নাটোর', 'চাঁপাইনবাবগঞ্জ',
];

export default function OnboardingPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { loginUser } = useAuth();

  const [isLogin, setIsLogin] = useState(searchParams.get('mode') === 'login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [district, setDistrict] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      if (isLogin) {
        const data = await login(username, password);
        loginUser(data.access_token);
      } else {
        await register(username, password);
        const data = await login(username, password);
        loginUser(data.access_token);
        if (district) localStorage.setItem('kb_district', district);
      }
      navigate('/app/chat', { replace: true });
    } catch (err) {
      setError(err.message || 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-bg flex flex-col">
      <header className="flex items-center justify-between px-4 py-3">
        <button onClick={() => navigate('/')} className="text-primary font-medium text-sm">
          ← {t('common.back')}
        </button>
        <LanguageSwitcher compact />
      </header>

      <main className="flex-1 flex items-center justify-center px-6 pb-8">
        <div className="w-full max-w-sm">
          {/* Logo */}
          <div className="text-center mb-8">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-primary to-accent
                            flex items-center justify-center text-3xl shadow-card">
              🌾
            </div>
            <h1 className="text-2xl font-bold text-primary-dark">
              {isLogin ? t('onboarding.login_title') : t('onboarding.title')}
            </h1>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-text-primary mb-1">
                {t('onboarding.username_label')}
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder={t('onboarding.name_placeholder')}
                className="input-field"
                required
                autoComplete="username"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-1">
                {t('onboarding.password_label')}
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="input-field"
                required
                autoComplete={isLogin ? 'current-password' : 'new-password'}
              />
            </div>

            {!isLogin && (
              <div>
                <label className="block text-sm font-medium text-text-primary mb-1">
                  {t('onboarding.district_label')}
                </label>
                <select
                  value={district}
                  onChange={(e) => setDistrict(e.target.value)}
                  className="input-field"
                >
                  <option value="">{t('onboarding.district_placeholder')}</option>
                  {DISTRICTS.map((d) => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
              </div>
            )}

            {error && (
              <div className="bg-danger-light text-danger text-sm p-3 rounded-btn text-center">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full flex items-center justify-center gap-2"
            >
              {loading && <Spinner size="sm" />}
              {isLogin ? t('onboarding.login_submit') : t('onboarding.submit')}
            </button>
          </form>

          <p className="text-center text-sm text-text-secondary mt-6">
            {isLogin ? t('onboarding.no_account') : t('onboarding.has_account')}{' '}
            <button
              onClick={() => { setIsLogin(!isLogin); setError(''); }}
              className="text-primary font-semibold hover:underline"
            >
              {isLogin ? t('onboarding.register') : t('onboarding.login_title')}
            </button>
          </p>
        </div>
      </main>
    </div>
  );
}
