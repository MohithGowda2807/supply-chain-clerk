/**
 * WebSocket event bus hook.
 * Connects to ws://localhost:8000/ws and dispatches typed events.
 */
import { useEffect, useRef, useCallback } from 'react';

export function useWebSocket(onEvent) {
  const wsRef = useRef(null);
  const pingRef = useRef(null);

  const connect = useCallback(() => {
    const ws = new WebSocket('ws://localhost:8000/ws');

    ws.onopen = () => {
      console.log('[WS] Connected');
      // Ping every 30 s to keep alive
      pingRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send('ping');
      }, 30_000);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onEvent(data);
      } catch (_) {}
    };

    ws.onclose = () => {
      console.log('[WS] Disconnected — reconnecting in 3 s');
      clearInterval(pingRef.current);
      setTimeout(connect, 3_000);
    };

    ws.onerror = () => ws.close();
    wsRef.current = ws;
  }, [onEvent]);

  useEffect(() => {
    connect();
    return () => {
      clearInterval(pingRef.current);
      wsRef.current?.close();
    };
  }, [connect]);
}
