import React, { useState, useRef } from 'react';
import { Camera, UploadCloud, Info, AlertTriangle, CheckCircle2, Loader2, FastForward } from 'lucide-react';

function ConfidencePill({ value }) {
  if (value === undefined || value === null) return null;
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
      const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      const res = await fetch(`${baseUrl}/intake/capture`, {
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
    <div className="intake-column">
      {/* Operating Instructions — compact horizontal layout */}
      <div className="instructions-card">
        <h2><Info size={18} /> Operating Instructions</h2>
        <ul className="instructions-list">
          <li><span className="step-number">1</span> Place item box on conveyor entry.</li>
          <li><span className="step-number">2</span> Capture or drop the supplier invoice below.</li>
          <li><span className="step-number">3</span> Verify assigned bin on screen.</li>
          <li><span className="step-number">4</span> Wait for IoT conveyor to auto-route the box.</li>
        </ul>
      </div>

      {/* Capture Panel */}
      <div className="capture-panel">
        
        {/* Drop zone */}
        <div
          className={`upload-zone ${dragOver ? 'drag-over' : ''} ${preview ? 'has-preview' : ''}`}
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
              <div className="upload-icon">
                <UploadCloud size={36} />
              </div>
              <div className="upload-text">Drop Invoice Document Here</div>
              <div className="upload-subtext">Supports JPEG, PNG, scanned PDF, or handwriting.</div>
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
            <><Loader2 className="spinner" size={18} /> Processing AI Extraction...</>
          ) : (
            <><Camera size={18} /> Capture & Process</>
          )}
        </button>

        {/* Error */}
        {error && (
          <div className="error-alert">
            <AlertTriangle size={18} style={{ flexShrink: 0 }} />
            <span>{error}</span>
          </div>
        )}

        {/* Result */}
        {result && (
          <>
            <div className="assigned-bin-banner">
              <div>
                <div style={{ fontSize: 12, color: '#166534', fontWeight: 700, marginBottom: 4, display: 'flex', alignItems: 'center', gap: 4 }}>
                  <CheckCircle2 size={14} />
                  Assigned Bin
                </div>
                <div className="bin-code">{result.assigned_bin}</div>
              </div>
              <div style={{ textAlign: 'right', display: 'flex', flexDirection: 'column', gap: 6, alignItems: 'flex-end' }}>
                <ConfidencePill value={result.overall_confidence} />
                {result.review_required && (
                  <div style={{ fontSize: 11, color: '#DC2626', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 4 }}>
                    <AlertTriangle size={12} /> Needs Review
                  </div>
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
              <div className="result-field" style={{ marginTop: 8, paddingTop: 8, borderTop: '2px dashed var(--border)'}}>
                <span className="result-label" style={{ display: 'flex', alignItems: 'center', gap: 6}}>
                  <FastForward size={12}/> Parsing Latency
                </span>
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
