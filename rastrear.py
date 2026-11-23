#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rastrear.py - Rastreador mínimo para las prácticas de SEO técnico (UT04).

Hace lo esencial que hace un robot: parte de una URL, descarga el HTML, extrae los enlaces <a href>
y los sigue, guardando para cada URL su código de estado, su profundidad y qué páginas la enlazan.
NO ejecuta JavaScript (igual que un robot que no renderiza).

Solo usa la biblioteca estándar de Python 3.8+ (sin instalar nada).

AVISO: es una herramienta casera y sencilla, hecha para esta práctica. No sustituye a un rastreador
profesional como Screaming Frog: no ejecuta JavaScript, no analiza imágenes, CSS ni scripts, no revisa
títulos, descripciones ni etiquetas canónicas, no tiene interfaz gráfica y solo se ha probado con el
sitio de prácticas. Úsala únicamente con ese sitio.

Uso:
    python rastrear.py http://www.modaurbana.test/
    python rastrear.py http://www.modaurbana.test/ --salida rastreo.csv --espera 0.5
    python rastrear.py http://www.modaurbana.test/ --comprobar /promo-black-friday.html /landing/navidad.html

IMPORTANTE: rastrea solo sitios propios o con autorización. Este programa se queda siempre dentro
del mismo dominio que la URL de partida.
"""
import argparse
import csv
import sys
import time
import urllib.error
import urllib.request
import urllib.robotparser
from collections import Counter, deque
from html.parser import HTMLParser
from urllib.parse import urldefrag, urljoin, urlsplit

AGENTE = "RastreadorDAW/1.0 (practica SEO; uso educativo)"


class Enlaces(HTMLParser):
    """Extrae los href de las etiquetas <a> (solo enlaces reales en el HTML recibido)."""

    def __init__(self):
        super().__init__()
        self.href = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for k, v in attrs:
                if k == "href" and v:
                    self.href.append(v.strip())


class SinRedireccion(urllib.request.HTTPRedirectHandler):
    """Para ver los 301/302 tal cual, sin seguirlos automáticamente."""

    def redirect_request(self, *args, **kwargs):
        return None


OPENER = urllib.request.build_opener(SinRedireccion)


def pedir(url, metodo="GET", intentos=3):
    """Devuelve (codigo, cabeceras, cuerpo_bytes). Reintenta si la red falla."""
    ultimo = None
    for n in range(intentos):
        req = urllib.request.Request(url, headers={"User-Agent": AGENTE}, method=metodo)
        try:
            with OPENER.open(req, timeout=15) as r:
                return r.status, r.headers, (r.read() if metodo == "GET" else b"")
        except urllib.error.HTTPError as e:      # 3xx, 4xx y 5xx llegan aquí
            return e.code, e.headers, (e.read() if metodo == "GET" else b"")
        except Exception as e:                   # red caída, timeout, DNS...
            ultimo = e
            time.sleep(1 + n)
    return 0, {}, str(ultimo).encode()


def normalizar(url):
    """Quita el fragmento (#...). Las variantes con ?parametros se consideran URL distintas."""
    return urldefrag(url)[0]


def rastrear(inicio, espera, maximo, respetar_robots):
    host = urlsplit(inicio).netloc
    esquema = urlsplit(inicio).scheme
    robots = urllib.robotparser.RobotFileParser()
    robots.set_url("%s://%s/robots.txt" % (esquema, host))
    hay_robots = False
    if respetar_robots:
        codigo, _, cuerpo = pedir(robots.url)
        if codigo == 200:
            robots.parse(cuerpo.decode("utf-8", "replace").splitlines())
            hay_robots = True
    print("robots.txt: %s" % ("encontrado y se respeta" if hay_robots else "no existe (todo permitido)" if respetar_robots else "ignorado"))

    datos = {}                      # url -> dict(estado, profundidad, destino, tipo)
    entrantes = {}                  # url -> lista de páginas que la enlazan
    cola = deque([(normalizar(inicio), 0, None)])
    vistas = {normalizar(inicio)}
    bloqueadas = []

    while cola and len(datos) < maximo:
        url, prof, _ = cola.popleft()
        if respetar_robots and hay_robots and not robots.can_fetch(AGENTE, url):
            datos[url] = {"estado": "bloqueada por robots.txt", "profundidad": prof, "destino": "", "tipo": ""}
            bloqueadas.append(url)
            continue
        codigo, cab, cuerpo = pedir(url)
        tipo = (cab.get("Content-Type", "") if cab else "").split(";")[0].strip()
        destino = ""
        info = {"estado": codigo, "profundidad": prof, "destino": "", "tipo": tipo}
        datos[url] = info
        print("  [%s] prof=%d  %s" % (codigo, prof, url))
        time.sleep(espera)

        nuevos = []
        if codigo in (301, 302, 303, 307, 308) and cab and cab.get("Location"):
            destino = normalizar(urljoin(url, cab.get("Location")))
            info["destino"] = destino
            nuevos.append(destino)
        elif codigo == 200 and tipo == "text/html":
            p = Enlaces()
            p.feed(cuerpo.decode("utf-8", "replace"))
            for h in p.href:
                if h.lower().startswith(("mailto:", "tel:", "javascript:")):
                    continue
                nuevos.append(normalizar(urljoin(url, h)))

        for n in nuevos:
            if urlsplit(n).netloc != host:           # nunca salir del dominio
                continue
            entrantes.setdefault(n, [])
            if url not in entrantes[n]:
                entrantes[n].append(url)
            if n not in vistas:
                vistas.add(n)
                cola.append((n, prof + 1, url))
    return datos, entrantes, bloqueadas


def resumen(datos):
    print("\n=== RESUMEN ===")
    print("URL descubiertas:", len(datos))
    print("Por código de estado:", dict(sorted(Counter(str(d["estado"]) for d in datos.values()).items())))
    print("Por profundidad:     ", dict(sorted(Counter(d["profundidad"] for d in datos.values()).items())))


def comprobar(base, rutas):
    print("\n=== COMPROBACIÓN DE URL ===")
    for r in rutas:
        url = urljoin(base, r)
        codigo, cab, _ = pedir(url, "HEAD")
        extra = (" -> " + cab.get("Location")) if cab and cab.get("Location") else ""
        print("  [%s] %s%s" % (codigo, url, extra))


def main():
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Rastreador mínimo para prácticas de SEO técnico.")
    ap.add_argument("url", help="URL de partida, por ejemplo http://www.modaurbana.test/")
    ap.add_argument("--salida", default="rastreo.csv", help="fichero CSV de resultados (por defecto rastreo.csv)")
    ap.add_argument("--espera", type=float, default=0.3, help="segundos de pausa entre peticiones (por defecto 0.3)")
    ap.add_argument("--maximo", type=int, default=500, help="máximo de URL a visitar (por defecto 500)")
    ap.add_argument("--ignorar-robots", action="store_true", help="no consultar robots.txt")
    ap.add_argument("--comprobar", nargs="+", metavar="RUTA", help="solo comprobar el código de estado de estas rutas")
    a = ap.parse_args()

    if not a.url.startswith(("http://", "https://")):
        sys.exit("La URL debe empezar por http:// o https://")
    if a.comprobar:
        comprobar(a.url, a.comprobar)
        return

    print("Rastreando %s (pausa %.1f s, máximo %d URL)" % (a.url, a.espera, a.maximo))
    datos, entrantes, _ = rastrear(a.url, a.espera, a.maximo, not a.ignorar_robots)
    with open(a.salida, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["url", "estado", "profundidad", "enlaces_entrantes", "redirige_a", "tipo", "enlazada_desde"])
        for u, d in sorted(datos.items(), key=lambda x: (x[1]["profundidad"], x[0])):
            ent = entrantes.get(u, [])
            w.writerow([u, d["estado"], d["profundidad"], len(ent), d["destino"], d["tipo"], " | ".join(ent)])
    resumen(datos)
    print("Resultados guardados en", a.salida)


if __name__ == "__main__":
    main()
