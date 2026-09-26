import React, { useState } from 'react';
import { X, Sparkles, ArrowRight, Check } from 'lucide-react';
import { generateBlueprint } from '../api';

interface BlueprintModalProps {
  isOpen: boolean;
  onClose: () => void;
  onApplyBlueprint: (proposal: any) => void;
}

export const BlueprintModal: React.FC<BlueprintModalProps> = ({ isOpen, onClose, onApplyBlueprint }) => {
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [proposal, setProposal] = useState<any>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;
    setLoading(true);
    setErrorMsg(null);
    setProposal(null);

    try {
      const data = await generateBlueprint(prompt.trim());
      setProposal(data);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to generate blueprint");
    } finally {
      setLoading(false);
    }
  };

  const handleAccept = () => {
    if (!proposal) return;
    onApplyBlueprint(proposal);
    onClose();
  };

  return (
    <div className="modal-backdrop">
      <div className="modal-content" style={{ maxWidth: '680px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ width: '32px', height: '32px', background: 'rgba(6,182,212,0.15)', borderRadius: 'var(--radius-md)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Sparkles size={18} color="var(--accent-cyan)" />
            </div>
            <div>
              <h2 style={{ fontSize: '1.15rem', fontWeight: 800 }}>Endpoint Blueprint Generator</h2>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                Describe your desired API in plain English. The engine will propose complete inputs, prompt, and output schema.
              </p>
            </div>
          </div>
          <button className="btn btn-secondary btn-sm" onClick={onClose}><X size={15} /></button>
        </div>

        <form onSubmit={handleGenerate}>
          <div className="form-group">
            <label className="form-label">What kind of AI API do you want to create?</label>
            <textarea
              className="form-textarea"
              rows={3}
              value={prompt}
              onChange={e => setPrompt(e.target.value)}
              placeholder="e.g. Create an API that extracts invoice line items, tax, and vendor details from receipts."
              required
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Quick templates:</span>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                style={{ fontSize: '0.72rem', padding: '2px 8px' }}
                onClick={() => setPrompt("Create an API that extracts customer identity and sentiment from support emails.")}
              >
                Support Tickets
              </button>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                style={{ fontSize: '0.72rem', padding: '2px 8px' }}
                onClick={() => setPrompt("Create an API that parses scanned receipts and bills for expense tracking.")}
              >
                Receipt Parser
              </button>
            </div>

            <button type="submit" className="btn btn-primary btn-sm" disabled={loading}>
              <Sparkles size={14} />
              {loading ? "Generating..." : "Generate Blueprint"}
            </button>
          </div>
        </form>

        {errorMsg && (
          <div style={{ marginTop: '14px', padding: '10px 14px', background: 'rgba(244,63,94,0.1)', border: '1px solid rgba(244,63,94,0.3)', borderRadius: 'var(--radius-md)', color: '#FB7185', fontSize: '0.8rem' }}>
            {errorMsg}
          </div>
        )}

        {proposal && (
          <div style={{ marginTop: '20px', padding: '16px', background: 'rgba(255,255,255,0.02)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
              <h3 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--accent-cyan)' }}>{proposal.name}</h3>
              <span className="badge badge-provider">{proposal.provider} / {proposal.model_id}</span>
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '12px' }}>{proposal.description}</p>

            <div style={{ marginBottom: '12px' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>Generated Inputs:</span>
              <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: '4px' }}>
                {proposal.inputs?.map((inp: any, i: number) => (
                  <span key={i} className="badge" style={{ background: 'rgba(255,255,255,0.06)' }}>
                    {inp.name} ({inp.type})
                  </span>
                ))}
              </div>
            </div>

            <div style={{ marginBottom: '16px' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>Proposed Output Schema:</span>
              <pre className="code-block" style={{ maxHeight: '140px', marginTop: '4px', fontSize: '0.75rem' }}>
                {JSON.stringify(proposal.schema_definition, null, 2)}
              </pre>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
              <button type="button" className="btn btn-secondary btn-sm" onClick={() => setProposal(null)}>
                Discard
              </button>
              <button type="button" className="btn btn-primary btn-sm" onClick={handleAccept}>
                <Check size={14} />
                Review & Edit in Connector Builder
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
