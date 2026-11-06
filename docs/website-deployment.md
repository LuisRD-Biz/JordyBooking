# Página pública — jordyflores.com

## Política vigente tras reorganización

**No desplegar todavía.** Producción exclusivamente desde `main`, después de
aprobar e integrar los dos PR. Directorio del build: `website/dist`; Worker
`young-moon-14a9`. Se conservan dominio, HTTPS y DNS. Configuración manual pendiente.
Consultar [CI/CD](ci-cd.md) y [flujo de contribución](../CONTRIBUTING.md) tras integrar la base.
El bloque siguiente conserva el estado anterior como antecedente.

## Estado inicial de la web — 3 de noviembre de 2026 (antecedente)

Implementada en `website/`, rama `whatsapp-cloud-api`. No se hizo commit, push,
merge ni despliegue. Wrangler no está autenticado. El dominio continúa sirviendo
la versión anterior «Hello World», con HTTPS y respuesta 200.

El CRM de `frontend/`, FastAPI, PostgreSQL y WhatsApp permanecen independientes.
El único directorio que se publica es `website/dist`. Nunca seleccionar la raíz
del repositorio ni el build del administrador como directorio de assets.

## Desarrollo y construcción

Requisitos: Node.js 22.12 o posterior y pnpm 11.25.0 (versiones fijadas en package.json).
Desde la raíz del repositorio:

```powershell
cd website
pnpm install --frozen-lockfile
pnpm dev
```

Desarrollo: `http://127.0.0.1:5174`. Para revisar el resultado que se publicará:

```powershell
pnpm build
pnpm preview
```

Vista previa de Workers local: `http://127.0.0.1:4174`. Detener con Ctrl+C.
El build verifica TypeScript, compila React, genera HTML para inicio, privacidad
y 404, y audita enlaces locales, archivos permitidos y patrones de secretos.
No requiere Python, base de datos, claves de Meta ni servicios del administrador.
Los tipos de letra se sirven localmente; no hay solicitudes a Google Fonts.

## Publicación mediante GitHub (preferida)

Primero integrar con revisión el PR de la base en `main` y después el PR
`feature/website`. La web original ya está en GitHub en `543b1dd`; no conectar
la rama histórica ni una rama feature al Worker de producción.

1. Iniciar sesión en la cuenta de Cloudflare propietaria de `jordyflores.com`.
2. Abrir **Workers & Pages → young-moon-14a9**. Comprobar que es el Worker del
   dominio y guardar el identificador de la versión actual para poder volver atrás.
   Revisar **Settings → Domains & Routes**: debe conservarse `jordyflores.com`.
   Revisar bindings, variables y triggers antes de reemplazar el código; si hay
   funciones distintas del Hello World, detenerse y evaluar esa configuración.
3. Abrir **Settings → Builds → Connect** y conectar el repositorio
   **LuisRD-Biz/JordyBooking**. Otorgar acceso únicamente al repositorio necesario.
4. Usar estos valores:

   | Campo | Valor |
   | --- | --- |
   | Production branch | `main` |
   | Root directory | `website` |
   | Build command | `pnpm install --frozen-lockfile && pnpm build` |
   | Deploy command | `pnpm exec wrangler deploy` |
   | Node.js | `24.22.1` (o versión compatible >=22.12) |
   | pnpm | `11.25.0`, declarado en `packageManager` |

5. Si se ofrece un comando para ramas no productivas, mantenerlas sin despliegue
   automático inicialmente. Solo `main` puede apuntar al Worker de producción. Desactivar builds de ramas no productivas.
6. Usar la autenticación de despliegue administrada por Cloudflare Builds. No copiar
   tokens al código, `.env` público o variables `VITE_*`/`PUBLIC_WEBSITE_*`.
7. Ejecutar el primer build. La configuración `wrangler.jsonc` selecciona el Worker
   existente y `./dist`; no declara cambios de DNS ni nuevos dominios. `keep_vars`
   conserva variables, pero no sustituye la revisión de bindings/configuración.
8. Verificar `https://jordyflores.com`: debe mostrar Jordy Flores, sin Hello World.
   Revisar `/privacidad/` (200), una ruta inexistente (404), `/admin` y `/api` (404),
   imágenes, tipografía, móvil, HTTPS y encabezados. Confirmar que el dominio sigue
   asociado al mismo Worker. Solo entonces considerar publicada esta versión.

Una vez conectada `main`, cada integración que afecte la web puede publicar cambios.
En Settings → Builds → Build watch paths, incluir `website/*` (patrón documentado
por Cloudflare, relativo al repositorio y con coincidencia de subrutas). Así un
cambio solo en backend o documentación no despliega la web. Si se añaden herramientas
compartidas usadas en el build, incluir sus rutas también. Comprobar el primer
build manualmente: el filtro puede omitirse en un primer build o cambios de configuración.
No usar Actions y Cloudflare como dos publicadores simultáneos. Actions valida;
Cloudflare Builds publica después de integrar código aprobado en main.

Documentación oficial: [conectar un Worker existente a GitHub](https://developers.cloudflare.com/workers/ci-cd/builds/),
[configuración de Builds](https://developers.cloudflare.com/workers/ci-cd/builds/configuration/),
[Workers Static Assets](https://developers.cloudflare.com/workers/static-assets/).

## Alternativa: despliegue manual

Solo con autorización de publicación adicional, desde un checkout limpio de `main`
con los dos PR integrados, dentro de `website/`, después de revisar el Worker y dominio:

```powershell
pnpm exec wrangler login
pnpm exec wrangler whoami
pnpm exec wrangler deployments list
pnpm install --frozen-lockfile
pnpm build
pnpm deploy:check
pnpm exec wrangler deploy
```

El propietario debe completar el inicio de sesión. Elegir su cuenta existente,
sin crear una cuenta temporal. No cambiar registros DNS, nameservers o certificados.
Guardar el ID del despliegue anterior; si hace falta revertir, usar **Deployments**
del mismo Worker para recuperar esa versión y comprobar nuevamente el dominio.

## Actualizar textos, fotos y contacto

- Editar navegación y destinos de contacto en `website/src/content.ts`. La política de privacidad sigue en `website/src/App.tsx`.
- Las colecciones, los paquetes y la presentación editorial están en `website/src/Editorial.tsx`.
- Para sustituir fotografías, consultar el [catálogo editorial, las reglas de selección y las capturas](website-editorial-v4/README.md).
- Revisar los metadatos por ruta en `website/scripts/prerender.mjs`, la imagen social en `website/public/og-image.png` y el mapa de rutas en `website/public/sitemap.xml`. Ejecutar `pnpm build` desde `website/` y revisar la vista local antes de publicar.

## Verificación histórica de la primera versión


- Dependencias instaladas en proyecto nuevo; instalación con lockfile completada.
- TypeScript y build de producción generados; auditoría de 18 archivos correcta.
- Simulación de despliegue de Wrangler completada sin bindings. Hubo un aviso local
  de permisos del archivo de log; no hubo publicación ni error del paquete generado.
- Workers local: inicio y privacidad 200; ruta inexistente, `/admin`, `/api` y
  `/.env` 404; CSP presente en todas esas respuestas.
- Revisión visual a 1440×960 y 390×844, sin desbordamiento horizontal; filtro Bodas,
  menú móvil y enlace de privacidad funcionan. Consola revisada sin errores.
- No se ejecutó Lighthouse ni se probó envío de mensajes. No se alteró el CRM.

La auditoría busca patrones conocidos, no es una certificación de ausencia de
todo secreto. Revisar los archivos públicos antes de añadir contenido nuevo.
Encabezados en `public/_headers`, según [Cloudflare](https://developers.cloudflare.com/workers/static-assets/headers/).
