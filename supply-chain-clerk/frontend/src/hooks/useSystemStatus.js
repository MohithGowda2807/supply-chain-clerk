/**
 * System status poller — hits /status every 10 s.
 */
import { useState, useEffect } from 'react';

const DEFAULT = {
  vlm_api: 'unknown',
  neo4j:   'unknown',
  mqtt:    'unknown',
  esp32_alive: false,
  esp32_last_seen: null,
};

export function useSystemStatus() {
  const [status, setStatus] = useState(DEFAULT);
  const [avgLatency, setAvgLatency] = useState(null);
  const latencies = [];

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
    latencies.push(ms);
    if (latencies.length > 10) latencies.shift();
    setAvgLatency(Math.round(latencies.reduce((a,b)=>a+b,0) / latencies.length));
  };

  return { status, avgLatency, recordLatency };
}
