import { useState, useEffect } from 'react';

export default function BulletinCard() {
  const [status, setStatus] = useState(null);
  const [syncing, setSyncing] = useState(false);

  const fetchStatus = async () => {
    try {
      const res = await fetch('/api/status/bulletins/status');
      if (res.ok) {
        const data = await res.json();
        setStatus(data);
      }
    } catch (e) {
      console.error("Erro ao buscar status dos boletins", e);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 30000); // 30s
    return () => clearInterval(interval);
  }, []);

  const handleSync = async () => {
    setSyncing(true);
    try {
      const res = await fetch('/api/status/bulletins/sync', { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        alert(data.message);
        fetchStatus();
      } else {
        alert("Erro na sincronização: " + data.error);
      }
    } catch (e) {
      alert("Falha na requisição de sincronia.");
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="premium-card bulletin-central" style={{ padding: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h3 style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', letterSpacing: '1px' }}>CENTRAL DE BOLETINS</h3>
        <button 
          className={`btn-action ${syncing ? 'syncing' : ''}`} 
          onClick={handleSync} 
          disabled={syncing}
          style={{ fontSize: '0.65rem', padding: '0.4rem 0.8rem' }}
        >
          {syncing ? '🔄 Sincronizando...' : '📥 Sincronizar Agora'}
        </button>
      </div>

      <div className="bulletin-days-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
        {status ? Object.entries(status).map(([day, info]) => (
          <div key={day} style={{ background: 'rgba(255,255,255,0.02)', padding: '0.8rem', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.05)' }}>
            <div style={{ fontSize: '0.6rem', fontWeight: 800, color: 'var(--text-muted)' }}>{day}</div>
            <div style={{ fontSize: '0.85rem', fontWeight: 800, marginTop: '4px' }}>
              {info.dates.length > 0 ? info.dates[0] : 'Vazio'}
            </div>
            <div style={{ fontSize: '0.65rem', color: 'var(--accent-success)', marginTop: '2px' }}>
              {info.count} arquivos
            </div>
          </div>
        )) : <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Carregando dados locais...</div>}
      </div>
      
      <div style={{ marginTop: '1rem', fontSize: '0.6rem', color: 'var(--text-muted)', textAlign: 'center' }}>
        Sincronização via GDrive: <strong>D:\SERVIDOR\BOLETINS</strong>
      </div>
    </div>
  );
}
