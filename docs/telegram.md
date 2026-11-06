# Telegram privado: @JordyBookingBot

El proceso local `jordy.telegram` usa [getUpdates](https://core.telegram.org/bots/api#getupdates)
para esperar mensajes por HTTPS. No inicia FastAPI, no abre puertos y no necesita
PostgreSQL, ngrok ni un webhook. Usa el entorno Python existente del backend.

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

4. **Arranque y prueba real, solo con autorización previa.** Desde la raíz:

   ```powershell
   .\scripts\start-telegram.ps1
   ```

   Usa una sola instancia. Desde la cuenta autorizada, Jordy abre el chat privado
   con **@JordyBookingBot** y envía `/start`: debe recibir «¡Hola, Jordy! El bot
   está listo.»; `/ping` responde «pong». El bot ignora otros usuarios, grupos
   y comandos. Detén el proceso con Ctrl+C. Si aparece 401, revisa el token; si
   aparece 409, comprueba si hay otro consumidor o un webhook previo. El script
   no los modifica. Una interrupción entre la respuesta y la confirmación de una
   actualización puede repetir una respuesta; los comandos no modifican datos.

**Simulación local**, sin token real ni acceso a Telegram:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_telegram.py -q
```
