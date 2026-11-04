import assert from 'node:assert/strict';
import {readFile, readdir, lstat, access} from 'node:fs/promises';
import {extname, join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const root = fileURLToPath(new URL('../dist/', import.meta.url));
const files = [];
async function walk(dir) {
  for (const name of await readdir(dir)) {
    const path = join(dir, name); const stat = await lstat(path);
    assert(!stat.isSymbolicLink(), 'No publicar enlaces simbólicos');
    if (stat.isDirectory()) await walk(path);
    else files.push(path);
  }
}
await walk(root);
const allowed = new Set(['.html','.js','.css','.svg','.png','.webp','.avif','.jpg','.jpeg','.woff','.woff2','.txt','.xml']);
for (const path of files) {
  assert(allowed.has(extname(path)) || path.endsWith('_headers'), `Archivo inesperado: ${path.slice(root.length)}`);
  assert(!/\.(map|env|pem|key|sql|sqlite|db)$/.test(path), 'Archivo privado en el build');
  if (!['.html','.js','.css','.svg','.txt','.xml'].includes(extname(path))) continue;
  const body = await readFile(path, 'utf8');
  assert(!/(?:DATABASE_URL|ADMIN_API_KEY|META_APP_SECRET|WHATSAPP_ACCESS_TOKEN|OPENAI_API_KEY|postgres(?:ql)?:\/\/|-----BEGIN [A-Z ]*PRIVATE KEY|\bEAA[A-Za-z0-9]{50,}|\bsk-(?:proj-)?[A-Za-z0-9_-]{35,})/.test(body), 'Posible secreto o dependencia privada: publicación detenida');
  if (extname(path) === '.html') {
    assert.equal((body.match(/<h1(?:\s|>)/g) || []).length, 1, 'Debe existir un título principal');
    assert(body.includes('<html lang="es-MX">'));
    assert(!body.includes('<!--app-html-->'));
    for (const [, link] of body.matchAll(/(?:href|src)="([^"]+)"/g)) {
      if (link.startsWith('#')) {assert(body.includes(`id="${link.slice(1)}"`), `Ancla ausente: ${link}`); continue;}
      if (!link.startsWith('/')) continue;
      const asset = link.split('#')[0];
      const file = asset.endsWith('/') ? `${asset}index.html` : asset;
      assert(resolve(root, '.' + file).startsWith(resolve(root)), 'Ruta fuera del build');
      await access(join(root, file));
    }
  }
}
for (const path of ['index.html','privacidad/index.html','404.html','_headers','robots.txt','sitemap.xml','og-image.png']) await access(join(root, path));
const home = await readFile(join(root,'index.html'),'utf8');
assert(home.includes('Jordy Flores') && !home.includes('Hello World'));
assert(!home.includes('<form'), 'No habilitar captación de datos sin aviso aprobado');
assert(!home.includes('href="https://wa.me/"'), 'No mostrar contactos vacíos');
const notFound = await readFile(join(root,'404.html'),'utf8');
assert(notFound.includes('noindex,follow'));
const headers = await readFile(join(root,'_headers'),'utf8');
assert(headers.includes("frame-ancestors 'none'") && headers.includes("connect-src 'none'"));
console.log(`Build auditado: ${files.length} archivos; enlaces locales, rutas, metadatos y patrones de secretos correctos.`);
