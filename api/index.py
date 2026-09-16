"""Ponto de entrada WSGI da Vercel; frontend e API compartilham o domínio."""
import os
from pathlib import Path
import sys

os.environ.setdefault("APP_ENV", "production")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "Backend"))
from Backend.api import app  # noqa: E402,F401
