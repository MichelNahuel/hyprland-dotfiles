#!/usr/bin/env python3
"""verificar.py <grub.cfg de referencia> <grub.cfg nuevo> [--sin-orden]

Comprueba que el grub.cfg nuevo tiene exactamente las mismas entradas que el de referencia
(generado con la configuración original), línea por línea, con solo estas diferencias:
  - orden: si hay Windows, pasa a ser la segunda entrada (la primera sigue siendo Linux)
  - nombre visible: "Windows Boot Manager (on /dev/…)" → "Windows 11"
Además, que la entrada por defecto no cambie, que la cuenta sea de 10 s y que el tema se cargue.
Con --sin-orden, las entradas tienen que quedar en el mismo orden y con el mismo nombre.
Sale con 1 ante cualquier diferencia inesperada."""
import difflib, re, sys

def bloques(texto):
    """Entradas de primer nivel (menuentry/submenu con todo su cuerpo), en orden."""
    lineas, out, i = texto.splitlines(), [], 0
    while i < len(lineas):
        if re.match(r"^(menuentry|submenu) ", lineas[i]):
            prof, cuerpo = 0, []
            while True:
                l = lineas[i]; cuerpo.append(l)
                prof += l.count("{") - l.count("}")
                i += 1
                if prof == 0: break
                if i >= len(lineas): sys.exit("llave sin cerrar en " + cuerpo[0])
            out.append(cuerpo)
        else:
            i += 1
    return out

def fuera_de_entradas(texto):
    out, prof = [], 0
    for l in texto.splitlines():
        if prof > 0 or re.match(r"^(menuentry|submenu) ", l):
            prof += l.count("{") - l.count("}")
            continue
        out.append(l)
    return out

titulo = lambda b: re.match(r"^\S+ '([^']*)'", b[0]).group(1)
WIN = re.compile(r"^menuentry 'Windows Boot Manager \(on [^']*\)'")

args = [a for a in sys.argv[1:] if not a.startswith("--")]
con_orden = "--sin-orden" not in sys.argv
if len(args) != 2: sys.exit(__doc__)
base, nuevo = (open(p).read() for p in args)
bb, bn = bloques(base), bloques(nuevo)
errores = []
print("referencia:", [titulo(b) for b in bb])
print("nuevo:     ", [titulo(b) for b in bn])

# 1) entradas esperadas, en orden
esperado = [list(b) for b in bb]
if con_orden:
    win = [k for k, b in enumerate(esperado) if WIN.match(b[0])]
    if len(win) == 1 and win[0] > 1:
        b = esperado.pop(win[0])
        b[0] = WIN.sub("menuentry 'Windows 11'", b[0])
        esperado.insert(1, b)
if ["\n".join(b) for b in esperado] != ["\n".join(b) for b in bn]:
    errores.append("las entradas no coinciden con las de referencia (contenido, nombre u orden)")
if not bb:
    errores.append("la referencia no tiene entradas")

# 2) la entrada por defecto no cambia
por_defecto = lambda t: re.findall(r'^\s*set default="([^"]*)"', t, re.M)
if por_defecto(base) != por_defecto(nuevo):
    errores.append(f"cambió la entrada por defecto: {por_defecto(base)} → {por_defecto(nuevo)}")

# 3) cuenta de 10 s y tema
if not re.search(r"^\s*set timeout=10$", nuevo, re.M):
    errores.append("no encontré set timeout=10")
if not re.search(r"^\s*set theme=.*/themes/nm/theme\.txt$", nuevo, re.M):
    errores.append("no encontré set theme=…/themes/nm/theme.txt")

# 4) lo que no son entradas: se muestra para revisarlo a mano
d = list(difflib.unified_diff(fuera_de_entradas(base), fuera_de_entradas(nuevo), "referencia", "nuevo", lineterm="", n=0))
print("\n--- cambios fuera de las entradas (encabezado, tema, cuenta) ---")
print("\n".join(d) if d else "(ninguno)")
print()
if errores:
    for e in errores: print("ERROR:", e)
    sys.exit(1)
hay_windows = any(WIN.match(b[0]) for b in bb)
print("VERIFICACIÓN OK: mismas entradas" + (", Linux primero y Windows segundo" if con_orden and hay_windows else ", mismo orden") +
      ", misma entrada por defecto, 10 s, tema cargado")
