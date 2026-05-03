/**
 * CapturePanel — document upload + Gemini extraction result display.
 */
import React, { useState, useRef } from 'react';

function ConfidencePill({ value }) {
  const pct = Math.round(value * 100);
  const cls = value >= 0.9 ? 'high' : value >= 0.75 ? 'medium' : 'low';
  return <span className={`confidence-pill ${cls}`}>{pct}%</span>;
}

function Field({ label, field }) {
  if (!field) return null;
  return (
    <div className="result-field">
      <span className="result-label">{label}</span>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <span className="result-value">{field.value ?? '—'}</span>
        <ConfidencePill value={field.confidence} />
      </div>
    </div>
  );
}

export default function CapturePanel({ onCapture }) {
  const [preview, setPreview] = useState(null);
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef(null);

  const handleFile = (f) => {
    if (!f) return;
    setFile(f);
    setResult(null);
    setError(null);
    const reader = new FileReader();
    reader.onload = (e) => setPreview(e.target.result);
    reader.readAsDataURL(f);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  };

  const capture = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const form = new FormData();
      form.append('file', file);
      const res = await fetch('http://localhost:8000/intake/capture', {
        method: 'POST',
        body: form,
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setResult(data);
      onCapture?.(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="panel capture-panel">
      <div className="panel-header">
        <span className="panel-title"><span className="icon">📷</span> Document Capture</span>
      </div>

      <div style={{ padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 10 }}>
        {/* Drop zone */}
        <div
          className={`upload-zone ${dragOver ? 'drag-over' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
        >
          <input
            ref={inputRef}
            type="file"
            accept="image/*"
            style={{ display: 'none' }}
            onChange={(e) => handleFile(e.target.files[0])}
          />
          {preview ? (
            <img src={preview} alt="preview" className="preview-image" />
          ) : (
            <>
              <span className="upload-icon">📄</span>
              <div className="upload-text">Drop invoice / packing slip here</div>
              <div className="upload-subtext">JPEG, PNG, or scanned PDF image · any handwriting</div>
            </>
          )}
        </div>

        {/* Capture button */}
        <button
          className="btn-capture"
          onClick={capture}
          disabled={!file || loading}
          id="btn-capture"
        >
          {loading ? (
            <><div className="spinner" /> Extracting with Gemini…</>
          ) : (
            <><span>⚡</span> Capture & Process</>
          )}
        </button>

        {/* Error */}
        {error && (
          <div style={{
            background: 'rgba(239,68,68,0.1)',
            border: '1px solid rgba(239,68,68,0.25)',
            borderRadius: 8, padding: '10px 12px',
            fontSize: 12, color: '#ef4444'
          }}>
            ⚠ {error}
          </div>
        )}

        {/* Result */}
        {result && (
          <>
            <div className="assigned-bin-banner">
              <div>
                <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 2 }}>Assigned Bin</div>
                <div className="bin-code">{result.assigned_bin}</div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <ConfidencePill value={result.overall_confidence} />
                {result.review_required && (
                  <div style={{ fontSize: 11, color: 'var(--accent-red)', marginTop: 4 }}>⚠ Needs Review</div>
                )}
              </div>
            </div>

            <div className="result-card">
              <Field label="Batch No."       field={result.record.batch_no} />
              <Field label="Product"         field={result.record.product_name} />
              <Field label="Supplier"        field={result.record.supplier_name} />
              <Field label="Expiry"          field={result.record.expiry_date} />
              <Field label="Quantity"        field={result.record.quantity} />
              <Field label="Unit"            field={result.record.unit_of_measure} />
              <div className="result-field">
                <span className="result-label">Latency</span>
                <span className="result-value" style={{ color: 'var(--accent-cyan)' }}>
                  {result.latency_ms} ms
                </span>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
