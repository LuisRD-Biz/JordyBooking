"""Administer panel accounts from the server shell. Passwords are typed, never passed as arguments.

python -m jordy.manage_users create --email ana@example.com --name "Ana" [--role admin]
python -m jordy.manage_users reset-password --email ana@example.com
python -m jordy.manage_users disable --email ana@example.com
python -m jordy.manage_users enable --email ana@example.com
python -m jordy.manage_users unlock --email ana@example.com
python -m jordy.manage_users list
"""

import argparse
import getpass
import sys

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from jordy import accounts
from jordy.config import StudioDatabaseSettings
from jordy.db import build_engine


def ask_password(email: str) -> str:
    print(
        f"Contraseña nueva: mínimo {accounts.PASSWORD_MIN} caracteres. "
        "Recomendado: una frase larga o una generada por tu gestor de contraseñas."
    )
    for _ in range(3):
        first = getpass.getpass("Contraseña: ")
        if first != getpass.getpass("Repite la contraseña: "):
            print("No coinciden. Intenta de nuevo.")
            continue
        try:
            accounts.validate_password(first, email)
            return first
        except accounts.PasswordRejected as error:
            print(error)
    raise SystemExit("Demasiados intentos. No se cambió nada.")


def find(session: Session, email: str) -> accounts.User:
    user = session.scalar(
        select(accounts.User).where(accounts.User.email == accounts.normalize_email(email))
    )
    if user is None:
        raise SystemExit("No existe un usuario con ese correo.")
    return user


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create")
    create.add_argument("--email", required=True)
    create.add_argument("--name", required=True)
    create.add_argument("--role", choices=accounts.ROLES, default="admin")
    for name in ("reset-password", "disable", "enable", "unlock"):
        commands.add_parser(name).add_argument("--email", required=True)
    commands.add_parser("list")
    args = parser.parse_args(argv)

    engine = build_engine(StudioDatabaseSettings().database_url)
    try:
        with Session(engine) as session, session.begin():
            if args.command == "list":
                for user in session.scalars(select(accounts.User).order_by(accounts.User.id)):
                    state = "activo" if user.is_active else "desactivado"
                    last = (
                        user.last_login_at.isoformat(timespec="minutes")
                        if user.last_login_at
                        else "nunca"
                    )
                    row = f"{user.id:>3}  {user.email:<40} {user.role:<9} {state:<12}"
                    print(f"{row} último acceso: {last}")
                return
            if args.command == "create":
                email = accounts.normalize_email(args.email)
                if session.scalar(select(accounts.User.id).where(accounts.User.email == email)):
                    raise SystemExit("Ya existe un usuario con ese correo.")
                try:
                    user = accounts.create_user(
                        session, email, args.name, ask_password(email), args.role
                    )
                except ValueError as error:
                    raise SystemExit(str(error)) from None
                print(f"Usuario creado: {user.email} ({user.role}).")
                return
            user = find(session, args.email)
            if args.command == "reset-password":
                accounts.set_password(session, user, ask_password(user.email))
                print("Contraseña cambiada. Se cerraron todas sus sesiones.")
            elif args.command == "disable":
                user.is_active = False
                accounts.revoke_user_sessions(session, user.id)
                print("Usuario desactivado y sesiones cerradas.")
            elif args.command == "enable":
                user.is_active = True
                print("Usuario activado.")
            elif args.command == "unlock":
                session.execute(
                    delete(accounts.LoginAttempt).where(
                        accounts.LoginAttempt.email == user.email,
                        accounts.LoginAttempt.succeeded.is_(False),
                    )
                )
                print("Intentos fallidos borrados para ese correo.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
