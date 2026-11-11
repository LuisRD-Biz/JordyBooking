import React, {useState} from 'react';
import {FileCheck2, Plus} from 'lucide-react';
import {useStudio} from '../app/context';
import type {AgendaItem} from '../calendar/agenda';
import {capitalize, fmt} from '../lib/dates';
import {Badge, Empty} from '../shared';
import type {Row} from '../shared';
import {Chips, ListError, Pager, RowCard, SearchBox, usePage} from '../ui/lists';

type Range = 'all' | 'today' | 'month';
const RANGES: {value: Range; label: string}[] = [{value: 'all', label: 'Todas'}, {value: 'today', label: 'Hoy'}, {value: 'month', label: 'Este mes'}];
const STATUS: Record<string, string> = {scheduled: 'Agendada', completed: 'Realizada', cancelled: 'Cancelada'};
const KIND: Record<string, string> = {contract: 'Firma de contrato', meeting: 'Reunión'};

/** Search across meetings and contract signings; they also appear on the calendar. */
export function Appointments() {
  const {zone, today, revision, open} = useStudio();
  const [range, setRange] = useState<Range>('all'), [text, setText] = useState(''), [page, setPage] = useState(1);
  const dates: Record<Range, Row> = {all: {}, today: {day: today}, month: {month: Number(today.slice(5, 7)), year: Number(today.slice(0, 4))}};
  const {result, error, busy, loaded, retry} = usePage('/api/search/appointments', {...dates[range], q: text, page, order: range === 'all' ? 'desc' : 'asc'}, revision);
  const asItem = (a: Row): AgendaItem => ({type: 'appointment', id: a.id, starts_at: a.starts_at, ends_at: a.ends_at, title: a.customer_name, subtitle: KIND[a.kind], status: a.status, kind: a.kind, customer_id: a.customer_id, booking_id: a.booking_id, resource_id: null, location: a.location});
  return <section className="panel list">
    <div className="list-controls">
      <SearchBox label="Buscar cita" placeholder="Nombre del cliente…" onSearch={value => { setText(value); setPage(1); }}/>
      <button className="primary" onClick={() => open('appointment')}><Plus size={16}/>Nueva cita</button>
      <Chips label="Periodo" options={RANGES} value={range} onChange={value => { setRange(value); setPage(1); }}/>
    </div>
    <ListError what="las citas" error={error} retry={retry}/>
    {result.items.length > 0 && <ul className="rows" aria-busy={busy}>
      {result.items.map(a => <RowCard key={a.id} title={a.customer_name} subtitle={KIND[a.kind]}
        meta={<>{capitalize(fmt(a.starts_at, zone, 'EEE d MMM yyyy, HH:mm'))}<small>{a.location}</small></>}
        badge={<Badge status={a.status} label={STATUS[a.status]}/>} onClick={() => open('event-appointment', asItem(a))}/>)}
    </ul>}
    {!result.items.length && (loaded ? <Empty icon={FileCheck2} title="Sin citas en este periodo" text="Las firmas de contrato también se programan desde la reservación."/> : !error && <p className="muted pad">Buscando…</p>)}
    <Pager result={result} onPage={setPage}/>
  </section>;
}
