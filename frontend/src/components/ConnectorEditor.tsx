import React, { useState, useEffect } from 'react';
import { X, Plus, Trash2, Save, Cpu, Layers } from 'lucide-react';
import { createConnector, updateConnector, fetchModels } from '../api';

interface ConnectorEditorProps {
  connector?: any | null; // if null, create mode
  isOpen: boolean;
  onClose: () => void;
  onSaved: () => void;
}

export const ConnectorEditor: React.FC<ConnectorEditorProps> = ({ connector, isOpen, onClose, onSaved }) => {
  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [description, setDescription] = useState('');
  const [provider, setProvider] = useState('gemini');
  const [modelId, setModelId] = useState('gemini-2.5-flash');
  const [systemPrompt, setSystemPrompt] = useState('');
  const [routingStrategy, setRoutingStrategy] = useState('balanced');
  const [fallbackEnabled, setFallbackEnabled] = useState(true);
  const [fallbackProvider, setFallbackProvider] = useState('openai');
  const [fallbackModel, setFallbackModel] = useState('gpt-4o-mini');
  const [isActive, setIsActive] = useState(true);

  const [inputs, setInputs] = useState<any[]>([]);
  const [schemaText, setSchemaText] = useState('{\n  "result": "string"\n}');
  const [catalogModels, setCatalogModels] = useState<any[]>([]);
  const [saving, setSaving] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    fetchModels().then(data => {
      if (data?.models) setCatalogModels(data.models);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (connector) {
      setName(connector.name || '');
      setSlug(connector.slug || '');
      setDescription(connector.description || '');
      setProvider(connector.provider || 'gemini');
      setModelId(connector.model_id || 'gemini-2.5-flash');
      setSystemPrompt(connector.system_prompt || '');
      setRoutingStrategy(connector.routing_strategy || 'balanced');
      setFallbackEnabled(connector.fallback_enabled ?? true);
      setFallbackProvider(connector.fallback_provider || 'openai');
      setFallbackModel(connector.fallback_model || 'gpt-4o-mini');
      setIsActive(connector.is_active ?? true);
      setInputs(connector.inputs?.map((i: any) => ({
        name: i.name,
        type: i.type,
        is_required: i.is_required,
        description: i.description || '',
        default_value: i.default_value || ''
      })) || []);
      setSchemaText(
        connector.schema_definition
          ? JSON.stringify(connector.schema_definition, null, 2)
          : '{\n  "result": "string"\n}'
      );
    } else {
      // New Connector Defaults
      setName('');
      setSlug('');
      setDescription('');
      setProvider('gemini');
      setModelId('gemini-2.5-flash');
      setSystemPrompt('You are a helpful and specialized AI assistant. Process the provided input accurately.');
      setRoutingStrategy('balanced');
      setFallbackEnabled(true);
      setFallbackProvider('openai');
      setFallbackModel('gpt-4o-mini');
      setIsActive(true);
      setInputs([
        { name: 'input_text', type: 'text', is_required: true, description: 'Primary input query', default_value: '' }
      ]);
      setSchemaText('{\n  "summary": "string",\n  "key_findings": "array",\n  "sentiment": "string"\n}');
    }
    setErrorMsg(null);
  }, [connector, isOpen]);

  if (!isOpen) return null;

  const handleAddInput = () => {
    setInputs(prev => [
      ...prev,
      { name: `param_${prev.length + 1}`, type: 'text', is_required: true, description: '', default_value: '' }
    ]);
  };

  const handleRemoveInput = (idx: number) => {
    setInputs(prev => prev.filter((_, i) => i !== idx));
  };

  const handleInputChange = (idx: number, field: string, val: any) => {
    setInputs(prev => {
      const copy = [...prev];
      copy[idx] = { ...copy[idx], [field]: val };
      return copy;
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setErrorMsg("Connector name is required.");
      return;
    }
    if (!systemPrompt.trim()) {
      setErrorMsg("System prompt instructions are required.");
      return;
    }

    let parsedSchema = null;
    if (schemaText.trim()) {
      try {
        parsedSchema = JSON.parse(schemaText);
      } catch (err: any) {
        setErrorMsg(`Invalid JSON in Output Schema: ${err.message}`);
        return;
      }
    }

    setSaving(true);
    setErrorMsg(null);

    const payload = {
      name,
      slug: slug.trim() || undefined,
      description,
      provider,
      model_id: modelId,
      system_prompt: systemPrompt,
      routing_strategy: routingStrategy,
      fallback_enabled: fallbackEnabled,
      fallback_provider: fallbackProvider,
      fallback_model: fallbackModel,
      is_active: isActive,
      inputs,
      schema_definition: parsedSchema
    };

    try {
      if (connector) {
        await updateConnector(connector.slug, payload);
      } else {
        await createConnector(payload);
      }
      onSaved();
      onClose();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to save connector.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-backdrop">
      <div className="modal-content">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 800 }}>
              {connector ? `Edit Connector: ${connector.name}` : "Create New AI Connector"}
            </h2>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Configure provider adapters, dynamic input schema, and intelligent routing.
            </p>
          </div>
          <button className="btn btn-secondary btn-sm" onClick={onClose}>
            <X size={16} />
          </button>
        </div>

        {errorMsg && (
          <div style={{ padding: '10px 14px', background: 'rgba(244,63,94,0.15)', border: '1px solid rgba(244,63,94,0.3)', borderRadius: 'var(--radius-md)', color: '#FB7185', fontSize: '0.82rem', marginBottom: '16px' }}>
            {errorMsg}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          {/* General Information */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
            <div className="form-group">
              <label className="form-label">Connector Name *</label>
              <input
                type="text"
                className="form-input"
                value={name}
                onChange={e => setName(e.target.value)}
                placeholder="e.g. Legal Contract Summarizer"
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">URL Slug (leave blank to auto-generate)</label>
              <input
                type="text"
                className="form-input"
                value={slug}
                onChange={e => setSlug(e.target.value)}
                placeholder="contract-summarizer"
                disabled={Boolean(connector)}
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Description / Purpose</label>
            <input
              type="text"
              className="form-input"
              value={description}
              onChange={e => setDescription(e.target.value)}
              placeholder="Brief description of the task this connector performs"
            />
          </div>

          {/* Provider & Model Selection */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '14px' }}>
            <div className="form-group">
              <label className="form-label">AI Provider</label>
              <select className="form-select" value={provider} onChange={e => setProvider(e.target.value)}>
                <option value="gemini">Google Gemini</option>
                <option value="openai">OpenAI</option>
                <option value="groq">Groq</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">AI Model</label>
              <select className="form-select" value={modelId} onChange={e => setModelId(e.target.value)}>
                {catalogModels.filter(m => m.provider === provider).map(m => (
                  <option key={m.model_id} value={m.model_id}>{m.display_name} ({m.model_id})</option>
                ))}
                {/* Fallbacks if empty */}
                {provider === "gemini" && <option value="gemini-2.5-flash">Gemini 2.5 Flash</option>}
                {provider === "gemini" && <option value="gemini-1.5-pro">Gemini 1.5 Pro</option>}
                {provider === "openai" && <option value="gpt-4o-mini">GPT-4o Mini</option>}
                {provider === "openai" && <option value="gpt-4o">GPT-4o</option>}
                {provider === "groq" && <option value="llama-3.3-70b-versatile">Llama 3.3 70B</option>}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Routing Strategy</label>
              <select className="form-select" value={routingStrategy} onChange={e => setRoutingStrategy(e.target.value)}>
                <option value="specific">Specific Model (Explicit)</option>
                <option value="balanced">Balanced (Cost/Speed/Quality)</option>
                <option value="cheapest">Cheapest Candidate</option>
                <option value="fastest">Fastest Throughput</option>
                <option value="highest_quality">Highest Quality</option>
                <option value="auto">Auto (Task context aware)</option>
              </select>
            </div>
          </div>

          {/* Automatic Fallback Config */}
          <div style={{ background: 'rgba(255,255,255,0.02)', padding: '14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
              <input
                type="checkbox"
                id="chk-fallback"
                checked={fallbackEnabled}
                onChange={e => setFallbackEnabled(e.target.checked)}
                style={{ width: '16px', height: '16px', accentColor: 'var(--accent-cyan)' }}
              />
              <label htmlFor="chk-fallback" style={{ fontSize: '0.85rem', fontWeight: 600, cursor: 'pointer' }}>
                Enable Automatic Fallback (Retry on secondary model during transient provider failure)
              </label>
            </div>

            {fallbackEnabled && (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label">Fallback Provider</label>
                  <select className="form-select" value={fallbackProvider} onChange={e => setFallbackProvider(e.target.value)}>
                    <option value="openai">OpenAI</option>
                    <option value="gemini">Google Gemini</option>
                    <option value="groq">Groq</option>
                  </select>
                </div>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label">Fallback Model</label>
                  <input
                    type="text"
                    className="form-input"
                    value={fallbackModel}
                    onChange={e => setFallbackModel(e.target.value)}
                    placeholder="gpt-4o-mini or gemini-2.5-flash"
                  />
                </div>
              </div>
            )}
          </div>

          {/* System Prompt */}
          <div className="form-group">
            <label className="form-label">System Instructions / Prompt *</label>
            <textarea
              className="form-textarea code-editor"
              rows={3}
              value={systemPrompt}
              onChange={e => setSystemPrompt(e.target.value)}
              placeholder="Define instructions, tone, and operational boundaries for this connector..."
              required
            />
          </div>

          {/* Dynamic Input Parameters */}
          <div style={{ marginBottom: '18px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
              <label className="form-label" style={{ marginBottom: 0 }}>Dynamic Input Fields ({inputs.length})</label>
              <button type="button" className="btn btn-secondary btn-sm" onClick={handleAddInput}>
                <Plus size={13} /> Add Input Field
              </button>
            </div>

            {inputs.map((inp, idx) => (
              <div key={idx} style={{ display: 'grid', gridTemplateColumns: '150px 110px 90px 1fr 34px', gap: '8px', alignItems: 'center', marginBottom: '8px' }}>
                <input
                  type="text"
                  className="form-input"
                  placeholder="field_name"
                  value={inp.name}
                  onChange={e => handleInputChange(idx, 'name', e.target.value)}
                  style={{ fontSize: '0.8rem', padding: '6px 8px', fontFamily: 'var(--font-mono)' }}
                  required
                />
                <select
                  className="form-select"
                  value={inp.type}
                  onChange={e => handleInputChange(idx, 'type', e.target.value)}
                  style={{ fontSize: '0.8rem', padding: '6px 8px' }}
                >
                  <option value="text">text</option>
                  <option value="number">number</option>
                  <option value="boolean">boolean</option>
                  <option value="image">image</option>
                  <option value="file">file</option>
                  <option value="json">json</option>
                </select>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <input
                    type="checkbox"
                    checked={inp.is_required}
                    onChange={e => handleInputChange(idx, 'is_required', e.target.checked)}
                    id={`req-${idx}`}
                  />
                  <label htmlFor={`req-${idx}`} style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Req</label>
                </div>
                <input
                  type="text"
                  className="form-input"
                  placeholder="Description or purpose"
                  value={inp.description}
                  onChange={e => handleInputChange(idx, 'description', e.target.value)}
                  style={{ fontSize: '0.8rem', padding: '6px 8px' }}
                />
                <button type="button" className="btn btn-danger btn-sm" onClick={() => handleRemoveInput(idx)} style={{ padding: '6px' }}>
                  <Trash2 size={13} />
                </button>
              </div>
            ))}
          </div>

          {/* Structured Output Schema */}
          <div className="form-group">
            <label className="form-label">Structured Output Schema (JSON Schema or field map)</label>
            <textarea
              className="form-textarea code-editor"
              rows={4}
              value={schemaText}
              onChange={e => setSchemaText(e.target.value)}
              placeholder="e.g. { 'title': 'string', 'score': 'number' }"
            />
          </div>

          {/* Modal Actions */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              <Save size={16} />
              {saving ? "Saving..." : "Save Connector"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
