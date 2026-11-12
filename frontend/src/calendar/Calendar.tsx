import React, {useRef} from 'react';
import {ChevronLeft, ChevronRight} from 'lucide-react';
import {addDays, addMonths, capitalize, dayLabel, daysInMonth, weekday} from '../lib/dates';
import {TONES, toneOf} from './agenda';
import type {AgendaItem, Tone} from './agenda';

export type View = 'month' | 'week';
const WEEKDAYS = ['L', 'M', 'M', 'J', 'V', 'S', 'D'];
const NAMES: Record<Tone, string> = {pending: 'por aprobar', confirmed: 'confirmada', appointment: 'cita', block: 'bloqueo', cancelled: 'cancelada'};

export const weekOf = (day: string) => Array.from({length: 7}, (_, index) => addDays(day, index - weekday(day)));

function describe(items: AgendaItem[] = []) {
  if (!items.length) return 'sin eventos';
  const counts = new Map<Tone, number>();
  items.forEach(item => counts.set(toneOf(item), (counts.get(toneOf(item)) || 0) + 1));
  return [...counts].map(([tone, count]) => `${count} ${NAMES[tone]}`).join(', ');
}

function DayCell({day, items, today, selected, zone, onSelect, label}: {day: string; items?: AgendaItem[]; today: string; selected: string; zone: string; onSelect: (day: string) => void; label?: string}) {
  const present = new Set((items || []).map(toneOf));
  return <button type="button" className="day" aria-pressed={day === selected} aria-current={day === today ? 'date' : undefined}
    aria-label={`${dayLabel(day, zone, "EEEE d 'de' MMMM")}, ${describe(items)}`} onClick={() => onSelect(day)}>
    {label && <small aria-hidden="true">{label}</small>}
    <span aria-hidden="true">{Number(day.slice(8))}</span>
    <span className="dots" aria-hidden="true">{TONES.filter(entry => present.has(entry.tone)).map(entry => <i key={entry.tone} className={`dot ${entry.tone}`}/>)}</span>
  </button>;
}

export function Calendar({view, onView, month, onMonth, selected, onSelect, onToday, today, zone, days, busy}: {
  view: View; onView: (view: View) => void;
  month: string; onMonth: (month: string) => void;
  selected: string; onSelect: (day: string) => void; onToday: () => void;
  today: string; zone: string; days: Map<string, AgendaItem[]>; busy: boolean;
}) {
  const touch = useRef<{x: number; y: number} | null>(null);
  const step = (direction: number) => {
    if (view === 'month') onMonth(addMonths(month, direction));
    else onSelect(addDays(selected, direction * 7));
  };
  const week = weekOf(selected);
  const title = view === 'month' ? `${month}-01` : week[3];
  const monthDays = Array.from({length: daysInMonth(month)}, (_, index) => `${month}-${String(index + 1).padStart(2, '0')}`);

  return <section className="panel calendar" aria-busy={busy}>
    <header className="calendar-top">
      <h2 aria-live="polite">{capitalize(dayLabel(title, zone, 'MMMM yyyy'))}</h2>
      <button type="button" className="secondary compact" onClick={onToday} disabled={selected === today && month === today.slice(0, 7)}>Hoy</button>
      <button type="button" className="icon-btn" aria-label={view === 'month' ? 'Mes anterior' : 'Semana anterior'} onClick={() => step(-1)}><ChevronLeft size={22}/></button>
      <button type="button" className="icon-btn" aria-label={view === 'month' ? 'Mes siguiente' : 'Semana siguiente'} onClick={() => step(1)}><ChevronRight size={22}/></button>
    </header>
    <div className="segmented" role="group" aria-label="Vista del calendario">
      <button type="button" aria-pressed={view === 'month'} onClick={() => onView('month')}>Mes</button>
      <button type="button" aria-pressed={view === 'week'} onClick={() => onView('week')}>Semana</button>
    </div>
    <div className={`month-grid ${view}`}
      onTouchStart={event => { touch.current = {x: event.touches[0].clientX, y: event.touches[0].clientY}; }}
      onTouchEnd={event => {
        const start = touch.current;
        touch.current = null;
        if (!start) return;
        const dx = event.changedTouches[0].clientX - start.x, dy = event.changedTouches[0].clientY - start.y;
        if (Math.abs(dx) > 56 && Math.abs(dx) > Math.abs(dy) * 1.5) step(dx < 0 ? 1 : -1);
      }}>
      {view === 'month' ? <>
        {WEEKDAYS.map((name, index) => <span className="weekday" key={index} aria-hidden="true">{name}</span>)}
        {Array.from({length: weekday(monthDays[0])}, (_, index) => <span key={`blank-${index}`}/>)}
        {monthDays.map(day => <DayCell key={day} day={day} items={days.get(day)} today={today} selected={selected} zone={zone} onSelect={onSelect}/>)}
      </> : week.map((day, index) => <DayCell key={day} day={day} label={WEEKDAYS[index]} items={days.get(day)} today={today} selected={selected} zone={zone} onSelect={onSelect}/>)}
    </div>
    <ul className="legend" aria-label="Significado de los puntos">
      {TONES.map(entry => <li key={entry.tone}><i className={`dot ${entry.tone}`}/>{entry.label}</li>)}
    </ul>
  </section>;
}
