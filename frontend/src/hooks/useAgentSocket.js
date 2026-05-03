import { useState, useEffect, useCallback } from 'react';

/**
 * Custom React Hook for managing a WebSocket connection to stream agent statuses.
 * @param {string} url - The WebSocket URL (e.g., 'ws://localhost:8000/api/ws/agent_status')
 * @returns {object} { status, isConnected }
 */
export function useAgentSocket(url) {
  const [status, setStatus] = useState('Idle');
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    if (!url) return;

    let ws = null;
    let reconnectTimer = null;

    const connect = () => {
      ws = new WebSocket(url);

      ws.onopen = () => {
        console.log('Connected to Agent WebSocket');
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.message) {
            setStatus(data.message);
          }
        } catch (err) {
          console.error('Failed to parse WebSocket message', err);
        }
      };

      ws.onclose = () => {
        console.log('Disconnected from Agent WebSocket. Reconnecting in 3s...');
        setIsConnected(false);
        // Basic reconnect logic
        reconnectTimer = setTimeout(connect, 3000);
      };

      ws.onerror = (error) => {
        console.error('WebSocket Error:', error);
        ws.close();
      };
    };

    connect();

    // Cleanup on unmount
    return () => {
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (ws) ws.close();
    };
  }, [url]);

  return { status, isConnected };
}
