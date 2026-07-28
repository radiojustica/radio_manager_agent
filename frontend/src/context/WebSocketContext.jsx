import { createContext, useContext, useEffect, useRef, useState } from 'react';

const WebSocketContext = createContext(null);

export function WebSocketProvider({ children }) {
  const [player, setPlayer] = useState({
    title: 'Carregando...',
    status: 'stopped',
    energy: 0,
    butt_ativos: 0,
    butt_count: 3,
    butt_detalhes: [],
    curadoria_status: 'IDLE',
    sazonalidade: { ativa: false, nome: 'Programação Convencional', detalhe: 'Sem campanhas temáticas ativas.', tipo: 'normal' },
    updated_at: new Date().toISOString(),
  });
  // systemHealth vem de dois lugares:
  // 1. /api/engine/stats → cpu, ram_percent, ram_free_mb, network_online (telemetria)
  // 2. /api/status/hardware/realtime → uptime, disk, cpu_temp, etc. (dados reais do OS)
  const [systemHealth, setSystemHealth] = useState({ cpu: 0, ram_percent: 0, ram_free_mb: 0, network_online: false, uptime_human: '—', disk: {}, cpu_temp: null, cpu_count: 0, cpu_freq: null, ram_total_gb: 0, ram_available_gb: 0, ups: {}, uptime_seconds: 0 });
  const [streamingInfo, setStreamingInfo] = useState({ enabled: false, listeners: -1, url: null });
  const [events, setEvents] = useState([]);
  const [connected, setConnected] = useState(false);
  const [acervoFila, setAcervoFila] = useState([]);
  const wsRef = useRef(null);
  const retryRef = useRef(null);
  const delayRef = useRef(1000);

  const connect = () => {
    if (wsRef.current && wsRef.current.readyState <= 1) return;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/status`);
    wsRef.current = ws;
    ws.onopen = () => { setConnected(true); delayRef.current = 1000; };
    ws.onmessage = (e) => {
      try {
        const json = JSON.parse(e.data);
        if (json?.player) setPlayer((p) => ({ ...p, ...json.player }));
        if (Array.isArray(json?.events)) setEvents(json.events);
      } catch (err) {
        console.error('[WS] parse error:', err);
      }
    };
    ws.onclose = () => {
      setConnected(false);
      retryRef.current = setTimeout(() => {
        delayRef.current = Math.min(delayRef.current * 2, 30000);
        connect();
      }, delayRef.current);
    };
    ws.onerror = () => ws.close();
  };

  useEffect(() => {
    connect();

    const fetchPlayer = async () => {
      try {
        const res = await fetch('/api/status/player/now');
        if (res.ok) { const data = await res.json(); setPlayer(p => ({ ...p, ...data })); }
      } catch (err) { console.error('[HTTP] erro ao buscar player:', err); }
    };
    const fetchHealth = async () => {
      try {
        const res = await fetch('/api/engine/stats');
        if (res.ok) {
          const data = await res.json();
          if (data.health) setSystemHealth(prev => ({ ...prev, ...data.health }));
          if (data.streaming_enabled !== undefined) setStreamingInfo({ enabled: data.streaming_enabled, listeners: data.listeners ?? -1, url: data.streaming_url ?? null });
        }
      } catch (err) { console.error('[HTTP] erro ao buscar telemetria:', err); }
    };
    const fetchHardware = async () => {
      try {
        const res = await fetch('/api/status/hardware/realtime');
        if (res.ok) {
          const data = await res.json();
          if (data.error) return;
          setSystemHealth(prev => ({
            ...prev,
            uptime_human: data.uptime_human || prev.uptime_human,
            uptime_seconds: data.uptime_seconds ?? prev.uptime_seconds,
            disk: data.disk || prev.disk,
            cpu_temp: data.cpu_temp_celsius ?? prev.cpu_temp,
            cpu_count: data.cpu_count ?? prev.cpu_count,
            cpu_freq: data.cpu_freq_current_mhz ? `${data.cpu_freq_current_mhz.toFixed(0)}` : prev.cpu_freq,
            ram_total_gb: data.ram_total_gb ?? prev.ram_total_gb,
            ram_available_gb: data.ram_available_gb ?? prev.ram_available_gb,
            ups: data.ups ?? { charge: -1, voltage: '—', minutes: '—' },
          }));
        }
      } catch (err) { console.error('[HTTP] erro ao buscar hardware:', err); }
    };
    const fetchQueue = async () => {
      try {
        const res = await fetch('/api/acervo?page=1&limit=4');
        if (res.ok) { const data = await res.json(); if (data.items?.length) setAcervoFila(data.items); }
      } catch (err) { console.error('[HTTP] erro ao buscar fila:', err); }
    };

    fetchPlayer();
    fetchHealth();
    fetchHardware();
    fetchQueue();
    const id = setInterval(() => { fetchPlayer(); fetchHealth(); fetchHardware(); fetchQueue(); }, 5000);

    return () => { clearInterval(id); clearTimeout(retryRef.current); wsRef.current?.close(); };
  }, []);

  return (
    <WebSocketContext.Provider value={{ player, systemHealth, streamingInfo, events, connected, acervoFila }}>
      {children}
    </WebSocketContext.Provider>
  );
}

export const useWsData = () => useContext(WebSocketContext);
