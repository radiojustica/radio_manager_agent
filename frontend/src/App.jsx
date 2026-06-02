import { useState, useEffect } from 'react';
import { WebSocketProvider, useWsData } from './context/WebSocketContext';
import NowPlayingCard from './components/NowPlayingCard';
import BulletinCard from './components/BulletinCard';
import EventTicker from './components/EventTicker';
import ControlPanel from './components/ControlPanel';
import AcervoPage from './components/AcervoPage';
import ConfigPage from './components/ConfigPage';
import AcquisitionPage from './components/AcquisitionPage';
import AutopilotCard from './components/AutopilotCard';
import SchedulePage from './components/SchedulePage';

/* ── ICONS ─────────────────────────────────────────── */
const Icon = {
  Monitor: () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>
    </svg>
  ),
  Library: () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
    </svg>
  ),
  Download: () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
    </svg>
  ),
  Settings: () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
    </svg>
  ),
  Expand: () => (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/>
    </svg>
  ),
  Shrink: () => (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 8V5a2 2 0 0 1 2-2h3m13 5V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/>
    </svg>
  ),
  Radio: () => (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="2"/><path d="M12 7a5 5 0 0 1 5 5 5 5 0 0 1-5 5 5 5 0 0 1-5-5 5 5 0 0 1 5-5z"/><path d="M12 2a10 10 0 0 1 10 10 10 10 0 0 1-10 10 10 10 0 0 1-10-10 10 10 0 0 1 10-10z"/>
    </svg>
  ),
  Calendar: () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
    </svg>
  ),
};

/* ── PAGE META ─────────────────────────────────────── */
const PAGES = {
  monitoramento: { title: 'Centro de Controle', sub: 'Telemetria sistêmica em tempo real' },
  acervo:        { title: 'Database SQLite',    sub: 'Gestão de metadados e algoritmos' },
  aquisicao:     { title: 'Expansão de Acervo', sub: 'Aquisição inteligente de novas faixas' },
  grade:         { title: 'Grade Horária',      sub: 'Gerenciamento visual do ecossistema de blocos' },
  configuracoes: { title: 'Hub de Sensores',    sub: 'Ajuste de regras e filtros de segurança' },
};

/* ── DAYPART ───────────────────────────────────────── */
function getDaypart() {
  const h = new Date().getHours();
  if (h >= 0  && h < 5)  return { name: 'Madrugada',   format: 'Suave / Automática',     range: 'E1, E2', color: '#38bdf8' };
  if (h >= 5  && h < 10) return { name: 'Manhã',        format: 'Energética / Despertar', range: 'E4, E5', color: '#fbbf24' };
  if (h >= 10 && h < 16) return { name: 'Tarde',        format: 'Hits / Trabalho',        range: 'E3, E4', color: '#10b981' };
  if (h >= 16 && h < 20) return { name: 'Fim de Tarde', format: 'Agitado / Road Rhythm',  range: 'E4, E5', color: '#f97316' };
  return                         { name: 'Noite',        format: 'Tranquila / Romântica',  range: 'E1, E2', color: '#6366f1' };
}

/* ── INNER APP (uses WS context) ───────────────────── */
function InnerApp() {
  const [activeTab, setActiveTab] = useState('monitoramento');
  const [stats, setStats] = useState({ total: 0, auditadas: 0, redflags: 0, health: null, energia_dist: {}, top_estilos: null, top_artistas: null });
  const [mood, setMood] = useState('Ensolarado');
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [error, setError] = useState(null);
  const { connected } = useWsData();

  useEffect(() => {
    const isFull = activeTab === 'acervo';
    const fetchStats = async () => {
      try {
        const res = await fetch(`/api/engine/stats?full=${isFull}`);
        if (!res.ok) throw new Error('API offline');
        setStats(await res.json());
        setError(null);
      } catch {
        setError('Conexão com o Servidor Omni Core perdida.');
      }
    };
    fetchStats();
    const id = setInterval(fetchStats, 5000);
    return () => clearInterval(id);
  }, [activeTab]);

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen?.();
      setIsFullscreen(false);
    }
  };

  const page = PAGES[activeTab] || PAGES.monitoramento;
  const daypart = getDaypart();

  const NAV = [
    { id: 'monitoramento', label: 'Cockpit',    Icon: Icon.Monitor  },
    { id: 'acervo',        label: 'Biblioteca', Icon: Icon.Library  },
    { id: 'aquisicao',     label: 'Aquisição',  Icon: Icon.Download },
    { id: 'grade',         label: 'Grade',      Icon: Icon.Calendar },
    { id: 'configuracoes', label: 'Sensores',   Icon: Icon.Settings },
  ];

  return (
    <div className={`dashboard-layout ${isFullscreen ? 'fullscreen' : ''}`}>
      {/* ── SIDEBAR ── */}
      <nav className="sidebar">
        <div className="brand">
          <div className="brand-logo">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="white">
              <path d="M12 2L2 7v10l10 5 10-5V7l-10-5zm0 2.8L19 8.2v7.6l-7 3.4-7-3.4V8.2l7-3.4z"/>
            </svg>
          </div>
          <div>
            <div className="brand-name">Omni Core</div>
            <div className="brand-sub">Radio Engine</div>
          </div>
        </div>

        <div className="nav-section">
          {NAV.map(({ id, label, Icon: Ic }) => (
            <div
              key={id}
              className={`nav-item ${activeTab === id ? 'active' : ''}`}
              onClick={() => setActiveTab(id)}
            >
              <Ic />
              <span>{label}</span>
            </div>
          ))}
        </div>

        <div className="guardian-pill">
          <div className="guardian-dot" />
          <span className="guardian-label">AI Guardian Online</span>
          <span className={`ws-indicator ${connected ? 'connected' : ''}`} title={connected ? 'WS conectado' : 'WS desconectado'} />
        </div>
      </nav>

      {/* ── MAIN ── */}
      <main className="main-viewport">
        {error && (
          <div className="error-alert">
            <span>⚠️</span>
            {error}
          </div>
        )}

        <header className="top-header">
          <div className="page-title">
            <h1>{page.title}</h1>
            <p>{page.sub}</p>
          </div>
          <div className="header-actions">
            {activeTab === 'monitoramento' && (
              <button
                className="btn"
                onClick={() => fetch('/api/status/system/show-window', { method: 'POST' })}
              >
                <Icon.Radio /> Abrir Backend
              </button>
            )}
            <button className="btn btn-icon" onClick={toggleFullscreen} title="Alternar tela cheia">
              {isFullscreen ? <Icon.Shrink /> : <Icon.Expand />}
            </button>
          </div>
        </header>

        {/* ── MONITORAMENTO ── */}
        {activeTab === 'monitoramento' && (
          <div className="monitor-grid fade-in">
            {/* Coluna Esquerda */}
            <div className="col-stack">
              <NowPlayingCard />
              <BulletinCard />

              {/* Stats trio */}
              <div className="stats-trio">
                {[
                  { label: 'ACERVO TOTAL', value: stats?.total || 0, cls: '' },
                  { label: 'AUDITADAS',    value: stats?.auditadas || 0, cls: 'success' },
                  { label: 'RED FLAGS',    value: stats?.redflags || 0, cls: 'danger' },
                ].map(({ label, value, cls }) => (
                  <div key={label} className="card card-sm">
                    <div className="card-label">{label}</div>
                    <div className={`card-value ${cls}`}>{value}</div>
                  </div>
                ))}
              </div>

              {/* Hardware Health */}
              <div className="card">
                <div className="section-header">
                  <div className="section-title">
                    <div className="accent-line" style={{ background: 'var(--accent-danger)' }} />
                    SAÚDE CRÍTICA DO HARDWARE
                  </div>
                </div>
                {stats?.health ? (
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
                    {/* CPU */}
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', marginBottom: '0.5rem' }}>
                        <span style={{ fontWeight: 600 }}>Carga de CPU</span>
                        <span style={{ fontWeight: 800, color: stats.health.cpu > 80 ? 'var(--accent-danger)' : 'var(--accent-primary)' }}>
                          {stats.health.cpu}%
                        </span>
                      </div>
                      <div className="progress-track">
                        <div className="progress-fill" style={{ width: `${stats.health.cpu}%`, background: 'var(--accent-primary)' }} />
                      </div>
                    </div>
                    {/* RAM */}
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', marginBottom: '0.5rem' }}>
                        <span style={{ fontWeight: 600 }}>Memória RAM</span>
                        <span style={{ fontWeight: 800 }}>{stats.health.ram_percent}%</span>
                      </div>
                      <div className="progress-track">
                        <div className="progress-fill" style={{ width: `${stats.health.ram_percent}%`, background: 'var(--accent-success)' }} />
                      </div>
                      <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', marginTop: '4px', textAlign: 'right', fontWeight: 700 }}>
                        {stats.health.ram_free_mb} MB DISPONÍVEL
                      </div>
                    </div>
                  </div>
                ) : (
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Obtendo telemetria de hardware...</div>
                )}
              </div>
            </div>

            {/* Coluna Direita */}
            <div className="col-stack">
              <ControlPanel
                currentMood={mood}
                setMood={setMood}
                onTrigger={(ep) => fetch(`/api/engine/${ep}?mood=${mood}`, { method: 'POST' })}
                onSync={() => fetch('/api/status/acervo/sync', { method: 'POST' })}
              />

              <AutopilotCard />

              {/* Daypart */}
              <div className="card">
                <div className="section-header">
                  <div className="section-title">
                    <div className="accent-line" />
                    FILTRO DE ENERGIA ATIVO
                  </div>
                  <span className="status-badge playing" style={{ fontSize: '0.58rem' }}>AUTO-DAYPARTING</span>
                </div>

                <div className="daypart-block">
                  <div className="daypart-dot" style={{ background: daypart.color, boxShadow: `0 0 12px ${daypart.color}` }} />
                  <div>
                    <div className="daypart-name">
                      {daypart.name}
                      <span className="daypart-range">— {daypart.range}</span>
                    </div>
                    <div className="daypart-format">{daypart.format}</div>
                  </div>
                </div>

                <div className="daypart-meta">
                  <div className="daypart-meta-item"><strong>Quota Regional:</strong> Ativa (1/30m)</div>
                  <div className="daypart-meta-item" style={{ textAlign: 'right' }}><strong>Padding:</strong> +800s Security</div>
                </div>
              </div>

              {/* Insights */}
              {stats?.top_estilos && (
                <div className="card">
                  <div className="section-header">
                    <div className="section-title">
                      <div className="accent-line" style={{ background: 'var(--accent-warning)' }} />
                      INSIGHTS DO ACERVO
                    </div>
                    <span style={{ fontSize: '0.68rem', color: 'var(--accent-primary)', fontWeight: 800 }}>
                      {stats.tempo_total_h}H DE MÚSICA
                    </span>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    {/* Top artista */}
                    {stats.top_artistas?.length > 0 && (
                      <div>
                        <div className="insight-row-label">Maior Representatividade</div>
                        <div className="insight-row">
                          <span className="insight-artist">{stats.top_artistas[0].nome}</span>
                          <span className="insight-count">{stats.top_artistas[0].qtd} faixas</span>
                        </div>
                      </div>
                    )}

                    {/* Estilos */}
                    <div>
                      <div className="insight-row-label">Top Estilos Musicais</div>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        {stats.top_estilos.slice(0, 3).map((e, i) => (
                          <div key={i} className="style-bar-row">
                            <div className="style-bar-tick" style={{ background: i === 0 ? 'var(--accent-primary)' : 'rgba(255,255,255,0.08)' }} />
                            <span style={{ flex: 1 }}>{e.nome}</span>
                            <span className="style-bar-pct">{Math.round((e.qtd / stats.total) * 100)}%</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Energy distribution */}
                    <div>
                      <div className="insight-row-label">Densidade de Energia (E1–E5)</div>
                      <div className="energy-bars">
                        {Object.entries(stats.energia_dist).map(([lvl, cnt]) => (
                          <div
                            key={lvl}
                            className="energy-bar"
                            style={{
                              height: `${Math.max(15, (cnt / stats.total) * 100)}%`,
                              background: Number(lvl) > 3 ? 'var(--accent-warning)' : 'var(--accent-primary)',
                            }}
                          />
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

        {activeTab === 'acervo'        && <AcervoPage />}
        {activeTab === 'aquisicao'     && <AcquisitionPage />}
        {activeTab === 'grade'         && <SchedulePage />}
        {activeTab === 'configuracoes' && <ConfigPage />}
      </main>

      {isFullscreen && (
        <div className="fullscreen-hint">Pressione ESC para sair da imersão</div>
      )}
    </div>
  );
}

/* ── ROOT EXPORT ───────────────────────────────────── */
export default function App() {
  return (
    <WebSocketProvider>
      <InnerApp />
    </WebSocketProvider>
  );
}
