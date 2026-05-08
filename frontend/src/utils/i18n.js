/**
 * i18n — Simple bilingual (Bengali/English) string lookup.
 *
 * Usage:
 *   import { t, setLang, getLang } from '../utils/i18n';
 *   t('loading')        // → "লোড হচ্ছে..." (default Bengali)
 *   t('loading', 'en')  // → "Loading..."
 */

const strings = {
  bn: {
    // General
    loading: 'লোড হচ্ছে...',
    error_generic: 'কিছু একটা সমস্যা হয়েছে। আবার চেষ্টা করুন।',
    retry: 'আবার চেষ্টা করুন',
    no_data: 'কোনো তথ্য পাওয়া যায়নি।',
    save: 'সংরক্ষণ করুন',
    cancel: 'বাতিল',
    submit: 'জমা দিন',
    search: 'অনুসন্ধান',
    refresh: 'রিফ্রেশ',
    logout: 'লগ আউট',

    // Navigation
    nav_overview: 'ফার্ম ইন্টেলিজেন্স',
    nav_chat: 'AI চ্যাট',
    nav_market: 'বাজার তথ্য',
    nav_tips: 'দৈনিক টিপস',
    nav_diary: 'খামার ডায়েরি',
    nav_soil: 'মাটির স্বাস্থ্য',
    nav_water: 'সেচ ব্যবস্থা',
    nav_finance: 'আর্থিক তথ্য',
    nav_community: 'কমিউনিটি',
    nav_marketplace: 'বাজার',
    nav_emergency: 'জরুরি সহায়তা',

    // Status
    online: 'সংযুক্ত',
    offline: 'অফলাইন মোড সক্রিয়',
    pending_sync: 'সিঙ্ক বাকি',
    syncing: 'সিঙ্ক হচ্ছে...',
    agent_ready: 'এজেন্ট প্রস্তুত',
    reconnecting: 'পুনঃসংযোগ হচ্ছে...',
  },

  en: {
    // General
    loading: 'Loading...',
    error_generic: 'Something went wrong. Please try again.',
    retry: 'Retry',
    no_data: 'No data found.',
    save: 'Save',
    cancel: 'Cancel',
    submit: 'Submit',
    search: 'Search',
    refresh: 'Refresh',
    logout: 'Log out',

    // Navigation
    nav_overview: 'Farm Intelligence',
    nav_chat: 'AI Chat',
    nav_market: 'Market Intelligence',
    nav_tips: 'Daily Tips',
    nav_diary: 'Farm Diary',
    nav_soil: 'Soil Health',
    nav_water: 'Irrigation',
    nav_finance: 'Finance Hub',
    nav_community: 'Community Q&A',
    nav_marketplace: 'Marketplace',
    nav_emergency: 'Emergency',

    // Status
    online: 'Connected',
    offline: 'Offline mode enabled',
    pending_sync: 'pending',
    syncing: 'Syncing...',
    agent_ready: 'Agent ready',
    reconnecting: 'Reconnecting...',
  },
};

let currentLang = 'bn';

/**
 * Translate a key to the current or specified language.
 * Falls back to English, then to the raw key.
 */
export const t = (key, lang) => {
  const l = lang || currentLang;
  return strings[l]?.[key] || strings['en']?.[key] || key;
};

export const setLang = (lang) => { currentLang = lang; };
export const getLang = () => currentLang;
export const getAvailableLanguages = () => ['bn', 'en'];
