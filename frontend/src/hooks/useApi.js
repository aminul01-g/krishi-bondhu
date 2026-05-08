import { useState, useEffect, useCallback, useRef } from 'react';

/**
 * Generic data-fetching hook with loading, error, and refetch support.
 *
 * @param {Function} fetchFn - Async function that returns data. Receives an AbortSignal.
 * @param {Array} deps - Dependency array (re-fetches when deps change).
 * @param {Object} options - { immediate: true } to fetch on mount.
 * @returns {{ data, loading, error, refetch }}
 *
 * @example
 *   const { data, loading, error, refetch } = useApi(
 *     () => getMarketPrices('rice'),
 *     ['rice']
 *   );
 */
export function useApi(fetchFn, deps = [], options = { immediate: true }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const abortRef = useRef(null);

  const refetch = useCallback(async () => {
    // Abort previous in-flight request
    if (abortRef.current) abortRef.current.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    setError(null);

    try {
      const result = await fetchFn(controller.signal);
      if (!controller.signal.aborted) {
        setData(result);
      }
    } catch (err) {
      if (!controller.signal.aborted) {
        console.error('[useApi] Fetch error:', err);
        setError(err.message || 'An error occurred');
      }
    } finally {
      if (!controller.signal.aborted) {
        setLoading(false);
      }
    }
  }, [fetchFn, ...deps]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (options.immediate) {
      refetch();
    }
    return () => {
      if (abortRef.current) abortRef.current.abort();
    };
  }, [refetch]); // eslint-disable-line react-hooks/exhaustive-deps

  return { data, loading, error, refetch };
}
