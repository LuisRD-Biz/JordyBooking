import re

from jordy.domain import RuleViolation

ERRORS = {
    "send_policy_blocked": (
        "Este intento fue bloqueado por las validaciones de envío. "
        "El registro antiguo no identifica cuál; revisa la configuración actual."
    ),
    "http_400": (
        "Meta rechazó este mensaje. El registro antiguo no conserva una causa específica."
    ),
    "http_401_meta_190": (
        "WhatsApp no pudo enviar este mensaje. La credencial puede ser inválida, "
        "haber caducado o estar revocada. Revisa la credencial de Meta "
        "en la configuración privada."
    ),
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


def error_diagnostic(code):
    if not code:
        return None
    if code == "http_401_meta_190" or code == "meta_190":
        return {"category": "credential", "message": ERRORS["http_401_meta_190"], "code": code}
    if re.fullmatch(r"http_(429|5\d\d)(?:_meta_\d+)?", code):
        return {
            "category": "provider_temporary",
            "code": code,
            "message": "El proveedor limitó o no pudo atender este intento. No se reenvió.",
        }
    if code in {"provider_result_unknown", "send_result_unknown"}:
        return {
            "category": "review",
            "code": code,
            "message": "Resultado incierto: comprueba la recepción antes de repetir.",
        }
    return {
        "category": "attempt",
        "code": code,
        "message": ERRORS.get(code, "Este intento no se completó. Revisa su diagnóstico."),
    }


class SendPolicyViolation(RuleViolation):
    def __init__(self, code):
        self.code = code
        super().__init__(ERRORS[code])


def resolve_recipient(config, conversation):
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
