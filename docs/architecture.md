# Arquitectura y decisiones

## Mapa del repositorio

```text
backend/jordy/
  main.py, api.py, auth.py               aplicación privada y autenticación
  domain.py, repository.py, services.py  reglas, recursos y transacciones de reservas
  crm.py, customers.py, search.py        oportunidades, contactos y búsquedas
  documents.py                          originales privados y versiones
  commercial*.py                        señales, propuestas y resúmenes
  messaging/                            webhook, proveedor, bandeja y worker WhatsApp
  telegram/                             autorización, comandos y long polling privado
  admin_reads.py, admin_queries.py       casos de consulta y proyecciones PostgreSQL
  integrations.py, worker.py            adaptador y outbox de calendario
frontend/src/                           panel React servido por FastAPI
website/{src,public,scripts}/           portafolio estático con build propio
migrations/versions/                    historial Alembic compartido
scripts/                                arranque local y verificaciones operativas
tests/                                  pruebas por componente y esquema efímero
docs/                                   guías, decisiones y evidencia histórica
.github/workflows/                      validación de backend, panel y web
```

**Reserva y CRM.** El panel llama a la API del mismo origen. El CRM convierte una
cotización en una solicitud con el snapshot acordado. La aprobación asigna recursos
y una reprogramación confirmada los vuelve a asignar. PostgreSQL protege contra solapamientos incluso
si dos solicitudes compiten. Las citas administrativas y las fechas comerciales
tienen tablas y ciclos de vida propios.

**Canales.** El webhook de WhatsApp valida y persiste eventos. Su worker procesa
la cola y aplica la política de envío. La web pública solo ofrece enlaces de contacto.
Telegram identifica al operador y llama a casos de consulta del backend. Iniciar
FastAPI para atender Telegram también iniciaría la recuperación de resúmenes,
capaz de escribir datos. Por eso los procesos tienen puntos de entrada separados.

**Contrato de lectura.** `telegram/commands.py` entrega parámetros a
`AdminReads.agenda`, `availability` o `pending`. Los casos devuelven registros
inmutables con límite y un indicador de más resultados. `admin_queries.py` abre
una transacción PostgreSQL `REPEATABLE READ, READ ONLY` por comando. Las tres
operaciones son también el punto de extensión para otro cliente, incluida una
futura interfaz con IA. La interfaz solo necesita esas operaciones y sus
resultados. El proceso que la aloje debe conservar la autorización del operador.

## Auditoría y orden de trabajo

| Hallazgo en la base del PR #5 | Decisión y criterio de revisión |
| --- | --- |
| `telegram.py` reunía transporte HTTP, permisos, respuestas y arranque. Añadir PostgreSQL ahí acoplaría los fallos de consultas al polling. | Separar adaptador y lecturas. Conservar el punto de entrada y los tests de la primera versión como prueba de equivalencia. |
| El criterio «necesita respuesta» vivía dentro de la serialización HTTP de la bandeja. El motor de disponibilidad ya contempla preparación, márgenes y asignación por capacidad. | Reutilizar el criterio de bandeja y la consulta de disponibilidad. Telegram solo presenta resultados e identificadores necesarios. |
| `project-status.md` y `NEXT_SESSION.md` repiten estados fechados. El README aún presentaba la integración inicial como pendiente. | Crear [un índice por tarea](README.md), corregir referencias actuales y preservar las bitácoras con fecha. |
| Los scripts PowerShell repiten cómo localizar el proyecto y Python. Panel, receptor, túnel y Telegram necesitan controles y ciclos de vida diferentes. | Conservar los lanzadores públicos. Separar la creación de datos de prueba del instalador del panel, que también prepara la base operativa. |
| Panel y web usan React y TypeScript pero publican artefactos distintos, con versiones y dependencias propias. Las migraciones registran todos los modelos en el mismo esquema. | Conservar ambos lockfiles y las cuatro migraciones existentes. Una consulta sobre tablas actuales no requiere DDL. |

### Cambios que requieren otro PR

1. **Acceso operativo.** Probar un rol PostgreSQL con permisos SELECT limitados a
   las tablas requeridas en una instalación de ensayo. Separar su rotación de la
   credencial del panel antes de ampliar el número de operadores.
2. **Rutas y transacciones.** `commercial.py` reúne HTTP, detección, generación
   de informes y recuperación programada. `messaging/api.py` consulta cliente,
   último mensaje e indicadores por conversación. Separar primero las lecturas
   con pruebas de equivalencia de filtros y tiempos. Medir consultas por página
   antes de modificar la serialización del panel. Mover modelos entre módulos
   requeriría verificar el registro en Alembic y los cuatro upgrades históricos.
3. **Interfaz privada.** `main.tsx` y `features.tsx` superan 32 KB cada uno y
   combinan formularios, selección y recarga. Extraer una pantalla por PR con
   comprobaciones de sesión, navegación y borradores. El volumen de
   `tests/test_messaging.py` por sí solo no justifica mover sus escenarios.
4. **Escala.** Evaluar índices y paginación con planes de ejecución sobre datos
   sintéticos representativos si las consultas llegan al límite habitual.
   Mantener las pruebas concurrentes de ocupación antes de cambiar bloqueos.

## ADR 001 — Monolito modular y primer corte vertical

Estado: enfoque aprobado por el usuario; implementación inicial administrativa.

FastAPI expone contratos Pydantic; servicios coordinan transacciones SQLAlchemy;
dominio implementa matching y transiciones sin depender de HTTP. Repositorio concentra
consultas de recursos. PostgreSQL es la fuente principal. Alembic versiona el esquema.

Se evita crear un repositorio genérico por tabla: no aporta valor a este tamaño.
El panel React/TypeScript/Vite consume la misma API desde el mismo origen. Usa una
sesión firmada HttpOnly, SameSite=Strict, de ocho horas; las mutaciones con cookie
requieren Origin exacto. La clave administrativa no se incluye en JavaScript.

## ADR 002 — Consistencia de recursos

En confirmaciones y reprogramaciones se bloquea la reserva y después los recursos en
orden de ID. Los bloqueos manuales usan el mismo orden de recursos. Todas las ocupaciones
activas comparten `EXCLUDE USING gist (resource_id WITH =, tstzrange(...) WITH &&)`.
`btree_gist` se instala por migración. La comprobación de disponibilidad es orientativa;
la confirmación vuelve a calcular dentro de la transacción.

El bloqueo conservador de todos los recursos serializa operaciones de agenda, adecuado
para ocho trabajadores. Limita el rendimiento a gran escala; se puede reducir a candidatos
cuando exista evidencia de necesidad. Las pruebas usan PostgreSQL real, no SQLite.

## ADR 003 — Acceso administrativo local

Una clave de al menos 32 caracteres configura el acceso administrativo. Comparación
en tiempo constante; los endpoints de datos requieren clave o sesión administrativa.
Health, configuración pública de acceso y descripción OpenAPI no contienen datos del
estudio. La identidad auditada es `jordy-admin`.
No es RBAC multiusuario: portal y cuentas individuales quedan pendientes. Mantener
el servicio en localhost; producción requiere autenticación individual, HTTPS,
limitación de solicitudes, políticas de sesión, observabilidad y despliegue revisado.

## ADR 004 — Integraciones desacopladas

Outbox guarda eventos junto con la reserva. Worker separado toma lotes con SKIP LOCKED,
reintenta hasta cinco veces y aplica backoff. El adaptador de calendario es simulado;
no ofrece sincronización, historial externo ni entrega real. Sus eventos contienen ID
y acción, y el adaptador real deberá consultar la versión vigente de la reserva y
resolver orden/versiones, idempotencia y reconciliación antes de conectarse.

Recomendación para un calendario nuevo: evaluar Outlook/Microsoft Graph por sus
notificaciones de cambios. Si Jordy ya opera en iCloud, verificar su calendario y
probar CalDAV autorizado antes de considerar migración. No se han solicitado credenciales.

Referencias consultadas:
- https://learn.microsoft.com/en-us/graph/outlook-change-notifications-overview
- https://support.apple.com/en-us/102654
- https://www.postgresql.org/docs/17/rangetypes.html

## ADR 005 — Contactos, CRM y búsquedas

`customers.py` captura contactos y advierte duplicados por teléfono/correo normalizados,
incluido el campo de contacto antiguo cuando contiene únicamente teléfono o correo.
No fusiona nombres. Bloqueos consultivos transaccionales serializan altas del mismo
identificador; una excepción explícita permite personas distintas que comparten contacto.
La captura ocasional y la solicitud se guardan juntas, conservando la idempotencia anterior.

`crm.py` gestiona oportunidades, versiones inmutables de cotización y citas. Se bloquea
primero la oportunidad y después el paquete al cotizar o solicitar desde una cotización.
El snapshot de la cotización elegida pasa a la reserva; no se toma el nuevo precio del
catálogo. Una oportunidad no ocupa recursos. La confirmación conserva el motor previo.

`search.py` aplica filtros, conteos, orden estable por fecha e ID y paginación en PostgreSQL.
React solicita páginas de reservaciones, contactos, oportunidades, citas y documentos;
el calendario recibe conteos por día y una página del día seleccionado. Los catálogos
pequeños de recursos/paquetes mantienen el cargador anterior. Los límites, índices,
clasificación y semántica de fechas se explican en [CRM y documentos](crm-documents.md).

## ADR 006 — Almacenamiento privado y escritorio

Los originales se guardan fuera del directorio público con nombres UUID; PostgreSQL
conserva metadatos/versiones. `documents.py` verifica PDF con pypdf e imágenes con Pillow.
Estas dos dependencias se incorporaron porque comprobar extensiones o cabeceras no
valida realmente esos formatos; no se añadió un framework ni servicio de almacenamiento.
La firma, la asociación del archivo y el visto bueno son acciones separadas.

El acceso directo usa `start-panel.ps1` → `launch_panel.py`, sin servicio permanente.
El lanzador verifica el cluster y la revisión de Alembic, pero no inicializa ni migra.
Un bloqueo de archivo impide arranques simultáneos. `/health/ready` comprueba la base,
la revisión y el frontend, e identifica este checkout mediante un hash sin exponer rutas.


## ADR 007 — Mensajería oficial con entrada aislada

Se conserva el monolito y la misma outbox con discriminador de tema. La aplicación ASGI
`jordy.messaging.webhook:app` solo expone GET/POST de Meta en loopback:8001; el panel
permanece privado en :8000. Firma sobre bytes originales, persistencia antes de aceptar
y procesamiento transaccional separado. El adaptador real Graph valida habilitación,
cuenta, destinatario autorizado y ventana/plantilla antes de cada envío manual.
Un intento incierto nunca se reenvía automáticamente. `accepted` no significa `delivered`.
La identidad pertenece al canal/cuenta y se vincula a un cliente por teléfono único exacto
o confirmación administrativa. No se crean reservaciones ni cotizaciones por mensajes.
Ver [arquitectura, límites y operación de WhatsApp](whatsapp.md). El estado inicial
de esta integración y su prueba posterior se documentan en el ADR 008.

## ADR 008 — Identidad entrante y destinatario de envío distintos (19 octubre 2026)

La prueba del usuario confirmó que `wa_id` y `to` pueden diferir para su contacto de
prueba mexicano. No se deduce una transformación por país ni se modifican conversaciones
o clientes históricos. `WHATSAPP_RECIPIENT_BINDINGS` contiene asociaciones administrativas
explícitas por WABA, Phone Number ID e identidad entrante. El destino de cada asociación
debe seguir perteneciendo a `WHATSAPP_ALLOWED_RECIPIENTS`; asociar no autoriza.
Sin asociación solo se conserva el comportamiento anterior cuando la identidad misma
está expresamente autorizada. Asociaciones ambiguas o de otra cuenta no se aplican.

La validación devuelve el destino exacto. Al encolar se conserva en `messages.details`
y al despachar se compara nuevamente con la resolución vigente. No se enruta usando
datos recibidos del contacto. React muestra el destino y puede enviar `expected_recipient`
como comprobación de lo revisado, nunca como instrucción para elegir otro número.
Se conserva la idempotencia de solicitudes existentes; su respuesta mantiene la ruta original.

Cada trabajo nuevo conserva una revisión opaca de configuración, calculada con HMAC
usando el token como clave y los ajustes de envío como contenido. No contiene el token.
El procesador compara su revisión efectiva antes de contactar Meta: discrepancias
de token, emisor, lista, asociación o política bloquean el trabajo sin reintento.
Los archivos de configuración ahora se resuelven desde la raíz del repositorio; las
variables de entorno mantienen prioridad y cada proceso conserva caché hasta reiniciarse.
El panel muestra su revisión y el worker imprime solo su prefijo para poder compararlos.

`SendPolicyViolation`, subtipo de `RuleViolation`, mantiene HTTP 422 y el `detail`
legible del contrato administrativo. El worker almacena categorías específicas en
`error_code`/`last_error`. El adaptador conserva solo estado HTTP y código numérico Meta,
nunca su mensaje completo. Los callbacks se correlacionan por cuenta/ID de mensaje y
por identidad observada o destino guardado al encolar, sin resolver alias dinámicamente.
No se añade migración ni se actualizan mensajes históricos.
