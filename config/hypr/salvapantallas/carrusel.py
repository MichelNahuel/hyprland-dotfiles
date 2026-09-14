#!/usr/bin/env python3
"""Salvapantallas: mapa político de Argentina + carrusel de próceres.

A la izquierda el mapa, con la provincia de turno iluminada. A la derecha su
personaje, con nombre, fechas y provincia. El cambio de un personaje al siguiente
es el barrido de la N de la consola: salvas de 4 olas que suben desde abajo; cada
ola que pasa por una fila gira sus caracteres (/ - \\) y, pasadas las cuatro, la
fila ya muestra el retrato nuevo.

Orden: Entre Ríos, el resto en orden alfabético, Tierra del Fuego al final.

Uso:  carrusel.py                          → en la terminal (salvapantallas)
      carrusel.py --video salida.mp4       → vista previa en video
"""
import json, os, sys, time, signal, argparse, shutil, subprocess, hashlib, textwrap
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import mapa, retratos

CACHE = os.path.expanduser("~/.cache/salvapantallas")
OLAS = 4                    # olas por salva, como en la N
MS_PASO = 40                # cada paso de la salva sube una fila
PASOS_APARICION = 100      # la imagen inicial se arma en 100 pasos de MS_PASO (4 s)
GRACIA_ENTRADA = 1.0         # segundos iniciales en los que se ignora el mouse/teclado
UMBRAL_MOUSE = 3             # filas (y el doble de columnas) que hay que mover el mouse para salir
MS_LATIDO = 110              # la provincia iluminada: cada paso de la salva (como la N)
MS_CIERRE_LATIDO = 700       # la provincia entera, entre una salva y la siguiente
MARGEN_RELOJ = 1             # filas de aire arriba del reloj (y el doble de columnas a la derecha)
SEG_QUIETO = 9              # tiempo que queda cada personaje
FILAS_RETRATO = 80
ANCHO_DESCRIPCION = 90        # letras por renglón de la descripción (en letra grande)
CICLO = ("/", "-", "\\")    # lo que muestra una fila mientras la cruzan las olas
CELESTE, CREMA, GRIS = mapa.CELESTE, mapa.CREMA, mapa.LIMITE
TEXTO = (196, 189, 174)       # fechas y descripción: más claro que GRIS para que se lea
DORADO = (236, 196, 110)       # días especiales
TEXTO_DIA = (240, 226, 190)
COLORES_CHISPA = [(255, 236, 170), (236, 196, 110), (210, 235, 255), (255, 255, 255)]
FORMA_CHISPA = " .+*x*+. "     # cómo evoluciona una chispa durante su vida
CHISPAS = 140                  # chispas a la vez alrededor del personaje del día
PUNTO_MS = 180                 # giro de los dos puntos del reloj

def orden_provincias(proceres):
    sin_tildes = lambda s: s.lower().translate(str.maketrans("áéíóúü", "aeiouu"))
    todas = [p["provincia"] for p in proceres]
    resto = sorted((p for p in todas if p not in ("Entre Ríos", "Tierra del Fuego")), key=sin_tildes)
    return ["Entre Ríos"] + resto + ["Tierra del Fuego"]

NOMBRE_OFICIAL = {"Tierra del Fuego": "Tierra del Fuego, Antártida e Islas del Atlántico Sur",
                  "CABA": "Ciudad Autónoma de Buenos Aires"}

# ------------------------------------------------------------------ piezas
def retrato_en_cache(prov, dib, filas):
    """Los retratos tardan en calcularse: se guardan ya convertidos a caracteres."""
    ruta = os.path.join(AQUI, "imagenes", dib["imagen"])
    firma = hashlib.sha1(json.dumps([dib, filas, os.path.getmtime(ruta), retratos.VERSION]).encode()).hexdigest()[:10]
    archivo = os.path.join(CACHE, f"{prov}-{firma}.json")
    if os.path.exists(archivo):
        with open(archivo) as fh: return [[(c, tuple(k) if k else None) for c, k in fila] for fila in json.load(fh)]
    celdas = retratos.dibujar(ruta, filas, dib["recorte"], dib.get("ovalo", 0.47), dib.get("sombreado"), dib.get("figura"), dib.get("fondo_claro"), dib.get("fondo_azul"),
                               dib.get("fondo_color"), dib.get("figura_completa", False),
                               dib.get("silueta"), dib.get("contraste_local", 0.6),
                               dib.get("solo_cara", False))
    os.makedirs(CACHE, exist_ok=True)
    with open(archivo, "w") as fh: json.dump(celdas, fh)
    return celdas

def renglones(personaje, prov):
    """Líneas de texto bajo el retrato: (texto, color); "" es un renglón chico de separación."""
    texto = [(personaje["nombre"].upper(), CREMA)]
    if personaje.get("apodo"):
        texto.append((f"«{personaje['apodo']}»", CREMA))
    texto += [(personaje["vida"], TEXTO), (NOMBRE_OFICIAL.get(prov, prov), CELESTE)]
    if personaje.get("descripcion"):
        texto.append(("", None))
        texto += [(linea, TEXTO) for linea in textwrap.wrap(personaje["descripcion"], ANCHO_DESCRIPCION)]
    return texto

def filas_texto(texto):
    return sum(1 if not linea else mapa.ESCALA_TEXTO for linea, _ in texto)

def panel(personaje, prov, retrato, ancho, alto):
    """Retrato centrado arriba y, debajo, nombre, apodo, fechas, provincia y descripción.

    El texto va en letra grande: cada renglón es una celda "ancla" con la línea completa y
    las celdas que tapa (ESCALA×largo columnas, ESCALA filas) quedan como "" (ocupadas).
    """
    E = mapa.ESCALA_TEXTO
    celdas = [[(" ", None)] * ancho for _ in range(alto)]
    rh, rw = len(retrato), len(retrato[0])
    texto = renglones(personaje, prov)
    alto_texto = filas_texto(texto)
    bloque = rh + 1 + alto_texto
    oy, ox = max(0, (alto - bloque) // 2), max(0, (ancho - rw) // 2)
    for y in range(min(rh, alto)):
        for x in range(min(rw, ancho - ox)):
            celdas[oy + y][ox + x] = retrato[y][x]
    y = oy + rh + 1
    for linea, color in texto:
        if not linea:
            y += 1; continue
        linea = linea[:ancho // E]
        x0 = max(0, (ancho - E * len(linea)) // 2)
        if y + E <= alto:
            for dy in range(E):
                for dx in range(E * len(linea)):
                    celdas[y + dy][x0 + dx] = ("", None)
            celdas[y][x0] = (linea if len(linea) > 1 else linea + " ", color)
        y += E
    return celdas

class Mapa:
    """Mapa con una provincia iluminada; se calcula una sola vez por tamaño."""
    def __init__(self, cols, filas):
        self.unidades, self.ids, _ = mapa.construir(cols, filas)
        self.color = mapa.colorear(self.unidades, self.ids)
        self.nombre = {i: u[0] for i, u in enumerate(self.unidades, 1)}
        self._cache = {}
        self._activas = {}
    def con(self, prov):
        if prov not in self._cache:
            iluminadas = {i for i, n in self.nombre.items()
                          if n == prov or (prov == "Tierra del Fuego" and n == "Islas Malvinas")}
            vivo = lambda i: tuple(min(255, int(v * 1.30)) for v in mapa.PALETA[self.color[i]])
            def relleno(i):
                return vivo(i) if i in iluminadas else tuple(int(v * 0.40) for v in mapa.PALETA[self.color[i]])
            celdas = mapa.dibujar_regiones(self.ids, relleno)
            # el contorno de la provincia activa también toma su color, si no solo cambian los puntos
            filas, cols = len(self.ids), len(self.ids[0])
            for y in range(filas):
                for x in range(cols):
                    ch, _ = celdas[y][x]
                    if ch in (" ", "."): continue
                    cerca = {self.ids[yy][xx] for yy in (y - 1, y, y + 1) for xx in (x - 1, x, x + 1)
                             if 0 <= yy < filas and 0 <= xx < cols} & iluminadas
                    if cerca: celdas[y][x] = (ch, vivo(min(cerca)))
            self._cache[prov] = celdas
            self._activas[prov] = [(y, x) for y in range(filas) for x in range(cols)
                                   if celdas[y][x][0] != " " and (self.ids[y][x] in iluminadas or (
                                       celdas[y][x][0] != "." and {self.ids[yy][xx] for yy in (y - 1, y, y + 1)
                                       for xx in (x - 1, x, x + 1) if 0 <= yy < filas and 0 <= xx < cols} & iluminadas))]
        return self._cache[prov]

    def latido(self, prov, ms_total):
        """Cuadros del mapa mientras el personaje está quieto: salvas de olas que suben por la
        provincia iluminada, como la N y la M de la consola. Cada ola hace avanzar una fase a
        las filas que toca; cada carácter sigue su ciclo y la ola que pasa brilla un poco más.
        Devuelve [(celdas, ms)] que suman `ms_total` y terminan con la provincia entera."""
        base = self.con(prov)
        activas = self._activas[prov]
        if not activas:
            return [(base, ms_total)]
        filas_prov = sorted({y for y, _ in activas})
        alto = len(filas_prov)
        cuadros, t = [], 0
        while True:
            dur = (alto + OLAS - 1) * MS_LATIDO + MS_CIERRE_LATIDO
            if t + dur > ms_total: break
            fases = [0] * alto
            for paso in range(alto + OLAS - 1):
                frente = {}
                for k in range(OLAS):
                    r = alto - 1 - (paso - k)              # de abajo hacia arriba
                    if 0 <= r < alto and paso - k >= 0:
                        fases[r] += 1; frente[r] = k
                c = [fila[:] for fila in base]
                por_fila = {fy: (fases[i], frente.get(i)) for i, fy in enumerate(filas_prov)}
                for y, x in activas:
                    fase, k = por_fila[y]
                    ch, col = base[y][x]
                    nuevo = ciclo_celda(ch)[fase % OLAS]
                    if k is not None:                       # la ola que pasa: más clara
                        col = tuple(min(255, int(v * (1.35 - 0.08 * k))) for v in col)
                    c[y][x] = (nuevo, col)
                cuadros.append((c, MS_LATIDO)); t += MS_LATIDO
            cuadros.append((base, MS_CIERRE_LATIDO)); t += MS_CIERRE_LATIDO
        cuadros.append((base, max(1, ms_total - t)))
        return cuadros

def ciclo_celda(ch):
    """Ciclo de 4 fases de cada carácter del mapa, con los mismos papeles que la N de la consola."""
    if ch == "|": return ("|", "/", "-", "\\")
    if ch == "/": return ("/", "\\", "/", "\\")
    if ch == "\\": return ("\\", "/", "\\", "/")
    if ch == "_": return ("_", "-", "_", "-")
    if ch == ".": return (".", ":", ".", ":")
    return (ch, ch, ch, ch)

# ------------------------------------------------------------------ barrido
def barrido(viejo, nuevo, desde=0):
    """Cuadros de la salva de 4 olas que convierte `viejo` en `nuevo`, fila por fila desde abajo.
    Antes de la columna `desde` (el mapa) la ola solo pasa por las celdas que cambian."""
    alto = len(nuevo)
    fase = [0] * alto
    for t in range(alto + OLAS):
        frente = {}
        for k in range(OLAS):
            r = alto - 1 - (t - k)
            if 0 <= r < alto and t - k >= 0:
                fase[r] += 1; frente[r] = k
        cuadro = []
        for r in range(alto):
            if fase[r] == 0:        cuadro.append(viejo[r])
            elif fase[r] >= OLAS:   cuadro.append(nuevo[r])
            else:
                g = CICLO[fase[r] - 1]
                brillo = 1.0 - 0.18 * frente.get(r, OLAS - 1)       # la ola de adelante, la más clara
                col = tuple(int(v * brillo) for v in CREMA)
                cuadro.append([(a if a == b else (g, col)) if x < desde else
                               ((g, col) if (a[0] != " " or b[0] != " ") else (" ", None))
                               for x, (a, b) in enumerate(zip(viejo[r], nuevo[r]))])
        yield cuadro

# ------------------------------------------------------------------ aparición
def aparicion(final, pasos=PASOS_APARICION, semilla=None):
    """Cuadros en los que `final` se va armando con caracteres que aparecen al azar.

    Cada carácter suelto es una unidad; en el texto grande cada letra es una unidad (las letras
    todavía ocultas se dibujan como espacios, así el renglón mantiene su ancho)."""
    import random
    azar = random.Random(semilla)
    unidades = []
    for y, fila in enumerate(final):
        for x, (ch, col) in enumerate(fila):
            if ch in (" ", "") or not col: continue
            if len(ch) > 1:
                pre = len(ch) - len(mapa.ancla(ch)[1])      # el prefijo de escala no es una letra
                unidades += [(y, x, k) for k, letra in enumerate(ch) if k >= pre and letra != " "]
            else:
                unidades.append((y, x, None))
    azar.shuffle(unidades)
    vacio = [[(" ", None) if ch != "" else ("", None) for ch, _ in fila] for fila in final]
    for y, fila in enumerate(final):                  # los renglones grandes arrancan en blanco
        for x, (ch, col) in enumerate(fila):
            if len(ch) > 1:
                pre = len(ch) - len(mapa.ancla(ch)[1])
                vacio[y][x] = (ch[:pre] + " " * (len(ch) - pre), col)
    cuadro = [fila[:] for fila in vacio]
    por_paso = max(1, -(-len(unidades) // pasos))
    for i in range(0, len(unidades), por_paso):
        for y, x, k in unidades[i:i + por_paso]:
            if k is None:
                cuadro[y][x] = final[y][x]
            else:
                texto = cuadro[y][x][0]
                cuadro[y][x] = (texto[:k] + final[y][x][0][k] + texto[k + 1:], final[y][x][1])
        yield [fila[:] for fila in cuadro]

def desaparicion(inicial, pasos=PASOS_APARICION, semilla=None):
    """Lo inverso de `aparicion`: los caracteres se van apagando al azar hasta no quedar ninguno."""
    cuadros = list(aparicion(inicial, pasos, semilla))
    vacio = [[(" ", None) if ch != "" else ("", None) for ch, _ in fila] for fila in inicial]
    for y, fila in enumerate(inicial):
        for x, (ch, col) in enumerate(fila):
            if len(ch) > 1:
                pre = len(ch) - len(mapa.ancla(ch)[1])
                vacio[y][x] = (ch[:pre] + " " * (len(ch) - pre), col)
    yield from reversed(cuadros[:-1])
    yield vacio

# ------------------------------------------------------------------ reloj
# Dígitos de "andamio", como la N de la consola: rieles |/| y tapas _ ▔, de 7 filas × 9 columnas.
SEGMENTOS = {"0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc",
             "5": "afgcd", "6": "afgecd", "7": "abc", "8": "abcdefg", "9": "abcdfg"}
PUNTO_GIRA = "▖▘▝▗"             # los dos puntos giran como los de la consola

def digito(d):
    seg = SEGMENTOS[d]
    g = [[" "] * 9 for _ in range(7)]
    riel = lambda r: ["|", "/" if r % 2 else "\\", "|"]
    if "a" in seg: g[0] = ["_"] * 9
    else:
        if "f" in seg: g[0][0:3] = ["_"] * 3
        if "b" in seg: g[0][6:9] = ["_"] * 3
    for r in range(1, 6):
        izq = ("f" in seg) if r <= 2 else ("e" in seg) if r >= 4 else ("f" in seg or "e" in seg)
        der = ("b" in seg) if r <= 2 else ("c" in seg) if r >= 4 else ("b" in seg or "c" in seg)
        if izq: g[r][0:3] = riel(r)
        if der: g[r][6:9] = riel(r)
    if "g" in seg: g[3][3:6] = ["_"] * 3
    if "d" in seg: g[6] = ["▔"] * 9
    else:
        if "e" in seg: g[6][0:3] = ["▔"] * 3
        if "c" in seg: g[6][6:9] = ["▔"] * 3
    return g

def ciclo_reloj(ch):
    if ch == "▔": return ("▔", "-", "▔", "-")
    return ciclo_celda(ch)

class Reloj:
    """La hora con caracteres en la esquina superior derecha. Cuando cambia el minuto la recorre
    una salva de olas (como a la N) y los dos puntos giran todo el tiempo."""
    ALTO = 7
    def __init__(self):
        self.minuto, self.salva = None, 0.0
    def aplicar(self, cuadro):
        ahora = time.time()
        texto = time.strftime("%H:%M")
        if texto != self.minuto:
            self.minuto, self.salva = texto, ahora
        piezas = []
        for ch in texto:
            if ch == ":":
                punto = PUNTO_GIRA[int(ahora * 1000 / PUNTO_MS) % 4]
                piezas.append([[" "] * 3 if r not in (2, 4) else [" ", punto, " "] for r in range(self.ALTO)])
            else:
                piezas.append(digito(ch))
        filas_arte = []
        for r in range(self.ALTO):
            fila = []
            for k, pieza in enumerate(piezas):
                if k: fila.append(" ")
                fila += pieza[r]
            filas_arte.append(fila)
        ancho_arte = len(filas_arte[0])
        x0, y0 = len(cuadro[0]) - ancho_arte - MARGEN_RELOJ * 2, MARGEN_RELOJ
        paso = int((ahora - self.salva) * 1000 / MS_LATIDO)
        c = [fila[:] if y0 <= y < y0 + self.ALTO else fila for y, fila in enumerate(cuadro)]
        for r, fila in enumerate(filas_arte):
            desde_abajo = self.ALTO - 1 - r
            fase = max(0, min(OLAS, paso - desde_abajo + 1))           # olas que ya pasaron por la fila
            en_ola = 0 <= paso - desde_abajo < OLAS
            col = tuple(min(255, int(v * 1.3)) for v in CREMA) if en_ola else CREMA
            for x, ch in enumerate(fila):
                if ch == " ": continue
                if ch in PUNTO_GIRA:
                    c[y0 + r][x0 + x] = (ch, CREMA)
                else:
                    c[y0 + r][x0 + x] = (ciclo_reloj(ch)[fase % OLAS], col)
        return c

# ------------------------------------------------------------------ efemérides
def efemerides_de_hoy():
    """{provincia: [motivos]} de hoy (SALVA_FECHA=MM-DD para probar otra fecha)."""
    hoy = os.environ.get("SALVA_FECHA") or time.strftime("%m-%d")
    try:
        datos = json.load(open(os.path.join(AQUI, "efemerides.json")))
    except OSError:
        return {}
    return {prov: [motivo for fecha, motivo in lista if fecha == hoy]
            for prov, lista in datos.items() if any(fecha == hoy for fecha, _ in lista)}

def diseno_efemeride(mapa_c, panel_c, mcols, motivos):
    """Dónde y cómo va el cartel del día especial: entre el mapa y el retrato, centrado en alto.
    Devuelve [(y, x, texto, color)] en letra grande."""
    E = mapa.ESCALA_TEXTO
    filas = len(mapa_c)
    borde_mapa = [max([x for x, (c, _) in enumerate(f) if c != " "] or [0]) for f in mapa_c]
    borde_retrato = [mcols + min([x for x, (c, _) in enumerate(f) if c not in (" ", "")] or [len(f)])
                     for f in panel_c]
    ancho = 40
    for _ in range(3):
        renglones_ = [("* HOY *", DORADO), ("", None)]
        for k, motivo in enumerate(motivos):
            if k: renglones_.append(("", None))
            renglones_ += [(l, TEXTO_DIA) for l in textwrap.wrap(motivo, max(8, ancho // E))]
        alto = sum(E if t else 1 for t, _ in renglones_)
        y0 = max(0, filas // 2 - alto // 2 - 4)
        izq = max(borde_mapa[y0:y0 + alto]) + 3
        der = min(borde_retrato[y0:y0 + alto]) - 3
        ancho = max(16, der - izq)
    salida, y = [], y0
    centro = (izq + der) // 2
    for t, color in renglones_:
        if not t:
            y += 1; continue
        salida.append((y, max(0, centro - E * len(t) // 2), t, color))
        y += E
    return salida

def con_cartel(cuadro, diseno):
    E = mapa.ESCALA_TEXTO
    filas_tocadas = {y + dy for y, _, _, _ in diseno for dy in range(E)}
    c = [fila[:] if y in filas_tocadas else fila for y, fila in enumerate(cuadro)]
    for y, x, t, color in diseno:
        for dy in range(E):
            for dx in range(E * len(t)):
                if 0 <= y + dy < len(c) and 0 <= x + dx < len(c[0]): c[y + dy][x + dx] = ("", None)
        c[y][x] = (t if len(t) > 1 else t + " ", color)
    return c

def anillo_chispas(panel_c, mcols, alto_retrato, oy):
    """Celdas vacías alrededor del retrato (a 2-6 celdas de su silueta) donde pueden brillar chispas."""
    import numpy as np
    from scipy import ndimage
    filas, ancho = len(panel_c), len(panel_c[0])
    silueta = np.zeros((filas, ancho), bool)
    for y in range(oy, min(filas, oy + alto_retrato)):
        for x, (ch, _) in enumerate(panel_c[y]):
            if ch not in (" ", ""): silueta[y, x] = True
    silueta = ndimage.binary_fill_holes(silueta)
    if silueta.any():
        # cierre convexo: sin esto, una entalladura del contorno (el hueco entre la cabeza y un
        # brazo levantado, o entre un instrumento y el cuerpo) queda "afuera" de la silueta pero
        # visualmente adentro de la figura, y ahí podían caer chispas que parecen superpuestas
        from scipy.spatial import ConvexHull
        from PIL import Image, ImageDraw
        ys, xs = np.nonzero(silueta)
        try:
            casco = ConvexHull(np.column_stack([xs, ys]))
            poligono = [(int(xs[i]), int(ys[i])) for i in casco.vertices]
            img = Image.new("1", (ancho, filas), 0)
            ImageDraw.Draw(img).polygon(poligono, fill=1)
            silueta |= np.asarray(img, dtype=bool)
        except Exception:
            pass    # menos de 3 puntos o colineales: se queda con la silueta rellena
    dist = ndimage.distance_transform_edt(~silueta, sampling=(1, 0.5))
    anillo = (dist >= 1.5) & (dist <= 4.5)
    anillo[oy + alto_retrato:, :] = False
    anillo[:MARGEN_RELOJ + Reloj.ALTO + 1, ancho - 50:] = False    # no pisar el reloj
    return [(int(y), int(x) + mcols) for y, x in zip(*np.nonzero(anillo))]

def con_chispas(cuadro, anillo):
    """Chispas que titilan alrededor del personaje del día: aparecen, crecen y se apagan."""
    if not anillo: return cuadro
    ahora = int(time.time() * 1000)
    c = None
    for i in range(CHISPAS):
        vida = 700 + (i * 37) % 600
        t = ahora + i * 911
        ciclo, fase = divmod(t, vida)
        pos = anillo[hash((i, ciclo)) % len(anillo)]
        brillo = FORMA_CHISPA[fase * len(FORMA_CHISPA) // vida]
        if brillo == " ": continue
        y, x = pos
        if cuadro[y][x][0] != " ": continue
        if c is None: c = [fila[:] for fila in cuadro]
        c[y][x] = (brillo, COLORES_CHISPA[(i + ciclo) % len(COLORES_CHISPA)])
    return c or cuadro

# ------------------------------------------------------------------ secuencia
def secuencia(cols, filas, una_vuelta=False):
    """Genera (celdas, milisegundos, repintar) sin fin: quieto → barrido → siguiente."""
    proceres = {p["provincia"]: p for p in json.load(open(os.path.join(AQUI, "proceres.json")))}
    dibujos = json.load(open(os.path.join(AQUI, "dibujos.json")))
    orden = [p for p in orden_provincias(proceres.values()) if p in dibujos]
    if os.environ.get("SALVA_PERSONAJES"):          # pruebas: vuelta corta
        orden = orden[:int(os.environ["SALVA_PERSONAJES"])]
    # ancho que ocupa el mapa a esta altura, con la misma proyección que usa mapa.construir
    lon0, lon1, lat0, lat1 = -73.6, -53.5, -55.1, -21.7
    wp = (lon1 - lon0) * mapa.math.cos(mapa.math.radians((lat0 + lat1) / 2))
    mcols = min(cols // 2, mapa.math.ceil(wp * mapa.ASPECTO_CELDA / ((lat1 - lat0) / filas)) + 4)
    pcols = cols - mcols
    m = Mapa(mcols, filas)
    personajes = {}
    for prov in orden:
        p = dict(proceres[prov]); p.update({k: v for k, v in dibujos[prov].items() if k in ("nombre", "vida", "apodo", "descripcion")})
        personajes[prov] = p
    # todos los retratos del mismo alto: el que le deja lugar al texto más largo, con aire arriba y abajo
    fr = min(FILAS_RETRATO, filas - 5 - max(filas_texto(renglones(p, prov)) for prov, p in personajes.items()))
    paneles = {prov: panel(p, prov, retrato_en_cache(prov, dibujos[prov], fr), pcols, filas)
               for prov, p in personajes.items()}
    unir = lambda izq, der: [a + b for a, b in zip(izq, der)]
    reloj = Reloj().aplicar
    # días especiales: esos personajes van primero, con su cartel en el medio y chispas alrededor
    especiales = efemerides_de_hoy()
    if especiales:
        primero = [p for p in orden if p in especiales]
        resto = [p for p in orden if p not in especiales]
        if "Tierra del Fuego" in especiales and "Tierra del Fuego" in orden:
            resto.append("Tierra del Fuego")          # la vuelta siempre termina con el pingüino
        orden = primero + resto
    carteles, anillos = {}, {}
    for prov in especiales:
        if prov not in paneles: continue
        carteles[prov] = diseno_efemeride(m.con(prov), paneles[prov], mcols, especiales[prov])
        rh = len(retrato_en_cache(prov, dibujos[prov], fr))
        oy = max(0, (filas - (rh + 1 + filas_texto(renglones(personajes[prov], prov)))) // 2)
        anillos[prov] = anillo_chispas(paneles[prov], mcols, rh, oy)
    def cuadro_de(prov, mapa_c=None):
        c = unir(mapa_c or m.con(prov), paneles[prov])
        return con_cartel(c, carteles[prov]) if prov in carteles else c
    # al arrancar, el primer personaje y el mapa aparecen de a caracteres al azar
    for cuadro in aparicion(reloj(cuadro_de(orden[0]))):
        yield cuadro, MS_PASO, False
    i = 0
    while True:
        prov, sig = orden[i % len(orden)], orden[(i + 1) % len(orden)]
        # quieto: la provincia "late" con las olas; el primer cuadro repinta todo desde cero
        for k, (mapa_c, ms) in enumerate(m.latido(prov, SEG_QUIETO * 1000)):
            c = reloj(cuadro_de(prov, mapa_c))
            if prov in anillos: c = con_chispas(c, anillos[prov])
            yield c, ms, k == 0
        if una_vuelta and i == len(orden) - 1:
            # fin de la vuelta (el pingüino): se desvanece de a caracteres al azar y termina
            for cuadro in desaparicion(reloj(cuadro_de(prov))):
                yield cuadro, MS_PASO, False
            return
        # el barrido pasa a la vez por el retrato y por el mapa: la provincia nueva se ilumina con la ola
        for cuadro in barrido(cuadro_de(prov), cuadro_de(sig), desde=mcols):
            yield reloj(cuadro), MS_PASO, False
        i += 1

# ------------------------------------------------------------------ salidas
def fila_ansi(fila):
    """Una fila en ANSI. Las anclas de texto grande usan el protocolo de tamaño de texto de kitty
    (OSC 66); las celdas que tapan no se escriben (si no, borrarían la letra grande)."""
    out, previo, absorber, salto = [], None, 0, 0
    for ch, c in fila:
        if ch == "":
            if absorber: absorber -= 1
            else: salto += 1
            continue
        if salto:
            out.append(f"\x1b[{salto}C"); salto = 0
        if c != previo:
            out.append("\x1b[0m" if c is None else f"\x1b[38;2;{c[0]};{c[1]};{c[2]}m"); previo = c
        if len(ch) > 1:
            E, texto = mapa.ancla(ch)
            out.append(f"\x1b]66;s={E};{texto}\x1b\\")
            absorber = E * len(texto) - 1
        else:
            out.append(ch)
    return "".join(out) + "\x1b[0m"

def terminal(una_vuelta=False):
    """Carrusel en la terminal.

    Con SALVA_RESULTADO (lo usa hypr/scripts/salvapantallas.sh) escribe en ese archivo cómo
    terminó: "actividad" si se tocó una tecla o se movió el mouse, "fin" si terminó la vuelta.
    En los dos casos deja la pantalla como está y espera a que el script cierre la ventana.
    """
    import termios, tty, select
    sal, ent = sys.stdout, sys.stdin.fileno()
    viejo_tty = termios.tcgetattr(ent)
    def restaurar(*_):
        sal.write("\x1b[?1003l\x1b[?1006l\x1b[0m\x1b[?25h\x1b[?1049l"); sal.flush()
        termios.tcsetattr(ent, termios.TCSADRAIN, viejo_tty)
        sys.exit(0)
    for s_ in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP): signal.signal(s_, restaurar)
    tty.setcbreak(ent)
    # pantalla alternativa, sin cursor, y que la terminal avise de cualquier movimiento del mouse
    sal.write("\x1b[?1049h\x1b[?25l\x1b[2J\x1b[?1003h\x1b[?1006h"); sal.flush()
    resultado = os.environ.get("SALVA_RESULTADO")
    def terminar(como):
        if resultado:
            with open(resultado, "w") as fh: fh.write(como)
            limite = time.time() + (5 if como == "actividad" else 20)   # la cierra el script; si no, se cierra sola
            while time.time() < limite: time.sleep(0.1)
        restaurar()
    arranque = time.time()
    origen = []                                  # primera posición del mouse vista
    def hubo_actividad(datos):
        """Una tecla cuenta siempre; el mouse, solo si se movió unas celdas (no un temblor)."""
        import re
        texto = datos.decode(errors="ignore")
        reportes = re.findall(r"\x1b\[<(\d+);(\d+);(\d+)[Mm]", texto)
        if re.sub(r"\x1b\[<\d+;\d+;\d+[Mm]", "", texto): return True        # teclado
        for boton, x, y in reportes:
            boton, x, y = int(boton), int(x), int(y)
            if boton < 32 or boton in (64, 65): return True                       # clic o rueda
            if not origen: origen.append((x, y)); continue
            if abs(x - origen[0][0]) > UMBRAL_MOUSE * 2 or abs(y - origen[0][1]) > UMBRAL_MOUSE: return True
        return False
    def esperar(ms):
        """Duerme `ms` milisegundos, pero corta si llega una tecla o un movimiento del mouse."""
        fin = time.time() + ms / 1000
        while True:
            falta = fin - time.time()
            if falta <= 0: return False
            listo, _, _ = select.select([ent], [], [], falta)
            if not listo: return False
            datos = os.read(ent, 4096)
            if time.time() - arranque <= GRACIA_ENTRADA:
                continue                         # al abrir la ventana llega un movimiento "fantasma"
            if hubo_actividad(datos): return True
    cols, filas = shutil.get_terminal_size()
    previo = None
    def mitad_baja(fila):
        """¿La fila es la mitad de abajo de un renglón grande? (tiene celdas "" que no tapa un ancla propia)"""
        absorber = 0
        for ch, _ in fila:
            if ch == "":
                if absorber: absorber -= 1
                else: return True
            elif len(ch) > 1:
                E, texto = mapa.ancla(ch)
                absorber = E * len(texto) - 1
        return False
    for celdas, ms, repintar in secuencia(cols, filas, una_vuelta):
        if previo is None or repintar:
            # al quedar quieto se repinta todo desde cero: no sobrevive ningún resto del barrido
            cambiadas = set(range(len(celdas)))
            partes = ["\x1b[2J"]
        else:
            cambiadas = {y for y, fila in enumerate(celdas) if previo[y] != fila}
            # la letra grande ocupa dos filas: si cambia la de abajo, se repinta también la de arriba
            pendientes = list(cambiadas)
            while pendientes:                     # letras de más de dos filas: se sube hasta el ancla
                y = pendientes.pop()
                if y > 0 and y - 1 not in cambiadas and (mitad_baja(celdas[y]) or mitad_baja(previo[y])):
                    cambiadas.add(y - 1); pendientes.append(y - 1)
            partes = []
        # de abajo hacia arriba y borrando la línea: la fila con el texto grande se dibuja última
        for y in sorted(cambiadas, reverse=True):
            partes.append(f"\x1b[{y+1};1H\x1b[0m\x1b[2K" + fila_ansi(celdas[y]))
        sal.write("".join(partes)); sal.flush()
        if previo is None and os.environ.get("SALVA_LISTO"):
            open(os.environ["SALVA_LISTO"], "w").close()      # aviso: ya está dibujando (para quitar el parpadeo)
        previo = celdas
        if esperar(ms): terminar("actividad")
    terminar("fin")

def video(ruta, cols, filas, segundos, cw=6, ch=14, fps=25):
    from PIL import Image, ImageDraw, ImageFont
    fuentes = {e: ImageFont.truetype(mapa.ruta_fuente(), int(ch * 0.82 * e)) for e in range(1, 8)}
    atlas = {}
    def glifo(c, col, e=1):
        k = (c, col, e)
        if k not in atlas:
            g = Image.new("RGBA", (cw * e, ch * e), (0, 0, 0, 0))
            ImageDraw.Draw(g).text((cw * e / 2, ch * e / 2), c, font=fuentes[e], fill=col, anchor="mm")
            atlas[k] = g
        return atlas[k]
    W, H = cols * cw, filas * ch
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", "-vf", "scale=1920:-2",
                           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", ruta], stdin=subprocess.PIPE)
    total, t = segundos * 1000, 0.0
    for celdas, ms, _ in secuencia(cols, filas):
        img = Image.new("RGB", (W, H), (14, 16, 20))
        for y, fila in enumerate(celdas):
            for x, (c, col) in enumerate(fila):
                if not col or c in (" ", ""): continue
                if len(c) > 1:
                    E, texto = mapa.ancla(c)
                    for k, letra in enumerate(texto):
                        g = glifo(letra, col, E)
                        img.paste(g, ((x + k * E) * cw, y * ch), g)
                else:
                    img.paste(glifo(c, col), (x * cw, y * ch), glifo(c, col))
        n = max(1, round(ms * fps / 1000))
        datos = img.tobytes()
        for _ in range(n): ff.stdin.write(datos)
        t += ms
        if t >= total: break
    ff.stdin.close(); ff.wait()

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--video"); ap.add_argument("--cols", type=int, default=350)
    ap.add_argument("--filas", type=int, default=92); ap.add_argument("--segundos", type=int, default=40)
    ap.add_argument("--una-vuelta", action="store_true", help="una sola vuelta que termina desvaneciéndose")
    a = ap.parse_args()
    if a.video: video(a.video, a.cols, a.filas, a.segundos); print(f"{a.video} listo")
    else: terminal(a.una_vuelta)
