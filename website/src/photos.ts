import { manifest } from './photo-manifest';

export type Category = 'Bodas' | 'XV aÃ±os' | 'Sesiones';
export interface Photograph {
  id: string;
  category: Category;
  title: string;
  alt: string;
  width: number;
  height: number;
  orientation: 'portrait' | 'landscape' | 'square';
  isHero: boolean;
  position: number;
  focal: 'left' | 'center' | 'right' | 'top' | 'bottom';
  featured: boolean;
  visible: boolean;
  base: string;
  widths: number[];
}

export function selectPhotos(records: readonly Photograph[]) {
  const photographs = records.filter(p => p.visible).sort((a, b) => a.position - b.position);
  const hero = photographs.find(p => p.isHero);
  const chapterPhotos = photographs.filter(p => p.featured && !p.isHero);
  const portfolio = photographs.filter(p => !p.featured && !p.isHero);
  return {photographs, hero, chapterPhotos, portfolio};
}

export const {photographs, hero, chapterPhotos, portfolio} = selectPhotos(manifest);

export function source(photo: Photograph, width = Math.max(...photo.widths)) {
  return `${photo.base}-${width}.webp`;
}
