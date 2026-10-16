# JordyBooking

Panel administrativo React y API de disponibilidad y reservaciones con PostgreSQL real.
Solicitudes pendientes no bloquean fechas; Jordy confirma sesiones
con lugar acordado y eventos con contrato firmado registrado.

## Desarrollo local

Para abrir el panel en Windows consulta [la guía del panel](docs/panel.md).
La instalación local dispone del acceso directo **Jordy Studio**. Incluye CRM,
cotizaciones versionadas, citas de firma, documentos privados y búsquedas paginadas.
Consulta [cómo usar estas funciones](docs/crm-documents.md).

Requisitos: Python 3.12+, uv y PostgreSQL con permiso para instalar `btree_gist`.
Docker Compose es opcional si ya tienes PostgreSQL.

1. Ejecuta `uv sync --locked`.
2. Copia `.env.example` a `.env`. Configura `DATABASE_URL`, una contraseña local de BD
   y una clave `ADMIN_API_KEY` generada con `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
   La clave y contraseña son diferentes. No publiques `.env`.
3. Si usas Docker: `docker compose up -d db`.
4. Aplica `uv run alembic upgrade head`.
5. Inicia `uv run uvicorn jordy.main:app --app-dir backend --host 127.0.0.1 --port 8000`.
6. Abre http://127.0.0.1:8000/docs y usa **Authorize** con la clave administrativa.

Flujo para probar en `/docs`: crear cliente → recursos y capacidades → paquete con
requisitos → consultar disponibilidad → crear solicitud con `Idempotency-Key` →
registrar contrato si es evento → aprobar indicando lugar → consultar asignaciones.
Los códigos de capacidad son configurables (por ejemplo `photographer`, `assistant`,
`second_camera`, `studio_set`). Registra a cada persona una sola vez.

Para Navidad configura sesión de 90 minutos y `buffer_minutes=30`, preparación 0.
`GET /api/availability/christmas-slots` consulta seis horarios de lunes a viernes
en octubre/noviembre, con disponibilidad compartida con eventos normales. Configura
el set como recurso y requisito si solo puede utilizarlo una sesión a la vez.

## Verificación

```powershell
uv run ruff check backend scripts tests migrations
uv run ruff format --check backend scripts tests migrations
# Base exclusiva de pruebas; el nombre debe terminar en _test.
$env:TEST_DATABASE_URL = 'postgresql+psycopg://usuario:password@localhost:5432/jordy_test'
uv run pytest -q
```

Sin `TEST_DATABASE_URL`, las pruebas de integración se omiten explícitamente.
La suite crea y elimina solo un schema aleatorio propio. Requiere permisos para
crear schemas y extensión; no usa datos del estudio. CI levanta PostgreSQL 18.

El worker de prueba se ejecuta en proceso separado. En PowerShell usa
`$env:PYTHONPATH='backend'; uv run python -m jordy.worker`.
Procesa un lote y marca `simulated`; no envía mensajes ni conecta calendarios.

## Alcance y siguientes pasos

Este corte incluye un panel React con sesión administrativa local. Las cuentas de usuario
individuales están pendientes. No exponer esta versión a Internet. Calendario real, apartado
navideño con vencimiento, recordatorios, portal de clientes e IA aún están pendientes.
La firma se registra como referencia administrativa, no como firma electrónica.

Documentación: [requisitos](docs/requirements.md), [reglas](docs/business-rules.md),
[arquitectura](docs/architecture.md), [modelo ER](docs/database.md), [roadmap](docs/roadmap.md).
