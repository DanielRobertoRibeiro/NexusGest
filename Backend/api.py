"""API REST do NexusGest.

Este módulo é independente do programa de terminal (main.py). Ele expõe os
dados do mesmo MySQL para que o frontend se comunique apenas via HTTP/JSON.
"""

from decimal import Decimal, InvalidOperation
import logging
import re
import os
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException
from mysql.connector import Error

from banco import conectar_banco, fechar_banco
from security import configure_security
from reports import reports


app = Flask(__name__, static_folder=None)
app.config["JSON_SORT_KEYS"] = False
app.json.ensure_ascii = False
configure_security(app)
app.register_blueprint(reports)
logging.basicConfig(level=logging.INFO)

ESTADOS_VALIDOS = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT",
    "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO",
    "RR", "SC", "SP", "SE", "TO",
}
STATUS_VALIDOS = {"Ativo", "Inativo"}


@app.errorhandler(Error)
def database_error(error):
    app.logger.exception("Falha de banco")
    if getattr(error, "errno", None) == 1062:
        return resposta_erro("Este registro já existe.", 409)
    return resposta_erro("Não foi possível concluir a operação no banco.", 503)


@app.errorhandler(HTTPException)
def http_error(error):
    return resposta_erro("Requisição inválida ou recurso não encontrado.", error.code)


@app.route("/api/<path:_caminho>", methods=["OPTIONS"])
def opcoes(_caminho):
    return "", 204


def resposta_sucesso(data=None, mensagem=None, status=200):
    corpo = {"success": True, "data": data}
    if mensagem:
        corpo["message"] = mensagem
    return jsonify(corpo), status


def resposta_erro(mensagem, status=400):
    return jsonify({"success": False, "message": mensagem}), status


def obter_dados_json():
    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        return None, resposta_erro("Envie um JSON válido no corpo da requisição.")
    return dados, None


def normalizar_numero(valor, campo, inteiro=False):
    try:
        if isinstance(valor, bool):
            raise ValueError()
        numero = Decimal(str(valor))
        if not numero.is_finite():
            raise ValueError()
        if inteiro and numero != numero.to_integral_value():
            return None, f"{campo} deve ser inteiro."
        if numero > (2147483647 if inteiro else Decimal('99999999.99')):
            return None, f"{campo} ultrapassa o limite permitido."
        numero = int(numero) if inteiro else numero.quantize(Decimal('0.01'))
    except (InvalidOperation, TypeError, ValueError, OverflowError):
        return None, f"{campo} deve ser um número válido."

    if numero < 0:
        return None, f"{campo} não pode ser negativo."
    return numero, None


def validar_cliente(dados):
    cliente = {
        "company": str(dados.get("company") or "").strip(),
        "name": str(dados.get("name") or "").strip(),
        "cnpj": str(dados.get("cnpj", "")).strip(),
        "state": str(dados.get("state", "")).strip().upper(),
        "status": str(dados.get("status", "")).strip(),
    }

    if not cliente["company"]:
        return None, "Razão social é obrigatória."
    if not cliente["name"]:
        return None, "Nome fantasia é obrigatório."
    if len(cliente["company"]) > 150 or len(cliente["name"]) > 150:
        return None, "Razão social e nome fantasia devem ter até 150 caracteres."

    cnpj_numeros = re.sub(r"\D", "", cliente["cnpj"])
    if len(cnpj_numeros) != 14:
        return None, "CNPJ deve conter 14 dígitos."
    cliente["cnpj"] = (
        f"{cnpj_numeros[:2]}.{cnpj_numeros[2:5]}.{cnpj_numeros[5:8]}/"
        f"{cnpj_numeros[8:12]}-{cnpj_numeros[12:]}"
    )

    if cliente["state"] not in ESTADOS_VALIDOS:
        return None, "Estado inválido."
    if cliente["status"] not in STATUS_VALIDOS:
        return None, "Status inválido."

    cliente["revenue"], erro = normalizar_numero(
        dados.get("revenue", 0), "Faturamento"
    )
    if erro:
        return None, erro
    return cliente, None


def validar_produto(dados):
    produto = {
        "name": str(dados.get("name") or "").strip(),
        "category": str(dados.get("category") or "").strip(),
        "brand": str(dados.get("brand") or "").strip(),
    }
    for campo, rotulo in (("name", "Nome"), ("category", "Categoria"), ("brand", "Marca")):
        if not produto[campo]:
            return None, f"{rotulo} é obrigatório(a)."
        if len(produto[campo]) > (150 if campo == "name" else 100):
            return None, f"{rotulo} excede o tamanho permitido."

    produto["stock"], erro = normalizar_numero(
        dados.get("stock"), "Estoque", inteiro=True
    )
    if erro:
        return None, erro
    produto["price"], erro = normalizar_numero(dados.get("price"), "Preço")
    if erro:
        return None, erro
    return produto, None


def serializar_cliente(linha):
    return {
        "id": linha["id"],
        "cnpj": linha["cnpj"],
        "company": linha["razao_social"],
        "name": linha["nome_fantasia"],
        "state": linha["estado"],
        "status": linha["status"],
        "revenue": float(linha["faturamento"] or 0),
    }


def serializar_produto(linha):
    return {
        "id": linha["id"],
        "name": linha["nome"],
        "category": linha["categoria"],
        "brand": linha["marca"],
        "stock": linha["estoque"],
        "price": float(linha["preco"] or 0),
    }


def consultar_um(cursor, tabela, identificador):
    cursor.execute(f"SELECT * FROM {tabela} WHERE id = %s", (identificador,))
    return cursor.fetchone()


def abrir_conexao():
    conexao = conectar_banco()
    if not conexao:
        return None, resposta_erro("Não foi possível conectar ao banco de dados.", 503)
    return conexao, None


@app.get("/api/health")
def health_check():
    conexao, erro = abrir_conexao()
    if erro:
        return erro
    fechar_banco(conexao)
    return resposta_sucesso({"status": "online"})


@app.get("/api/clientes")
def listar_clientes():
    conexao, erro = abrir_conexao()
    if erro:
        return erro
    cursor = conexao.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM clientes ORDER BY id")
        return resposta_sucesso([serializar_cliente(linha) for linha in cursor.fetchall()])
    except Error:
        app.logger.exception("Erro ao listar clientes")
        return resposta_erro("Não foi possível carregar os clientes.", 500)
    finally:
        cursor.close()
        fechar_banco(conexao)


@app.post("/api/clientes")
def criar_cliente():
    dados, erro = obter_dados_json()
    if erro:
        return erro
    cliente, erro = validar_cliente(dados)
    if erro:
        return resposta_erro(erro)

    conexao, erro = abrir_conexao()
    if erro:
        return erro
    cursor = conexao.cursor(dictionary=True)
    try:
        cursor.execute(
            """INSERT INTO clientes
               (cnpj, data_cadastro, status, razao_social, nome_fantasia, estado, faturamento)
               VALUES (%s, CURDATE(), %s, %s, %s, %s, %s)""",
            (cliente["cnpj"], cliente["status"], cliente["company"], cliente["name"],
             cliente["state"], cliente["revenue"]),
        )
        conexao.commit()
        registro = consultar_um(cursor, "clientes", cursor.lastrowid)
        return resposta_sucesso(serializar_cliente(registro), "Cliente cadastrado com sucesso.", 201)
    except Error as excecao:
        conexao.rollback()
        if getattr(excecao, "errno", None) == 1062:
            return resposta_erro("Já existe um cliente cadastrado com este CNPJ.", 409)
        app.logger.exception("Erro ao criar cliente")
        return resposta_erro("Não foi possível cadastrar o cliente.", 500)
    finally:
        cursor.close()
        fechar_banco(conexao)


@app.put("/api/clientes/<int:identificador>")
def atualizar_cliente(identificador):
    dados, erro = obter_dados_json()
    if erro:
        return erro
    cliente, erro = validar_cliente(dados)
    if erro:
        return resposta_erro(erro)

    conexao, erro = abrir_conexao()
    if erro:
        return erro
    cursor = conexao.cursor(dictionary=True)
    try:
        if not consultar_um(cursor, "clientes", identificador):
            return resposta_erro("Cliente não encontrado.", 404)
        cursor.execute(
            """UPDATE clientes
               SET cnpj = %s, status = %s, razao_social = %s, nome_fantasia = %s,
                   estado = %s, faturamento = %s
               WHERE id = %s""",
            (cliente["cnpj"], cliente["status"], cliente["company"], cliente["name"],
             cliente["state"], cliente["revenue"], identificador),
        )
        conexao.commit()
        return resposta_sucesso(
            serializar_cliente(consultar_um(cursor, "clientes", identificador)),
            "Cliente atualizado com sucesso.",
        )
    except Error as excecao:
        conexao.rollback()
        if getattr(excecao, "errno", None) == 1062:
            return resposta_erro("Já existe um cliente cadastrado com este CNPJ.", 409)
        app.logger.exception("Erro ao atualizar cliente")
        return resposta_erro("Não foi possível atualizar o cliente.", 500)
    finally:
        cursor.close()
        fechar_banco(conexao)


@app.delete("/api/clientes/<int:identificador>")
def excluir_cliente(identificador):
    return excluir_registro("clientes", identificador, "Cliente")


@app.get("/api/produtos")
def listar_produtos():
    conexao, erro = abrir_conexao()
    if erro:
        return erro
    cursor = conexao.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM produtos ORDER BY id")
        return resposta_sucesso([serializar_produto(linha) for linha in cursor.fetchall()])
    except Error:
        app.logger.exception("Erro ao listar produtos")
        return resposta_erro("Não foi possível carregar os produtos.", 500)
    finally:
        cursor.close()
        fechar_banco(conexao)


@app.post("/api/produtos")
def criar_produto():
    dados, erro = obter_dados_json()
    if erro:
        return erro
    produto, erro = validar_produto(dados)
    if erro:
        return resposta_erro(erro)

    conexao, erro = abrir_conexao()
    if erro:
        return erro
    cursor = conexao.cursor(dictionary=True)
    try:
        cursor.execute(
            """INSERT INTO produtos (nome, categoria, preco, estoque, marca)
               VALUES (%s, %s, %s, %s, %s)""",
            (produto["name"], produto["category"], produto["price"], produto["stock"], produto["brand"]),
        )
        conexao.commit()
        registro = consultar_um(cursor, "produtos", cursor.lastrowid)
        return resposta_sucesso(serializar_produto(registro), "Produto cadastrado com sucesso.", 201)
    except Error:
        conexao.rollback()
        app.logger.exception("Erro ao criar produto")
        return resposta_erro("Não foi possível cadastrar o produto.", 500)
    finally:
        cursor.close()
        fechar_banco(conexao)


@app.put("/api/produtos/<int:identificador>")
def atualizar_produto(identificador):
    dados, erro = obter_dados_json()
    if erro:
        return erro
    produto, erro = validar_produto(dados)
    if erro:
        return resposta_erro(erro)

    conexao, erro = abrir_conexao()
    if erro:
        return erro
    cursor = conexao.cursor(dictionary=True)
    try:
        if not consultar_um(cursor, "produtos", identificador):
            return resposta_erro("Produto não encontrado.", 404)
        cursor.execute(
            """UPDATE produtos
               SET nome = %s, categoria = %s, preco = %s, estoque = %s, marca = %s
               WHERE id = %s""",
            (produto["name"], produto["category"], produto["price"], produto["stock"],
             produto["brand"], identificador),
        )
        conexao.commit()
        return resposta_sucesso(
            serializar_produto(consultar_um(cursor, "produtos", identificador)),
            "Produto atualizado com sucesso.",
        )
    except Error:
        conexao.rollback()
        app.logger.exception("Erro ao atualizar produto")
        return resposta_erro("Não foi possível atualizar o produto.", 500)
    finally:
        cursor.close()
        fechar_banco(conexao)


@app.delete("/api/produtos/<int:identificador>")
def excluir_produto(identificador):
    return excluir_registro("produtos", identificador, "Produto")


def excluir_registro(tabela, identificador, entidade):
    conexao, erro = abrir_conexao()
    if erro:
        return erro
    cursor = conexao.cursor()
    try:
        cursor.execute(f"DELETE FROM {tabela} WHERE id = %s", (identificador,))
        if cursor.rowcount == 0:
            return resposta_erro(f"{entidade} não encontrado(a).", 404)
        conexao.commit()
        return resposta_sucesso(None, f"{entidade} excluído(a) com sucesso.")
    except Error:
        conexao.rollback()
        app.logger.exception("Erro ao excluir %s", entidade.lower())
        return resposta_erro(f"Não foi possível excluir o(a) {entidade.lower()}.", 500)
    finally:
        cursor.close()
        fechar_banco(conexao)


DIST = Path(__file__).resolve().parent.parent / "Frontend" / "dist"


@app.get("/")
@app.get("/<path:path>")
def frontend(path="index.html"):
    if path.startswith("api/"):
        return resposta_erro("Recurso não encontrado.", 404)
    if not DIST.is_dir():
        return resposta_erro("Compile a interface: cd Frontend e npm run build.", 503)
    candidate = (DIST / path).resolve()
    if candidate.is_relative_to(DIST.resolve()) and candidate.is_file():
        return send_from_directory(DIST, path)
    if "." in path:
        return resposta_erro("Arquivo não encontrado.", 404)
    return send_from_directory(DIST, "index.html")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")),
            debug=os.getenv("FLASK_DEBUG") == "1")
