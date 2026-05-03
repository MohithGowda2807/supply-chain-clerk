/**
 * BinGrid — 20-bin warehouse grid grouped by zone.
 */
import React from 'react';
import BinCard from './BinCard';

const INITIAL_BINS = [
  // Herbal zone
  ...['A01','A02','A03','A04','A05','A06','A07'].map((c, i) => ({ bin_code: c, zone: 'herbal', led_index: i, led_state: 'off' })),
  // Analgesic zone
  ...['B01','B02','B03','B04','B05','B06'].map((c, i) => ({ bin_code: c, zone: 'analgesic', led_index: 7+i, led_state: 'off' })),
  // Supplement zone
  ...['C01','C02','C03','C04','C05','C06','C07'].map((c, i) => ({ bin_code: c, zone: 'supplement', led_index: 13+i, led_state: 'off' })),
];

const ZONE_LABELS = { herbal: '🌿 Herbal Zone', analgesic: '💊 Analgesic Zone', supplement: '🧴 Supplement Zone' };

export default function BinGrid({ bins }) {
  const allBins = INITIAL_BINS.map(initial => {
    const live = bins.find(b => b.bin_code === initial.bin_code);
    return live ? { ...initial, ...live } : initial;
  });

  const zones = ['herbal', 'analgesic', 'supplement'];

  return (
    <div className="panel bin-grid-panel">
      <div className="panel-header">
        <span className="panel-title"><span className="icon">🏭</span> Warehouse Twin</span>
        <span className="panel-count">{allBins.filter(b => b.led_state !== 'off').length}/{allBins.length} active</span>
      </div>
      <div className="bin-grid">
        {zones.map(zone => (
          <React.Fragment key={zone}>
            <div className="zone-label">{ZONE_LABELS[zone]}</div>
            {allBins.filter(b => b.zone === zone).map(bin => (
              <BinCard key={bin.bin_code} bin={bin} />
            ))}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}
