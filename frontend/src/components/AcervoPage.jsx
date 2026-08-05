import React, { useState, useEffect, useCallback } from 'react';
import './AcervoPage.css';

const TEMA_OPCOES = [
  { v: 'verao_reis', l: 'Jan: Verão/Reis' },
  { v: 'carnaval', l: 'Fev: Carnaval' },
  { v: 'mulheres', l: 'Mar: Mulheres' },
  { v: 'choro_instrumental', l: 'Abr: Choro/Instrumental' },
  { v: 'cultura_popular', l: 'Mai: Cultura Popular' },
  { v: 'junho', l: 'Jun: São João' },
  { v: 'jazz_bossa', l: 'Jul: Jazz/Bossa' },
  { v: 'cultura_potiguar', l: 'Ago: Cultura Potiguar' },
  { v: 'nova_cena', l: 'Set: Nova Cena' },
  { v: 'nordestino', l: 'Out: Dia do Nordestino' },
  { v: 'consciencia_negra', l: 'Nov: Consciência Negra' },
  { v: 'natal', l: 'Dez: Natal' },
];

const AcervoPage = () => {
  const [musicas, setMusicas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filtros, setFiltros] = useState({
    search: '', estilo: '', energia_min: '', energia_max: '',
    bpm_min: '', bpm_max: '', auditado: '', redflag: '', tema_especial: '',
  });
  const [sortBy, setSortBy] = useState('');
  const [order, setOrder] = useState('asc');
  const [estilos, setEstilos] = useState([]);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [pagination, setPagination] = useState({ page: 1, limit: 100, total: 0, pages: 1 });
  const [editingId, setEditingId] = useState(null);
  const [editValues, setEditValues] = useState({ energia: 3, estilo: '', redflag: false, tema_especial: '' });
  const [generatingAiId, setGeneratingAiId] = useState(null);
  // Estatísticas e distribuição (dados reais)
  const [stats, setStats] = useState({ total: 0, auditadas: 0, redflags: 0, estilos: [], energia_dist: {} });
  const [toast, setToast] = useState('');

  const showToast = (m) => { setToast(m); setTimeout(() => setToast(''), 3500); };

  const carregarStats = useCallback(async () => {
    try {
      const res = await fetch('/api/acervo/distribuicao');
      if (res.ok) setStats(await res.json());
    } catch (e) { console.error(e); }
  }, []);

  useEffect(() => { fetch('/api/acervo/estilos').then(r => r.json()).then(setEstilos).catch(console.error); }, []);
  useEffect(() => { carregarStats(); }, [carregarStats]);

  const carregarAcervo = async (page = 1) => {
    setLoading(true);
    const params = new URLSearchParams({
      page: page.toString(),
      limit: pagination.limit.toString(),
      ...(sortBy && { sort_by: sortBy, order }),
      ...(filtros.search && { search: filtros.search }),
      ...(filtros.estilo && { estilo: filtros.estilo }),
      ...(filtros.energia_min && { energia_min: filtros.energia_min }),
      ...(filtros.energia_max && { energia_max: filtros.energia_max }),
      ...(filtros.bpm_min && { bpm_min: filtros.bpm_min }),
      ...(filtros.bpm_max && { bpm_max: filtros.bpm_max }),
      ...(filtros.auditado !== '' && { auditado: filtros.auditado }),
      ...(filtros.redflag !== '' && { redflag: filtros.redflag }),
      ...(filtros.tema_especial && { tema_especial: filtros.tema_especial }),
    });
    try {
      const res = await fetch(`/api/acervo?${params}`);
      const data = await res.json();
      setMusicas(data.items);
      setPagination(prev => ({ ...prev, ...data }));
    } catch (err) {
      console.error('Erro ao carregar acervo:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { carregarAcervo(1); }, [filtros, sortBy, order]);

  const handleFiltroChange = (e) => {
    const { name, value } = e.target;
    setFiltros(prev => ({ ...prev, [name]: value }));
  };

  const toggleSort = (col) => {
    if (sortBy === col) { setOrder(o => o === 'asc' ? 'desc' : 'asc'); }
    else { setSortBy(col); setOrder('asc'); }
  };

  const handleSelectAll = (e) => {
    if (e.target.checked) setSelectedIds(new Set(musicas.map(m => m.id)));
    else setSelectedIds(new Set());
  };
  const handleSelectOne = (id) => {
    const s = new Set(selectedIds);
    s.has(id) ? s.delete(id) : s.add(id);
    setSelectedIds(s);
  };

  const handleBatchAuditar = async () => {
    if (selectedIds.size === 0) return;
    const ids = Array.from(selectedIds);
    await fetch('/api/acervo/batch/auditar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(ids) });
    showToast(`${ids.length} faixa(s) enviada(s) para reauditoria.`);
    carregarAcervo(pagination.page); setSelectedIds(new Set());
  };

  const handleBatchRedflag = async (block) => {
    if (selectedIds.size === 0) return;
    const ids = Array.from(selectedIds);
    const res = await fetch('/api/acervo/batch/redflag', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ids, redflag: block }) });
    const d = await res.json();
    showToast(`${d.processados} faixa(s) ${block ? 'BLOQUEADA(S)' : 'LIBERADA(S)'}.`);
    carregarAcervo(pagination.page); carregarStats(); setSelectedIds(new Set());
  };

  const handleExportar = (todos = false) => {
    let url = '/api/acervo/exportar';
    if (!todos && selectedIds.size > 0) url += `?ids=${Array.from(selectedIds).join(',')}`;
    window.open(url, '_blank');
  };

  const handleImportar = async (e) => {
    if (!e.target.files?.[0]) return;
    setLoading(true);
    const formData = new FormData();
    formData.append('file', e.target.files[0]);
    try {
      const res = await fetch('/api/acervo/importar', { method: 'POST', body: formData });
      const data = await res.json();
      showToast(`Importação concluída: ${data.atualizados} atualizados.`);
      carregarAcervo(pagination.page); carregarStats();
    } catch (err) { showToast('Erro na importação.'); }
    finally { setLoading(false); }
  };

  const startEditing = (m) => {
    setEditingId(m.id);
    setEditValues({ energia: m.energia, estilo: m.estilo || '', redflag: m.redflag || false, tema_especial: m.tema_especial || '' });
  };
  const saveEditing = async (id) => {
    await fetch(`/api/acervo/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(editValues) });
    setEditingId(null); carregarAcervo(pagination.page); carregarStats();
  };
  const cancelEditing = () => setEditingId(null);

  const handleEnrichTrack = async (id) => {
    setGeneratingAiId(id);
    try { await fetch(`/api/ai/enrich-track/${id}`, { method: 'POST' }); carregarAcervo(pagination.page); }
    catch { showToast('Erro ao gerar insight da IA.'); }
    finally { setGeneratingAiId(null); }
  };
  const handleBatchEnrich = async () => {
    if (selectedIds.size === 0) return;
    setLoading(true);
    try {
      const idsList = Array.from(selectedIds);
      await fetch('/api/ai/enrich-batch', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ids: idsList, limit: idsList.length }) });
      showToast(`Processamento de ${idsList.length} faixas iniciado.`);
      carregarAcervo(pagination.page);
    } finally { setLoading(false); setSelectedIds(new Set()); }
  };

  const renderEnergiaBar = (energia) => {
    const pct = (energia / 5) * 100;
    return (<div className="energia-mini-bar"><div className="energia-fill" style={{ width: `${pct}%` }} /></div>);
  };

  const sortArrow = (col) => sortBy === col ? (order === 'asc' ? ' ▲' : ' ▼') : '';
  const maxEstilo = Math.max(1, ...stats.estilos.map(e => e.qtd));
  const maxEnergia = Math.max(1, ...Object.values(stats.energia_dist).map(Number));
  const auditPct = stats.total ? Math.round((stats.auditadas / stats.total) * 100) : 0;

  return (
    <div className="acervo-page">
      {/* ===== HEADER DE ESTATÍSTICAS (REAIS) ===== */}
      <div className="acervo-stats-row">
        <div className="stat-tile"><div className="stat-num">{stats.total.toLocaleString('pt-BR')}</div><div className="stat-label">Faixas no Acervo</div></div>
        <div className="stat-tile"><div className="stat-num" style={{ color: 'var(--accent-success)' }}>{auditPct}%</div><div className="stat-label">Auditadas ({stats.auditadas})</div></div>
        <div className="stat-tile"><div className="stat-num" style={{ color: 'var(--accent-danger)' }}>{stats.redflags}</div><div className="stat-label">Bloqueadas (RedFlag)</div></div>
        <div className="stat-tile"><div className="stat-num">{stats.estilos.length}</div><div className="stat-label">Estilos Distintos</div></div>
      </div>

      {/* ===== GRÁFICOS DE DISTRIBUIÇÃO (REAIS) ===== */}
      <div className="acervo-charts">
        <div className="chart-card glass-panel">
          <h4>Distribuição por Estilo</h4>
          <div className="chart-bars">
            {stats.estilos.slice(0, 12).map(e => (
              <div key={e.nome} className="chart-bar-row">
                <span className="chart-bar-label">{e.nome}</span>
                <div className="chart-bar-track">
                  <div className="chart-bar-fill" style={{ width: `${(e.qtd / maxEstilo) * 100}%` }} />
                </div>
                <span className="chart-bar-val">{e.qtd.toLocaleString('pt-BR')}</span>
              </div>
            ))}
            {stats.estilos.length === 0 && <div className="chart-empty">Carregando...</div>}
          </div>
        </div>
        <div className="chart-card glass-panel">
          <h4>Distribuição por Energia (1–5)</h4>
          <div className="energia-dist">
            {[1, 2, 3, 4, 5].map(n => {
              const qtd = Number(stats.energia_dist[n] || 0);
              return (
                <div key={n} className="energia-dist-col">
                  <div className="energia-dist-bar-wrap">
                    <div className="energia-dist-bar" style={{ height: `${(qtd / maxEnergia) * 100}%` }} />
                  </div>
                  <div className="energia-dist-val">{qtd.toLocaleString('pt-BR')}</div>
                  <div className="energia-dist-label">E{n}</div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* ===== FILTROS ===== */}
      <div className="filtros-panel glass-panel">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h3 style={{ margin: 0 }}>Filtros e Gestão de Acervo</h3>
          <div style={{ display: 'flex', gap: '8px' }}>
            <input type="file" id="csv-import-acervo" accept=".csv" style={{ display: 'none' }} onChange={handleImportar} />
            <button className="btn-action" style={{ fontSize: '0.75rem', padding: '0.4rem 0.8rem' }} onClick={() => document.getElementById('csv-import-acervo').click()}>📥 Importar CSV</button>
            <button className="btn-action" style={{ fontSize: '0.75rem', padding: '0.4rem 0.8rem' }} onClick={() => handleExportar(true)}>📂 Exportar Todo CSV</button>
          </div>
        </div>
        <div className="filtros-grid">
          <input type="text" name="search" placeholder="Buscar título ou artista..." value={filtros.search} onChange={handleFiltroChange} />
          <select name="estilo" value={filtros.estilo} onChange={handleFiltroChange}>
            <option value="">Todos os estilos</option>
            {estilos.map(e => <option key={e} value={e}>{e}</option>)}
          </select>
          <select name="energia_min" value={filtros.energia_min} onChange={handleFiltroChange}>
            <option value="">Energia mín.</option>
            {[1, 2, 3, 4, 5].map(n => <option key={n} value={n}>{n}</option>)}
          </select>
          <select name="energia_max" value={filtros.energia_max} onChange={handleFiltroChange}>
            <option value="">Energia máx.</option>
            {[1, 2, 3, 4, 5].map(n => <option key={n} value={n}>{n}</option>)}
          </select>
          <input type="number" name="bpm_min" placeholder="BPM mín." value={filtros.bpm_min} onChange={handleFiltroChange} style={{ width: '90px' }} />
          <input type="number" name="bpm_max" placeholder="BPM máx." value={filtros.bpm_max} onChange={handleFiltroChange} style={{ width: '90px' }} />
          <select name="auditado" value={filtros.auditado} onChange={handleFiltroChange}>
            <option value="">Auditoria</option>
            <option value="true">Auditadas</option>
            <option value="false">Pendentes</option>
          </select>
          <select name="redflag" value={filtros.redflag} onChange={handleFiltroChange}>
            <option value="">Status</option>
            <option value="true">Bloqueadas</option>
            <option value="false">Liberadas</option>
          </select>
          <select name="tema_especial" value={filtros.tema_especial} onChange={handleFiltroChange}>
            <option value="">Tema especial</option>
            <option value="nenhum">Nenhum</option>
            {TEMA_OPCOES.map(t => <option key={t.v} value={t.v}>{t.l}</option>)}
          </select>
        </div>
        <div className="acoes-batch">
          <button onClick={handleBatchAuditar} disabled={selectedIds.size === 0}>🔄 Reprocessar ({selectedIds.size})</button>
          <button onClick={() => handleBatchRedflag(true)} disabled={selectedIds.size === 0} style={{ background: 'var(--accent-danger)', color: 'white' }}>🚫 Bloquear ({selectedIds.size})</button>
          <button onClick={() => handleBatchRedflag(false)} disabled={selectedIds.size === 0} style={{ background: 'var(--accent-success)', color: 'black' }}>✅ Liberar ({selectedIds.size})</button>
          <button onClick={handleBatchEnrich} disabled={selectedIds.size === 0} style={{ background: 'var(--accent-primary)', color: 'white' }}>🧠 Gerar IA ({selectedIds.size})</button>
          <button onClick={() => handleExportar(false)} disabled={selectedIds.size === 0}>📤 Exportar Seleção</button>
        </div>
      </div>

      {/* ===== TABELA ===== */}
      <div className="acervo-table-container glass-panel">
        {loading ? (<div className="loading">Carregando acervo...</div>) : (
          <>
            <table className="acervo-table">
              <thead>
                <tr>
                  <th><input type="checkbox" onChange={handleSelectAll} checked={selectedIds.size === musicas.length && musicas.length > 0} /></th>
                  <th onClick={() => toggleSort('titulo')} className="sortable">Título{sortArrow('titulo')}</th>
                  <th onClick={() => toggleSort('artista')} className="sortable">Artista{sortArrow('artista')}</th>
                  <th onClick={() => toggleSort('estilo')} className="sortable">Estilo{sortArrow('estilo')}</th>
                  <th>Tema Especial</th>
                  <th onClick={() => toggleSort('energia')} className="sortable">Energia{sortArrow('energia')}</th>
                  <th>BPM</th>
                  <th>Status</th>
                  <th>IA Insight</th>
                  <th>Ações</th>
                </tr>
              </thead>
              <tbody>
                {musicas.map(m => (
                  <tr key={m.id} className={m.redflag ? 'redflag-row' : ''}>
                    <td><input type="checkbox" checked={selectedIds.has(m.id)} onChange={() => handleSelectOne(m.id)} /></td>
                    <td>{editingId === m.id ? <input type="text" value={editValues.titulo || m.titulo} disabled /> : m.titulo}</td>
                    <td>{editingId === m.id ? <input type="text" value={editValues.artista || m.artista} disabled /> : m.artista}</td>
                    <td>{editingId === m.id ? (
                      <select value={editValues.estilo} onChange={e => setEditValues({ ...editValues, estilo: e.target.value })}>
                        <option value="">Selecione</option>
                        {estilos.map(e => <option key={e} value={e}>{e}</option>)}
                      </select>
                    ) : m.estilo}</td>
                    <td>{editingId === m.id ? (
                      <select value={editValues.tema_especial} onChange={e => setEditValues({ ...editValues, tema_especial: e.target.value })}>
                        <option value="">Nenhum</option>
                        {TEMA_OPCOES.map(t => <option key={t.v} value={t.v}>{t.l}</option>)}
                      </select>
                    ) : (m.tema_especial || '---')}</td>
                    <td>{editingId === m.id ? (
                      <input type="number" min="1" max="5" value={editValues.energia} onChange={e => setEditValues({ ...editValues, energia: parseInt(e.target.value) })} />
                    ) : (<div className="energia-cell">{renderEnergiaBar(m.energia)}<span>{m.energia}</span></div>)}</td>
                    <td>{m.bpm ?? '—'}</td>
                    <td>{m.redflag ? '🚫 Bloqueada' : m.auditado_acustica ? '✅ Auditada' : '⏳ Pendente'}</td>
                    <td className="ai-insight-cell">
                      {generatingAiId === m.id ? (<span className="loading-spinner">🧠 Pensando...</span>) : (
                        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                          <span className="insight-text" title={m.ai_insight}>{m.ai_insight || '---'}</span>
                          <button className="btn-mini-ai" onClick={() => handleEnrichTrack(m.id)} title="Gerar/Atualizar">🪄</button>
                        </div>
                      )}
                    </td>
                    <td>{editingId === m.id ? (<><button onClick={() => saveEditing(m.id)}>💾</button><button onClick={cancelEditing}>❌</button></>) : (<button onClick={() => startEditing(m)}>✏️</button>)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="pagination">
              <button disabled={pagination.page <= 1} onClick={() => carregarAcervo(pagination.page - 1)}>Anterior</button>
              <span>Página {pagination.page} de {pagination.pages} (Total: {pagination.total})</span>
              <button disabled={pagination.page >= pagination.pages} onClick={() => carregarAcervo(pagination.page + 1)}>Próxima</button>
            </div>
          </>
        )}
      </div>

      {toast && <div className="acervo-toast">{toast}</div>}
    </div>
  );
};

export default AcervoPage;
