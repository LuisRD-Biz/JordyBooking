# Verificación de fase 4 — 16 de octubre de 2026

## Estado de entrega

Backend, almacenamiento, bandeja, adaptador real y controles de envío implementados localmente.
**Prueba real con Meta pendiente** de autorización del usuario, sustitución del token expuesto,
configuración privada y túnel temporal. No se ha abierto un túnel ni enviado un mensaje real.
No se han publicado cambios en GitHub.

## Auditoría y cambios

Base de trabajo limpia: rama `crm-documents`, commit `d21bf2f`. Trabajo en
`codex/whatsapp-cloud-api`. Baseline: **52 pruebas aprobadas**, TypeScript/Vite compilaban.
Se revisaron autenticación, CRM, esquema, migraciones, outbox y arranque Windows.

- Módulo `backend/jordy/messaging/{config,webhook,service,worker,provider,api}.py`.
- Modelos en `backend/jordy/models.py`; router local en `main.py`; filtro de tema en `worker.py`.
- Migración `migrations/versions/7b41c092a661_add_messaging.py`: tres tablas y tema de outbox.
- Bandeja `frontend/src/messages.tsx`; navegación, CRM, enlace a cliente y estilos existentes.
- `tests/test_messaging.py`: pruebas PostgreSQL y transporte HTTP simulado.
- Scripts `start-whatsapp.ps1`, `check_webhook_isolation.py`, `start-webhook-tunnel.ps1`.
- `pyproject.toml`/`uv.lock`: httpx pasa de pruebas a ejecución, sin nuevas versiones.
- README, arquitectura, ERD, roadmap, guía `whatsapp.md` y plantilla privada sin valores.

## Resultados finales

| Comprobación | Resultado |
|---|---|
| Suite completa PostgreSQL | **90 passed**, incluyendo 38 casos de mensajería y los 52 previos |
| Ruff backend/pruebas/migraciones/comprobador | Sin hallazgos |
| TypeScript + Vite | Compilación correcta, 2422 módulos |
| `uv lock --check --offline` | Correcto, 37 paquetes; no se cambiaron versiones |
| `alembic check` sobre la base local migrada | Sin diferencias de esquema pendientes |
| Receptor real temporal 127.0.0.1:8001 | Rutas/métodos aislados comprobados por HTTP; detenido al finalizar |
| Panel real 127.0.0.1:8000 | Mensajes abre correctamente, estado vacío real y envíos deshabilitados |
| Vista sintética aislada 127.0.0.1:8002 | Historial entrante/saliente, estado, vista previa y enlace a oportunidad correctos; no se confirmó envío |
| Conservación de datos | 16 tablas previas comparadas por número de filas y hashes de su contenido: sin cambios |

Las pruebas cubren challenge, firma incorrecta/ausente/manipulada, límites, aislamiento,
fallos de almacenamiento y reintentos, duplicados concurrentes, contactos conocidos/nuevos/
ambiguos, tipos desconocidos, estados tardíos/anticipados, paginación, autenticación,
destinatarios/plantillas/ventana/token/habilitación, HTTP error, timeout y resultado incierto,
commit previo a red, concurrencia de envío, reinicio durante envío y aislamiento del calendario.
Avisos de sistema y multimedia no abren la ventana local; desviación futura de reloj no la extiende.

Advertencia existente: TestClient de Starlette marca obsoleto su uso de httpx y propone httpx2.
No provoca fallos; no se cambió el stack de pruebas por esta advertencia.

## Base operativa y limpieza

Respaldo previo: `.local/backups/before-whatsapp-20261016-225207.dump`.
Migración aditiva aplicada y servidor local reiniciado. La comparación se guardó sin contenido
de clientes en `.local/whatsapp-migration-verification.json`. Había cero documentos en el
directorio configurado; no se eliminó ni modificó ese directorio ni PostgreSQL existente.

La vista sintética utilizó un esquema exclusivo `preview_<UUID>` en `jordy_panel_test`.
Se cerró su servidor y se eliminó exclusivamente ese esquema temporal al concluir.
No se insertaron conversaciones ficticias en `jordy_panel`. El receptor de prueba también
se detuvo y se comprobó que 8001 quedó cerrado. No se inició ningún procesador de envío real.

## Pendientes para aceptación completa

Sustituir token expuesto, rellenar configuración privada y versión vigente, autorizar
destinatario/túnel/envíos, suscribir `messages` de la WABA y realizar con el usuario el recorrido
teléfono → webhook → PostgreSQL → bandeja → respuesta → teléfono → callback de entrega.
Registrar ese resultado después de hacerlo; este documento no lo da por probado.

Limitaciones y políticas de privacidad pendientes: [guía de WhatsApp](whatsapp.md).
Instrucciones para iniciar y detener componentes, configurar Meta y conceptos explicados
sin jerga se encuentran en esa misma guía.
