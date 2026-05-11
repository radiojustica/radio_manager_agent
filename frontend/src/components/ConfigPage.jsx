import React, { useState, useEffect } from 'react';
import './ConfigPage.css';
import ScheduleEditor from './ScheduleEditor';

const ConfigPage = () => {
    const [activeSubTab, setActiveSubTab] = useState('badwords');
    const [badwords, setBadwords] = useState([]);
    const [newWord, setNewWord] = useState('');
    const [grade, setGrade] = useState({});
    const [quarantineLogs, setQuarantineLogs] = useState([]);
    const [quarantineFiles, setQuarantineFiles] = useState([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (activeSubTab === 'badwords') carregarBadwords();
        if (activeSubTab === 'grade') carregarGrade();
        if (activeSubTab === 'quarantine') carregarQuarentena();
    }, [activeSubTab]);

    const carregarBadwords = () => {
        fetch('/api/config/badwords').then(res => res.json()).then(setBadwords);
    };

    const carregarGrade = () => {
        fetch('/api/config/grade').then(res => res.json()).then(setGrade);
    };

    const carregarQuarentena = () => {
        fetch('/api/config/quarantine/logs').then(res => res.json()).then(setQuarantineLogs);
        fetch('/api/config/quarantine/files').then(res => res.json()).then(setQuarantineFiles);
    };

    const handleAddBadword = () => {
        if (!newWord) return;
        const updated = [...badwords, newWord];
        fetch('/api/config/badwords', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updated)
        }).then(() => {
            setBadwords(updated);
            setNewWord('');
        });
    };

    const handleRemoveBadword = (word) => {
        const updated = badwords.filter(w => w !== word);
        fetch('/api/config/badwords', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updated)
        }).then(() => setBadwords(updated));
    };

    const handleSaveGrade = () => {
        fetch('/api/config/grade', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(grade)
        }).then(() => alert('Configurações de Grade salvas com sucesso!'));
    };

    const handleRestoreFile = (file) => {
        fetch(`/api/config/quarantine/restore?filename=${encodeURIComponent(file)}`, { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    alert('Arquivo restaurado e marcado como seguro!');
                    carregarQuarentena();
                } else {
                    alert('Erro ao restaurar: ' + data.message);
                }
            });
    };

    return (
        <div className="config-page">
            <div className="config-tabs">
                <button className={activeSubTab === 'badwords' ? 'active' : ''} onClick={() => setActiveSubTab('badwords')}>🛡️ Segurança (Badwords)</button>
                <button className={activeSubTab === 'grade' ? 'active' : ''} onClick={() => setActiveSubTab('grade')}>📅 Regras de Grade</button>
                <button className={activeSubTab === 'schedule' ? 'active' : ''} onClick={() => setActiveSubTab('schedule')}>⚡ Energia (Horário)</button>
                <button className={activeSubTab === 'quarantine' ? 'active' : ''} onClick={() => setActiveSubTab('quarantine')}>☣️ Quarentena</button>
            </div>

            <div className="config-content glass-panel">
                {activeSubTab === 'schedule' && <ScheduleEditor />}
                {activeSubTab === 'badwords' && (
                    <div className="badwords-section">
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <div>
                                <h3>Filtro de Conteúdo Impróprio</h3>
                                <p>Termos e artistas bloqueados (Red Flag automática).</p>
                            </div>
                            <div className="status-pill warning">{badwords.length} Termos Ativos</div>
                        </div>
                        
                        <div className="add-word">
                            <input value={newWord} onChange={e => setNewWord(e.target.value)} placeholder="Adicionar nova palavra, artista ou termo..." />
                            <button onClick={handleAddBadword}>Adicionar à Lista</button>
                        </div>
                        
                        <div className="word-list">
                            {badwords.length === 0 ? <p style={{ color: 'var(--text-muted)' }}>Nenhuma palavra cadastrada.</p> : 
                            badwords.map(w => (
                                <span key={w} className="word-tag">{w} <button onClick={() => handleRemoveBadword(w)}>×</button></span>
                            ))}
                        </div>
                    </div>
                )}

                {activeSubTab === 'grade' && (
                    <div className="grade-section">
                        <h3>Hub de Inteligência Musical</h3>
                        <div className="grade-grid">
                            <div className="field">
                                <label>Músicas a cada Vinheta:</label>
                                <input type="number" value={grade.vinheta_a_cada_n || 1} onChange={e => setGrade({...grade, vinheta_a_cada_n: parseInt(e.target.value)})} />
                            </div>
                            <div className="field">
                                <label>Músicas a cada Comercial:</label>
                                <input type="number" value={grade.spot_a_cada_n || 4} onChange={e => setGrade({...grade, spot_a_cada_n: parseInt(e.target.value)})} />
                            </div>
                            <div className="field">
                                <label>Quota Regional (Regional a cada N):</label>
                                <input type="number" value={grade.regional_a_cada_n || 8} onChange={e => setGrade({...grade, regional_a_cada_n: parseInt(e.target.value)})} />
                            </div>
                            <div className="field">
                                <label>Mood Padrão (Vibe):</label>
                                <select value={grade.mood_padrao || 'Ensolarado'} onChange={e => setGrade({...grade, mood_padrao: e.target.value})}>
                                    <option value="Ensolarado">Ensolarado</option>
                                    <option value="Chuvoso">Chuvoso</option>
                                    <option value="Nublado">Nublado</option>
                                </select>
                            </div>
                            <div className="field">
                                <label>Duração Estimada Música (s):</label>
                                <input type="number" value={grade.duracao_estimada_musica_s || 210} onChange={e => setGrade({...grade, duracao_estimada_musica_s: parseInt(e.target.value)})} />
                            </div>
                            <div className="field">
                                <label>Histórico Anti-repetição (Qtd):</label>
                                <input type="number" value={grade.max_historico_musicas || 200} onChange={e => setGrade({...grade, max_historico_musicas: parseInt(e.target.value)})} />
                            </div>
                        </div>
                        <button className="btn-save" onClick={handleSaveGrade}>💾 Salvar Parâmetros da Inteligência</button>
                    </div>
                )}

                {activeSubTab === 'quarantine' && (
                    <div className="quarantine-section">
                        <div className="quarantine-split">
                            <div className="files-list">
                                <h3>Itens Sob Custódia</h3>
                                <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>Arquivos movidos por corrupção ou segurança.</p>
                                {quarantineFiles.length === 0 ? <p>Cofre vazio. Nenhum item em quarentena.</p> : (
                                    <div className="scroll-area" style={{ maxHeight: '400px', overflowY: 'auto' }}>
                                        {quarantineFiles.map(f => (
                                            <div key={f} className="quarantine-item">
                                                <span>{f}</span>
                                                <button onClick={() => handleRestoreFile(f)}>Restaurar ✅</button>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                            <div className="logs-area">
                                <h3>Audit Log</h3>
                                <div className="log-console">
                                    {quarantineLogs.length === 0 ? <div className="log-line">Aguardando eventos...</div> : 
                                    quarantineLogs.map((l, i) => <div key={i} className="log-line">{l}</div>)}
                                </div>
                                <button className="btn-secondary" style={{ marginTop: '10px' }} onClick={carregarQuarentena}>🔄 Atualizar Logs</button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default ConfigPage;
