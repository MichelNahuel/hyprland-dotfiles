#!/usr/bin/env python3
"""Genera las piezas animadas de la consola: la N, la M y el punto que gira.

Las letras se arman con | / \\ _ ▔ y las recorren salvas de cuatro olas que suben
de abajo hacia arriba:

    _____        ___          _____      _____
    |/|\\\\\\       |/|          |/|\\\\\\    ///|/|
    |\\| \\\\\\      |\\|          |\\| \\\\\\  /// |\\|
    |/|  \\\\\\     |/|          |/|  \\\\\\///  |/|
    |\\|   \\\\\\    |\\|          |\\|   \\\\//   |\\|
    |/|    \\\\\\   |/|          |/|          |/|
    |\\|     \\\\\\  |\\|          |\\|          |\\|
    |/|      \\\\\\ |/|          |/|          |/|
    |\\|       \\\\\\|\\|          |\\|          |\\|
    ▔▔▔        ▔▔▔▔▔          ▔▔▔          ▔▔▔

Cada ola que pasa por una fila la hace avanzar una fase, y cada carácter sigue su
propio ciclo según lo que era originalmente:

    rieles      |  ->  /  ->  -  ->  \\  ->  |     (vuelta completa en 4 olas)
    andamio     /  ->  \\  ->  /  ->  \\        (y al revés si nació \\)
    diagonal    \\  ->  /  ->  \\  ->  /
    remates     _  ->  -  ->  _  ->  -        (lo mismo el ▔ de abajo)

La fase se lleva por celda según su papel y no transformando el carácter que se
ve: un | que pasó a / debe seguir a -, mientras que un / que nació / pasa a \\.

El punto es aparte: un cuadrado que salta entre las cuatro esquinas (▖ ▘ ▝ ▗), con
su propio ritmo. Al ser una imagen separada, kitty lo anima con su propio reloj y
su giro no depende del de las letras. El carácter se dibuja estirado a un lienzo
cuadrado, porque la celda de texto es el doble de alta que ancha y, si no, cada
cuadrante se vería como una barra angosta en vez de un cuadrado.

Salida: APNG (transparencia real y bordes suaves), que kitty reproduce en bucle
sin bloquear el shell.

Colores: de ~/.cache/fastfetch/logo-n-colores (lo escribe matugen con cada
wallpaper); si no existe, de la paleta de kitty; si tampoco, valores fijos.

Uso: python3 logo-n.py [--salida RUTA] [--salida-m RUTA] [--salida-punto RUTA]
                       [--ancho-celda PX] [--alto-celda PX] [--gif]
"""

import argparse
import math
import os
import re
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

HOME = os.path.expanduser("~")
COLORES_MATUGEN = os.path.join(HOME, ".cache/fastfetch/logo-n-colores")
COLORES_KITTY = os.path.join(HOME, ".config/kitty/colors-matugen.conf")
SALIDA = os.path.join(HOME, ".cache/fastfetch/logo-n.png")
SALIDA_M = os.path.join(HOME, ".cache/fastfetch/logo-m.png")
SALIDA_PUNTO = os.path.join(HOME, ".cache/fastfetch/punto.png")
SALIDA_BANDERA = os.path.join(HOME, ".cache/fastfetch/bandera.png")

# Celda de texto de kitty: 8 x 19 px con font_size 7 (se usa el doble por nitidez).
# Si cambia font_size, hay que rehacer estos valores: la imagen debe tener la misma
# proporción que la grilla de celdas o el logo deja de encajar en su caja.
# Medidas conocidas: 7 -> 8x19 | 7.5 -> 9x20 | 8 -> 10x22 | 9 -> 11x24 | 10 -> 12x27
ANCHO_CELDA = 16
ALTO_CELDA = 38

COLS, FILAS = 16, 10            # 8 filas de cuerpo + 2 de remates
ANDAMIO = 3                     # ancho de cada trazo vertical
TAPA_LARGA = 5                  # remate que cierra andamio + esquina de la diagonal
HONDURA_V = 4                   # filas que baja la V de la M
FASES = 4                       # largo del ciclo de cada carácter
OLAS = FASES                    # olas por salva: así cada fila da la vuelta completa

MS_PASO = 110                   # cada paso de la salva (avanza una fila)
MS_CIERRE = 700                 # la letra entera, entre una salva y la siguiente

CICLO_PUNTO = "▖▘▝▗"            # el cuadrado recorriendo las esquinas
PUNTO_LADO = 76                 # lienzo cuadrado del punto, en píxeles
PUNTO_MS = 180                  # ritmo propio, independiente del de las letras

# Ciclos de 4 fases por papel de cada celda
CICLO_RIEL = ("|", "/", "-", "\\")
CICLO_TAPA_ALTA = ("_", "-", "_", "-")
CICLO_TAPA_BAJA = ("▔", "-", "▔", "-")

# La bandera argentina, a la derecha del todo. Hecha con caracteres como el resto
# de la consola: caracteres de línea para la tela y, para el sol, los mismos
# trazos que arman la N y la M (\ | / -), de modo que hable el mismo idioma.
# Los colores son los de la bandera: no los toca matugen.
BANDERA_COLS, BANDERA_FILAS = 40, 10
BANDERA_CELESTE = (116, 172, 223)
BANDERA_BLANCO = (240, 244, 248)
BANDERA_SOL = (246, 180, 14)
TELA_CELESTE, TELA_BLANCA = "═", "─"
SOL_ARTE = ("\\|/",
            "-O-",
            "/|\\")
SOL_FILA = 3
BANDERA_CUADROS, BANDERA_MS = 14, 95
BANDERA_AMP = 0.42              # amplitud de la onda, en alto de celda
BANDERA_LARGO = 17              # largo de onda, en celdas (absoluto: al ensanchar la
                                # bandera aparecen más ondas en vez de estirarse)


def ciclo_barra(base):
    """/ y \\ solo se invierten: vuelven a su lugar cada dos olas."""
    otro = "\\" if base == "/" else "/"
    return (base, otro, base, otro)


# --------------------------------------------------------------------- colores
def colores():
    """(cuerpo, frente) como #rrggbb."""
    try:
        with open(COLORES_MATUGEN, encoding="utf-8") as fh:
            valores = [l.strip() for l in fh if l.strip().startswith("#")]
        if len(valores) >= 2:
            return valores[0], valores[1]
    except OSError:
        pass
    return (_de_kitty("color4", "#a1d399"), _de_kitty("foreground", "#e0e4db"))


def _de_kitty(clave, por_defecto):
    try:
        with open(COLORES_KITTY, encoding="utf-8") as fh:
            for linea in fh:
                m = re.match(rf"^\s*{re.escape(clave)}\s+(#[0-9a-fA-F]{{6}})\s*$", linea)
                if m:
                    return m.group(1)
    except OSError:
        pass
    return por_defecto


def a_rgb(hexa):
    hexa = hexa.lstrip("#")
    return tuple(int(hexa[i:i + 2], 16) for i in (0, 2, 4))


def mezcla(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def ruta_fuente():
    for consulta in ("JetBrainsMono Nerd Font Mono:style=Regular",
                     "JetBrainsMono Nerd Font:style=Regular",
                     "monospace"):
        try:
            ruta = subprocess.run(["fc-match", "-f", "%{file}", consulta],
                                  capture_output=True, text=True, check=True).stdout.strip()
            if ruta and os.path.exists(ruta):
                return ruta
        except (OSError, subprocess.CalledProcessError):
            continue
    raise SystemExit("No encontré una fuente monoespaciada")


# ------------------------------------------------------------------------ arte
def _andamios(g):
    """Rieles de andamio a los costados y remates arriba y abajo."""
    for c in range(0, TAPA_LARGA):
        g[0][c] = CICLO_TAPA_ALTA
    for c in range(COLS - ANDAMIO, COLS):
        g[0][c] = CICLO_TAPA_ALTA
    for c in range(0, ANDAMIO):
        g[FILAS - 1][c] = CICLO_TAPA_BAJA
    for c in range(COLS - TAPA_LARGA, COLS):
        g[FILAS - 1][c] = CICLO_TAPA_BAJA
    for r in range(1, FILAS - 1):
        i = r - 1
        interno = ciclo_barra("/" if i % 2 == 0 else "\\")
        g[r][0], g[r][1], g[r][2] = CICLO_RIEL, interno, CICLO_RIEL
        g[r][COLS - 3], g[r][COLS - 2], g[r][COLS - 1] = CICLO_RIEL, interno, CICLO_RIEL


def arte():
    """La N: andamios + diagonal bajando de izquierda a derecha."""
    g = [[None] * COLS for _ in range(FILAS)]
    _andamios(g)
    for r in range(1, FILAS - 1):
        i = r - 1
        for c in range(ANDAMIO + i, ANDAMIO + i + 3):
            g[r][c] = ciclo_barra("\\")
    return g


def arte_m():
    """La M: andamios + la V del medio, con el cruce repartido por la mitad."""
    g = [[None] * COLS for _ in range(FILAS)]
    _andamios(g)
    # En la M las dos diagonales arrancan arriba y ninguna llega abajo: remates
    # largos (5) en las dos esquinas de arriba y cortos (3) en las de abajo.
    for c in range(COLS - TAPA_LARGA, COLS):
        g[0][c] = CICLO_TAPA_ALTA
    for c in range(COLS - TAPA_LARGA, COLS - ANDAMIO):
        g[FILAS - 1][c] = None
    medio = (COLS - 1) // 2
    for r in range(1, FILAS - 1):
        i = r - 1
        if i >= HONDURA_V:
            continue
        for c in range(ANDAMIO + i, ANDAMIO + i + 3):
            if c <= medio:
                g[r][c] = ciclo_barra("\\")
        for c in range(COLS - 6 - i, COLS - 3 - i):
            if c > medio:
                g[r][c] = ciclo_barra("/")
    return g


def cuadros():
    """[(fases_por_fila, {fila: nº de ola}, ms)] de una salva de OLAS olas."""
    fases = [0] * FILAS
    salida = []
    for t in range(FILAS + OLAS - 1):
        frentes = {}
        for k in range(OLAS):
            avance = t - k
            if avance < 0:
                continue                      # esta ola todavía no salió
            r = FILAS - 1 - avance
            if 0 <= r < FILAS:
                fases[r] += 1
                frentes[r] = k
        salida.append((list(fases), frentes, MS_PASO))
    salida.append((list(fases), {}, MS_CIERRE))   # la letra entera antes de la próxima salva
    return salida


def texto(g, fases):
    """La grilla como líneas de texto (para verificar el dibujo)."""
    return ["".join(celda[fases[r] % FASES] if celda else " " for celda in fila)
            for r, fila in enumerate(g)]


def dibujar(g, fases, frentes, fuente, cw, chh, cuerpo, frente):
    # fastfetch/icat colocan la imagen unos píxeles más abajo de lo que corresponde:
    # con font_size 9 sobraban 7 px y con 7 sobraban 8, o sea casi lo mismo en píxeles
    # de pantalla. Este margen transparente al pie hace que la imagen se escale un
    # poco más chica y su base suba, quedando a ras de la última línea de datos.
    PIE = 16
    im = Image.new("RGBA", (COLS * cw, FILAS * chh + PIE), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for r, fila in enumerate(g):
        color = cuerpo
        if r in frentes:                       # la ola de adelante, la más clara
            color = mezcla(frente, cuerpo, frentes[r] / OLAS)
        for c, celda in enumerate(fila):
            if celda is None:
                continue
            d.text(((c + 0.5) * cw, (r + 0.5) * chh), celda[fases[r] % FASES],
                   font=fuente, fill=color + (255,), anchor="mm")
    return im


def cuadros_punto(cuerpo, ruta_tipografia):
    """El cuadrado saltando entre esquinas, en un lienzo cuadrado.

    Lleva un margen transparente al pie para que el piso del salto quede al mismo
    nivel que el ▔ de las letras: la imagen de las letras también tiene margen
    abajo, así que su tinta termina más arriba que su caja, y como la colocación
    va por celdas enteras esto es lo que permite ajustar los píxeles que faltan.
    """
    PIE_PUNTO = 14
    fuente = ImageFont.truetype(ruta_tipografia, 120)
    asc, desc = fuente.getmetrics()
    ancho_celda, alto_celda = int(fuente.getlength("█")), asc + desc
    salida = []
    for ch in CICLO_PUNTO:
        celda = Image.new("RGBA", (ancho_celda, alto_celda), (0, 0, 0, 0))
        ImageDraw.Draw(celda).text((0, 0), ch, font=fuente, fill=cuerpo + (255,), anchor="la")
        # se estira la celda a un cuadrado: si no, cada cuadrante sería una barra
        cuadrado = celda.resize((PUNTO_LADO, PUNTO_LADO), Image.LANCZOS)
        lienzo = Image.new("RGBA", (PUNTO_LADO, PUNTO_LADO + PIE_PUNTO), (0, 0, 0, 0))
        lienzo.paste(cuadrado, (0, 0), cuadrado)
        salida.append(lienzo)
    return salida


def cuadros_bandera(fuente, cw, chh):
    """La bandera flameando: cada columna sube y baja siguiendo una onda viajera.

    La onda desplaza la columna entera, que es como ondula una tela de verdad, y
    el sombreado (más claro en las crestas) le da volumen. El sol viaja con la
    tela porque su desplazamiento sale de la misma onda que el resto.
    """
    PIE = 16                                   # mismo margen al pie que las letras
    amp, largo = chh * BANDERA_AMP, BANDERA_LARGO
    sol_col = (BANDERA_COLS - 3) // 2
    salida = []
    for k in range(BANDERA_CUADROS):
        fase = 2 * math.pi * k / BANDERA_CUADROS
        im = Image.new("RGBA", (BANDERA_COLS * cw, BANDERA_FILAS * chh + PIE), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        for c in range(BANDERA_COLS):
            ang = 2 * math.pi * (c / largo) + fase
            desp = amp * math.sin(ang)
            luz = 1 + 0.16 * math.cos(ang)
            for r in range(BANDERA_FILAS):
                if r < 3 or r >= BANDERA_FILAS - 3:
                    color, ch = BANDERA_CELESTE, TELA_CELESTE
                else:
                    color, ch = BANDERA_BLANCO, TELA_BLANCA
                sr, sc = r - SOL_FILA, c - sol_col
                if 0 <= sr < 3 and 0 <= sc < 3:
                    ch, color = SOL_ARTE[sr][sc], BANDERA_SOL
                tinta = tuple(max(0, min(255, round(v * luz))) for v in color)
                d.text(((c + .5) * cw, (r + .5) * chh + desp), ch, font=fuente,
                       fill=tinta + (255,), anchor="mm")
        salida.append(im)
    return salida


def a_paleta(im):
    """RGBA -> cuadro GIF con un índice reservado para la transparencia."""
    alpha = im.getchannel("A")
    rgb = Image.new("RGB", im.size, (0, 0, 0))
    rgb.paste(im, mask=alpha)
    q = rgb.quantize(colors=255)
    q.paste(255, mask=alpha.point(lambda a: 255 if a < 90 else 0))
    return q


def escribir_apng(ruta, imgs, tiempos, disposal=1):
    os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
    imgs[0].save(ruta, save_all=True, append_images=imgs[1:], duration=tiempos,
                 loop=0, disposal=disposal)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default=SALIDA, help="APNG de la N")
    ap.add_argument("--salida-m", default=SALIDA_M, help="APNG de la M")
    ap.add_argument("--salida-punto", default=SALIDA_PUNTO, help="APNG del punto que gira")
    ap.add_argument("--salida-bandera", default=SALIDA_BANDERA,
                    help="APNG de la bandera argentina flameando")
    ap.add_argument("--ancho-celda", type=int, default=ANCHO_CELDA)
    ap.add_argument("--alto-celda", type=int, default=ALTO_CELDA)
    ap.add_argument("--gif", action="store_true",
                    help="además, escribir un .gif de la N (paleta de 256 colores)")
    ap.add_argument("--barra", default=os.path.join(HOME, ".config/waybar/assets/logo-n.png"),
                    help="PNG fijo de la N para la barra superior (vacío para no escribirlo)")
    args = ap.parse_args()

    hex_cuerpo, hex_frente = colores()
    cuerpo, frente = a_rgb(hex_cuerpo), a_rgb(hex_frente)
    tipografia = ruta_fuente()
    fuente = ImageFont.truetype(tipografia, int(args.alto_celda * 0.82))
    secuencia = cuadros()
    tiempos = [ms for _, _, ms in secuencia]

    for ruta, grilla, nombre in ((args.salida, arte(), "N"), (args.salida_m, arte_m(), "M")):
        if not ruta:
            continue
        imgs = [dibujar(grilla, fases, frentes, fuente, args.ancho_celda, args.alto_celda,
                        cuerpo, frente)
                for fases, frentes, _ in secuencia]
        escribir_apng(ruta, imgs, tiempos)
        print(f"{ruta}: APNG {nombre}, {len(imgs)} cuadros, {imgs[0].width}x{imgs[0].height}px "
              f"({COLS}x{FILAS} celdas), salva de {OLAS} olas, cuerpo {hex_cuerpo}, frente {hex_frente}")

    if args.salida_punto:
        # disposal=2 (borrar antes del próximo cuadro): sin eso los cuadrados se acumulan
        puntos = cuadros_punto(cuerpo, tipografia)
        escribir_apng(args.salida_punto, puntos, [PUNTO_MS] * len(puntos), disposal=2)
        print(f"{args.salida_punto}: APNG punto, {len(puntos)} cuadros de {PUNTO_MS}ms, "
              f"{PUNTO_LADO}x{PUNTO_LADO}px (ritmo propio)")

    if args.salida_bandera:
        banderas = cuadros_bandera(fuente, args.ancho_celda, args.alto_celda)
        escribir_apng(args.salida_bandera, banderas, [BANDERA_MS] * len(banderas), disposal=2)
        print(f"{args.salida_bandera}: APNG bandera, {len(banderas)} cuadros de {BANDERA_MS}ms, "
              f"{banderas[0].width}x{banderas[0].height}px ({BANDERA_COLS}x{BANDERA_FILAS} celdas)")

    # La N quieta y blanca para la barra superior (Waybar no anima imágenes en CSS).
    COLOR_BARRA = "#ffffff"
    if args.barra:
        tinta = a_rgb(COLOR_BARRA)
        quieto = dibujar(arte(), [0] * FILAS, {}, fuente, args.ancho_celda, args.alto_celda,
                         tinta, tinta)
        os.makedirs(os.path.dirname(args.barra) or ".", exist_ok=True)
        quieto.save(args.barra)
        print(f"{args.barra}: PNG fijo para la barra")

    if args.gif:
        ruta_gif = os.path.splitext(args.salida)[0] + ".gif"
        imgs = [dibujar(arte(), f, fr, fuente, args.ancho_celda, args.alto_celda, cuerpo, frente)
                for f, fr, _ in secuencia]
        gif = [a_paleta(im) for im in imgs]
        gif[0].save(ruta_gif, save_all=True, append_images=gif[1:], duration=tiempos,
                    loop=0, transparency=255, disposal=2, optimize=False)
        print(f"{ruta_gif}: GIF de respaldo")


if __name__ == "__main__":
    sys.exit(main())
