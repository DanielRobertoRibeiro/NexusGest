"""Migrações aditivas e recuperação administrativa local do NexusGest."""

import argparse
import getpass
import os
from pathlib import Path
import re
import secrets

from werkzeug.security import generate_password_hash

from security import TOKEN_FILE, database

ROOT = Path(__file__).resolve().parent


def migrate():
    with database() as (connection, cursor):
        cursor.execute("SELECT GET_LOCK('nexusgest_schema', 30) AS acquired")
        if cursor.fetchone()["acquired"] != 1:
            raise RuntimeError("Outra migração está em andamento.")
        try:
            cursor.execute("""CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(100) PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB""")
            cursor.execute("SELECT version FROM schema_migrations")
            done = {row["version"] for row in cursor.fetchall()}
            # Reaproveita SOMENTE os DDLs: nunca reinsere exemplos ou troca DB_NAME.
            base = (ROOT / "banco.sql").read_text(encoding="utf-8")
            ddl = re.findall(r"CREATE TABLE IF NOT EXISTS \w+\s*\(.*?\);", base, re.S)
            migrations = [("001_core", ddl)]
            for path in sorted((ROOT / "migrations").glob("*.sql")):
                migrations.append((path.stem, [s.strip() for s in path.read_text(encoding="utf-8").split(";") if s.strip()]))
            for version, statements in migrations:
                if version in done:
                    continue
                for statement in statements:
                    cursor.execute(statement)
                cursor.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (version,))
                connection.commit()
                print("Migração aplicada:", version)
            cursor.execute("SELECT COUNT(*) AS total FROM users")
            first_run = cursor.fetchone()["total"] == 0
        finally:
            cursor.execute("SELECT RELEASE_LOCK('nexusgest_schema')")
            cursor.fetchone()
    if first_run and not os.getenv("SETUP_TOKEN") and os.getenv("APP_ENV") != "production":
        if not TOKEN_FILE.exists():
            TOKEN_FILE.write_text(secrets.token_urlsafe(32), encoding="ascii")
    if first_run and os.getenv("APP_ENV") == "production" and len(os.getenv("SETUP_TOKEN", "")) < 32:
        raise RuntimeError("Defina SETUP_TOKEN com pelo menos 32 caracteres para o primeiro acesso.")
    return first_run


def reset_password(email):
    password = getpass.getpass("Nova senha (12 a 128 caracteres): ")
    if not 12 <= len(password) <= 128 or password != getpass.getpass("Confirme a senha: "):
        raise SystemExit("Senhas diferentes ou tamanho inválido.")
    with database() as (connection, cursor):
        cursor.execute("SELECT id FROM users WHERE email=%s", (email.strip().lower(),))
        user = cursor.fetchone()
        if not user:
            raise SystemExit("Usuário não encontrado.")
        cursor.execute("UPDATE users SET password_hash=%s WHERE id=%s", (generate_password_hash(password), user["id"]))
        cursor.execute("DELETE FROM auth_sessions WHERE user_id=%s", (user["id"],))
        connection.commit()
    print("Senha atualizada. As sessões antigas foram encerradas.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["migrate", "reset-password"])
    parser.add_argument("--email")
    args = parser.parse_args()
    if args.command == "migrate":
        migrate()
        print("Banco atualizado; os cadastros existentes foram preservados.")
    elif args.email:
        reset_password(args.email)
    else:
        parser.error("Informe --email para recuperar uma conta.")
