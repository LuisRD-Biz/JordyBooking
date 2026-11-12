import React, {useEffect, useRef, useState} from 'react';
import {AlertCircle, Check, Download, Eye, FileText, Plus, Search, Upload} from 'lucide-react';
import {api} from '../api';
import {useStudio} from '../app/context';
import {fmt, localInput, toUtc} from '../lib/dates';
import {actorLabel} from '../pages/Activity';
import {Editor} from '../shared';
import type {Row} from '../shared';
import {ACCEPT, DOCUMENT_TYPES, fileProblem, uploadDocument} from './documents';

type Stage = 'none' | 'uploaded' | 'signed' | 'linked';
const STAGES: {id: Stage; label: string}[] = [
  {id: 'none', label: 'Sin contrato'},
  {id: 'uploaded', label: 'Archivo subido'},
  {id: 'signed', label: 'Firmado'},
  {id: 'linked', label: 'Vinculado'},
];
const FILTER_FROM = 10; // The search box only earns its place on long lists.

/**
 * One visible state for the contract (no contract → file uploaded → signed → linked) with a
 * single button for the next step, and the booking's private documents underneath.
 * Uploading a PDF never counts as signing: the signature is always registered explicitly.
 */
export function ContractTab({booking, contract}: {booking: Row; contract: Row | null}) {
  const {zone, changed, open} = useStudio();
  const [documents, setDocuments] = useState<Row[]>([]), [total, setTotal] = useState(0), [query, setQuery] = useState('');
  const [limit, setLimit] = useState(0), [version, setVersion] = useState(0);
  const [error, setError] = useState(''), [progress, setProgress] = useState<number | null>(null);
  const [dialog, setDialog] = useState<'sign' | 'link' | 'add' | null>(null), [preview, setPreview] = useState('');
  const picker = useRef<HTMLInputElement>(null);

  useEffect(() => { api('/api/documents/settings').then(result => setLimit(result.max_bytes)).catch(() => undefined); }, []);
  useEffect(() => {
    let active = true;
    api(`/api/bookings/${booking.id}/documents?page_size=100&order=desc${query ? `&q=${encodeURIComponent(query)}` : ''}`)
      .then(result => { if (active) { setDocuments(result.items); if (!query) setTotal(result.total); } })
      .catch(err => { if (active) setError(`No se pudieron cargar los documentos: ${err.message}`); });
    return () => { active = false; };
  }, [booking.id, version, query]);

  const contractFiles = documents.filter(d => d.document_type === 'contract' && d.is_current);
  const linked = contract?.document_id ? documents.find(d => d.id === contract.document_id) : undefined;
  const stage: Stage = contract ? (contract.document_id ? 'linked' : 'signed') : contractFiles.length ? 'uploaded' : 'none';
  const isEvent = booking.kind === 'event', pending = booking.status === 'pending_approval';
  // The signature is registered on events that are still waiting for approval.
  const canSign = isEvent && pending && !contract;
  const refresh = (message?: string) => { setVersion(value => value + 1); changed(message); };

  async function uploadContract(file: File | undefined) {
    if (!file) return;
    const problem = fileProblem(file, limit);
    if (problem) { setError(problem); return; }
    setError(''); setProgress(0);
    try {
      const document = await uploadDocument(booking.id, file, {type: 'contract'}, setProgress);
      // With the signature already on record, the file is what was missing: link it right away.
      if (contract) await api(`/api/bookings/${booking.id}/contract/document`, 'POST', {document_id: document.id});
      refresh(contract ? 'Archivo vinculado al contrato' : 'Contrato subido');
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setProgress(null);
      if (picker.current) picker.current.value = '';
    }
  }

  const busy = progress !== null;
  const choose = () => picker.current?.click();
  const headline: Record<Stage, {title: string; text: string}> = {
    none: {
      title: 'Sin contrato',
      text: isEvent ? 'Este evento necesita un contrato firmado antes de aprobarse. Empieza por subir el archivo.' : 'Las sesiones no requieren contrato. Puedes adjuntar uno si lo necesitas.',
    },
    uploaded: {
      title: 'Archivo subido',
      text: canSign ? 'Subir el archivo no equivale a firmar. Cuando esté firmado, regístralo con su folio y fecha.' : 'El archivo está guardado. La firma solo se registra en eventos que están por aprobar.',
    },
    signed: {title: 'Firmado', text: 'La firma está registrada. Falta vincular el archivo del contrato.'},
    linked: {title: 'Firmado y vinculado', text: pending ? 'El contrato está completo. Ya puedes aprobar la reservación.' : 'El contrato está completo.'},
  };
  const position = STAGES.findIndex(entry => entry.id === stage);

  return <div className="stack">
    <section className={`contract-state ${stage}`} aria-label="Estado del contrato">
      <ol className="steps">
        {STAGES.map((entry, index) => <li key={entry.id} aria-current={index === position ? 'step' : undefined} className={index < position ? 'done' : undefined}>
          <i aria-hidden="true">{index < position ? <Check size={12}/> : index + 1}</i><span>{entry.label}</span>
        </li>)}
      </ol>
      <h3>{headline[stage].title}</h3>
      <p className="muted">{headline[stage].text}</p>
      {contract && <dl>
        <dt>Folio</dt><dd>{contract.reference}</dd>
        <dt>Firmado</dt><dd>{fmt(contract.signed_at, zone, "d 'de' MMMM yyyy, HH:mm")}</dd>
        {linked && <><dt>Archivo</dt><dd><a href={`/api/documents/${linked.id}/download`}>{linked.original_name}</a></dd></>}
      </dl>}
      <input ref={picker} type="file" accept={ACCEPT} hidden onChange={event => uploadContract(event.target.files?.[0])}/>
      {busy && <progress max={100} value={progress!} aria-label="Subiendo archivo"/>}
      {stage === 'none' && <button className="primary" disabled={busy} onClick={choose}><Upload size={16}/>{busy ? `Subiendo ${progress}%` : 'Subir contrato'}</button>}
      {stage === 'none' && canSign && <button className="text-btn" onClick={() => setDialog('sign')}>Ya está firmado en papel: registrar la firma</button>}
      {stage === 'uploaded' && canSign && <button className="confirm" onClick={() => setDialog('sign')}><Check size={16}/>Registrar firma</button>}
      {stage === 'signed' && (contractFiles.length
        ? <button className="primary" onClick={() => setDialog('link')}><FileText size={16}/>Vincular archivo</button>
        : <button className="primary" disabled={busy} onClick={choose}><Upload size={16}/>{busy ? `Subiendo ${progress}%` : 'Subir contrato firmado'}</button>)}
      {stage === 'linked' && pending && <button className="confirm" onClick={() => open('approve', booking)}><Check size={16}/>Aprobar reservación</button>}
    </section>
    {error && <div className="error" role="alert"><AlertCircle size={18}/>{error}</div>}

    <section className="stack">
      <header className="row between">
        <h3>Documentos{total > 0 && ` (${total})`}</h3>
        <button className="secondary" onClick={() => setDialog('add')}><Plus size={16}/>Agregar</button>
      </header>
      {total > FILTER_FROM && <label className="search"><Search size={18}/><input type="search" aria-label="Buscar documento" placeholder="Nombre del archivo…" value={query} onChange={event => setQuery(event.target.value)}/></label>}
      {documents.length ? <ul className="documents">
        {documents.map(d => <li key={d.id}>
          <FileText size={22} aria-hidden="true"/>
          <div>
            <strong>{d.original_name}</strong>
            <small>{DOCUMENT_TYPES[d.document_type]} · v{d.version}{d.is_current ? '' : ' · versión anterior'}{contract?.document_id === d.id ? ' · vinculado al contrato' : ''}</small>
            <small>{fmt(d.created_at, zone, 'd MMM yyyy, HH:mm')} · {actorLabel(d.actor)} · {Math.ceil(d.size / 1024)} KB</small>
            {d.notes && <p>{d.notes}</p>}
          </div>
          {d.mime.startsWith('image/') && <button className="icon-btn" aria-label={`Vista previa de ${d.original_name}`} aria-expanded={preview === d.id} onClick={() => setPreview(preview === d.id ? '' : d.id)}><Eye size={20}/></button>}
          <a className="icon-btn" href={`/api/documents/${d.id}/download`} aria-label={`Descargar ${d.original_name}`}><Download size={20}/></a>
          {preview === d.id && <img src={`/api/documents/${d.id}/preview`} alt={d.original_name}/>}
        </li>)}
      </ul> : <p className="muted">{query ? 'Ningún documento coincide.' : 'Aún no hay documentos. Los archivos son privados del estudio.'}</p>}
    </section>

    {dialog === 'sign' && <Editor title="Registrar firma del contrato" subtitle="Confirma que el contrato ya está firmado. Es un registro administrativo, no una firma electrónica." saveLabel="Registrar firma" onClose={() => setDialog(null)}
      fields={[
        {name: 'reference', label: 'Folio o referencia'},
        {name: 'signed_at', label: 'Fecha de firma', type: 'datetime-local', value: localInput(new Date(), zone)},
        ...(contractFiles.length ? [{name: 'document_id', label: 'Archivo del contrato', type: 'select', required: false, value: contractFiles[0].id, options: contractFiles.map(d => ({value: d.id, label: `${d.original_name} · v${d.version}`}))}] : []),
      ]}
      onSave={async data => {
        await api(`/api/bookings/${booking.id}/contract`, 'POST', {reference: data.reference, signed_at: toUtc(String(data.signed_at), zone), document_id: data.document_id || null});
        setDialog(null);
        refresh('Firma registrada');
      }}/>}
    {dialog === 'link' && <Editor title="Vincular archivo al contrato" subtitle="Se conservan el folio y la fecha de firma ya registrados." saveLabel="Vincular" onClose={() => setDialog(null)}
      fields={[{name: 'document_id', label: 'Archivo del contrato', type: 'select', value: contractFiles[0]?.id, options: contractFiles.map(d => ({value: d.id, label: `${d.original_name} · v${d.version}`}))}]}
      onSave={async data => {
        await api(`/api/bookings/${booking.id}/contract/document`, 'POST', {document_id: data.document_id});
        setDialog(null);
        refresh('Archivo vinculado al contrato');
      }}/>}
    {dialog === 'add' && <AddDocument bookingId={booking.id} limit={limit} current={documents.filter(d => d.is_current)} onClose={() => setDialog(null)} onSaved={() => { setDialog(null); refresh('Documento guardado'); }}/>}
  </div>;
}

/** Attach any other file (deposit receipt, annex…) or a new version of an existing one. */
function AddDocument({bookingId, limit, current, onClose, onSaved}: {bookingId: number; limit: number; current: Row[]; onClose: () => void; onSaved: () => void}) {
  const [file, setFile] = useState<File | null>(null), [progress, setProgress] = useState<number | null>(null);
  return <Editor title="Agregar documento" subtitle={`PDF, JPG o PNG${limit ? ` · máximo ${Math.round(limit / 1048576)} MB` : ''}. Adjuntar un archivo no registra su firma.`} saveLabel={progress === null ? 'Guardar documento' : `Subiendo ${progress}%`} onClose={onClose}
    fields={[]}
    onSave={async data => {
      if (!file) throw new Error('Elige un archivo.');
      const problem = fileProblem(file, limit);
      if (problem) throw new Error(problem);
      const replaces = String(data.replaces || '');
      const type = replaces ? current.find(d => d.id === replaces)!.document_type : String(data.document_type);
      try {
        await uploadDocument(bookingId, file, {type, notes: String(data.notes || ''), replaces}, setProgress);
      } finally { setProgress(null); }
      onSaved();
    }}>
    <label className="field"><span>Archivo<b aria-hidden="true"> *</b></span><input type="file" accept={ACCEPT} required onChange={event => setFile(event.target.files?.[0] || null)}/></label>
    <label className="field"><span>Tipo</span><select name="document_type" defaultValue="deposit">{Object.entries(DOCUMENT_TYPES).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
    {current.length > 0 && <label className="field"><span>Versión</span>
      <select name="replaces" defaultValue=""><option value="">Documento nuevo</option>{current.map(d => <option key={d.id} value={d.id}>Sustituye a: {d.original_name}</option>)}</select>
      <small>Al sustituir se conserva el tipo del documento original.</small>
    </label>}
    <label className="field"><span>Observaciones</span><textarea name="notes" maxLength={2000} rows={2}/></label>
    {progress !== null && <progress max={100} value={progress} aria-label="Subiendo archivo"/>}
  </Editor>;
}
