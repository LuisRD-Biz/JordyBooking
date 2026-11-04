/** Public copy only. Never import CRM records or environment files here. */
export type Category = 'Bodas' | 'XV años' | 'Sesiones' | 'Eventos';
export type Photograph = {
  id: string; category: Category; title: string; aspect: 'portrait' | 'landscape';
  src: string | null; alt: string; width: number; height: number;
};

export const studio = {
  name: 'Jordy Flores Fotografía',
  headline: ['Hay momentos', 'que merecen', 'quedarse.'],
  introduction: 'Fotografía y video para volver a sentir. Las miradas, los abrazos y esos pequeños instantes que hacen tu historia.',
  about: 'Una mirada cercana a lo que importa.',
  aboutText: 'Una boda, una celebración, una nueva etapa. Cada historia tiene su propio ritmo. Nuestro enfoque es acompañarla con sensibilidad, cuidando la luz, los detalles y la forma en que quieres recordarla.',
};

// Populate only with links confirmed by Jordy. Empty channels do not render.
export const contact = {
  whatsapp: '', // https://wa.me/ + confirmed international commercial number
  instagram: '',
  facebook: '',
  email: '',
};

export function contactLinks() {
  const candidates = [
    {label: 'WhatsApp', value: contact.whatsapp, hosts: ['wa.me']},
    {label: 'Instagram', value: contact.instagram, hosts: ['instagram.com', 'www.instagram.com']},
    {label: 'Facebook', value: contact.facebook, hosts: ['facebook.com', 'www.facebook.com', 'fb.com']},
  ];
  const links: {label: string; href: string}[] = [];
  for (const item of candidates) {
    if (!item.value) continue;
    const url = new URL(item.value);
    if (url.protocol !== 'https:' || !item.hosts.includes(url.hostname) || url.username || url.password) {
      throw new Error(`Enlace público no válido: ${item.label}`);
    }
    links.push({label: item.label, href: url.href});
  }
  if (contact.email) {
    if (!/^[^\s@?&]+@[^\s@?&]+\.[^\s@?&]+$/.test(contact.email)) throw new Error('Correo público no válido');
    links.push({label: 'Correo electrónico', href: `mailto:${contact.email}`});
  }
  return links;
}

export const services = [
  {number: '01', name: 'Bodas', detail: 'El inicio de algo que vale la pena recordar.', category: 'Bodas'},
  {number: '02', name: 'XV años', detail: 'Una nueva etapa. Una celebración muy tuya.', category: 'XV años'},
  {number: '03', name: 'Sesiones fotográficas', detail: 'Un momento para detenerte y ser tú.', category: 'Sesiones'},
  {number: '04', name: 'Eventos sociales', detail: 'Las personas y los instantes que los reúnen.', category: 'Eventos'},
  {number: '05', name: 'Fotografía y video', detail: 'La emoción, también en movimiento.', category: 'Todas'},
] as const;

// No third-party photography. Replace null with an authorized /media/… file.
export const hero: Photograph = {
  id: 'hero', category: 'Bodas', title: 'El comienzo de una historia', aspect: 'portrait',
  src: null, alt: '', width: 1000, height: 1250,
};
export const photographs: Photograph[] = [
  {id: '01', category: 'Bodas', title: 'Lo que empieza con un sí', aspect: 'portrait', src: null, alt: '', width: 800, height: 1000},
  {id: '02', category: 'Sesiones', title: 'El arte de ser tú', aspect: 'landscape', src: null, alt: '', width: 1200, height: 900},
  {id: '03', category: 'XV años', title: 'Una nueva forma de brillar', aspect: 'portrait', src: null, alt: '', width: 800, height: 1000},
  {id: '04', category: 'Eventos', title: 'Estar, celebrar, recordar', aspect: 'landscape', src: null, alt: '', width: 1200, height: 900},
];

export const sections = [
  ['nosotros', 'El estudio'], ['servicios', 'Servicios'], ['portafolio', 'Portafolio'], ['contacto', 'Contacto'],
] as const;
