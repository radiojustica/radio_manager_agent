import React, { useState } from 'react';

const ControlPanel = ({ onTrigger, onSync, currentMood, setMood }) => {
  const [loading, setLoading] = useState(false);

  const handleAction = async (action, fn) => {
    setLoading(true);
    try {
      await fn();
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  return (
    <div className="premium-card">
      <h3 style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '12px', fontSize: '1rem' }}>
        <span style={{ color: 'var(--accent-primary)', fontSize: '1.2rem' }}>⚡</span> 
        CONTROLE DE PROGRAMAÇÃO
      </h3>
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <label style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-secondary)', flexShrink: 0, textTransform: 'uppercase' }}>Vibe Atual:</label>
          <select 
            value={currentMood} 
            onChange={(e) => setMood(e.target.value)}
            className="btn-action"
            style={{ flexGrow: 1, padding: '0.6rem 1rem', textTransform: 'none' }}
          >
            <option value="Ensolarado">☀️ Ensolarado</option>
            <option value="Chuvoso">🌧️ Chuvoso</option>
            <option value="Nublado">☁️ Nublado</option>
          </select>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
          <button 
            disabled={loading}
            onClick={() => handleAction('24h', () => onTrigger('gerar-24h'))}
            className="btn-action"
          >
            Gera 24h
          </button>
          <button 
            disabled={loading}
            onClick={() => handleAction('extra', () => onTrigger('gerar-extra'))}
            className="btn-action"
          >
            Bloco Extra
          </button>
        </div>

        <button
          disabled={loading}
          onClick={() => handleAction('sync', onSync)}
          className="btn-action btn-primary"
          style={{ width: '100%' }}
        >
          🔄 Sincronizar Acervo
        </button>
        </div>
        </div>
        );
        };
export default ControlPanel;
