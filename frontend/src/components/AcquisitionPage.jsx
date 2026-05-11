import { useState } from 'react';

export default function AcquisitionPage() {
  const [recommendations, setRecs] = useState([]);
  const [selected, setSelected] = useState({});
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);
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

  const handleToggle = (idx) => {
    setSelected(prev => ({ ...prev, [idx]: !prev[idx] }));
  };

  const triggerDownloads = async (type) => {
    setDownloading(true);
    let queries = [];
    
    if (type === 'recs') {
      queries = recommendations.filter((_, idx) => selected[idx]).map(r => r.sugestao);
    } else {
      queries = manualLinks.split('\n').filter(l => l.trim() !== '');
    }

    if (queries.length === 0) {
      alert('Nenhuma música selecionada ou link inserido.');
      setDownloading(false);
      return;
    }

    try {
      const res = await fetch('/api/downloader/download', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ queries, estilo: 'outros' })
      });
      const data = await res.json();
      setStatus(data.message);
      if (type === 'manual') setManualLinks('');
    } catch (e) {
      setStatus('Erro ao iniciar downloads.');
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="acervo-container anim-fade-in">
      <div className="page-header" style={{ marginBottom: '2rem' }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--accent-primary)' }}>Aquisição Proativa de Acervo</h2>
        <p style={{ color: 'var(--text-secondary)' }}>Módulo de expansão inteligente baseado em tendências de reprodução.</p>
      </div>

      <div className="grid-2col" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
        {/* COMPORTAMENTO 2: INTELIGENTE */}
        <div className="premium-card" style={{ padding: '1.5rem' }}>
          <div className="card-header-flex" style={{ marginBottom: '1.5rem' }}>
            <h3 className="module-tag">SUGESTÕES DO DIRETOR</h3>
            <button 
              className="action-btn" 
              onClick={fetchRecommendations} 
              disabled={loading}
              style={{ background: 'var(--accent-primary)', color: '#000', padding: '8px 16px', borderRadius: '8px', fontWeight: 700 }}
            >
              {loading ? 'ANALISANDO...' : '🔄 UPDATE (LER LOGS)'}
            </button>
          </div>

          <div className="recs-list" style={{ minHeight: '300px', background: 'rgba(0,0,0,0.2)', borderRadius: '12px', padding: '10px' }}>
            {recommendations.length > 0 ? (
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ textAlign: 'left', fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                    <th style={{ padding: '10px' }}>Sel.</th>
                    <th>Artista / Sugestão</th>
                    <th>Estilo</th>
                  </tr>
                </thead>
                <tbody>
                  {recommendations.map((rec, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', fontSize: '0.85rem' }}>
                      <td style={{ padding: '10px' }}>
                        <input type="checkbox" checked={!!selected[idx]} onChange={() => handleToggle(idx)} />
                      </td>
                      <td style={{ padding: '10px' }}>
                        <div style={{ fontWeight: 700 }}>{rec.artista}</div>
                        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{rec.motivo}</div>
                      </td>
                      <td><span className="style-tag">{rec.estilo}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '300px', color: 'var(--text-muted)' }}>
                <span style={{ fontSize: '2rem', marginBottom: '1rem' }}>📊</span>
                <p>Clique em Update para analisar os últimos 5 dias.</p>
              </div>
            )}
          </div>

          {recommendations.length > 0 && (
            <button 
              className="action-btn" 
              onClick={() => triggerDownloads('recs')} 
              disabled={downloading}
              style={{ width: '100%', marginTop: '1.5rem', background: 'var(--accent-success)', color: '#000' }}
            >
              {downloading ? 'PROCESSANDO...' : '📥 BAIXAR SELECIONADAS (COM AUTO-TRIM)'}
            </button>
          )}
        </div>

        {/* COMPORTAMENTO 1: MANUAL */}
        <div className="premium-card" style={{ padding: '1.5rem' }}>
          <h3 className="module-tag" style={{ marginBottom: '1.5rem' }}>DOWNLOAD MANUAL</h3>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
            Insira links do YouTube ou nomes de músicas (um por linha).
          </p>
          <textarea 
            value={manualLinks}
            onChange={(e) => setManualLinks(e.target.value)}
            placeholder="Ex: https://youtube.com/watch?v=...\nGilberto Gil - Aquele Abraço"
            style={{ 
              width: '100%', height: '250px', background: 'rgba(0,0,0,0.3)', 
              border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px',
              color: '#fff', padding: '1rem', fontFamily: 'monospace'
            }}
          />
          <button 
            className="action-btn" 
            onClick={() => triggerDownloads('manual')} 
            disabled={downloading}
            style={{ width: '100%', marginTop: '1.5rem', background: 'var(--accent-primary)', color: '#000' }}
          >
            {downloading ? 'BAIXANDO...' : '🚀 INICIAR CAPTURA MANUAL'}
          </button>
        </div>
      </div>

      {statusMsg && (
        <div style={{ 
          marginTop: '2rem', padding: '1rem', background: 'rgba(56, 189, 248, 0.1)', 
          borderRadius: '10px', border: '1px solid var(--accent-primary)', color: 'var(--accent-primary)',
          fontSize: '0.8rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '10px'
        }}>
          <span>ℹ️</span> {statusMsg}
        </div>
      )}
    </div>
  );
}
