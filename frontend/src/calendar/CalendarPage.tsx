import React, {useEffect, useMemo, useState} from 'react';
import {AlertCircle, ChevronRight} from 'lucide-react';
import {useStudio} from '../app/context';
import {navigate} from '../app/router';
import {dayLabel} from '../lib/dates';
import {byDay, useAgenda} from './agenda';
import {Calendar, weekOf} from './Calendar';
import type {View} from './Calendar';
import {DayAgenda} from './DayAgenda';

const VIEW_KEY = 'jordy.calendar.view';

function PendingStrip({onToday}: {onToday: () => void}) {
  const {metrics} = useStudio();
  const pending: number = metrics.pending || 0, signatures: number = metrics.signatures_today || 0;
  if (!pending && !signatures) return null;
  return <div className="pending-strip" role="group" aria-label="Pendientes">
    {pending > 0 && <button type="button" onClick={() => navigate('reservaciones/por-aprobar')}>
      <i className="dot pending"/><span><strong>{pending}</strong> por aprobar</span><ChevronRight size={16} aria-hidden="true"/>
    </button>}
    {signatures > 0 && <button type="button" onClick={onToday}>
      <i className="dot appointment"/><span><strong>{signatures}</strong> {signatures === 1 ? 'firma hoy' : 'firmas hoy'}</span><ChevronRight size={16} aria-hidden="true"/>
    </button>}
  </div>;
}

export function CalendarPage({day, onDay}: {day: string; onDay: (day: string) => void}) {
  const {zone, today, revision} = useStudio();
  const [view, setView] = useState<View>(() => (localStorage.getItem(VIEW_KEY) === 'week' ? 'week' : 'month'));
  const [month, setMonth] = useState(day.slice(0, 7));
  useEffect(() => setMonth(day.slice(0, 7)), [day]);

  const months = useMemo(() => (view === 'month' ? [month] : [...new Set(weekOf(day).map(value => value.slice(0, 7)))]), [view, month, day]);
  const {items, error, loading, retry} = useAgenda(months, revision);
  const days = useMemo(() => byDay(items, zone), [items, zone]);

  return <div className="calendar-layout">
    <div className="stack">
      <PendingStrip onToday={() => onDay(today)}/>
      {error && <div className="error" role="alert"><AlertCircle size={18}/><span>No se pudo cargar la agenda de {dayLabel(`${months[0]}-01`, zone, 'MMMM')}: {error}. Se muestran los últimos datos cargados.</span><button className="text-btn" onClick={retry}>Reintentar</button></div>}
      <Calendar view={view} onView={value => { localStorage.setItem(VIEW_KEY, value); setView(value); }}
        month={month} onMonth={setMonth} selected={day} onSelect={onDay} onToday={() => { setMonth(today.slice(0, 7)); onDay(today); }} today={today} zone={zone} days={days} busy={loading}/>
    </div>
    <DayAgenda day={day} items={days.get(day) || []}/>
  </div>;
}
