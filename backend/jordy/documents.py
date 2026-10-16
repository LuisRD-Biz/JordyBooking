"""Private original files, validated by parsers and versioned independently of signing."""

import hashlib
import os
import warnings
from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from PIL import Image
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.orm import Session

from jordy.api import authenticate
from jordy.config import settings
from jordy.db import get_session
from jordy.domain import Conflict, RuleViolation
from jordy.models import Booking, BookingDocument, Customer
from jordy.repository import require
from jordy.schemas import Input
from jordy.search import Filters, date_predicates, paginate
from jordy.services import audit, now

router = APIRouter(prefix="/api", dependencies=[Depends(authenticate)])
DB = Annotated[Session, Depends(get_session)]


class ContractDocumentInput(Input):
    document_id: UUID


@router.post("/bookings/{identity}/contract/document")
def associate_contract_document(identity: int, data: ContractDocumentInput, session: DB):
    with session.begin():
        booking = require(session, Booking, identity, lock=True)
        if not booking.contract:
            raise RuleViolation("Primero registra expresamente la firma del contrato.")
        document = session.get(BookingDocument, data.document_id)
        if not document or document.booking_id != identity or document.document_type != "contract":
            raise RuleViolation("Selecciona un contrato adjunto de esta misma reservación.")
        booking.contract.document_id = document.id
        audit(session, "contract.document_linked", identity)
    return {"document_id": document.id}


def private_root():
    root = settings().document_root.resolve()
    project = Path(__file__).resolve().parents[2]
    for public in [project / "frontend", project / ".git"]:
        if root == public or public in root.parents:
            raise RuleViolation("El almacenamiento de documentos debe ser privado.")
    root.mkdir(parents=True, exist_ok=True)
    return root


def validate_file(path: Path, name: str):
    ext = Path(name).suffix.lower()
    try:
        if ext == ".pdf":
            with path.open("rb") as stream:
                if stream.read(5) != b"%PDF-":
                    raise ValueError()
                stream.seek(0)
                reader = PdfReader(stream, strict=True)
                if reader.is_encrypted or not len(reader.pages):
                    raise ValueError()
                root = reader.trailer["/Root"]
                if "/OpenAction" in root or "/AA" in root:
                    raise ValueError()
                names = root.get("/Names", {})
                if hasattr(names, "get_object"):
                    names = names.get_object()
                if "/JavaScript" in names or "/EmbeddedFiles" in names:
                    raise ValueError()
            return "application/pdf"
        expected = {".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG"}.get(ext)
        if not expected:
            raise ValueError()
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(path) as image:
                if image.format != expected or image.width * image.height > 25_000_000:
                    raise ValueError()
                image.verify()
            with Image.open(path) as image:
                image.load()
        return "image/png" if expected == "PNG" else "image/jpeg"
    except Exception as exc:
        raise RuleViolation(
            "Archivo inválido. Usa PDF no cifrado, JPG o PNG válido; "
            "no se admiten PDF con acciones automáticas o adjuntos."
        ) from exc


def metadata(doc):
    return {
        key: getattr(doc, key)
        for key in [
            "id",
            "booking_id",
            "group_id",
            "version",
            "is_current",
            "document_type",
            "original_name",
            "mime",
            "size",
            "sha256",
            "notes",
            "created_at",
            "actor",
        ]
    }


@router.get("/documents/settings")
def limits():
    return {"max_bytes": settings().document_max_bytes, "types": ["pdf", "jpg", "jpeg", "png"]}


@router.post("/bookings/{identity}/documents", status_code=201)
async def upload(
    identity: int,
    request: Request,
    session: DB,
    filename: str = Query(min_length=1, max_length=240),
    document_type: Literal["contract", "deposit", "annex", "other"] = "contract",
    notes: str = Query(default="", max_length=2000),
    replaces: UUID | None = None,
):
    if any(c in filename for c in ["/", "\\", "\x00", "\r", "\n"]) or filename in {".", ".."}:
        raise RuleViolation("Nombre de archivo inválido.")
    root = private_root()
    identity_uuid = uuid4()
    temporary = root / f"{identity_uuid.hex}.part"
    final = root / f"{identity_uuid.hex}.bin"
    size, digest = 0, hashlib.sha256()
    committed = False
    try:
        with temporary.open("xb") as stream:
            async for chunk in request.stream():
                size += len(chunk)
                if size > settings().document_max_bytes:
                    raise HTTPException(413, "El archivo supera el tamaño máximo permitido.")
                digest.update(chunk)
                stream.write(chunk)
            stream.flush()
            os.fsync(stream.fileno())
        if not size:
            raise RuleViolation("El archivo está vacío.")
        mime = validate_file(temporary, filename)
        with session.begin():
            booking = require(session, Booking, identity, lock=True)
            previous = session.get(BookingDocument, replaces) if replaces else None
            if replaces and (not previous or previous.booking_id != identity):
                raise RuleViolation("El documento sustituido debe pertenecer a esta reservación.")
            if previous and (not previous.is_current or previous.document_type != document_type):
                raise Conflict("Solo puedes sustituir la versión vigente conservando su tipo.")
            doc = BookingDocument(
                id=identity_uuid,
                booking_id=identity,
                group_id=previous.group_id if previous else identity_uuid,
                version=previous.version + 1 if previous else 1,
                document_type=document_type,
                original_name=filename,
                storage_key=final.name,
                mime=mime,
                size=size,
                sha256=digest.hexdigest(),
                notes=notes,
                created_at=now(),
            )
            if previous:
                previous.is_current = False
            session.add(doc)
            require(session, Customer, booking.customer_id).last_activity_at = now()
            audit(session, "document.uploaded", identity)
            session.flush()
            # Atomic rename within the same private directory; only our UUID files are touched.
            temporary.rename(final)
            result = metadata(doc)
        committed = True
        return result
    finally:
        temporary.unlink(missing_ok=True)
        if not committed:
            final.unlink(missing_ok=True)


@router.get("/bookings/{identity}/documents")
def listing(identity: int, session: DB, filters: Annotated[Filters, Query()]):
    require(session, Booking, identity)
    stmt = select(BookingDocument).where(
        BookingDocument.booking_id == identity,
        *date_predicates(BookingDocument.created_at, filters=filters),
    )
    if filters.q:
        stmt = stmt.where(BookingDocument.original_name.icontains(filters.q, autoescape=True))
    rows, result = paginate(
        session, stmt, filters, [BookingDocument.created_at, BookingDocument.id]
    )
    result["items"] = [metadata(row[0]) for row in rows]
    return result


def document_file(identity, session):
    doc = session.get(BookingDocument, identity)
    if doc is None:
        raise HTTPException(404, "Documento no encontrado.")
    root = private_root()
    path = (root / doc.storage_key).resolve()
    if path.parent != root or not path.is_file():
        raise HTTPException(404, "Archivo no disponible; revisa el almacenamiento privado.")
    return doc, path


@router.get("/documents/{identity}/download")
def download(identity: UUID, session: DB):
    doc, path = document_file(identity, session)
    return FileResponse(
        path,
        media_type="application/octet-stream",
        filename=doc.original_name,
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "no-store"},
    )


@router.get("/documents/{identity}/preview")
def preview(identity: UUID, session: DB):
    doc, path = document_file(identity, session)
    if doc.mime not in {"image/png", "image/jpeg"}:
        raise RuleViolation("Descarga el PDF para revisarlo en tu lector de documentos.")
    return FileResponse(
        path,
        media_type=doc.mime,
        headers={
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store",
            "Content-Security-Policy": "default-src 'none'; sandbox",
        },
    )
