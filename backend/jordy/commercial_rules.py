"""Conservative Spanish rules. A detection is never a booking instruction."""

import re
import unicodedata
from datetime import date, timedelta
from zoneinfo import ZoneInfo

MONTHS = (
    "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre"
).split()
WEEKDAYS = "lunes martes miercoles jueves viernes sabado domingo".split()
PATTERNS = {
    "price": r"\b(precio|cuanto cuesta|cuanto sale|costo|cotiza\w*|paquetes?)\b",
    "wedding": r"\b(bodas?|casamiento|matrimonio)\b",
    "xv": r"\b(xv|15 anos|quince anos|quinceanera\w*)\b",
    "session": r"\b(sesion(?:es)?|navidad|navidena\w*|retrato\w*)\b",
    "other_service": r"\b(bautizo|graduacion|comunion|cumpleanos|evento|video)\b",
    "availability": r"\b(disponib\w*|tienen (?:esa |la )?fecha|fecha libre|hay lugar)\b",
    "reschedule": r"\b(cambi\w* (?:la |de )?fecha|reprogram\w*|pospon\w*|mejor seria|"
    r"mejor el|en lugar del|quise decir|corrijo)\b",
    "deposit": r"\b(anticipo|apartar|apartado|deposito)\b",
    "contract": r"\b(contrato|firma\w*)\b",
    "payment": r"\b(pag\w*|saldo|transferencia|efectivo)\b",
    "agreement": r"\b(confirm\w*|acord\w*|quedamos|de acuerdo|contrat\w*|acepto)\b",
    "appointment": r"\b(cita|reunion|nos vemos|paso al estudio)\b",
    "cancellation": r"\b(cancel\w*|ya no quiero|ya no queremos)\b",
    "jordy_attention": r"\b(jordy|urgente|problema|queja)\b",
}


def normalize(value):
    return "".join(
        c for c in unicodedata.normalize("NFD", value.lower()) if unicodedata.category(c) != "Mn"
    )


def detect(body, occurred_at, timezone):
    if not body:
        return []
    result = []
    base = occurred_at.astimezone(ZoneInfo(timezone)).date()
    # Sentence-level evidence keeps a negation attached to the relevant assertion.
    for index, original in enumerate(re.split(r"(?<=[.!?])\s+|\n+", body)):
        text = normalize(original)
        if not text.strip():
            continue
        context = "statement"
        if re.search(r"\b(no|nunca|tampoco|sin)\b", text):
            context = "negated"
        elif re.search(r"\b(si|tal vez|quizas|supongamos|seria|podria)\b", text):
            context = "hypothetical"
        elif "?" in text or "¿" in text:
            context = "question"
        if context != "negated" and re.search(PATTERNS["reschedule"], text):
            context = "correction"
        certainty = "possible" if context != "statement" else "explicit"

        def add(kind, suffix="", mentioned=None, level=None):
            result.append(
                {
                    "signal_key": f"{index}:{kind}:{suffix}",
                    "kind": kind,
                    "evidence": original[:500],
                    "mentioned_date": mentioned,
                    "certainty": level or certainty,
                    "context": context,
                }
            )

        for kind, pattern in PATTERNS.items():
            if re.search(pattern, text):
                # Even an explicit verbal agreement remains only a possible agreement.
                add(
                    kind,
                    level="possible"
                    if kind in {"agreement", "cancellation", "appointment", "reschedule"}
                    else certainty,
                )
        # No year inference for "15 de mayo"; preserve evidence for human review.
        pattern = r"\b(\d{1,2}) de (" + "|".join(MONTHS) + r")(?: (?:de |del )?(\d{4}))?\b"
        dates = list(re.finditer(pattern, text))
        dates += list(re.finditer(r"\b(\d{4})-(\d{2})-(\d{2})\b", text))
        dates += list(re.finditer(r"(?<![\d/-])\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b", text))
        for item in dates:
            mentioned = None
            try:
                if " de " in item[0] and item[3]:
                    mentioned = date(int(item[3]), MONTHS.index(item[2]) + 1, int(item[1]))
                elif re.fullmatch(r"\d{4}-\d{2}-\d{2}", item[0]):
                    mentioned = date.fromisoformat(item[0])
                # Numeric DD/MM remains ambiguous across locale conventions.
            except ValueError:
                pass
            add("date", str(item.start()), mentioned, "explicit" if mentioned else "ambiguous")
        relative = re.search(r"\b(pasado manana|manana|hoy)\b", text)
        if relative:
            # "por la mañana" denotes a time of day, not tomorrow.
            time_only = relative[0] == "manana" and re.search(r"\b(?:la|por la) manana\b", text)
            if not time_only:
                offset = {"hoy": 0, "manana": 1, "pasado manana": 2}[relative[0]]
                value = base + timedelta(days=offset)
                add("date", "relative", value, certainty)
        if re.search(r"\b(?:proximo |este |el )?(" + "|".join(WEEKDAYS) + r")\b", text):
            # "Próximo sábado" can mean the nearest or following week: never guess.
            add("date", "weekday", level="ambiguous")
    return result
