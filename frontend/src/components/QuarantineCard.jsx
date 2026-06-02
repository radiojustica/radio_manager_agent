import React, { useState, useEffect } from 'react';

export default function QuarantineCard() {
  const [quarantineList, setQuarantineList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actioningId, setActioningId] = useState(null);

  const loadQuarantine = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/acervo/quarantine');
      if (res.ok) {
        const data = await res.json();
        setQuarantineList(data);
      }
    } catch (e) {
      console.error("Erro ao carregar quarentena", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadQuarantine();
    // Atualiza a cada 30 segundos
    const interval = setInterval(loadQuarantine, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleRelease = async (id) => {
    setActioningId(id);
    try {
      const res = await fetch(`/api/acervo/quarantine/${id}/release`, {
        method: 'POST'
      });
      if (res.ok) {
        loadQuarantine();
      } else {
        alert("Falha ao liberar música da quarentena.");
      }
    } catch (e) {
      console.error("Erro ao liberar musica", e);
      alert("Erro ao conectar ao servidor.");
    } finally {
      setActioningId(null);
    }
  };

  return (
    <div className="premium-card quarantine-central card" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.2rem' }}>
        <div className="section-title">
          <div className="accent-line" style={{ background: 'var(--accent-danger)' }} />
          QUARENTENA EDITORIAL TJ
        </div>
        <span className="status-badge" style={{ 
          fontSize: '0.62rem', 
          background: quarantineList.length > 0 ? 'rgba(239, 68, 68, 0.15)' : 'rgba(16, 185, 129, 0.15)',
          color: quarantineList.length > 0 ? 'var(--accent-danger)' : 'var(--accent-success)',
          padding: '0.2rem 0.5rem',
          borderRadius: '12px',
          fontWeight: 700
        }}>
          {quarantineList.length} BLOQUEADA(S)
        </span>
      </div>

      <div className="quarantine-content" style={{ minHeight: '140px', maxHeight: '300px', overflowY: 'auto' }}>
        {loading && quarantineList.length === 0 ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '140px', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            Carregando dados da quarentena...
          </div>
        ) : quarantineList.length === 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '140px', gap: '8px' }}>
            <span style={{ fontSize: '1.5rem' }}>🛡️</span>
            <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--accent-success)' }}>ACERVO HIGIENIZADO</div>
            <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>Nenhuma música inapropriada na grade.</div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {quarantineList.map(song => (
              <div key={song.id} style={{ 
                background: 'rgba(239, 68, 68, 0.03)', 
                padding: '0.8rem', 
                borderRadius: '10px', 
                border: '1px solid rgba(239, 68, 68, 0.12)', 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center',
                gap: '12px'
              }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', flex: 1, minWidth: 0 }}>
                  <div style={{ 
                    fontSize: '0.78rem', 
                    fontWeight: 800, 
                    color: 'var(--text-primary)', 
                    overflow: 'hidden', 
                    textOverflow: 'ellipsis', 
                    whiteSpace: 'nowrap' 
                  }}>
                    {song.artista} - {song.titulo}
                  </div>
                  <div style={{ 
                    fontSize: '0.64rem', 
                    color: 'var(--accent-danger)', 
                    fontWeight: 600,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    display: '-webkit-box',
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: 'vertical'
                  }} title={song.quarantine_reason || song.ai_insight}>
                    <strong>Motivo:</strong> {song.quarantine_reason || song.ai_insight || 'Sem motivo registrado'}
                  </div>
                </div>
                <button
                  className="btn btn-primary"
                  onClick={() => handleRelease(song.id)}
                  disabled={actioningId === song.id}
                  style={{
                    fontSize: '0.62rem',
                    padding: '0.35rem 0.7rem',
                    background: 'rgba(16, 185, 129, 0.1)',
                    color: 'var(--accent-success)',
                    border: '1px solid rgba(16, 185, 129, 0.2)',
                    borderRadius: '6px',
                    fontWeight: 700,
                    cursor: 'pointer',
                    whiteSpace: 'nowrap',
                    transition: 'all 0.2s ease'
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.background = 'var(--accent-success)';
                    e.currentTarget.style.color = 'var(--bg-void)';
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.background = 'rgba(16, 185, 129, 0.1)';
                    e.currentTarget.style.color = 'var(--accent-success)';
                  }}
                >
                  {actioningId === song.id ? '⏳' : '🔓 Liberar'}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
