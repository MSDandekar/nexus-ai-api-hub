import React, { useState, useEffect } from 'react';
import { Activity, Search, RefreshCw, Eye, CheckCircle2, AlertTriangle, Layers, Clock, DollarSign, X } from 'lucide-react';
import { fetchLogs } from '../api';

export const LogsViewer: React.FC = () => {
  const [logs, setLogs] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [connectorFilter, setConnectorFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [selectedLog, setSelectedLog] = useState<any | null>(null);

  const loadData = () => {
    setLoading(true);
    fetchLogs(50, 0, connectorFilter || undefined, statusFilter || undefined)
      .then(d => {
        setLogs(d.logs || []);
        setTotal(d.total || 0);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, [connectorFilter, statusFilter]);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Persistent Request Logs</h1>
          <p className="page-subtitle">Complete audit logs of every gateway invocation with token consumption, routing decisions, and error details.</p>
        </div>
        <button className="btn btn-secondary btn-sm" onClick={loadData} disabled={loading}>
          <RefreshCw size={14} className={loading ? "spin" : ""} /> Refresh Logs
        </button>
      </div>

      {/* Filter Bar */}
      <div className="card" style={{ marginBottom: '20px', padding: '16px 20px', display: 'flex', gap: '14px', flexWrap: 'wrap', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Search size={15} color="var(--text-muted)" />
          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontWeight: 600 }}>Filter by:</span>
        </div>
        <input
          type="text"
          className="form-input"
          placeholder="Connector slug..."
          value={connectorFilter}
          onChange={e => setConnectorFilter(e.target.value)}
          style={{ width: '200px', padding: '6px 10px', fontSize: '0.8rem' }}
        />
        <select
          className="form-select"
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}
          style={{ width: '160px', padding: '6px 10px', fontSize: '0.8rem' }}
        >
          <option value="">All Statuses</option>
          <option value="success">Success</option>
          <option value="repaired">Repaired</option>
          <option value="failure">Failure</option>
        </select>
        <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginLeft: 'auto' }}>
          Showing {logs.length} of {total} stored logs
        </span>
      </div>

      {/* Logs Table */}
      <div className="card">
        {loading ? (
          <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)' }}>Loading persistent logs...</div>
        ) : logs.length === 0 ? (
          <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)' }}>No request logs found.</div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.8rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)' }}>
                  <th style={{ padding: '10px' }}>Request ID</th>
                  <th style={{ padding: '10px' }}>Connector</th>
                  <th style={{ padding: '10px' }}>Timestamp</th>
                  <th style={{ padding: '10px' }}>Provider / Model</th>
                  <th style={{ padding: '10px' }}>Status</th>
                  <th style={{ padding: '10px' }}>Latency</th>
                  <th style={{ padding: '10px' }}>Tokens</th>
                  <th style={{ padding: '10px' }}>Cost</th>
                  <th style={{ padding: '10px', textAlign: 'right' }}>Payload</th>
                </tr>
              </thead>
              <tbody>
                {logs.map(l => (
                  <tr key={l.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <td style={{ padding: '10px', fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)' }}>
                      {l.request_id}
                    </td>
                    <td style={{ padding: '10px', fontWeight: 600 }}>{l.connector_slug}</td>
                    <td style={{ padding: '10px', color: 'var(--text-muted)' }}>
                      {l.timestamp ? new Date(l.timestamp).toLocaleTimeString() : '-'}
                    </td>
                    <td style={{ padding: '10px' }}>
                      <div style={{ display: 'flex', flexDirection: 'column' }}>
                        <span>{l.provider} / {l.model}</span>
                        {l.fallback_used && (
                          <span style={{ fontSize: '0.7rem', color: 'var(--accent-amber)' }}>Fallback from {l.fallback_provider}</span>
                        )}
                      </div>
                    </td>
                    <td style={{ padding: '10px' }}>
                      <span className={`badge ${l.status === 'success' ? 'badge-active' : l.status === 'repaired' ? 'badge-routing' : 'badge-disabled'}`}>
                        {l.status}
                      </span>
                    </td>
                    <td style={{ padding: '10px', color: 'var(--text-secondary)' }}>
                      {l.response_time_ms ? `${l.response_time_ms} ms` : '-'}
                    </td>
                    <td style={{ padding: '10px', color: 'var(--text-secondary)' }}>
                      {l.tokens?.total || 0}
                    </td>
                    <td style={{ padding: '10px', color: 'var(--accent-amber)', fontFamily: 'var(--font-mono)' }}>
                      ${l.estimated_cost_usd ? l.estimated_cost_usd.toFixed(6) : "0.000000"}
                    </td>
                    <td style={{ padding: '10px', textAlign: 'right' }}>
                      <button className="btn btn-secondary btn-sm" onClick={() => setSelectedLog(l)}>
                        <Eye size={12} /> Inspect
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Payload Inspector Modal */}
      {selectedLog && (
        <div className="modal-backdrop">
          <div className="modal-content" style={{ maxWidth: '800px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div>
                <h2 style={{ fontSize: '1.15rem', fontWeight: 800 }}>Request Inspection: {selectedLog.request_id}</h2>
                <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                  Connector: {selectedLog.connector_slug} &nbsp;|&nbsp; Status: {selectedLog.status}
                </span>
              </div>
              <button className="btn btn-secondary btn-sm" onClick={() => setSelectedLog(null)}><X size={15} /></button>
            </div>

            {selectedLog.error_message && (
              <div style={{ padding: '10px 14px', background: 'rgba(244,63,94,0.1)', border: '1px solid rgba(244,63,94,0.3)', borderRadius: 'var(--radius-md)', color: '#FB7185', fontSize: '0.82rem', marginBottom: '14px' }}>
                <strong>Error:</strong> {selectedLog.error_code} - {selectedLog.error_message}
              </div>
            )}

            {selectedLog.routing_reason && (
              <div style={{ padding: '10px 14px', background: 'rgba(139,92,246,0.08)', border: '1px solid rgba(139,92,246,0.2)', borderRadius: 'var(--radius-md)', fontSize: '0.8rem', color: '#A78BFA', marginBottom: '14px' }}>
                <strong>Routing ({selectedLog.routing_strategy}):</strong> {selectedLog.routing_reason}
              </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
              <div>
                <h4 style={{ fontSize: '0.85rem', fontWeight: 700, marginBottom: '6px' }}>Input Parameters</h4>
                <pre className="code-block" style={{ maxHeight: '280px', fontSize: '0.75rem' }}>
                  {selectedLog.request_payload ? JSON.stringify(JSON.parse(selectedLog.request_payload), null, 2) : "No request payload recorded"}
                </pre>
              </div>

              <div>
                <h4 style={{ fontSize: '0.85rem', fontWeight: 700, marginBottom: '6px' }}>AI Response Output</h4>
                <pre className="code-block" style={{ maxHeight: '280px', fontSize: '0.75rem' }}>
                  {selectedLog.response_payload ? JSON.stringify(JSON.parse(selectedLog.response_payload), null, 2) : "No response payload recorded"}
                </pre>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
