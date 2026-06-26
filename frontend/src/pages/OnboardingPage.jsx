import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { register, login, upsertFarmerProfile } from '../services/api';
import { Spinner } from '../components/shared/LoadingStates';
import { LanguageSwitcher } from '../components/shared/LanguageSwitcher';
import {
  DISTRICTS, COMMON_CROPS, EXPERIENCE_OPTIONS,
  LAND_MIN, LAND_MAX, LAND_STEP, toBengaliNumerals,
} from '../utils/farmOptions';

/**
 * OnboardingPage
 *  - Login: single-step form (unchanged).
 *  - Registration: 3-step stepper that builds the farmer profile.
 *
 * Auth note: this page is wrapped in PublicRoute, which redirects to
 * /app/dashboard as soon as an auth token exists in React state. To avoid
 * being kicked out mid-flow, the access token from step 1 is held in local
 * state (pendingToken) and only committed to the session at the very end of
 * step 3, after the profile has been saved.
 */
export default function OnboardingPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { loginUser } = useAuth();

  const [isLogin, setIsLogin] = useState(searchParams.get('mode') === 'login');
  const [step, setStep] = useState(1); // registration step (1..3)

  // ── Account (step 1) ──
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [phone, setPhone] = useState('');

  // ── Location (step 2) ──
  const [district, setDistrict] = useState('');
  const [upazila, setUpazila] = useState('');

  // ── Farm details (step 3) ──
  const [crops, setCrops] = useState([]);
  const [landArea, setLandArea] = useState(5);
  const [experience, setExperience] = useState('');

  // Token obtained in step 1, held until step 3 completes.
  const [pendingToken, setPendingToken] = useState(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const switchMode = (nextLogin) => {
    setIsLogin(nextLogin);
    setStep(1);
    setError('');
  };

  // ── Step 1 → 2 : register + login, hold the token ──
  const handleStep1Next = async (e) => {
    e.preventDefault();
    setError('');
    if (pendingToken) { setStep(2); return; } // already authenticated earlier in flow
    setLoading(true);
    try {
      await register(username, password);
      const data = await login(username, password);
      setPendingToken(data.access_token);
      setStep(2);
    } catch (err) {
      setError(err.message || 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  // ── Step 2 → 3 : validate location ──
  const handleStep2Next = (e) => {
    e.preventDefault();
    setError('');
    if (!district) { setError(t('onboarding.district_placeholder')); return; }
    setStep(3);
  };

  const toggleCrop = (crop) => {
    setError('');
    setCrops((prev) =>
      prev.includes(crop) ? prev.filter((c) => c !== crop) : [...prev, crop]
    );
  };

  // ── Step 3 : save profile, then establish the session ──
  const handleStep3Submit = async (e) => {
    e.preventDefault();
    setError('');
    if (crops.length === 0) { setError(t('onboarding.crops_required')); return; }
    setLoading(true);
    try {
      // Temporarily expose the token so the shared api client can authorize
      // the profile request. This does NOT update React state, so PublicRoute
      // will not redirect while the request is in flight.
      localStorage.setItem('kb_auth_token', pendingToken);

      await upsertFarmerProfile({
        district,
        upazila: upazila.trim() || null,
        crops,
        land_area_bigha: Number(landArea),
        farming_experience_years: experience ? Number(experience) : null,
        phone_number: phone.trim() || null,
      });

      // Profile saved — now commit the session and enter the app.
      loginUser(pendingToken);
      navigate('/app/dashboard', { replace: true });
    } catch (err) {
      // Roll back the transient token so a refresh returns here cleanly.
      localStorage.removeItem('kb_auth_token');
      setError(err.message || 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  // ── Login submit (unchanged single-form flow) ──
  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data = await login(username, password);
      loginUser(data.access_token);
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
          {isLogin ? (
            <LoginView
              t={t}
              username={username}
              password={password}
              setUsername={setUsername}
              setPassword={setPassword}
              onSubmit={handleLogin}
              loading={loading}
              error={error}
              switchMode={switchMode}
            />
          ) : (
            <RegisterStepper
              t={t}
              step={step}
              // account
              username={username}
              password={password}
              phone={phone}
              setUsername={setUsername}
              setPassword={setPassword}
              setPhone={setPhone}
              // location
              district={district}
              upazila={upazila}
              setDistrict={setDistrict}
              setUpazila={setUpazila}
              // farm
              crops={crops}
              toggleCrop={toggleCrop}
              landArea={landArea}
              setLandArea={setLandArea}
              experience={experience}
              setExperience={setExperience}
              // flow
              onStep1Next={handleStep1Next}
              onStep2Next={handleStep2Next}
              onStep2Back={() => { setError(''); setStep(1); }}
              onStep3Submit={handleStep3Submit}
              onStep3Back={() => { setError(''); setStep(2); }}
              loading={loading}
              error={error}
              switchMode={switchMode}
            />
          )}
        </div>
      </main>
    </div>
  );
}

/* ───────────────────────── Login (single form) ───────────────────────── */

function LoginView({ t, username, password, setUsername, setPassword, onSubmit, loading, error, switchMode }) {
  return (
    <>
      <div className="text-center mb-8">
        <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-primary to-accent
                        flex items-center justify-center text-3xl shadow-card">
          🌾
        </div>
        <h1 className="text-2xl font-bold text-primary-dark">{t('onboarding.login_title')}</h1>
      </div>

      <form onSubmit={onSubmit} className="space-y-4">
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
            autoComplete="current-password"
          />
        </div>

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
          {t('onboarding.login_submit')}
        </button>
      </form>

      <ModeSwitch isLogin onClick={() => switchMode(false)} t={t} />
    </>
  );
}

/* ───────────────────────── Registration stepper ───────────────────────── */

function RegisterStepper(props) {
  const {
    t, step,
    onStep1Next, onStep2Next, onStep2Back, onStep3Submit, onStep3Back,
  } = props;

  const stepTitle =
    step === 1 ? t('onboarding.step_account_title')
    : step === 2 ? t('onboarding.step_location_title')
    : t('onboarding.step_farm_title');

  return (
    <>
      {/* Progress dots (● ○ ○ → ● ● ○ → ● ● ●) */}
      <div className="flex items-center justify-center gap-2 mb-5">
        {[1, 2, 3].map((n) => (
          <span
            key={n}
            className={`w-2.5 h-2.5 rounded-full transition-all ${
              n <= step ? 'bg-primary scale-110' : 'bg-border'
            }`}
          />
        ))}
      </div>

      {/* Title + logo (logo only on step 1) */}
      <div className="text-center mb-6">
        {step === 1 && (
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-primary to-accent
                          flex items-center justify-center text-3xl shadow-card">
            🌾
          </div>
        )}
        <h1 className="text-xl font-bold text-primary-dark">{stepTitle}</h1>
      </div>

      {step === 1 && <StepAccount {...props} onSubmit={onStep1Next} />}
      {step === 2 && <StepLocation {...props} onSubmit={onStep2Next} onBack={onStep2Back} />}
      {step === 3 && <StepFarm {...props} onSubmit={onStep3Submit} onBack={onStep3Back} />}

      {step === 1 && <ModeSwitch isLogin={false} onClick={() => props.switchMode(true)} t={t} />}
    </>
  );
}

/* ── Step 1: Account ── */
function StepAccount({ t, username, password, phone, setUsername, setPassword, setPhone, onSubmit, loading, error }) {
  return (
    <form onSubmit={onSubmit} className="space-y-4">
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
          {t('onboarding.phone_label')}
        </label>
        <input
          type="tel"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          placeholder="আপনার ফোন নম্বর"
          className="input-field"
          autoComplete="tel"
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
          autoComplete="new-password"
        />
      </div>

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
        {t('onboarding.next')}
      </button>
    </form>
  );
}

/* ── Step 2: Location ── */
function StepLocation({ t, district, upazila, setDistrict, setUpazila, onSubmit, onBack, error }) {
  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-text-primary mb-1">
          {t('onboarding.district_label')}
        </label>
        <select
          value={district}
          onChange={(e) => setDistrict(e.target.value)}
          className="input-field"
          required
        >
          <option value="">{t('onboarding.district_placeholder')}</option>
          {DISTRICTS.map((d) => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-text-primary mb-1">
          {t('onboarding.upazila_label')}
        </label>
        <input
          type="text"
          value={upazila}
          onChange={(e) => setUpazila(e.target.value)}
          placeholder="আপনার উপজেলার নাম লিখুন"
          className="input-field"
        />
      </div>

      {error && (
        <div className="bg-danger-light text-danger text-sm p-3 rounded-btn text-center">
          {error}
        </div>
      )}

      <div className="flex gap-3">
        <button
          type="button"
          onClick={onBack}
          className="btn-outline flex-1"
        >
          {t('onboarding.back')}
        </button>
        <button
          type="submit"
          className="btn-primary flex-[2] flex items-center justify-center gap-2"
        >
          {t('onboarding.next')}
        </button>
      </div>
    </form>
  );
}

/* ── Step 3: Farm details ── */
function StepFarm({
  t, crops, toggleCrop, landArea, setLandArea, experience, setExperience,
  onSubmit, onBack, loading, error,
}) {
  return (
    <form onSubmit={onSubmit} className="space-y-5">
      {/* Crop chips (multi-select) */}
      <div>
        <label className="block text-sm font-medium text-text-primary mb-1">
          {t('onboarding.crops_label')}
        </label>
        <p className="text-xs text-text-secondary mb-2">{t('onboarding.crops_hint')}</p>
        <div className="flex flex-wrap gap-2">
          {COMMON_CROPS.map((crop) => {
            const selected = crops.includes(crop);
            return (
              <button
                key={crop}
                type="button"
                onClick={() => toggleCrop(crop)}
                className={`px-3.5 py-1.5 rounded-pill text-sm font-medium border transition-all
                  ${selected
                    ? 'bg-primary text-white border-primary shadow-card'
                    : 'bg-surface text-text-primary border-border hover:border-primary'}`}
              >
                {crop}
              </button>
            );
          })}
        </div>
      </div>

      {/* Land area slider */}
      <div>
        <div className="flex items-baseline justify-between mb-1">
          <label className="block text-sm font-medium text-text-primary">
            {t('onboarding.land_label')}
          </label>
          <span className="text-sm font-semibold text-primary">
            {toBengaliNumerals(landArea)} {t('onboarding.land_unit')}
          </span>
        </div>
        <input
          type="range"
          min={LAND_MIN}
          max={LAND_MAX}
          step={LAND_STEP}
          value={landArea}
          onChange={(e) => setLandArea(Number(e.target.value))}
          className="w-full accent-primary"
        />
      </div>

      {/* Farming experience */}
      <div>
        <label className="block text-sm font-medium text-text-primary mb-1">
          {t('onboarding.experience_label')}
        </label>
        <select
          value={experience}
          onChange={(e) => setExperience(e.target.value)}
          className="input-field"
        >
          <option value="">{t('onboarding.experience_placeholder')}</option>
          {EXPERIENCE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>

      {error && (
        <div className="bg-danger-light text-danger text-sm p-3 rounded-btn text-center">
          {error}
        </div>
      )}

      <div className="flex gap-3">
        <button
          type="button"
          onClick={onBack}
          className="btn-outline flex-1"
        >
          {t('onboarding.back')}
        </button>
        <button
          type="submit"
          disabled={loading}
          className="btn-primary flex-[2] flex items-center justify-center gap-2"
        >
          {loading && <Spinner size="sm" />}
          {t('onboarding.submit')}
        </button>
      </div>
    </form>
  );
}

/* ── Login / Register toggle ── */
function ModeSwitch({ isLogin, onClick, t }) {
  return (
    <p className="text-center text-sm text-text-secondary mt-6">
      {isLogin ? t('onboarding.no_account') : t('onboarding.has_account')}{' '}
      <button onClick={onClick} className="text-primary font-semibold hover:underline">
        {isLogin ? t('onboarding.register') : t('onboarding.login_title')}
      </button>
    </p>
  );
}
