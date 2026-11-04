import {readFile, writeFile, mkdir, rm} from 'node:fs/promises';
import {render, publicPhotos, validateContacts} from '../.build/prerender.js';

validateContacts();
for (const photo of publicPhotos()) {
  if (photo.src && (!/^\/media\/[a-zA-Z0-9_./-]+\.(avif|webp|jpe?g|png)$/.test(photo.src) || photo.src.includes('..') || !photo.alt.trim())) {
    throw new Error(`Imagen no válida o sin texto alternativo: ${photo.id}`);
  }
}
const template = await readFile(new URL('../dist/index.html', import.meta.url), 'utf8');
if (!template.includes('<!--app-html-->')) throw new Error('Falta el punto de prerenderizado.');
const routes = [
  {path: '/', file: 'index.html', title: 'Jordy Flores Fotografía — Historias que se quedan', description: 'Jordy Flores Fotografía. Bodas, XV años, sesiones y eventos sociales. Fotografía y video para los momentos que quieres conservar.'},
  {path: '/privacidad/', file: 'privacidad/index.html', title: 'Privacidad — Jordy Flores Fotografía', description: 'Información sobre el funcionamiento de esta página de presentación y la revisión pendiente del aviso de privacidad del estudio.'},
  {path: '/404.html', file: '404.html', title: 'Página no encontrada — Jordy Flores Fotografía', description: 'La página que buscas no está aquí. Vuelve al inicio de Jordy Flores Fotografía.'},
];
for (const route of routes) {
  let html = template.replace('<!--app-html-->', render(route.path))
    .replace(/<title>.*?<\/title>/s, `<title>${route.title}</title>`)
    .replace(/(<meta name="description" content=")[^"]*(")/, `$1${route.description}$2`)
    .replace(/(<meta property="og:title" content=")[^"]*(")/, `$1${route.title}$2`)
    .replace(/(<meta property="og:description" content=")[^"]*(")/, `$1${route.description}$2`)
    .replace(/https:\/\/jordyflores.com\/(?=" \/>)/g, `https://jordyflores.com${route.path}`);
  if (route.path === '/404.html') {
    html = html.replace('content="index,follow"', 'content="noindex,follow"')
      .replace(/\s*<link rel="canonical"[^>]+>/, '');
  }
  const out = new URL(`../dist/${route.file}`, import.meta.url);
  await mkdir(new URL('.', out), {recursive: true});
  await writeFile(out, html);
}
// This contributor note must never become a public asset.
await rm(new URL('../dist/media/README.txt', import.meta.url), {force: true});
console.log('Prerender: inicio, privacidad y 404; ningún servidor requerido.');
