from jordy.admin_reads import AdminInputError, AdminReads, AdminReadUnavailable, BookingItem

REPLIES = {"/start": "¡Hola, Jordy! El bot está listo.", "/ping": "pong"}
UNAVAILABLE = "La consulta no está disponible. Inténtalo de nuevo en unos momentos."
AVAILABILITY_USAGE = "Usa /disponibilidad AAAA-MM-DD HH:MM ID_PAQUETE."
KINDS = {"session": "Sesión", "event": "Evento"}
STATUSES = {
    "pending_approval": "por aprobar",
    "confirmed": "confirmada",
    "cancelled": "cancelada",
    "completed": "completada",
}


def booking_line(item: BookingItem) -> str:
    same_day = item.starts_at.date() == item.ends_at.date()
    end = item.ends_at.strftime("%H:%M" if same_day else "%Y-%m-%d %H:%M")
    return (
        f"#{item.id} · {item.starts_at:%Y-%m-%d %H:%M}–{end} · "
        f"{KINDS[item.kind]} · {STATUSES[item.status]}"
    )


def agenda(reads: AdminReads, args: list[str]) -> str:
    if len(args) > 1:
        return "Usa /agenda hoy, /agenda mañana, /agenda semana o /agenda AAAA-MM-DD."
    result = reads.agenda(args[0].lower() if args else "hoy")
    dates = str(result.start_day)
    if result.end_day != result.start_day:
        dates += f" al {result.end_day}"
    lines = [f"Agenda del {dates} ({reads.zone})"]
    lines.extend(booking_line(item) for item in result.bookings)
    if not result.bookings:
        lines.append("Sin reservas para este periodo.")
    if result.more:
        lines.append("Hay más reservas. Consulta el panel para verlas todas.")
    return "\n".join(lines)


def availability(reads: AdminReads, args: list[str]) -> str:
    if len(args) < 3:
        missing = (
            "la fecha, la hora y el ID del paquete",
            "la hora y el ID del paquete",
            "el ID del paquete",
        )[len(args)]
        return f"Indica {missing}. {AVAILABILITY_USAGE}"
    if len(args) != 3:
        return AVAILABILITY_USAGE
    day, at, package_id = args
    if not package_id.isascii() or not package_id.isdecimal() or len(package_id) > 10:
        return f"El ID del paquete debe ser un entero positivo. {AVAILABILITY_USAGE}"
    result = reads.availability(day, at, int(package_id))
    lines = [
        f"Paquete #{result.package_id} · {result.starts_at:%Y-%m-%d %H:%M} ({reads.zone})",
        "Disponibilidad preliminar. No se apartan recursos ni se confirma una reserva.",
    ]
    if result.available:
        lines.append("Hay disponibilidad para el paquete.")
        for resource_id, role in result.assignments:
            lines.append(f"Recurso #{resource_id} · {' '.join(role.split())}")
        if result.more_assignments:
            lines.append("Hay más recursos sugeridos.")
    else:
        lines.append("Los recursos disponibles no cubren los requisitos del paquete.")
    return "\n".join(lines)


def pending(reads: AdminReads, args: list[str]) -> str:
    if args:
        return "Usa /pendientes sin parámetros."
    result = reads.pending()
    lines = [f"Solicitudes de reserva por aprobar ({reads.zone})"]
    lines.extend(booking_line(item) for item in result.bookings)
    if not result.bookings:
        lines.append("Sin solicitudes pendientes.")
    if result.more_bookings:
        lines.append("Hay más solicitudes en el panel.")
    if result.conversations is None:
        return "\n".join(lines)
    lines.append("Conversaciones pendientes de seguimiento")
    for item in result.conversations:
        lines.append(f"#{item.id} · último mensaje recibido {item.last_incoming_at:%Y-%m-%d %H:%M}")
    if not result.conversations:
        lines.append("Sin seguimientos pendientes.")
    if result.more_conversations:
        lines.append("Hay más seguimientos en el panel.")
    return "\n".join(lines)


COMMANDS = {"/agenda": agenda, "/disponibilidad": availability, "/pendientes": pending}


def reply_for(
    update: dict, allowed: frozenset[int], reads: AdminReads | None = None
) -> tuple[int, str] | None:
    msg = update.get("message")
    if not isinstance(msg, dict):
        return None
    sender, chat, text = msg.get("from"), msg.get("chat"), msg.get("text")
    if not isinstance(sender, dict) or not isinstance(chat, dict) or not isinstance(text, str):
        return None
    uid = sender.get("id")
    if (
        type(uid) is not int
        or uid not in allowed
        or sender.get("is_bot") is not False
        or chat.get("type") != "private"
        or type(chat.get("id")) is not int
        or chat["id"] != uid
    ):
        return None
    if reply := REPLIES.get(text.strip()):
        return uid, reply
    words = text.split()
    if not words or words[0] not in COMMANDS:
        return None
    if reads is None:
        return uid, UNAVAILABLE
    try:
        return uid, COMMANDS[words[0]](reads, words[1:])
    except AdminInputError as exc:
        return uid, str(exc)
    except AdminReadUnavailable:
        return uid, UNAVAILABLE
