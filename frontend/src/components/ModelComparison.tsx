import React, { useState } from 'react';
import { Cpu, Play, Clock, Layers, DollarSign, CheckCircle2, AlertTriangle, Scale, Sparkles } from 'lucide-react';
import { compareModels } from '../api';

export const ModelComparison: React.FC = () => {
  const [prompt, setPrompt] = useState('Explain the strategic implications of autonomous multi-agent AI gateways in enterprise software architecture.');
  const [systemPrompt, setSystemPrompt] = useState('You are an enterprise software architect. Provide clear, structured analysis.');
  const [schemaText, setSchemaText] = useState('{\n  "overview": "string",\n  "key_benefits": "array",\n  "risk_factors": "array",\n  "recommendation": "string"\n}');

  const [modelAProvider, setModelAProvider] = useState('gemini');
  const [modelAModel, setModelAModel] = useState('gemini-2.5-flash');
  const [modelBProvider, setModelBProvider] = useState('openai');
  const [modelBModel, setModelBModel] = useState('gpt-4o-mini');

  const [includeJudge, setIncludeJudge] = useState(true);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleRunCompare = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;
    setLoading(true);
    setErrorMsg(null);
    setResult(null);

    let parsedSchema = null;
    if (schemaText.trim()) {
      try {
        parsedSchema = JSON.parse(schemaText);
      } catch (e: any) {
        setErrorMsg(`Invalid JSON schema: ${e.message}`);
        setLoading(false);
        return;
      }
    }

    try {
      const res = await compareModels({
        prompt,
        system_prompt: systemPrompt,
        schema_definition: parsedSchema,
        model_a_provider: modelAProvider,
        model_a_id: modelAModel,
        model_b_provider: modelBProvider,
        model_b_id: modelBModel,
        include_ai_judge: includeJudge
      });
      setResult(res);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to execute model comparison");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Model Evaluation & Benchmark</h1>
          <p className="page-subtitle">Execute identical prompts and structured schemas concurrently across two AI providers.</p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '380px 1fr', gap: '24px', alignItems: 'start' }}>
        {/* Controls */}
        <div className="card">
          <h2 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Scale size={18} color="var(--accent-cyan)" /> Dual Model Setup
          </h2>

          <form onSubmit={handleRunCompare}>
            {/* Model A */}
            <div style={{ background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', marginBottom: '14px' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--accent-cyan)', textTransform: 'uppercase' }}>Candidate A</span>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginTop: '6px' }}>
                <select className="form-select" value={modelAProvider} onChange={e => setModelAProvider(e.target.value)} style={{ fontSize: '0.8rem', padding: '6px' }}>
                  <option value="gemini">Gemini</option>
                  <option value="openai">OpenAI</option>
                  <option value="groq">Groq</option>
                </select>
                <input
                  type="text"
                  className="form-input"
                  value={modelAModel}
                  onChange={e => setModelAModel(e.target.value)}
                  style={{ fontSize: '0.8rem', padding: '6px' }}
                />
              </div>
            </div>

            {/* Model B */}
            <div style={{ background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', marginBottom: '14px' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--accent-violet)', textTransform: 'uppercase' }}>Candidate B</span>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginTop: '6px' }}>
                <select className="form-select" value={modelBProvider} onChange={e => setModelBProvider(e.target.value)} style={{ fontSize: '0.8rem', padding: '6px' }}>
                  <option value="openai">OpenAI</option>
                  <option value="gemini">Gemini</option>
                  <option value="groq">Groq</option>
                </select>
                <input
                  type="text"
                  className="form-input"
                  value={modelBModel}
                  onChange={e => setModelBModel(e.target.value)}
                  style={{ fontSize: '0.8rem', padding: '6px' }}
                />
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Test Prompt</label>
              <textarea
                className="form-textarea"
                rows={3}
                value={prompt}
                onChange={e => setPrompt(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Output Schema (JSON)</label>
              <textarea
                className="form-textarea code-editor"
                rows={3}
                value={schemaText}
                onChange={e => setSchemaText(e.target.value)}
              />
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
              <input
                type="checkbox"
                id="chk-judge"
                checked={includeJudge}
                onChange={e => setIncludeJudge(e.target.checked)}
                style={{ width: '16px', height: '16px', accentColor: 'var(--accent-cyan)' }}
              />
              <label htmlFor="chk-judge" style={{ fontSize: '0.8rem', cursor: 'pointer' }}>
                Include heuristic evaluation summary
              </label>
            </div>

            <button type="submit" className="btn btn-primary" disabled={loading} style={{ width: '100%', padding: '10px' }}>
              <Play size={15} />
              {loading ? "Benchmarking Models..." : "Run Side-by-Side Comparison"}
            </button>
          </form>
        </div>

        {/* Results */}
        <div>
          {errorMsg && (
            <div style={{ padding: '12px 16px', background: 'rgba(244,63,94,0.1)', border: '1px solid rgba(244,63,94,0.3)', borderRadius: 'var(--radius-md)', color: '#FB7185', fontSize: '0.85rem', marginBottom: '18px' }}>
              {errorMsg}
            </div>
          )}

          {result && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
              {/* Comparison Summary Card */}
              <div className="card" style={{ background: 'linear-gradient(to right, rgba(6,182,212,0.06), rgba(139,92,246,0.06))' }}>
                <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '12px' }}>Deterministic Comparison Summary</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '12px' }}>
                  <div style={{ background: 'rgba(0,0,0,0.2)', padding: '10px 14px', borderRadius: 'var(--radius-md)' }}>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Faster Model</span>
                    <div style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--accent-emerald)', marginTop: '2px' }}>
                      {result.comparison.faster_model}
                    </div>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Δ {result.comparison.latency_difference_ms} ms</span>
                  </div>

                  <div style={{ background: 'rgba(0,0,0,0.2)', padding: '10px 14px', borderRadius: 'var(--radius-md)' }}>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Lower Cost Model</span>
                    <div style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--accent-amber)', marginTop: '2px' }}>
                      {result.comparison.cheaper_model}
                    </div>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Δ ${result.comparison.cost_difference_usd.toFixed(6)}</span>
                  </div>

                  <div style={{ background: 'rgba(0,0,0,0.2)', padding: '10px 14px', borderRadius: 'var(--radius-md)' }}>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Token Difference</span>
                    <div style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--accent-blue)', marginTop: '2px' }}>
                      {result.comparison.token_difference} tokens
                    </div>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Schema valid: {result.comparison.both_valid ? "Both Pass" : "Check Errors"}</span>
                  </div>
                </div>

                {result.ai_judge && (
                  <div style={{ marginTop: '14px', paddingTop: '12px', borderTop: '1px solid var(--border-color)' }}>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
                      {result.ai_judge.label}
                    </span>
                    <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                      {result.ai_judge.verdict}
                    </p>
                  </div>
                )}
              </div>

              {/* Side by side outputs */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '18px' }}>
                {/* Model A Output */}
                <div className="card">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                    <span className="badge badge-provider">{result.model_a.provider} / {result.model_a.model}</span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Clock size={12} /> {result.model_a.latency_ms} ms
                    </span>
                  </div>

                  <div style={{ display: 'flex', gap: '10px', fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '10px' }}>
                    <span>Tokens: {result.model_a.total_tokens}</span>
                    <span>Cost: ${result.model_a.estimated_cost_usd?.toFixed(6)}</span>
                    <span style={{ color: result.model_a.schema_valid ? 'var(--accent-emerald)' : 'var(--accent-rose)' }}>
                      {result.model_a.schema_valid ? "Schema Valid" : "Schema Failed"}
                    </span>
                  </div>

                  <pre className="code-block" style={{ maxHeight: '340px', fontSize: '0.75rem' }}>
                    {JSON.stringify(result.model_a.parsed_output || result.model_a.raw_text, null, 2)}
                  </pre>
                </div>

                {/* Model B Output */}
                <div className="card">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                    <span className="badge badge-routing">{result.model_b.provider} / {result.model_b.model}</span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Clock size={12} /> {result.model_b.latency_ms} ms
                    </span>
                  </div>

                  <div style={{ display: 'flex', gap: '10px', fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '10px' }}>
                    <span>Tokens: {result.model_b.total_tokens}</span>
                    <span>Cost: ${result.model_b.estimated_cost_usd?.toFixed(6)}</span>
                    <span style={{ color: result.model_b.schema_valid ? 'var(--accent-emerald)' : 'var(--accent-rose)' }}>
                      {result.model_b.schema_valid ? "Schema Valid" : "Schema Failed"}
                    </span>
                  </div>

                  <pre className="code-block" style={{ maxHeight: '340px', fontSize: '0.75rem' }}>
                    {JSON.stringify(result.model_b.parsed_output || result.model_b.raw_text, null, 2)}
                  </pre>
                </div>
              </div>
            </div>
          )}

          {!result && !loading && !errorMsg && (
            <div className="card" style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--text-muted)' }}>
              Configure Candidate A and B on the left, then click <strong>Run Side-by-Side Comparison</strong> to benchmark speed, costs, and schema conformance.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
