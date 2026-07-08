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

const MIN_USERNAME = 3;
const MIN_PASSWORD = 8; // matches backend UserRegister(min_length=8)

/** 0..4 password strength score + i18n label key. */
function passwordScore(pw) {
  let s = 0;
  if (pw.length >= MIN_PASSWORD) s++;
  if (pw.length >= 12) s++;
  if (/[0-9]/.test(pw)) s++;
  if (/[^a-zA-Z0-9]/.test(pw) || (/[a-z]/.test(pw) && /[A-Z]/.test(pw))) s++;
  return Math.min(s, 4);
}

/**
 * OnboardingPage
 *  - Login: single-step form.
 *  - Registration: 3-step stepper that builds the farmer profile.
 *
 * Auth note: this page is wrapped in PublicRoute, which redirects to
 * /app/dashboard as soon as an auth token exists in React state. To avoid being
 * kicked out mid-flow, the access token from step 1 is held in local state
 * (pendingToken) and only committed to the session at the very end of step 3,
 * after the profile has been saved.
 */
export default function OnboardingPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { loginUser } = useAuth();

  const [isLogin, setIsLogin] = useState(searchParams.get('mode') === 'login');
  const [step, setStep] = useState(1);

  // ── Account (step 1) ──
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [phone, setPhone] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  // ── Location (step 2) ──
  const [district, setDistrict] = useState('');
  const [upazila, setUpazila] = useState('');

  // ── Farm details (step 3) ──
  const [crops, setCrops] = useState([]);
  const [landArea, setLandArea] = useState(5);
  const [experience, setExperience] = useState('');

  const [pendingToken, setPendingToken] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const switchMode = (nextLogin) => {
    setIsLogin(nextLogin);
    setStep(1);
    setError('');
  };

  // ── Step 1 → 2 : validate, register + login, hold the token ──
  const handleStep1Next = async (e) => {
    e.preventDefault();
    setError('');
    if (pendingToken) { setStep(2); return; }
    if (username.trim().length < MIN_USERNAME) { setError(t('onboarding.username_too_short')); return; }
    if (password.length < MIN_PASSWORD) { setError(t('onboarding.password_too_short')); return; }
    setLoading(true);
    try {
      await register(username.trim(), password);
      const data = await login(username.trim(), password);
      setPendingToken(data.access_token);
      setStep(2);
    } catch (err) {
      setError(err.message || 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

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
      // Temporarily expose the token so the shared api client can authorize the
      // profile request. This does NOT update React state, so PublicRoute will
      // not redirect while the request is in flight.
      localStorage.setItem('kb_auth_token', pendingToken);
      await upsertFarmerProfile({
        district,
        upazila: upazila.trim() || null,
        crops,
        land_area_bigha: Number(landArea),
        farming_experience_years: experience ? Number(experience) : null,
        phone_number: phone.trim() || null,
      });
      loginUser(pendingToken);
      navigate('/app/dashboard', { replace: true });
    } catch (err) {
      localStorage.removeItem('kb_auth_token');
      setError(err.message || 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data = await login(username.trim(), password);
      loginUser(data.access_token);
      navigate('/app/chat', { replace: true });
    } catch (err) {
      setError(err.message || 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  const sharedFormProps = {
    t, username, password, phone, showPassword,
    setUsername: (v) => { setError(''); setUsername(v); },
    setPassword: (v) => { setError(''); setPassword(v); },
    setPhone, setShowPassword,
    loading, error,
  };

  return (
    <div className="min-h-screen bg-bg md:grid md:grid-cols-2">
      {/* ── Brand panel (desktop) ── */}
      <aside className="hidden md:flex brand-gradient text-white relative overflow-hidden">
        <div className="dot-texture absolute inset-0" />
        <div className="relative flex flex-col justify-between p-10 lg:p-14">
          <button onClick={() => navigate('/')} className="flex items-center gap-2 text-white/90 hover:text-white w-max">
            <span className="text-2xl">🌾</span>
            <span className="text-lg font-bold">{t('app.name')}</span>
          </button>
          <div className="max-w-sm animate-fade-up">
            <h2 className="text-3xl lg:text-4xl font-extrabold leading-tight mb-6">
              {t('onboarding.brand_headline')}
            </h2>
            <ul className="space-y-4">
              {['brand_point_1', 'brand_point_2', 'brand_point_3'].map((k) => (
                <li key={k} className="flex items-center gap-3 text-white/90">
                  <span className="w-7 h-7 rounded-full bg-white/15 flex items-center justify-center text-sm">✓</span>
                  {t(`onboarding.${k}`)}
                </li>
              ))}
            </ul>
          </div>
          <p className="text-white/50 text-xs">© 2026 KrishiBondhu</p>
        </div>
      </aside>

      {/* ── Form panel ── */}
      <main className="flex flex-col min-h-screen md:min-h-0">
        <header className="flex items-center justify-between px-4 py-3 md:justify-end">
          <button onClick={() => navigate('/')} className="text-primary font-medium text-sm md:hidden">
            ← {t('common.back')}
          </button>
          <LanguageSwitcher compact />
        </header>

        <div className="flex-1 flex items-center justify-center px-6 pb-10">
          <div className="w-full max-w-sm animate-fade-up">
            {isLogin ? (
              <LoginView {...sharedFormProps} onSubmit={handleLogin} switchMode={switchMode} />
            ) : (
              <RegisterStepper
                {...sharedFormProps}
                step={step}
                district={district} upazila={upazila}
                setDistrict={(v) => { setError(''); setDistrict(v); }} setUpazila={setUpazila}
                crops={crops} toggleCrop={toggleCrop}
                landArea={landArea} setLandArea={setLandArea}
                experience={experience} setExperience={setExperience}
                onStep1Next={handleStep1Next}
                onStep2Next={handleStep2Next}
                onStep2Back={() => { setError(''); setStep(1); }}
                onStep3Submit={handleStep3Submit}
                onStep3Back={() => { setError(''); setStep(2); }}
                switchMode={switchMode}
              />
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

/* ── Reusable password field with show/hide + strength meter ── */
function PasswordField({ t, value, onChange, showPassword, setShowPassword, autoComplete, withMeter }) {
  const score = withMeter ? passwordScore(value) : 0;
  const labels = ['strength_weak', 'strength_weak', 'strength_fair', 'strength_good', 'strength_strong'];
  const colors = ['bg-danger', 'bg-danger', 'bg-accent', 'bg-primary-light', 'bg-primary'];
  return (
    <div>
      <label className="block text-sm font-medium text-text-primary mb-1">{t('onboarding.password_label')}</label>
      <div className="relative">
        <input
          type={showPassword ? 'text' : 'password'}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="••••••••"
          className="input-field pr-16"
          required
          autoComplete={autoComplete}
        />
        <button
          type="button"
          onClick={() => setShowPassword((s) => !s)}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-semibold text-primary hover:text-primary-dark"
        >
          {showPassword ? t('onboarding.hide_password') : t('onboarding.show_password')}
        </button>
      </div>
      {withMeter && value.length > 0 && (
        <div className="mt-2">
          <div className="flex gap-1.5" aria-hidden="true">
            {[0, 1, 2, 3].map((i) => (
              <span key={i} className={`pw-seg ${i < score ? colors[score] : ''}`} />
            ))}
          </div>
          <p className="text-xs text-text-secondary mt-1">
            {t('onboarding.password_strength_label')}: {t(`onboarding.${labels[score]}`)}
          </p>
        </div>
      )}
      {withMeter && value.length === 0 && (
        <p className="text-xs text-text-secondary mt-1">{t('onboarding.password_hint')}</p>
      )}
    </div>
  );
}

function ErrorBox({ error }) {
  if (!error) return null;
  return (
    <div className="bg-danger-light text-danger text-sm p-3 rounded-btn flex items-start gap-2" role="alert">
      <span>⚠️</span><span>{error}</span>
    </div>
  );
}

/* ───────────────────────── Login (single form) ───────────────────────── */
function LoginView({ t, username, password, setUsername, setPassword, showPassword, setShowPassword, onSubmit, loading, error, switchMode }) {
  return (
    <>
      <div className="text-center mb-8">
        <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-primary to-accent
                        flex items-center justify-center text-3xl shadow-card">🌾</div>
        <h1 className="text-2xl font-bold text-primary-dark">{t('onboarding.welcome_back')}</h1>
        <p className="text-text-secondary text-sm mt-1">{t('onboarding.login_subtitle')}</p>
      </div>
      <form onSubmit={onSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-text-primary mb-1">{t('onboarding.username_label')}</label>
          <input type="text" value={username} onChange={(e) => setUsername(e.target.value)}
                 placeholder={t('onboarding.name_placeholder')} className="input-field" required autoComplete="username" />
        </div>
        <PasswordField t={t} value={password} onChange={setPassword} showPassword={showPassword}
                       setShowPassword={setShowPassword} autoComplete="current-password" withMeter={false} />
        <ErrorBox error={error} />
        <button type="submit" disabled={loading} className="btn-primary w-full flex items-center justify-center gap-2">
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
  const { t, step, onStep1Next, onStep2Next, onStep2Back, onStep3Submit, onStep3Back } = props;
  const TOTAL = 3;
  const meta = {
    1: { title: t('onboarding.step_account_title'), subtitle: t('onboarding.step_account_subtitle') },
    2: { title: t('onboarding.step_location_title'), subtitle: t('onboarding.step_location_subtitle') },
    3: { title: t('onboarding.step_farm_title'), subtitle: t('onboarding.step_farm_subtitle') },
  }[step];

  return (
    <>
      {/* Progress bar + label */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold text-primary">
            {t('onboarding.step_label', { n: step, total: TOTAL })}
          </span>
        </div>
        <div className="h-2 rounded-full bg-border overflow-hidden">
          <div className="h-full bg-primary rounded-full transition-all duration-500"
               style={{ width: `${(step / TOTAL) * 100}%` }} />
        </div>
      </div>

      <div className="text-center mb-6">
        {step === 1 && (
          <div className="w-14 h-14 mx-auto mb-3 rounded-2xl bg-gradient-to-br from-primary to-accent
                          flex items-center justify-center text-2xl shadow-card md:hidden">🌾</div>
        )}
        <h1 className="text-xl font-bold text-primary-dark">{meta.title}</h1>
        <p className="text-text-secondary text-sm mt-1">{meta.subtitle}</p>
      </div>

      {step === 1 && <StepAccount {...props} onSubmit={onStep1Next} />}
      {step === 2 && <StepLocation {...props} onSubmit={onStep2Next} onBack={onStep2Back} />}
      {step === 3 && <StepFarm {...props} onSubmit={onStep3Submit} onBack={onStep3Back} />}

      {step === 1 && <ModeSwitch isLogin={false} onClick={() => props.switchMode(true)} t={t} />}
    </>
  );
}

/* ── Step 1: Account ── */
function StepAccount({ t, username, password, phone, setUsername, setPassword, setPhone, showPassword, setShowPassword, onSubmit, loading, error }) {
  const tooShort = username.length > 0 && username.trim().length < MIN_USERNAME;
  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-text-primary mb-1">{t('onboarding.username_label')}</label>
        <input type="text" value={username} onChange={(e) => setUsername(e.target.value)}
               placeholder={t('onboarding.name_placeholder')}
               className={`input-field ${tooShort ? 'border-danger focus:ring-danger/30 focus:border-danger' : ''}`}
               required autoComplete="username" />
        <p className={`text-xs mt-1 ${tooShort ? 'text-danger' : 'text-text-secondary'}`}>
          {t('onboarding.username_hint')}
        </p>
      </div>
      <div>
        <label className="block text-sm font-medium text-text-primary mb-1">{t('onboarding.phone_label')}</label>
        <input type="tel" value={phone} onChange={(e) => setPhone(e.target.value)}
               placeholder={t('onboarding.phone_label')} className="input-field" autoComplete="tel" />
      </div>
      <PasswordField t={t} value={password} onChange={setPassword} showPassword={showPassword}
                     setShowPassword={setShowPassword} autoComplete="new-password" withMeter />
      <ErrorBox error={error} />
      <button type="submit" disabled={loading} className="btn-primary w-full flex items-center justify-center gap-2">
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
        <label className="block text-sm font-medium text-text-primary mb-1">{t('onboarding.district_label')}</label>
        <select value={district} onChange={(e) => setDistrict(e.target.value)} className="input-field" required>
          <option value="">{t('onboarding.district_placeholder')}</option>
          {DISTRICTS.map((d) => <option key={d} value={d}>{d}</option>)}
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium text-text-primary mb-1">{t('onboarding.upazila_label')}</label>
        <input type="text" value={upazila} onChange={(e) => setUpazila(e.target.value)}
               placeholder={t('onboarding.upazila_placeholder')} className="input-field" />
      </div>
      <ErrorBox error={error} />
      <div className="flex gap-3">
        <button type="button" onClick={onBack} className="btn-outline flex-1">{t('onboarding.back')}</button>
        <button type="submit" className="btn-primary flex-[2] flex items-center justify-center gap-2">{t('onboarding.next')}</button>
      </div>
    </form>
  );
}

/* ── Step 3: Farm details ── */
function StepFarm({ t, crops, toggleCrop, landArea, setLandArea, experience, setExperience, onSubmit, onBack, loading, error }) {
  return (
    <form onSubmit={onSubmit} className="space-y-5">
      <div>
        <label className="block text-sm font-medium text-text-primary mb-1">{t('onboarding.crops_label')}</label>
        <p className="text-xs text-text-secondary mb-2">{t('onboarding.crops_hint')}</p>
        <div className="flex flex-wrap gap-2">
          {COMMON_CROPS.map((crop) => {
            const selected = crops.includes(crop);
            return (
              <button key={crop} type="button" onClick={() => toggleCrop(crop)}
                className={`px-3.5 py-1.5 rounded-pill text-sm font-medium border transition-all
                  ${selected ? 'bg-primary text-white border-primary shadow-card'
                             : 'bg-surface text-text-primary border-border hover:border-primary'}`}>
                {selected ? '✓ ' : ''}{crop}
              </button>
            );
          })}
        </div>
      </div>
      <div>
        <div className="flex items-baseline justify-between mb-1">
          <label className="block text-sm font-medium text-text-primary">{t('onboarding.land_label')}</label>
          <span className="text-sm font-semibold text-primary">
            {toBengaliNumerals(landArea)} {t('onboarding.land_unit')}
          </span>
        </div>
        <input type="range" min={LAND_MIN} max={LAND_MAX} step={LAND_STEP} value={landArea}
               onChange={(e) => setLandArea(Number(e.target.value))} className="w-full accent-primary" />
      </div>
      <div>
        <label className="block text-sm font-medium text-text-primary mb-1">{t('onboarding.experience_label')}</label>
        <select value={experience} onChange={(e) => setExperience(e.target.value)} className="input-field">
          <option value="">{t('onboarding.experience_placeholder')}</option>
          {EXPERIENCE_OPTIONS.map((opt) => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
        </select>
      </div>
      <ErrorBox error={error} />
      <div className="flex gap-3">
        <button type="button" onClick={onBack} className="btn-outline flex-1">{t('onboarding.back')}</button>
        <button type="submit" disabled={loading} className="btn-primary flex-[2] flex items-center justify-center gap-2">
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
