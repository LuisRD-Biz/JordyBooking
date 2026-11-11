import React, {useEffect, useState} from 'react';
import {ChevronLeft, ChevronRight, Plus} from 'lucide-react';
import {api} from '../api';
import {useStudio} from '../app/context';
import {DayBookings} from '../features';
import {addMonths, capitalize, dayLabel, daysInMonth, weekday} from '../lib/dates';
import type {Row} from '../shared';

/** Month grid with a booking count per day; the unified agenda replaces it in the next step. */
export function CalendarPage({day, onDay}: {day: string; onDay: (day: string) => void}) {
  const {zone, today, revision, open, openBooking} = useStudio();
  const [month, setMonth] = useState(day.slice(0, 7)), [counts, setCounts] = useState<Row>({});
  useEffect(() => {
    let active = true;
    api(`/api/search/calendar?month=${Number(month.slice(5))}&year=${month.slice(0, 4)}`).then(result => { if (active) setCounts(result); }).catch(() => undefined);
    return () => { active = false; };
  }, [month, revision]);
  const days = Array.from({length: daysInMonth(month)}, (_, index) => `${month}-${String(index + 1).padStart(2, '0')}`);
  return <div className="calendar-layout">
    <section className="panel calendar">
      <header className="calendar-top">
        <h2>{capitalize(dayLabel(`${month}-01`, zone, 'MMMM yyyy'))}</h2>
        <button className="icon-btn" aria-label="Mes anterior" onClick={() => setMonth(addMonths(month, -1))}><ChevronLeft size={20}/></button>
        <button className="icon-btn" aria-label="Mes siguiente" onClick={() => setMonth(addMonths(month, 1))}><ChevronRight size={20}/></button>
      </header>
      <div className="month-grid">
        {['L', 'M', 'M', 'J', 'V', 'S', 'D'].map((name, index) => <span className="weekday" key={index}>{name}</span>)}
        {Array.from({length: weekday(days[0])}, (_, index) => <span key={`blank-${index}`}/>)}
        {days.map(value => <button key={value} className="day" aria-pressed={value === day} aria-current={value === today ? 'date' : undefined} onClick={() => onDay(value)}>
          <span>{Number(value.slice(8))}</span>{counts[value] > 0 && <i className="dot confirmed"/>}
        </button>)}
      </div>
    </section>
    <section className="panel">
      <header className="panel-head"><h2>{capitalize(dayLabel(day, zone))}</h2></header>
      <DayBookings key={day} day={day} zone={zone} revision={revision} onOpen={booking => openBooking(booking.id)}/>
      <div className="pad"><button className="secondary" onClick={() => open('booking', {day})}><Plus size={16}/>Nueva reservación</button></div>
    </section>
  </div>;
}
