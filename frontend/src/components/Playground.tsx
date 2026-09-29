import React, { useState } from 'react';
import { Play, CheckCircle2, AlertTriangle, Clock, Cpu, DollarSign, Layers, Copy, Check } from 'lucide-react';
import { runConnectorApi } from '../api';
import { useConnectorSession } from '../executionStore';

interface PlaygroundProps {
  connector: any;
  apiKey: string;
  onApiKeyChange: (k: string) => void;
}

export const Playground: React.FC<PlaygroundProps> = ({ connector, apiKey, onApiKeyChange }) => {
  // Explicit session state decoupled from connector definitions and parent rerenders
  const {
    formValues: formData,
    files: fileData,
    imagePreviews,
    lastResult: responseResult,
    executionError: errorMsg,
    isExecuting: loading,
    setInput,
    setFile,
    startExecution,
    setExecutionSuccess,
    setExecutionError,
    clearOutput,
  } = useConnectorSession(connector);

  const [copied, setCopied] = useState(false);

  const handleInputChange = (name: string, val: any) => {
    // User editing input never clears output or error
    setInput(name, val);
  };

  const handleFileChange = (name: string, file: File | null) => {
    setFile(name, file);
  };

  const handleRun = async () => {
    if (!connector || loading) return;
    // Start the new request without automatically clearing previous result
    startExecution();

    try {
      // Process JSON field strings
      const payloadToSend = { ...formData };
      for (const inp of connector.inputs || []) {
        if (inp.type === "json" && typeof payloadToSend[inp.name] === "string") {
          try {
            payloadToSend[inp.name] = JSON.parse(payloadToSend[inp.name]);
          } catch (e) {
            // Keep as string to let validator report error
          }
        }
      }

      const res = await runConnectorApi(connector.slug, payloadToSend, apiKey, fileData);
      if (res.ok) {
        setExecutionSuccess(res);
      } else {
        const msg = res.data?.error?.message || `Request failed with error status (${res.status})`;
        setExecutionError(msg, res);
      }
    } catch (err: any) {
      setExecutionError(err.message || "Network error connecting to API");
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!connector) {
    return <div className="card">Select a connector to begin testing.</div>;
  }

  const meta = responseResult?.data?.meta;
  const isSuccess = responseResult?.data?.success ?? (responseResult ? responseResult.ok : false);
  const traceSteps = meta?.trace || [];

  return (
    <div>
      <div className="page-header">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h1 className="page-title">{connector.name}</h1>
            <span className={`badge ${connector.is_active ? 'badge-active' : 'badge-disabled'}`}>
              {connector.is_active ? 'Active' : 'Disabled'}
            </span>
          </div>
          <p className="page-subtitle">Interactive playground. Input form dynamically generated from connector specifications.</p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', fontWeight: 600 }}>Authorization Header</span>
            <input
              type="text"
              className="form-input"
              value={apiKey}
              onChange={(e) => onApiKeyChange(e.target.value)}
              placeholder="X-API-Key..."
              style={{ width: '260px', padding: '6px 10px', fontSize: '0.8rem', fontFamily: 'var(--font-mono)' }}
            />
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(350px, 45%) 1fr', gap: '24px', alignItems: 'start' }}>
        {/* Dynamic Form Inputs */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h2 style={{ fontSize: '1.05rem', fontWeight: 700 }}>Dynamic Request Parameters</h2>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{connector.inputs?.length || 0} fields</span>
          </div>

          <form onSubmit={(e) => { e.preventDefault(); handleRun(); }}>
            {connector.inputs?.length === 0 && (
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '16px' }}>No input parameters configured.</p>
            )}

            {connector.inputs?.map((inp: any) => (
              <div key={inp.name} className="form-group">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span>{inp.name}</span>
                    {inp.is_required ? (
                      <span style={{ color: 'var(--accent-rose)', fontSize: '0.75rem' }}>*required</span>
                    ) : (
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>(optional)</span>
                    )}
                  </label>
                  <span className="badge" style={{ background: 'rgba(255,255,255,0.04)', fontSize: '0.68rem' }}>{inp.type}</span>
                </div>

                {inp.description && (
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>{inp.description}</span>
                )}

                {/* Text Input */}
                {inp.type === "text" && (
                  inp.name.includes("body") || inp.name.includes("text") || inp.name.includes("article") ? (
                    <textarea
                      className="form-textarea"
                      rows={4}
                      value={formData[inp.name] || ""}
                      onChange={(e) => handleInputChange(inp.name, e.target.value)}
                      placeholder={`Enter ${inp.name}...`}
                    />
                  ) : (
                    <input
                      type="text"
                      className="form-input"
                      value={formData[inp.name] || ""}
                      onChange={(e) => handleInputChange(inp.name, e.target.value)}
                      placeholder={`Enter ${inp.name}...`}
                    />
                  )
                )}

                {/* Number Input */}
                {inp.type === "number" && (
                  <input
                    type="number"
                    className="form-input"
                    value={formData[inp.name] !== undefined ? formData[inp.name] : ""}
                    onChange={(e) => handleInputChange(inp.name, e.target.value === "" ? "" : Number(e.target.value))}
                  />
                )}

                {/* Boolean Input */}
                {inp.type === "boolean" && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '4px' }}>
                    <input
                      type="checkbox"
                      id={`chk-${inp.name}`}
                      checked={Boolean(formData[inp.name])}
                      onChange={(e) => handleInputChange(inp.name, e.target.checked)}
                      style={{ width: '18px', height: '18px', accentColor: 'var(--accent-cyan)' }}
                    />
                    <label htmlFor={`chk-${inp.name}`} style={{ fontSize: '0.85rem', cursor: 'pointer' }}>
                      {formData[inp.name] ? "True" : "False"}
                    </label>
                  </div>
                )}

                {/* JSON Input */}
                {inp.type === "json" && (
                  <textarea
                    className="form-textarea code-editor"
                    rows={4}
                    value={typeof formData[inp.name] === "object" ? JSON.stringify(formData[inp.name], null, 2) : formData[inp.name] || "{}"}
                    onChange={(e) => handleInputChange(inp.name, e.target.value)}
                    placeholder="Enter valid JSON object..."
                  />
                )}

                {/* Image Input */}
                {inp.type === "image" && (
                  <div>
                    <input
                      type="file"
                      accept="image/*"
                      className="form-input"
                      style={{ padding: '7px' }}
                      onChange={(e) => handleFileChange(inp.name, e.target.files?.[0] || null)}
                    />
                    {imagePreviews[inp.name] && (
                      <div style={{ marginTop: '8px', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', overflow: 'hidden', maxHeight: '160px', width: 'fit-content' }}>
                        <img src={imagePreviews[inp.name]} alt="Preview" style={{ height: '140px', objectFit: 'contain', display: 'block' }} />
                      </div>
                    )}
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '4px', display: 'block' }}>
                      Or pass image Base64 in JSON payload.
                    </span>
                  </div>
                )}

                {/* File Input */}
                {inp.type === "file" && (
                  <div>
                    <input
                      type="file"
                      className="form-input"
                      style={{ padding: '7px' }}
                      onChange={(e) => handleFileChange(inp.name, e.target.files?.[0] || null)}
                    />
                  </div>
                )}
              </div>
            ))}

            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading || !connector.is_active}
              style={{ width: '100%', marginTop: '12px', padding: '12px' }}
            >
              {loading ? "Executing API Pipeline..." : (
                <>
                  <Play size={16} />
                  Execute API Test
                </>
              )}
            </button>
          </form>
        </div>

        {/* Live Execution Results & Trace */}
        <div>
          {/* In-Flight Execution Banner (Visible when loading without wiping previous result) */}
          {loading && (
            <div className="card" style={{ marginBottom: '18px', display: 'flex', alignItems: 'center', gap: '12px', background: 'rgba(6,182,212,0.08)', borderColor: 'rgba(6,182,212,0.3)' }}>
              <div style={{ width: '18px', height: '18px', border: '2px solid rgba(6,182,212,0.3)', borderTopColor: 'var(--accent-cyan)', borderRadius: '50%', animation: 'spin 0.8s linear infinite', flexShrink: 0 }} />
              <div>
                <div style={{ fontSize: '0.85rem', color: 'var(--accent-cyan)', fontWeight: 600 }}>Executing API Pipeline...</div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Calling provider adapter &amp; validating response schema. Previous output preserved below.</div>
              </div>
              <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
            </div>
          )}

          {/* Status Banner */}
          {responseResult && (
            <div className="card" style={{ marginBottom: '18px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  {isSuccess ? (
                    <span className="badge badge-active" style={{ fontSize: '0.85rem', padding: '4px 12px' }}>
                      <CheckCircle2 size={16} /> HTTP 200 OK
                    </span>
                  ) : (
                    <span className="badge badge-disabled" style={{ fontSize: '0.85rem', padding: '4px 12px' }}>
                      <AlertTriangle size={16} /> Error ({responseResult.status})
                    </span>
                  )}
                  {meta?.request_id && (
                    <code style={{ fontSize: '0.8rem', color: 'var(--accent-cyan)' }}>{meta.request_id}</code>
                  )}
                </div>

                <div style={{ display: 'flex', gap: '14px', alignItems: 'center' }}>
                  {meta?.response_time_ms !== undefined && (
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Clock size={14} color="var(--accent-violet)" /> {meta.response_time_ms} ms
                    </span>
                  )}
                  {meta?.tokens?.total !== undefined && (
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Layers size={14} color="var(--accent-blue)" /> {meta.tokens.total} tokens
                    </span>
                  )}
                  {meta?.estimated_cost_usd !== undefined && (
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <DollarSign size={14} color="var(--accent-amber)" /> ${meta.estimated_cost_usd.toFixed(6)}
                    </span>
                  )}
                </div>
              </div>

              {/* Routing & Fallback Audit Notice */}
              {meta?.routing && (
                <div style={{ marginTop: '14px', padding: '10px 14px', background: 'rgba(139, 92, 246, 0.08)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(139, 92, 246, 0.2)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.82rem', fontWeight: 600, color: '#A78BFA' }}>
                    <Cpu size={14} /> Intelligent Routing Decision ({meta.routing.strategy.toUpperCase()})
                  </div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                    <strong>Selected:</strong> {meta.provider} / {meta.model} &nbsp;|&nbsp; <strong>Reason:</strong> {meta.routing.reason}
                  </div>
                  {meta.fallback_used && (
                    <div style={{ marginTop: '6px', color: 'var(--accent-amber)', fontSize: '0.75rem', fontWeight: 600 }}>
                      Notice: Primary model experienced transient failure. Automatic fallback routed to {meta.fallback_info?.provider}/{meta.fallback_info?.model}.
                    </div>
                  )}
                  {meta.repair_attempted && (
                    <div style={{ marginTop: '4px', color: 'var(--accent-emerald)', fontSize: '0.75rem', fontWeight: 600 }}>
                      Automatic Response Repair: Successfully repaired response schema format.
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Response Payload Display */}
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h3 style={{ fontSize: '0.95rem', fontWeight: 700 }}>Structured Response Output</h3>
                {loading && (
                  <span className="badge" style={{ background: 'rgba(6,182,212,0.15)', color: 'var(--accent-cyan)', fontSize: '0.72rem' }}>
                    Executing...
                  </span>
                )}
              </div>
              {(responseResult || errorMsg) && (
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={clearOutput}
                  >
                    Clear Output
                  </button>
                  {responseResult?.data && (
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={() => copyToClipboard(JSON.stringify(responseResult.data, null, 2))}
                    >
                      {copied ? <Check size={13} color="var(--accent-emerald)" /> : <Copy size={13} />}
                      {copied ? "Copied" : "Copy JSON"}
                    </button>
                  )}
                </div>
              )}
            </div>

            {/* Error Message Box */}
            {errorMsg && (
              <div style={{ padding: '14px', background: 'rgba(244,63,94,0.1)', border: '1px solid rgba(244,63,94,0.3)', borderRadius: 'var(--radius-md)', color: '#FB7185', fontSize: '0.85rem', marginBottom: responseResult ? '12px' : '0' }}>
                <strong>Execution Error:</strong> {errorMsg}
              </div>
            )}

            {/* When loading and no prior result exists */}
            {loading && !responseResult && !errorMsg && (
              <div style={{ padding: '36px 0', textAlign: 'center', color: 'var(--text-secondary)' }}>
                <div style={{ display: 'inline-block', width: '30px', height: '30px', border: '3px solid rgba(6,182,212,0.2)', borderTopColor: 'var(--accent-cyan)', borderRadius: '50%', animation: 'spin 0.8s linear infinite', marginBottom: '12px' }} />
                <p style={{ fontSize: '0.85rem' }}>Calling provider adapter &amp; executing schema validation...</p>
                <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
              </div>
            )}

            {/* Structured response payload */}
            {responseResult && (
              <pre className="code-block" style={{ maxHeight: '420px', overflowY: 'auto', opacity: loading ? 0.7 : 1 }}>
                {JSON.stringify(responseResult.data, null, 2)}
              </pre>
            )}

            {/* Initial empty state */}
            {!loading && !responseResult && !errorMsg && (
              <div style={{ padding: '40px 0', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                Fill out the dynamic input fields on the left and click <strong>Execute API Test</strong> to view real-time results and request trace.
              </div>
            )}
          </div>

          {/* Execution Trace Timeline */}
          {traceSteps.length > 0 && (
            <div className="card" style={{ marginTop: '18px' }}>
              <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '12px' }}>Request Execution Trace</h3>
              <div className="trace-timeline">
                {traceSteps.map((step: any, idx: number) => (
                  <div key={idx} className={`trace-step ${step.status}`}>
                    <div style={{ width: '100%' }}>
                      <div className="trace-step-title" style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span>{idx + 1}. {step.step}</span>
                        <span style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: step.status === 'ok' ? 'var(--accent-emerald)' : step.status === 'warning' ? 'var(--accent-amber)' : 'var(--accent-rose)' }}>
                          {step.status}
                        </span>
                      </div>
                      <div className="trace-step-desc">{step.detail}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
