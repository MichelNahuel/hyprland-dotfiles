#!/usr/bin/env python3
"""Genera el logo animado de fastfetch: una N de andamio que se invierte de abajo
hacia arriba.

La letra se arma con | / \\ _ ▔ :

    _____        ___
    |/|\\\\\\       |/|
    |\\| \\\\\\      |\\|
    |/|  \\\\\\     |/|
    |\\|   \\\\\\    |\\|
    |/|    \\\\\\   |/|
    |\\|     \\\\\\  |\\|
    |/|      \\\\\\ |/|
    |\\|       \\\\\\|\\|
    ▔▔▔        ▔▔▔▔▔

- Trazos verticales tipo andamio: |/| y |\\| alternados fila por fila.
- Diagonal de tres caracteres que baja de izquierda a derecha.
- Remates fijos: "_" arriba (se dibuja al pie de su celda) y "▔" abajo (se dibuja
  en lo alto de la suya), así el marco queda cerrado contra el cuerpo.

La onda sube fila por fila invirtiendo cada / en \\ y viceversa; los remates y los
rieles "|" no cambian. Al llegar arriba la letra quedó espejada (se lee como И) y
la onda siguiente la devuelve a N: el bucle es continuo.

Salida: APNG (transparencia real y bordes suaves). kitty lo reproduce en bucle,
sin bloquear el shell, y fastfetch lo muestra con --logo-type kitty-icat.

Colores: de ~/.cache/fastfetch/logo-n-colores (lo escribe matugen con cada
wallpaper); si no existe, de la paleta de kitty; si tampoco, valores fijos.

Uso: python3 logo-n.py [--salida RUTA] [--ancho-celda PX] [--alto-celda PX] [--gif]
"""

import argparse
import os
import re
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

HOME = os.path.expanduser("~")
COLORES_MATUGEN = os.path.join(HOME, ".cache/fastfetch/logo-n-colores")
COLORES_KITTY = os.path.join(HOME, ".config/kitty/colors-matugen.conf")
SALIDA = os.path.join(HOME, ".cache/fastfetch/logo-n.png")

# Celda de texto de kitty: 12 x 27 px con font_size 10 (se usa el doble por nitidez)
ANCHO_CELDA = 24
ALTO_CELDA = 54

COLS, FILAS = 16, 10            # 8 filas de cuerpo + 2 de remates
ANDAMIO = 3                     # ancho de cada trazo vertical
TAPA_LARGA = 5                  # remate que cierra andamio + esquina de la diagonal
ESPEJO = {"/": "\\", "\\": "/"}  # "|", "_" y "▔" no se invierten

MS_PASO = 100                   # cada paso de la onda (una fila)
MS_PAUSA = 800                  # pausa con la letra quieta entre ondas


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
def arte():
    """La N de andamio en una grilla de COLS x FILAS."""
    g = [[" "] * COLS for _ in range(FILAS)]

    # remates (fijos: no se invierten)
    for c in range(0, TAPA_LARGA):
        g[0][c] = "_"
    for c in range(COLS - ANDAMIO, COLS):
        g[0][c] = "_"
    for c in range(0, ANDAMIO):
        g[FILAS - 1][c] = "▔"
    for c in range(COLS - TAPA_LARGA, COLS):
        g[FILAS - 1][c] = "▔"

    # cuerpo: andamios a los costados y diagonal bajando
    for r in range(1, FILAS - 1):
        i = r - 1
        interno = "/" if i % 2 == 0 else "\\"
        g[r][0], g[r][1], g[r][2] = "|", interno, "|"
        g[r][COLS - 3], g[r][COLS - 2], g[r][COLS - 1] = "|", interno, "|"
        for c in range(ANDAMIO + i, ANDAMIO + i + 3):
            g[r][c] = "\\"
    return g


def espejar_fila(g, r):
    g[r] = [ESPEJO.get(ch, ch) for ch in g[r]]


def cuadros(g):
    """[(grilla, fila_del_frente, ms)]: N -> И -> N."""
    salida = [([list(f) for f in g], None, MS_PAUSA)]
    for _ in range(2):
        for r in range(FILAS - 1, -1, -1):      # de abajo hacia arriba
            espejar_fila(g, r)
            salida.append(([list(f) for f in g], r, MS_PASO))
        salida.append(([list(f) for f in g], None, MS_PAUSA))
    return salida


def dibujar(g, frente_en, fuente, cw, chh, cuerpo, frente):
    im = Image.new("RGBA", (COLS * cw, FILAS * chh), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    estela = [frente, mezcla(frente, cuerpo, 0.55), mezcla(frente, cuerpo, 0.85)]
    for r, fila in enumerate(g):
        color = cuerpo
        if frente_en is not None and 0 <= r - frente_en < len(estela):
            color = estela[r - frente_en]
        for c, ch in enumerate(fila):
            if ch != " ":
                d.text(((c + 0.5) * cw, (r + 0.5) * chh), ch, font=fuente,
                       fill=color + (255,), anchor="mm")
    return im


def a_paleta(im):
    """RGBA -> cuadro GIF con un índice reservado para la transparencia."""
    alpha = im.getchannel("A")
    rgb = Image.new("RGB", im.size, (0, 0, 0))
    rgb.paste(im, mask=alpha)
    q = rgb.quantize(colors=255)
    q.paste(255, mask=alpha.point(lambda a: 255 if a < 90 else 0))
    return q


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default=SALIDA, help="ruta del APNG de salida")
    ap.add_argument("--ancho-celda", type=int, default=ANCHO_CELDA)
    ap.add_argument("--alto-celda", type=int, default=ALTO_CELDA)
    ap.add_argument("--gif", action="store_true",
                    help="además, escribir un .gif (paleta de 256 colores, bordes duros)")
    args = ap.parse_args()

    hex_cuerpo, hex_frente = colores()
    cuerpo, frente = a_rgb(hex_cuerpo), a_rgb(hex_frente)
    fuente = ImageFont.truetype(ruta_fuente(), int(args.alto_celda * 0.82))

    imgs, tiempos = [], []
    for g, frente_en, ms in cuadros(arte()):
        imgs.append(dibujar(g, frente_en, fuente, args.ancho_celda, args.alto_celda, cuerpo, frente))
        tiempos.append(ms)

    os.makedirs(os.path.dirname(args.salida) or ".", exist_ok=True)
    imgs[0].save(args.salida, save_all=True, append_images=imgs[1:], duration=tiempos,
                 loop=0, disposal=1)
    print(f"{args.salida}: APNG, {len(imgs)} cuadros, {imgs[0].width}x{imgs[0].height}px "
          f"({COLS}x{FILAS} celdas), cuerpo {hex_cuerpo}, frente {hex_frente}")

    if args.gif:
        ruta_gif = os.path.splitext(args.salida)[0] + ".gif"
        gif = [a_paleta(im) for im in imgs]
        gif[0].save(ruta_gif, save_all=True, append_images=gif[1:], duration=tiempos,
                    loop=0, transparency=255, disposal=2, optimize=False)
        print(f"{ruta_gif}: GIF de respaldo")


if __name__ == "__main__":
    sys.exit(main())
