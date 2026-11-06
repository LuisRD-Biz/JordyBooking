REPLIES = {"/start": "¡Hola, Jordy! El bot está listo.", "/ping": "pong"}


def reply_for(update: dict, allowed: frozenset[int]) -> tuple[int, str] | None:
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
    reply = REPLIES.get(text.strip())
    return (uid, reply) if reply else None
