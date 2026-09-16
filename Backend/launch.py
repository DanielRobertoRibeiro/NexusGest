"""Inicializador local: migrações, primeira conta e servidor de produção Windows."""
import os
import socket
import threading
import webbrowser

from manage import migrate
from security import setup_token


def main():
    port = int(os.getenv("PORT", "5000"))
    with socket.socket() as sock:
        if sock.connect_ex(("127.0.0.1", port)) == 0:
            raise SystemExit(f"A porta {port} está ocupada. Encerre a API antiga com Ctrl+C e tente novamente.")
    first_run = migrate()
    from api import app, DIST
    from waitress import serve
    if not DIST.is_dir():
        raise SystemExit("Interface não compilada. Execute preparar.cmd primeiro.")
    url = f"http://127.0.0.1:{port}/"
    if first_run:
        url += "#setup=" + setup_token()
    print("NexusGest pronto. Abra:", url, flush=True)
    print("Mantenha esta janela aberta. Ctrl+C encerra o servidor.", flush=True)
    if os.getenv("NO_BROWSER") != "1":
        threading.Timer(1, lambda: webbrowser.open(url)).start()
    serve(app, host="127.0.0.1", port=port, threads=8)


if __name__ == "__main__":
    main()
