import { useEffect, useState } from 'react';

/**
 * MONITORAMENTO DE PROCESSOS DE TRANSMISSÃO
 * Mostra o ZaraRadio (playout) e TODAS as instâncias do BUTT encoder
 * (uma por mountpoint: 64k, 128k, 32k...) com dados REAIS por processo.
 * Não usa mock: PID, status de conexão, CPU% e RAM (MB) vêm do backend.
 */
export default function ProcessMonitor({ player, systemHealth, style }) {
  const [osCpu, setOsCpu] = useState(systemHealth?.cpu_percent ?? null);
  const [osRamGb, setOsRamGb] = useState(systemHealth?.ram_available_gb ?? null);

  // Atualiza métricas de SO a partir do systemHealth quando disponível
  useEffect(() => {
    if (systemHealth) {
      setOsCpu(systemHealth.cpu_percent ?? null);
      setOsRamGb(systemHealth.ram_available_gb ?? null);
    }
  }, [systemHealth]);

  const instances = player?.butt_detalhes || [];
  const ativos = instances.filter(i => i.status === 'transmitindo').length;

  const StatusPill = ({ ok, warn, label }) => {
    const color = ok ? 'var(--accent-success)' : warn ? 'var(--accent-warning)' : 'var(--accent-danger)';
    return (
      <span style={{
        display: 'inline-flex', alignItems: 'center', gap: '6px',
        fontSize: '0.7rem', fontWeight: 800, textTransform: 'uppercase', color
      }}>
        <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: color, boxShadow: `0 0 6px ${color}`, display: 'inline-block' }} />
        {label}
      </span>
    );
  };

  const renderCard = (title, sub, statusNode, cpu, ram, actionLabel, actionColor) => (
    <div className="proc-card" style={{ borderColor: statusNode.props.ok ? 'rgba(34,197,94,0.3)' : statusNode.props.warn ? 'rgba(250,204,21,0.3)' : 'rgba(244,63,94,0.3)' }}>
      <div className="proc-card-head">
        <div>
          <div className="proc-title">{title}</div>
          <div className="proc-sub">{sub}</div>
        </div>
        {statusNode}
      </div>
      <div className="proc-metrics">
        <div><span>CPU</span><strong>{cpu != null ? `${cpu}%` : '—'}</strong></div>
        <div><span>RAM</span><strong>{ram != null ? `${ram} MB` : '—'}</strong></div>
      </div>
      <button className="proc-action" style={{ background: actionColor, color: actionColor === 'var(--accent-success)' ? '#062' : '#fff' }}>
        {actionLabel}
      </button>
    </div>
  );

  return (
    <div className="proc-monitor" style={style}>
      <div className="section-header" style={{ marginBottom: '1.25rem' }}>
        <div className="section-title">
          <div className="accent-line" style={{ background: ativos > 0 ? 'var(--accent-success)' : 'var(--accent-danger)' }} />
          MONITORAMENTO DE PROCESSOS DE TRANSMISSÃO
        </div>
      </div>

      <div className="proc-grid">
        {/* ZARARADIO (PLAYOUT) */}
        {renderCard(
          'ZARARADIO (PLAYOUT)',
          'Playout principal',
          <StatusPill ok={player?.status === 'playing'} label={player?.status === 'playing' ? 'Ativo' : 'Parado'} />,
          osCpu,
          osRamGb != null ? Math.round(osRamGb * 1024) : null,
          player?.status === 'playing' ? 'NO AR (REPRODUZINDO)' : 'PARADO',
          'var(--accent-success)'
        )}

        {/* UMA CARD POR INSTÂNCIA DO BUTT */}
        {instances.length > 0 ? instances.map((inst, idx) => {
          const isLive = inst.status === 'transmitindo';
          const label = (inst.window_title || `BUTT ${inst.pid}`).replace(/^Conectado a\s*/i, '');
          return (
            <div key={inst.pid || idx} className="proc-card" style={{ borderColor: isLive ? 'rgba(34,197,94,0.3)' : 'rgba(250,204,21,0.3)' }}>
              <div className="proc-card-head">
                <div>
                  <div className="proc-title">BUTT ENCODER (PID: {inst.pid})</div>
                  <div className="proc-sub">{label || 'Desconhecido'}</div>
                </div>
                <StatusPill
                  ok={isLive}
                  warn={!isLive && inst.has_connection}
                  label={isLive ? 'Estabelecida' : inst.has_connection ? 'Conectado' : 'Offline'}
                />
              </div>
              <div className="proc-metrics">
                <div><span>CPU</span><strong>{inst.cpu_percent != null ? `${inst.cpu_percent}%` : '—'}</strong></div>
                <div><span>RAM</span><strong>{inst.mem_mb != null ? `${inst.mem_mb} MB` : '—'}</strong></div>
              </div>
              <button className="proc-action" style={{ background: isLive ? 'var(--accent-success)' : 'var(--accent-warning)', color: isLive ? '#062' : '#531' }}>
                {isLive ? 'TRANSMITINDO' : 'AGUARDANDO'}
              </button>
            </div>
          );
        }) : (
          <div className="proc-card" style={{ borderColor: 'rgba(244,63,94,0.3)' }}>
            <div className="proc-card-head">
              <div>
                <div className="proc-title">BUTT ENCODER</div>
                <div className="proc-sub">Nenhuma instância detectada</div>
              </div>
              <StatusPill ok={false} label="Offline" />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
