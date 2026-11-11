import React from 'react';
import {Ban, CalendarPlus, ChevronRight, Plus} from 'lucide-react';
import {useStudio} from '../app/context';
import {capitalize, dayKey, dayLabel, fmt} from '../lib/dates';
import {labels} from '../shared';
import {toneOf} from './agenda';
import type {AgendaItem} from './agenda';

const APPOINTMENT_STATUS: Record<string, string> = {scheduled: '', completed: ' · Realizada', cancelled: ' · Cancelada'};

function statusText(item: AgendaItem) {
  if (item.type === 'block') return 'Bloqueo';
  if (item.type === 'appointment') return `${item.kind === 'contract' ? 'Firma' : 'Reunión'}${APPOINTMENT_STATUS[item.status] || ''}`;
  return labels[item.status] || item.status;
}

/** "10:00 – 11:30", or how the item relates to this day when it spans several. */
function hours(item: AgendaItem, day: string, zone: string) {
  const starts = dayKey(item.starts_at, zone) === day, ends = dayKey(new Date(item.ends_at).getTime() - 1, zone) === day;
  if (!starts && !ends) return {main: 'Todo', rest: 'el día'};
  if (!starts) return {main: 'Hasta', rest: fmt(item.ends_at, zone, 'HH:mm')};
  return {main: fmt(item.starts_at, zone, 'HH:mm'), rest: ends ? fmt(item.ends_at, zone, 'HH:mm') : 'en adelante'};
}

/** Everything that happens on one day, in order, whatever its type. */
export function DayAgenda({day, items}: {day: string; items: AgendaItem[]}) {
  const {zone, today, open, openBooking} = useStudio();
  const short = dayLabel(day, zone, 'd MMM');
  const past = day < today;
  const openItem = (item: AgendaItem) => {
    if (item.type === 'booking') openBooking(item.id);
    else open(item.type === 'appointment' ? 'event-appointment' : 'event-block', item);
  };
  return <section className="panel day-agenda" aria-labelledby="day-agenda-title">
    <header className="panel-head">
      <h2 id="day-agenda-title">{capitalize(dayLabel(day, zone))}</h2>
      <span className="muted">{day === today ? 'Hoy · ' : ''}{items.length ? `${items.length} ${items.length === 1 ? 'evento' : 'eventos'}` : 'Sin eventos'}</span>
    </header>
    {items.length > 0 && <ul className="events">
      {items.map(item => {
        const time = hours(item, day, zone);
        return <li key={`${item.type}-${item.id}`}>
          <button type="button" className={`event ${toneOf(item)}`} onClick={() => openItem(item)}>
            <time><strong>{time.main}</strong><small>{time.rest}</small></time>
            <span className="event-body">
              <strong>{item.title}</strong>
              <small>{[item.subtitle, item.location].filter(Boolean).join(' · ')}</small>
              <em className={`event-status ${toneOf(item)}`}>{statusText(item)}</em>
            </span>
            <ChevronRight size={18} aria-hidden="true"/>
          </button>
        </li>;
      })}
    </ul>}
    {past
      ? !items.length && <p className="muted pad">No hubo eventos este día.</p>
      : items.length
        ? <div className="day-actions"><button type="button" className="secondary" onClick={() => open('create', {day})}><Plus size={18}/>Agregar el {short}</button></div>
        : <div className="day-empty">
            <p className="muted">Día libre. Puedes registrar algo desde aquí.</p>
            <button type="button" className="primary" onClick={() => open('booking', {day})}><CalendarPlus size={18}/>Nueva reservación el {short}</button>
            <button type="button" className="secondary" onClick={() => open('block', {day})}><Ban size={18}/>Bloquear</button>
          </div>}
  </section>;
}
