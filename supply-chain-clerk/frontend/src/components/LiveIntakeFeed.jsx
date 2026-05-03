/**
 * LiveIntakeFeed — scrollable list of last 20 intake events.
 */
import React, { useState } from 'react';

function timeAgo(ts) {
  if (!ts) return '';
  const diff = Math.floor((Date.now() - ts) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff/60)}m ago`;
  return `${Math.floor(diff/3600)}h ago`;
}

function ReviewModal({ item, onClose }) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title">Review — {item.product_name}</div>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        <div className="modal-body">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            {Object.entries(item.record || {}).map(([key, field]) => (
              <div key={key} style={{
                background: 'var(--bg-700)',
                borderRadius: 8, padding: '10px 12px',
                border: '1px solid var(--border)'
              }}>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 4 }}>{key.replace(/_/g,' ')}</div>
                <div style={{ fontSize: 13, fontFamily: 'JetBrains Mono, monospace' }}>
                  {field?.value ?? <span style={{ color: 'var(--accent-red)' }}>null</span>}
                </div>
                <div style={{ fontSize: 11, color: field?.confidence >= 0.75 ? 'var(--accent-green)' : 'var(--accent-red)', marginTop: 4 }}>
                  {Math.round((field?.confidence || 0) * 100)}% confidence
                </div>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 16, display: 'flex', gap: 10 }}>
            <span className="feed-tag bin">Bin: {item.assigned_bin}</span>
            <span className="feed-tag batch">ID: {item.intake_id?.slice(-8)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function LiveIntakeFeed({ events }) {
  const [review, setReview] = useState(null);

  return (
    <div className="panel live-feed-panel">
      <div className="panel-header">
        <span className="panel-title"><span className="icon">📋</span> Live Intake Feed</span>
        <span className="panel-count">{Math.min(events.length, 20)}</span>
      </div>

      <div className="feed-list">
        {events.length === 0 ? (
          <div className="empty-state">
            <span className="empty-icon">📭</span>
            <span>Waiting for intake events…</span>
            <span style={{ fontSize: 11 }}>Capture a document to begin</span>
          </div>
        ) : (
          events.slice(0, 20).map((ev, i) => (
            <div
              key={ev.intake_id || i}
              className={`feed-item ${ev.review_required ? 'review-required' : ''}`}
              onClick={() => ev.review_required && setReview(ev)}
            >
              <div className="feed-item-header">
                <div className="feed-product">{ev.product_name || 'Unknown Product'}</div>
                <div className="feed-time">{timeAgo(ev.ts)}</div>
              </div>
              <div className="feed-meta">
                <span className="feed-tag bin">📦 {ev.assigned_bin}</span>
                {ev.batch_no && <span className="feed-tag batch">{ev.batch_no}</span>}
                <span className={`confidence-pill ${
                  ev.confidence >= 0.9 ? 'high' : ev.confidence >= 0.75 ? 'medium' : 'low'
                }`}>{Math.round((ev.confidence || 0)*100)}%</span>
                {ev.review_required && <span className="feed-tag review">⚠ Review</span>}
              </div>
            </div>
          ))
        )}
      </div>

      {review && <ReviewModal item={review} onClose={() => setReview(null)} />}
    </div>
  );
}
