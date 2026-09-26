import React, { useState, useEffect } from 'react';
import { Key, Plus, Trash2, ToggleLeft, ToggleRight, Copy, Check, ShieldAlert, ShieldCheck } from 'lucide-react';
import { fetchKeys, createKey, toggleKey, deleteKey } from '../api';

export const ApiKeysManager: React.FC = () => {
  const [keys, setKeys] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [newKeyName, setNewKeyName] = useState('');
  const [creating, setCreating] = useState(false);
  const [createdKeyData, setCreatedKeyData] = useState<any | null>(null);
  const [copied, setCopied] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const loadKeys = () => {
    setLoading(true);
    fetchKeys()
      .then(d => setKeys(d.keys || []))
      .catch(err => setErrorMsg(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadKeys();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKeyName.trim()) return;
    setCreating(true);
    setErrorMsg(null);
    try {
      const data = await createKey(newKeyName.trim());
      setCreatedKeyData(data);
      setNewKeyName('');
      loadKeys();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to create API key");
    } finally {
      setCreating(false);
    }
  };

  const handleToggle = async (id: number) => {
    try {
      await toggleKey(id);
      loadKeys();
    } catch (err: any) {
      setErrorMsg(err.message);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Are you sure you want to permanently revoke and delete this API key?")) return;
    try {
      await deleteKey(id);
      loadKeys();
    } catch (err: any) {
      setErrorMsg(err.message);
    }
  };

  const copyKey = (key: string) => {
    navigator.clipboard.writeText(key);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">API Authentication & Keys</h1>
          <p className="page-subtitle">Manage client API keys. Stored securely with SHA-256 hashes on the backend.</p>
        </div>
      </div>

      {errorMsg && (
        <div style={{ padding: '12px 16px', background: 'rgba(244,63,94,0.1)', border: '1px solid rgba(244,63,94,0.3)', borderRadius: 'var(--radius-md)', color: '#FB7185', fontSize: '0.85rem', marginBottom: '18px' }}>
          {errorMsg}
        </div>
      )}

      {/* Created Key Modal/Banner */}
      {createdKeyData && (
        <div className="card" style={{ marginBottom: '24px', border: '1px solid var(--accent-emerald)', background: 'rgba(16, 185, 129, 0.08)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#34D399', fontWeight: 700, marginBottom: '6px' }}>
            <ShieldCheck size={18} /> API Key Generated Successfully
          </div>
          <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '12px' }}>
            Copy your new API key now. For your security, this key is never stored in plain text and <strong>cannot be displayed again</strong>.
          </p>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <code style={{ flex: 1, background: '#060911', padding: '10px 14px', borderRadius: 'var(--radius-md)', color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)', fontSize: '0.85rem', border: '1px solid var(--border-color)' }}>
              {createdKeyData.api_key}
            </code>
            <button className="btn btn-primary" onClick={() => copyKey(createdKeyData.api_key)}>
              {copied ? <Check size={15} /> : <Copy size={15} />}
              {copied ? "Copied!" : "Copy Key"}
            </button>
            <button className="btn btn-secondary" onClick={() => setCreatedKeyData(null)}>
              Done
            </button>
          </div>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '360px 1fr', gap: '24px', alignItems: 'start' }}>
        {/* Create Key Card */}
        <div className="card">
          <h2 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Plus size={16} color="var(--accent-cyan)" /> Generate New Key
          </h2>
          <form onSubmit={handleCreate}>
            <div className="form-group">
              <label className="form-label">Key Name / Client Identifier</label>
              <input
                type="text"
                className="form-input"
                placeholder="e.g. Mobile App Client, Production Webhook"
                value={newKeyName}
                onChange={e => setNewKeyName(e.target.value)}
                required
              />
            </div>
            <button type="submit" className="btn btn-primary" disabled={creating} style={{ width: '100%' }}>
              <Key size={15} />
              {creating ? "Generating..." : "Generate API Key"}
            </button>
          </form>

          <div style={{ marginTop: '20px', padding: '12px', background: 'rgba(255,255,255,0.02)', borderRadius: 'var(--radius-md)', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            <strong>Master Dev Key:</strong> You can also use the default admin master key <code>nexus-dev-master-key-2026</code> in development mode.
          </div>
        </div>

        {/* Existing Keys Table */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
            <h2 style={{ fontSize: '1.05rem', fontWeight: 700 }}>Active Application Keys</h2>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{keys.length} keys total</span>
          </div>

          {loading ? (
            <div style={{ padding: '20px', color: 'var(--text-muted)' }}>Loading keys...</div>
          ) : keys.length === 0 ? (
            <div style={{ padding: '20px', color: 'var(--text-muted)' }}>No API keys created yet.</div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.82rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)' }}>
                    <th style={{ padding: '10px' }}>Name</th>
                    <th style={{ padding: '10px' }}>Prefix</th>
                    <th style={{ padding: '10px' }}>Status</th>
                    <th style={{ padding: '10px' }}>Created</th>
                    <th style={{ padding: '10px' }}>Last Used</th>
                    <th style={{ padding: '10px', textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {keys.map(k => (
                    <tr key={k.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                      <td style={{ padding: '12px 10px', fontWeight: 600 }}>{k.name}</td>
                      <td style={{ padding: '12px 10px' }}>
                        <code style={{ color: 'var(--accent-cyan)' }}>{k.key_prefix}••••</code>
                      </td>
                      <td style={{ padding: '12px 10px' }}>
                        <span className={`badge ${k.is_active ? 'badge-active' : 'badge-disabled'}`}>
                          {k.is_active ? 'Active' : 'Revoked'}
                        </span>
                      </td>
                      <td style={{ padding: '12px 10px', color: 'var(--text-muted)' }}>
                        {k.created_at ? new Date(k.created_at).toLocaleDateString() : '-'}
                      </td>
                      <td style={{ padding: '12px 10px', color: 'var(--text-muted)' }}>
                        {k.last_used_at ? new Date(k.last_used_at).toLocaleTimeString() : 'Never'}
                      </td>
                      <td style={{ padding: '12px 10px', textAlign: 'right' }}>
                        <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end' }}>
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={() => handleToggle(k.id)}
                            title={k.is_active ? "Revoke key" : "Activate key"}
                          >
                            {k.is_active ? <ToggleRight size={14} color="var(--accent-emerald)" /> : <ToggleLeft size={14} color="var(--accent-rose)" />}
                          </button>
                          <button className="btn btn-danger btn-sm" onClick={() => handleDelete(k.id)} title="Delete key">
                            <Trash2 size={13} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
