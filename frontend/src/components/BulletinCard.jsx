import { useState, useEffect } from 'react';

export default function BulletinCard() {
  const [activeTab, setActiveTab] = useState('bulletins'); // 'bulletins', 'njud' ou 'giro'
  const [bulletinStatus, setBulletinStatus] = useState(null);
  const [njudStatus, setNjudStatus] = useState(null);
  const [giroStatus, setGiroStatus] = useState(null);
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

  const fetchGiroStatus = async () => {
    try {
      const res = await fetch('/api/status/giro/status');
      if (res.ok) {
        const data = await res.json();
        setGiroStatus(data);
      }
    } catch (e) {
      console.error("Erro ao buscar status do Giro", e);
    }
  };

  const fetchAll = () => {
    fetchBulletinStatus();
    fetchNjudStatus();
    fetchGiroStatus();
  };

  useEffect(() => {
    fetchAll();
    const interval = setInterval(fetchAll, 30000); // 30s
    return () => clearInterval(interval);
  }, []);

  const handleSync = async () => {
    setSyncing(true);
    try {
      const res = await fetch('/api/workers/spider/run', { method: 'POST' });
      const data = await res.json();
      if (data.result && data.result.status !== 'error') {
        fetchAll();
      } else {
        console.error("Falha na sincronização do Spider:", data.result?.violations);
      }
    } catch (e) {
      console.error("Falha no acionamento do Spider", e);
    } finally {
      setSyncing(false);
    }
  };

  const currentStatus = activeTab === 'bulletins' ? bulletinStatus : (activeTab === 'njud' ? njudStatus : giroStatus);
  const currentPath = activeTab === 'bulletins' ? 'D:\\SERVIDOR\\BOLETINS' : (activeTab === 'njud' ? 'D:\\SERVIDOR\\PROGRAMAS\\JORNAL' : 'D:\\SERVIDOR\\PROGRAMAS\\PROGRAMA_40\\GIRONASCOMARCAS');

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
          {syncing ? '🔄 Sincronizando...' : '📥 Sincronizar via Spider'}
        </button>
      </div>

      {/* Tabs Selector */}
      <div style={{ display: 'flex', background: 'rgba(255,255,255,0.02)', padding: '4px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)', gap: '4px' }}>
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
            padding: '0.4rem',
            fontSize: '0.6rem'
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
            padding: '0.4rem',
            fontSize: '0.6rem'
          }}
        >
          Jornais
        </button>
        <button
          onClick={() => setActiveTab('giro')}
          className={`btn btn-sm ${activeTab === 'giro' ? 'btn-primary' : ''}`}
          style={{
            flex: 1,
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
            background: activeTab === 'giro' ? 'var(--accent-primary)' : 'transparent',
            border: 'none',
            color: activeTab === 'giro' ? 'var(--bg-void)' : 'var(--text-secondary)',
            boxShadow: activeTab === 'giro' ? 'var(--shadow-sm)' : 'none',
            transition: 'all 0.2s ease',
            padding: '0.4rem',
            fontSize: '0.6rem'
          }}
        >
          Giro
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
