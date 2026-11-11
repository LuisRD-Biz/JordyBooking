import React, {useEffect, useRef, useState} from 'react';
import {api} from '../api';
import {useStudio} from '../app/context';
import {fmt, localInput, toUtc} from '../lib/dates';
import {Editor, money} from '../shared';
import type {Row} from '../shared';
import {qs} from '../ui/lists';

const BLANK = {name: '', phone: '', email: '', notes: '', featured: false};

/** Pick an existing contact or capture a new one, warning about likely duplicates. */
export function ContactPicker({value, onChange, locked = false, existingOnly = false}: {value: Row; onChange: (value: Row) => void; locked?: boolean; existingOnly?: boolean}) {
  const [mode, setMode] = useState(value.customer_id || existingOnly ? 'existing' : 'new');
  const [query, setQuery] = useState(''), [results, setResults] = useState<Row[]>([]), [error, setError] = useState('');
  const term = mode === 'existing' ? query : JSON.stringify([value.new_customer?.phone, value.new_customer?.email]);
  useEffect(() => {
    let active = true;
    const timer = window.setTimeout(() => {
      setError('');
      if (mode === 'existing' && query.length < 3) { setResults([]); return; }
      const endpoint = mode === 'existing'
        ? `/api/search/customers?q=${encodeURIComponent(query)}&page_size=8`
        : `/api/search/contact-matches?${qs({phone: value.new_customer?.phone, email: value.new_customer?.email})}`;
      api(endpoint).then(found => { if (active) setResults(Array.isArray(found) ? found : found.items); }).catch(err => { if (active) setError(err.message); });
    }, 250);
    return () => { active = false; window.clearTimeout(timer); };
  }, [term, mode]);
  const change = (key: string, input: any) => onChange({new_customer: {...value.new_customer, [key]: input}});
  const modes = [['existing', 'Cliente existente'], ['new', 'Cliente nuevo']].filter(([id]) => !existingOnly || id === 'existing');

  return <fieldset className="group">
    <legend>Cliente</legend>
    {!locked && modes.length > 1 && <div className="segmented" role="group" aria-label="Tipo de cliente">
      {modes.map(([id, label]) => <button type="button" key={id} aria-pressed={mode === id} onClick={() => { setMode(id); setResults([]); onChange(id === 'existing' ? {} : {new_customer: BLANK}); }}>{label}</button>)}
    </div>}
    {mode === 'existing' ? <>
      {value.customer_id
        ? <div className="success">{value.customer_name || `Contacto #${value.customer_id}`}{!locked && <button type="button" className="text-btn" onClick={() => { onChange({}); setQuery(''); }}>Cambiar</button>}</div>
        : <label className="field"><span>Buscar por nombre, teléfono o correo</span><input type="search" value={query} onChange={event => setQuery(event.target.value)} placeholder="Escribe al menos 3 caracteres"/></label>}
    </> : <>
      <label className="field"><span>Nombre<b aria-hidden="true"> *</b></span><input required value={value.new_customer?.name || ''} onChange={event => change('name', event.target.value)} maxLength={200} autoComplete="off"/></label>
      <label className="field"><span>Teléfono<b aria-hidden="true"> *</b></span><input required type="tel" inputMode="tel" minLength={7} maxLength={40} value={value.new_customer?.phone || ''} onChange={event => change('phone', event.target.value)} autoComplete="off"/></label>
      <label className="field"><span>Correo</span><input type="email" inputMode="email" value={value.new_customer?.email || ''} onChange={event => change('email', event.target.value)} autoComplete="off"/></label>
    </>}
    {results.length > 0 && !locked && !value.customer_id && <div className="matches">
      <strong>{mode === 'existing' ? 'Coincidencias' : 'Ya hay contactos con esos datos. ¿Es alguno de ellos?'}</strong>
      {results.map(c => <button key={c.id} type="button" className="secondary" onClick={() => { setMode('existing'); setResults([]); setQuery(''); onChange({customer_id: c.id, customer_name: c.name}); }}>{c.name} · {c.phone || c.email || c.contact}</button>)}
      {mode !== 'existing' && <label className="check-label"><input type="checkbox" checked={value.new_customer?.duplicate_ack || false} onChange={event => change('duplicate_ack', event.target.checked)}/>Es otra persona: crear un contacto nuevo.</label>}
    </div>}
    {error && <div className="error" role="alert">{error}</div>}
  </fieldset>;
}

export function contactPayload(value: Row) {
  if (value.customer_id) return {customer_id: Number(value.customer_id)};
  const customer = value.new_customer;
  if (!customer?.name || !customer?.phone) throw new Error('Elige un cliente o captura su nombre y teléfono.');
  return {new_customer: {...customer, email: customer.email || null}};
}

/** New booking request. It does not hold resources until it is approved. */
export function BookingForm({initial = {}, onClose, onSaved}: {initial?: Row; onClose: () => void; onSaved: () => void}) {
  const {packages, zone} = useStudio();
  const [contact, setContact] = useState<Row>(initial.customer_id ? {customer_id: initial.customer_id, customer_name: initial.customer_name} : {new_customer: BLANK});
  const key = useRef(crypto.randomUUID());
  return <Editor title={initial.quote_id ? 'Solicitud desde cotización' : 'Nueva reservación'} subtitle="Queda por aprobar: no aparta personal ni equipo hasta que la apruebes." saveLabel="Crear solicitud" onClose={onClose}
    fields={[
      {name: 'package_id', label: 'Paquete', type: 'select', value: initial.package_id, options: packages.map(p => ({value: p.id, label: `${p.name} · ${money(p.price, p.currency)}`}))},
      {name: 'starts_at', label: 'Fecha y hora', type: 'datetime-local', value: initial.starts_at ? localInput(initial.starts_at, zone) : undefined, hint: `Hora del estudio (${zone.split('/').pop()?.replaceAll('_', ' ')}).`},
      {name: 'location', label: 'Lugar', required: false, hint: 'Puedes acordarlo después.'},
    ]}
    onSave={async data => {
      if (initial.quote_id && Number(data.package_id) !== initial.package_id) throw new Error('Conserva el paquete de la cotización elegida.');
      await api('/api/bookings', 'POST', {
        ...contactPayload(contact), package_id: Number(data.package_id), starts_at: toUtc(String(data.starts_at), zone),
        location: data.location || null, ...(initial.quote_id ? {quote_id: initial.quote_id} : {}),
      }, {'Idempotency-Key': key.current});
      onClose();
      onSaved();
    }}>
    <ContactPicker value={contact} onChange={setContact} locked={!!initial.quote_id}/>
    {initial.quote_snapshot && <div className="success">Cotización elegida: {money(initial.quote_snapshot.price, initial.quote_snapshot.currency)}. Se conserva este precio aunque el catálogo cambie.</div>}
  </Editor>;
}

/** Meeting or contract signing. A signing is always tied to one of the client's bookings. */
export function AppointmentForm({booking, day, onClose, onSaved}: {booking?: Row; day: string; onClose: () => void; onSaved: () => void}) {
  const {zone} = useStudio();
  const [contact, setContact] = useState<Row>(booking ? {customer_id: booking.customer_id, customer_name: booking.customer_name} : {});
  const [bookings, setBookings] = useState<Row[]>([]);
  useEffect(() => {
    setBookings([]);
    if (booking || !contact.customer_id) return;
    let active = true;
    api(`/api/search/bookings?customer_id=${contact.customer_id}&upcoming=true&page_size=20`)
      .then(page => { if (active) setBookings(page.items.filter((b: Row) => ['pending_approval', 'confirmed'].includes(b.status))); })
      .catch(() => undefined);
    return () => { active = false; };
  }, [contact.customer_id]);
  return <Editor title={booking ? 'Cita para esta reservación' : 'Nueva cita o firma'} subtitle="Queda en el calendario del estudio. Si ocupa a una persona, registra además un bloqueo." saveLabel="Programar" onClose={onClose}
    fields={[]}
    onSave={async data => {
      if (!contact.customer_id) throw new Error('Elige un cliente existente.');
      const linked = booking?.id || Number(data.booking_id) || null;
      if (data.kind === 'contract' && !linked) throw new Error('La firma de contrato necesita una reservación del cliente.');
      await api('/api/appointments', 'POST', {
        customer_id: contact.customer_id, booking_id: linked, kind: data.kind, location: data.location, notes: data.notes || '',
        starts_at: toUtc(String(data.starts_at), zone), ends_at: toUtc(String(data.ends_at), zone),
      });
      onClose();
      onSaved();
    }}>
    <ContactPicker value={contact} onChange={setContact} locked={!!booking} existingOnly/>
    {!booking && bookings.length > 0 && <label className="field"><span>Reservación vinculada</span>
      <select name="booking_id" defaultValue=""><option value="">Ninguna</option>{bookings.map(b => <option key={b.id} value={b.id}>{b.snapshot.name} · {fmt(b.starts_at, zone, 'd MMM yyyy')}</option>)}</select>
    </label>}
    <label className="field"><span>Motivo</span>
      <select name="kind" defaultValue={booking ? 'contract' : 'meeting'}><option value="meeting">Reunión</option><option value="contract">Firma de contrato</option></select>
    </label>
    <label className="field"><span>Inicio<b aria-hidden="true"> *</b></span><input name="starts_at" type="datetime-local" required defaultValue={`${day}T10:00`}/></label>
    <label className="field"><span>Fin<b aria-hidden="true"> *</b></span><input name="ends_at" type="datetime-local" required defaultValue={`${day}T11:00`}/></label>
    <label className="field"><span>Lugar<b aria-hidden="true"> *</b></span><input name="location" required maxLength={500}/></label>
    <label className="field"><span>Observaciones</span><textarea name="notes" maxLength={2000} rows={2}/></label>
  </Editor>;
}
