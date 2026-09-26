import React, { useState, useEffect } from 'react';
import { BookOpen, Copy, Check, Terminal, Shield, ArrowRight, Layers, FileCode } from 'lucide-react';
import { fetchConnectorDocs } from '../api';

interface DocumentationProps {
  slug: string;
  apiKey: string;
}

export const Documentation: React.FC<DocumentationProps> = ({ slug, apiKey }) => {
  const [docs, setDocs] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copiedCurl, setCopiedCurl] = useState(false);

  useEffect(() => {
    if (!slug) return;
    setLoading(true);
    fetchConnectorDocs(slug)
      .then(data => setDocs(data))
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [slug]);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCurl(true);
    setTimeout(() => setCopiedCurl(false), 2000);
  };

  if (loading) {
    return <div className="card">Loading documentation for {slug}...</div>;
  }

  if (error || !docs) {
    return <div className="card" style={{ color: 'var(--accent-rose)' }}>{error || "Failed to load documentation."}</div>;
  }

  // Customize cURL with active key if available
  const personalizedCurl = docs.curl_example.replace("YOUR_API_KEY", apiKey || "YOUR_API_KEY");

  return (
    <div>
      <div className="page-header">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h1 className="page-title">{docs.connector_name} API Reference</h1>
            <span className="badge badge-active">{docs.method}</span>
          </div>
          <p className="page-subtitle">{docs.description || "Production-ready generated AI API endpoint documentation."}</p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(350px, 1fr) 460px', gap: '24px', alignItems: 'start' }}>
        {/* Left Column: API Specification */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Endpoint Card */}
          <div className="card">
            <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '12px' }}>Endpoint & Method</h3>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', background: 'var(--bg-primary)', padding: '10px 14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
              <span className="badge badge-active" style={{ fontSize: '0.8rem', padding: '4px 10px' }}>{docs.method}</span>
              <code style={{ fontSize: '0.9rem', color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)' }}>{docs.endpoint}</code>
            </div>

            <div style={{ marginTop: '16px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Content-Type</span>
                <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>{docs.content_type}</div>
              </div>
              <div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Authentication</span>
                <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>{docs.authentication.header}</div>
              </div>
            </div>
          </div>

          {/* Parameters Table */}
          <div className="card">
            <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '12px' }}>Input Parameters</h3>
            {docs.parameters.length === 0 ? (
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>No input parameters required.</p>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.82rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)' }}>
                      <th style={{ padding: '8px 10px' }}>Field</th>
                      <th style={{ padding: '8px 10px' }}>Type</th>
                      <th style={{ padding: '8px 10px' }}>Required</th>
                      <th style={{ padding: '8px 10px' }}>Default</th>
                      <th style={{ padding: '8px 10px' }}>Description</th>
                    </tr>
                  </thead>
                  <tbody>
                    {docs.parameters.map((p: any) => (
                      <tr key={p.name} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                        <td style={{ padding: '10px', fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)', fontWeight: 600 }}>{p.name}</td>
                        <td style={{ padding: '10px' }}><span className="badge" style={{ background: 'rgba(255,255,255,0.05)' }}>{p.type}</span></td>
                        <td style={{ padding: '10px' }}>
                          {p.required ? <span style={{ color: 'var(--accent-rose)', fontWeight: 600 }}>Required</span> : <span style={{ color: 'var(--text-muted)' }}>Optional</span>}
                        </td>
                        <td style={{ padding: '10px', color: 'var(--text-muted)' }}>{p.default !== null && p.default !== undefined ? String(p.default) : "-"}</td>
                        <td style={{ padding: '10px', color: 'var(--text-secondary)' }}>{p.description || "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Expected Output Schema */}
          <div className="card">
            <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '12px' }}>Expected Output Schema</h3>
            <pre className="code-block" style={{ maxHeight: '240px' }}>
              {JSON.stringify(docs.output_schema, null, 2)}
            </pre>
          </div>
        </div>

        {/* Right Column: Code Snippets & cURL */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* cURL Example */}
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
              <h3 style={{ fontSize: '0.95rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Terminal size={15} color="var(--accent-cyan)" /> cURL Request Example
              </h3>
              <button className="btn btn-secondary btn-sm" onClick={() => copyToClipboard(personalizedCurl)}>
                {copiedCurl ? <Check size={13} color="var(--accent-emerald)" /> : <Copy size={13} />}
                {copiedCurl ? "Copied" : "Copy"}
              </button>
            </div>
            <pre className="code-block" style={{ fontSize: '0.78rem' }}>
              {personalizedCurl}
            </pre>
          </div>

          {/* Expected 200 Success Response */}
          <div className="card">
            <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <FileCode size={15} color="var(--accent-emerald)" /> Standard Success Response (200 OK)
            </h3>
            <pre className="code-block" style={{ fontSize: '0.78rem', maxHeight: '260px' }}>
              {JSON.stringify(docs.expected_response, null, 2)}
            </pre>
          </div>

          {/* Standard Error Format */}
          <div className="card">
            <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '10px', color: '#FB7185' }}>
              Predictable Error Response Format
            </h3>
            <pre className="code-block" style={{ fontSize: '0.78rem', color: '#FDA4AF' }}>
{`{
  "success": false,
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR | UNAUTHORIZED | PROVIDER_ERROR",
    "message": "Human-readable explanation of error",
    "details": ["Field 'email' is missing"]
  },
  "meta": {
    "request_id": "REQ-20260927-XXXX",
    "response_time_ms": 14.2
  }
}`}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
};
