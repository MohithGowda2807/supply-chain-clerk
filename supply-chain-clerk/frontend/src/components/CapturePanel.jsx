import React, { useState, useRef, useCallback, useEffect } from 'react';
import { Camera, UploadCloud, Info, AlertTriangle, CheckCircle2, Loader2, FastForward, Video, VideoOff } from 'lucide-react';

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
  const [webcamActive, setWebcamActive] = useState(false);
  const inputRef = useRef(null);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);

  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(t => t.stop());
      }
    };
  }, []);

  const startWebcam = useCallback(async () => {
    try {
      setError(null);
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'environment' }
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setWebcamActive(true);
      setPreview(null);
      setFile(null);
      setResult(null);
    } catch (err) {
      setError('Could not access webcam. Make sure it is plugged in and you allowed camera permission.');
    }
  }, []);

  const stopWebcam = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setWebcamActive(false);
  }, []);

  const captureFromWebcam = useCallback(() => {
    if (!videoRef.current || !canvasRef.current) return;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);
    canvas.toBlob((blob) => {
      if (!blob) return;
      const f = new File([blob], 'webcam-capture.jpg', { type: 'image/jpeg' });
      setFile(f);
      setPreview(canvas.toDataURL('image/jpeg'));
      setResult(null);
      setError(null);
      stopWebcam();
    }, 'image/jpeg', 0.92);
  }, [stopWebcam]);

  const handleFile = (f) => {
    if (!f) return;
    if (webcamActive) stopWebcam();
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
      <div className="instructions-card">
        <h2><Info size={18} /> Operating Instructions</h2>
        <ul className="instructions-list">
          <li><span className="step-number">1</span> Place item box on conveyor entry.</li>
          <li><span className="step-number">2</span> Capture or drop the supplier invoice below.</li>
          <li><span className="step-number">3</span> Verify assigned bin on screen.</li>
          <li><span className="step-number">4</span> Wait for IoT conveyor to auto-route the box.</li>
        </ul>
      </div>

      <div className="capture-panel">
        <button
          className="btn-webcam-toggle"
          onClick={webcamActive ? stopWebcam : startWebcam}
          style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
            width: '100%', padding: '10px 16px', marginBottom: 10,
            border: '2px solid #3b82f6', borderRadius: 10, cursor: 'pointer',
            background: webcamActive ? '#ef4444' : '#3b82f6', color: '#fff',
            fontWeight: 700, fontSize: 14, transition: 'all 0.2s ease',
          }}
        >
          {webcamActive ? <><VideoOff size={18} /> Stop Webcam</> : <><Video size={18} /> Open USB Webcam</>}
        </button>

        {webcamActive && (
          <div style={{ position: 'relative', marginBottom: 10 }}>
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              style={{
                width: '100%', borderRadius: 10, border: '3px solid #3b82f6',
                background: '#000',
              }}
            />
            <button
              onClick={captureFromWebcam}
              style={{
                position: 'absolute', bottom: 12, left: '50%', transform: 'translateX(-50%)',
                padding: '10px 28px', background: '#22c55e', color: '#fff', border: 'none',
                borderRadius: 25, fontWeight: 700, fontSize: 14, cursor: 'pointer',
                display: 'flex', alignItems: 'center', gap: 8, 
                boxShadow: '0 4px 15px rgba(0,0,0,0.4)',
              }}
            >
              <Camera size={18} /> Snap Photo
            </button>
          </div>
        )}

        <canvas ref={canvasRef} style={{ display: 'none' }} />
        
        {!webcamActive && (
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
              capture="environment"
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
                <div className="upload-subtext">Or click to browse. Supports JPEG, PNG, scanned PDF.</div>
              </>
            )}
          </div>
        )}

        {!webcamActive && preview && (
          <div style={{ marginBottom: 10 }}>
            <img src={preview} alt="preview" style={{ width: '100%', borderRadius: 10, border: '2px solid var(--border)' }} />
          </div>
        )}

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

        {error && (
          <div className="error-alert">
            <AlertTriangle size={18} style={{ flexShrink: 0 }} />
            <span>{error}</span>
          </div>
        )}

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
