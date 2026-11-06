> Bitácora histórica. Para consultar la arquitectura y las guías vigentes, abre el [índice de documentación](README.md).

# Reorganización Git/CI — 3 de noviembre de 2026

Árbol inicial limpio; web ya publicada en GitHub en `543b1dd`.
Ramas publicadas en GitHub con autorización explícita del usuario.
[PR #1 — base](https://github.com/LuisRD-Biz/JordyBooking/pull/1), commit `ac45671`;
[PR #2 — web, borrador dependiente](https://github.com/LuisRD-Biz/JordyBooking/pull/2),
commit funcional `22ab5c2` sobre web original `543b1dd`. CI remoto de #1 correcto
(frontend, test, security); consultar #2 para el resultado de su ejecución vigente.
`main` verificada sin protección (`protected: false`), sin modificar reglas.

Ramas preparadas: `feature/project-baseline` desde `0d9d1e2` y `feature/website`
desde `543b1dd`. Primero revisar/integrar base con merge commit, después cambiar
el destino del PR web a `main` y revisar/integrar. No se fusiona en esta tarea.
Backend: 136 pruebas locales correctas con PostgreSQL aislado, Ruff y build del panel.
CI web: instalación congelada, TypeScript, build, auditoría y rutas de Workers local.
No se modifican migraciones ni servicios WhatsApp. No se despliega producción.
Cloudflare: rama de producción `main`, raíz `website`, assets `dist`; conexión
y protección de main pendientes de aprobación/configuración. No crear develop.
Ver `website-deployment.md` y los PR para resultados remotos; estados anteriores
a continuación se conservan como antecedentes, no instrucciones actuales.

---

# Estado del proyecto — 3 de noviembre de 2026

## Web pública

- `website/`: React/TypeScript/Vite independiente, diseño editorial adaptable,
  servicios, portafolio filtrable con muestras identificadas, contacto configurable,
  privacidad, 404, HTML prerenderizado, SEO, Open Graph y encabezados de seguridad.
- Build validado y vista local revisada en escritorio y móvil. Rutas privadas 404.
- Configuración preparada para Static Assets del Worker `young-moon-14a9`.
- **Pendiente publicar:** Wrangler sin sesión; dominio verificado todavía con
  Hello World y HTTPS 200. No se hizo push, merge ni cambio sobre main.
- Faltan fotos autorizadas, contactos oficiales y revisión de privacidad.
- CRM, backend y datos no modificados. Estado operativo anterior no revalidado.
- Instrucciones: [website-deployment.md](website-deployment.md).

---

# Estado anterior — 20 de octubre de 2026

## Cierre de jornada

- Mensajes reorganizado en pestañas accesibles con teclado: Mensajes, Señales, Notas,
  Fechas. Lista y conversación se alternan en pantallas pequeñas; el historial
  conserva su scroll y las herramientas no se acumulan encima del formulario.
- Acceso directo a Resumen diario; indicadores de respuesta pendiente y señales
  sin revisar. Los borradores se mantienen al cambiar pestañas del mismo contacto.
- Consulta del mensaje original por señal con validación de conversación.
- Errores históricos desplegables por mensaje; configuración activa y revisión
  pendiente del proveedor diferenciadas, sin reintentos ni cambios de secretos.
- Corregida una falla silenciosa: al no cargar reservas del contacto se muestra
  un error, en lugar de aparentar que no existen.
- Los fallos de conexión ahora usan texto comprensible; los errores de lectura
  se limpian al recuperarse y no se confunden con errores de una acción manual.
- **26 pruebas dirigidas aprobadas**, en PostgreSQL aislado: diagnósticos,
  autenticación, aislamiento, idempotencia y fase 5. No suite completa.
- Compilación aprobada. Se repitió tras corregir el espacio insuficiente del
  historial en pantalla pequeña y el aviso de conexión que quedaba obsoleto.
- Revisión visual en navegador integrado a 697×672: pestañas, formulario, notas,
  propuestas, análisis y acceso al resumen. No se enviaron ni guardaron operaciones
  reales. No se acreditó revisión visual de todas las resoluciones de escritorio.
- Ocho rutas GET locales respondieron 200 (salud, configuración/bandeja, resumen,
  horario, propuestas, reservas y dashboard). Receptor sin firma: 401 esperado.
- Un proceso raíz por componente (panel, receptor y worker), un túnel existente.
- **Pendiente activo de revisión:** último intento con configuración actual
  `http_401_meta_190`. Configuración local sin bloqueos; credencial no comprobada
  remotamente. Cinco fallos históricos conservados. Sin trabajos pendientes al revisar.
- No nuevas migraciones durante el cierre, nuevas dependencias, automatizaciones,
  envíos, cambios de reservas, contratos, secretos ni publicación remota.

Continuación: [NEXT_SESSION.md](NEXT_SESSION.md). Los resultados siguientes de
fase 5 se conservan como historial, no sustituyen este cierre.

## Implementado

- FastAPI + PostgreSQL: clientes, oportunidades, cotizaciones versionadas, reservas,
  disponibilidad, asignaciones, bloqueos y validación de solapamientos.
- Contratos registrados/documentos privados, citas administrativas y auditoría.
- Panel React con sesión administrativa y arranque local Windows.
- WhatsApp Cloud API: receptor aislado, mensajes almacenados, historial de estados,
  cola de envío manual, destinatario autorizado explícito y revisión de configuración.
- Fase 5: reglas deterministas, señales trazables y revisables, notas manuales,
  propuestas comerciales por día sin hora obligatoria, resumen diario persistente,
  ejecución nocturna optativa y recuperación al arrancar.

## Evidencia y alcance

- Recepción WhatsApp real informada por el usuario en la fase anterior. Se mantienen
  los registros recibidos y fallos históricos. El usuario indicó sustituir el token;
  se habilitó el envío manual en el trabajo previo. Esta fase no valida una nueva
  entrega real ni envía mensajes.
- El motor operacional y CRM ya usan PostgreSQL. Sus reglas no se reconstruyeron.
- Fase 5 se validó con PostgreSQL de pruebas en esquema aislado, sin datos reales
  de clientes: idempotencia, reporte reproducible, revisión de otra conversación
  rechazada, relación con oportunidad de otro cliente rechazada, propuesta sin
  cambios a reserva confirmada/contrato y recuperación de días pendientes.
- La prueba lingüística detectó un solapamiento entre fecha ISO y fecha numérica:
  corregido y repetido el grupo afectado. Resultado combinado: **17 casos distintos
  aprobados**. No se ejecutó la suite completa.
- Compilación React/TypeScript/Vite aprobada tras corregir un delimitador JSX.
  No se realizó una prueba visual exhaustiva en navegador.
- Migración `9c51e760ab12` aplicada en la base local; panel reiniciado y
  `/health/ready` respondió correctamente. El resumen del **20/10/2026** se generó
  mediante la API autenticada y quedó guardado con las fuentes locales disponibles.
  Se comprobó que el horario automático sigue sin configurar. No se alteraron
  secretos ni se publicaron cambios en GitHub.

## Simulado o sin conectar

- Calendario externo (iCloud/Outlook/Google): sin integración real.
- Operaciones antiguas de calendario/notificación pueden conservar estado simulado;
  eso no indica que un evento se haya publicado externamente.
- No hay IA ni análisis de audio. Las notas de audio son escritas por Jordy.
- Las pruebas de fase 5 son datos sintéticos; no acreditan comprensión perfecta de
  mensajes comerciales reales.

## Limitaciones y problemas conocidos

- Acceso de un administrador: sin cuentas individuales, roles ni separación de
  múltiples estudios. La etiqueta Jordy representa la identidad administrativa.
- Operación local: sin ejecución con computadora apagada. Túnel de WhatsApp y
  procesos de recepción requieren mantenerse activos para mensajes entrantes.
- No se ha acreditado despliegue público endurecido, copias externas/restauración,
  retención comercial o limitación de frecuencia para producción.
- Fechas sin año, formatos numéricos y días de semana ambiguos requieren revisión.
  Las reglas no cubren todas las expresiones, ironías ni referencias entre mensajes.
- Un reporte guardado requiere regeneración para incorporar información tardía.
- Los listados de señales son completos por conversación; historiales muy extensos
  podrán necesitar paginación adicional. Propuestas en agenda: páginas de 200.
- Advertencia existente de deprecación Starlette/TestClient/httpx en pruebas.
- Los fallos históricos de WhatsApp siguen visibles; un fallo antiguo no demuestra
  un problema activo. Los resúmenes no reintentan envíos.

## Archivos y migración de esta fase

- `backend/jordy/commercial_rules.py`: detección.
- `backend/jordy/commercial_models.py`: cinco tablas nuevas.
- `backend/jordy/commercial.py`: API, revisión, propuestas y reportes.
- `backend/jordy/main.py`: rutas, recuperación nocturna y errores seguros.
- `migrations/versions/9c51e760ab12_commercial_followup.py`, `migrations/env.py`.
- `frontend/src/commercial.tsx`, `messages.tsx`, `main.tsx`, `shared.tsx`, `style.css`.
- `tests/test_commercial.py`, `docs/commercial-followup.md`, este reporte.

## Siguiente fase recomendada

Validar el flujo con Jordy en conversaciones reales, afinar reglas a partir de falsos
positivos revisados y definir políticas de apartados y cambios contractuales.
Después: respaldo/restauración, roles y proveedor de calendario. No automatizar
decisiones de contratación ni envíos a partir de señales.

Uso del resumen y decisiones pendientes: [Guía de fase 5](commercial-followup.md).
