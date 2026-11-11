import React, {useState} from 'react';
import {SlidersHorizontal} from 'lucide-react';
import {useStudio} from '../app/context';
import {capitalize, fmt} from '../lib/dates';
import {Badge, Editor, Empty} from '../shared';
import type {Row} from '../shared';
import {Chips, ListError, Pager, RowCard, SearchBox, usePage} from '../ui/lists';

type Quick = 'all' | 'pending' | 'confirmed' | 'month' | 'contract';
const QUICK: {value: Quick; label: string}[] = [
  {value: 'all', label: 'Todas'},
  {value: 'pending', label: 'Por aprobar'},
  {value: 'confirmed', label: 'Confirmadas'},
  {value: 'month', label: 'Este mes'},
  {value: 'contract', label: 'Con contrato'},
];

/** Find any booking: a search box, quick chips and the rarely used filters in a sheet. */
export function Bookings({initial = 'all'}: {initial?: Quick}) {
  const {zone, today, revision, openBooking} = useStudio();
  const [quick, setQuick] = useState<Quick>(initial), [text, setText] = useState(''), [page, setPage] = useState(1);
  const [advanced, setAdvanced] = useState<Row>({}), [filtering, setFiltering] = useState(false);
  const quickParams: Record<Quick, Row> = {
    all: {}, pending: {status: 'pending_approval'}, confirmed: {status: 'confirmed', upcoming: true},
    month: {month: Number(today.slice(5, 7)), year: Number(today.slice(0, 4))}, contract: {has_contract: true},
  };
  // "Este mes" is itself a date filter, so it replaces the range chosen in the sheet.
  const {date_from, date_to, ...rest} = advanced;
  const params = {...rest, ...(quick === 'month' ? {} : {date_from, date_to}), ...quickParams[quick], q: text, page};
  const {result, error, busy, loaded, retry} = usePage('/api/search/bookings', params, revision);
  const active = Object.values(advanced).filter(Boolean).length;
  const reset = () => setPage(1);

  return <section className="panel list">
    <div className="list-controls">
      <SearchBox label="Buscar reservación" placeholder="Cliente o servicio…" onSearch={value => { setText(value); reset(); }}/>
      <button className="secondary" onClick={() => setFiltering(true)}><SlidersHorizontal size={16}/>Filtros{active > 0 && <b>{active}</b>}</button>
      <Chips label="Filtro rápido" options={QUICK} value={quick} onChange={value => { setQuick(value); reset(); }}/>
    </div>
    <ListError what="las reservaciones" error={error} retry={retry}/>
    {result.items.length > 0 && <ul className="rows" aria-busy={busy}>
      {result.items.map(b => <RowCard key={b.id} title={b.customer_name} subtitle={b.snapshot.name}
        meta={<>{capitalize(fmt(b.starts_at, zone, 'EEE d MMM yyyy, HH:mm'))}<small>{b.location || 'Lugar por acordar'}</small></>}
        badge={<Badge status={b.status}/>} onClick={() => openBooking(b.id)}/>)}
    </ul>}
    {!result.items.length && (loaded ? <Empty title="Sin coincidencias" text="Prueba con otro nombre, otro filtro o un rango de fechas distinto."/> : !error && <p className="muted pad">Buscando…</p>)}
    <Pager result={result} onPage={setPage}/>
    {filtering && <Editor title="Filtros" saveLabel="Aplicar" onClose={() => setFiltering(false)}
      fields={[
        {name: 'date_from', label: 'Desde', type: 'date', required: false, value: advanced.date_from},
        {name: 'date_to', label: 'Hasta', type: 'date', required: false, value: advanced.date_to},
        {name: 'kind', label: 'Tipo de servicio', type: 'select', required: false, value: advanced.kind, options: [{value: 'event', label: 'Evento'}, {value: 'session', label: 'Sesión'}]},
        {name: 'status', label: 'Estado', type: 'select', required: false, value: advanced.status, hint: 'Los chips «Por aprobar» y «Confirmadas» tienen prioridad.', options: [{value: 'pending_approval', label: 'Por aprobar'}, {value: 'confirmed', label: 'Confirmadas'}, {value: 'completed', label: 'Completadas'}, {value: 'cancelled', label: 'Canceladas'}]},
        {name: 'order', label: 'Orden', type: 'select', required: false, value: advanced.order, options: [{value: 'asc', label: 'Más antiguas primero'}, {value: 'desc', label: 'Más recientes primero'}]},
      ]}
      onSave={data => {
        if (data.date_from && data.date_to && data.date_from > data.date_to) throw new Error('La fecha inicial es posterior a la final.');
        setAdvanced(Object.fromEntries(Object.entries(data).filter(([, value]) => value)));
        reset();
        setFiltering(false);
      }}>
      {active > 0 && <button type="button" className="text-btn" onClick={() => { setAdvanced({}); reset(); setFiltering(false); }}>Quitar todos los filtros</button>}
    </Editor>}
  </section>;
}
