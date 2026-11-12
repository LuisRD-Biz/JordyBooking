import React, {useState} from 'react';
import {AlertCircle, CalendarDays, Clock3, MapPin, User} from 'lucide-react';
import {api} from '../api';
import {useStudio} from '../app/context';
import {capitalize, dayKey, fmt} from '../lib/dates';
import {Badge, Modal} from '../shared';
import type {AgendaItem} from './agenda';

function range(item: AgendaItem, zone: string) {
  const sameDay = dayKey(item.starts_at, zone) === dayKey(new Date(item.ends_at).getTime() - 1, zone);
  return sameDay
    ? `${fmt(item.starts_at, zone, 'HH:mm')} – ${fmt(item.ends_at, zone, 'HH:mm')}`
    : `${fmt(item.starts_at, zone, 'd MMM, HH:mm')} – ${fmt(item.ends_at, zone, 'd MMM, HH:mm')}`;
}

function useAction(onClose: () => void) {
  const {changed} = useStudio();
  const [busy, setBusy] = useState(false), [error, setError] = useState('');
  async function run(path: string, body: unknown, message: string) {
    setBusy(true); setError('');
    try {
      await api(path, 'POST', body);
      onClose();
      changed(message);
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }
  return {busy, error, run};
}

export function AppointmentDetail({item, onClose}: {item: AgendaItem; onClose: () => void}) {
  const {zone, openBooking} = useStudio();
  const {busy, error, run} = useAction(onClose);
  const status = `/api/appointments/${item.id}/status`;
  return <Modal title={item.subtitle} subtitle={item.title} onClose={onClose}>
    <div className="sheet-body stack">
      <Badge status={item.status} label={{scheduled: 'Agendada', completed: 'Realizada', cancelled: 'Cancelada'}[item.status]}/>
      <ul className="facts">
        <li><CalendarDays size={18}/>{capitalize(fmt(item.starts_at, zone, "EEEE d 'de' MMMM yyyy"))}</li>
        <li><Clock3 size={18}/>{range(item, zone)}</li>
        <li><MapPin size={18}/>{item.location}</li>
        <li><User size={18}/>{item.title}</li>
      </ul>
      {item.booking_id && <button className="secondary" onClick={() => openBooking(item.booking_id!)}>Ver la reservación</button>}
      {error && <div className="error" role="alert"><AlertCircle size={18}/>{error}</div>}
    </div>
    {item.status === 'scheduled' && <footer className="modal-footer">
      <button className="danger-btn" disabled={busy} onClick={() => run(status, {status: 'cancelled'}, 'Cita cancelada')}>Cancelar cita</button>
      <button className="confirm" disabled={busy} onClick={() => run(status, {status: 'completed'}, 'Cita realizada')}>Marcar realizada</button>
    </footer>}
  </Modal>;
}

export function BlockDetail({item, onClose}: {item: AgendaItem; onClose: () => void}) {
  const {zone} = useStudio();
  const {busy, error, run} = useAction(onClose);
  return <Modal title="Bloqueo" subtitle={item.title} onClose={onClose}>
    <div className="sheet-body stack">
      <Badge status="block" label={item.kind === 'staff' ? 'Persona' : 'Equipo o set'}/>
      <ul className="facts">
        <li><Clock3 size={18}/>{range(item, zone)}</li>
        <li><User size={18}/>{item.title}</li>
      </ul>
      <p>{item.subtitle}</p>
      {error && <div className="error" role="alert"><AlertCircle size={18}/>{error}</div>}
    </div>
    <footer className="modal-footer">
      <button className="secondary" disabled={busy} onClick={() => run(`/api/blocks/${item.id}/release`, undefined, 'Horario liberado')}>Liberar horario</button>
    </footer>
  </Modal>;
}
