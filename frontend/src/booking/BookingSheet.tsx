import React, {useEffect, useState} from 'react';
import {CalendarDays, Clock3, MapPin} from 'lucide-react';
import {api} from '../api';
import {useStudio} from '../app/context';
import {DocumentSection} from '../features';
import {fmt} from '../lib/dates';
import {Badge, Modal, money} from '../shared';
import type {Row} from '../shared';

/** Booking detail opened from its own route (#/reserva/:id). */
export function BookingSheet({id, onClose}: {id: number; onClose: () => void}) {
  const {zone, revision, reload, open} = useStudio();
  const [booking, setBooking] = useState<Row | null>(null), [error, setError] = useState('');
  useEffect(() => {
    let active = true;
    Promise.all([api(`/api/bookings/${id}`), api(`/api/bookings/${id}/contract`)])
      .then(([row, contract]) => { if (active) setBooking({...row, contract}); })
      .catch(err => { if (active) setError(`No se pudo abrir la reservación: ${err.message}`); });
    return () => { active = false; };
  }, [id, revision]);
  return <Modal routed side title={booking ? booking.snapshot.name : 'Reservación'} subtitle={`Reservación #${id}`} onClose={onClose}>
    <div className="sheet-body stack">
      {error && <div className="error" role="alert">{error}</div>}
      {booking && <>
        <Badge status={booking.status}/>
        <p><CalendarDays size={18}/> {fmt(booking.starts_at, zone, 'EEEE d MMMM yyyy')}</p>
        <p><Clock3 size={18}/> {fmt(booking.starts_at, zone, 'HH:mm')} – {fmt(booking.ends_at, zone, 'HH:mm')}</p>
        <p><MapPin size={18}/> {booking.location || 'Lugar por acordar'}</p>
        <p>{money(booking.snapshot.price, booking.snapshot.currency)}</p>
        <DocumentSection bookingId={id} zone={zone} onChanged={reload}/>
      </>}
    </div>
    {booking && <footer className="modal-footer">
      {booking.status === 'pending_approval' && <button className="primary" onClick={() => open('approve', booking)}>Aprobar</button>}
      {['pending_approval', 'confirmed'].includes(booking.status) && <>
        <button className="secondary" onClick={() => open('reschedule', booking)}>Reprogramar</button>
        <button className="danger-btn" onClick={() => open('cancel', booking)}>Cancelar</button>
      </>}
    </footer>}
  </Modal>;
}
