/**
 * Minimal hash router with real history.
 *
 * The stack is kept shallow and predictable so the phone's "back" button never leaves the
 * panel from an inner view:
 *
 *   index 0  calendar (always seeded, even when the panel is opened on a deep link)
 *   index 1  a section (clients, leads, more…); sections replace one another
 *   index 2+ pushed detail views (a booking sheet, a page opened from "Más")
 *
 * Dialogs and sheets add their own history entry through `useBackClose`, with the same URL,
 * so "back" closes the top one instead of navigating.
 */
import {useEffect, useRef, useSyncExternalStore} from 'react';

export type Route = {name: string; param?: string; path: string};

export const HOME = 'calendario';
const NAMES = new Set([
  HOME, 'reserva', 'clientes', 'oportunidades', 'mas', 'reservaciones', 'citas',
  'paquetes', 'equipo', 'temporada', 'actividad', 'configuracion',
]);

type EntryState = {idx: number; overlay: number};

const listeners = new Set<() => void>();
const closers: (() => void)[] = [];
let pendingBacks = 0;
let queued: (() => void)[] = [];
let flushTimer: number | undefined;

export function parse(hash: string): Route {
  const [name = '', param] = hash.replace(/^#\/?/, '').split('/').map(part => decodeURIComponent(part));
  if (!NAMES.has(name)) return {name: HOME, path: HOME};
  return {name, param: param || undefined, path: param ? `${name}/${param}` : name};
}

const state = (): EntryState => ({idx: history.state?.idx ?? 0, overlay: history.state?.overlay ?? 0});
const emit = () => listeners.forEach(listener => listener());

function flush() {
  window.clearTimeout(flushTimer);
  const run = queued;
  queued = [];
  run.forEach(step => step());
}

/**
 * Run `step` once every dialog has been closed and its history entry removed. Opening one
 * dialog from another goes through here, so their history entries never interleave.
 */
export function afterOverlays(step: () => void) {
  if (!closers.length && !pendingBacks) return step();
  queued.push(step);
  // Closing is idempotent; each dialog removes its own history entry when it unmounts.
  [...closers].reverse().forEach(close => close());
  window.clearTimeout(flushTimer);
  flushTimer = window.setTimeout(() => { pendingBacks = 0; flush(); }, 600);
}

function write(path: string, idx: number, replace: boolean) {
  const url = `#/${path}`;
  if (replace) history.replaceState({idx, overlay: 0}, '', url);
  else history.pushState({idx, overlay: 0}, '', url);
  emit();
}

/** Push a detail view, or replace the current entry (used for the selected calendar day). */
export function navigate(path: string, options: {replace?: boolean} = {}) {
  afterOverlays(() => {
    const {idx} = state();
    if (options.replace) write(path, idx, true);
    else if (parse(location.hash).path !== path) write(path, idx + 1, false);
  });
}

/** Show a top-level section: the calendar lives at index 0, every other section at index 1. */
export function goSection(name: string) {
  afterOverlays(() => {
    const target = name === HOME ? 0 : 1;
    const {idx} = state();
    if (idx > target) {
      pendingBacks++;
      queued.push(() => write(name, target, true));
      history.go(target - idx);
    } else {
      write(name, target, idx === target);
    }
  });
}

/** Leave a detail view. Falls back to the calendar when there is nothing underneath. */
export function goBack() {
  if (state().idx > 0) history.back();
  else write(HOME, 0, true);
}

function onPop() {
  if (pendingBacks > 0) {
    pendingBacks--;
    // Not inside the traversal itself: browsers drop a pushState made while popstate fires.
    if (!pendingBacks) window.setTimeout(flush, 0);
    return;
  }
  // A navigation entry has overlay depth 0, so every open dialog closes.
  const depth = state().overlay;
  while (closers.length > depth) closers.pop()!();
  emit();
}

let started = false;
function start() {
  if (started) return;
  started = true;
  const route = parse(location.hash);
  // Seed the calendar underneath a deep link so "back" lands inside the panel.
  history.replaceState({idx: 0, overlay: 0}, '', `#/${HOME}`);
  if (route.name !== HOME || route.param) {
    const top = route.name === HOME ? 0 : 1;
    if (top) history.pushState({idx: 1, overlay: 0}, '', `#/${route.path}`);
    else history.replaceState({idx: 0, overlay: 0}, '', `#/${route.path}`);
  }
  window.addEventListener('popstate', onPop);
  window.addEventListener('hashchange', () => {
    // A hash typed by hand or followed from a plain link has no state yet.
    if (history.state?.idx === undefined) history.replaceState({idx: 1, overlay: 0}, '');
    emit();
  });
}

function subscribe(listener: () => void) {
  start();
  listeners.add(listener);
  return () => { listeners.delete(listener); };
}

export function useRoute(): Route {
  const hash = useSyncExternalStore(subscribe, () => location.hash);
  return parse(hash);
}

/**
 * Give an open dialog its own history entry: "back" calls `onClose`, and closing the dialog
 * any other way removes the entry again. A view that already has its own route passes
 * `enabled = false`.
 */
export function useBackClose(onClose: () => void, enabled = true) {
  const latest = useRef(onClose);
  latest.current = onClose;
  useEffect(() => {
    if (!enabled) return;
    start();
    const close = () => latest.current();
    closers.push(close);
    history.pushState({idx: state().idx, overlay: closers.length}, '');
    return () => {
      const position = closers.indexOf(close);
      if (position < 0) return; // Already closed by "back".
      closers.splice(position, 1);
      pendingBacks++;
      history.back();
    };
  }, [enabled]);
}
