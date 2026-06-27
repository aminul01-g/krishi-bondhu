import { useState, useEffect, useCallback, useRef } from 'react';
import { useToast } from '../contexts/ToastContext';
import { postDamageReport } from '../services/api';
import { isNetworkError } from '../services/api';
import {
  queueReport,
  getPendingReports,
  getPendingCount,
  getPhotos,
  removeReport,
} from '../utils/emergencyDb';

/**
 * useEmergencyQueue
 *
 * Exposes the pending-report count (for nav badges) and drives automatic
 * replay of any reports that were saved offline.
 *
 * Replay happens:
 *   - once on mount, and
 *   - whenever the window fires the `online` event,
 * but only if `navigator.onLine` is true.
 *
 * On each successful retry the report is removed from IndexedDB and a success
 * toast is shown ("স্থগিত রিপোর্ট পাঠানো হয়েছে ✅"). If a retry still fails
 * for connectivity reasons, the report stays queued and we stop the current
 * pass (the next `online` event will try again).
 *
 * @returns {{ pendingCount: number, syncing: boolean, triggerSync: Function }}
 */
export function useEmergencyQueue() {
  const toast = useToast();
  const [pendingCount, setPendingCount] = useState(0);
  const [syncing, setSyncing] = useState(false);
  const inflight = useRef(false); // guard against overlapping sync passes

  const refreshCount = useCallback(async () => {
    try {
      const count = await getPendingCount();
      setPendingCount(count);
    } catch {
      // IndexedDB unavailable (rare) — just leave the count as-is.
    }
  }, []);

  const sync = useCallback(async () => {
    if (inflight.current) return;
    if (typeof navigator !== 'undefined' && navigator.onLine === false) return;
    inflight.current = true;
    setSyncing(true);
    try {
      const pending = await getPendingReports();
      if (!pending.length) return;

      for (const report of pending) {
        try {
          // Read stored photo Blobs back and convert to base64 to match the
          // exact payload shape that EmergencyPage sends for online reports.
          const photos = await getPhotos(report.photoIds);
          const imageData = [];
          for (const photo of photos) {
            const base64 = await fileToDataURL(photo);
            if (base64) imageData.push(base64);
          }

          await postDamageReport({
            crop_type: report.cropType,
            damage_cause: report.damageCause,
            damage_estimate_percent: report.damagePercent,
            yield_loss_estimate_percent: report.damagePercent,
            lat: report.lat,
            lon: report.lon,
            voice_statement_transcribed: report.voiceText,
            image_data: imageData,
          });

          await removeReport(report.id);
          toast.show('স্থগিত রিপোর্ট পাঠানো হয়েছে ✅');
        } catch (err) {
          // If still offline, stop retrying for now and leave it queued.
          if (isNetworkError(err)) break;
          // Non-network error: keep the item queued (the user can revisit).
          // Don't spam toasts for each failed item; stop after the first.
          break;
        }
      }
    } finally {
      inflight.current = false;
      setSyncing(false);
      await refreshCount();
    }
  }, [toast, refreshCount]);

  const triggerSync = useCallback(() => { sync(); }, [sync]);

  // Initial load: refresh count + attempt a sync.
  useEffect(() => {
    refreshCount();
    sync();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Replay whenever connectivity returns.
  useEffect(() => {
    const onOnline = () => { sync(); };
    window.addEventListener('online', onOnline);
    return () => window.removeEventListener('online', onOnline);
  }, [sync]);

  return { pendingCount, syncing, triggerSync, refreshCount };
}

/** Read a File/Blob as a data URL (base64). Resolves '' on failure. */
function fileToDataURL(file) {
  return new Promise((resolve) => {
    if (!file) { resolve(''); return; }
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result || '');
    reader.onerror = () => resolve('');
    reader.readAsDataURL(file);
  });
}
