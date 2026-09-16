"""Sessões revogáveis no MySQL e autorização aplicada a toda a API."""

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import os
from pathlib import Path
import secrets

from flask import Blueprint, current_app, g, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from banco import conectar_banco

auth = Blueprint("auth", __name__)
ROLES = {"admin", "operador", "consulta"}
COOKIE = "nexusgest_session"
TOKEN_FILE = Path(__file__).with_name(".setup-token")


class ApiError(Exception):
    def __init__(self, message, status=400):
        self.message, self.status = message, status


@contextmanager
def database():
    connection = conectar_banco()
    if connection is None:
        raise ApiError("Banco indisponível. Verifique a configuração do servidor.", 503)
    cursor = connection.cursor(dictionary=True)
    try:
        yield connection, cursor
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def ok(data=None, status=200):
    return jsonify(success=True, data=data), status


def body():
    value = request.get_json(silent=True)
    if not isinstance(value, dict):
        raise ApiError("Envie um objeto JSON válido.")
    return value


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def public_user(user):
    return {key: user[key] for key in ("id", "name", "email", "role", "active")}


def validate_user(data, require_password=True):
    name = str(data.get("name") or "").strip()
    email = str(data.get("email") or "").strip().lower()
    password = data.get("password", "")
    role = data.get("role", "consulta")
    if not 2 <= len(name) <= 120:
        raise ApiError("Nome deve ter de 2 a 120 caracteres.")
    if not 3 <= len(email) <= 190 or "@" not in email or any(c.isspace() for c in email):
        raise ApiError("Informe um e-mail válido.")
    if role not in ROLES:
        raise ApiError("Perfil inválido.")
    if require_password or password:
        if not isinstance(password, str) or not 12 <= len(password) <= 128:
            raise ApiError("A senha deve ter de 12 a 128 caracteres.")
    return name, email, role, password


def setup_token():
    return os.getenv("SETUP_TOKEN") or (TOKEN_FILE.read_text().strip() if TOKEN_FILE.exists() else "")


def throttle(cursor, connection, email):
    # Persistido no banco: funciona também com múltiplos workers.
    for scope in ("ip:" + (request.remote_addr or "unknown"), "email:" + email):
        key = digest(scope)
        cursor.execute("""INSERT INTO auth_attempts (bucket, attempts, window_start)
            VALUES (%s, 1, UTC_TIMESTAMP()) ON DUPLICATE KEY UPDATE
            attempts = IF(window_start < UTC_TIMESTAMP() - INTERVAL 15 MINUTE, 1, attempts + 1),
            window_start = IF(window_start < UTC_TIMESTAMP() - INTERVAL 15 MINUTE,
                              UTC_TIMESTAMP(), window_start)""", (key,))
        cursor.execute("SELECT attempts FROM auth_attempts WHERE bucket = %s", (key,))
        if cursor.fetchone()["attempts"] > 20:
            connection.commit()
            raise ApiError("Muitas tentativas. Aguarde 15 minutos e tente novamente.", 429)
    connection.commit()


def create_session(cursor, user):
    token, csrf = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
    cursor.execute("DELETE FROM auth_sessions WHERE expires_at < UTC_TIMESTAMP()")
    cursor.execute("""INSERT INTO auth_sessions (token_hash, user_id, csrf_token, expires_at)
        VALUES (%s, %s, %s, %s)""", (
        digest(token), user["id"], csrf,
        datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=8),
    ))
    response = jsonify(success=True, data={"user": public_user(user), "csrf": csrf})
    response.set_cookie(COOKIE, token, httponly=True, secure=current_app.config["COOKIE_SECURE"],
                        samesite="Lax", max_age=8 * 3600, path="/")
    return response


@auth.get("/api/auth/status")
def status():
    if os.getenv("APP_ENV") == "production" and not os.getenv("DB_PASSWORD"):
        return ok({"requiresSetup": False, "databaseConfigured": False})
    with database() as (_, cursor):
        cursor.execute("SELECT COUNT(*) AS total FROM users")
        return ok({"requiresSetup": cursor.fetchone()["total"] == 0, "databaseConfigured": True})


@auth.post("/api/auth/setup")
def setup():
    provided = request.headers.get("X-Setup-Token", "")
    expected = setup_token()
    if not expected or not hmac.compare_digest(provided, expected):
        raise ApiError("Chave de configuração inválida. Use o link exibido no servidor.", 403)
    data = body()
    name, email, _, password = validate_user({**data, "role": "admin"})
    with database() as (connection, cursor):
        # Linha única criada na migração serializa o primeiro cadastro.
        cursor.execute("SELECT id FROM auth_setup_lock WHERE id = 1 FOR UPDATE")
        cursor.fetchone()
        cursor.execute("SELECT COUNT(*) AS total FROM users")
        if cursor.fetchone()["total"]:
            raise ApiError("A configuração inicial já foi concluída.", 409)
        cursor.execute("INSERT INTO users (name, email, password_hash, role) VALUES (%s,%s,%s,'admin')",
                       (name, email, generate_password_hash(password)))
        user = dict(id=cursor.lastrowid, name=name, email=email, role="admin", active=True)
        response = create_session(cursor, user)
        connection.commit()
        return response, 201


@auth.post("/api/auth/login")
def login():
    data = body()
    email = str(data.get("email") or "").strip().lower()[:190]
    password = data.get("password", "")
    if not isinstance(password, str) or len(password) > 128:
        raise ApiError("E-mail ou senha incorretos.", 401)
    with database() as (connection, cursor):
        throttle(cursor, connection, email)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        # Hash fictício evita resposta muito mais rápida para e-mails inexistentes.
        valid = check_password_hash(user["password_hash"] if user else current_app.config["DUMMY_HASH"], password)
        if not valid or not user or not user["active"]:
            raise ApiError("E-mail ou senha incorretos.", 401)
        old = request.cookies.get(COOKIE)
        if old:
            cursor.execute("DELETE FROM auth_sessions WHERE token_hash = %s", (digest(old),))
        response = create_session(cursor, user)
        connection.commit()
        return response


@auth.get("/api/auth/me")
def me():
    return ok({"user": g.user, "csrf": g.csrf})


@auth.post("/api/auth/logout")
def logout():
    with database() as (connection, cursor):
        cursor.execute("DELETE FROM auth_sessions WHERE token_hash = %s", (g.token_hash,))
        connection.commit()
    response = jsonify(success=True, data=None)
    response.delete_cookie(COOKIE, path="/", secure=current_app.config["COOKIE_SECURE"], samesite="Lax")
    return response


@auth.post("/api/auth/password")
def password_change():
    data = body()
    new = data.get("password", "")
    if not isinstance(new, str) or not 12 <= len(new) <= 128:
        raise ApiError("A nova senha deve ter de 12 a 128 caracteres.")
    current = data.get("currentPassword", "")
    if not isinstance(current, str) or len(current) > 128:
        raise ApiError("Senha atual incorreta.", 403)
    with database() as (connection, cursor):
        throttle(cursor, connection, g.user["email"])
        cursor.execute("SELECT password_hash FROM users WHERE id = %s FOR UPDATE", (g.user["id"],))
        if not check_password_hash(cursor.fetchone()["password_hash"], current):
            raise ApiError("Senha atual incorreta.", 403)
        cursor.execute("UPDATE users SET password_hash = %s WHERE id = %s",
                       (generate_password_hash(new), g.user["id"]))
        cursor.execute("DELETE FROM auth_sessions WHERE user_id = %s", (g.user["id"],))
        response = create_session(cursor, g.user)
        connection.commit()
        return response


@auth.get("/api/users")
def list_users():
    with database() as (_, cursor):
        cursor.execute("SELECT id, name, email, role, active FROM users ORDER BY name")
        return ok(cursor.fetchall())


@auth.post("/api/users")
def add_user():
    data = body()
    name, email, role, password = validate_user(data)
    active = data.get("active", True)
    if not isinstance(active, bool):
        raise ApiError("Estado do usuário inválido.")
    with database() as (connection, cursor):
        cursor.execute("INSERT INTO users (name,email,role,password_hash,active) VALUES (%s,%s,%s,%s,%s)",
                       (name, email, role, generate_password_hash(password), active))
        identifier = cursor.lastrowid
        connection.commit()
    return ok(dict(id=identifier, name=name, email=email, role=role, active=active), 201)


@auth.put("/api/users/<int:identifier>")
def edit_user(identifier):
    data = body()
    name, email, role, password = validate_user(data, require_password=False)
    active = data.get("active", True)
    if not isinstance(active, bool):
        raise ApiError("Estado do usuário inválido.")
    with database() as (connection, cursor):
        cursor.execute("SELECT id FROM users WHERE role = 'admin' AND active = 1 ORDER BY id FOR UPDATE")
        admins = [row["id"] for row in cursor.fetchall()]
        if identifier in admins and len(admins) == 1 and (role != "admin" or not active):
            raise ApiError("Mantenha pelo menos um administrador ativo.", 409)
        cursor.execute("SELECT id FROM users WHERE id = %s FOR UPDATE", (identifier,))
        if not cursor.fetchone():
            raise ApiError("Usuário não encontrado.", 404)
        cursor.execute("UPDATE users SET name=%s,email=%s,role=%s,active=%s WHERE id=%s",
                       (name, email, role, active, identifier))
        if password:
            cursor.execute("UPDATE users SET password_hash=%s WHERE id=%s", (generate_password_hash(password), identifier))
        cursor.execute("DELETE FROM auth_sessions WHERE user_id=%s", (identifier,))
        connection.commit()
    return ok(dict(id=identifier, name=name, email=email, role=role, active=active))


def configure_security(app):
    app.config.update(COOKIE_SECURE=os.getenv("APP_ENV") == "production",
                      MAX_CONTENT_LENGTH=64 * 1024,
                      DUMMY_HASH=generate_password_hash(secrets.token_urlsafe(32)))
    app.register_blueprint(auth)

    @app.errorhandler(ApiError)
    def api_error(error):
        return jsonify(success=False, message=error.message), error.status

    @app.before_request
    def authorize():
        if not request.path.startswith("/api/"):
            return None
        if request.method == "OPTIONS":
            return "", 204
        if request.method not in {"GET", "HEAD"}:
            origin = request.headers.get("Origin")
            allowed = {request.host_url.rstrip("/")}
            allowed.update(v.strip().rstrip("/") for v in os.getenv("ALLOWED_ORIGINS", "").split(",") if v.strip())
            if origin and origin not in allowed:
                raise ApiError("Origem não autorizada.", 403)
        if request.path in {"/api/health", "/api/auth/status", "/api/auth/login", "/api/auth/setup"}:
            return None
        token = request.cookies.get(COOKIE, "")
        if not token:
            raise ApiError("Entre na sua conta para continuar.", 401)
        with database() as (_, cursor):
            cursor.execute("""SELECT u.id,u.name,u.email,u.role,u.active,s.csrf_token
                FROM auth_sessions s JOIN users u ON u.id=s.user_id
                WHERE s.token_hash=%s AND s.expires_at > UTC_TIMESTAMP() AND u.active=1""", (digest(token),))
            user = cursor.fetchone()
        if not user:
            raise ApiError("Sua sessão expirou. Entre novamente.", 401)
        g.user, g.csrf, g.token_hash = public_user(user), user["csrf_token"], digest(token)
        if request.method not in {"GET", "HEAD"}:
            if not hmac.compare_digest(request.headers.get("X-CSRF-Token", ""), g.csrf):
                raise ApiError("Sessão de segurança inválida. Atualize a página.", 403)
        if request.path.startswith("/api/users") and user["role"] != "admin":
            raise ApiError("Apenas administradores podem gerenciar usuários.", 403)
        if request.path.startswith(("/api/clientes", "/api/produtos")):
            if request.method not in {"GET", "HEAD"} and user["role"] == "consulta":
                raise ApiError("Seu perfil permite apenas consulta.", 403)
            if request.method == "DELETE" and user["role"] != "admin":
                raise ApiError("Apenas administradores podem excluir registros.", 403)

    @app.after_request
    def headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response
