"""Ponto de entrada WSGI da Vercel; frontend e API compartilham o domínio."""
import os
from pathlib import Path
import sys

os.environ.setdefault("APP_ENV", "production")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "Backend"))

# Inicialização controlada para o primeiro deploy. As migrações são
# idempotentes e protegidas por um lock no próprio MySQL.
if os.getenv("RUN_MIGRATIONS") == "1":
    from Backend.manage import migrate  # noqa: E402

    migrate()

from Backend.api import app  # noqa: E402,F401

