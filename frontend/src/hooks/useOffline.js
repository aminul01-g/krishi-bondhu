import { useState, useEffect, useCallback } from 'react';
import { getQueueCount, flushQueue } from '../services/offlineQueue';

/**
 * Hook for tracking online/offline status and pending sync count.
 *
 * @returns {{ isOffline: boolean, pendingCount: number }}
 *
 * @example
 *   const { isOffline, pendingCount } = useOffline();
 */
export function useOffline() {
  const [isOffline, setIsOffline] = useState(!navigator.onLine);
  const [pendingCount, setPendingCount] = useState(0);

  const updatePendingCount = useCallback(async () => {
    try {
      const count = await getQueueCount();
      setPendingCount(count);
    } catch {
      setPendingCount(0);
    }
  }, []);

  useEffect(() => {
    const handleOnline = () => {
      setIsOffline(false);
      flushQueue();
      updatePendingCount();
    };

    const handleOffline = () => {
      setIsOffline(true);
    };

    const handleSyncUpdate = () => {
      updatePendingCount();
    };

    // Initial count
    updatePendingCount();

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    window.addEventListener('offline-sync-updated', handleSyncUpdate);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      window.removeEventListener('offline-sync-updated', handleSyncUpdate);
    };
  }, [updatePendingCount]);

  return { isOffline, pendingCount };
}
