import {formatDistanceToNowStrict} from 'date-fns';
import {formatInTimeZone, fromZonedTime} from 'date-fns-tz';
import {es} from 'date-fns/locale';

type Instant = string | number | Date;

/** Format an instant in the studio's time zone. */
export const fmt = (value: Instant, zone: string, pattern = 'd MMM yyyy') =>
  formatInTimeZone(new Date(value), zone, pattern, {locale: es});

/** Studio-local calendar day (YYYY-MM-DD) of an instant. */
export const dayKey = (value: Instant, zone: string) => fmt(value, zone, 'yyyy-MM-dd');

/** Studio-local wall time ("2026-11-14T10:00") to a UTC ISO string. */
export const toUtc = (local: string, zone: string) => fromZonedTime(local, zone).toISOString();

/** Value for a datetime-local input. */
export const localInput = (value: Instant, zone: string) => fmt(value, zone, "yyyy-MM-dd'T'HH:mm");

export const capitalize = (text: string) => text.charAt(0).toUpperCase() + text.slice(1);

/** "viernes 14 nov" for a calendar day. */
export const dayLabel = (day: string, zone: string, pattern = 'EEEE d MMM') =>
  fmt(fromZonedTime(`${day}T12:00`, zone), zone, pattern).replace('.', '');

export function addDays(day: string, amount: number) {
  const date = new Date(`${day}T12:00:00Z`);
  date.setUTCDate(date.getUTCDate() + amount);
  return date.toISOString().slice(0, 10);
}

export function addMonths(month: string, amount: number) {
  const [year, index] = month.split('-').map(Number);
  const date = new Date(Date.UTC(year, index - 1 + amount, 1));
  return date.toISOString().slice(0, 7);
}

export const isDay = (value?: string): value is string =>
  !!value && /^\d{4}-\d{2}-\d{2}$/.test(value) && !Number.isNaN(Date.parse(`${value}T12:00:00Z`));

/** Monday-based weekday index (0–6) of a calendar day. */
export const weekday = (day: string) => (new Date(`${day}T12:00:00Z`).getUTCDay() + 6) % 7;

export const daysInMonth = (month: string) => {
  const [year, index] = month.split('-').map(Number);
  return new Date(Date.UTC(year, index, 0)).getUTCDate();
};

export const relative = (value: Instant) =>
  Date.now() - new Date(value).getTime() < 60_000
    ? 'hace un momento'
    : formatDistanceToNowStrict(new Date(value), {locale: es, addSuffix: true});
