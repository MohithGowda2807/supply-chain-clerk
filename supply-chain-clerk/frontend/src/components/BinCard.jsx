/**
 * BinCard — single bin card with LED state visualisation.
 */
import React from 'react';

const STATE_LABELS = {
  off:         { emoji: '○', label: 'Empty' },
  awaiting:    { emoji: '🟢', label: 'Awaiting' },
  confirmed:   { emoji: '✅', label: 'Confirmed' },
  expiry:      { emoji: '🟡', label: 'Near Expiry' },
  quarantine:  { emoji: '🔴', label: 'Quarantine' },
};

export default function BinCard({ bin }) {
  const stateKey = bin.led_state || 'off';
  const info = STATE_LABELS[stateKey] || STATE_LABELS.off;

  return (
    <div className={`bin-card state-${stateKey}`} title={bin.bin_code}>
      <div className="bin-code-label">{bin.bin_code}</div>
      {bin.product_name && (
        <div className="bin-product">{bin.product_name.slice(0, 12)}</div>
      )}
      <div className="bin-state-badge">{info.emoji}</div>
      {bin.needs_review && (
        <div className="feed-tag review" style={{ marginTop: 4, display: 'inline-block', fontSize: 9 }}>⚠</div>
      )}
    </div>
  );
}
