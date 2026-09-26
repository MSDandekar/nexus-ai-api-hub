import React from 'react';
import { Activity, Cpu, Layers, DollarSign, Clock, ShieldCheck, Play, BookOpen, ToggleLeft, ToggleRight, Trash2, Edit3, Plus, Sparkles } from 'lucide-react';

interface DashboardProps {
  metrics: any;
  connectors: any[];
  onOpenTest: (slug: string) => void;
  onOpenDocs: (slug: string) => void;
  onOpenEdit: (connector: any) => void;
  onToggleStatus: (slug: string) => void;
  onDelete: (slug: string) => void;
  onOpenCreate: () => void;
  onOpenBlueprint: () => void;
}

export const Dashboard: React.FC<DashboardProps> = ({
  metrics,
  connectors,
  onOpenTest,
  onOpenDocs,
  onOpenEdit,
  onToggleStatus,
  onDelete,
  onOpenCreate,
  onOpenBlueprint
}) => {
  const overview = metrics?.overview || {
    total_connectors: connectors.length,
    active_connectors: connectors.filter(c => c.is_active).length,
    total_requests: 0,
    success_rate: 100,
    avg_latency_ms: 0,
    total_cost_usd: 0,
    cost_today_usd: 0,
    cost_this_week_usd: 0
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">API Gateway Dashboard</h1>
          <p className="page-subtitle">Real-time gateway intelligence, active connectors, and unified multi-model routing.</p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button className="btn btn-secondary" onClick={onOpenBlueprint}>
            <Sparkles size={16} color="var(--accent-cyan)" />
            AI Blueprint Generator
          </button>
          <button className="btn btn-primary" onClick={onOpenCreate}>
            <Plus size={16} />
            Create Connector
          </button>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-card-header">
            <span>Connectors</span>
            <Layers size={18} color="var(--accent-cyan)" />
          </div>
          <div className="metric-value">{overview.total_connectors}</div>
          <div className="metric-sub">
            <span style={{ color: 'var(--accent-emerald)', fontWeight: 600 }}>{overview.active_connectors} Active</span>
            <span>· {overview.total_connectors - overview.active_connectors} Disabled</span>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-card-header">
            <span>Total Requests</span>
            <Activity size={18} color="var(--accent-blue)" />
          </div>
          <div className="metric-value">{overview.total_requests.toLocaleString()}</div>
          <div className="metric-sub">
            <span style={{ color: 'var(--accent-emerald)', fontWeight: 600 }}>{overview.success_rate}% Success</span>
            <span>· {overview.failure_rate || 0}% Failed</span>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-card-header">
            <span>Avg Latency</span>
            <Clock size={18} color="var(--accent-violet)" />
          </div>
          <div className="metric-value">{overview.avg_latency_ms} <span style={{ fontSize: '1rem', fontWeight: 500 }}>ms</span></div>
          <div className="metric-sub">End-to-end gateway execution</div>
        </div>

        <div className="metric-card">
          <div className="metric-card-header">
            <span>Estimated Cost</span>
            <DollarSign size={18} color="var(--accent-amber)" />
          </div>
          <div className="metric-value">${overview.total_cost_usd.toFixed(4)}</div>
          <div className="metric-sub">
            <span>Today: ${overview.cost_today_usd?.toFixed(4) || "0.0000"}</span>
            <span>· Week: ${overview.cost_this_week_usd?.toFixed(4) || "0.0000"}</span>
          </div>
        </div>
      </div>

      {/* Connectors Section */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <h2 style={{ fontSize: '1.15rem', fontWeight: 700 }}>Configured AI Connectors</h2>
        <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Showing {connectors.length} connectors</span>
      </div>

      <div className="connectors-grid">
        {connectors.map((c) => (
          <div key={c.slug} className={`connector-card ${!c.is_active ? 'disabled' : ''}`}>
            <div>
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '8px' }}>
                <h3 style={{ fontSize: '1.05rem', fontWeight: 700 }}>{c.name}</h3>
                <span className={`badge ${c.is_active ? 'badge-active' : 'badge-disabled'}`}>
                  {c.is_active ? 'Active' : 'Disabled'}
                </span>
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '8px', minHeight: '38px' }}>
                {c.description || "Reusable custom AI connector endpoint."}
              </p>

              <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', margin: '14px 0' }}>
                <span className="badge badge-provider">
                  <Cpu size={12} />
                  {c.provider} / {c.model_id}
                </span>
                <span className="badge badge-routing">
                  Strategy: {c.routing_strategy}
                </span>
                <span className="badge" style={{ background: 'rgba(255,255,255,0.05)', color: 'var(--text-secondary)' }}>
                  {c.inputs?.length || 0} Dynamic Inputs
                </span>
              </div>

              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', justifyContent: 'space-between' }}>
                <span>Slug: <code style={{ color: 'var(--accent-cyan)' }}>/api/v1/run/{c.slug}</code></span>
                <span>{c.request_count || 0} requests</span>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '8px', marginTop: '18px', paddingTop: '14px', borderTop: '1px solid var(--border-color)', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', gap: '6px' }}>
                <button className="btn btn-primary btn-sm" onClick={() => onOpenTest(c.slug)} title="Test in Playground">
                  <Play size={13} /> Test
                </button>
                <button className="btn btn-secondary btn-sm" onClick={() => onOpenDocs(c.slug)} title="API Docs & cURL">
                  <BookOpen size={13} /> Docs
                </button>
              </div>

              <div style={{ display: 'flex', gap: '4px' }}>
                <button className="btn btn-secondary btn-sm" onClick={() => onOpenEdit(c)} title="Edit configuration">
                  <Edit3 size={13} />
                </button>
                <button 
                  className="btn btn-secondary btn-sm" 
                  onClick={() => onToggleStatus(c.slug)} 
                  title={c.is_active ? "Disable connector" : "Enable connector"}
                  style={{ color: c.is_active ? 'var(--accent-emerald)' : 'var(--accent-rose)' }}
                >
                  {c.is_active ? <ToggleRight size={15} /> : <ToggleLeft size={15} />}
                </button>
                <button className="btn btn-danger btn-sm" onClick={() => onDelete(c.slug)} title="Delete connector">
                  <Trash2 size={13} />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
