import React, {useState} from 'react';
import {Ban, CalendarPlus, ChevronRight, FileCheck2, UserPlus} from 'lucide-react';
import {api} from '../api';
import {AppointmentDetail, BlockDetail} from '../calendar/EventDetails';
import type {AgendaItem} from '../calendar/agenda';
import {AppointmentForm, BookingForm, CustomerEditor} from '../features';
import {capitalize, dayLabel, localInput, toUtc} from '../lib/dates';
import {Editor, Modal, PackageEditor, ResourceEditor} from '../shared';
import type {Row} from '../shared';
import {useStudio} from './context';
import type {Dialog} from './context';

/** The "+" selector: what to create, and for which day. */
function CreateMenu({initialDay, onClose}: {initialDay: string; onClose: () => void}) {
  const {zone, today, open} = useStudio();
  const [day, setDay] = useState(initialDay);
  const options = [
    {type: 'booking', icon: CalendarPlus, title: 'Reservación', text: 'Sesión o evento con un paquete'},
    {type: 'appointment', icon: FileCheck2, title: 'Cita o firma', text: 'Reunión o firma de contrato'},
    {type: 'block', icon: Ban, title: 'Bloqueo', text: 'Aparta el tiempo de una persona o equipo'},
    {type: 'customer', icon: UserPlus, title: 'Cliente', text: 'Registra un contacto nuevo'},
  ];
  return <Modal title="Nuevo" subtitle={`Para el ${dayLabel(day, zone, "EEEE d 'de' MMMM")}`} onClose={onClose}>
    <div className="sheet-body stack">
      <label className="field"><span>Fecha</span><input type="date" value={day} min={today} onChange={e => e.target.value && setDay(e.target.value)}/></label>
      <div className="link-list">
        {options.map(option => <button key={option.type} onClick={() => open(option.type, {day})}>
          <option.icon size={20}/><span><strong>{option.title}</strong><small>{option.text}</small></span><ChevronRight size={18} aria-hidden="true"/>
        </button>)}
      </div>
    </div>
  </Modal>;
}

function Availability({day, onClose}: {day: string; onClose: () => void}) {
  const {packages, zone} = useStudio();
  const [result, setResult] = useState<Row | null>(null);
  return <Editor title="Consultar disponibilidad" subtitle="La consulta no aparta recursos; se vuelve a comprobar al confirmar." saveLabel="Consultar" onClose={onClose}
    fields={[
      {name: 'package_id', label: 'Paquete', type: 'select', options: packages.map(p => ({value: p.id, label: p.name}))},
      {name: 'starts_at', label: 'Fecha y hora', type: 'datetime-local', value: `${day}T10:00`},
    ]}
    onSave={async data => {
      setResult(null);
      setResult(await api('/api/availability', 'POST', {package_id: Number(data.package_id), starts_at: toUtc(String(data.starts_at), zone)}));
    }}>
    {result && <div className={result.available ? 'success' : 'error'} role="status">{result.available ? 'Hay personal y equipo disponibles en ese horario.' : 'No hay suficiente personal o equipo en ese horario.'}</div>}
  </Editor>;
}

/** Date, time and place in one form; only what changed is sent. */
function EditBooking({booking, onClose}: {booking: Row; onClose: () => void}) {
  const {zone, changed} = useStudio();
  const locked = booking.kind === 'event' && !!booking.contract;
  const original = localInput(booking.starts_at, zone);
  const path = `/api/bookings/${booking.id}`;
  return <Editor title="Editar reservación" subtitle={`${booking.customer_name} · ${booking.snapshot.name}`} fields={[]} onClose={onClose}
    onSave={async data => {
      const starts = String(data.starts_at || original), location = String(data.location || '').trim();
      if (!location && booking.location) throw new Error('El lugar no puede quedar vacío una vez acordado.');
      if (starts !== original) await api(`${path}/reschedule`, 'POST', {starts_at: toUtc(starts, zone), ...(location ? {location} : {})});
      else if (location !== (booking.location || '')) await api(`${path}/location`, 'POST', {location});
      onClose();
      changed();
    }}>
    <label className="field"><span>Fecha y hora</span>
      <input name="starts_at" type="datetime-local" defaultValue={original} disabled={locked} required/>
      <small>{locked ? 'Un evento con contrato conserva su fecha hasta revisar el contrato.' : 'Si el nuevo horario no está disponible, la reservación conserva el actual.'}</small>
    </label>
    <label className="field"><span>Lugar</span><input name="location" defaultValue={booking.location || ''} maxLength={500} placeholder="Por acordar"/></label>
    <p className="note">Los acuerdos y observaciones van en la pestaña Notas.</p>
  </Editor>;
}

/** Every dialog that can be opened from more than one screen. */
export function Dialogs({dialog, close}: {dialog: Dialog | null; close: () => void}) {
  const {zone, today, selectedDay, packages, resources, changed} = useStudio();
  if (!dialog) return null;
  const row = dialog.row;
  // New records start from the selected day; a day already gone falls back to today.
  const day: string = row?.day || (selectedDay < today ? today : selectedDay);
  const save = async (path: string, method = 'POST', body?: Row) => {
    await api(path, method, body);
    close();
    changed();
  };
  const when = `${capitalize(dayLabel(day, zone))} · hora del estudio`;

  switch (dialog.type) {
    case 'create':
      return <CreateMenu initialDay={day} onClose={close}/>;
    case 'booking':
      return <BookingForm packages={packages} zone={zone} initial={row?.starts_at || row?.quote_id ? row : {...row, starts_at: toUtc(`${day}T10:00`, zone)}} onClose={close} onSaved={() => changed('Solicitud creada')}/>;
    case 'appointment':
      return <AppointmentForm booking={row?.id ? row : undefined} day={day} zone={zone} onClose={close} onSaved={() => changed('Cita programada')}/>;
    case 'customer':
      return <CustomerEditor customer={row?.id ? row : undefined} onClose={close} onSaved={() => changed()}/>;
    case 'event-appointment':
      return <AppointmentDetail item={row as AgendaItem} onClose={close}/>;
    case 'event-block':
      return <BlockDetail item={row as AgendaItem} onClose={close}/>;
    case 'availability':
      return <Availability day={day} onClose={close}/>;
    case 'resource':
      return <ResourceEditor existing={row} resources={resources} onClose={close} onSave={data => save(`/api/resources${row ? `/${row.id}` : ''}`, row ? 'PUT' : 'POST', data)}/>;
    case 'package':
      return <PackageEditor existing={row} resources={resources} onClose={close} onSave={data => save(`/api/packages${row ? `/${row.id}` : ''}`, row ? 'PUT' : 'POST', data)}/>;
    case 'block':
      return <Editor title="Bloquear un horario" subtitle={when} onClose={close} saveLabel="Bloquear"
        fields={[
          {name: 'resource_id', label: 'Persona o equipo', type: 'select', value: row?.resource_id, options: resources.map(r => ({value: r.id, label: r.name}))},
          {name: 'starts_at', label: 'Inicio', type: 'datetime-local', value: `${day}T10:00`},
          {name: 'ends_at', label: 'Fin', type: 'datetime-local', value: `${day}T12:00`},
          {name: 'reason', label: 'Motivo'},
        ]}
        onSave={data => save('/api/blocks', 'POST', {...data, resource_id: Number(data.resource_id), starts_at: toUtc(String(data.starts_at), zone), ends_at: toUtc(String(data.ends_at), zone)})}/>;
    case 'release':
      return <Editor title="Liberar horario" subtitle="La persona o el equipo volverá a estar disponible en este horario." fields={[]} saveLabel="Liberar" onClose={close} onSave={() => save(`/api/blocks/${row!.id}/release`)}/>;
    case 'edit':
      return <EditBooking booking={row!} onClose={close}/>;
    case 'approve':
      return <Editor title="Aprobar reservación" subtitle="Se comprueba la disponibilidad y se asigna al personal y equipo." saveLabel="Confirmar reservación" onClose={close}
        fields={[{name: 'location', label: 'Lugar acordado', value: row?.location}]}
        onSave={data => save(`/api/bookings/${row!.id}/approve`, 'POST', data)}/>;
    case 'reschedule':
      return <Editor title="Reprogramar" subtitle="Si el nuevo horario no está disponible, la reservación conserva su fecha actual." saveLabel="Reprogramar" onClose={close}
        fields={[
          {name: 'starts_at', label: 'Nueva fecha y hora', type: 'datetime-local', value: localInput(row!.starts_at, zone)},
          {name: 'location', label: 'Lugar', value: row?.location, required: false, hint: 'Déjalo vacío para conservar el actual.'},
        ]}
        onSave={data => save(`/api/bookings/${row!.id}/reschedule`, 'POST', {starts_at: toUtc(String(data.starts_at), zone), ...(String(data.location || '').trim() ? {location: data.location} : {})})}/>;
    case 'cancel':
      return <Editor title="Cancelar reservación" subtitle="Se libera al personal y al equipo. El registro permanece en el historial." fields={[]} saveLabel="Sí, cancelar" danger onClose={close} onSave={() => save(`/api/bookings/${row!.id}/cancel`)}/>;
    case 'complete':
      return <Editor title="Marcar como completada" subtitle="Confirma que el servicio ya terminó." fields={[]} saveLabel="Completar" onClose={close} onSave={() => save(`/api/bookings/${row!.id}/complete`)}/>;
    default:
      return null;
  }
}
