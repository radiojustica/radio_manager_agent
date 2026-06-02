import { useState, useEffect } from 'react';

export default function BulletinCard() {
  const [activeTab, setActiveTab] = useState('bulletins'); // 'bulletins' ou 'njud'
  const [bulletinStatus, setBulletinStatus] = useState(null);
  const [njudStatus, setNjudStatus] = useState(null);
  const [syncing, setSyncing] = useState(false);

  const fetchBulletinStatus = async () => {
    try {
      const res = await fetch('/api/status/bulletins/status');
      if (res.ok) {
        const data = await res.json();
        setBulletinStatus(data);
      }
    } catch (e) {
      console.error("Erro ao buscar status dos boletins", e);
    }
  };

  const fetchNjudStatus = async () => {
    try {
      const res = await fetch('/api/status/njud/status');
      if (res.ok) {
        const data = await res.json();
        setNjudStatus(data);
      }
    } catch (e) {
      console.error("Erro ao buscar status do NJUD", e);
    }
  };

  const fetchAll = () => {
    fetchBulletinStatus();
    fetchNjudStatus();
  };

  useEffect(() => {
    fetchAll();
    const interval = setInterval(fetchAll, 30000); // 30s
    return () => clearInterval(interval);
  }, []);

  const handleSync = async () => {
    setSyncing(true);
    try {
      const endpoint = activeTab === 'bulletins' ? '/api/status/bulletins/sync' : '/api/status/njud/sync';
      const res = await fetch(endpoint, { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        fetchAll();
      }
    } catch (e) {
      console.error("Falha na sincronização manual", e);
    } finally {
      setSyncing(false);
    }
  };

  const currentStatus = activeTab === 'bulletins' ? bulletinStatus : njudStatus;
  const currentPath = activeTab === 'bulletins' ? 'D:\\SERVIDOR\\BOLETINS' : 'D:\\SERVIDOR\\PROGRAMAS\\JORNAL';

  return (
    <div className="premium-card bulletin-central card" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
        <div className="section-title">
          <div className="accent-line" style={{ background: 'var(--accent-primary)' }} />
          CENTRAL DE CONTEÚDO
        </div>
        <button 
          className={`btn btn-primary btn-sm ${syncing ? 'syncing' : ''}`} 
          onClick={handleSync} 
          disabled={syncing}
          style={{
            fontSize: '0.68rem',
            padding: '0.4rem 0.8rem',
            minWidth: '130px'
          }}
        >
          {syncing ? '🔄 Sincronizando...' : '📥 Sincronizar Agora'}
        </button>
      </div>

      {/* Tabs Selector */}
      <div style={{ display: 'flex', background: 'rgba(255,255,255,0.02)', padding: '4px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }}>
        <button
          onClick={() => setActiveTab('bulletins')}
          className={`btn btn-sm ${activeTab === 'bulletins' ? 'btn-primary' : ''}`}
          style={{
            flex: 1,
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
            background: activeTab === 'bulletins' ? 'var(--accent-primary)' : 'transparent',
            border: 'none',
            color: activeTab === 'bulletins' ? 'var(--bg-void)' : 'var(--text-secondary)',
            boxShadow: activeTab === 'bulletins' ? 'var(--shadow-sm)' : 'none',
            transition: 'all 0.2s ease',
            padding: '0.4rem'
          }}
        >
          Boletins
        </button>
        <button
          onClick={() => setActiveTab('njud')}
          className={`btn btn-sm ${activeTab === 'njud' ? 'btn-primary' : ''}`}
          style={{
            flex: 1,
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
            background: activeTab === 'njud' ? 'var(--accent-primary)' : 'transparent',
            border: 'none',
            color: activeTab === 'njud' ? 'var(--bg-void)' : 'var(--text-secondary)',
            boxShadow: activeTab === 'njud' ? 'var(--shadow-sm)' : 'none',
            transition: 'all 0.2s ease',
            padding: '0.4rem'
          }}
        >
          Jornais (NJUD)
        </button>
      </div>

      <div className="bulletin-days-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', minHeight: '130px' }}>
        {currentStatus ? Object.entries(currentStatus).map(([day, info]) => (
          <div key={day} style={{ background: 'rgba(255,255,255,0.02)', padding: '0.6rem 0.8rem', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.05)', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
            <div style={{ fontSize: '0.56rem', fontWeight: 800, color: 'var(--text-muted)', letterSpacing: '0.5px' }}>{day}</div>
            <div style={{ fontSize: '0.8rem', fontWeight: 800, marginTop: '2px', color: 'var(--text-primary)' }}>
              {info.dates && info.dates.length > 0 ? info.dates[0] : 'Vazio'}
            </div>
            <div style={{ fontSize: '0.62rem', color: info.count > 0 ? 'var(--accent-success)' : 'var(--text-muted)', marginTop: '2px', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <span style={{ width: '5px', height: '5px', borderRadius: '50%', background: info.count > 0 ? 'var(--accent-success)' : 'var(--text-muted)' }} />
              {info.count} arquivo(s)
            </div>
          </div>
        )) : (
          <div style={{ gridColumn: 'span 2', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            Carregando dados locais...
          </div>
        )}
      </div>
      
      <div style={{ marginTop: '0.5rem', fontSize: '0.6rem', color: 'var(--text-muted)', textAlign: 'center', background: 'rgba(255,255,255,0.01)', padding: '6px', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.02)' }}>
        Diretório Local: <strong>{currentPath}</strong>
      </div>
    </div>
  );
}
