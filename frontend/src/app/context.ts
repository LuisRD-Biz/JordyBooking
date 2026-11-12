import {createContext, useContext} from 'react';
import type {Row} from '../shared';

export type Dialog = {type: string; row?: Row};

export type Studio = {
  user: Row;
  zone: string;
  today: string;
  selectedDay: string;
  packages: Row[];
  resources: Row[];
  metrics: Row;
  revision: number;
  reload: () => Promise<void>;
  changed: (message?: string) => void;
  open: (type: string, row?: Row) => void;
  openBooking: (id: number) => void;
  seasonVisible: boolean;
  setSeasonAlways: (value: boolean) => void;
  seasonAlways: boolean;
};

export const StudioContext = createContext<Studio | null>(null);

export function useStudio(): Studio {
  const studio = useContext(StudioContext);
  if (!studio) throw new Error('StudioContext is missing');
  return studio;
}
