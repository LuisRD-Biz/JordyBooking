# Arquitectura y decisiones

## ADR 001 — Monolito modular y primer corte vertical

Estado: enfoque aprobado por el usuario; implementación inicial administrativa.

FastAPI expone contratos Pydantic; servicios coordinan transacciones SQLAlchemy;
dominio implementa matching y transiciones sin depender de HTTP. Repositorio concentra
consultas de recursos. PostgreSQL es la fuente principal. Alembic versiona el esquema.

Se evita crear un repositorio genérico por tabla: no aporta valor a este tamaño.
Un futuro panel React/TypeScript/Vite consume la misma API. No usar la clave de este
entregable en un frontend público: antes se implementarán sesiones de usuario seguras.

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
en tiempo constante; ningún endpoint de datos está disponible sin esa clave. Solo
health y descripción OpenAPI son públicos. La identidad auditada es `jordy-admin`.
No es RBAC multiusuario: portal y cuentas individuales quedan pendientes. Mantener
el servicio en localhost; producción requiere autenticación individual, HTTPS,
limitación de solicitudes, políticas de sesión, observabilidad y despliegue revisado.

## ADR 004 — Integraciones desacopladas

Outbox guarda eventos junto con la reserva. Worker separado toma lotes con SKIP LOCKED,
reintenta hasta cinco veces y aplica backoff. El único adaptador disponible es simulado;
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
