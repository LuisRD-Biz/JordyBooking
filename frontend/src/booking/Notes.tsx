import React, {useEffect, useRef, useState} from 'react';
import {AlertCircle, Send} from 'lucide-react';
import {api} from '../api';
import {useStudio} from '../app/context';
import {fmt, relative} from '../lib/dates';
import type {Row} from '../shared';

const MAX = 4000;

export function Notes({bookingId, onCount}: {bookingId: number; onCount: (count: number) => void}) {
  const {zone} = useStudio();
  const [notes, setNotes] = useState<Row[] | null>(null), [error, setError] = useState('');
  const [draft, setDraft] = useState(''), [busy, setBusy] = useState(false);
  const key = useRef(crypto.randomUUID());
  const path = `/api/bookings/${bookingId}/notes`;

  useEffect(() => {
    let active = true;
    api<Row[]>(path)
      .then(rows => { if (active) { setNotes(rows); onCount(rows.length); } })
      .catch(err => { if (active) setError(`No se pudieron cargar las notas: ${err.message}`); });
    return () => { active = false; };
  }, [path]);

  async function add(event: React.FormEvent) {
    event.preventDefault();
    const body = draft.trim();
    if (!body || busy) return;
    setBusy(true); setError('');
    try {
      const note = await api<Row>(path, 'POST', {body}, {'Idempotency-Key': key.current});
      const next = [...(notes || []).filter(existing => existing.id !== note.id), note];
      setNotes(next);
      onCount(next.length);
      setDraft('');
      key.current = crypto.randomUUID();
    } catch (err) {
      setError(`No se pudo guardar la nota: ${(err as Error).message}`);
    } finally { setBusy(false); }
  }

  return <div className="notes">
    {notes === null && !error && <p className="muted">Cargando notas…</p>}
    {notes?.length === 0 && <p className="muted">Aún no hay notas. Anota aquí acuerdos, preferencias o pendientes de esta reservación.</p>}
    {notes && notes.length > 0 && <ol>
      {notes.map(note => <li key={note.id}>
        <header><strong>{note.author_name}</strong><time dateTime={note.created_at} title={fmt(note.created_at, zone, "d MMM yyyy, HH:mm")}>{relative(note.created_at)}</time></header>
        <p className="prewrap">{note.body}</p>
      </li>)}
    </ol>}
    {error && <div className="error" role="alert"><AlertCircle size={18}/>{error}</div>}
    <form className="note-form" onSubmit={add}>
      <textarea aria-label="Nueva nota" placeholder="Escribe una nota…" rows={2} maxLength={MAX} value={draft} onChange={event => setDraft(event.target.value)}/>
      <button className="confirm" disabled={busy || !draft.trim()}><Send size={16}/>{busy ? 'Guardando…' : 'Agregar nota'}</button>
      <small>Las notas no se editan ni se borran; si algo cambia, agrega otra.</small>
    </form>
  </div>;
}
