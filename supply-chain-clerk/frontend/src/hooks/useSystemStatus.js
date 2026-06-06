/**
 * System status poller — hits /status every 10 s.
 */
import { useState, useEffect, useRef } from 'react';

const DEFAULT = {
  vlm_api: 'unknown',
  neo4j:   'unknown',
  mqtt:    'unknown',
  esp32_alive: false,
  esp32_connection: 'none',
  esp32_last_seen: null,
};

export function useSystemStatus() {
  const [status, setStatus] = useState(DEFAULT);
  const [avgLatency, setAvgLatency] = useState(null);
  const latenciesRef = useRef([]);

  const poll = async () => {
    try {
      const res = await fetch('http://localhost:8000/status');
      if (res.ok) setStatus(await res.json());
    } catch (_) {}
  };

  useEffect(() => {
    poll();
    const id = setInterval(poll, 10_000);
    return () => clearInterval(id);
  }, []);

  const recordLatency = (ms) => {
    latenciesRef.current.push(ms);
    if (latenciesRef.current.length > 10) latenciesRef.current.shift();
    setAvgLatency(Math.round(latenciesRef.current.reduce((a,b)=>a+b,0) / latenciesRef.current.length));
  };

  return { status, avgLatency, recordLatency };
}
