/**
 * SystemStatusBar — persistent top bar showing service health.
 */
import React from 'react';
import { Package, Brain, Database, Network, Cpu, Usb } from 'lucide-react';

function Dot({ state, pulse }) {
  return (
    <span
      className={`status-dot ${state === 'ok' ? 'ok' : state === 'unknown' ? '' : 'error'} ${pulse ? 'pulse' : ''}`}
    />
  );
}

export default function SystemStatusBar({ status, avgLatency }) {
  const esp32State = status.esp32_alive ? 'ok' : 'error';
  const esp32Label = status.esp32_connection === 'usb'
    ? 'ESP32 (USB)'
    : status.esp32_connection === 'mqtt'
      ? 'ESP32 (MQTT)'
      : 'ESP32';

  return (
    <header className="status-bar">
      <div className="status-bar-brand">
        <div className="logo-icon">
          <Package size={16} style={{ color: 'white' }} />
        </div>
        <span>
          Supply Chain <span style={{ color: 'var(--accent-primary)' }}>Clerk</span>
        </span>
      </div>

      <div className="status-indicators">
        <div className="status-indicator">
          <Dot state={status.vlm_api} pulse />
          <Brain size={13} style={{ color: 'var(--text-secondary)' }} />
          <span>VLM API</span>
        </div>
        <div className="status-indicator">
          <Dot state={status.neo4j} />
          <Database size={13} style={{ color: 'var(--text-secondary)' }} />
          <span>Neo4j</span>
        </div>
        <div className="status-indicator">
          <Dot state={status.mqtt} />
          <Network size={13} style={{ color: 'var(--text-secondary)' }} />
          <span>MQTT</span>
        </div>
        <div className="status-indicator">
          <Dot state={esp32State} pulse={status.esp32_alive} />
          {status.esp32_connection === 'usb'
            ? <Usb size={13} style={{ color: status.esp32_alive ? 'var(--accent-green)' : 'var(--text-secondary)' }} />
            : <Cpu size={13} style={{ color: status.esp32_alive ? 'var(--accent-green)' : 'var(--text-secondary)' }} />
          }
          <span>{esp32Label}</span>
        </div>
        {avgLatency !== null && (
          <div className="latency-badge">
            <span>⚡</span> {avgLatency} ms avg
          </div>
        )}
      </div>
    </header>
  );
}
