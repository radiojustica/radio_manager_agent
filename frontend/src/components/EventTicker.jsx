import { useEffect, useRef } from 'react';
import { useWsData } from '../context/WebSocketContext';
import './Telemetria.css';

const EVENT_ICONS = {
  RESTART:      '🔄',
  QUARANTINE:   '☣️',
  WARNING:      '⚠️',
  LIVE_START:   '🎙️',
  LIVE_END:     '📴',
  TASK_DELETED: '🗑️',
  WORKER:       '⚙️',
};

function getIcon(type) {
  return EVENT_ICONS[type] || '◆';
}

export default function EventTicker() {
  const { events } = useWsData();
  const listRef = useRef(null);

  // Auto-scroll to bottom when new events arrive
  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [events]);

  return (
    <div className="card event-ticker">
      <div className="ticker-header">
        <div className="accent-line" style={{ background: 'var(--accent-purple)' }} />
        TRACKER DO GUARDIÃO
      </div>

      <div className="events-list" ref={listRef}>
        {events.length === 0 ? (
          <div className="event-empty">Aguardando eventos do guardião...</div>
        ) : (
          [...events].reverse().map((evt, i) => (
            <div key={i} className={`event-item ${evt.type || ''}`}>
              <span className="event-icon">{getIcon(evt.type)}</span>
              <span className="event-time">{evt.time}</span>
              <span className="event-msg">{evt.message}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
