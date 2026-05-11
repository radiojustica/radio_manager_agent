import { useState } from 'react';
import './ConfigPage.css'; // Reutilizando estilos existentes

export default function ScheduleEditor() {
  const [rules, setRules] = useState([
    { bloco: 'Madrugada', energia_alvo: 2 },
    { bloco: 'Manhã', energia_alvo: 4 },
    { bloco: 'Tarde', energia_alvo: 5 },
    { bloco: 'Noite', energia_alvo: 3 },
  ]);
  const [saving, setSaving] = useState(false);

  const handleLevelChange = (bloco, level) => {
    setRules(rules.map(r => r.bloco === bloco ? { ...r, energia_alvo: level } : r));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await fetch('/api/config/schedule', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(rules),
      });
      if (res.ok) {
        alert('✅ Configurações de energia salvas no SQLite!');
      }
    } catch (e) {
      alert('Erro ao salvar no banco de dados.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="schedule-editor glass-panel" style={{ marginTop: '20px', padding: '1.5rem' }}>
      <h3 className="module-title">EDITOR DE ENERGIA POR BLOCO</h3>
      <p style={{ fontSize: '0.8rem', opacity: 0.7, marginBottom: '1rem' }}>
        Defina a energia alvo (1-5) para cada período do dia.
      </p>

      <div className="rules-grid">
        {rules.map(rule => (
          <div key={rule.bloco} className="rule-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <span style={{ fontWeight: 'bold' }}>{rule.bloco}</span>
            <div className="energy-selector" style={{ display: 'flex', gap: '5px' }}>
              {[1, 2, 3, 4, 5].map(level => (
                <button
                  key={level}
                  onClick={() => handleLevelChange(rule.bloco, level)}
                  className={`btn-level ${rule.energia_alvo === level ? 'active' : ''}`}
                  style={{
                    width: '30px',
                    height: '30px',
                    borderRadius: '5px',
                    border: '1px solid #444',
                    background: rule.energia_alvo === level ? '#00ff00' : 'transparent',
                    color: rule.energia_alvo === level ? '#000' : '#fff',
                    cursor: 'pointer'
                  }}
                >
                  {level}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>

      <button 
        onClick={handleSave} 
        disabled={saving}
        className="btn-action"
        style={{ width: '100%', marginTop: '1rem', padding: '1rem' }}
      >
        {saving ? 'SALVANDO...' : 'SALVAR NO SQLITE'}
      </button>
    </div>
  );
}
