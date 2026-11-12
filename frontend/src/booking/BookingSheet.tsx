import React, {useEffect, useState} from 'react';
import {AlertCircle, CalendarClock, CalendarDays, Check, CheckCheck, Clock3, FileCheck2, Mail, MapPin, Pencil, Phone, Plus, X} from 'lucide-react';
import {api} from '../api';
import {useStudio} from '../app/context';
import {capitalize, fmt} from '../lib/dates';
import {Badge, Modal, money, roles} from '../shared';
import type {Row} from '../shared';
import {ContractTab} from './ContractTab';
import {Notes} from './Notes';

type Tab = 'resumen' | 'notas' | 'contrato' | 'citas';
const APPOINTMENT_STATUS: Record<string, string> = {scheduled: 'Agendada', completed: 'Realizada', cancelled: 'Cancelada'};

/**
 * Everything about one booking, opened from its own route (#/reserva/:id): a bottom sheet on
 * phones and a side panel on desktop. The next action for its status stays fixed at the foot.
 */
export function BookingSheet({id, onClose}: {id: number; onClose: () => void}) {
  const {zone, revision, open} = useStudio();
  const [summary, setSummary] = useState<Row | null>(null), [error, setError] = useState('');
  const [tab, setTab] = useState<Tab>('resumen'), [noteCount, setNoteCount] = useState<number | null>(null);

  useEffect(() => {
    let active = true;
    api<Row>(`/api/bookings/${id}/summary`)
      .then(result => { if (active) { setSummary(result); setError(''); } })
      // A failed refresh keeps the booking that was already on screen.
      .catch(err => { if (active) setError(`No se pudo ${summary ? 'actualizar' : 'abrir'} la reservación: ${err.message}`); });
    return () => { active = false; };
  }, [id, revision]);

  const booking: Row | undefined = summary?.booking, customer: Row | undefined = summary?.customer;
  const contract: Row | null = summary?.contract || null;
  // What dialogs opened from here need to know about the booking.
  const row = booking && {...booking, customer_name: customer!.name, contract};
  const notes = noteCount ?? summary?.counts.notes ?? 0;
  const tabs: {id: Tab; label: string; count?: number}[] = [
    {id: 'resumen', label: 'Resumen'},
    {id: 'notas', label: 'Notas', count: notes},
    {id: 'contrato', label: 'Contrato', count: summary?.counts.documents},
    {id: 'citas', label: 'Citas', count: summary?.appointments.length},
  ];

  return <Modal routed side title={customer?.name || 'Reservación'} subtitle={booking ? `${booking.snapshot.name} · Reservación #${id}` : `Reservación #${id}`} onClose={onClose}>
    <div className="sheet-body flush">
      {error && <div className="error" role="alert"><AlertCircle size={18}/>{error}</div>}
      {!summary && !error && <p className="muted pad">Abriendo la reservación…</p>}
      {booking && customer && <>
        <section className="sheet-summary">
          <div className="row"><Badge status={booking.status}/><span className="tag">{booking.kind === 'event' ? 'Evento' : 'Sesión'}</span></div>
          <ul className="facts">
            <li><CalendarDays size={18}/>{capitalize(fmt(booking.starts_at, zone, "EEEE d 'de' MMMM yyyy"))}</li>
            <li><Clock3 size={18}/>{fmt(booking.starts_at, zone, 'HH:mm')} – {fmt(booking.ends_at, zone, 'HH:mm')}</li>
            <li><MapPin size={18}/>{booking.location || 'Lugar por acordar'}</li>
          </ul>
          {(customer.phone || customer.email) && <div className="row">
            {customer.phone && <a className="secondary" href={`tel:${customer.phone.replace(/[^\d+]/g, '')}`}><Phone size={16}/>Llamar</a>}
            {customer.email && <a className="secondary" href={`mailto:${customer.email}`}><Mail size={16}/>Correo</a>}
          </div>}
        </section>
        <div className="tabbar" role="tablist" aria-label="Secciones de la reservación">
          {tabs.map(entry => <button key={entry.id} type="button" role="tab" id={`tab-${entry.id}`} aria-selected={tab === entry.id} aria-controls="booking-panel" onClick={() => setTab(entry.id)}>
            {entry.label}{!!entry.count && <b>{entry.count}</b>}
          </button>)}
        </div>
        <div className="tabpanel" role="tabpanel" id="booking-panel" aria-labelledby={`tab-${tab}`}>
          {tab === 'resumen' && <div className="stack">
            <dl>
              <dt>Precio acordado</dt><dd>{money(booking.snapshot.price, booking.snapshot.currency)} {booking.snapshot.currency}</dd>
              <dt>Duración</dt><dd>{booking.snapshot.duration_minutes} min</dd>
              <dt>Condiciones</dt><dd className="prewrap">{booking.snapshot.terms || 'Sin condiciones adicionales'}</dd>
              <dt>Contacto</dt><dd>{[customer.phone, customer.email].filter(Boolean).join(' · ') || customer.contact || 'Sin datos de contacto'}</dd>
            </dl>
            <h3>Personal y equipo asignado</h3>
            {summary!.assignments.length
              ? <div className="chips">{summary!.assignments.map((a: Row) => <span key={a.resource_id}>{a.resource_name} · {roles[a.capability] || a.capability}</span>)}</div>
              : <p className="muted">{booking.status === 'pending_approval' ? 'Se asigna al aprobar la reservación.' : 'Sin asignaciones activas.'}</p>}
          </div>}
          {tab === 'notas' && <Notes bookingId={id} onCount={setNoteCount}/>}
          {tab === 'contrato' && <ContractTab booking={booking} contract={contract}/>}
          {tab === 'citas' && <div className="stack">
            {summary!.appointments.length
              ? <ul className="plain-list">{summary!.appointments.map((a: Row) => <li key={a.id}>
                  <strong>{a.kind === 'contract' ? 'Firma de contrato' : 'Reunión'}</strong>
                  <span>{capitalize(fmt(a.starts_at, zone, 'EEE d MMM, HH:mm'))} – {fmt(a.ends_at, zone, 'HH:mm')} · {a.location}</span>
                  <Badge status={a.status} label={APPOINTMENT_STATUS[a.status]}/>
                </li>)}</ul>
              : <p className="muted">Sin citas para esta reservación.</p>}
            <button className="secondary" onClick={() => open('appointment', row)}><Plus size={16}/>Programar cita o firma</button>
          </div>}
        </div>
      </>}
    </div>
    {row && <ActionBar booking={row} onContract={() => setTab('contrato')}/>}
  </Modal>;
}

/** The action that moves the booking forward, plus edit, reschedule and cancel while it is open. */
function ActionBar({booking, onContract}: {booking: Row; onContract: () => void}) {
  const {open} = useStudio();
  const pending = booking.status === 'pending_approval';
  if (!pending && booking.status !== 'confirmed') return null;
  const needsContract = pending && booking.kind === 'event' && !booking.contract;
  const finished = new Date(booking.ends_at).getTime() < Date.now();
  // An event with a contract keeps its date until the contract is reviewed.
  const locked = booking.kind === 'event' && !!booking.contract;
  return <footer className="action-bar">
    {needsContract && <button className="primary wide" onClick={onContract}><FileCheck2 size={18}/>Registrar contrato</button>}
    {pending && !needsContract && <button className="confirm wide" onClick={() => open('approve', booking)}><Check size={18}/>Aprobar</button>}
    {!pending && finished && <button className="confirm wide" onClick={() => open('complete', booking)}><CheckCheck size={18}/>Completar</button>}
    <button className="secondary" onClick={() => open('edit', booking)}><Pencil size={16}/>Editar</button>
    <button className="secondary" disabled={locked} title={locked ? 'Un evento con contrato no se reprograma desde aquí' : undefined} onClick={() => open('reschedule', booking)}><CalendarClock size={16}/>Reprogramar</button>
    <button className="danger-btn" onClick={() => open('cancel', booking)}><X size={16}/>Cancelar</button>
  </footer>;
}
