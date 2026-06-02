import { useState, useEffect } from 'react';
import './ConfigPage.css'; // Usando estilos baseados nas páginas de config

const DIAS_UTEIS = ['segunda', 'terca', 'quarta', 'quinta', 'sexta'];
const FIM_SEMANA = ['sabado', 'domingo'];
const TODOS_DIAS = [...DIAS_UTEIS, ...FIM_SEMANA];

const DIAS_LABELS = {
  segunda: 'Segunda-feira',
  terca: 'Terça-feira',
  quarta: 'Quarta-feira',
  quinta: 'Quinta-feira',
  sexta: 'Sexta-feira',
  sabado: 'Sábado',
  domingo: 'Domingo',
};

const ITEMS_LABELS = {
  SPOT: { label: 'SPOT (Vinheta Curta)', color: '#f59e0b', desc: 'Vinheta curta de transição' },
  VH_INSTITUCIONAL: { label: 'Vinheta Institucional', color: '#8b5cf6', desc: 'Identificação oficial da rádio' },
  BOLETIM: { label: 'Boletim Noticioso', color: '#38bdf8', desc: 'Notícias do dia (ou randômico no FDS)' },
  MUSICA: { label: 'Música (Grade)', color: '#10b981', desc: 'Músicas e programação musical normal' },
  GIRO_NAS_COMARCAS: { label: 'Giro nas Comarcas', color: '#ec4899', desc: 'Programa fixo (10 min)' },
  MEMORIA_DA_JUSTICA: { label: 'Memória da Justiça', color: '#f97316', desc: 'Programa fixo (40 min)' },
  LEVEMENTE: { label: 'Levemente', color: '#14b8a6', desc: 'Programa fixo (40 min)' },
  NOTICIAS_DO_JUDICIARIO: { label: 'Notícias do Judiciário', color: '#6366f1', desc: 'Programa de notícias (5 min)' },
};

export default function SchedulePage() {
  const [schedule, setSchedule] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState('segunda');
  
  // Estado para Edição de Horário (Modal)
  const [editingDay, setEditingDay] = useState(null);
  const [editingTimeKey, setEditingTimeKey] = useState(null); // 'new' para novo horário
  const [editTimeStr, setEditTimeStr] = useState('10:00');
  const [editItems, setEditItems] = useState([]);
  
  // Estado para Duplicação
  const [dupTargetDays, setDupTargetDays] = useState([]);

  const fetchSchedule = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/schedule/weekly');
      if (res.ok) {
        const data = await res.ok ? await res.json() : null;
        if (data) setSchedule(data);
      }
    } catch (e) {
      console.error('Erro ao buscar grade:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSchedule();
  }, []);

  const handleSave = async () => {
    if (!schedule) return;
    setSaving(true);
    try {
      const res = await fetch('/api/schedule/weekly', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(schedule),
      });
      if (res.ok) {
        alert('✅ Grade semanal salva e ativa no SQLite com sucesso!');
        fetchSchedule();
      } else {
        alert('Erro ao salvar no servidor.');
      }
    } catch (e) {
      alert('Falha na comunicação com o servidor.');
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    if (!window.confirm('Tem certeza que deseja restaurar a grade padrão de fábrica? Todas as customizações locais serão perdidas.')) {
      return;
    }
    setLoading(true);
    try {
      const res = await fetch('/api/schedule/weekly/reset', { method: 'POST' });
      if (res.ok) {
        alert('✅ Grade padrão restaurada com sucesso!');
        fetchSchedule();
      }
    } catch (e) {
      alert('Erro ao restaurar a grade.');
    } finally {
      setLoading(false);
    }
  };

  // Abrir editor para um horário existente
  const openEdit = (day, timeKey) => {
    setEditingDay(day);
    setEditingTimeKey(timeKey);
    setEditTimeStr(timeKey);
    setEditItems(schedule.excecoes_diurnas[day][timeKey] || []);
    setDupTargetDays([]);
  };

  // Abrir editor para novo horário
  const openNew = (day) => {
    setEditingDay(day);
    setEditingTimeKey('new');
    setEditTimeStr('10:00');
    setEditItems(['SPOT', 'BOLETIM', 'SPOT', 'MUSICA']);
    setDupTargetDays([]);
  };

  // Fechar editor
  const closeEdit = () => {
    setEditingDay(null);
    setEditingTimeKey(null);
  };

  // Salvar alterações locais do horário editado
  const saveLocalEdit = () => {
    if (!editTimeStr.match(/^\d{2}:\d{2}$/)) {
      alert('Formato de hora inválido! Use HH:MM (ex: 09:30)');
      return;
    }
    
    const updated = { ...schedule };
    
    // Se for dia útil (excecoes_diurnas)
    if (DIAS_UTEIS.includes(editingDay)) {
      // Se era um horário existente e mudou a hora, remove o antigo
      if (editingTimeKey !== 'new' && editingTimeKey !== editTimeStr) {
        delete updated.excecoes_diurnas[editingDay][editingTimeKey];
      }
      
      // Salva no dia selecionado
      updated.excecoes_diurnas[editingDay][editTimeStr] = editItems;
      
      // Duplicar para outros dias se selecionado
      dupTargetDays.forEach(targetDay => {
        if (!updated.excecoes_diurnas[targetDay]) {
          updated.excecoes_diurnas[targetDay] = {};
        }
        updated.excecoes_diurnas[targetDay][editTimeStr] = [...editItems];
      });
    }
    
    setSchedule(updated);
    closeEdit();
  };

  // Remover horário localmente
  const deleteLocalTime = (day, timeKey) => {
    if (!window.confirm(`Deseja remover o horário das ${timeKey} de ${DIAS_LABELS[day]}?`)) {
      return;
    }
    const updated = { ...schedule };
    if (DIAS_UTEIS.includes(day)) {
      delete updated.excecoes_diurnas[day][timeKey];
    }
    setSchedule(updated);
    closeEdit();
  };

  const addItemToEdit = (item) => {
    setEditItems([...editItems, item]);
  };

  const removeItemFromEdit = (index) => {
    setEditItems(editItems.filter((_, i) => i !== index));
  };

  const moveItemInEdit = (index, direction) => {
    const newItems = [...editItems];
    const targetIdx = index + direction;
    if (targetIdx >= 0 && targetIdx < newItems.length) {
      const temp = newItems[index];
      newItems[index] = newItems[targetIdx];
      newItems[targetIdx] = temp;
      setEditItems(newItems);
    }
  };

  const toggleDupDay = (day) => {
    if (dupTargetDays.includes(day)) {
      setDupTargetDays(dupTargetDays.filter(d => d !== day));
    } else {
      setDupTargetDays([...dupTargetDays, day]);
    }
  };

  if (loading) {
    return (
      <div className="config-page text-center" style={{ padding: '4rem' }}>
        <h2 style={{ color: 'var(--accent-primary)', fontSize: '1.5rem', fontWeight: 800 }}>
          Carregando grade semanal de programação...
        </h2>
      </div>
    );
  }

  const excecoesDia = (schedule?.excecoes_diurnas && schedule.excecoes_diurnas[activeTab]) || {};
  const isWeekend = FIM_SEMANA.includes(activeTab);

  // Ordena os horários do dia
  const sortedTimes = Object.keys(excecoesDia).sort();

  return (
    <div className="config-page fade-in">
      <div className="glass-panel" style={{ padding: '2rem', marginBottom: '2rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1.5rem' }}>
          <div>
            <h2 style={{ fontSize: '1.4rem', fontWeight: 900, letterSpacing: '0.5px', color: '#fff' }}>
              GERENCIADOR DE GRADE SEMANAL (OMNI-SCHEDULER)
            </h2>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
              Defina programas, vinhetas, spots e loops de boletins diretamente no banco de dados do Omni Core.
            </p>
          </div>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button 
              onClick={handleReset} 
              className="btn btn-secondary" 
              style={{ padding: '0.6rem 1.2rem', fontSize: '0.75rem' }}
            >
              🔄 Restaurar Padrão
            </button>
            <button 
              onClick={handleSave} 
              disabled={saving} 
              className="btn btn-action" 
              style={{ background: 'var(--accent-success)', padding: '0.6rem 1.2rem', fontSize: '0.75rem' }}
            >
              {saving ? '📥 SALVANDO...' : '📥 SALVAR E APLICAR GRADE'}
            </button>
          </div>
        </div>
      </div>

      {/* Tabs dos Dias da Semana */}
      <div className="config-tabs" style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', marginBottom: '1.5rem' }}>
        {TODOS_DIAS.map(day => (
          <button
            key={day}
            onClick={() => setActiveTab(day)}
            className={activeTab === day ? 'active' : ''}
            style={{
              flex: '1 1 120px',
              border: '1px solid rgba(255,255,255,0.08)',
              background: activeTab === day ? 'var(--accent-primary)' : 'rgba(255,255,255,0.02)',
              color: activeTab === day ? '#000' : 'var(--text-secondary)',
              fontWeight: 700,
              padding: '0.8rem 1rem',
              borderRadius: '8px',
              textAlign: 'center',
              textTransform: 'uppercase',
              fontSize: '0.75rem',
            }}
          >
            {DIAS_LABELS[day]}
          </button>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: isWeekend ? '1fr' : '3fr 1.2fr', gap: '2rem' }}>
        {/* Painel Central da Grade */}
        <div className="glass-panel" style={{ padding: '2rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 800, color: 'var(--accent-primary)' }}>
              GRADE HORÁRIA: {DIAS_LABELS[activeTab].toUpperCase()}
            </h3>
            {!isWeekend && (
              <button 
                onClick={() => openNew(activeTab)} 
                className="btn btn-action btn-sm"
                style={{ fontSize: '0.7rem', padding: '0.4rem 0.8rem' }}
              >
                ➕ Novo Horário Especial
              </button>
            )}
          </div>

          {isWeekend ? (
            <div style={{ padding: '2rem', textAlign: 'center', background: 'rgba(255,255,255,0.01)', borderRadius: '12px', border: '1px dashed rgba(255,255,255,0.08)' }}>
              <div style={{ fontSize: '2rem', marginBottom: '10px' }}>🏖️</div>
              <h4 style={{ fontWeight: 800, color: '#fff', fontSize: '1rem' }}>Fim de Semana (Sábado e Domingo)</h4>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', maxWidth: '500px', margin: '10px auto' }}>
                Conforme a nova regra simplificada do piloto automático, no sábado e domingo o sistema roda no modo 
                <strong> Loop Contínuo a cada 30 minutos</strong>, contendo:
              </p>
              <div style={{ display: 'flex', justifyContent: 'center', gap: '8px', marginTop: '1rem' }}>
                <span className="badge" style={{ background: '#f59e0b', color: '#000', padding: '0.4rem 0.8rem', borderRadius: '4px', fontWeight: 700 }}>SPOT</span>
                <span className="badge" style={{ background: '#38bdf8', color: '#000', padding: '0.4rem 0.8rem', borderRadius: '4px', fontWeight: 700 }}>BOLETIM RANDOM</span>
                <span className="badge" style={{ background: '#f59e0b', color: '#000', padding: '0.4rem 0.8rem', borderRadius: '4px', fontWeight: 700 }}>SPOT</span>
                <span className="badge" style={{ background: '#10b981', color: '#000', padding: '0.4rem 0.8rem', borderRadius: '4px', fontWeight: 700 }}>MÚSICAS</span>
              </div>
              <p style={{ fontSize: '0.72rem', color: 'var(--accent-primary)', marginTop: '1.5rem', fontWeight: 600 }}>
                💡 Os boletins são selecionados de forma randômica de todos os dias úteis (Segunda a Sexta).
              </p>
            </div>
          ) : (
            <div>
              {sortedTimes.length === 0 ? (
                <div style={{ padding: '3rem', textAlign: 'center', background: 'rgba(0,0,0,0.1)', borderRadius: '10px' }}>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Nenhum horário especial configurado para este dia.</p>
                  <button onClick={() => openNew(activeTab)} className="btn btn-action" style={{ marginTop: '1rem' }}>
                    Criar Primeiro Horário
                  </button>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {sortedTimes.map(timeKey => {
                    const items = excecoesDia[timeKey] || [];
                    return (
                      <div 
                        key={timeKey}
                        className="rule-row"
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          background: 'rgba(255,255,255,0.02)',
                          padding: '1rem 1.5rem',
                          borderRadius: '10px',
                          border: '1px solid rgba(255,255,255,0.04)',
                          transition: 'all 0.2s',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
                          <span style={{ fontSize: '1.1rem', fontWeight: 900, color: 'var(--accent-primary)', width: '60px' }}>
                            {timeKey}
                          </span>
                          
                          {/* Sequência de blocos */}
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', alignItems: 'center' }}>
                            {items.map((item, idx) => {
                              const meta = ITEMS_LABELS[item] || { label: item, color: '#444' };
                              return (
                                <span 
                                  key={idx}
                                  className="badge"
                                  style={{
                                    background: `${meta.color}22`,
                                    border: `1px solid ${meta.color}`,
                                    color: meta.color,
                                    fontSize: '0.65rem',
                                    fontWeight: 800,
                                    padding: '0.35rem 0.7rem',
                                    borderRadius: '5px',
                                    textTransform: 'uppercase',
                                  }}
                                  title={meta.desc}
                                >
                                  {item.replace(/_/g, ' ')}
                                </span>
                              );
                            })}
                          </div>
                        </div>

                        {/* Botões de Ação */}
                        <div style={{ display: 'flex', gap: '8px' }}>
                          <button 
                            onClick={() => openEdit(activeTab, timeKey)}
                            className="btn btn-secondary btn-sm"
                            style={{ fontSize: '0.65rem', padding: '0.4rem 0.8rem', border: '1px solid rgba(255,255,255,0.1)' }}
                          >
                            ✏️ Editar
                          </button>
                          <button 
                            onClick={() => deleteLocalTime(activeTab, timeKey)}
                            className="btn btn-secondary btn-sm"
                            style={{ fontSize: '0.65rem', padding: '0.4rem 0.8rem', color: 'var(--accent-danger)', borderColor: 'rgba(239, 68, 68, 0.2)' }}
                          >
                            🗑️ Deletar
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Barra Lateral Informativa e Legenda */}
        {!isWeekend && (
          <div className="glass-panel" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            <h4 style={{ fontSize: '0.85rem', fontWeight: 800, color: 'var(--text-secondary)', letterSpacing: '1px' }}>
              LEGENDA DE ELEMENTOS
            </h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {Object.entries(ITEMS_LABELS).map(([key, meta]) => (
                <div key={key} style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
                  <div 
                    style={{
                      width: '12px',
                      height: '12px',
                      borderRadius: '3px',
                      background: meta.color,
                      marginTop: '3px',
                      boxShadow: `0 0 6px ${meta.color}aa`
                    }}
                  />
                  <div>
                    <div style={{ fontSize: '0.78rem', fontWeight: 700, color: '#fff' }}>{meta.label}</div>
                    <div style={{ fontSize: '0.68rem', color: 'var(--text-secondary)' }}>{meta.desc}</div>
                  </div>
                </div>
              ))}
            </div>
            
            <div style={{ background: 'rgba(56, 189, 248, 0.04)', border: '1px solid rgba(56, 189, 248, 0.15)', borderRadius: '8px', padding: '1rem', marginTop: 'auto' }}>
              <h5 style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--accent-primary)', marginBottom: '5px' }}>ℹ️ REGRAS DE GERAÇÃO</h5>
              <p style={{ fontSize: '0.68rem', color: 'var(--text-secondary)', lineHeight: '1.4' }}>
                Os horários cadastrados definem exceções. Fora do intervalo comercial (09h00 às 18h00), o Omni Core insere loops automáticos de boletins e spots a cada 30 minutos na programação.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* MODAL DE EDIÇÃO DE HORÁRIO */}
      {editingDay && (
        <div 
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            width: '100vw',
            height: '100vh',
            background: 'rgba(3, 7, 18, 0.85)',
            backdropFilter: 'blur(8px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            animation: 'fadeIn 0.2s ease-out',
          }}
        >
          <div 
            className="glass-panel" 
            style={{
              width: '90%',
              maxWidth: '550px',
              padding: '2rem',
              border: '1px solid var(--border-glass)',
              background: 'var(--bg-surface)',
              boxShadow: 'var(--shadow-lg), 0 0 50px rgba(56, 189, 248, 0.15)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: '1rem' }}>
              <h4 style={{ fontWeight: 900, color: '#fff', fontSize: '1.1rem' }}>
                {editingTimeKey === 'new' ? 'CRIAR HORÁRIO ESPECIAL' : `EDITAR HORÁRIO: ${editingTimeKey}`}
              </h4>
              <button 
                onClick={closeEdit} 
                style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', fontSize: '1.2rem', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            {/* Campo Hora */}
            <div className="field" style={{ marginBottom: '1.5rem' }}>
              <label style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
                Horário de Início (Formato HH:MM)
              </label>
              <input 
                type="text" 
                value={editTimeStr}
                onChange={(e) => setEditTimeStr(e.target.value)}
                placeholder="Ex: 10:45"
                style={{
                  padding: '0.8rem',
                  fontSize: '1rem',
                  background: 'rgba(0,0,0,0.3)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: '8px',
                  color: '#fff',
                  width: '120px',
                  textAlign: 'center',
                  fontWeight: 'bold',
                }}
              />
            </div>

            {/* Itens na sequência */}
            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 800, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '8px' }}>
                Sequência de Execução (Ordem Linear)
              </label>
              
              <div 
                style={{
                  background: 'rgba(0,0,0,0.2)',
                  border: '1px solid rgba(255,255,255,0.05)',
                  borderRadius: '10px',
                  padding: '1rem',
                  minHeight: '80px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px',
                }}
              >
                {editItems.length === 0 ? (
                  <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.75rem', padding: '1rem' }}>
                    Adicione elementos à sequência abaixo...
                  </div>
                ) : (
                  editItems.map((item, idx) => {
                    const meta = ITEMS_LABELS[item] || { label: item, color: '#777' };
                    return (
                      <div 
                        key={idx}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          background: 'rgba(255,255,255,0.02)',
                          padding: '0.5rem 0.8rem',
                          borderRadius: '6px',
                          borderLeft: `3px solid ${meta.color}`,
                        }}
                      >
                        <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#fff' }}>
                          {idx + 1}. {meta.label}
                        </span>
                        <div style={{ display: 'flex', gap: '4px' }}>
                          <button 
                            onClick={() => moveItemInEdit(idx, -1)} 
                            disabled={idx === 0}
                            style={{ background: 'none', border: 'none', color: '#fff', cursor: 'pointer', padding: '0 4px', opacity: idx === 0 ? 0.3 : 1 }}
                          >
                            ▲
                          </button>
                          <button 
                            onClick={() => moveItemInEdit(idx, 1)} 
                            disabled={idx === editItems.length - 1}
                            style={{ background: 'none', border: 'none', color: '#fff', cursor: 'pointer', padding: '0 4px', opacity: idx === editItems.length - 1 ? 0.3 : 1 }}
                          >
                            ▼
                          </button>
                          <button 
                            onClick={() => removeItemFromEdit(idx)}
                            style={{ background: 'none', border: 'none', color: 'var(--accent-danger)', cursor: 'pointer', marginLeft: '8px', fontSize: '0.85rem' }}
                          >
                            🗑️
                          </button>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            {/* Adicionar novos elementos */}
            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 800, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '8px' }}>
                Inserir Elemento na Sequência
              </label>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {Object.keys(ITEMS_LABELS).map(key => {
                  const meta = ITEMS_LABELS[key];
                  return (
                    <button
                      key={key}
                      onClick={() => addItemToEdit(key)}
                      style={{
                        padding: '0.4rem 0.8rem',
                        fontSize: '0.68rem',
                        background: 'rgba(255,255,255,0.03)',
                        border: `1px solid ${meta.color}66`,
                        borderRadius: '6px',
                        color: '#fff',
                        fontWeight: 700,
                        cursor: 'pointer',
                        transition: 'all 0.15s',
                      }}
                      onMouseEnter={(e) => {
                        e.target.style.background = `${meta.color}15`;
                      }}
                      onMouseLeave={(e) => {
                        e.target.style.background = 'rgba(255,255,255,0.03)';
                      }}
                    >
                      +{key.replace(/_/g, ' ')}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Duplicar para outros dias */}
            <div style={{ marginBottom: '1.8rem', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '1rem' }}>
              <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 800, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '8px' }}>
                Duplicar este horário também para:
              </label>
              <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                {DIAS_UTEIS.filter(d => d !== editingDay).map(day => (
                  <button
                    key={day}
                    onClick={() => toggleDupDay(day)}
                    style={{
                      padding: '0.35rem 0.7rem',
                      fontSize: '0.62rem',
                      background: dupTargetDays.includes(day) ? 'var(--accent-primary)' : 'rgba(255,255,255,0.02)',
                      border: '1px solid rgba(255,255,255,0.08)',
                      borderRadius: '5px',
                      color: dupTargetDays.includes(day) ? '#000' : 'var(--text-secondary)',
                      fontWeight: 700,
                      cursor: 'pointer',
                    }}
                  >
                    {DIAS_LABELS[day].split('-')[0]}
                  </button>
                ))}
              </div>
            </div>

            {/* Ações do Modal */}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button onClick={closeEdit} className="btn btn-secondary">
                Cancelar
              </button>
              <button onClick={saveLocalEdit} className="btn btn-action">
                Confirmar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
