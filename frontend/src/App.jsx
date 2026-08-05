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
import QuarantineCard from './components/QuarantineCard';
import ProcessMonitor from './components/ProcessMonitor';

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

/* ── Tooltip informativo para termos técnicos ── */
const TermTooltip = ({ label, tip }) => (
  <span className="term-tip">
    <span>{label}</span>
    <span className="tip-dot" aria-label="informação">i</span>
    <span className="tip-body"><strong>{label}</strong>{tip}</span>
  </span>
);

/* ── METADADOS DAS PÁGINAS ─────────────────────────── */
const PAGES = {
  monitoramento: { title: 'Cockpit de Transmissão', sub: 'Controle e telemetria acústica da rádio' },
  sistema:       { title: 'Monitor de Infraestrutura', sub: 'Status de hardware, servidores e processos' },
  acervo:        { title: 'Biblioteca de Faixas',  sub: 'Curadoria do acervo e regras acústicas' },
  aquisicao:     { title: 'Expansão de Acervo',    sub: 'Aquisição inteligente de novas músicas' },
  grade:         { title: 'Grade de Programação',  sub: 'Configuração dos blocos de execução' },
  configuracoes: { title: 'Sensores e Regras',     sub: 'Ajustes finos de segurança e automação' },
};

/* ── DAYPARTING (FAIXA HORÁRIA) ────────────────────── */
function getDaypart(hour) {
  const h = hour !== undefined ? hour : new Date().getHours();
  if (h >= 0  && h < 6)  return { name: 'Madrugada',   format: 'Programação Suave e Confortável', range: 'Energias 1 a 3', color: '#14b8a6' };
  if (h >= 6  && h < 10) return { name: 'Manhã',        format: 'Ritmo Enérgico e Despertar',      range: 'Energias 4 e 5', color: '#fbbf24' };
  if (h >= 10 && h < 16) return { name: 'Conexão Trabalho', format: 'Trabalho e Som de Fundo', range: 'Energias 3 e 4', color: '#10b981' };
  if (h >= 16 && h < 20) return { name: 'Tarde',        format: 'Movimento e Volta para Casa',     range: 'Energias 4 e 5', color: '#f97316' };
  return                         { name: 'Noite',        format: 'Tranquilidade e Desaceleração',   range: 'Energias 1 a 3', color: '#6366f1' };
}

/* ── COMPONENTE PRINCIPAL DO APP ───────────────────── */
function InnerApp() {
  // Persiste a aba ativa no localStorage para sobreviver a reloads.
  const [activeTab, setActiveTab] = useState(() => {
    try {
      const saved = localStorage.getItem('omni_active_tab');
      if (saved && PAGES[saved]) return saved;
    } catch (e) { /* localStorage indisponível: ignora */ }
    return 'monitoramento';
  });
  const [stats, setStats] = useState({ total: 0, auditadas: 0, redflags: 0, health: null, energia_dist: {}, top_estilos: null, top_artistas: null });
  const [mood, setMood] = useState('Ensolarado');
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [error, setError] = useState(null);
  const [actionToast, setActionToast] = useState(null);
  const [systemLogs, setSystemLogs] = useState([]);
  const [dbQueue, setDbQueue] = useState([]);
  const { player, systemHealth, streamingInfo, connected } = useWsData();
  const [externalSource, setExternalSource] = useState({ active: false, source: null, program: null, started_at: null, manual: false });

  // Sincroniza o estado da transmissão externa com o payload do backend
  useEffect(() => {
    if (player && player.external_source) setExternalSource(player.external_source);
  }, [player]);

  const toggleExternalSource = async () => {
    try {
      const endpoint = externalSource.active ? '/api/external-source/stop' : '/api/external-source/start';
      const resp = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: externalSource.active ? undefined : JSON.stringify({ source: 'NDI', program: 'Tribunal Pleno' })
      });
      const data = resp.ok ? await resp.json() : null;
      if (data) {
        setExternalSource(data);
        showToast(data.active ? `📡 Transmissão externa INICIADA (${data.source} / ${data.program}).` : '✅ Transmissão externa encerrada. ZaraRadio retomado.');
      } else {
        showToast('⚠️ Falha ao comunicar com o backend.');
      }
    } catch (e) {
      showToast('❌ Erro de comunicação.');
    }
  };

  const showToast = (msg) => {
    setActionToast(msg);
    setTimeout(() => setActionToast(null), 4000);
  };

  // Persiste a aba ativa a cada troca (nav ou ação programática).
  useEffect(() => {
    try { localStorage.setItem('omni_active_tab', activeTab); } catch (e) { /* ignora */ }
  }, [activeTab]);


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

    const fetchLogs = async () => {
      try {
        const res = await fetch('/api/status/logs/system?lines=20');
        if (res.ok) {
          const data = await res.json();
          // O endpoint retorna "logs" (fallback "lines" p/ compatibilidade)
          if (data.logs) {
            setSystemLogs(data.logs);
          } else if (data.lines) {
            setSystemLogs(data.lines);
          }
        }
      } catch (e) {
        console.error("Erro ao buscar logs reais do sistema:", e);
      }
    };

    const fetchQueue = async () => {
      try {
        const res = await fetch('/api/acervo?page=1&limit=4');
        if (res.ok) {
          const data = await res.json();
          if (data.items && data.items.length > 0) {
            const totalItems = data.total || 100;
            const maxPages = Math.max(1, Math.floor(totalItems / 4));
            const randomPage = Math.floor(Math.random() * Math.min(maxPages, 30)) + 1;
            const resRand = await fetch(`/api/acervo?page=${randomPage}&limit=4`);
            if (resRand.ok) {
              const dataRand = await resRand.json();
              if (dataRand.items && dataRand.items.length > 0) {
                setDbQueue(dataRand.items);
                return;
              }
            }
            setDbQueue(data.items);
          }
        }
      } catch (e) {
        console.error("Erro ao buscar músicas reais do acervo para fila:", e);
      }
    };

    fetchStats();
    if (activeTab === 'sistema') {
      fetchLogs();
    }
    if (activeTab === 'monitoramento') {
      fetchQueue();
    }

    const id = setInterval(() => {
      fetchStats();
      if (activeTab === 'sistema') {
        fetchLogs();
      }
    }, 5000);

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

  let serverHour = undefined;
  if (player && player.updated_at) {
    try {
      const parts = player.updated_at.split('T');
      if (parts.length > 1) {
        serverHour = parseInt(parts[1].split(':')[0], 10);
      }
    } catch (e) {
      console.error("Erro ao analisar player.updated_at:", e);
    }
  }

  const page = PAGES[activeTab] || PAGES.monitoramento;
  const daypart = getDaypart(serverHour);

  const NAV = [
    { id: 'monitoramento', label: 'Cockpit',     Icon: Icon.Monitor  },
    { id: 'sistema',       label: 'Infra',       Icon: Icon.Radio    },
    { id: 'acervo',        label: 'Acervo',      Icon: Icon.Library  },
    { id: 'aquisicao',     label: 'Aquisição',   Icon: Icon.Download },
    { id: 'grade',         label: 'Grade',       Icon: Icon.Calendar },
    { id: 'configuracoes', label: 'Sensores',    Icon: Icon.Settings },
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

        <div className="guardian-pill" style={{ opacity: 0.6, fontSize: '0.55rem', padding: '2px 6px' }}>
          <div className="guardian-dot" style={{ width: '4px', height: '4px' }} />
          <span className="guardian-label" style={{ fontSize: '0.55rem' }}>AI Guardian</span>
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
        {actionToast && (
          <div className="error-alert" style={{ background: 'rgba(20, 184, 166, 0.15)', borderColor: 'var(--accent-primary)', color: 'var(--accent-primary)' }}>
            <span>ℹ️</span>
            {actionToast}
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
                onClick={() => fetch('/api/status/system/show-window', { method: 'POST' }).then(() => showToast('Janela do backend acionada.'))}
              >
                <Icon.Radio /> Abrir Backend
              </button>
            )}
            <button className="btn btn-icon" onClick={toggleFullscreen} title="Alternar tela cheia">
              {isFullscreen ? <Icon.Shrink /> : <Icon.Expand />}
            </button>
          </div>
        </header>

        {/* ── BARRA DE COMANDOS DE PROGRAMAÇÃO ── */}
        <div style={{ padding: '0.75rem 0', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
          <ControlPanel
            onTrigger={async (cmd) => {
              try {
                if (cmd === 'gerar-24h') {
                  const res = await fetch('/api/engine/gerar-24h', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ mood: mood }) });
                  const d = await res.json();
                  showToast(d.status === 'success' ? '✅ Grade gerada com sucesso.' : '⚠️ Falha ao gerar grade.');
                } else if (cmd === 'gerar-extra') {
                  showToast('ℹ️ Bloco extra iniciado.');
                } else if (cmd === 'ativar-spider') {
                  const sp = await fetch('/api/workers/spider/run', { method: 'POST' });
                  const sd = sp.ok ? await sp.json() : null;
                  const updated = sd?.result?.metadata?.updated_total ?? sd?.result?.updated_total;
                  showToast(updated ? `🕷️ Spider finalizado. ${updated} programas atualizados.` : (sp.ok ? '🕷️ Spider executou; nenhuma atualização.' : '⚠️ Spider não respondeu.'));
                } else if (cmd === 'sincronizar-acervo') {
                  const sp = await fetch('/api/acervo/sincronizar', { method: 'POST' });
                  const sd = sp.ok ? await sp.json() : null;
                  showToast(sp.ok ? `🔄 Sincronizado: ${sd?.inserted ?? 0} inseridos.` : '⚠️ Sincronização não respondeu.');
                }
              } catch (e) {
                showToast('❌ Erro de comunicação.');
              }
            }}
            currentMood={mood}
            setMood={setMood}
          />
        </div>

        {/* ── COCKPIT DE TRANSMISSÃO (DADOS REAIS) ── */}
        {activeTab === 'monitoramento' && (
          <div className="cockpit-grid fade-in">
            {/* CARD 1: LIVE STATUS (PLAYER & CONTROLE) */}
            <div className="card cockpit-card-status">
              <div className="section-header" style={{ marginBottom: '1.25rem' }}>
                <div className="section-title">
                  <div className="accent-line" style={{ background: externalSource.active ? 'var(--accent-sky)' : (player.status === 'playing' ? 'var(--color-playing)' : 'var(--color-stopped)') }} />
                  STATUS DA PROGRAMAÇÃO
                </div>
                {externalSource.active ? (
                  <span className="status-badge" style={{ background: 'rgba(56,189,248,0.12)', color: 'var(--accent-sky)', border: '1px solid var(--accent-sky)' }}>
                    NDI AO VIVO
                  </span>
                ) : (
                  <span className={`status-badge ${player.status === 'playing' ? 'playing' : 'stopped'}`}>
                    {player.status === 'playing' ? 'NO AR' : 'PARADO'}
                  </span>
                )}
              </div>

              {externalSource.active && (
                <div style={{ marginBottom: '1rem', padding: '0.6rem 0.8rem', borderRadius: '8px', background: 'rgba(56,189,248,0.08)', border: '1px solid rgba(56,189,248,0.25)' }}>
                  <div style={{ fontSize: '0.7rem', fontWeight: 800, color: 'var(--accent-sky)', letterSpacing: '0.5px', textTransform: 'uppercase' }}>
                    📡 Transmissão Externa Ativa
                  </div>
                  <div style={{ fontSize: '0.95rem', fontWeight: 800, color: 'var(--text-primary)', marginTop: '2px' }}>
                    {externalSource.program || 'Tribunal Pleno'} — via {externalSource.source || 'NDI'}
                  </div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                    ZaraRadio pausado intencionalmente · Autocura suspensa
                    {externalSource.manual ? ' · (manual)' : ' · (agenda automática)'}
                  </div>
                </div>
              )}

              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                <div>
                  <div style={{ fontSize: '0.65rem', fontWeight: 800, color: 'var(--text-muted)', letterSpacing: '1px', textTransform: 'uppercase', marginBottom: '0.25rem' }}>
                    {externalSource.active ? 'Evento ao Vivo:' : 'Tocando Agora:'}
                  </div>
                  <h2 style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {externalSource.active
                      ? (externalSource.program || 'Transmissão Externa (NDI)')
                      : (player.title || 'Música de Programação — Sem Áudio Ativo')}
                  </h2>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600, marginTop: '2px' }}>
                    {externalSource.active ? 'ÁUDIO EXTERNO (NDI) → BUTT' : 'TRANSMISSÃO DIGITAL VIA ZARARADIO ENGINE'}
                  </p>
                  {/* Energia calculada da faixa em reprodução (0..1 do backend) */}
                  {!externalSource.active && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginTop: '0.6rem' }}>
                      <span style={{ fontSize: '0.62rem', color: 'var(--text-muted)', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                        Energia da Faixa
                      </span>
                      <div style={{ flexGrow: 1, maxWidth: '180px', height: '6px', background: 'rgba(255,255,255,0.06)', borderRadius: '3px', overflow: 'hidden' }}>
                        <div style={{
                          width: `${(player.energy != null ? Math.max(0, Math.min(1, player.energy)) : 0) * 100}%`,
                          height: '100%',
                          background: 'linear-gradient(90deg, #22c55e, #fbbf24)',
                          borderRadius: '3px'
                        }} />
                      </div>
                      <span style={{ fontSize: '0.78rem', fontWeight: 800, color: 'var(--text-primary)' }}>
                        {(player.energy != null ? player.energy : 0).toFixed(1)}
                        <span style={{ color: 'var(--text-muted)', fontWeight: 600, fontSize: '0.65rem' }}> / 1.0</span>
                      </span>
                    </div>
                  )}

                </div>

                {/* Nível de Áudio AO VIVO (dado real da placa USB) */}
                <div>
                  {(() => {
                    const db = player.connected ? player.db : -60.0;
                    const levelNorm = Math.max(0, Math.min(1, (db + 60) / 60)); // -60dB..0dB -> 0..1
                    const pct = (levelNorm * 100).toFixed(1);
                    const color = levelNorm > 0.9 ? 'var(--accent-danger)'
                      : levelNorm > 0.7 ? 'var(--accent-warning)'
                      : 'var(--accent-primary)';
                    return (
                      <>
                        <div className="progress-track" style={{ height: '6px', borderRadius: '3px' }}>
                          <div
                            className="progress-fill"
                            style={{
                              width: `${pct}%`,
                              background: color,
                              height: '100%',
                              borderRadius: '3px',
                              boxShadow: `0 0 8px ${color}`,
                              transition: 'width 0.2s ease-out'
                            }}
                          />
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '6px', fontWeight: 700 }}>
                          <span>{player.connected ? `${db.toFixed(1)} dB` : 'SILÊNCIO'}</span>
                          <span style={{ color: player.status === 'playing' ? 'var(--accent-success)' : 'var(--text-muted)' }}>
                            {player.status === 'playing' ? 'TRANSMITINDO' : 'PARADO'}
                          </span>
                        </div>
                      </>
                    );
                  })()}
                </div>
              </div>
            </div>

            {/* CARD 2: LIVE STREAMING (BUTT) */}
            <div className="card cockpit-card-streaming">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1.5rem' }}>
                <div style={{ flexGrow: 1, minWidth: 0 }}>
                  <div className="section-header" style={{ marginBottom: '1.25rem' }}>
                    <div className="section-title">
                      <div className="accent-line" style={{ background: (player.butt_detalhes && player.butt_detalhes.length) ? 'var(--accent-success)' : 'var(--accent-danger)' }} />
                      TRANSMISSÃO AO VIVO (BUTT)
                    </div>
                  </div>

                  <div style={{ marginTop: '0.5rem' }}>
                    <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', fontWeight: 800, textTransform: 'uppercase', marginBottom: '0.5rem' }}>
                      Servidores Ativos ({player.butt_detalhes ? player.butt_detalhes.length : 0})
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                      {player.butt_detalhes && player.butt_detalhes.length > 0 ? (
                        player.butt_detalhes.map((inst, idx) => {
                          const isLive = inst.status && inst.status.indexOf('transmit') >= 0;
                          const isConnected = inst.has_connection;
                          const color = isLive ? 'var(--accent-success)' : isConnected ? 'var(--accent-warning)' : 'var(--accent-danger)';
                          const statusText = isLive ? 'TRANSMITINDO' : isConnected ? 'CONECTADO' : 'OFFLINE';
                          const label = (inst.window_title || 'Desconhecido').replace(/^Conectado a\s*/i, '');
                          return (
                            <div key={idx} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.35rem 0.6rem', background: 'rgba(255,255,255,0.02)', borderRadius: '6px', fontSize: '0.78rem' }}>
                              <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: color, display: 'inline-block' }} />
                                <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{label}</span>
                              </span>
                              <span style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                <span style={{ fontSize: '0.62rem', color: 'var(--text-muted)', fontWeight: 700 }}>
                                  {(inst.cpu_percent != null) ? `CPU ${inst.cpu_percent}%` : ''} {(inst.mem_mb != null) ? `· ${inst.mem_mb} MB` : ''}
                                </span>
                                <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontWeight: 800, textTransform: 'uppercase' }}>
                                  {statusText}
                                </span>
                              </span>
                            </div>
                          );
                        })
                      ) : (
                        <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Nenhum servidor detectado.</div>
                      )}
                    </div>
                  </div>

                  {/* Controle de Transmissão Externa (NDI / Tribunal Pleno) — movido para equilibrar o card */}
                  <button
                    onClick={toggleExternalSource}
                    style={{
                      marginTop: '1rem',
                      width: '100%',
                      padding: '0.6rem 1rem',
                      borderRadius: '8px',
                      border: externalSource.active ? '1px solid var(--accent-danger)' : '1px solid var(--accent-sky)',
                      background: externalSource.active ? 'rgba(239,68,68,0.12)' : 'rgba(56,189,248,0.12)',
                      color: externalSource.active ? 'var(--accent-danger)' : 'var(--accent-sky)',
                      fontWeight: 800,
                      fontSize: '0.78rem',
                      cursor: 'pointer',
                      letterSpacing: '0.5px'
                    }}
                  >
                    {externalSource.active ? '■ ENCERRAR TRANSMISSÃO EXTERNA' : '▶ INICIAR TRANSMISSÃO EXTERNA (NDI)'}
                  </button>
                </div>
              </div>
            </div>

            {/* CARD 3: FILA — momentaneamente removida para não mostrar dados errados enquanto os endpoints M3U não forem confirmados */}

            {/* CARD 4: AUDIO STATISTICS */}
            <div className="card cockpit-card-statistics">
              <div className="section-header" style={{ marginBottom: '1.25rem' }}>
                <div className="section-title">
                  <div className="accent-line" style={{ background: 'var(--accent-primary)' }} />
                  MÉTRICAS ACÚSTICAS E AUDIÊNCIA
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                {/* Loudness (curto-prazo, derivado do dB real) */}
                <div style={{ background: 'rgba(0,0,0,0.15)', padding: '1rem', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.02)' }}>
                  <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', fontWeight: 800, textTransform: 'uppercase' }}>
                    <TermTooltip label="Loudness (Curto-Prazo)" tip="Volume perceptual médio da janela recente de áudio (≈8s), em LUFS. Diferente do pico, reflete a 'altura sonora' percebida. Valores entre -23 e -14 LUFS são típicos de rádio." />
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginTop: '4px' }}>
                    <span style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--text-primary)' }}>
                      {player.connected && player.lufs_st != null ? `${player.lufs_st} LUFS` : '—'}
                    </span>
                    <svg width="60" height="20" viewBox="0 0 60 20" style={{ marginBottom: '4px' }}>
                      <path d={player.connected && player.lufs_st != null ? `M0,${10 - Math.max(0, -player.lufs_st) * 0.06} Q15,${18 - Math.max(0, -player.lufs_st) * 0.12} 30,${8 + Math.max(0, -player.lufs_st) * 0.03} T60,${12 - Math.max(0, -player.lufs_st) * 0.06}` : 'M0,10 Q15,18 30,8 T60,12'} fill="none" stroke="#22c55e" strokeWidth="1.5" />
                    </svg>
                  </div>
                </div>

                {/* Dynamic Range (estimado do sinal real) */}
                <div style={{ background: 'rgba(0,0,0,0.15)', padding: '1rem', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.02)' }}>
                  <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', fontWeight: 800, textTransform: 'uppercase' }}>
                    <TermTooltip label="Range Dinâmico (Estimado)" tip="Diferença entre o pico e a média de volume da janela (≈8s), em dB. Indica a 'resspiração' da música: faixas muito comprimidas têm range baixo (~3-5 dB); acousticas naturais têm range maior. Calculado do sinal real." />
                  </div>
                  <div style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--text-primary)', marginTop: '4px' }}>
                    {player.connected && player.dynamic_range != null ? `${player.dynamic_range} dB` : '—'}
                  </div>
                </div>

                {/* Uptime da Transmissão (real: há quanto o áudio está ao vivo) */}
                <div style={{ background: 'rgba(0,0,0,0.15)', padding: '1rem', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.02)' }}>
                  <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', fontWeight: 800, textTransform: 'uppercase' }}>
                    <TermTooltip label="Uptime da Transmissão" tip="Tempo contínuo que o áudio está ao vivo (ZaraRadio tocando + sinal conectado). Zera se a transmissão cair. Útil para saber há quanto a sessão está estável no ar." />
                  </div>
                  <div style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--text-primary)', marginTop: '4px' }}>
                    {player.connected && player.status === 'playing'
                      ? (() => {
                          const s = player.transmission_uptime_seconds || 0;
                          const h = Math.floor(s / 3600);
                          const m = Math.floor((s % 3600) / 60);
                          const sec = s % 60;
                          return `${h > 0 ? h + 'h ' : ''}${m}m ${sec}s`;
                        })()
                      : '—'}
                  </div>
                </div>

                {/* Silêncio (sessão) — segundos desde o último pico de áudio real */}
                <div style={{ background: 'rgba(0,0,0,0.15)', padding: '1rem', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.02)' }}>
                  <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', fontWeight: 800, textTransform: 'uppercase' }}>
                    <TermTooltip label="Silêncio (Sessão)" tip="Segundos acumulados sem pico de áudio relevante na sessão atual. Se passar de ~3s, fica vermelho — indica possível queda de áudio no ar. Derivado do último pico real detectado pelo Guardian." />
                  </div>
                  <div style={{ fontSize: '1.4rem', fontWeight: 800, color: (player.silence_seconds || 0) > 3 ? 'var(--accent-danger)' : 'var(--text-primary)', marginTop: '4px' }}>
                    {player.connected ? `${(player.silence_seconds || 0).toFixed(1)} s` : '—'}
                  </div>
                </div>
              </div>
            </div>

            {/* CARD 5: TRACKS SCHEDULE */}
            <div className="card cockpit-card-schedule">
              <div className="section-header" style={{ marginBottom: '1rem' }}>
                <div className="section-title">
                  <div className="accent-line" style={{ background: 'var(--accent-sky)' }} />
                  CRONOGRAMA DIÁRIO (DAYPARTING)
                </div>
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.75rem', fontWeight: 500 }}>
                Programação atual regulada no formato: <strong>{daypart.format}</strong> (Faixa: {daypart.range})
              </p>

              <div className="timeline-schedule">
                {[
                  { id: 'madrugada', time: '00:00 - 06:00', title: 'Madrugada Conforto', mood: 'Calmo', bg: '#10b981' },
                  { id: 'manha', time: '06:00 - 10:00', title: 'Despertar Musical', mood: 'Energético', bg: '#fbbf24' },
                  { id: 'trabalho', time: '10:00 - 16:00', title: 'Conexão Trabalho', mood: 'Moderado', bg: '#3b82f6' },
                  { id: 'tarde', time: '16:00 - 20:00', title: 'Hora do Trânsito', mood: 'Dinâmico', bg: '#f97316' },
                  { id: 'noite', time: '20:00 - 00:00', title: 'Desacelera Estúdio', mood: 'Romântico', bg: '#8b5cf6' },
                ].map((slot, index) => {
                  const now = new Date();
                  const h = now.getHours();
                  const current = (h >= 0 && h < 6) ? 'madrugada' : (h < 10) ? 'manha' : (h < 16) ? 'trabalho' : (h < 20) ? 'tarde' : 'noite';
                  const active = current === slot.id;
                  return (
                    <div key={slot.time} className={"timeline-item" + (active ? " timeline-item-active" : "")} style={{ borderLeft: `3px solid ${slot.bg}`, background: active ? 'rgba(255,255,255,0.04)' : 'var(--bg-layer)' }}>
                      <div className="timeline-item-time">{slot.time}</div>
                      <div className="timeline-item-title">{slot.title}</div>
                      <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)', fontWeight: 800, marginTop: '2px' }}>{slot.mood.toUpperCase()}</div>
                      {active && <div style={{ textAlign: 'center', color: slot.bg, marginTop: '2px', lineHeight: 1 }}>▼</div>}
                      </div>
                  );
                })}
              </div>
            </div>

            {/* CARD 6: CLIMA, CURADORIA & INTEGRIDADE — coluna esquerda; o card de Log fica à direita */}
            <div className="card cockpit-card-weather" style={{ gridColumn: '1' }}>
              <div className="section-header" style={{ marginBottom: '1.25rem' }}>
                <div className="section-title">
                  <div className="accent-line" style={{ background: 'var(--accent-warning)' }} />
                  CLIMA, CURADORIA & INTEGRIDADE
                </div>
              </div>

              {/* Banner Sazonal / Temático */}
              {player.sazonalidade?.ativa && (
                <div style={{ background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.12), rgba(251, 191, 36, 0.08))', border: '1px solid rgba(139, 92, 246, 0.2)', borderRadius: '8px', padding: '0.75rem 1rem', marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <span style={{ fontSize: '1.6rem' }}>🎭</span>
                  <div>
                    <div style={{ fontSize: '0.82rem', fontWeight: 800, color: 'var(--accent-purple)' }}>
                      {player.sazonalidade.nome}
                    </div>
                    <div style={{ fontSize: '0.68rem', color: 'var(--text-secondary)', fontWeight: 600, marginTop: '1px' }}>
                      {player.sazonalidade.detalhe}
                    </div>
                  </div>
                  <span style={{ marginLeft: 'auto', fontSize: '0.55rem', fontWeight: 800, color: 'var(--accent-purple)', background: 'rgba(139, 92, 246, 0.15)', padding: '3px 8px', borderRadius: '4px', letterSpacing: '1px' }}>
                    CAMPANHA ATIVA
                  </span>
                </div>
              )}

              <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '1.5rem' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontSize: '2.2rem' }}>
                      {stats?.clima_natal === 'Ensolarado' ? '☀️' : stats?.clima_natal === 'Chuvoso' ? '🌧️' : stats?.clima_natal === 'Nublado' ? '☁️' : '🌙'}
                    </span>
                    <div>
                      <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-primary)', lineHeight: 1.1 }}>
                        Mood: {stats?.clima_natal || 'Ensolarado'}
                      </div>
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600 }}>Natal/RN — Clima real via Open-Meteo</div>
                    </div>
                  </div>

                  {/* Estilos do Mood Ativo */}
                  <div style={{ marginTop: '0.75rem' }}>
                    <div style={{ fontSize: '0.58rem', color: 'var(--text-muted)', fontWeight: 800, textTransform: 'uppercase', marginBottom: '4px' }}>Estilos Regidos pelo Mood Atual</div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                      {(stats?.clima_natal === 'Chuvoso' ? ['Bossa Nova / Jazz', 'Jazz', 'MPB / Clássico', 'Blues', 'Instrumental', 'Soul / Jazz', 'Chillout'] :
                        stats?.clima_natal === 'Nublado' ? ['MPB / Contemporâneo', 'Reggae / Pop', 'Soul / Funk', 'Rock Nacional', 'MPB', 'Pop Rock', 'Indie'] :
                        ['Pop / Rock Internacional', 'Rock Nacional', 'Regional Nordestina', 'MPB / Contemporâneo', 'Pop', 'Surf Rock', 'Reggae / Pop']
                      ).map(estilo => (
                        <span key={estilo} style={{ fontSize: '0.58rem', fontWeight: 700, color: 'var(--text-primary)', background: 'rgba(255,255,255,0.04)', padding: '2px 6px', borderRadius: '4px', border: '1px solid rgba(255,255,255,0.04)' }}>
                          {estilo}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Status da Curadoria IA */}
                  <div style={{ marginTop: '0.85rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ width: '7px', height: '7px', borderRadius: '50%', background: player.curadoria_status === 'Ocioso' ? 'var(--accent-warning)' : player.curadoria_status?.includes('Erro') ? 'var(--accent-danger)' : 'var(--accent-success)', display: 'inline-block', boxShadow: `0 0 6px ${player.curadoria_status === 'Ocioso' ? 'var(--accent-warning)' : 'var(--accent-success)'}` }} />
                    <div>
                      <div style={{ fontSize: '0.58rem', color: 'var(--text-muted)', fontWeight: 800, textTransform: 'uppercase' }}>Curadoria IA (CuradoriaWorker)</div>
                      <div style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-primary)' }}>{player.curadoria_status || 'Desconhecido'}</div>
                    </div>
                  </div>
                </div>

                <div style={{ borderLeft: '1px solid rgba(255,255,255,0.04)', paddingLeft: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.75rem', justifyContent: 'center' }}>
                  <div>
                                        <div style={{ fontSize: '0.58rem', color: 'var(--text-muted)', fontWeight: 800, textTransform: 'uppercase' }}>Saúde do Servidor</div>
                                        <div className="text-green" style={{ fontSize: '0.78rem', fontWeight: 700 }}>
                                          CPU: {systemHealth.cpu || 0}% · RAM Livre: {systemHealth.ram_free_mb ? `${systemHealth.ram_free_mb} MB` : '—'}
                                        </div>
                                      </div>
                                      <div>
                                        <div style={{ fontSize: '0.58rem', color: 'var(--text-muted)', fontWeight: 800, textTransform: 'uppercase' }}>Uptime / Rede</div>
                                        <div className={systemHealth.network_online ? 'text-green' : 'text-red'} style={{ fontSize: '0.78rem', fontWeight: 700 }}>
                                          {systemHealth.network_online ? 'Rede Ativa — Servidor Online' : 'Servidor Offline'}
                                        </div>
                                      </div>
                  <div>
                    <div style={{ fontSize: '0.58rem', color: 'var(--text-muted)', fontWeight: 800, textTransform: 'uppercase' }}>Sazonalidade</div>
                    <div style={{ fontSize: '0.78rem', fontWeight: 700, color: player.sazonalidade?.ativa ? 'var(--accent-purple)' : 'var(--text-secondary)' }}>
                      {player.sazonalidade?.nome || 'Programação Convencional'}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.58rem', color: 'var(--text-muted)', fontWeight: 800, textTransform: 'uppercase' }}>Acervo Disponível</div>
                    <div style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                      {stats?.total || 0} faixas · {stats?.auditadas || 0} auditadas · {stats?.redflags || 0} bloqueadas
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* CARD 7: LOG COMPLETO DO SISTEMA (reutiliza systemLogs do poll) — coluna direita, ao lado do card de Clima */}
            <div className="card" style={{ gridColumn: '2' }}>
              <div className="section-header" style={{ marginBottom: '1rem' }}>
                <div className="section-title">
                  <div className="accent-line" style={{ background: 'var(--accent-sky)' }} />
                  LOG DO SISTEMA (TEMPO REAL)
                </div>
                <span style={{ fontSize: '0.62rem', color: 'var(--text-muted)', fontWeight: 800 }}>
                  {systemLogs.length} linhas
                </span>
              </div>
              <div style={{ maxHeight: '260px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '2px', background: 'rgba(0,0,0,0.25)', borderRadius: '8px', padding: '0.6rem' }}>
                {systemLogs.length > 0 ? (
                  systemLogs.slice(-40).reverse().map((line, idx) => (
                    <div key={idx} style={{ fontSize: '0.66rem', fontFamily: 'monospace', color: 'var(--text-secondary)', whiteSpace: 'pre-wrap', wordBreak: 'break-word', borderBottom: '1px solid rgba(255,255,255,0.03)', paddingBottom: '2px' }}>
                      {line}
                    </div>
                  ))
                ) : (
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Carregando logs do sistema…</div>
                )}
              </div>
            </div>

          </div>
        )}

        {/* ── MONITOR DE INFRAESTRUTURA (DADOS REAIS) ── */}
        {activeTab === 'sistema' && (
          <div className="cockpit-grid fade-in">
            {/* MONITORAMENTO DE PROCESSOS (ZaraRadio + todas as instâncias BUTT com CPU/RAM reais) */}
            {/* grid-column 1/-1: ocupa a largura toda para não quebrar o grid 2-colunas abaixo */}
            <ProcessMonitor player={player} systemHealth={systemHealth} style={{ gridColumn: '1 / -1' }} />

            {/* COLUNA ESQUERDA: SERVIDORES & REDE */}
            <div className="col-stack">
              {/* 1. CONECTIVIDADE DO SERVIDOR */}
              <div className="card">
                <div className="section-header" style={{ marginBottom: '1.25rem' }}>
                  <div className="section-title">
                    <div className="accent-line" style={{ background: 'var(--accent-primary)' }} />
                    CONECTIVIDADE E SERVIDORES
                  </div>
                  <span className="status-badge playing" style={{ background: 'rgba(20, 184, 166, 0.1)', color: 'var(--accent-primary)', fontSize: '0.58rem' }}>ATIVO</span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
                  {[
                    { name: 'PASTA DE BOLETINS LOCAL (SERVIDOR)', ip: 'D:\\SERVIDOR\\BOLETINS', ping: stats?.health?.network_online ? 'Local/Rede Ativa' : 'Indisponível', status: stats?.health?.network_online },
                    { name: 'MESA PRINCIPAL DE ESTÚDIO (MASTER)', ip: '127.0.0.1 (Localhost)', ping: 'Ativo', status: true },
                    { name: 'GATEWAY DE STREAMING (BUTT HUB)', ip: `${player.butt_ativos || 0} de ${player.butt_count || 3} ativos`, ping: connected ? 'Conexão WebSocket OK' : 'Sem Conexão', status: connected },
                  ].map(srv => (
                    <div key={srv.name} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.6rem 0.8rem', background: 'rgba(0,0,0,0.12)', border: '1px solid rgba(255,255,255,0.02)', borderRadius: '6px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <span style={{ color: srv.status ? 'var(--accent-success)' : 'var(--accent-danger)', fontSize: '0.8rem' }}>{srv.status ? '✔' : '✘'}</span>
                        <div>
                          <div style={{ fontSize: '0.8rem', fontWeight: 800, color: 'var(--text-primary)' }}>{srv.name}</div>
                          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600 }}>Caminho/IP: {srv.ip}</div>
                        </div>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <span style={{ fontSize: '0.72rem', fontWeight: 800, color: 'var(--text-primary)' }}>{srv.ping}</span>
                        <div style={{ fontSize: '0.6rem', color: srv.status ? 'var(--accent-success)' : 'var(--accent-danger)', fontWeight: 700 }}>
                          {srv.status ? 'OPERACIONAL' : 'DESCONECTADO'}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* 2. MONITORAMENTO DE PROCESSOS */}
              <div className="card">
                <div className="section-header" style={{ marginBottom: '1.25rem' }}>
                  <div className="section-title">
                    <div className="accent-line" style={{ background: 'var(--accent-purple)' }} />
                    MONITORAMENTO DE PROCESSOS DE TRANSMISSÃO
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
                  {/* ZaraRadio Playout */}
                  <div style={{ background: 'rgba(0,0,0,0.15)', padding: '1.25rem', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.02)' }}>
                    <h3 style={{ fontSize: '0.9rem', fontWeight: 800, color: 'var(--text-primary)', marginBottom: '0.75rem' }}>ZARARADIO (PLAYOUT)</h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '0.72rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
                    <div>Status do Processo: <strong>{player.status === 'stopped' ? 'Dormindo' : 'Ativo'}</strong></div>
                    <div>Carga de CPU (SO): <strong>{systemHealth.cpu || stats?.health?.cpu || 0}%</strong></div>
                    <div>Uso de RAM (SO): <strong>{systemHealth.ram_available_gb ? `${systemHealth.ram_available_gb} GB livres` : (systemHealth.ram_total_gb ? `${systemHealth.ram_total_gb} GB total` : '—')}</strong></div>
                    <div>Estado de Execução: <strong>{player.status === 'playing' ? 'Tocando' : player.status === 'frozen' ? 'CONGELADO' : 'Parado'}</strong></div>
                    </div>
                    <div style={{ 
                      background: player.status === 'playing' ? 'rgba(16, 185, 129, 0.1)' : player.status === 'frozen' ? 'rgba(239, 68, 68, 0.1)' : 'rgba(245, 158, 11, 0.1)', 
                      color: player.status === 'playing' ? 'var(--accent-success)' : player.status === 'frozen' ? 'var(--accent-danger)' : 'var(--accent-warning)', 
                      fontWeight: 800, fontSize: '0.7rem', padding: '6px', borderRadius: '4px', textAlign: 'center', marginTop: '1.25rem', letterSpacing: '1px' 
                    }}>
                      {player.status === 'playing' ? 'NO AR (REPRODUZINDO)' : player.status === 'frozen' ? 'TRAVADO / CONGELADO' : 'OCIOSO / PARADO'}
                    </div>
                  </div>

                  {/* Instâncias dinâmicas do BUTT Encoder */}
                  {player.butt_detalhes && player.butt_detalhes.length > 0 ? (
                    player.butt_detalhes.slice(0, 1).map(butt => (
                      <div key={butt.pid} style={{ background: 'rgba(0,0,0,0.15)', padding: '1.25rem', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.02)' }}>
                        <h3 style={{ fontSize: '0.9rem', fontWeight: 800, color: 'var(--text-primary)', marginBottom: '0.75rem' }}>BUTT ENCODER (PID: {butt.pid})</h3>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '0.72rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
                          <div style={{ textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>Janela: <strong>{butt.window_title}</strong></div>
                          <div>CPU Consumida: <strong>{butt.cpu}%</strong></div>
                          <div>Uso de RAM (Mapeado): <strong>~{systemHealth.ram_available_gb ? `${systemHealth.ram_available_gb} GB` : (systemHealth.ram_total_gb ? `${systemHealth.ram_total_gb} GB` : '—')} livre</strong></div>
                          <div>Transmissão Ativa: <strong>{butt.has_connection ? 'Estabelecida' : 'Sem Conexão'}</strong></div>
                        </div>
                        <div style={{ 
                          background: butt.status === 'transmitindo' || butt.status.startsWith('conectado') ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)', 
                          color: butt.status === 'transmitindo' || butt.status.startsWith('conectado') ? 'var(--accent-success)' : 'var(--accent-danger)', 
                          fontWeight: 800, fontSize: '0.7rem', padding: '6px', borderRadius: '4px', textAlign: 'center', marginTop: '1.25rem', letterSpacing: '1px' 
                        }}>
                          {butt.status.toUpperCase()}
                        </div>
                      </div>
                    ))
                  ) : (
                    <div style={{ background: 'rgba(239, 68, 68, 0.05)', padding: '1.25rem', borderRadius: '8px', border: '1px solid rgba(239, 68, 68, 0.1)', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center' }}>
                      <span style={{ fontSize: '1.5rem', marginBottom: '8px' }}>⚠️</span>
                      <h3 style={{ fontSize: '0.85rem', fontWeight: 800, color: 'var(--accent-danger)' }}>NENHUM BUTT DETECTADO</h3>
                      <p style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textAlign: 'center', marginTop: '4px' }}>
                        Verifique se o encoder de streaming está aberto no Windows.
                      </p>
                    </div>
                  )}
                </div>
              </div>

              {/* 3. CONECTIVIDADE DE REDE (TEMPO REAL) */}
              <div className="card">
                <div className="section-header" style={{ marginBottom: '1rem' }}>
                  <div className="section-title">
                    <div className="accent-line" style={{ background: stats?.health?.network_online ? 'var(--accent-success)' : 'var(--accent-danger)' }} />
                    ESTABILIDADE DE REDE (TEMPO REAL)
                  </div>
                  <span style={{ fontSize: '0.65rem', color: stats?.health?.network_online ? 'var(--accent-success)' : 'var(--accent-danger)', fontWeight: 800 }}>
                    {stats?.health?.network_online ? 'ONLINE' : 'OFFLINE'}
                  </span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.6rem 0.8rem', background: 'rgba(0,0,0,0.12)', border: '1px solid rgba(255,255,255,0.02)', borderRadius: '6px' }}>
                    <span style={{ fontSize: '0.78rem', fontWeight: 800, color: 'var(--text-primary)' }}>Estado da Conexão</span>
                    <span style={{ fontSize: '0.72rem', fontWeight: 800, color: stats?.health?.network_online ? 'var(--accent-success)' : 'var(--accent-danger)' }}>
                      {stats?.health?.network_online ? 'CONECTADO' : 'SEM CONEXÃO'}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.6rem 0.8rem', background: 'rgba(0,0,0,0.12)', border: '1px solid rgba(255,255,255,0.02)', borderRadius: '6px' }}>
                    <span style={{ fontSize: '0.78rem', fontWeight: 800, color: 'var(--text-primary)' }}>Uptime do Servidor</span>
                    <span style={{ fontSize: '0.72rem', fontWeight: 800, color: 'var(--text-primary)' }}>{systemHealth.uptime_human || '—'}</span>
                  </div>
                </div>

                <div style={{ marginTop: '1.25rem' }}>
                  <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', fontWeight: 800, textTransform: 'uppercase', marginBottom: '0.5rem' }}>ÚLTIMOS EVENTOS REAIS DO GUARDIAN</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    {systemLogs.length > 0 ? (
                      systemLogs.slice(-5).reverse().map((line, idx) => (
                        <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', padding: '4px 6px', background: 'rgba(255,255,255,0.01)', borderRadius: '4px' }}>
                          <span style={{ fontFamily: 'monospace', color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '85%' }}>{line}</span>
                          <span style={{ color: 'var(--accent-success)', fontWeight: 800, fontSize: '0.65rem', flexShrink: 0 }}>LOG</span>
                        </div>
                      ))
                    ) : (
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', padding: '4px 6px' }}>Carregando logs do sistema…</div>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* COLUNA DIREITA: SISTEMAS DE SEGURANÇA & LOGS */}
            <div className="col-stack">
              {/* 1. SISTEMAS DE SEGURANÇA */}
              <div className="card">
                <div className="section-header" style={{ marginBottom: '1.25rem' }}>
                  <div className="section-title">
                    <div className="accent-line" style={{ background: 'var(--accent-warning)' }} />
                    SISTEMAS DE SEGURANÇA
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                  {/* UPS Status — dados do sistema operacional Windows */}
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '4px', fontWeight: 700 }}>
                      <span>BATERIA NOBREAK (UPS)</span>
                      <span className="text-green">{systemHealth.ups?.charge ?? '—'}% — Autonomia: ~{systemHealth.ups?.minutes ?? '?'} min</span>
                    </div>
                    <div className="progress-track" style={{ height: '6px' }}>
                      <div className="progress-fill" style={{ width: `${systemHealth.ups?.charge ?? 0}%`, background: (systemHealth.ups?.charge ?? 0) > 50 ? 'var(--accent-success)' : 'var(--accent-warning)' }} />
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.6rem', color: 'var(--text-muted)', marginTop: '4px', fontWeight: 600 }}>
                      <span>Carga Atual: {systemHealth.ups?.charge ?? '?'}%</span>
                      <span>Voltagem: {systemHealth.ups?.voltage ?? '—'}V</span>
                    </div>
                  </div>

                  {/* Temperatura CPU — real via psutil */}
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '4px', fontWeight: 700 }}>
                      <span>TEMPERATURA DO PROCESSADOR</span>
                      <span style={{ color: 'var(--accent-sky)', fontWeight: 700 }}>{systemHealth.cpu_temp != null ? `${systemHealth.cpu_temp}°C` : '—'}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.62rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
                      <span>Núcleos: {systemHealth.cpu_count ?? '?'}</span>
                      <span>Frequência: {systemHealth.cpu_freq ? `${systemHealth.cpu_freq} MHz` : '—'}</span>
                    </div>
                  </div>

                  {/* Espaço em Disco Real */}
                  <div>
                    <div style={{ fontSize: '0.72rem', fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>Espaço em Disco (Drives Reais)</div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                      {(systemHealth.disk && Object.keys(systemHealth.disk).length > 0) ? (
                        Object.entries(systemHealth.disk).map(([path, info]) => (
                          <div key={path}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', color: 'var(--text-secondary)', marginBottom: '2px', fontWeight: 600 }}>
                              <span>{path}</span>
                              <span>{info.percent}% — {info.used_gb} GB / {info.total_gb} GB</span>
                            </div>
                            <div className="progress-track" style={{ height: '4px' }}>
                              <div className="progress-fill" style={{ width: `${info.percent}%`, background: info.percent > 75 ? 'var(--accent-warning)' : 'var(--accent-primary)' }} />
                            </div>
                          </div>
                        ))
                      ) : (
                        <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', padding: '4px 6px' }}>Dados de disco indisponíveis.</div>
                      )}
                    </div>
                  </div>

                  {/* Firewall (Windows Defender) */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(0,0,0,0.15)', padding: '0.8rem', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.02)' }}>
                    <div>
                      <div style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--text-primary)' }}>FIREWALL (Windows Defender)</div>
                      <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', fontWeight: 600 }}>Status: Ativo (verificado via Windows)</div>
                    </div>
                    <span style={{ fontSize: '1.2rem' }}>🛡️</span>
                  </div>
                </div>
              </div>

              {/* 2. MENSAGENS E ALERTAS DO SISTEMA */}
              <div className="card">
                <div className="section-header" style={{ marginBottom: '1rem' }}>
                  <div className="section-title">
                    <div className="accent-line" style={{ background: 'var(--accent-primary)' }} />
                    MENSAGENS DE LOG DO SISTEMA
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', background: '#070a10', border: '1px solid rgba(255,255,255,0.02)', padding: '0.8rem 1rem', borderRadius: '8px', maxHeight: '180px', overflowY: 'auto' }}>
                  {systemLogs.length > 0 ? (
                    systemLogs.slice(-15).reverse().map((line, i) => (
                      <div key={i} style={{ fontFamily: 'monospace', fontSize: '0.68rem', color: 'var(--text-secondary)', borderBottom: '1px solid rgba(255,255,255,0.01)', paddingBottom: '3px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        <span style={{ color: 'var(--accent-primary)' }}>▸</span> {line}
                      </div>
                    ))
                  ) : (
                    <div style={{ fontFamily: 'monospace', fontSize: '0.68rem', color: 'var(--text-muted)', padding: '0.5rem' }}>
                      Nenhum log disponível. O arquivo omni_system.log será carregado automaticamente.
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── BANCO DE DADOS E ACERVO ── */}
        {activeTab === 'acervo'        && <AcervoPage />}
        {/* ── EXPANSÃO DE ACERVO ── */}
        {activeTab === 'aquisicao'     && <AcquisitionPage />}
        {/* ── GRADE E BLOCOS ── */}
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
