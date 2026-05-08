import { useState, useEffect, useCallback } from 'react';

/**
 * Generic data-fetching hook with abort support.
 * @param {Function} fetchFn - Async function receiving AbortSignal
 * @param {Array} deps - Dependency array to trigger re-fetch
 */
export function useApi(fetchFn, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const execute = useCallback(() => {
    const ctrl = new AbortController();
    setLoading(true);
    setError(null);
    fetchFn(ctrl.signal)
      .then(setData)
      .catch((e) => { if (e.name !== 'AbortError') setError(e.message); })
      .finally(() => setLoading(false));
    return () => ctrl.abort();
  }, deps);

  useEffect(() => {
    const cleanup = execute();
    return cleanup;
  }, [execute]);

  return { data, loading, error, refetch: execute };
}
