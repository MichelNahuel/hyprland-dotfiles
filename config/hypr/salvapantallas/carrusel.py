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
SEG_QUIETO = 9              # tiempo que queda cada personaje
FILAS_RETRATO = 80
ANCHO_DESCRIPCION = 90        # letras por renglón de la descripción (en letra grande)
CICLO = ("/", "-", "\\")    # lo que muestra una fila mientras la cruzan las olas
CELESTE, CREMA, GRIS = mapa.CELESTE, mapa.CREMA, mapa.LIMITE
TEXTO = (196, 189, 174)       # fechas y descripción: más claro que GRIS para que se lea

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
        return self._cache[prov]

# ------------------------------------------------------------------ barrido
def barrido(viejo, nuevo):
    """Cuadros de la salva de 4 olas que convierte `viejo` en `nuevo`, fila por fila desde abajo."""
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
                cuadro.append([(g, col) if (a[0] != " " or b[0] != " ") else (" ", None)
                               for a, b in zip(viejo[r], nuevo[r])])
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
                unidades += [(y, x, k) for k, letra in enumerate(ch) if letra != " "]
            else:
                unidades.append((y, x, None))
    azar.shuffle(unidades)
    vacio = [[(" ", None) if ch != "" else ("", None) for ch, _ in fila] for fila in final]
    for y, fila in enumerate(final):                  # los renglones grandes arrancan en blanco
        for x, (ch, col) in enumerate(fila):
            if len(ch) > 1: vacio[y][x] = (" " * len(ch), col)
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
            if len(ch) > 1: vacio[y][x] = (" " * len(ch), col)
    yield from reversed(cuadros[:-1])
    yield vacio

# ------------------------------------------------------------------ secuencia
def secuencia(cols, filas, una_vuelta=False):
    """Genera (celdas, milisegundos) sin fin: quieto → barrido → siguiente."""
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
    # al arrancar, el primer personaje y el mapa aparecen de a caracteres al azar
    for cuadro in aparicion(unir(m.con(orden[0]), paneles[orden[0]])):
        yield cuadro, MS_PASO
    i = 0
    while True:
        prov, sig = orden[i % len(orden)], orden[(i + 1) % len(orden)]
        yield unir(m.con(prov), paneles[prov]), SEG_QUIETO * 1000
        if una_vuelta and i == len(orden) - 1:
            # fin de la vuelta (el pingüino): se desvanece de a caracteres al azar y termina
            for cuadro in desaparicion(unir(m.con(prov), paneles[prov])):
                yield cuadro, MS_PASO
            return
        for cuadro in barrido(paneles[prov], paneles[sig]):
            yield unir(m.con(sig), cuadro), MS_PASO
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
            out.append(f"\x1b]66;s={mapa.ESCALA_TEXTO};{ch}\x1b\\")
            absorber = mapa.ESCALA_TEXTO * len(ch) - 1
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
    def esperar(ms):
        """Duerme `ms` milisegundos, pero corta si llega una tecla o un movimiento del mouse."""
        fin = time.time() + ms / 1000
        while True:
            falta = fin - time.time()
            if falta <= 0: return False
            listo, _, _ = select.select([ent], [], [], falta)
            if not listo: return False
            datos = os.read(ent, 4096)
            if time.time() - arranque > GRACIA_ENTRADA: return True
            # el primer segundo se descarta: al abrir la ventana llega un movimiento "fantasma"
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
                absorber = mapa.ESCALA_TEXTO * len(ch) - 1
        return False
    for celdas, ms in secuencia(cols, filas, una_vuelta):
        if previo is None or ms >= 1000:
            # al quedar quieto se repinta todo desde cero: no sobrevive ningún resto del barrido
            cambiadas = set(range(len(celdas)))
            partes = ["\x1b[2J"]
        else:
            cambiadas = {y for y, fila in enumerate(celdas) if previo[y] != fila}
            # la letra grande ocupa dos filas: si cambia la de abajo, se repinta también la de arriba
            cambiadas |= {y - 1 for y in cambiadas if y > 0 and (mitad_baja(celdas[y]) or mitad_baja(previo[y]))}
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
    fuentes = {e: ImageFont.truetype(mapa.ruta_fuente(), int(ch * 0.82 * e)) for e in (1, mapa.ESCALA_TEXTO)}
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
    for celdas, ms in secuencia(cols, filas):
        img = Image.new("RGB", (W, H), (14, 16, 20))
        for y, fila in enumerate(celdas):
            for x, (c, col) in enumerate(fila):
                if not col or c in (" ", ""): continue
                if len(c) > 1:
                    for k, letra in enumerate(c):
                        g = glifo(letra, col, mapa.ESCALA_TEXTO)
                        img.paste(g, ((x + k * mapa.ESCALA_TEXTO) * cw, y * ch), g)
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
