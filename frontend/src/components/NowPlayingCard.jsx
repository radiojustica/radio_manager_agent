import { useEffect, useState, useRef } from 'react';
import './Telemetria.css';

export default function NowPlayingCard() {
  const [data, setData] = useState({ title: 'Carregando...', status: 'stopped', energy: 0, butt_ativos: 0, butt_count: 3 });
  const [isReconnecting, setIsReconnecting] = useState(false);

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch('/api/status/player/now');
        if (res.ok) {
          const json = await res.json();
          setData(json);
        }
      } catch (e) {
        console.error("Erro ao buscar NowPlaying", e);
      }
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  const handleForceReconnect = async () => {
    setIsReconnecting(true);
    try {
      const res = await fetch('/api/butt/reconnect', { method: 'POST' });
      const json = await res.json();
      if (json.success) {
        alert(`✅ Reconexão forçada: ${json.reconnected} BUTTs acionados.`);
      }
    } catch (e) {
      alert('Erro de conexão com o backend.');
    } finally {
      setIsReconnecting(false);
    }
  };

  const energyLevel = Math.round(data.energy * 5);
  const segments = [1, 2, 3, 4, 5];

  return (
    <div className={`premium-card now-playing-card ${data.status}`}>
      <div className="card-header-flex">
        <h3 className="module-tag">NO AR AGORA</h3>
        <div className={`status-pill ${data.status}`}>
           {data.status === 'playing' ? 'LIVE' : data.status === 'frozen' ? 'FROZEN' : 'STOPPED'}
        </div>
      </div>

      <div className="track-info">
        <div className="track-title-container">
          <h2 className="track-title" title={data.title}>{data.title}</h2>
        </div>
        <p className="track-meta">SINCRONIA TEMPORAL 24/7 • ZARARADIO ENGINE</p>
      </div>
      
      <div className="vu-meter-section">
        <div className="vu-header">
           <span className="vu-label">NÍVEL DE ENERGIA ACÚSTICA (LIBROSA)</span>
           <span className="vu-value">{energyLevel.toFixed(1)} <small>/ 5.0</small></span>
        </div>
        <div className="vu-container">
          {segments.map(s => (
            <div 
              key={s} 
              className={`vu-segment s${s} ${energyLevel >= s ? 'active' : ''}`}
            />
          ))}
        </div>
      </div>
      
      <div className="card-footer-stats">
        <div className="butt-status-group">
           <div className="stat-icon">📡</div>
           <div className="stat-text">
              <span className="stat-label">STREAMING NODES</span>
              <span className="stat-value">{data.butt_ativos} / {data.butt_count} ATIVOS</span>
           </div>
        </div>
        
        <button 
          onClick={handleForceReconnect} 
          disabled={isReconnecting}
          className="btn-action"
          style={{ padding: '0.6rem 1rem', fontSize: '0.75rem' }}
          title="Forçar reconexão de encoders"
        >
          {isReconnecting ? '...' : 'RECONECTAR HUB'}
        </button>
      </div>

      <div className="worker-status-banner">
         <span className="worker-label">WORKER STATUS:</span>
         <span className="worker-value">{data.curadoria_status || 'IDLE'}</span>
      </div>
    </div>
  );
}
