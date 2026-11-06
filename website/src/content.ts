// Populate only with links confirmed by Jordy. Empty channels do not render.
export const contact = {
  whatsapp: 'https://wa.me/524499209781', // https://wa.me/ + confirmed international commercial number
  instagram: 'https://www.instagram.com/jordy_fotografia/',
  facebook: 'https://www.facebook.com/Jordyfloresss/',
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

export const sections = [
  ['portafolio', 'Portafolio'], ['bodas', 'Bodas'], ['xv', 'XV años'], ['sesiones', 'Sesiones'], ['contacto', 'Contacto'],
] as const;

export const whatsappMessages = {
  bodas: 'Hola, quisiera consultar los paquetes de boda y la disponibilidad de mi fecha.',
  xv: 'Hola, quisiera consultar los paquetes de XV años y la disponibilidad de mi fecha.',
  sesiones: 'Hola, quisiera consultar el precio y la disponibilidad de una sesión fotográfica.',
  hero: 'Hola, vi la página de Jordy Flores Fotografía y me gustaría cotizar un evento.',
  general: 'Hola, me gustaría recibir información sobre fotografía y video.',
};
export function whatsappLink(kind: keyof typeof whatsappMessages = 'general') {
  return `${contact.whatsapp}?text=${encodeURIComponent(whatsappMessages[kind])}`;
}

export function packageLink(name: string) {
  return contact.whatsapp + "?text=" + encodeURIComponent(`Hola, quisiera cotizar el paquete de boda ${name} y consultar disponibilidad.`);
}
