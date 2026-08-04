import { useState } from 'react';

const MOODS = [
  { value: 'Ensolarado', label: 'Ensolarado' },
  { value: 'Chuvoso',    label: 'Chuvoso' },
  { value: 'Nublado',    label: 'Nublado' },
  { value: 'Frio',       label: 'Frio' },
];

function CompactButton({ label, onClick, disabled, loadingLabel, variant, onResult }) {
  const [loading, setLoading] = useState(false);
  const handleClick = async () => {
    setLoading(true);
    try {
      const result = await onClick();
      if (onResult) onResult(result);
    } finally {
      setLoading(false);
    }
  };
  return (
    <button
      className={`btn ${variant}`}
      onClick={handleClick}
      disabled={disabled || loading}
      title={label}
      style={{ whiteSpace: 'nowrap' }}
    >
      {loading ? (loadingLabel || '...') : label}
    </button>
  );
}

export default function ControlPanel({ onTrigger, currentMood, setMood }) {
  return (
    <div
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        gap: '0.75rem',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <div className="accent-line" />
        <div className="section-title">CONTROLE DE PROGRAMAÇÃO</div>
        <span style={{ fontSize: '1rem' }}>⚡</span>
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '0.5rem' }}>
        <select
          value={currentMood}
          onChange={(e) => setMood(e.target.value)}
          className="btn select"
          style={{ textTransform: 'none' }}
          title={currentMood}
        >
          {MOODS.map(m => (
            <option key={m.value} value={m.value}>{m.label}</option>
          ))}
        </select>

        <CompactButton label="Gera 24h" loadingLabel="Gerando..." onClick={() => onTrigger('gerar-24h')} />
        <CompactButton label="Bloco Extra" loadingLabel="Gerando..." onClick={() => onTrigger('gerar-extra')} />
        <CompactButton label="🕷️ Ativar Spider" loadingLabel="Escaneando..." variant="btn-primary" onClick={() => onTrigger('ativar-spider')} onResult={(r)=> { if(r?.spiderResult) try { window.dispatchEvent(new CustomEvent('spider-result', { detail: r.spiderResult })); } catch(e){} }} />
        <CompactButton label="🔄 Sincronizar Acervo" loadingLabel="Sincronizando..." onClick={() => onTrigger('sincronizar-acervo')} onResult={(r)=> { if(r?.syncResult) try { window.dispatchEvent(new CustomEvent('sync-result', { detail: r.syncResult })); } catch(e){} }} />
      </div>
    </div>
  );
}
