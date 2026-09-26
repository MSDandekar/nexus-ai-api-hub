import React, { useState, useEffect } from 'react';
import { Layers, Activity, BookOpen, Play, Cpu, Key, FileText, Sparkles, Plus } from 'lucide-react';
import { fetchMetrics, fetchConnectors, toggleConnector, deleteConnector } from './api';

import { Dashboard } from './components/Dashboard';
import { Playground } from './components/Playground';
import { Documentation } from './components/Documentation';
import { ConnectorEditor } from './components/ConnectorEditor';
import { BlueprintModal } from './components/BlueprintModal';
import { ModelComparison } from './components/ModelComparison';
import { ApiKeysManager } from './components/ApiKeysManager';
import { LogsViewer } from './components/LogsViewer';

export function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'playground' | 'docs' | 'compare' | 'keys' | 'logs'>('dashboard');
  const [apiKey, setApiKey] = useState('nexus-dev-master-key-2026');
  
  const [metrics, setMetrics] = useState<any>(null);
  const [connectors, setConnectors] = useState<any[]>([]);
  const [selectedSlug, setSelectedSlug] = useState<string>('card-scanner');

  // Modals
  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [editingConnector, setEditingConnector] = useState<any | null>(null);
  const [isBlueprintOpen, setIsBlueprintOpen] = useState(false);

  const loadData = async () => {
    try {
      const [m, c] = await Promise.all([fetchMetrics(), fetchConnectors()]);
      setMetrics(m);
      setConnectors(c.connectors || []);
      if (c.connectors && c.connectors.length > 0 && !c.connectors.some((item: any) => item.slug === selectedSlug)) {
        setSelectedSlug(c.connectors[0].slug);
      }
    } catch (err) {
      console.error("Failed to load initial data", err);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleOpenTest = (slug: string) => {
    setSelectedSlug(slug);
    setActiveTab('playground');
  };

  const handleOpenDocs = (slug: string) => {
    setSelectedSlug(slug);
    setActiveTab('docs');
  };

  const handleOpenEdit = (connector: any) => {
    setEditingConnector(connector);
    setIsEditorOpen(true);
  };

  const handleOpenCreate = () => {
    setEditingConnector(null);
    setIsEditorOpen(true);
  };

  const handleToggleStatus = async (slug: string) => {
    try {
      await toggleConnector(slug);
      loadData();
    } catch (err) {
      alert("Failed to toggle connector status");
    }
  };

  const handleDelete = async (slug: string) => {
    if (!confirm(`Are you sure you want to permanently delete connector '${slug}'?`)) return;
    try {
      await deleteConnector(slug);
      loadData();
    } catch (err) {
      alert("Failed to delete connector");
    }
  };

  const handleApplyBlueprint = (proposal: any) => {
    setEditingConnector(proposal);
    setIsEditorOpen(true);
  };

  const activeConnector = connectors.find(c => c.slug === selectedSlug) || connectors[0];

  return (
    <div className="app-container">
      {/* Top Header */}
      <header className="app-header">
        <div className="brand">
          <div className="brand-icon">
            <Cpu size={22} />
          </div>
          <div>
            <div className="brand-title">AI Nexus</div>
            <div className="brand-tagline">Intelligent Multi-Model API Hub</div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="nav-tabs">
          <button
            className={`nav-tab ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => setActiveTab('dashboard')}
          >
            <Activity size={15} /> Dashboard
          </button>
          <button
            className={`nav-tab ${activeTab === 'playground' ? 'active' : ''}`}
            onClick={() => setActiveTab('playground')}
          >
            <Play size={15} /> Playground
          </button>
          <button
            className={`nav-tab ${activeTab === 'docs' ? 'active' : ''}`}
            onClick={() => setActiveTab('docs')}
          >
            <BookOpen size={15} /> API Docs
          </button>
          <button
            className={`nav-tab ${activeTab === 'compare' ? 'active' : ''}`}
            onClick={() => setActiveTab('compare')}
          >
            <Layers size={15} /> Model Compare
          </button>
          <button
            className={`nav-tab ${activeTab === 'keys' ? 'active' : ''}`}
            onClick={() => setActiveTab('keys')}
          >
            <Key size={15} /> API Keys
          </button>
          <button
            className={`nav-tab ${activeTab === 'logs' ? 'active' : ''}`}
            onClick={() => setActiveTab('logs')}
          >
            <FileText size={15} /> Request Logs
          </button>
        </nav>

        {/* Global Key & Action */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button className="btn btn-secondary btn-sm" onClick={() => setIsBlueprintOpen(true)}>
            <Sparkles size={14} color="var(--accent-cyan)" /> Blueprint
          </button>
          <button className="btn btn-primary btn-sm" onClick={handleOpenCreate}>
            <Plus size={14} /> New API
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="main-content">
        {activeTab === 'dashboard' && (
          <Dashboard
            metrics={metrics}
            connectors={connectors}
            onOpenTest={handleOpenTest}
            onOpenDocs={handleOpenDocs}
            onOpenEdit={handleOpenEdit}
            onToggleStatus={handleToggleStatus}
            onDelete={handleDelete}
            onOpenCreate={handleOpenCreate}
            onOpenBlueprint={() => setIsBlueprintOpen(true)}
          />
        )}

        {activeTab === 'playground' && (
          <div>
            {/* Connector selector bar if in playground */}
            <div style={{ display: 'flex', gap: '8px', marginBottom: '16px', overflowX: 'auto', paddingBottom: '4px' }}>
              {connectors.map(c => (
                <button
                  key={c.slug}
                  className={`btn btn-sm ${selectedSlug === c.slug ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setSelectedSlug(c.slug)}
                >
                  {c.name}
                </button>
              ))}
            </div>

            <Playground
              connector={activeConnector}
              apiKey={apiKey}
              onApiKeyChange={setApiKey}
            />
          </div>
        )}

        {activeTab === 'docs' && (
          <div>
            {/* Connector selector bar for docs */}
            <div style={{ display: 'flex', gap: '8px', marginBottom: '16px', overflowX: 'auto', paddingBottom: '4px' }}>
              {connectors.map(c => (
                <button
                  key={c.slug}
                  className={`btn btn-sm ${selectedSlug === c.slug ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setSelectedSlug(c.slug)}
                >
                  {c.name}
                </button>
              ))}
            </div>

            <Documentation
              slug={selectedSlug}
              apiKey={apiKey}
            />
          </div>
        )}

        {activeTab === 'compare' && <ModelComparison />}

        {activeTab === 'keys' && <ApiKeysManager />}

        {activeTab === 'logs' && <LogsViewer />}
      </main>

      {/* Modals */}
      <ConnectorEditor
        connector={editingConnector}
        isOpen={isEditorOpen}
        onClose={() => setIsEditorOpen(false)}
        onSaved={loadData}
      />

      <BlueprintModal
        isOpen={isBlueprintOpen}
        onClose={() => setIsBlueprintOpen(false)}
        onApplyBlueprint={handleApplyBlueprint}
      />
    </div>
  );
}

export default App;
