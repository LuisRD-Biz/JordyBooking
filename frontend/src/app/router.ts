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

export function afterOverlays(step: () => void) {
  if (!closers.length && !pendingBacks) return step();
  queued.push(step);
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

export function navigate(path: string, options: {replace?: boolean} = {}) {
  afterOverlays(() => {
    const {idx} = state();
    if (options.replace) write(path, idx, true);
    else if (parse(location.hash).path !== path) write(path, idx + 1, false);
  });
}

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

export function goBack() {
  if (state().idx > 0) history.back();
  else write(HOME, 0, true);
}

function onPop() {
  if (pendingBacks > 0) {
    pendingBacks--;
    if (!pendingBacks) window.setTimeout(flush, 0);
    return;
  }
  const depth = state().overlay;
  while (closers.length > depth) closers.pop()!();
  emit();
}

let started = false;
function start() {
  if (started) return;
  started = true;
  const route = parse(location.hash);
  history.replaceState({idx: 0, overlay: 0}, '', `#/${HOME}`);
  if (route.name !== HOME || route.param) {
    const top = route.name === HOME ? 0 : 1;
    if (top) history.pushState({idx: 1, overlay: 0}, '', `#/${route.path}`);
    else history.replaceState({idx: 0, overlay: 0}, '', `#/${route.path}`);
  }
  window.addEventListener('popstate', onPop);
  window.addEventListener('hashchange', () => {
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
      if (position < 0) return;
      closers.splice(position, 1);
      pendingBacks++;
      history.back();
    };
  }, [enabled]);
}
