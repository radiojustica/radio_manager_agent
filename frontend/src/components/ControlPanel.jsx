import { useState } from 'react';

const MOODS = [
  { value: 'Ensolarado', label: '☀️ Ensolarado' },
  { value: 'Chuvoso',    label: '🌧️ Chuvoso' },
  { value: 'Nublado',    label: '☁️ Nublado' },
  { value: 'Frio',       label: '❄️ Frio' },
];

function ActionButton({ label, onClick, disabled, loadingLabel, variant = '' }) {
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState(null);

  const handleClick = async () => {
    setLoading(true);
    setFeedback(null);
    try {
      await onClick();
      setFeedback({ ok: true, msg: '✓ Ok' });
    } catch (e) {
      setFeedback({ ok: false, msg: '✗ Erro' });
    } finally {
      setLoading(false);
      setTimeout(() => setFeedback(null), 3000);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <button
        className={`btn ${variant}`}
        onClick={handleClick}
        disabled={disabled || loading}
      >
        {loading && <span className="spinner" />}
        {loading ? (loadingLabel || 'Aguarde...') : label}
      </button>
      {feedback && (
        <span style={{
          fontSize: '0.62rem',
          fontWeight: 700,
          color: feedback.ok ? 'var(--accent-success)' : 'var(--accent-danger)',
          textAlign: 'center',
        }}>
          {feedback.msg}
        </span>
      )}
    </div>
  );
}

export default function ControlPanel({ onTrigger, onSync, currentMood, setMood }) {
  return (
    <div className="card">
      <div className="section-header" style={{ marginBottom: '1.5rem' }}>
        <div className="section-title">
          <div className="accent-line" />
          CONTROLE DE PROGRAMAÇÃO
        </div>
        <span style={{ fontSize: '1.2rem' }}>⚡</span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
        {/* Mood Selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <label style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-muted)', flexShrink: 0, textTransform: 'uppercase', letterSpacing: '1px' }}>
            Vibe Atual:
          </label>
          <select
            value={currentMood}
            onChange={(e) => setMood(e.target.value)}
            className="btn select"
            style={{ flexGrow: 1, textTransform: 'none' }}
          >
            {MOODS.map(m => (
              <option key={m.value} value={m.value}>{m.label}</option>
            ))}
          </select>
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
          <ActionButton
            label="Gera 24h"
            loadingLabel="Gerando..."
            onClick={() => onTrigger('gerar-24h')}
          />
          <ActionButton
            label="Bloco Extra"
            loadingLabel="Gerando..."
            onClick={() => onTrigger('gerar-extra')}
          />
        </div>

        <ActionButton
          label="🔄 Sincronizar Acervo"
          loadingLabel="Sincronizando..."
          variant="btn-primary"
          onClick={onSync}
        />
      </div>
    </div>
  );
}
