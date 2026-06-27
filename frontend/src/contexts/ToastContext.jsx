import { createContext, useContext, useState, useRef, useCallback, useEffect } from 'react';

/**
 * Minimal toast/notification system for KrishiBondhu.
 *
 * Usage:
 *   const toast = useToast();
 *   toast.show('স্থগিত রিপোর্ট পাঠানো হয়েছে ✅');
 *   toast.show('পাঠাতে ব্যর্থ', 'error');
 *
 * Toasts auto-dismiss after `duration` ms and render in a single fixed
 * container above the bottom tab bar.
 */

const ToastContext = createContext(null);

const DEFAULT_DURATION = 4000;

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  // Track the id counter in a ref so removal still works after rapid additions.
  const counter = useRef(0);
  // Map of toastId -> timeout handle, for manual dismissal before auto-hide.
  const timers = useRef({});

  const dismiss = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
    if (timers.current[id]) {
      clearTimeout(timers.current[id]);
      delete timers.current[id];
    }
  }, []);

  const show = useCallback((message, variant = 'success', duration = DEFAULT_DURATION) => {
    counter.current += 1;
    const id = counter.current;
    setToasts((prev) => [...prev, { id, message, variant }]);
    if (duration > 0) {
      timers.current[id] = setTimeout(() => dismiss(id), duration);
    }
    return id;
  }, [dismiss]);

  // Cleanup any pending timers on unmount.
  useEffect(() => () => {
    Object.values(timers.current).forEach(clearTimeout);
    timers.current = {};
  }, []);

  return (
    <ToastContext.Provider value={{ show, dismiss }}>
      {children}
      <ToastContainer toasts={toasts} onDismiss={dismiss} />
    </ToastContext.Provider>
  );
}

/** Fixed container rendering the active toasts. */
function ToastContainer({ toasts, onDismiss }) {
  if (!toasts.length) return null;
  return (
    <div
      className="fixed left-1/2 -translate-x-1/2 z-[60] flex flex-col items-center gap-2 w-[92%] max-w-md"
      style={{ bottom: 'calc(env(safe-area-inset-bottom, 0px) + 5rem)' }}
      role="status"
      aria-live="polite"
    >
      {toasts.map((t) => (
        <button
          key={t.id}
          onClick={() => onDismiss(t.id)}
          className={`w-full text-center text-sm font-medium text-white shadow-elevated
                      rounded-card px-4 py-3 animate-[slideDown_0.25s_ease]
                      ${t.variant === 'error' ? 'bg-danger' : 'bg-primary'}`}
        >
          {t.message}
        </button>
      ))}
    </div>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    // Graceful no-op if used outside a provider (e.g. during early dev).
    return { show: () => {}, dismiss: () => {} };
  }
  return ctx;
}
