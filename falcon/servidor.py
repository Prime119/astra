#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FALCON — Lanzador local.
Levanta un servidor web en esta carpeta y abre el navegador automáticamente.
Uso:  python servidor.py     (o doble clic en "Abrir-Falcon.bat")
Detener: cierra la ventana o presiona Ctrl+C.
"""
import http.server
import socketserver
import webbrowser
import threading
import os

PORT_INICIAL = 8000

# Servir desde la carpeta de este archivo (donde está index.html)
os.chdir(os.path.dirname(os.path.abspath(__file__)))


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass  # consola silenciosa


def abrir_servidor(puerto_inicial):
    socketserver.TCPServer.allow_reuse_address = True
    puerto = puerto_inicial
    for _ in range(25):
        try:
            return socketserver.TCPServer(("", puerto), Handler), puerto
        except OSError:
            puerto += 1
    raise SystemExit("No se encontró un puerto libre (8000-8024).")


def main():
    servidor, puerto = abrir_servidor(PORT_INICIAL)
    url = "http://localhost:{}/".format(puerto)
    print("=" * 52)
    print("  FALCON // Sistema de monitoreo CFE")
    print("  Sirviendo en: " + url)
    print("  Abriendo el navegador automaticamente...")
    print("  (cierra esta ventana o Ctrl+C para detener)")
    print("=" * 52)
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
        servidor.server_close()


if __name__ == "__main__":
    main()
