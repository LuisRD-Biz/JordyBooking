# Telegram administrativo privado · @JordyBookingBot

El proceso local `jordy.telegram` recibe mensajes por HTTPS y consulta PostgreSQL
directamente. Se ejecuta por separado del panel, del worker de WhatsApp y de la web pública.
La autorización exige que el remitente sea una persona de la lista permitida en su propio
chat privado. Los comandos administrativos abren transacciones de solo lectura.

## Pruebas locales en Windows

Desde PowerShell, en la raíz del repositorio, con `uv` y los binarios de PostgreSQL
instalados, ejecuta lo siguiente. Ajusta `PG_BIN` a la carpeta que contiene `initdb.exe`
y `pg_ctl.exe` si instalaste otra versión.

```powershell
uv sync --locked
$env:PG_BIN = 'C:\Program Files\PostgreSQL\18\bin'
.\.venv\Scripts\python.exe scripts/test-postgres.py -q -k telegram
```

Este comando crea un clúster temporal en loopback, aplica las migraciones en esquemas
de prueba, utiliza registros sintéticos y detiene el clúster al terminar. El transporte
Telegram está simulado. Para ejecutar toda la suite, omite `-k telegram`.

## Configuración de la instancia autorizada

1. **Token.** En la raíz del repositorio crea `.env.telegram` con un editor local.
   Guarda el token de **@JordyBookingBot** obtenido por su propietario desde
   BotFather. Usa una carpeta accesible solo a los operadores de confianza.
   El archivo ya está excluido por Git. No pegues el token en comandos, chats o PR.

   ```dotenv
   TELEGRAM_BOT_TOKEN=REEMPLAZAR_EN_LOCAL
   TELEGRAM_ALLOWED_USER_IDS=[]
   ```

2. **Identificar a Jordy sin contactar con ningún bot.** Desde su propia cuenta
   en Telegram Desktop, Jordy abre Ajustes → Avanzados → Exportar datos de Telegram,
   selecciona solo información de la cuenta, sin chats ni medios, y formato JSON.
   En la carpeta exportada, fuera del repositorio, lee
   `personal_information.user_id` en `result.json`. Ese campo contiene el ID de
   la cuenta ([formato de Telegram Desktop](https://github.com/telegramdesktop/tdesktop/blob/dev/Telegram/SourceFiles/export/output/export_output_json.cpp)).
   Confirma únicamente el número con Jordy en persona o por un canal ya verificado;
   no compartas el archivo exportado. No uses su alias, teléfono ni el ID del bot.

3. **Autorizar.** Sustituye `[]` por una lista JSON con el número confirmado,
   sin comillas. Con la lista vacía o inválida el proceso no se conecta.
   Cada cambio de la lista, incluida una revocación, requiere reiniciar el proceso.
   Comprueba que no haya variables de entorno `TELEGRAM_*` anteriores que
   sustituyan los valores del archivo.

4. **PostgreSQL y calendario.** El worker lee `DATABASE_URL` y `STUDIO_TIMEZONE`
   de `.env` en la raíz. Las variables del proceso tienen prioridad. Usa la conexión
   del estudio con el esquema migrado y, si se dispone de él, un rol con permisos
   de lectura. El valor predeterminado de la zona es `America/Mexico_City`.
   El worker solo carga los ajustes que necesita y no ejecuta migraciones.

5. **Arranque real, solo con autorización previa.** Verifica que haya un único host
   encargado del bot. Desde la raíz ejecuta `.\scripts\start-telegram.ps1` y abre
   el chat privado de **@JordyBookingBot** desde la cuenta autorizada.
   Detén el proceso con Ctrl+C.

## Comandos

| Comando | Qué devuelve |
| --- | --- |
| `/start` | «¡Hola, Jordy! El bot está listo.» |
| `/ping` | «pong» |
| `/agenda`, `/agenda hoy`, `/agenda mañana`, `/agenda 2026-11-15` | Reservas que coinciden con el día local, incluidas las que cruzan la medianoche. Muestra ID, inicio, fin, tipo y estado registrado. |
| `/agenda semana` | Desde hoy hasta el sexto día siguiente, ambos incluidos, en la zona del estudio. |
| `/disponibilidad 2026-11-15 16:30 7` | Ejemplo de formato. Sustituye `7` por un ID de paquete real. El motor comprueba requisitos, duración, preparación, margen y ocupaciones activas. Muestra los IDs de recursos sugeridos y sus funciones cuando hay asignación posible. La consulta es preliminar. La confirmación pertenece al flujo de reservas del estudio. |
| `/pendientes` | Solicitudes de reserva por aprobar y conversaciones de WhatsApp en atención humana que esperan respuesta, con su ID y hora del último mensaje entrante. Un envío en cola o fallido deja el seguimiento pendiente. |

Si omites la fecha, la hora o el paquete en `/disponibilidad`, el bot te indica
qué falta. Reenvía el comando completo con la hora de inicio en formato de 24 horas.
Para consultar los IDs de paquete, inicia sesión en el panel y abre `/docs` en ese
mismo origen. En `GET /api/packages`, selecciona **Try it out** y **Execute**, y busca
el `id` que corresponde al `name` del paquete. El bot admite hasta 15 resultados por
lista e indica cuando existen más. Las respuestas omiten nombres, teléfonos, direcciones
y textos de conversaciones de clientes.

## Fallos y recuperación

- Si la conexión falla durante una consulta, el bot responde con un aviso breve.
  Cada comando abre su propia sesión y permite reintentar cuando PostgreSQL se recupere.
  Una lista vacía solo se muestra después de que la consulta se haya completado.
- Si la configuración de la base o de la zona es inválida al arrancar, el worker
  conserva `/start` y `/ping`. Corrige los ajustes y reinicia para habilitar las consultas.
- Un bloqueo del sistema operativo impide dos consumidores del mismo bot bajo el mismo
  usuario local, incluso entre copias del repositorio. El bloqueo se libera al salir.
  Entre equipos o cuentas distintas sigue siendo necesario designar un solo consumidor.
  Un error 409 de Telegram detiene el worker. Revisa otros procesos y webhooks antes de
  reiniciar. Con 401, revisa el token en el archivo privado.
- Ante un fallo transitorio de Telegram, el worker reintenta. Una interrupción después
  de contestar y antes de confirmar el cursor de recepción puede repetir una respuesta.
  Cada comando es de lectura.
