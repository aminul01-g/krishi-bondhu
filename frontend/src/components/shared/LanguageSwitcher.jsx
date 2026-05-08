import { useTranslation } from 'react-i18next';

/**
 * Bengali/English language toggle button.
 */
export function LanguageSwitcher({ compact = false }) {
  const { i18n } = useTranslation();
  const currentLang = i18n.language;

  const toggle = () => {
    const next = currentLang === 'bn' ? 'en' : 'bn';
    i18n.changeLanguage(next);
    localStorage.setItem('kb_lang', next);
  };

  if (compact) {
    return (
      <button
        onClick={toggle}
        className="flex items-center gap-1 px-2 py-1 rounded-pill text-xs font-semibold
                   bg-primary/10 text-primary hover:bg-primary/20 transition-all"
        aria-label="Switch language"
      >
        <span className={currentLang === 'bn' ? 'opacity-50' : 'font-bold'}>EN</span>
        <span className="text-border">|</span>
        <span className={currentLang === 'en' ? 'opacity-50' : 'font-bold'}>বাং</span>
      </button>
    );
  }

  return (
    <button
      onClick={toggle}
      className="flex items-center gap-2 px-4 py-2 rounded-btn border border-border
                 hover:bg-primary/5 transition-all text-sm font-medium"
      aria-label="Switch language"
    >
      🌐
      <span>{currentLang === 'bn' ? 'English' : 'বাংলা'}</span>
    </button>
  );
}
