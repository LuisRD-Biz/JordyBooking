"""Individual accounts: Argon2id passwords, revocable server-side sessions and login throttling.

Security notes
- Passwords are stored only as Argon2id hashes (memory-hard; salted per user).
- Session cookies carry a 256-bit random token; the database keeps only its SHA-256,
  so a database leak does not yield usable cookies.
- Failed logins are recorded per e-mail and per client IP. Throttling applies the same way
  to existing and unknown e-mails, and unknown e-mails still pay for a hash verification,
  so responses do not reveal which accounts exist.
"""

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    delete,
    func,
    select,
    text,
)
from sqlalchemy.orm import Mapped, Session, mapped_column

from jordy.models import Base

ROLES = ("admin", "employee", "client")
SESSION_LIFETIME = timedelta(hours=8)
SESSION_IDLE = timedelta(hours=2)
TOUCH_EVERY = timedelta(minutes=1)
ATTEMPT_WINDOW = timedelta(minutes=15)
MAX_FAILURES_PER_EMAIL = 5
MAX_FAILURES_PER_IP = 20
ATTEMPT_RETENTION = timedelta(days=90)
PASSWORD_MIN = 12
PASSWORD_MAX = 128

hasher = PasswordHasher()  # Argon2id, RFC 9106 profile: t=3, m=64 MiB, p=4
_DUMMY_HASH = hasher.hash(secrets.token_urlsafe(32))


def now() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'employee', 'client')", name="ck_users_role"),
        CheckConstraint("email = lower(email)", name="ck_users_email_lower"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(20))
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True, server_default=text("true"))
    password_changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class UserSession(Base):
    __tablename__ = "user_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(300))


class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    email: Mapped[str] = mapped_column(String(254))
    ip: Mapped[str] = mapped_column(String(64))
    succeeded: Mapped[bool]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


@dataclass(frozen=True)
class Principal:
    session_id: int
    user_id: int | None
    name: str
    email: str | None
    role: str


class LoginRejected(Exception):
    """Wrong e-mail or password. Deliberately does not say which."""


class LoginThrottled(Exception):
    """Too many recent failures for this e-mail or client."""


class PasswordRejected(ValueError):
    pass


def normalize_email(email: str) -> str:
    return email.strip().lower()[:254]


def validate_password(password: str, email: str = "") -> None:
    if len(password) < PASSWORD_MIN:
        raise PasswordRejected(f"La contraseña debe tener al menos {PASSWORD_MIN} caracteres.")
    if len(password) > PASSWORD_MAX:
        raise PasswordRejected(f"La contraseña admite como máximo {PASSWORD_MAX} caracteres.")
    if len(set(password)) < 4:
        raise PasswordRejected("La contraseña es demasiado repetitiva.")
    local = normalize_email(email).split("@")[0]
    if local and len(local) >= 4 and local in password.lower():
        raise PasswordRejected("La contraseña no debe contener tu correo.")


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_user(session: Session, email: str, name: str, password: str, role: str = "admin"):
    email = normalize_email(email)
    if role not in ROLES:
        raise ValueError("Rol no válido.")
    if "@" not in email or len(email) < 6:
        raise ValueError("Correo no válido.")
    if not name.strip():
        raise ValueError("El nombre es obligatorio.")
    validate_password(password, email)
    if session.scalar(select(User.id).where(User.email == email)) is not None:
        raise ValueError("Ya existe un usuario con ese correo.")
    user = User(
        email=email, name=name.strip()[:120], role=role, password_hash=hasher.hash(password)
    )
    session.add(user)
    session.flush()
    return user


def set_password(session: Session, user: User, password: str, keep_session: int | None = None):
    validate_password(password, user.email)
    user.password_hash = hasher.hash(password)
    user.password_changed_at = now()
    revoke_user_sessions(session, user.id, keep_session)


def _failures(session: Session, column, value: str, since: datetime) -> int:
    return session.scalar(
        select(func.count())
        .select_from(LoginAttempt)
        .where(column == value, LoginAttempt.succeeded.is_(False), LoginAttempt.created_at > since)
    )


def authenticate(session: Session, email: str, password: str, ip: str) -> User:
    """Verify credentials inside the caller's transaction.

    Success is recorded here. On LoginRejected/LoginThrottled the caller's transaction rolls
    back, so the caller must record the failed attempt in a new transaction.
    """
    email = normalize_email(email)
    moment = now()
    since = moment - ATTEMPT_WINDOW
    if (
        _failures(session, LoginAttempt.email, email, since) >= MAX_FAILURES_PER_EMAIL
        or _failures(session, LoginAttempt.ip, ip, since) >= MAX_FAILURES_PER_IP
    ):
        # The caller records throttled attempts too, so a sustained attack keeps the lock active.
        raise LoginThrottled
    user = session.scalar(select(User).where(User.email == email))
    stored = user.password_hash if user is not None else _DUMMY_HASH
    try:
        hasher.verify(stored, password[:PASSWORD_MAX])
        valid = user is not None and user.is_active
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        valid = False
    if not valid:
        raise LoginRejected
    session.add(LoginAttempt(email=email, ip=ip, succeeded=True, created_at=moment))
    if hasher.check_needs_rehash(user.password_hash):
        user.password_hash = hasher.hash(password)
    user.last_login_at = moment
    session.execute(
        delete(LoginAttempt).where(LoginAttempt.created_at < moment - ATTEMPT_RETENTION)
    )
    return user


def start_session(
    session: Session, user: User | None, ip: str | None, user_agent: str | None
) -> str:
    token = secrets.token_urlsafe(32)
    moment = now()
    session.add(
        UserSession(
            token_hash=hash_token(token),
            user_id=user.id if user else None,
            kind="user" if user else "local",
            created_at=moment,
            last_seen_at=moment,
            expires_at=moment + SESSION_LIFETIME,
            ip=ip,
            user_agent=(user_agent or "")[:300] or None,
        )
    )
    return token


def resolve_session(session: Session, token: str | None) -> Principal | None:
    if not token or len(token) > 100:
        return None
    row = session.execute(
        select(UserSession, User)
        .outerjoin(User, User.id == UserSession.user_id)
        .where(UserSession.token_hash == hash_token(token))
    ).first()
    if row is None:
        return None
    stored, user = row
    moment = now()
    if (
        stored.revoked_at is not None
        or stored.expires_at <= moment
        or stored.last_seen_at + SESSION_IDLE <= moment
    ):
        return None
    if stored.kind == "user" and (user is None or not user.is_active):
        return None
    if moment - stored.last_seen_at >= TOUCH_EVERY:
        stored.last_seen_at = moment
    if user is None:
        return Principal(stored.id, None, "Acceso local", None, "admin")
    return Principal(stored.id, user.id, user.name, user.email, user.role)


def revoke_session(session: Session, token: str | None) -> None:
    if token:
        session.query(UserSession).filter(
            UserSession.token_hash == hash_token(token), UserSession.revoked_at.is_(None)
        ).update({UserSession.revoked_at: now()})


def revoke_user_sessions(session: Session, user_id: int, keep_session: int | None = None) -> None:
    query = session.query(UserSession).filter(
        UserSession.user_id == user_id, UserSession.revoked_at.is_(None)
    )
    if keep_session is not None:
        query = query.filter(UserSession.id != keep_session)
    query.update({UserSession.revoked_at: now()})
