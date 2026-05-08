import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import bn from '../locales/bn.json';
import en from '../locales/en.json';

const savedLang = localStorage.getItem('kb_lang') || 'bn';

i18n.use(initReactI18next).init({
  resources: {
    bn: { translation: bn },
    en: { translation: en },
  },
  lng: savedLang,
  fallbackLng: 'bn',
  interpolation: { escapeValue: false },
});

export default i18n;
