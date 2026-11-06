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
  isHero: boolean;
  position: number;
  focal: 'left' | 'center' | 'right' | 'top' | 'bottom';
  featured: boolean;
  visible: boolean;
  base: string;
  widths: number[];
}

export function validateManifest(records: readonly Photograph[]) {
  const ids = new Set<string>();
  if (records.filter(p => p.visible && p.isHero).length > 1) {
    throw new Error('Solo una fotografía visible puede ocupar la portada.');
  }
  for (const p of records) {
    const orientation = p.width === p.height ? 'square' : p.width > p.height ? 'landscape' : 'portrait';
    if (!p.id.trim() || ids.has(p.id) || !p.alt.trim() || !p.title.trim() ||
        !Number.isSafeInteger(p.position) || p.position < 1 ||
        !Number.isSafeInteger(p.width) || p.width < 1 ||
        !Number.isSafeInteger(p.height) || p.height < 1 || p.orientation !== orientation ||
        !/^\/media\/(?:[\w-]+\/)*[\w-]+$/.test(p.base) ||
        !p.widths.length || p.widths.some((w, i) =>
          !Number.isSafeInteger(w) || w <= 0 || w > p.width || (i > 0 && w <= p.widths[i-1]))) {
      throw new Error(`Ficha fotográfica inválida: ${p.id}`);
    }
    ids.add(p.id);
  }
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
