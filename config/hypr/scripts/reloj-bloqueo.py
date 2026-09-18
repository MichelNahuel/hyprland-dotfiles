#!/usr/bin/env python3
"""Hora de la pantalla de bloqueo con los dígitos de "andamio" del salvapantallas y de la N.

hyprlock la pide cada segundo (label con cmd[update:1000]). Imprime nueve renglones; los dos
puntos giran por las cuatro esquinas como los de la consola.
    reloj-bloqueo.py          → la hora
    reloj-bloqueo.py fecha    → "DOM · 13/09" en español
"""
import sys, time

SEGMENTOS = {"0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc",
             "5": "afgcd", "6": "afgecd", "7": "abc", "8": "abcdefg", "9": "abcdfg"}
GIRO = "▖▘▝▗"
BANDA = 2                          # renglones de andamio de las franjas de arriba y de abajo
ALTO = 2 * BANDA + 5               # techo _, cuerpo (2*BANDA + 3) y piso ▔

def digito(d):
    """Dígito de 9 columnas: las franjas horizontales son andamio (|/| repetido), y solo el
    cierre de arriba y de abajo usa _ y ▔, como en la N de la consola."""
    seg = SEGMENTOS[d]
    g = [[" "] * 9 for _ in range(ALTO)]
    unidad = lambda r, c: g[r].__setitem__(slice(c, c + 3), ["|", "/" if r % 2 else "\\", "|"])
    medio = 1 + BANDA + 1
    franja_a, franja_d = range(1, 1 + BANDA), range(ALTO - 1 - BANDA, ALTO - 1)
    if "a" in seg:
        for r in franja_a: [unidad(r, c) for c in (0, 3, 6)]
        g[0] = ["_"] * 9
    else:
        if "f" in seg: g[0][0:3] = ["_"] * 3
        if "b" in seg: g[0][6:9] = ["_"] * 3
    if "d" in seg:
        for r in franja_d: [unidad(r, c) for c in (0, 3, 6)]
        g[ALTO - 1] = ["▔"] * 9
    else:
        if "e" in seg: g[ALTO - 1][0:3] = ["▔"] * 3
        if "c" in seg: g[ALTO - 1][6:9] = ["▔"] * 3
    for r in range(1, ALTO - 1):
        if ("a" in seg and r in franja_a) or ("d" in seg and r in franja_d): continue
        if r == medio: izq, der = "f" in seg or "e" in seg, "b" in seg or "c" in seg
        elif r < medio: izq, der = "f" in seg, "b" in seg
        else: izq, der = "e" in seg, "c" in seg
        if izq: unidad(r, 0)
        if der: unidad(r, 6)
    if "g" in seg: unidad(medio, 3)
    return g

def hora():
    ahora = time.localtime()
    punto = GIRO[ahora.tm_sec % 4]
    piezas = [digito(c) if c != ":" else [[" "] * 3 if r not in (ALTO // 2 - 1, ALTO // 2 + 1) else [" ", punto, " "] for r in range(ALTO)]
              for c in time.strftime("%H:%M", ahora)]
    return "\n".join(" ".join("".join(p[r]) for p in piezas) for r in range(ALTO))

def fecha():
    dias = ["LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB", "DOM"]
    ahora = time.localtime()
    return f"{dias[ahora.tm_wday]}  ·  {time.strftime('%d/%m', ahora)}"

if __name__ == "__main__":
    texto = fecha() if sys.argv[1:] == ["fecha"] else hora()
    # hyprlock interpreta marcado Pango: escapar & < >. Los espacios van como espacio de ancho
    # fijo (U+2007): hyprlock alinea cada renglón por su cuenta y recorta los espacios comunes.
    texto = texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    print(texto.replace(" ", "\u2007"))
