import {useEffect, useState} from 'react';
import {api} from '../api';
import {addDays, dayKey, daysInMonth} from '../lib/dates';

export type AgendaItem = {
  type: 'booking' | 'appointment' | 'block';
  id: number;
  starts_at: string;
  ends_at: string;
  title: string;
  subtitle: string;
  status: string;
  kind: string;
  customer_id: number | null;
  booking_id: number | null;
  resource_id: number | null;
  location: string | null;
};

export type Tone = 'pending' | 'confirmed' | 'appointment' | 'block' | 'cancelled';
export const TONES: {tone: Tone; label: string}[] = [
  {tone: 'pending', label: 'Por aprobar'},
  {tone: 'confirmed', label: 'Confirmada'},
  {tone: 'appointment', label: 'Cita'},
  {tone: 'block', label: 'Bloqueo'},
];

export function toneOf(item: AgendaItem): Tone {
  if (item.type === 'block') return 'block';
  if (item.status === 'cancelled') return 'cancelled';
  if (item.type === 'appointment') return 'appointment';
  return item.status === 'pending_approval' ? 'pending' : 'confirmed';
}

export function byDay(items: AgendaItem[], zone: string): Map<string, AgendaItem[]> {
  const days = new Map<string, AgendaItem[]>();
  const add = (day: string, item: AgendaItem) => days.set(day, [...(days.get(day) || []), item]);
  for (const item of items) {
    const first = dayKey(item.starts_at, zone);
    add(first, item);
    if (item.type !== 'block') continue;
    const last = dayKey(new Date(item.ends_at).getTime() - 1, zone);
    for (let day = addDays(first, 1); day <= last; day = addDays(day, 1)) add(day, item);
  }
  return days;
}

const cache = new Map<string, {revision: number; request: Promise<AgendaItem[]>}>();

function month(key: string, revision: number): Promise<AgendaItem[]> {
  const hit = cache.get(key);
  if (hit && hit.revision === revision) return hit.request;
  const request = api<AgendaItem[]>(`/api/agenda?from=${key}-01&to=${key}-${String(daysInMonth(key)).padStart(2, '0')}`);
  cache.set(key, {revision, request});
  request.catch(() => { if (cache.get(key)?.request === request) cache.delete(key); });
  return request;
}

export function useAgenda(months: string[], revision: number) {
  const [items, setItems] = useState<AgendaItem[]>([]), [error, setError] = useState(''), [loading, setLoading] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const key = months.join(',');
  useEffect(() => {
    let active = true;
    setLoading(true);
    Promise.all(key.split(',').map(value => month(value, revision)))
      .then(results => {
        if (!active) return;
        const unique = new Map(results.flat().map(item => [`${item.type}-${item.id}`, item]));
        setItems([...unique.values()].sort((a, b) => a.starts_at.localeCompare(b.starts_at)));
        setError('');
      })
      .catch(err => { if (active) setError((err as Error).message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [key, revision, attempt]);
  return {items, error, loading, retry: () => setAttempt(value => value + 1)};
}
