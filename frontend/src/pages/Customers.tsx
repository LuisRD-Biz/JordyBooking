import React, {useEffect, useState} from 'react';
import {CalendarPlus, Mail, Pencil, Phone, Plus, Star, Users} from 'lucide-react';
import {api} from '../api';
import {useStudio} from '../app/context';
import {capitalize, fmt} from '../lib/dates';
import {Badge, Editor, Empty, Modal} from '../shared';
import type {Row} from '../shared';
import {Chips, ListError, Pager, RowCard, SearchBox, usePage} from '../ui/lists';

type Group = 'contracted' | 'all' | 'prospect' | 'recurrent' | 'featured';
const GROUPS: {value: Group; label: string}[] = [
  {value: 'contracted', label: 'Con contrataciones'},
  {value: 'all', label: 'Todos'},
  {value: 'prospect', label: 'Interesados'},
  {value: 'recurrent', label: 'Recurrentes'},
  {value: 'featured', label: 'Destacados'},
];
const CATEGORY: Record<string, string> = {prospect: 'Interesado', occasional: 'Ocasional', client: 'Cliente', recurrent: 'Recurrente'};

export function Customers() {
  const {zone, revision, open} = useStudio();
  const [group, setGroup] = useState<Group>('contracted'), [text, setText] = useState(''), [page, setPage] = useState(1);
  const [selected, setSelected] = useState<Row | null>(null);
  const {result, error, busy, loaded, retry} = usePage('/api/search/customers', {classification: group, q: text, page}, revision);
  return <section className="panel list">
    <div className="list-controls">
      <SearchBox label="Buscar cliente" placeholder="Nombre, teléfono o correo…" onSearch={value => { setText(value); setPage(1); }}/>
      <button className="primary" onClick={() => open('customer')}><Plus size={16}/>Nuevo cliente</button>
      <Chips label="Grupo de clientes" options={GROUPS} value={group} onChange={value => { setGroup(value); setPage(1); }}/>
    </div>
    <ListError what="los clientes" error={error} retry={retry}/>
    {result.items.length > 0 && <ul className="rows" aria-busy={busy}>
      {result.items.map(c => <RowCard key={c.id} title={<>{c.name}{c.featured && <Star size={14} className="star" aria-label="Destacado"/>}</>}
        subtitle={c.phone || c.email || c.contact}
        meta={<>{c.contracts_count} {c.contracts_count === 1 ? 'contratación' : 'contrataciones'}<small>{c.last_booking ? `Última: ${fmt(c.last_booking, zone, 'd MMM yyyy')}` : 'Sin fechas todavía'}</small></>}
        badge={<span className="tag">{CATEGORY[c.classification]}</span>} onClick={() => setSelected(c)}/>)}
    </ul>}
    {!result.items.length && (loaded ? <Empty icon={Users} title="Sin clientes en esta vista" text="Cambia de grupo o captura al cliente al crear su reservación."/> : !error && <p className="muted pad">Buscando…</p>)}
    <Pager result={result} onPage={setPage}/>
    {selected && <CustomerCard customer={selected} onClose={() => setSelected(null)}/>}
  </section>;
}

function CustomerCard({customer, onClose}: {customer: Row; onClose: () => void}) {
  const {zone, revision, open, openBooking} = useStudio();
  const [bookings, setBookings] = useState<Row[] | null>(null), [error, setError] = useState('');
  useEffect(() => {
    let active = true;
    api(`/api/search/bookings?customer_id=${customer.id}&page_size=100&order=desc`)
      .then(page => { if (active) setBookings(page.items); })
      .catch(err => { if (active) setError(`No se pudo cargar el historial: ${err.message}`); });
    return () => { active = false; };
  }, [customer.id, revision]);
  const now = Date.now();
  const open_ = (b: Row) => ['pending_approval', 'confirmed'].includes(b.status) && new Date(b.ends_at).getTime() >= now;
  const upcoming = (bookings || []).filter(open_).reverse(), past = (bookings || []).filter(b => !open_(b));
  const list = (rows: Row[]) => <ul className="rows inset">
    {rows.map(b => <RowCard key={b.id} title={b.snapshot.name} subtitle={capitalize(fmt(b.starts_at, zone, 'EEE d MMM yyyy, HH:mm'))} badge={<Badge status={b.status}/>} onClick={() => openBooking(b.id)}/>)}
  </ul>;
  return <Modal side title={customer.name} subtitle={`${CATEGORY[customer.classification]} · ${customer.contracts_count} ${customer.contracts_count === 1 ? 'contratación' : 'contrataciones'}`} onClose={onClose}>
    <div className="sheet-body stack">
      <div className="row">
        {customer.phone && <a className="secondary grow" href={`tel:${customer.phone.replace(/[^\d+]/g, '')}`}><Phone size={16}/>Llamar</a>}
        {customer.email && <a className="secondary grow" href={`mailto:${customer.email}`}><Mail size={16}/>Correo</a>}
      </div>
      <dl>
        {customer.phone && <><dt>Teléfono</dt><dd>{customer.phone}</dd></>}
        {customer.email && <><dt>Correo</dt><dd>{customer.email}</dd></>}
        {customer.contact && customer.contact !== customer.phone && customer.contact !== customer.email && <><dt>Otro contacto</dt><dd>{customer.contact}</dd></>}
        {customer.created_at && <><dt>Registro</dt><dd>{fmt(customer.created_at, zone, 'd MMM yyyy')}</dd></>}
      </dl>
      {customer.notes && <div><h3>Notas del cliente</h3><p className="prewrap muted">{customer.notes}</p></div>}
      {error && <div className="error" role="alert">{error}</div>}
      <h3>Próximas fechas</h3>
      {bookings === null && !error ? <p className="muted">Cargando…</p> : upcoming.length ? list(upcoming) : <p className="muted">No tiene fechas próximas.</p>}
      <h3>Historial</h3>
      {past.length ? list(past) : bookings !== null && <p className="muted">Aún no hay historial.</p>}
    </div>
    <footer className="modal-footer">
      <button className="secondary" onClick={() => open('customer', customer)}><Pencil size={16}/>Editar</button>
      <button className="primary" onClick={() => open('booking', {customer_id: customer.id, customer_name: customer.name})}><CalendarPlus size={16}/>Nueva reservación</button>
    </footer>
  </Modal>;
}

export function CustomerEditor({customer, onClose, onSaved}: {customer?: Row; onClose: () => void; onSaved: () => void}) {
  const [ack, setAck] = useState(false), [featured, setFeatured] = useState(!!customer?.featured);
  return <Editor title={customer ? 'Editar cliente' : 'Nuevo cliente'} onClose={onClose}
    fields={[
      {name: 'name', label: 'Nombre', value: customer?.name},
      {name: 'phone', label: 'Teléfono', type: 'tel', required: false, value: customer?.phone},
      {name: 'email', label: 'Correo', type: 'email', required: false, value: customer?.email},
      {name: 'contact', label: 'Otro contacto', required: false, value: customer?.contact, hint: 'Instagram, un segundo teléfono…'},
      {name: 'notes', label: 'Notas del cliente', type: 'textarea', required: false, value: customer?.notes},
    ]}
    onSave={async data => {
      if (!data.phone && !data.email && !data.contact) throw new Error('Indica al menos un teléfono, un correo u otro contacto.');
      await api(`/api/customers${customer ? `/${customer.id}` : ''}`, customer ? 'PUT' : 'POST', {...data, phone: data.phone || null, email: data.email || null, featured, duplicate_ack: ack});
      onClose();
      onSaved();
    }}>
    <label className="check-label"><input type="checkbox" checked={featured} onChange={event => setFeatured(event.target.checked)}/>Marcar como destacado</label>
    <label className="check-label"><input type="checkbox" checked={ack} onChange={event => setAck(event.target.checked)}/>Si coincide con otro contacto, es una persona distinta.</label>
  </Editor>;
}
