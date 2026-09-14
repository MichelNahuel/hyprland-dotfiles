#!/usr/bin/env python3
"""Genera el tema de GRUB "N.M.": una pantalla que se corrompe un poco más cada segundo.

GRUB no anima nada por sí solo: lo único que se redibuja es cada componente con
id "__timeout__", una vez por segundo. El fondo "vivo" se logra con muchas etiquetas
de volcado de memoria que llevan el contador (%d) en el medio, así cambian cada segundo.

Los datos de la cabecera (placa, CPU, GPU, discos) se leen del equipo donde se genera.

    generar_tema.py tema <carpeta>        → tema (fondo.png, theme.txt, texturas y fuentes .pf2)
    generar_tema.py preview <video.mp4>   → vista previa (simula los 10 segundos; necesita ffmpeg)
    generar_tema.py resolucion            → la resolución para la que se genera

Resolución: GRUB_TEMA_RES=1920x1080 (por defecto, la del panel interno o 1920x1200).
Los componentes van en píxeles absolutos: la resolución tiene que ser la que GRUB use de verdad.
"""
import os, sys, random, subprocess, glob, re, hashlib, tempfile, shutil
from PIL import Image, ImageDraw, ImageFont

def leer(ruta, defecto=""):
    try:
        return open(ruta).read().strip()
    except OSError:
        return defecto

def comando(*args):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""

def resolucion():
    if os.environ.get("GRUB_TEMA_RES"):
        return tuple(int(v) for v in os.environ["GRUB_TEMA_RES"].lower().split("x"))
    for patron in ("/sys/class/drm/card*-eDP-*", "/sys/class/drm/card*-LVDS-*", "/sys/class/drm/card*-*"):
        for con in sorted(glob.glob(patron)):
            if leer(con + "/status") == "connected":
                m = re.match(r"(\d+)x(\d+)", leer(con + "/modes"))
                if m: return int(m[1]), int(m[2])
    return 1920, 1200

def fuente(estilo):
    ruta = comando("fc-match", "-f", "%{file}", f"JetBrainsMono Nerd Font Mono:style={estilo}")
    if not ruta.lower().endswith((".ttf", ".otf")) or "jetbrains" not in ruta.lower():
        sys.exit(f"Falta JetBrainsMono Nerd Font Mono {estilo} (sudo pacman -S ttf-jetbrains-mono-nerd)")
    return ruta

W, H = resolucion()
REG, BOLD = fuente("Regular"), fuente("Bold")

FONDO = (9, 10, 13)
CREMA = (230, 223, 207)
TENUE = (60, 58, 54)
MEDIO = (120, 115, 105)
ROJO = (196, 72, 58)
RUIDO = (26, 27, 31)

f = lambda s, bold=False: ImageFont.truetype(BOLD if bold else REG, s)

# ------------------------------------------------------------ pilares
CAPITEL = [
    "▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄",
    "█▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀█",
    " \\_____________/ ",
    "  |_|_|_|_|_|_|  ",
]
FUSTE = "  |:| |:| |:| |  "
BASA = [
    "  |_|_|_|_|_|_|  ",
    " /_____________\\ ",
    "█▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄█",
    "▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀",
]

def pilar_entero(alto):
    return CAPITEL + [FUSTE] * (alto - len(CAPITEL) - len(BASA)) + BASA

def pilar_roto(alto):
    """El mismo pilar partido: el capitel caído y torcido arriba, el fuste quebrado a un tercio
    con el borde astillado, un hueco en el medio, fisuras y escombros al pie."""
    ancho = len(FUSTE)
    filas = []
    # capitel desplazado, torcido y agrietado (quedó colgando arriba)
    filas += ["    ▄▄▄▄▄▄▄▄▄▄▄▄▄", "   █▀▀▀▀▀▀▀▀▀▀▀▀/ ", "   \\_______ __/  ", "     |_|_/  |_|   "]
    filas += ["                 "] * 2
    filas += ["      .   ,      ", "          `  .   ", "                 "]
    # borde superior astillado del fuste
    filas += [r"        ._       ", r"      ,/:|  .    ", r"    /:| |:|\     ", r"  |:| |:| |:|\.  "]
    cuerpo = alto - len(filas) - len(BASA) - 3
    for i in range(cuerpo):
        linea = FUSTE
        if cuerpo // 3 <= i < cuerpo // 3 + 4:                      # hueco: falta un pedazo
            linea = [r"  |:| |/     | |  ", r"  |:| /       \|  ", r"  |:|  \      /|  ", r"  |:| |:\   /:| |  "][i - cuerpo // 3][:ancho]
        elif i in (2 * cuerpo // 3, 2 * cuerpo // 3 + 1):          # fisura en diagonal
            linea = "  |:| |:/ /:| |  " if i == 2 * cuerpo // 3 else "  |:|/ /|:| |  "
        filas.append(linea.ljust(ancho)[:ancho])
    filas += BASA
    filas += ["  .  ,:  ` ._.  ", " ._/:\\. ,  ::. `", "▀`:.  ▀▄ .:,▀ ._"]   # escombros al pie
    return filas

# ------------------------------------------------------------ datos del equipo
def recortar_texto(t, n=100):
    return t if len(t) <= n else t[:n - 1] + "…"

def equipo():
    """Líneas de la cabecera con el hardware real. Si algo no se puede leer, se omite."""
    dmi = "/sys/class/dmi/id/"
    nombre, version = leer(dmi + "product_name"), leer(dmi + "product_version")
    bios = " ".join(leer(dmi + "bios_version").replace("(", "").replace(")", "").split())
    modelo = version if version and version.lower() not in ("none", "default string", "to be filled by o.e.m.") else ""
    placa = " · ".join(x for x in (modelo or nombre, nombre if modelo else "", f"BIOS {bios}" if bios else "") if x)
    cpuinfo = leer("/proc/cpuinfo")
    cpu = re.search(r"^model name\s*:\s*(.+)$", cpuinfo, re.M)
    cpu = re.sub(r"\s+(\d+-Core|with Radeon.*|Processor)$", "", cpu[1].strip()) if cpu else "desconocida"
    nucleos = re.search(r"^cpu cores\s*:\s*(\d+)", cpuinfo, re.M)
    hilos = os.cpu_count() or 0
    ucode = next((u for u in ("amd-ucode", "intel-ucode") if os.path.exists(f"/boot/{u}.img")), "")
    cpu = " · ".join(x for x in (cpu, f"{nucleos[1]} núcleos / {hilos} hilos" if nucleos else f"{hilos} hilos", ucode) if x)
    gpus = []
    for linea in comando("lspci").splitlines():
        if re.search(r"VGA compatible|Display controller|3D controller", linea):
            corchetes = re.findall(r"\[([^\]]+)\]", linea)
            gpus.append(corchetes[-1] if corchetes else linea.split(": ", 1)[-1])
    drivers = sorted({os.path.basename(os.path.realpath(d)) for d in glob.glob("/sys/class/drm/card[0-9]/device/driver")})
    gpu = " · ".join(x for x in (" + ".join(gpus), " ".join(drivers)) if x) or "desconocida"
    mem = re.search(r"^MemTotal:\s*(\d+)", leer("/proc/meminfo"), re.M)
    swaps = [l.split() for l in leer("/proc/swaps").splitlines()[1:] if l.strip()]
    memoria = f"{round(int(mem[1]) / 2**20)} GiB" if mem else "?"
    if swaps:
        memoria += f" · swap {round(sum(int(s[2]) for s in swaps) / 2**20)} GiB ({', '.join(os.path.basename(s[0]) for s in swaps)})"
    discos = []
    for linea in comando("lsblk", "-dno", "NAME,MODEL,SIZE,TYPE").splitlines():
        partes = linea.split()
        if len(partes) >= 3 and partes[-1] == "disk" and not partes[0].startswith(("zram", "loop")):
            modelo_d = " ".join(partes[1:-2]).replace("_", " ")[:18]
            discos.append(f"{partes[0]} {modelo_d} {partes[-2]}".replace("  ", " "))
    efi_dir = next((d for d in ("/boot/efi", "/efi", "/boot") if os.path.isdir(d + "/EFI")), "")
    efi_dev = os.path.basename(comando("findmnt", "-no", "SOURCE", efi_dir)) if efi_dir else ""
    grub_v = comando("grub-install", "--version").split()[-1:] or [""]
    grub_v = re.sub(r"^\d+:", "", grub_v[0]).split("-")[0]
    windows = bool(efi_dir and glob.glob(efi_dir + "/EFI/[Mm]icrosoft"))
    efi = " · ".join(x for x in (efi_dev or "BIOS", f"GRUB {grub_v}" if grub_v else "GRUB", "Windows Boot Manager" if windows else "") if x)
    lineas = [("PLACA", placa or "desconocida"), ("CPU", cpu), ("GPU", gpu), ("MEMORIA", memoria),
              ("DISCOS", " · ".join(discos) or "?"), ("EFI", efi)]
    return {
        "lineas": [recortar_texto(f"{k:<8}{v}") for k, v in lineas],
        "ref": "0x%s-%s" % (hashlib.sha1((nombre + version).encode()).hexdigest()[:4].upper(),
                           re.sub(r"[^A-Z0-9]", "", (modelo or nombre).upper())[-6:] or "0000"),
        "sistemas": 2 if windows else 1,
        "efi_dev": efi_dev,
    }

EQUIPO = equipo()

# ------------------------------------------------------------ fondo
def volcado(azar, ancho=15):
    return " ".join(f"{azar.randrange(256):02X}" for _ in range(ancho // 3))

def fondo():
    azar = random.Random(1878)
    im = Image.new("RGB", (W, H), FONDO)
    d = ImageDraw.Draw(im)
    chica = f(12)
    # ruido de caracteres en todo el fondo
    signos = "01{}[]<>/\\|:;.,=+-*#%$&@!?~^_ABCDEF0123456789"
    for y in range(0, H, 16):
        linea = "".join(azar.choice(signos) if azar.random() < 0.55 else " " for _ in range(W // 7 + 1))
        d.text((0, y), linea, font=chica, fill=RUIDO)
    # líneas de barrido (scanlines)
    for y in range(0, H, 3):
        d.line([(0, y), (W, y)], fill=(6, 7, 9))
    # pilares: el de la izquierda entero, el de la derecha roto
    pil = f(16)
    alto = (H - 180) // 17
    for k, linea in enumerate(pilar_entero(alto)):
        d.text((70, 110 + k * 17), linea, font=pil, fill=MEDIO)
    for k, linea in enumerate(pilar_roto(alto + 3)):
        d.text((W - 70 - 170, 110 + (k - 3) * 17), linea, font=pil, fill=MEDIO)
    # cabecera recargada
    d.text((300, 40), "N.M. // CARGADOR DE ARRANQUE // NIVEL DE ACCESO: RESTRINGIDO", font=f(18, True), fill=CREMA)
    d.text((300, 66), f"sesión no autorizada · registro activo · no cierre esta ventana · ref {EQUIPO['ref']}",
           font=f(13), fill=MEDIO)
    d.rectangle((300, 92, W - 300, 93), fill=TENUE)
    info = EQUIPO["lineas"]
    for k, t in enumerate(info):
        d.text((300, 104 + k * 19), t, font=f(13), fill=MEDIO)
    # advertencia
    aviso = "▲ ADVERTENCIA: ESTA PANTALLA NO DEBERÍA SER VISIBLE"
    d.text((W - 300, 110), aviso, font=f(15, True), fill=ROJO, anchor="ra")
    d.text((W - 300, 132), "integridad del sector 0x3F: NO VERIFICADA", font=f(13), fill=ROJO, anchor="ra")
    d.text((W - 300, 151), f"se detectaron {EQUIPO['sistemas']} sistema{'s' if EQUIPO['sistemas'] > 1 else ''} · 1 pilar comprometido", font=f(13), fill=MEDIO, anchor="ra")
    # bloques "censurados"
    for (x, y, w) in [(300, 250, 260), (300, 272, 180), (W - 560, 190, 260), (W - 480, 212, 180)]:
        d.rectangle((x, y, x + w, y + 12), fill=(38, 36, 34))
    # marco del panel del menú (el menú en sí lo dibuja GRUB encima)
    mx0, my0, mx1, my1 = int(W * 0.30), MENU[1] - 24, int(W * 0.70), BARRA_Y + 48
    d.rectangle((mx0 - 18, my0 - 18, mx1 + 18, my1 + 18), fill=(12, 13, 16))
    for (x, y) in [(mx0 - 18, my0 - 18), (mx1 + 18, my0 - 18), (mx0 - 18, my1 + 18), (mx1 + 18, my1 + 18)]:
        sx = 1 if x < W / 2 else -1; sy = 1 if y < H / 2 else -1
        d.line([(x, y), (x + 40 * sx, y)], fill=CREMA, width=2)
        d.line([(x, y), (x, y + 40 * sy)], fill=CREMA, width=2)
    d.text((mx0 - 18, my0 - 44), "┌─[ SELECCIÓN DE SISTEMA ]──── canal 0 · sin cifrar", font=f(14), fill=MEDIO)
    # cuenta regresiva: el "└─›" va en el fondo; el número lo pone GRUB (etiquetas solo ASCII)
    x0 = MENU[0]
    d.rectangle(ZONA_CUENTA, fill=(12, 13, 16))
    d.text((x0, CUENTA_TXT + 15), "└─›", font=f(18), fill=CREMA, anchor="lm")
    # ayuda, fija en el fondo
    d.rectangle(ZONA_AYUDA, fill=(9, 10, 13))
    d.text((W / 2, int(H * 0.94) + 15), "↑ ↓  elegir     ·     enter  arrancar     ·     e  editar     ·     c  consola",
           font=f(14), fill=(200, 194, 179), anchor="mm")
    # pie
    d.rectangle((300, H - 110, W - 300, H - 109), fill=TENUE)
    d.text((300, H - 98), f"log: /dev/{EQUIPO['efi_dev'] or 'sda1'} montado · lectura ok · escritura DENEGADA · {EQUIPO['sistemas']} entradas visibles",
           font=f(12), fill=TENUE)
    return im

# ------------------------------------------------------------ etiquetas que cambian cada segundo
def etiquetas_vivas():
    """[(x, y, texto con %d, color)] — volcados de memoria que cambian con el contador."""
    azar = random.Random(7735)
    salida = []
    columnas = [(300, 330), (300, 360), (300, 420), (300, 450), (300, 480), (300, 700), (300, 730), (300, 790),
                (1380, 300), (1380, 330), (1380, 690), (1380, 720), (1380, 780), (1380, 810), (1380, 840)]
    for x, y in columnas:
        texto = f"0x{azar.randrange(16**4):04X}%d  {volcado(azar, 15)} {azar.randrange(256):02X}"   # un solo %d: GRUB pasa un único valor
        salida.append((x, y, texto, TENUE))
    salida.append((300, 880, "reintentos restantes: %d", ROJO))
    salida.append((1380, 880, "canal abierto hace %d s", MEDIO))
    return salida

# ------------------------------------------------------------ corrupción progresiva
# Cada franja es una progress_bar con id "__timeout__". GRUB la llena de izquierda a derecha según el
# tiempo transcurrido (1/11 al empezar, 11/11 al llegar a cero) y estira la textura al ancho lleno:
# así la zona "desgarrada" avanza y se deforma un poco más cada segundo. El menú, la cuenta y la
# ayuda se dibujan después, encima, para que siempre se lean.
ITEMS = ["Arch Linux", "Windows 11", "Advanced options for Arch Linux", "UEFI Firmware Settings"]
MENU = (int(W * 0.31), int(H * 0.36), int(W * 0.38), 264)          # alto fijo: entran 4 entradas a cualquier resolución
CUENTA_Y = MENU[1] + MENU[3] + 6                                     # fila de la cuenta regresiva, debajo del menú
CUENTA_TXT = CUENTA_Y + 6
BARRA_Y = CUENTA_Y + 42
# zonas que la corrupción nunca pisa: GRUB redibuja cada franja encima de lo que haya, así que
# si una franja cruzara el menú lo taparía. Las franjas se cortan alrededor de estas zonas.
ZONA_MENU = (MENU[0] - 24, MENU[1] - 24, MENU[0] + MENU[2] + 24, MENU[1] + MENU[3] + 24)
ZONA_CUENTA = (MENU[0] - 24, CUENTA_Y - 6, MENU[0] + MENU[2] + 24, BARRA_Y + 14)
ZONA_AYUDA = (0, int(H * 0.935) - 4, W, int(H * 0.935) + 40)
ZONAS_LIBRES = [ZONA_MENU, ZONA_CUENTA, ZONA_AYUDA]

def recortar(x, y, w, h):
    """Parte una franja en los pedazos que no tocan ninguna zona libre."""
    pedazos = [(x, x + w)]
    for zx0, zy0, zx1, zy1 in ZONAS_LIBRES:
        if y + h <= zy0 or y >= zy1: continue
        nuevos = []
        for a, b in pedazos:
            if b <= zx0 or a >= zx1: nuevos.append((a, b)); continue
            if a < zx0: nuevos.append((a, zx0))
            if b > zx1: nuevos.append((zx1, b))
        pedazos = nuevos
    return [(a, y, b - a, h) for a, b in pedazos if b - a >= 12]

def franjas():
    azar = random.Random(4096)
    lista = []
    for _ in range(44):                                  # desgarros horizontales
        h = azar.choice([3, 4, 6, 8, 10, 14, 18, 24, 32, 40])
        y = azar.randrange(0, H - 120 - h)
        x = azar.choice([0, 0, 0, azar.randrange(0, W // 2)])
        w = W - x if azar.random() < 0.6 else azar.randrange(160, W - x)
        lista.append((x, y, w, h))
    for _ in range(10):                                  # astillas verticales
        w = azar.choice([6, 10, 16, 24, 40])
        h = azar.randrange(120, 700)
        x = azar.randrange(0, W - w); y = azar.randrange(0, H - 120 - h)
        lista.append((x, y, w, h))
    return lista

def corromper(recorte, azar):
    """Textura de una franja: la misma zona de la pantalla, desplazada, con canales corridos y basura."""
    im = recorte.convert("RGB")
    w, h = im.size
    lienzo = Image.new("RGB", (w, h), FONDO)
    y = 0
    while y < h:                                          # sub-renglones corridos a los costados
        alto = azar.randrange(1, 6)
        dx = azar.choice([-1, 1]) * azar.randrange(8, max(9, w // 3))
        tira = im.crop((0, y, w, min(h, y + alto)))
        lienzo.paste(tira, (dx % w, y)); lienzo.paste(tira, (dx % w - w, y))
        y += alto
    r, g, b = lienzo.split()                              # separación de canales (rojo corrido)
    r = r.transform(r.size, Image.AFFINE, (1, 0, -azar.randrange(4, 18), 0, 1, 0))
    lienzo = Image.merge("RGB", (r, g, b))
    d = ImageDraw.Draw(lienzo)
    for _ in range(max(1, w // 90)):                      # bloques quemados y píxeles estirados
        bx = azar.randrange(0, w); bw = azar.randrange(10, 120); bh = azar.randrange(1, max(2, h))
        by = azar.randrange(0, max(1, h - bh + 1))
        color = azar.choice([ROJO, CREMA, (20, 20, 24), (90, 30, 26), (230, 223, 207)])
        if azar.random() < 0.5:
            d.rectangle((bx, by, bx + bw, by + bh), fill=color)
        else:
            col = lienzo.getpixel((min(bx, w - 1), by))
            d.rectangle((bx, by, bx + bw * 3, by + bh), fill=col)
    if h >= 12:                                           # basura de caracteres
        fuente = f(min(14, h - 2))
        basura = "".join(azar.choice("▓▒░█▀▄#@%&$!?/\\|<>01ERRXXXX?¿") for _ in range(w // 8))
        d.text((azar.randrange(-40, 10), (h - fuente.size) // 2), basura, font=fuente,
               fill=azar.choice([ROJO, CREMA, MEDIO]))
    return lienzo

def pantalla_limpia(seg=10):
    im = fondo(); d = ImageDraw.Draw(im, "RGBA")
    for x, yy, texto, col in etiquetas_vivas():
        d.text((x, yy), texto.replace("%d", str(seg)), font=f(14), fill=col)
    return im

def primer_plano(im, seg, frac):
    """Lo que GRUB dibuja encima de las franjas: menú, cuenta regresiva y ayuda."""
    d = ImageDraw.Draw(im, "RGBA")
    x0, y0, w, h = MENU
    d.rectangle((x0, y0, x0 + w, y0 + h), fill=(12, 13, 16, 255), outline=(230, 223, 207, 90))
    y = y0 + 10
    for i, t in enumerate(ITEMS):
        if i == 0:
            d.rectangle((x0 + 4, y, x0 + w - 4, y + 46), fill=(40, 40, 42, 255))
            d.rectangle((x0 + 4, y, x0 + 7, y + 46), fill=CREMA)
            d.text((x0 + 26, y + 23), t, font=f(22, True), fill=CREMA, anchor="lm")
        else:
            d.text((x0 + 26, y + 23), t, font=f(18), fill=(138, 132, 120), anchor="lm")
        y += 54
    d.rectangle((x0, CUENTA_Y, x0 + int(W * 0.30), CUENTA_Y + 30), fill=(12, 13, 16, 255))
    d.text((x0, CUENTA_TXT + 15), f"└─› arranca solo en {seg} s", font=f(18), fill=CREMA, anchor="lm")
    bw = int(W * 0.38)
    d.rectangle((x0, BARRA_Y, x0 + bw, BARRA_Y + 6), fill=(38, 37, 42))
    d.rectangle((x0, BARRA_Y, x0 + int(bw * frac), BARRA_Y + 6), fill=ROJO)
    d.rectangle((0, int(H * 0.935), W, int(H * 0.935) + 34), fill=(9, 10, 13, 255))
    d.text((W / 2, int(H * 0.94) + 15), "↑ ↓  elegir     ·     enter  arrancar     ·     e  editar     ·     c  consola",
           font=f(14), fill=(200, 194, 179), anchor="mm")
    return im

def texturas():
    """[(x, y, w, h, textura)] — la textura se genera a partir de la pantalla limpia."""
    azar = random.Random(1812)
    limpia = pantalla_limpia()
    piezas = [p for fr in franjas() for p in recortar(*fr)]
    return [(x, y, w, h, corromper(limpia.crop((x, y, x + w, y + h)), azar)) for x, y, w, h in piezas]

def caja(carpeta, prefijo, borde, relleno, solo_izq=None, solo_centro=False):
    """Nueve piezas de un pixmap style de GRUB (bordes de 1 px).
    solo_centro: guarda únicamente la pieza _c (GRUB tolera que falten las demás). Importa porque GRUB
    registra en el TPM cada archivo que abre, y con cientos de piezas el registro del firmware se llena."""
    if solo_centro:
        c = relleno if isinstance(relleno, Image.Image) else Image.new("RGBA", (4, 4), relleno)
        c.save(os.path.join(carpeta, f"{prefijo}_c.png")); return
    piezas = {k: Image.new("RGBA", (1, 1), borde) for k in ("n", "s", "e", "w", "ne", "nw", "se", "sw")}
    piezas["c"] = relleno if isinstance(relleno, Image.Image) else Image.new("RGBA", (4, 4), relleno)
    if solo_izq:
        for k in ("n", "s", "e", "ne", "nw", "se", "sw"): piezas[k] = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        piezas["w"] = Image.new("RGBA", (solo_izq, 4), borde)
    for k, im in piezas.items(): im.save(os.path.join(carpeta, f"{prefijo}_{k}.png"))

CABECERA_TEMA = """# Tema de GRUB "N.M." (versión agresiva, se corrompe cada segundo).
# Generado por generar_tema.py: no editar a mano.
title-text: ""
desktop-image: "fondo.png"
desktop-color: "#090a0d"
terminal-font: "JetBrainsMono NFM Regular 18"
terminal-box: "terminal_*.png"
terminal-left: "20%"
terminal-top: "15%"
terminal-width: "60%"
terminal-height: "70%"
terminal-border: "0"
"""

PRIMER_PLANO_TEMA = """

+ boot_menu {{
    left = {x0}
    top = {y0}
    width = {w}
    height = {h}
    menu_pixmap_style = "menu_*.png"
    item_font = "JetBrainsMono NFM Regular 18"
    item_color = "#8a8478"
    selected_item_font = "JetBrainsMono NFM Bold 22"
    selected_item_color = "#e6dfcf"
    selected_item_pixmap_style = "sel_*.png"
    item_height = 46
    item_padding = 22
    item_spacing = 8
    icon_width = 0
    icon_height = 0
    item_icon_space = 0
    scrollbar = false
}}

+ label {{
    id = "__timeout__"
    left = {cx}
    top = {cy}
    width = {tw}
    height = 30
    align = "left"
    text = "arranca solo en %d s"
    font = "JetBrainsMono NFM Regular 18"
    color = "#e6dfcf"
}}

+ progress_bar {{
    id = "__timeout__"
    left = {x0}
    top = {by}
    width = {bw}
    height = 6
    fg_color = "#c4483a"
    bg_color = "#26252a"
    border_color = "#26252a"
    show_text = false
}}

"""

def fuentes_pf2(carpeta):
    """Fuentes de GRUB a partir de JetBrainsMono (solo los rangos que usa el tema, para que pesen poco)."""
    rangos = "0x20-0x7E,0xA0-0x17F,0x2010-0x203F,0x2190-0x21FF,0x2500-0x259F"
    for ttf, estilo, tam in ((REG, "regular", 14), (REG, "regular", 18), (BOLD, "bold", 22)):
        subprocess.run(["grub-mkfont", "-r", rangos, "-s", str(tam), "-o",
                        os.path.join(carpeta, f"jetbrains-{estilo}-{tam}.pf2"), ttf], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def tema(TEMA):
    os.makedirs(TEMA, exist_ok=True)
    for n in os.listdir(TEMA):
        if n.endswith(".png") or n == "theme.txt": os.remove(os.path.join(TEMA, n))
    fondo().save(os.path.join(TEMA, "fondo.png"), optimize=True)
    OSC = (12, 13, 16, 255)
    caja(TEMA, "menu", CREMA + (90,), OSC)
    caja(TEMA, "sel", CREMA + (255,), (40, 40, 42, 255), solo_izq=3)
    caja(TEMA, "terminal", CREMA + (90,), (9, 10, 13, 240))
    caja(TEMA, "vacio", (0, 0, 0, 0), (0, 0, 0, 0), solo_centro=True)
    hexa = lambda c: "#%02x%02x%02x" % tuple(c[:3])
    x0, y0, w, h = MENU
    partes = [CABECERA_TEMA]
    # 1) volcados de memoria que cambian con el contador
    for x, y, texto, col in etiquetas_vivas():
        partes.append(f'\n+ label {{ id = "__timeout__" left = {x} top = {y} width = 520 height = 20 align = "left"'
                      f'\n    text = "{texto}" font = "JetBrainsMono NFM Regular 14" color = "{hexa(col)}" }}')
    # 2) desgarros: una barra de progreso por franja, con su textura corrupta
    for k, (x, y, fw, fh, tex) in enumerate(texturas()):
        caja(TEMA, f"corr{k:02d}", (0, 0, 0, 0), tex.convert("RGBA"), solo_centro=True)
        partes.append(f'\n+ progress_bar {{ id = "__timeout__" left = {x} top = {y} width = {fw} height = {fh}'
                      f'\n    bar_style = "vacio_*.png" highlight_style = "corr{k:02d}_*.png" highlight_overlay = true show_text = false }}')
    # 3) primer plano, siempre legible
    partes.append(PRIMER_PLANO_TEMA.format(tx=x0 - 4, ty=CUENTA_Y, tw=int(W * 0.30), py=int(H * 0.935), W=W,
                                           x0=x0, y0=y0, w=w, h=h, cy=CUENTA_TXT, by=BARRA_Y, cx=x0 + 48,
                                           bw=int(W * 0.38), ay=int(H * 0.94)))
    open(os.path.join(TEMA, "theme.txt"), "w").write("".join(partes) + "\n")
    fuentes_pf2(TEMA)

# ------------------------------------------------------------ vista previa
def preview(salida):
    tex = texturas()
    carpeta = tempfile.mkdtemp(prefix="grub-tema-")
    primero = 11                                           # GRUB: first_timeout = timeout + 1
    k = 0
    for seg in range(10, -1, -1):
        frac = (primero - seg) / primero
        im = pantalla_limpia(seg)
        for x, y, w, h, t in tex:                          # progress_bar: textura estirada al ancho lleno
            ancho = max(1, int(w * frac))
            im.paste(t.resize((ancho, h), Image.NEAREST), (x, y))
        primer_plano(im, seg, frac)
        im.save(f"{carpeta}/{k:03d}.png"); k += 1
    im = Image.new("RGB", (W, H), (0, 0, 0)); im.save(f"{carpeta}/{k:03d}.png")   # arranca el sistema: negro
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", "1", "-i", f"{carpeta}/%03d.png",
                    "-vf", "fps=25", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", salida], check=True)
    shutil.rmtree(carpeta)

if __name__ == "__main__":
    if sys.argv[1:] == ["resolucion"]: print(f"{W}x{H}")
    elif len(sys.argv) == 3 and sys.argv[1] == "tema": tema(sys.argv[2])
    elif len(sys.argv) == 3 and sys.argv[1] == "preview": preview(sys.argv[2])
    else: sys.exit(__doc__)
