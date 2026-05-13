import { useState, useEffect } from 'react';

const ProgressBar = ({ percentage, status, speed, eta }) => (
  <div style={{ marginBottom: '1rem', background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)' }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '8px', fontWeight: 700 }}>
      <span style={{ color: 'var(--text-secondary)' }}>{status?.toUpperCase()}</span>
      <span style={{ color: 'var(--accent-primary)' }}>{percentage?.toFixed(1)}%</span>
    </div>
    <div style={{ width: '100%', height: '6px', background: 'rgba(255,255,255,0.1)', borderRadius: '3px', overflow: 'hidden' }}>
      <div 
        style={{ 
          width: `${percentage}%`, 
          height: '100%', 
          background: 'var(--accent-primary)', 
          transition: 'width 0.3s ease-out',
          boxShadow: '0 0 10px var(--accent-primary)'
        }} 
      />
    </div>
    <div style={{ display: 'flex', gap: '15px', marginTop: '8px', fontSize: '0.65rem', color: 'var(--text-muted)', fontWeight: 600 }}>
      {speed && <span>⚡ {speed}</span>}
      {eta && <span>⏳ {eta}</span>}
    </div>
  </div>
);

export default function AcquisitionPage() {
  const [recommendations, setRecs] = useState([]);
  const [selected, setSelected] = useState({});
  const [loading, setLoading] = useState(false);
  const [activeDownloads, setActiveDownloads] = useState({});
  const [manualLinks, setManualLinks] = useState('');
  const [statusMsg, setStatus] = useState('');

  const fetchRecommendations = async () => {
    setLoading(true);
    setStatus('Analisando logs dos últimos 5 dias...');
    try {
      const res = await fetch('/api/downloader/recommendations');
      const data = await res.json();
      if (data.success) {
        setRecs(data.recommendations);
        setStatus(`Análise concluída. ${data.recommendations.length} sugestões encontradas.`);
      }
    } catch (e) {
      setStatus('Erro ao buscar recomendações.');
    } finally {
      setLoading(false);
    }
  };

  const fetchProgress = async () => {
    try {
      const res = await fetch('/api/downloader/progress');
      const data = await res.json();
      setActiveDownloads(data.active || {});
    } catch (e) {
      console.error("Erro ao buscar progresso:", e);
    }
  };

  useEffect(() => {
    const hasActive = Object.values(activeDownloads).some(d => d.status !== 'completed' && d.status !== 'failed');
    if (hasActive || Object.keys(activeDownloads).length > 0) {
      const interval = setInterval(fetchProgress, 2000);
      return () => clearInterval(interval);
    }
  }, [activeDownloads]);

  // Initial fetch for progress in case something is already running
  useEffect(() => {
    fetchProgress();
  }, []);

  const handleToggle = (idx) => {
    setSelected(prev => ({ ...prev, [idx]: !prev[idx] }));
  };

  const allSelected = recommendations.length > 0 && recommendations.every((_, idx) => selected[idx]);

  const handleSelectAll = () => {
    if (allSelected) {
      setSelected({});
    } else {
      const newSelected = {};
      recommendations.forEach((_, idx) => {
        newSelected[idx] = true;
      });
      setSelected(newSelected);
    }
  };

  const triggerDownloads = async (type) => {
    let queries = [];
    if (type === 'recs') {
      queries = recommendations.filter((_, idx) => selected[idx]).map(r => r.sugestao);
    } else {
      queries = manualLinks.split('\n').filter(l => l.trim() !== '');
    }

    if (queries.length === 0) return;

    try {
      const res = await fetch('/api/downloader/download', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ queries, estilo: 'outros' })
      });
      const data = await res.json();
      setStatus(data.message);
      if (type === 'manual') setManualLinks('');
      fetchProgress(); // Start polling immediately
    } catch (e) {
      setStatus('Erro ao iniciar downloads.');
    }
  };

  const downloadEntries = Object.entries(activeDownloads).filter(([_, d]) => d.status !== 'completed');

  return (
    <div className="acervo-container anim-fade-in" style={{ maxWidth: '1400px', margin: '0 auto', padding: '2rem' }}>
      <div className="page-header" style={{ marginBottom: '3rem', borderLeft: '4px solid var(--accent-primary)', paddingLeft: '1.5rem' }}>
        <h2 style={{ fontSize: '2rem', fontWeight: 900, letterSpacing: '-0.5px', color: '#fff' }}>Aquisição Inteligente</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>Expansão proativa do acervo via análise de tendências e captura multicanal.</p>
      </div>

      <div className="main-layout-flex" style={{ display: 'flex', gap: '2.5rem', alignItems: 'flex-start' }}>
        <div style={{ flex: 2, display: 'flex', flexDirection: 'column', gap: '2.5rem' }}>
          
          {/* SEÇÃO DE SUGESTÕES */}
          <div className="premium-card" style={{ padding: '2rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
              <div>
                <h3 style={{ fontSize: '1rem', fontWeight: 800, color: 'var(--accent-primary)', marginBottom: '4px' }}>RECOMENDAÇÕES DO DIRETOR</h3>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Top tendências dos últimos 5 dias</p>
              </div>
              <button 
                className="btn-action" 
                onClick={fetchRecommendations} 
                disabled={loading}
                style={{ background: 'rgba(56, 189, 248, 0.1)', color: 'var(--accent-primary)', border: '1px solid var(--accent-primary)' }}
              >
                {loading ? 'ANALISANDO...' : '🔄 ATUALIZAR'}
              </button>
            </div>

            <div className="table-scroll-area" style={{ maxHeight: '500px', overflowY: 'auto', borderRadius: '14px', border: '1px solid rgba(255,255,255,0.05)', background: 'rgba(0,0,0,0.15)' }}>
              {recommendations.length > 0 ? (
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead style={{ position: 'sticky', top: 0, background: '#111', zIndex: 10 }}>
                    <tr style={{ textAlign: 'left', fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '1px' }}>
                      <th style={{ padding: '15px 20px' }}>
                        <input type="checkbox" checked={allSelected} onChange={handleSelectAll} />
                      </th>
                      <th>Sugestão</th>
                      <th>Contexto</th>
                      <th style={{ paddingRight: '20px' }}>Estilo</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recommendations.map((rec, idx) => (
                      <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)', fontSize: '0.85rem' }}>
                        <td style={{ padding: '15px 20px' }}>
                          <input type="checkbox" checked={!!selected[idx]} onChange={() => handleToggle(idx)} />
                        </td>
                        <td style={{ padding: '15px 0' }}>
                          <div style={{ fontWeight: 800, color: '#fff' }}>{rec.artista}</div>
                          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '2px' }}>{rec.sugestao}</div>
                        </td>
                        <td style={{ color: 'var(--text-secondary)', fontSize: '0.75rem' }}>{rec.motivo}</td>
                        <td style={{ paddingRight: '20px' }}><span className="style-tag" style={{ fontSize: '0.6rem' }}>{rec.estilo}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div style={{ padding: '4rem 0', textAlign: 'center', color: 'var(--text-muted)' }}>
                  <div style={{ fontSize: '2.5rem', marginBottom: '1rem', opacity: 0.5 }}>📊</div>
                  <p style={{ fontWeight: 600 }}>Nenhuma sugestão carregada.</p>
                  <p style={{ fontSize: '0.75rem' }}>Clique em Atualizar para iniciar a análise heurística.</p>
                </div>
              )}
            </div>

            {recommendations.length > 0 && (
              <div style={{ marginTop: '2rem', display: 'flex', justifyContent: 'flex-end' }}>
                <button 
                  className="btn-action primary" 
                  onClick={() => triggerDownloads('recs')}
                  style={{ padding: '12px 30px', fontWeight: 800 }}
                >
                  📥 BAIXAR SELECIONADAS
                </button>
              </div>
            )}
          </div>
        </div>

        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '2.5rem' }}>
          
          {/* DOWNLOAD MANUAL */}
          <div className="premium-card" style={{ padding: '2rem' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 800, color: 'var(--accent-primary)', marginBottom: '1.5rem' }}>CAPTURA DIRETA</h3>
            <textarea 
              value={manualLinks}
              onChange={(e) => setManualLinks(e.target.value)}
              placeholder="Cole links do YouTube ou nomes de faixas aqui... (uma por linha)"
              style={{ 
                width: '100%', height: '180px', background: 'rgba(0,0,0,0.2)', 
                border: '1px solid rgba(255,255,255,0.08)', borderRadius: '12px',
                color: '#fff', padding: '1.2rem', fontSize: '0.85rem', fontFamily: "'Fira Code', monospace",
                resize: 'none', marginBottom: '1.5rem'
              }}
            />
            <button 
              className="btn-action block" 
              onClick={() => triggerDownloads('manual')}
              style={{ width: '100%', padding: '12px', background: 'var(--accent-primary)', color: '#000', fontWeight: 900 }}
            >
              🚀 INICIAR DOWNLOADS
            </button>
          </div>

          {/* TELEMETRIA DE DOWNLOADS ATIVOS */}
          <div className="premium-card" style={{ padding: '2rem', minHeight: '300px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '2rem' }}>
               <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: downloadEntries.length > 0 ? 'var(--accent-success)' : 'var(--text-muted)', boxShadow: downloadEntries.length > 0 ? '0 0 10px var(--accent-success)' : 'none' }}></div>
               <h3 style={{ fontSize: '0.9rem', fontWeight: 800 }}>FILA DE PROCESSAMENTO</h3>
            </div>

            {downloadEntries.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {downloadEntries.map(([query, data]) => (
                  <div key={query}>
                    <div style={{ fontSize: '0.7rem', fontWeight: 800, color: '#fff', marginBottom: '8px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {query}
                    </div>
                    <ProgressBar 
                      percentage={data.percentage} 
                      status={data.status} 
                      speed={data.speed} 
                      eta={data.eta} 
                    />
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ padding: '3rem 0', textAlign: 'center', color: 'var(--text-muted)', border: '2px dashed rgba(255,255,255,0.05)', borderRadius: '16px' }}>
                <p style={{ fontSize: '0.75rem', fontWeight: 700 }}>NENHUM DOWNLOAD ATIVO</p>
              </div>
            )}
          </div>

          {statusMsg && (
            <div style={{ 
              padding: '1.2rem', background: 'rgba(56, 189, 248, 0.05)', 
              borderRadius: '12px', border: '1px solid rgba(56, 189, 248, 0.2)', color: 'var(--accent-primary)',
              fontSize: '0.8rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '12px'
            }}>
              <span>ℹ️</span> {statusMsg}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
