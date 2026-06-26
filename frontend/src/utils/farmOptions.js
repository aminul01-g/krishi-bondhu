/**
 * Shared farm onboarding/edit options and Bengali formatting helpers.
 * Used by OnboardingPage (registration) and ProfileEditPage.
 */

// The 23 districts covered by KrishiBondhu (Bengali)
export const DISTRICTS = [
  'ঢাকা', 'চট্টগ্রাম', 'রাজশাহী', 'খুলনা', 'বরিশাল', 'সিলেট', 'রংপুর', 'ময়মনসিংহ',
  'কুমিল্লা', 'গাজীপুর', 'নারায়ণগঞ্জ', 'টাঙ্গাইল', 'কিশোরগঞ্জ', 'মানিকগঞ্জ', 'নরসিংদী',
  'ফরিদপুর', 'যশোর', 'সাতক্ষীরা', 'বগুড়া', 'দিনাজপুর', 'পাবনা', 'নাটোর', 'চাঁপাইনবাবগঞ্জ',
];

// 12 most common Bangladeshi crops, shown as selectable chips
export const COMMON_CROPS = [
  'ধান', 'গম', 'পাট', 'আলু', 'পেঁয়াজ', 'মরিচ',
  'টমেটো', 'ভুট্টা', 'সরিষা', 'বেগুন', 'শশা', 'মসুর',
];

// Farming experience brackets. value is the integer stored in the backend.
export const EXPERIENCE_OPTIONS = [
  { label: '১-৫ বছর',   value: 3 },
  { label: '৫-১০ বছর',  value: 7 },
  { label: '১০-২০ বছর', value: 15 },
  { label: '২০+ বছর',   value: 20 },
];

// Land slider bounds (in bigha)
export const LAND_MIN = 0.5;
export const LAND_MAX = 50;
export const LAND_STEP = 0.5;

// Bengali-Indic digits for localized display
const BN_DIGITS = ['০', '১', '২', '৩', '৪', '৫', '৬', '৭', '৮', '৯'];

/**
 * Convert the number/integer part of a value to Bengali numerals.
 * Non-digit characters (e.g. '.', '+', '-') are preserved as-is.
 * @param {number|string} value
 * @returns {string}
 */
export function toBengaliNumerals(value) {
  return String(value).replace(/[0-9]/g, (d) => BN_DIGITS[Number(d)]);
}
