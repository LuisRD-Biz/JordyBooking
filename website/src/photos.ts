import { manifest } from './photo-manifest';

export type Category = 'Bodas' | 'XV años' | 'Sesiones';
export interface Photograph {
  id: string;
  category: Category;
  title: string;
  alt: string;
  width: number;
  height: number;
  orientation: 'portrait' | 'landscape' | 'square';
  priority: number;
  position: number;
  focal: 'left' | 'center' | 'right' | 'top' | 'bottom';
  featured: boolean;
  visible: boolean;
  base: string;
  widths: number[];
}

export const photographs = manifest.filter(p => p.visible).sort((a, b) => a.position - b.position);
export const hero = [...photographs].sort((a, b) => Number(b.featured) - Number(a.featured) || a.priority - b.priority)[0];
export const chapterPhotos = photographs.filter(p => p.featured && p !== hero);
export const portfolio = photographs.filter(p => !p.featured && p !== hero);
export function source(photo: Photograph, width = Math.max(...photo.widths)) {
  return `${photo.base}-${width}.webp`;
}
