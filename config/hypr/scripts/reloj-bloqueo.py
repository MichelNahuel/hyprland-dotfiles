#!/usr/bin/env python3
"""Hora de la pantalla de bloqueo con los dígitos de "andamio" del salvapantallas y de la N.

hyprlock la pide cada segundo (label con cmd[update:1000]). Imprime siete renglones; los dos
puntos giran por las cuatro esquinas como los de la consola.
    reloj-bloqueo.py          → la hora
    reloj-bloqueo.py fecha    → "DOM · 13/09" en español
"""
import sys, time

SEGMENTOS = {"0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc",
             "5": "afgcd", "6": "afgecd", "7": "abc", "8": "abcdefg", "9": "abcdfg"}
GIRO = "▖▘▝▗"

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

def hora():
    ahora = time.localtime()
    punto = GIRO[ahora.tm_sec % 4]
    piezas = [digito(c) if c != ":" else [[" "] * 3 if r not in (2, 4) else [" ", punto, " "] for r in range(7)]
              for c in time.strftime("%H:%M", ahora)]
    return "\n".join(" ".join("".join(p[r]) for p in piezas) for r in range(7))

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
