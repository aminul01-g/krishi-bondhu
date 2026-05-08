import { useState, useEffect, useCallback } from 'react';

/**
 * Hook for geolocation with permission handling.
 */
export function useGeolocation() {
  const [position, setPosition] = useState({ lat: null, lon: null });
  const [error, setError] = useState(null);

  const requestLocation = useCallback(() => {
    if (!navigator.geolocation) {
      setError('Geolocation not supported');
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => setPosition({ lat: pos.coords.latitude, lon: pos.coords.longitude }),
      (err) => setError(err.message),
      { enableHighAccuracy: false, timeout: 10000 }
    );
  }, []);

  useEffect(() => { requestLocation(); }, [requestLocation]);

  return { ...position, error, requestLocation };
}
