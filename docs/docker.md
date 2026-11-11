# Panel privado con Docker Desktop

Desde la raíz de este repositorio, Docker Desktop en modo **contenedores Linux** y Compose v2 reciente o posterior. El panel React se compila en la imagen y FastAPI sirve tanto la interfaz como la API. PostgreSQL 18 y los documentos tienen volúmenes distintos. El flujo siguiente es para **un proyecto nuevo de desarrollo**, con datos propios.

## Primera instalación en PowerShell

1. Comprueba el contexto y los nombres libres. Usaremos `jordy-lab`, el puerto 18000 para el panel y el 15432 para PostgreSQL. El escritorio existente puede seguir usando 8000 y 55433. Si el proyecto, sus volúmenes o sus puertos ya están en uso, elige otros. Conserva el nombre elegido para los próximos arranques.

   ```powershell
   docker context show
   docker version
   docker compose version
   docker compose ls --all
   docker volume ls --filter label=com.docker.compose.project=jordy-lab
   Get-NetTCPConnection -State Listen -LocalPort 18000,15432 -ErrorAction SilentlyContinue
   ```

2. Genera tres claves independientes en un archivo privado ignorado por Git. Este bloque falla si `.env.compose` ya existe. Guarda una copia protegida para recuperar el acceso. Usa una sesión de PowerShell sin variables homónimas predefinidas, pues las variables de sesión tienen prioridad sobre el archivo.

   ```powershell
   function New-JordySecret {
       $bytes = New-Object byte[] 32
       $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
       try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
       [Convert]::ToBase64String($bytes)
   }
   $configPath = Join-Path (Get-Location) '.env.compose'
   $stream = [IO.File]::Open($configPath, [IO.FileMode]::CreateNew)
   $writer = [IO.StreamWriter]::new($stream, [Text.UTF8Encoding]::new($false))
   try {
       foreach ($name in 'POSTGRES_PASSWORD','JORDY_APP_PASSWORD','ADMIN_API_KEY') {
           $writer.WriteLine("$name=$(New-JordySecret)")
       }
       $writer.WriteLine('PANEL_PORT=18000')
       $writer.WriteLine('POSTGRES_HOST_PORT=15432')
       $writer.WriteLine('STUDIO_TIMEZONE=America/Mexico_City')
   } finally { $writer.Dispose() }
   ```

3. Define el atajo para esta terminal. Valida la configuración sin imprimir los valores resueltos. Construye la imagen e inicia únicamente la base.

   ```powershell
   function dc {
       docker compose --project-name jordy-lab --env-file .env.compose @args
       if ($LASTEXITCODE -ne 0) { throw "Falló Docker Compose ($LASTEXITCODE)" }
   }
   dc --profile tools config --quiet
   dc build api
   dc up -d --wait db
   dc run --rm migrate current
   ```

4. **Solo sobre la base nueva o después de revisar un respaldo recuperable**, aplica la cadena de Alembic y los permisos del panel. El destino del job está fijado a la base `jordy` del servicio `db` de este proyecto. El comando por defecto del job consulta la revisión. El cambio de esquema exige el argumento `upgrade`. Un bloqueo de PostgreSQL impide dos preparaciones concurrentes.

   ```powershell
   dc run --rm migrate upgrade
   dc run --rm migrate current
   dc up -d --wait api
   dc ps
   Invoke-RestMethod http://127.0.0.1:18000/health/ready
   Start-Process http://127.0.0.1:18000
   ```

   El estado esperado es `ready`. Abre el panel con **127.0.0.1** y utiliza el valor de `ADMIN_API_KEY` desde tu archivo privado. El origen del navegador debe coincidir exactamente. El acceso automático de escritorio está deshabilitado. Para una base que ya tiene datos comprueba el nombre del proyecto, el volumen y la revisión antes de ejecutar cualquier actualización. Cambiar el nombre del proyecto selecciona otros volúmenes.

## Servicios, variables y límites

| Elemento | Uso |
|---|---|
| `api` | Usuario Linux 10001, una instancia de Uvicorn. La comprobación de disponibilidad verifica revisión Alembic y panel compilado. El programador comercial existente corre dentro de ese proceso. |
| `db` | PostgreSQL 18, rol propietario `jordy`, base `jordy`. Conserva `postgres_data:/var/lib/postgresql` y la publicación heredada en loopback. `POSTGRES_PASSWORD` corresponde al propietario. El inicializador oficial solo usa esa contraseña al crear el volumen por primera vez. |
| `migrate` | Tarea manual del perfil `tools`, con acceso de propietario, sin clave del panel. Crea el rol `jordy_app` si falta, verifica su acceso y concede permisos de datos tras el upgrade. La revisión de Alembic queda de solo lectura para la API. Repetir el comando conserva la contraseña y los datos. Reservar esta base y su esquema público exclusivamente para Jordy Booking. |
| `JORDY_APP_PASSWORD` | Contraseña del rol restringido que usa FastAPI, mínimo 32 caracteres, distinta de la de PostgreSQL. Las conexiones usan el DNS interno `db` y libpq recibe la contraseña por separado. Una URL de escritorio en `.env` queda fuera del contenedor. |
| `ADMIN_API_KEY` | Clave administrativa de al menos 32 caracteres. Su rotación también invalida las sesiones firmadas. |
| `PANEL_PORT`, `POSTGRES_HOST_PORT` | Puertos del host publicados solo en 127.0.0.1. Valores por defecto 8000 y 5432. Los servicios se comunican por la red interna `data`. Los dos puentes para el host permiten publicar cada puerto sin compartir otra red entre panel y BD. |
| `STUDIO_TIMEZONE` | Zona de la agenda y resúmenes. Por defecto `America/Mexico_City`. |
| `MESSAGING_ENABLED` | `false` por defecto. Apagada, `/api/messaging/*` y `/api/commercial/*` responden 404, el programador de resúmenes no arranca y `/pendientes` de Telegram omite los seguimientos. El código y las tablas de WhatsApp se conservan. |
| `documents` | Se monta en `/var/lib/jordy/documents`, fuera de `/app/frontend/dist`. PostgreSQL conserva las versiones, referencias y SHA-256. La descarga se hace por la API autenticada. |

Las dependencias de Python y del panel se instalan desde `uv.lock` y `frontend/pnpm-lock.yaml`, con las versiones de herramientas del proyecto. Para actualizar imágenes base, revisar **etiqueta y digest** en un PR y repetir las pruebas. El contexto de construcción admite los archivos enumerados en `.dockerignore`. Las credenciales se inyectan al ejecutar los contenedores y son accesibles a quien administre Docker. Evita publicar la salida completa de `docker inspect` o `docker compose config`.

## Prueba y operación

La comprobación de Compose arranca su propio proyecto con nombres, puertos y credenciales temporales. Comprueba que el arranque deja el esquema vacío, ejecuta el upgrade dos veces, comprueba privilegios y autenticación, sirve un recurso JavaScript y guarda una reserva y un PDF. Después recrea los servicios y verifica la reserva y los bytes de la descarga. Al terminar elimina solo su proyecto de prueba. Requiere Docker y las dependencias de desarrollo.

```powershell
uv sync --locked
uv run pytest -q tests/compose_smoke.py
```

Para el proyecto de desarrollo:

```powershell
dc stop
dc up -d --wait
dc ps
dc logs --tail 30 api
dc down
```

`down` conserva ambos volúmenes. **Evita `down -v`, borrar volúmenes y las operaciones de limpieza global.** Un error de contraseña en un volumen inicializado se resuelve recuperando o rotando explícitamente la credencial, nunca reinicializando ese volumen. Un estado `unhealthy` requiere revisar base, revisión y build. Las políticas de reinicio recuperan procesos que salen. Un healthcheck fallido por sí solo no reinicia el contenedor.

## Datos existentes, respaldo y reversión

El lanzador Windows comprueba un clúster propio en `.local/panel-pgdata` y la base `jordy_panel` en el puerto 55433. El ejemplo anterior no lo importa. Para evaluar un traslado, usar una ventana y un proyecto de restauración distintos:

1. Identificar origen, revisión Alembic, versión real de PostgreSQL y `DOCUMENT_ROOT` efectivo. Inventariar reservas, ocupaciones, contratos, documentos por versión y estado de outbox. Detener todos los escritores, incluidos panel, receptor y workers. Mantener desactivado el tráfico de integraciones en el destino.
2. Obtener un respaldo lógico en formato custom con el `pg_dump` compatible del origen (`-Fc --file=...`). Copiar en el mismo corte **todos** los originales del directorio privado. Guardar ambos fuera del equipo con acceso restringido y registrar sus hashes. En Windows, usar un archivo para el dump binario, evitando redirigirlo mediante un pipeline de texto de PowerShell.
3. En un proyecto nuevo, arrancar solo `db`. Copiar el dump al contenedor y restaurarlo **antes del upgrade**, a la BD vacía del ensayo, con `pg_restore --exit-on-error --single-transaction --no-owner --no-privileges -U jordy -d jordy <archivo>`. Restaurar originales en el volumen `documents` con acceso restringido para UID 10001. Usar siempre nombres de volúmenes del proyecto de restauración. No montar el directorio físico de PostgreSQL Windows en Linux.
4. Verificar la revisión restaurada, aplicar el upgrade explícito en el ensayo y contrastar inventarios, secuencias de ID, `btree_gist` y todos los hashes registrados. Probar desde la API la descarga de una versión anterior, la autorización y una operación con datos sintéticos. Documentar discrepancias y tiempo de recuperación. El corte operativo requiere un ensayo satisfactorio con la copia autorizada del estudio.
5. **Revertir el ensayo** con `dc down` y volver al acceso directo Windows. Este PR conserva el código y los datos de escritorio. Para revertir la infraestructura en Git se puede revertir el commit del PR. Ante una migración aplicada, recuperar en volúmenes nuevos la pareja BD/documentos previamente validada. La migración comercial bloquea el downgrade destructivo. Si el destino ya recibió escrituras reales, congelarlo y conciliarlas antes de volver a abrir el origen.

Esta etapa cubre el administrador local. La web pública y sus despliegues siguen su propio procedimiento.
