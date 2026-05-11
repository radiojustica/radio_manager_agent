import { useEffect, useState } from 'react';
import './Telemetria.css';

export default function EventTicker() {
  const [events, setEvents] = useState([]);

  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/status`);

    ws.onmessage = (event) => {
      const json = JSON.parse(event.data);
      if (json.events) {
        setEvents(json.events);
      }
    };

    return () => ws.close();
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
