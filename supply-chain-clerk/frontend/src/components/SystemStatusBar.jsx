/**
 * SystemStatusBar — persistent top bar showing service health.
 */
import React from 'react';

function Dot({ state, pulse }) {
  return (
    <span
      className={`status-dot ${state === 'ok' ? 'ok' : state === 'unknown' ? '' : 'error'} ${pulse ? 'pulse' : ''}`}
    />
  );
}

export default function SystemStatusBar({ status, avgLatency }) {
  return (
    <header className="status-bar">
      <div className="status-bar-brand">
        <div className="logo-icon">📦</div>
        Supply Chain Clerk
      </div>

      <div className="status-indicators">
        <div className="status-indicator">
          <Dot state={status.vlm_api} pulse />
          <span>VLM API</span>
        </div>
        <div className="status-indicator">
          <Dot state={status.neo4j} />
          <span>Neo4j</span>
        </div>
        <div className="status-indicator">
          <Dot state={status.mqtt} />
          <span>MQTT</span>
        </div>
        <div className="status-indicator">
          <Dot state={status.esp32_alive ? 'ok' : 'error'} />
          <span>ESP32</span>
        </div>
        {avgLatency !== null && (
          <div className="latency-badge">⚡ {avgLatency} ms avg</div>
        )}
      </div>
    </header>
  );
}
