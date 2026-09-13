#!/usr/bin/env python3
"""Mapa político de Argentina hecho con caracteres ASCII.

Rasteriza los límites provinciales (geoBoundaries, más las Islas Malvinas) sobre la
grilla de celdas de la terminal: cada celda se asigna a la jurisdicción que más la
ocupa, los límites se dibujan con | / \\ _ - y cada provincia lleva un color distinto
del de sus vecinas. Las provincias van numeradas de norte a sur con sus referencias.

Uso:  mapa.py                     → dibuja en la terminal actual (ANSI)
      mapa.py --png archivo.png   → vista previa en imagen
"""
import json, math, os, sys, subprocess, argparse
from collections import deque
from PIL import Image, ImageDraw, ImageFont

DATOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "argentina.json")
ASPECTO_CELDA = 19 / 8          # alto/ancho de la celda de kitty (medido)
SS = 4                          # submuestreo por celda para decidir a quién pertenece
CABA = "CABA"

# paleta apagada, para que las pinturas sigan siendo las protagonistas
PALETA = [(200, 180, 138), (143, 168, 118), (122, 156, 198), (196, 127, 94), (168, 139, 176), (111, 179, 168)]
CREMA    = (230, 223, 207)      # contorno nacional (el crema de la pantalla de bloqueo)
LIMITE   = (128, 122, 110)      # límites entre provincias: más tenues que el contorno
CELESTE  = (116, 172, 223)      # rótulos del mar (el celeste de la bandera)
ESCALA_TEXTO = 2               # letras grandes (protocolo de tamaño de texto de kitty)
TENUE    = 0.80                 # brillo del relleno respecto del color de la provincia

def cargar():
    with open(DATOS, encoding="utf-8") as fh:
        return json.load(fh)

def area(r):
    return abs(sum(r[i][0]*r[i-1][1] - r[i-1][0]*r[i][1] for i in range(len(r)))) / 2

def construir(cols, filas):
    geo = cargar()
    nombres = sorted(geo["provincias"], key=lambda n: -sum(area(r) for r in geo["provincias"][n]))
    nombres.remove(CABA); nombres.append(CABA)           # la más chica se dibuja última
    unidades = [(n, geo["provincias"][n]) for n in nombres]
    unidades.append(("Islas Malvinas", geo["malvinas"]))

    lon0, lon1, lat0, lat1 = -73.6, -53.5, -55.1, -21.7
    coslat = math.cos(math.radians((lat0 + lat1) / 2))
    wp, hp = (lon1 - lon0) * coslat, (lat1 - lat0)
    s = max(hp / filas, wp * ASPECTO_CELDA / cols)        # grados por fila
    mcols, mfilas = math.ceil(wp * ASPECTO_CELDA / s), math.ceil(hp / s)
    ox, oy = (cols - mcols) // 2, (filas - mfilas) // 2

    img = Image.new("L", (cols * SS, filas * SS), 0)
    d = ImageDraw.Draw(img)
    for i, (_, polys) in enumerate(unidades, start=1):
        for r in polys:
            pts = [((ox + (x - lon0) * coslat * ASPECTO_CELDA / s) * SS, (oy + (lat1 - y) / s) * SS) for x, y in r]
            if len(pts) >= 3:
                d.polygon(pts, fill=i)
    px = img.load()

    ids = [[0] * cols for _ in range(filas)]
    icaba = nombres.index(CABA) + 1
    for fy in range(filas):
        for fx in range(cols):
            cuenta = {}
            for sy in range(SS):
                for sx in range(SS):
                    v = px[fx*SS + sx, fy*SS + sy]
                    if v: cuenta[v] = cuenta.get(v, 0) + 1
            tierra = sum(cuenta.values())
            if cuenta.get(icaba, 0) >= 2:
                ids[fy][fx] = icaba                        # que CABA no desaparezca
            elif tierra >= SS * SS * 0.3:
                ids[fy][fx] = max(cuenta, key=cuenta.get)
    return unidades, ids, (ox, oy, mcols, mfilas)

def colorear(unidades, ids):
    """Coloreo greedy: provincias vecinas nunca comparten color."""
    filas, cols = len(ids), len(ids[0])
    vecinos = {i: set() for i in range(1, len(unidades) + 1)}
    for y in range(filas):
        for x in range(cols):
            a = ids[y][x]
            if not a: continue
            for dy, dx in ((0, 1), (1, 0)):
                yy, xx = y + dy, x + dx
                if yy < filas and xx < cols and ids[yy][xx] and ids[yy][xx] != a:
                    vecinos[a].add(ids[yy][xx]); vecinos[ids[yy][xx]].add(a)
    color = {}
    for i in sorted(vecinos, key=lambda k: -len(vecinos[k])):
        usados = {color[v] for v in vecinos[i] if v in color}
        color[i] = next(c for c in range(len(PALETA)) if c not in usados)
    return color

def caracter_borde(ids, y, x):
    """Marching squares sobre el bloque 2x2 que empieza en (y, x).

    Devuelve (carácter, es_contorno_nacional) o (None, False) si no hay límite.
    Así cada frontera se dibuja una sola vez, con el trazo que sigue su forma.
    """
    filas, cols = len(ids), len(ids[0])
    g = lambda yy, xx: ids[yy][xx] if yy < filas and xx < cols else 0
    a, b, c, d = g(y, x), g(y, x+1), g(y+1, x), g(y+1, x+1)
    if a == b == c == d:              return None, False
    if not (a or b or c or d):        return None, False
    nacional = 0 in (a, b, c, d)
    if a == c and b == d:             ch = "|"      # límite vertical
    elif a == b and c == d:           ch = "_"      # límite horizontal
    elif a == b == c:                 ch = "/"      # corta la esquina inf-der
    elif b == c == d:                 ch = "/"      # corta la esquina sup-izq
    elif a == b == d:                 ch = "\\"     # corta la esquina inf-izq
    elif a == c == d:                 ch = "\\"     # corta la esquina sup-der
    elif a == d and b == c:           ch = "+"      # silla
    else:                             ch = "+"      # tres o cuatro jurisdicciones
    return ch, nacional

def dibujar_regiones(ids, relleno, contorno=None, limite=None):
    """Convierte una grilla de regiones en caracteres, con el estilo del mapa.

    ids: grilla de enteros (0 = vacío). relleno(id) → color del punto de relleno.
    El borde entre una región y el vacío va en `contorno`; entre dos regiones, en `limite`.
    La usan el mapa y los retratos, así los dos comparten exactamente el mismo trazo.
    """
    contorno = contorno or CREMA; limite = limite or LIMITE
    filas, cols = len(ids), len(ids[0])
    celdas = [[(" ", None)] * cols for _ in range(filas)]
    for y in range(filas):
        for x in range(cols):
            ch, exterior = caracter_borde(ids, y, x)
            if ch:
                celdas[y][x] = (ch, contorno if exterior else limite)
            elif ids[y][x]:
                celdas[y][x] = (".", relleno(ids[y][x]))
    # diagonales poco inclinadas: "//" se lee mejor como "_/" y dos barras invertidas como "\\_"
    for fila in celdas:
        for x in range(len(fila) - 1):
            if fila[x][0] == "/" and fila[x + 1][0] == "/": fila[x] = ("_", fila[x][1])
    for fila in celdas:
        for x in range(len(fila) - 1, 0, -1):
            if fila[x - 1][0] == "\\" and fila[x][0] == "\\": fila[x] = ("_", fila[x][1])
    return celdas

def rotulos(unidades, ids):
    """Número de cada provincia en su celda más alejada de los bordes."""
    filas, cols = len(ids), len(ids[0])
    dist = [[-1] * cols for _ in range(filas)]
    q = deque()
    for y in range(filas):
        for x in range(cols):
            if ids[y][x] and caracter_borde(ids, y, x)[0]:
                dist[y][x] = 0; q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1,0),(-1,0),(0,1),(0,-1)):
            yy, xx = y+dy, x+dx
            if 0 <= yy < filas and 0 <= xx < cols and ids[yy][xx] == ids[y][x] and dist[yy][xx] < 0:
                dist[yy][xx] = dist[y][x] + 1; q.append((yy, xx))
    candidatos, centro = {}, {}
    for y in range(filas):
        for x in range(cols):
            i = ids[y][x]
            if not i: continue
            centro.setdefault(i, []).append((y, x))
            ok2 = x + 1 < cols and ids[y][x+1] == i
            candidatos.setdefault(i, []).append((min(dist[y][x], dist[y][x+1] if ok2 else -1), y, x))
    mejor = {i: sorted(c, reverse=True) for i, c in candidatos.items()}
    # numeración de norte a sur (y después de oeste a este); Malvinas va sin número
    orden = sorted((i for i in centro if unidades[i-1][0] != "Islas Malvinas"),
                   key=lambda i: (round(sum(p[0] for p in centro[i]) / len(centro[i])),
                                  sum(p[1] for p in centro[i]) / len(centro[i])))
    numero = {i: k + 1 for k, i in enumerate(orden)}
    return numero, mejor, centro

def componer(cols, filas, numeros=False, rotulo_malvinas=False):
    unidades, ids, (ox, oy, mcols, mfilas) = construir(cols, filas)
    color = colorear(unidades, ids)
    numero, mejor, centro = rotulos(unidades, ids)
    tenue = lambda c: tuple(int(v * TENUE) for v in c)
    celdas = dibujar_regiones(ids, lambda i: tenue(PALETA[color[i]]))
    # números: en la celda más interior cuyo lugar sea relleno, sin pisar ningún límite
    for i, n in (numero.items() if numeros else ()):
        txt = str(n)
        for _, y, x in mejor[i]:
            if x + len(txt) <= cols and all(celdas[y][x + k][0] == "." for k in range(len(txt))):
                for k, c in enumerate(txt): celdas[y][x + k] = (c, PALETA[color[i]])
                break
        else:
            # jurisdicción demasiado chica para tener relleno (CABA): rótulo afuera, en el agua
            ys = [q[0] for q in centro[i]]; xs = [q[1] for q in centro[i]]
            ry, rx = round(sum(ys) / len(ys)), max(xs) + 2
            while rx + len(txt) <= cols and any(celdas[ry][rx + k][0] != " " for k in range(len(txt))):
                rx += 1
            for k, c in enumerate(txt):
                if rx + k < cols: celdas[ry][rx + k] = (c, PALETA[color[i]])
    # Malvinas: rótulo en el agua, a la derecha de las islas
    im = next(k for k, u in enumerate(unidades, 1) if u[0] == "Islas Malvinas")
    if rotulo_malvinas and im in centro:
        ys = [p[0] for p in centro[im]]; xs = [p[1] for p in centro[im]]
        ry, rx = round(sum(ys) / len(ys)), max(xs) + 2
        for k, c in enumerate("Islas Malvinas"):
            if rx + k < cols: celdas[ry][rx + k] = (c, CELESTE)
    leyenda = [(numero[i], unidades[i-1][0], PALETA[color[i]]) for i in sorted(numero, key=numero.get)]
    return celdas, leyenda, (ox, oy, mcols, mfilas)

def pantalla(cols, filas, ancho_leyenda=34, referencias=False):
    """El mapa a la izquierda y, a la derecha, un espacio libre (o las referencias)."""
    mcols = cols - ancho_leyenda
    celdas, leyenda, _ = componer(mcols, filas, numeros=referencias, rotulo_malvinas=referencias)
    if not referencias:
        return [fila + [(" ", None)] * ancho_leyenda for fila in celdas]
    vacio = (" ", None)
    celdas = [fila + [vacio] * ancho_leyenda for fila in celdas]
    def escribir(y, x, texto, color):
        for k, c in enumerate(texto):
            if 0 <= y < filas and 0 <= x + k < cols: celdas[y][x + k] = (c, color)
    x0 = mcols + 2
    alto = 6 + len(leyenda) + 3
    y = max(0, (filas - alto) // 2)
    escribir(y, x0, "REPÚBLICA ARGENTINA", CREMA)
    escribir(y + 1, x0, "-" * 19, LIMITE)
    escribir(y + 2, x0, "división política", LIMITE)
    y += 4
    for n, nombre, color in leyenda:
        escribir(y, x0, f"{n:>2}", color)
        escribir(y, x0 + 4, nombre, CREMA)
        y += 1
    escribir(y + 1, x0 + 4, "Islas Malvinas", CELESTE)
    escribir(y + 2, x0 + 4, "(Tierra del Fuego)", LIMITE)
    return celdas

def ansi(celdas):
    out = []
    for fila in celdas:
        linea, previo = [], None
        for ch, c in fila:
            if c != previo:
                linea.append("\x1b[0m" if c is None else f"\x1b[38;2;{c[0]};{c[1]};{c[2]}m"); previo = c
            linea.append(ch)
        out.append("".join(linea) + "\x1b[0m")
    return "\n".join(out)

def ruta_fuente():
    for q in ("JetBrainsMono Nerd Font Mono:style=Regular", "monospace"):
        try:
            r = subprocess.run(["fc-match", "-f", "%{file}", q], capture_output=True, text=True).stdout.strip()
            if r and os.path.exists(r): return r
        except OSError: pass
    raise SystemExit("sin fuente monoespaciada")

def png(celdas, ruta, cw=8, ch=19, escala=2, fondo=(14, 16, 20)):
    cw, ch = cw * escala, ch * escala
    img = Image.new("RGB", (len(celdas[0]) * cw, len(celdas) * ch), fondo)
    d = ImageDraw.Draw(img); f = ImageFont.truetype(ruta_fuente(), int(ch * 0.78))
    grande = ImageFont.truetype(ruta_fuente(), int(ch * 0.78 * ESCALA_TEXTO))
    for y, fila in enumerate(celdas):
        for x, (c, col) in enumerate(fila):
            if not col or c in (" ", ""): continue
            if len(c) > 1:              # texto grande: cada letra ocupa ESCALA_TEXTO×ESCALA_TEXTO celdas
                for k, letra in enumerate(c):
                    d.text(((x + k * ESCALA_TEXTO) * cw + cw * ESCALA_TEXTO / 2, y * ch + ch * ESCALA_TEXTO / 2),
                           letra, font=grande, fill=col, anchor="mm")
            else:
                d.text((x * cw + cw / 2, y * ch + ch / 2), c, font=f, fill=col, anchor="mm")
    img.save(ruta)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--png"); ap.add_argument("--cols", type=int); ap.add_argument("--filas", type=int)
    ap.add_argument("--referencias", action="store_true", help="números en el mapa y lista de provincias")
    a = ap.parse_args()
    try: tc, tf = os.get_terminal_size()
    except OSError: tc, tf = 200, 90
    cols, filas = a.cols or tc, a.filas or tf
    celdas = pantalla(cols, filas, referencias=a.referencias)
    if a.png: png(celdas, a.png); print(f"{a.png}: {cols}x{filas} celdas")
    else: sys.stdout.write("\x1b[2J\x1b[H" + ansi(celdas)); sys.stdout.flush()
