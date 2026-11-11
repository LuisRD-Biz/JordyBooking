import React, {useEffect, useState} from 'react';
import {Activity as ActivityIcon} from 'lucide-react';
import {api} from '../api';
import {useStudio} from '../app/context';
import {fmt} from '../lib/dates';
import {Badge, Empty} from '../shared';
import type {Row} from '../shared';

const ACTIONS: Record<string, string> = {
  'customer.created': 'Cliente registrado', 'customer.updated': 'Cliente actualizado',
  'resource.created': 'Recurso añadido', 'resource.updated': 'Recurso actualizado',
  'package.created': 'Paquete creado', 'package.updated': 'Paquete actualizado',
  'booking.requested': 'Reservación solicitada', 'booking.confirmed': 'Reservación confirmada',
  'booking.cancelled': 'Reservación cancelada', 'booking.completed': 'Reservación completada',
  'booking.rescheduled': 'Reservación reprogramada', 'booking.location_changed': 'Lugar actualizado',
  'booking.note_added': 'Nota agregada', 'contract.recorded': 'Contrato registrado',
  'contract.document_linked': 'Archivo vinculado al contrato', 'document.uploaded': 'Documento adjuntado',
  'block.created': 'Horario bloqueado', 'block.released': 'Horario liberado',
  'lead.created': 'Oportunidad registrada', 'lead.contacted': 'Contacto realizado',
  'lead.lost': 'Oportunidad no concretada', 'lead.reopen': 'Oportunidad reabierta',
  'quote.created': 'Versión de cotización creada', 'appointment.created': 'Cita programada',
  'appointment.completed': 'Cita realizada', 'appointment.cancelled': 'Cita cancelada',
};

/** Who did it: the signed-in account, the desktop's local access, or an automated process. */
export const actorLabel = (actor?: string) =>
  !actor || actor === 'jordy-admin' ? 'Sistema' : actor === 'local' ? 'Acceso local' : actor;

export function Activity() {
  const {zone, revision} = useStudio();
  const [audit, setAudit] = useState<Row[]>([]), [operations, setOperations] = useState<Row[]>([]), [error, setError] = useState('');
  useEffect(() => {
    let active = true;
    Promise.all([api('/api/audit?limit=200'), api('/api/operations?limit=50')])
      .then(([a, o]) => { if (active) { setAudit(a); setOperations(o); setError(''); } })
      // Keep whatever was already on screen.
      .catch(err => { if (active) setError(`No se pudo actualizar la actividad: ${err.message}`); });
    return () => { active = false; };
  }, [revision]);
  return <div className="two-columns">
    <section className="panel">
      <header className="panel-head"><h2>Historial del estudio</h2><p>Últimos 200 movimientos, con quién los hizo.</p></header>
      {error && <div className="error" role="alert">{error}</div>}
      {audit.length ? <ul className="timeline">{audit.map(entry => <li key={entry.id}>
        <strong>{ACTIONS[entry.action] || entry.action}</strong>
        <small>Registro #{entry.entity_id} · {fmt(entry.created_at, zone, 'd MMM, HH:mm')} · {actorLabel(entry.actor)}</small>
      </li>)}</ul> : !error && <Empty icon={ActivityIcon} title="Aún no hay movimientos" text="Cada cambio importante quedará registrado aquí."/>}
    </section>
    <section className="panel">
      <header className="panel-head"><h2>Avisos de reservaciones</h2><p>La sincronización con un calendario externo sigue pendiente.</p></header>
      {operations.length ? <ul className="timeline">{operations.map(op => <li key={op.id}>
        <strong>Reservación #{op.payload.booking_id} <Badge status={op.status}/></strong>
        <small>{op.attempts} intentos · {fmt(op.available_at, zone, 'd MMM, HH:mm')}</small>
      </li>)}</ul> : <p className="muted pad">Sin avisos pendientes.</p>}
    </section>
  </div>;
}
