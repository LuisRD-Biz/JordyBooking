import React from 'react';
import {FileCheck2} from 'lucide-react';
import {useStudio} from '../app/context';
import {DocumentSection} from '../features';
import type {Row} from '../shared';

/** Contract record and private files of a booking. */
export function ContractTab({booking, contract}: {booking: Row; contract: Row | null}) {
  const {zone, reload, open} = useStudio();
  return <div className="stack">
    {booking.kind === 'event' && <div className="note">
      <FileCheck2 size={18}/>
      <span>{contract ? `Contrato registrado: ${contract.reference}` : 'Este evento necesita un contrato firmado antes de confirmarse.'}</span>
    </div>}
    {booking.kind === 'event' && (contract || booking.status === 'pending_approval') && <button className="secondary" onClick={() => open('contract', {...booking, contract})}>
      {contract ? 'Vincular documento al contrato' : 'Registrar contrato'}
    </button>}
    <DocumentSection bookingId={booking.id} zone={zone} onChanged={reload}/>
  </div>;
}
