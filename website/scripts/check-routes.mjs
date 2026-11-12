import assert from 'node:assert/strict';
import {setTimeout} from 'node:timers/promises';

const origin = 'http://127.0.0.1:4175';
let ready = false;
for (let attempt = 0; attempt < 40; attempt++) {
  try {
    const response = await fetch(origin, {signal: AbortSignal.timeout(1000)});
    if (response.ok) {ready = true; break;}
  } catch {}
  await setTimeout(500);
}
assert(ready, 'Workers preview did not become ready');
for (const [path, status] of [['/',200],['/privacidad/',200],['/missing-page',404],['/admin',404],['/api',404],['/.env',404]]) {
  const response = await fetch(origin + path, {signal: AbortSignal.timeout(5000)});
  assert.equal(response.status, status, `${path}: unexpected status`);
  assert(response.headers.get('content-security-policy')?.includes("connect-src 'none'"));
  const body = await response.text();
  assert(body.includes('Jordy Flores'));
  if (status === 404) assert(body.includes('noindex'));
  console.log(`${path}: ${status}, security headers OK`);
}
