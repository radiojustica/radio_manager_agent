import { useState } from 'react';
import { useWsData } from '../context/WebSocketContext';
import './Telemetria.css';

const EVENT_ICONS = {
  RESTART:    '🔄',
  QUARANTINE: '☣️',
  WARNING:    '⚠️',
  LIVE_START: '🎙️',
  LIVE_END:   '📴',
  TASK_DELETED: '🗑️',
  DEFAULT:    '◆',
};

export default function NowPlayingCard() {
  const { player, connected } = useWsData();
  const [reconnecting, setReconnecting] = useState(false);
  const [reconnectMsg, setReconnectMsg] = useState(null);

  const { title = '—', status = 'stopped', energy = 0, butt_ativos = 0, butt_count = 3, curadoria_status = 'IDLE' } = player;

  const energyLevel = Math.round(energy * 5);
  const isLong = title.length > 40;

  const handleReconnect = async () => {
    setReconnecting(true);
    setReconnectMsg(null);
    try {
      const res = await fetch('/api/status/butt/reconnect', { method: 'POST' });
      const json = await res.json();
      setReconnectMsg(json.success ? `✓ ${json.reconnected} instâncias acionadas` : `✗ ${json.error || 'Falha'}`);
    } catch {
      setReconnectMsg('✗ Sem resposta do backend');
    } finally {
      setReconnecting(false);
      setTimeout(() => setReconnectMsg(null), 4000);
    }
  };

  const statusLabel = status === 'playing' ? 'LIVE' : status === 'frozen' ? 'CONGELADO' : 'PARADO';

  return (
    <div className={`card now-playing-card ${status}`}>
      <div className="status-ring" />

      <div className="np-header">
        <span className="np-module-label">NO AR AGORA</span>
        <span className={`status-badge ${status}`}>{statusLabel}</span>
      </div>

      <div className="np-track-block">
        <div className="np-title-wrap">
          <h2 className={`np-title ${isLong ? 'long' : ''}`} title={title}>
            {title}
          </h2>
        </div>
        <p className="np-subtitle">SINCRONIA TEMPORAL 24/7 • ZARARADIO ENGINE</p>
      </div>

      <div className="vu-section">
        <div className="vu-header">
          <span className="vu-label">NÍVEL DE ENERGIA ACÚSTICA (LIBROSA)</span>
          <span className="vu-value">{energyLevel.toFixed(1)} <small>/ 5.0</small></span>
        </div>
        <div className="vu-segments">
          {[1, 2, 3, 4, 5].map(s => (
            <div key={s} className={`vu-seg e${s} ${energyLevel >= s ? 'on' : ''}`} />
          ))}
        </div>
      </div>

      <div className="np-footer">
        <div className="butt-info">
          <span className="butt-icon">📡</span>
          <div className="butt-texts">
            <span className="butt-label">STREAMING NODES</span>
            <span className="butt-value">{butt_ativos} / {butt_count} ATIVOS</span>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
          <button
            onClick={handleReconnect}
            disabled={reconnecting}
            className="btn btn-sm"
            title="Forçar reconexão dos encoders BUTT"
          >
            {reconnecting ? <span className="spinner" /> : null}
            {reconnecting ? 'Conectando...' : 'RECONECTAR HUB'}
          </button>
          {reconnectMsg && (
            <span style={{ fontSize: '0.65rem', color: reconnectMsg.startsWith('✓') ? 'var(--accent-success)' : 'var(--accent-danger)', fontWeight: 700 }}>
              {reconnectMsg}
            </span>
          )}
        </div>
      </div>

      <div className="worker-banner">
        <span className="worker-key">WORKER STATUS:</span>
        <span className="worker-val">{curadoria_status}</span>
        <span style={{ marginLeft: 'auto' }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: connected ? 'var(--accent-success)' : 'var(--accent-danger)', display: 'inline-block', verticalAlign: 'middle', boxShadow: connected ? '0 0 6px rgba(16,185,129,0.6)' : 'none' }} />
        </span>
      </div>
    </div>
  );
}
