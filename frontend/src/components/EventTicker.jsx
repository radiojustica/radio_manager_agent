import { useEffect, useState } from 'react';
import './Telemetria.css';

export default function EventTicker() {
  const [events, setEvents] = useState([]);

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch('/api/status/guardian/events?limit=5');
        if (res.ok) {
          const json = await res.json();
          setEvents(json.events || []);
        }
      } catch (e) {
        console.error("Erro ao buscar Eventos", e);
      }
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="event-ticker glass-panel">
      <h3 className="module-title">TRACKER DO GUARDIÃO</h3>
      <div className="events-list">
        {events.length === 0 ? (
          <div className="event-item text-muted">Aguardando eventos...</div>
        ) : (
          events.map((evt, i) => (
            <div key={i} className="event-item">
              <span className="event-time">{evt.time}</span>
              <span className="event-msg">{evt.message}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
