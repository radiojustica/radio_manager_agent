import React, { useState, useEffect } from 'react';
import './AcervoPage.css';

const AcervoPage = () => {
    const [musicas, setMusicas] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filtros, setFiltros] = useState({
        search: '',
        estilo: '',
        energia_min: '',
        energia_max: '',
        auditado: '',
        redflag: ''
    });
    const [estilos, setEstilos] = useState([]);
    const [selectedIds, setSelectedIds] = useState(new Set());
    const [pagination, setPagination] = useState({ page: 1, limit: 100, total: 0, pages: 1 });
    const [editingId, setEditingId] = useState(null);
    const [editValues, setEditValues] = useState({ energia: 3, estilo: '', redflag: false });
    const [generatingAiId, setGeneratingAiId] = useState(null);

    // Carregar estilos para o filtro
    useEffect(() => {
        fetch('/api/acervo/estilos')
            .then(res => res.json())
            .then(setEstilos)
            .catch(console.error);
    }, []);

    // Carregar músicas com filtros
    const carregarAcervo = async (page = 1) => {
        setLoading(true);
        const params = new URLSearchParams({
            page: page.toString(),
            limit: pagination.limit.toString(),
            ...(filtros.search && { search: filtros.search }),
            ...(filtros.estilo && { estilo: filtros.estilo }),
            ...(filtros.energia_min && { energia_min: filtros.energia_min }),
            ...(filtros.energia_max && { energia_max: filtros.energia_max }),
            ...(filtros.auditado !== '' && { auditado: filtros.auditado }),
            ...(filtros.redflag !== '' && { redflag: filtros.redflag })
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

    useEffect(() => {
        carregarAcervo(1);
    }, [filtros]);

    const handleFiltroChange = (e) => {
        const { name, value } = e.target;
        setFiltros(prev => ({ ...prev, [name]: value }));
    };

    const handleSelectAll = (e) => {
        if (e.target.checked) {
            setSelectedIds(new Set(musicas.map(m => m.id)));
        } else {
            setSelectedIds(new Set());
        }
    };

    const handleSelectOne = (id) => {
        const newSet = new Set(selectedIds);
        if (newSet.has(id)) newSet.delete(id);
        else newSet.add(id);
        setSelectedIds(newSet);
    };

    const handleBatchAuditar = async () => {
        if (selectedIds.size === 0) return;
        const ids = Array.from(selectedIds);
        await fetch('/api/acervo/batch/auditar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(ids)
        });
        alert(`${ids.length} faixa(s) enviadas para reauditoria.`);
        carregarAcervo(pagination.page);
        setSelectedIds(new Set());
    };

    const handleExportar = (todos = false) => {
        let url = '/api/acervo/exportar';
        if (!todos && selectedIds.size > 0) {
            url += `?ids=${Array.from(selectedIds).join(',')}`;
        }
        window.open(url, '_blank');
    };

    const handleImportar = async (e) => {
        if (!e.target.files?.[0]) return;
        setLoading(true);
        const formData = new FormData();
        formData.append('file', e.target.files[0]);
        try {
            const res = await fetch('/api/acervo/importar', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            alert(`Importação concluída: ${data.atualizados} atualizados.`);
            carregarAcervo(pagination.page);
        } catch (err) {
            alert('Erro na importação.');
        } finally {
            setLoading(false);
        }
    };

    const startEditing = (musica) => {
        setEditingId(musica.id);
        setEditValues({
            energia: musica.energia,
            estilo: musica.estilo || '',
            redflag: musica.redflag || false
        });
    };

    const saveEditing = async (id) => {
        await fetch(`/api/acervo/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(editValues)
        });
        setEditingId(null);
        carregarAcervo(pagination.page);
    };

    const cancelEditing = () => {
        setEditingId(null);
    };

    const handleEnrichTrack = async (id) => {
        setGeneratingAiId(id);
        try {
            await fetch(`/api/ai/enrich-track/${id}`, { method: 'POST' });
            carregarAcervo(pagination.page);
        } catch (err) {
            alert('Erro ao gerar insight da IA.');
        } finally {
            setGeneratingAiId(null);
        }
    };

    const handleBatchEnrich = async () => {
        if (selectedIds.size === 0) return;
        setLoading(true);
        try {
            const ids = Array.from(selectedIds);
            // Processa um por um para não sobrecarregar o Ollama se necessário, 
            // mas o endpoint de batch já existe. Vamos usar o batch com limite do set.
            await fetch(`/api/ai/enrich-batch?limit=${ids.length}`, { method: 'POST' });
            alert(`Processamento de ${ids.length} faixas iniciado via Ollama.`);
            carregarAcervo(pagination.page);
        } catch (err) {
            alert('Erro no processamento em lote da IA.');
        } finally {
            setLoading(false);
            setSelectedIds(new Set());
        }
    };

    const renderEnergiaBar = (energia) => {
        const percent = (energia / 5) * 100;
        return (
            <div className="energia-mini-bar">
                <div className="energia-fill" style={{ width: `${percent}%` }} />
            </div>
        );
    };

    return (
        <div className="acervo-page">
            <div className="filtros-panel glass-panel">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                    <h3 style={{ margin: 0 }}>Filtros e Gestão de Acervo</h3>
                    <div style={{ display: 'flex', gap: '8px' }}>
                        <input
                            type="file"
                            id="csv-import-acervo"
                            accept=".csv"
                            style={{ display: 'none' }}
                            onChange={handleImportar}
                        />
                        <button className="btn-action" style={{ fontSize: '0.75rem', padding: '0.4rem 0.8rem' }} onClick={() => document.getElementById('csv-import-acervo').click()}>
                            📥 Importar CSV
                        </button>
                        <button className="btn-action" style={{ fontSize: '0.75rem', padding: '0.4rem 0.8rem' }} onClick={() => handleExportar(true)}>
                            📂 Exportar Todo CSV
                        </button>
                    </div>
                </div>
                <div className="filtros-grid">
                    <input
                        type="text"
                        name="search"
                        placeholder="Buscar título ou artista..."
                        value={filtros.search}
                        onChange={handleFiltroChange}
                    />
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
                </div>
                <div className="acoes-batch">
                    <button onClick={handleBatchAuditar} disabled={selectedIds.size === 0}>
                        🔄 Reprocessar Selecionadas ({selectedIds.size})
                    </button>
                    <button onClick={handleBatchEnrich} disabled={selectedIds.size === 0} style={{ background: 'var(--accent-primary)', color: 'white' }}>
                        🧠 Gerar IA p/ Selecionadas ({selectedIds.size})
                    </button>
                    <button onClick={() => handleExportar(false)} disabled={selectedIds.size === 0}>
                        📤 Exportar Seleção
                    </button>
                </div>
            </div>

            <div className="acervo-table-container glass-panel">
                {loading ? (
                    <div className="loading">Carregando acervo...</div>
                ) : (
                    <>
                        <table className="acervo-table">
                            <thead>
                                <tr>
                                    <th><input type="checkbox" onChange={handleSelectAll} checked={selectedIds.size === musicas.length && musicas.length > 0} /></th>
                                    <th>Título</th>
                                    <th>Artista</th>
                                    <th>Estilo</th>
                                    <th>Energia</th>
                                    <th>Status</th>
                                    <th>IA Insight (Ollama)</th>
                                    <th>Ações</th>
                                </tr>
                            </thead>
                            <tbody>
                                {musicas.map(m => (
                                    <tr key={m.id} className={m.redflag ? 'redflag-row' : ''}>
                                        <td><input type="checkbox" checked={selectedIds.has(m.id)} onChange={() => handleSelectOne(m.id)} /></td>
                                        <td>{editingId === m.id ? (
                                            <input type="text" value={editValues.titulo || m.titulo} disabled />
                                        ) : m.titulo}</td>
                                        <td>{editingId === m.id ? (
                                            <input type="text" value={editValues.artista || m.artista} disabled />
                                        ) : m.artista}</td>
                                        <td>{editingId === m.id ? (
                                            <select value={editValues.estilo} onChange={e => setEditValues({ ...editValues, estilo: e.target.value })}>
                                                <option value="">Selecione</option>
                                                {estilos.map(e => <option key={e} value={e}>{e}</option>)}
                                            </select>
                                        ) : m.estilo}</td>
                                        <td>
                                            {editingId === m.id ? (
                                                <input type="number" min="1" max="5" value={editValues.energia} onChange={e => setEditValues({ ...editValues, energia: parseInt(e.target.value) })} />
                                            ) : (
                                                <div className="energia-cell">
                                                    {renderEnergiaBar(m.energia)}
                                                    <span>{m.energia}</span>
                                                </div>
                                            )}
                                        </td>
                                        <td>
                                            {m.redflag ? '🚫 Bloqueada' : m.auditado_acustica ? '✅ Auditada' : '⏳ Pendente'}
                                        </td>
                                        <td className="ai-insight-cell">
                                            {generatingAiId === m.id ? (
                                                <span className="loading-spinner">🧠 Pensando...</span>
                                            ) : (
                                                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                                                    <span className="insight-text" title={m.ai_insight}>{m.ai_insight || '---'}</span>
                                                    <button 
                                                        className="btn-mini-ai" 
                                                        onClick={() => handleEnrichTrack(m.id)}
                                                        title="Gerar/Atualizar via Ollama"
                                                    >
                                                        🪄
                                                    </button>
                                                </div>
                                            )}
                                        </td>
                                        <td>
                                            {editingId === m.id ? (
                                                <>
                                                    <button onClick={() => saveEditing(m.id)}>💾</button>
                                                    <button onClick={cancelEditing}>❌</button>
                                                </>
                                            ) : (
                                                <button onClick={() => startEditing(m)}>✏️</button>
                                            )}
                                        </td>
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
        </div>
    );
};

export default AcervoPage;
