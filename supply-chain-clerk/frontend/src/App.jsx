/**
 * App.jsx — Root component.
 *
 * Layout:
 *   ┌─────────────────────────────── Status Bar ────────────────────────────────┐
 *   │  CapturePanel (top-left)              │  LiveIntakeFeed (right sidebar)   │
 *   │  BinGrid      (bottom-left)           │                                   │
 *   └───────────────────────────────────────────────────────────────────────────┘
 */
import React, { useState, useCallback } from 'react';
import SystemStatusBar from './components/SystemStatusBar';
import HardwareDashboard from './components/HardwareDashboard';
import CapturePanel    from './components/CapturePanel';
import BinGrid         from './components/BinGrid';
import LiveIntakeFeed  from './components/LiveIntakeFeed';
import { useWebSocket }    from './hooks/useWebSocket';
import { useSystemStatus } from './hooks/useSystemStatus';

export default function App() {
  const [events, setEvents] = useState([]);
  const [bins,   setBins]   = useState([]);
  const { status, avgLatency, recordLatency } = useSystemStatus();

  // ── WebSocket event dispatcher ─────────────────────────────────────────────
  const handleEvent = useCallback((event) => {
    switch (event.event_type) {
      case 'INTAKE_CREATED':
        setEvents(prev => [{ ...event, ts: Date.now() }, ...prev]);
        // Mark bin as awaiting
        setBins(prev => {
          const next = prev.filter(b => b.bin_code !== event.assigned_bin);
          return [...next, {
            bin_code: event.assigned_bin,
            led_state: 'awaiting',
            product_name: event.product_name,
            needs_review: event.review_required,
          }];
        });
        if (event.latency_ms) recordLatency(event.latency_ms);
        break;

      case 'BIN_CONFIRMED':
        setBins(prev => prev.map(b =>
          b.bin_code === event.bin_id
            ? { ...b, led_state: 'confirmed' }
            : b
        ));
        // After 2 s, set to off (matching firmware 2-s flash)
        setTimeout(() => {
          setBins(prev => prev.map(b =>
            b.bin_code === event.bin_id ? { ...b, led_state: 'off' } : b
          ));
        }, 2000);
        break;

      case 'EXPIRY_ALERT':
        setBins(prev => prev.map(b =>
          b.bin_code === event.bin_id ? { ...b, led_state: 'expiry' } : b
        ));
        break;

      case 'SYSTEM_STATUS':
        // ESP32 heartbeat — handled by useSystemStatus
        break;

      default:
        break;
    }
  }, [recordLatency]);

  useWebSocket(handleEvent);

  // ── Capture result handler (also fires INTAKE_CREATED via WS, but direct
  //    response is more immediate for the UI) ────────────────────────────────
  const handleCapture = useCallback((data) => {
    // Will be echoed via WS; no duplicate handling needed
  }, []);

  return (
    <div className="app-container">
      <SystemStatusBar status={status} avgLatency={avgLatency} />

      <div className="main-layout">
        <HardwareDashboard recentEvent={events[0]} bins={bins} status={status} />
        <CapturePanel onCapture={handleCapture} />
        <div className="right-column">
          <BinGrid bins={bins} />
          <LiveIntakeFeed events={events} />
        </div>
      </div>
    </div>
  );
}
