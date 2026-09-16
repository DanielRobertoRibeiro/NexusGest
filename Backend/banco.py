# ============================================================
# CONEXÃO COM O BANCO DE DADOS
# ============================================================

import os

import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv


load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


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

        if os.getenv("DB_SSL_CA"):
            configuracao.update(ssl_ca=os.environ["DB_SSL_CA"], ssl_verify_cert=True,
                                ssl_verify_identity=True)

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

