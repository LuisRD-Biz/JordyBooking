"""Stable internal categories; no provider prose or identifying values in errors."""

import re

from jordy.domain import RuleViolation

ERRORS = {
    "send_disabled": "Los envíos reales están deshabilitados.",
    "token_rotation_required": "Falta confirmar la sustitución del token expuesto.",
    "access_token_missing": "Falta configurar el token de acceso nuevo.",
    "sender_config_invalid": "Falta configurar correctamente la cuenta y el número emisor.",
    "graph_version_invalid": "Falta configurar una versión válida de Graph API.",
    "recipient_not_authorized": "Este destinatario no está autorizado para pruebas.",
    "recipient_unresolved": "Falta una asociación explícita válida para el destinatario de Meta.",
    "human_attention_required": "Abre la conversación bajo atención humana antes de responder.",
    "sender_account_mismatch": "La cuenta o número emisor no coincide con esta conversación.",
    "service_window_expired": "Fuera de la ventana de 24 horas: utiliza una plantilla aprobada.",
    "template_not_authorized": "La plantilla y su idioma no están autorizados.",
    "message_type_unsupported": "Tipo de mensaje no admitido.",
    "send_config_changed": (
        "La configuración de envío cambió entre panel y procesador. Revisa y reinicia ambos."
    ),
    "send_recipient_changed": (
        "El destinatario cambió desde la confirmación. Prepara un mensaje nuevo."
    ),
}


class SendPolicyViolation(RuleViolation):
    def __init__(self, code):
        self.code = code
        super().__init__(ERRORS[code])


def resolve_recipient(config, conversation):
    """Explicit bindings are scoped to WABA + sender. No country-number heuristics."""
    bindings = [
        b
        for b in config.whatsapp_recipient_bindings
        if b.account_id == conversation.account_id
        and b.phone_number_id == conversation.phone_number_id
        and b.external_contact == conversation.external_contact
    ]
    if len(bindings) > 1:
        raise SendPolicyViolation("recipient_unresolved")
    if bindings:
        recipient = bindings[0].send_recipient
    elif conversation.external_contact in config.whatsapp_allowed_recipients:
        recipient = conversation.external_contact
    else:
        raise SendPolicyViolation("recipient_unresolved")
    if not re.fullmatch(r"[0-9]{7,15}", recipient):
        raise SendPolicyViolation("recipient_unresolved")
    if recipient not in config.whatsapp_allowed_recipients:
        raise SendPolicyViolation("recipient_not_authorized")
    return recipient
