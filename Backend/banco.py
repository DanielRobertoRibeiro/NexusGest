# ============================================================
# CONEXÃO COM O BANCO DE DADOS
# ============================================================

import os
from pathlib import Path
import tempfile

import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv


load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


def _configurar_ssl(configuracao):
    """Ativa TLS verificado usando um arquivo ou um PEM vindo do ambiente."""
    ca_path = os.getenv("DB_SSL_CA")
    ca_pem = os.getenv("DB_SSL_CA_PEM")

    if ca_pem:
        ca_path = Path(tempfile.gettempdir()) / "nexusgest-mysql-ca.pem"
        if not ca_path.exists() or ca_path.read_text(encoding="utf-8") != ca_pem:
            ca_path.write_text(ca_pem, encoding="utf-8")

    if ca_path:
        configuracao.update(
            ssl_ca=str(ca_path),
            ssl_verify_cert=True,
            ssl_verify_identity=True,
        )


def conectar_banco():
    """
    Cria uma conexão com o banco de dados MySQL.
    """

    try:

        configuracao = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "3306")),
            "user": os.getenv("DB_USER", "root"),
            "password": os.getenv("DB_PASSWORD"),
            "database": os.getenv("DB_NAME", "erp_pai"),
            "charset": "utf8mb4",
            "collation": "utf8mb4_0900_ai_ci",
            "use_unicode": True,
            "connection_timeout": 10,
        }

        _configurar_ssl(configuracao)

        if not configuracao["password"]:
            print(
                "DB_PASSWORD não foi configurada. "
                "Defina as variáveis de ambiente antes de iniciar o sistema."
            )
            return None

        conexao = mysql.connector.connect(**configuracao)

        return conexao

    except Error as erro:

        print(f"Erro ao conectar ao MySQL: {erro}")

        return None


def fechar_banco(conexao):

    """
    Fecha a conexão com o banco.
    """

    if conexao and conexao.is_connected():

        conexao.close()


