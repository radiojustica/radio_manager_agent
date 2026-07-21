import { useState, useEffect } from 'react';

export default function AutopilotCard() {
  const [data, setData] = useState({ active: true, stats: { process_restarts: 0, silence_recoveries: 0, butt_reconnects: 0 }, recent_actions: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchStatus = async () => {
    try {
      const res = await fetch('/api/autopilot/status');
      if (!res.ok) throw new Error('API do Autopilot indisponível');
      const json = await res.json();
      setData(json);
      setError(null);
    } catch (e) {
      setError(e.message);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleToggle = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/autopilot/toggle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ active: !data.active }),
      });
      if (!res.ok) throw new Error('Falha ao alternar piloto automático');
      const json = await res.json();
      setData(prev => ({ ...prev, active: json.active }));
      fetchStatus();
    } catch (e) {
      alert(e.message);
    } finally {
      setLoading(false);
    }
  };

  const getFormatTime = (isoString) => {
    if (!isoString) return '';
    try {
      const date = new Date(isoString);
      return date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return '';
    }
  };

  const getBadgeClass = (type) => {
    switch (type) {
      case 'PROCESS_RESTART': return 'badge-restart';
      case 'SILENCE_RECOVERY': return 'badge-silence';
      case 'BUTT_RECONNECT': return 'badge-butt';
      case 'PLAYLIST_GEN': return 'badge-playlist';
      case 'SYNC_ACERVO': return 'badge-acervo';
      case 'SYNC_BULLETIN': return 'badge-bulletin';
      case 'SYNC_NJUD': return 'badge-njud';
      default: return 'badge-system';
    }
  };

  return (
    <div className="card">
      <div className="section-header" style={{ marginBottom: '1.25rem' }}>
        <div className="section-title">
          <div className="accent-line" style={{ background: data.active ? 'var(--accent-success)' : 'var(--text-muted)' }} />
          PILOTO AUTOMÁTICO (AUTOPILOT)
        </div>
        <span
          className={`status-badge ${data.active ? 'playing' : 'stopped'}`}
          style={{ fontSize: '0.62rem', letterSpacing: '0.5px' }}
        >
          {data.active ? 'AUTOPILOT: ON' : 'AUTOPILOT: OFF'}
        </span>
      </div>

      {error && (
        <div style={{ padding: '0.5rem 0.75rem', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.2)', color: 'var(--accent-danger)', borderRadius: '6px', fontSize: '0.72rem', marginBottom: '0.75rem' }}>
          ⚠️ {error}
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>


        {/* Toggle Button */}
        <button
          onClick={handleToggle}
          disabled={loading}
          className={`btn ${data.active ? 'btn-success' : ''}`}
          style={{
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '1px',
            fontSize: '0.78rem',
            padding: '0.75rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            transition: 'all 0.3s ease',
            boxShadow: data.active ? '0 0 15px rgba(16, 185, 129, 0.25)' : 'none',
            border: data.active ? '1px solid rgba(16, 185, 129, 0.4)' : '1px solid rgba(255,255,255,0.08)'
          }}
        >
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              background: data.active ? '#10b981' : '#ef4444',
              display: 'inline-block',
              animation: data.active ? 'pulse-green 2s infinite' : 'none'
            }}
          />
          {loading ? 'Processando...' : data.active ? 'Desativar Piloto Automático' : 'Ativar Piloto Automático'}
        </button>

        {/* Counter Stats Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.5rem', textAlign: 'center' }}>
          <div style={{ background: 'rgba(255,255,255,0.03)', padding: '0.5rem', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.05)' }}>
            <div style={{ fontSize: '0.58rem', fontWeight: 700, color: 'var(--text-muted)' }}>REINÍCIOS</div>
            <div style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--accent-primary)', marginTop: '2px' }}>
              {data.stats?.process_restarts || 0}
            </div>
          </div>
          <div style={{ background: 'rgba(255,255,255,0.03)', padding: '0.5rem', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.05)' }}>
            <div style={{ fontSize: '0.58rem', fontWeight: 700, color: 'var(--text-muted)' }}>SILÊNCIOS</div>
            <div style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--accent-warning)', marginTop: '2px' }}>
              {data.stats?.silence_recoveries || 0}
            </div>
          </div>
          <div style={{ background: 'rgba(255,255,255,0.03)', padding: '0.5rem', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.05)' }}>
            <div style={{ fontSize: '0.58rem', fontWeight: 700, color: 'var(--text-muted)' }}>ENCODERS</div>
            <div style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--accent-success)', marginTop: '2px' }}>
              {data.stats?.butt_reconnects || 0}
            </div>
          </div>
        </div>

        {/* Recent Actions Feed */}
        <div>
          <div style={{ fontSize: '0.68rem', fontWeight: 800, color: 'var(--text-muted)', letterSpacing: '0.5px', textTransform: 'uppercase', marginBottom: '0.5rem' }}>
            Histórico Recente de Autocura
          </div>
          <div
            style={{
              maxHeight: '120px',
              overflowY: 'auto',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
              paddingRight: '4px'
            }}
            className="custom-scrollbar"
          >
            {data.recent_actions?.length > 0 ? (
              data.recent_actions.map(action => (
                <div
                  key={action.id}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    padding: '6px 8px',
                    background: 'rgba(255,255,255,0.02)',
                    borderRadius: '4px',
                    borderLeft: `2.5px solid ${action.success ? '#10b981' : '#ef4444'}`,
                    fontSize: '0.68rem'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2px' }}>
                    <span className={`badge-action ${getBadgeClass(action.action_type)}`}>
                      {action.action_type}
                    </span>
                    <span style={{ fontSize: '0.6rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                      {getFormatTime(action.timestamp)}
                    </span>
                  </div>
                  <div style={{ color: 'var(--text-color)', opacity: 0.85, fontSize: '0.66rem', lineHeight: '1.2' }}>
                    {action.message}
                  </div>
                </div>
              ))
            ) : (
              <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textAlign: 'center', padding: '1rem 0' }}>
                Nenhuma ação de autocura registrada ainda.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
