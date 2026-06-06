/**
 * BinCard — single bin card with LED state visualisation.
 */
import React from 'react';
import { Circle, CheckCircle2, AlertCircle, Ban, ArrowRight } from 'lucide-react';

const STATE_ICONS = {
  off:         <Circle size={12} style={{ color: 'var(--text-muted)' }} />,
  awaiting:    <ArrowRight size={12} className="animate-pulse" style={{ color: 'var(--accent-green)' }} />,
  confirmed:   <CheckCircle2 size={12} style={{ color: 'var(--accent-cyan)' }} />,
  expiry:      <AlertCircle size={12} style={{ color: 'var(--accent-amber)' }} />,
  quarantine:  <Ban size={12} style={{ color: 'var(--accent-red)' }} />,
};

export default function BinCard({ bin }) {
  const stateKey = bin.led_state || 'off';
  const icon = STATE_ICONS[stateKey] || STATE_ICONS.off;

  return (
    <div className={`bin-card state-${stateKey}`} title={bin.bin_code}>
      <div className="bin-code-label">{bin.bin_code}</div>
      {bin.product_name ? (
        <div className="bin-product" title={bin.product_name}>
          {bin.product_name.length > 10 ? bin.product_name.slice(0, 8) + '..' : bin.product_name}
        </div>
      ) : (
        <div className="bin-product" style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>
          Empty
        </div>
      )}
      <div className="bin-state-badge" style={{ display: 'flex', justifyContent: 'center', marginTop: 4 }}>
        {icon}
      </div>
      {bin.needs_review && (
        <div className="feed-tag review" style={{ marginTop: 3, display: 'inline-block', fontSize: 8, padding: '1px 4px' }}>
          ⚠ Review
        </div>
      )}
    </div>
  );
}
