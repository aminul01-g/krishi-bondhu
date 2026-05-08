import { useTranslation } from 'react-i18next';
import { useOffline } from '../../hooks/useOffline';

/**
 * Sticky banner shown when device is offline.
 */
export function OfflineBanner() {
  const { isOffline } = useOffline();
  const { t } = useTranslation();

  if (!isOffline) return null;

  return (
    <div
      className="fixed top-0 left-0 right-0 z-50 bg-accent text-text-primary
                 text-center py-2 px-4 text-xs font-medium shadow-md
                 animate-in slide-in-from-top"
      role="alert"
    >
      <span className="mr-1">📡</span>
      {t('common.offline')} — {t('common.offline_msg')}
    </div>
  );
}
