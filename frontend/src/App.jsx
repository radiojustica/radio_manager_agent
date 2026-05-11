import { useState, useEffect } from 'react';
import NowPlayingCard from './components/NowPlayingCard';
import BulletinCard from './components/BulletinCard';
import EventTicker from './components/EventTicker';
import ControlPanel from './components/ControlPanel';
import AcervoPage from './components/AcervoPage';
import ConfigPage from './components/ConfigPage';
import AcquisitionPage from './components/AcquisitionPage';

const Icons = {
  Monitor: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="3" width="20" height="14" rx="2" ry="2" /><line x1="8" y1="21" x2="16" y2="21" /><line x1="12" y1="17" x2="12" y2="21" />
    </svg>
  ),
  Library: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 14h3M8 14h10M3 18h3M8 18h7M3 10h18M3 6h18" />
    </svg>
  ),
  Download: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
    </svg>
  ),
  Settings: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  ),
  Export: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" />
    </svg>
  ),
  Expand: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" />
    </svg>
  ),
  Shrink: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 8V5a2 2 0 0 1 2-2h3m13 5V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" />
    </svg>
  ),
  Radio: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="2"/><path d="M12 7a5 5 0 0 1 5 5 5 5 0 0 1-5 5 5 5 0 0 1-5-5 5 5 0 0 1 5-5z"/><path d="M12 2a10 10 0 0 1 10 10 10 10 0 0 1-10 10 10 10 0 0 1-10-10 10 10 0 0 1 10-10z"/>
    </svg>
  )
};

function App() {
  const [activeTab, setActiveTab] = useState('monitoramento');
  const [stats, setStats] = useState({ total: 0, auditadas: 0, redflags: 0, health: null, energia_dist: {} });
  const [mood, setMood] = useState('Ensolarado');
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const isFull = activeTab === 'acervo';
    const fetchStats = async () => {
      try {
        const res = await fetch(`/api/engine/stats?full=${isFull}`);
        if (!res.ok) throw new Error("API Offline");
        const data = await res.json();
        setStats(data);
        setError(null);
      } catch (err) {
        console.error("Erro na telemetria:", err);
        setError("Conexão com o Servidor Omni Core perdida.");
      }
    };

    fetchStats();
    const interval = setInterval(fetchStats, 5000);
    return () => clearInterval(interval);
  }, [activeTab]);

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
      setIsFullscreen(true);
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
        setIsFullscreen(false);
      }
    }
  };

  const handleExportCSV = () => {
    window.location.href = '/api/acervo/exportar';
  };

  return (
    <div className={`dashboard-layout ${isFullscreen ? 'fullscreen' : ''}`}>
      {/* SIDEBAR */}
      <nav className="sidebar">
        <div className="brand-header">
          <div className="brand-icon-box">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="white">
              <path d="M12 2L2 7v10l10 5 10-5V7l-10-5zm0 2.8L19 8.2v7.6l-7 3.4-7-3.4V8.2l7-3.4z" />
            </svg>
          </div>
          <span className="brand-text">Omni Core</span>
        </div>

        <div className="nav-links">
          <div className={`nav-link ${activeTab === 'monitoramento' ? 'active' : ''}`} onClick={() => setActiveTab('monitoramento')}>
            <Icons.Monitor />
            <span>Cockpit</span>
          </div>
          <div className={`nav-link ${activeTab === 'acervo' ? 'active' : ''}`} onClick={() => setActiveTab('acervo')}>
            <Icons.Library />
            <span>Biblioteca</span>
          </div>
          <div className={`nav-link ${activeTab === 'aquisicao' ? 'active' : ''}`} onClick={() => setActiveTab('aquisicao')}>
            <Icons.Download />
            <span>Aquisição</span>
          </div>
          <div className={`nav-link ${activeTab === 'configuracoes' ? 'active' : ''}`} onClick={() => setActiveTab('configuracoes')}>
            <Icons.Settings />
            <span>Sensores</span>
          </div>
        </div>

        <div style={{ marginTop: 'auto', padding: '1.5rem', display: 'flex', alignItems: 'center', gap: '8px', background: 'rgba(255,255,255,0.02)', borderRadius: '14px' }}>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--accent-success)', boxShadow: '0 0 10px var(--accent-success)' }}></div>
          <span style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--text-secondary)' }}>AI GUARDIAN ONLINE</span>
        </div>
      </nav>

      {/* MAIN CONTENT AREA */}
      <main className="main-viewport">
        {error && (
          <div className="connection-error-alert" style={{ 
            background: 'rgba(239, 68, 68, 0.1)', 
            border: '1px solid var(--accent-danger)', 
            padding: '1rem 2rem', 
            borderRadius: '12px', 
            marginBottom: '2rem',
            color: 'var(--accent-danger)',
            fontWeight: 700,
            display: 'flex',
            alignItems: 'center',
            gap: '12px'
          }}>
             <span style={{ fontSize: '1.2rem' }}>⚠️</span> {error}
          </div>
        )}
        <header className="top-nav">
          <div className="breadcrumb">
            <h1>{activeTab === 'monitoramento' ? 'Centro de Controle' : activeTab === 'acervo' ? 'Database SQLite' : activeTab === 'aquisicao' ? 'Expansão de Acervo' : 'Hub de Sensores'}</h1>
            <p>{activeTab === 'monitoramento' ? 'Telemetria sistêmica em tempo real' : activeTab === 'acervo' ? 'Gestão de metadados e algoritmos' : activeTab === 'aquisicao' ? 'Aquisição inteligente de novas faixas' : 'Ajuste de regras e filtros de segurança'}</p>
          </div>

          <div className="utility-bar">
            {activeTab === 'monitoramento' && (
              <button 
                className="btn-action" 
                onClick={() => fetch('/api/status/system/show-window', { method: 'POST' })}
              >
                <Icons.Radio />
                Abrir Backend
              </button>
            )}

            <button className="icon-btn" onClick={toggleFullscreen} title="Alternar Tela Cheia">
              {isFullscreen ? <Icons.Shrink /> : <Icons.Expand />}
            </button>
          </div>
        </header>

        {activeTab === 'monitoramento' && (
          <div className="monitor-grid">
            <div className="card-stack">
              <NowPlayingCard />
              <BulletinCard />
              
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.5rem' }}>
                <div className="premium-card" style={{ padding: '1.5rem' }}>
                  <div style={{ fontSize: '0.65rem', fontWeight: 800, color: 'var(--text-muted)', letterSpacing: '1px' }}>ACERVO TOTAL</div>
                  <div style={{ fontSize: '2rem', fontWeight: 800, marginTop: '5px' }}>{stats?.total || 0}</div>
                </div>
                <div className="premium-card" style={{ padding: '1.5rem' }}>
                  <div style={{ fontSize: '0.65rem', fontWeight: 800, color: 'var(--text-muted)', letterSpacing: '1px' }}>AUDITADAS</div>
                  <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--accent-success)', marginTop: '5px' }}>{stats?.auditadas || 0}</div>
                </div>
                <div className="premium-card" style={{ padding: '1.5rem' }}>
                  <div style={{ fontSize: '0.65rem', fontWeight: 800, color: 'var(--text-muted)', letterSpacing: '1px' }}>RED FLAGS</div>
                  <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--accent-danger)', marginTop: '5px' }}>{stats?.redflags || 0}</div>
                </div>
              </div>

              {/* HEALTH MONITOR INTEGRADO NO DASHBOARD */}
              <div className="premium-card health-monitor-dashboard" style={{ paddingTop: '1.5rem', paddingBottom: '1.5rem' }}>
                <div style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--text-secondary)', letterSpacing: '1.5px', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                   <div style={{ width: '12px', height: '2px', background: 'var(--accent-danger)' }}></div>
                   SAÚDE CRÍTICA DO HARDWARE
                </div>
                {stats?.health ? (
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '3rem' }}>
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '8px' }}>
                        <span style={{ fontWeight: 600 }}>Carga de CPU</span>
                        <span style={{ fontWeight: 800, color: stats.health.cpu > 80 ? 'var(--accent-danger)' : 'var(--accent-primary)' }}>{stats.health.cpu}%</span>
                      </div>
                      <div className="progress-track" style={{ height: '8px' }}>
                        <div className="progress-bar" style={{ width: `${stats.health.cpu}%`, background: 'var(--accent-primary)' }}></div>
                      </div>
                    </div>
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '8px' }}>
                        <span style={{ fontWeight: 600 }}>Memória RAM</span>
                        <span style={{ fontWeight: 800 }}>{stats.health.ram_percent}%</span>
                      </div>
                      <div className="progress-track" style={{ height: '8px' }}>
                         <div className="progress-bar" style={{ width: `${stats.health.ram_percent}%`, background: 'var(--accent-success)' }}></div>
                      </div>
                      <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginTop: '5px', textAlign: 'right', fontWeight: 700 }}>{stats.health.ram_free_mb} MB DISPONÍVEL</div>
                    </div>
                  </div>
                ) : <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Obtendo telemetria de hardware...</div>}
              </div>
            </div>

            <div className="card-stack">
              <ControlPanel
                currentMood={mood}
                setMood={setMood}
                onTrigger={(ep) => fetch(`/api/engine/${ep}?mood=${mood}`, { method: 'POST' })}
                onSync={() => fetch('/api/acervo/sincronizar', { method: 'POST' })}
              />

              {/* CARD DE REGRAS DE PROGRAMAÇÃO (DAYPARTING) */}
              <div className="premium-card" style={{ padding: '1.5rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                  <h3 style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>FILTRO DE ENERGIA ATIVO</h3>
                  <div className="status-pill playing" style={{ fontSize: '0.6rem' }}>AUTO-DAYPARTING</div>
                </div>
                
                {(() => {
                  const h = new Date().getHours();
                  let shift = { n: "Madrugada", f: "Suave / Automática", e: "E1, E2, E3", c: "var(--accent-primary)" };
                  if (h >= 6 && h < 10) shift = { n: "Manhã", f: "Energética / Despertar", e: "E4, E5", c: "#fbbf24" };
                  else if (h >= 10 && h < 16) shift = { n: "Tarde", f: "Hits / Trabalho", e: "E3, E4", c: "#10b981" };
                  else if (h >= 16 && h < 20) shift = { n: "Fim de Tarde", f: "Agitado / Road Rhythm", e: "E4, E5", c: "#f97316" };
                  else if (h >= 20 || h < 0) shift = { n: "Noite", f: "Tranquila / Romântica", e: "E1, E2, E3", c: "#6366f1" };

                  return (
                    <div className="shift-display" style={{ display: 'flex', gap: '15px', alignItems: 'center' }}>
                      <div className="shift-icon" style={{ 
                        width: '45px', height: '45px', borderRadius: '12px', background: 'rgba(255,255,255,0.03)', 
                        display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px solid rgba(255,255,255,0.05)'
                      }}>
                        <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: shift.c, boxShadow: `0 0 15px ${shift.c}` }}></div>
                      </div>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: '1.1rem', fontWeight: 800, color: '#fff' }}>{shift.n} <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>— {shift.e}</span></div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600 }}>{shift.f}</div>
                      </div>
                    </div>
                  );
                })()}

                <div style={{ marginTop: '1.5rem', paddingTop: '1.2rem', borderTop: '1px solid rgba(255,255,255,0.05)', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                   <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                      <strong style={{ color: 'var(--text-secondary)' }}>Quota Regional:</strong> Ativa (1/30m)
                   </div>
                   <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textAlign: 'right' }}>
                      <strong style={{ color: 'var(--text-secondary)' }}>Padding:</strong> +800s Security
                   </div>
                </div>
              </div>

              {stats?.top_estilos && (
                <div className="premium-card" style={{ padding: '1.5rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                    <h3 style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>INSIGHTS DO ACERVO</h3>
                    <div style={{ fontSize: '0.65rem', color: 'var(--accent-primary)', fontWeight: 800 }}>{stats.tempo_total_h}H DE MÚSICA</div>
                  </div>

                  <div className="insights-grid" style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '1.2rem' }}>
                    {/* Representatividade de Artista */}
                    {stats.top_artistas && stats.top_artistas.length > 0 && (
                      <div className="insight-item" style={{ background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.05)' }}>
                        <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '1px' }}>Maior Representatividade</div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{ fontSize: '0.9rem', fontWeight: 800, color: 'var(--accent-warning)' }}>{stats.top_artistas[0].nome}</span>
                          <span style={{ fontSize: '0.75rem', fontWeight: 700, opacity: 0.8 }}>{stats.top_artistas[0].qtd} faixas</span>
                        </div>
                      </div>
                    )}

                    {/* Distribuição de Estilos */}
                    <div className="insight-item">
                      <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '1px' }}>Top Estilos Musicais</div>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {stats.top_estilos.slice(0, 3).map((estilo, idx) => (
                          <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <div style={{ width: '4px', height: '12px', borderRadius: '2px', background: idx === 0 ? 'var(--accent-primary)' : 'rgba(255,255,255,0.1)' }}></div>
                            <span style={{ flex: 1, fontSize: '0.75rem', fontWeight: 600 }}>{estilo.nome}</span>
                            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{Math.round((estilo.qtd / stats.total) * 100)}%</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Mini Mapa de Energia */}
                    <div className="insight-item">
                       <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '1px' }}>Densidade de Energia (E1-E5)</div>
                       <div style={{ display: 'flex', alignItems: 'flex-end', gap: '6px', height: '40px' }}>
                        {Object.entries(stats.energia_dist).map(([level, count]) => (
                          <div key={level} style={{ flex: 1, height: '100%', display: 'flex', alignItems: 'flex-end' }}>
                            <div style={{ 
                              width: '100%', 
                              height: `${Math.max(15, (count / stats.total) * 100)}%`, 
                              background: level > 3 ? 'var(--accent-warning)' : 'var(--accent-primary)',
                              borderRadius: '2px 2px 1px 1px',
                              opacity: 0.8
                            }} />
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              <EventTicker />
            </div>
          </div>
        )}

        {activeTab === 'acervo' && (
          <AcervoPage />
        )}

        {activeTab === 'aquisicao' && (
          <AcquisitionPage />
        )}

        {activeTab === 'configuracoes' && (
          <ConfigPage />
        )}
      </main>

      {isFullscreen && (
        <div className="fullscreen-exit-hint">Pressione ESC para sair da imersão</div>
      )}
    </div>
  );
}

export default App;
