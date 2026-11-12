import React, {useEffect, useState} from 'react';
import {AlertCircle, ChevronRight, Search} from 'lucide-react';
import {api} from '../api';
import type {Row} from '../shared';

export type Page = {items: Row[]; total: number; page: number; page_size: number};
const EMPTY: Page = {items: [], total: 0, page: 1, page_size: 25};

export const qs = (params: Row) =>
  new URLSearchParams(Object.entries(params).filter(([, value]) => value !== '' && value !== null && value !== undefined).map(([key, value]) => [key, String(value)])).toString();

export function usePage(endpoint: string, params: Row, revision = 0) {
  const [result, setResult] = useState<Page>(EMPTY), [error, setError] = useState(''), [busy, setBusy] = useState(true), [attempt, setAttempt] = useState(0);
  const query = qs(params);
  useEffect(() => {
    let active = true;
    setBusy(true);
    api<Page>(`${endpoint}?${query}`)
      .then(page => { if (active) { setResult(page); setError(''); } })
      .catch(err => { if (active) setError((err as Error).message); })
      .finally(() => { if (active) setBusy(false); });
    return () => { active = false; };
  }, [endpoint, query, revision, attempt]);
  return {result, error, busy, loaded: result !== EMPTY, retry: () => setAttempt(value => value + 1)};
}

export function SearchBox({label, placeholder, onSearch}: {label: string; placeholder: string; onSearch: (text: string) => void}) {
  const [text, setText] = useState('');
  useEffect(() => {
    const timer = window.setTimeout(() => onSearch(text.trim()), 300);
    return () => window.clearTimeout(timer);
  }, [text]);
  return <label className="search"><Search size={18} aria-hidden="true"/><input type="search" aria-label={label} placeholder={placeholder} value={text} onChange={event => setText(event.target.value)}/></label>;
}

export function Chips<T extends string>({label, options, value, onChange}: {label: string; options: {value: T; label: string}[]; value: T; onChange: (value: T) => void}) {
  return <div className="chip-row" role="group" aria-label={label}>
    {options.map(option => <button key={option.value} type="button" aria-pressed={value === option.value} onClick={() => onChange(option.value)}>{option.label}</button>)}
  </div>;
}

export function RowCard({title, subtitle, meta, badge, label, onClick}: {title: React.ReactNode; subtitle?: React.ReactNode; meta?: React.ReactNode; badge?: React.ReactNode; label?: string; onClick: () => void}) {
  return <li>
    <button type="button" className="row-card" aria-label={label} onClick={onClick}>
      <span className="rc-main"><strong>{title}</strong>{subtitle && <small>{subtitle}</small>}</span>
      {meta && <span className="rc-meta">{meta}</span>}
      {badge && <span className="rc-badge">{badge}</span>}
      <ChevronRight size={18} aria-hidden="true"/>
    </button>
  </li>;
}

export function ListError({what, error, retry}: {what: string; error: string; retry: () => void}) {
  if (!error) return null;
  return <div className="error" role="alert"><AlertCircle size={18}/><span>No se pudo cargar {what}: {error}</span><button className="text-btn" onClick={retry}>Reintentar</button></div>;
}

export function Pager({result, onPage}: {result: Page; onPage: (page: number) => void}) {
  const pages = Math.max(1, Math.ceil(result.total / result.page_size));
  return <div className="pagination">
    <span>{result.total} {result.total === 1 ? 'resultado' : 'resultados'}{pages > 1 && ` · página ${result.page} de ${pages}`}</span>
    {pages > 1 && <>
      <button className="secondary" disabled={result.page === 1} onClick={() => onPage(result.page - 1)}>Anterior</button>
      <button className="secondary" disabled={result.page >= pages} onClick={() => onPage(result.page + 1)}>Siguiente</button>
    </>}
  </div>;
}
