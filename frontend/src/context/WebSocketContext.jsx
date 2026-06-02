import { createContext, useContext, useEffect, useRef, useState } from 'react';

const WebSocketContext = createContext(null);

export function WebSocketProvider({ children }) {
  const [player, setPlayer] = useState({
    title: 'Conectando...',
    status: 'stopped',
    energy: 0,
    butt_ativos: 0,
    butt_count: 3,
    curadoria_status: 'IDLE',
  });
  const [events, setEvents] = useState([]);
  const [connected, setConnected] = useState(false);

  const wsRef = useRef(null);
  const retryRef = useRef(null);
  const delayRef = useRef(1000);

  const connect = () => {
    if (wsRef.current && wsRef.current.readyState <= 1) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/status`);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      delayRef.current = 1000;
    };

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
        if (res.ok) {
          const data = await res.json();
          setPlayer(p => ({ ...p, ...data }));
        }
      } catch (err) {
        console.error('[HTTP] erro ao buscar player:', err);
      }
    };

    fetchPlayer();
    const intervalId = setInterval(fetchPlayer, 2000);

    return () => {
      clearTimeout(retryRef.current);
      clearInterval(intervalId);
      wsRef.current?.close();
    };
  }, []);

  return (
    <WebSocketContext.Provider value={{ player, events, connected }}>
      {children}
    </WebSocketContext.Provider>
  );
}

export const useWsData = () => useContext(WebSocketContext);
