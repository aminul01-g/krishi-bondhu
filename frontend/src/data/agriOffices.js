/**
 * District → local agriculture office (DAE — Department of Agricultural
 * Extension) contact mapping, used by the Emergency "forward to agriculture
 * office" share action.
 *
 * NOTE: These are hardcoded fallback numbers bundled with the client. They are
 * placeholders for per-district DAE upazila land-line numbers and should be
 * replaced with verified office contacts before production rollout. The helper
 * always returns a value (a national helpline fallback) so the feature never
 * silently breaks for an unmapped district.
 *
 * Keys mirror the 23 Bengali district names in utils/farmOptions.js.
 */

// 16123 is the national Bangladesh Call Centre / Krishi Call Centre number.
const NATIONAL_FALLBACK = '16123';

const AGRI_OFFICES = {
  'ঢাকা': '02-9558817',
  'চট্টগ্রাম': '031-636263',
  'রাজশাহী': '0721-776041',
  'খুলনা': '041-720661',
  'বরিশাল': '0431-217087',
  'সিলেট': '0821-715305',
  'রংপুর': '0521-63531',
  'ময়মনসিংহ': '091-63053',
  'কুমিল্লা': '081-65723',
  'গাজীপুর': '02-9804021',
  'নারায়ণগঞ্জ': '02-7670041',
  'টাঙ্গাইল': '0921-62622',
  'কিশোরগঞ্জ': '0941-62235',
  'মানিকগঞ্জ': '02-19622015',
  'নরসিংদী': '02-662404',
  'ফরিদপুর': '0631-66242',
  'যশোর': '0421-62155',
  'সাতক্ষীরা': '0471-62555',
  'বগুড়া': '051-67322',
  'দিনাজপুর': '0531-64784',
  'পাবনা': '0731-66168',
  'নাটোর': '0771-62042',
  'চাঁপাইনবাবগঞ্জ': '0781-62417',
};

/**
 * Resolve an agriculture-office contact for a district.
 * Returns the national helpline for unknown/blank districts.
 * @param {string} district  Bengali district name.
 * @returns {string}
 */
export function getOfficePhone(district) {
  if (!district) return NATIONAL_FALLBACK;
  return AGRI_OFFICES[district] || NATIONAL_FALLBACK;
}

export { NATIONAL_FALLBACK };
export default AGRI_OFFICES;
