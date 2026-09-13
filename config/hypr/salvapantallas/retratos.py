#!/usr/bin/env python3
"""Retratos de próceres con exactamente el mismo trazo que el mapa.

La imagen se lleva a la grilla de celdas de la terminal y su tono se divide en
niveles: luz y sombra. Las dos son "regiones", cada una con su contorno y su
relleno; fuera del medallón queda vacío, como el mar alrededor del mapa. Esas regiones se dibujan con mapa.dibujar_regiones, la
misma función que dibuja las provincias.
"""
import os, sys, argparse
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import mapa

# brillo del relleno por nivel de luz (1 = sombra, 3 = luz), sobre el crema del mapa
BRILLO = {1: 0.45, 2: 0.90}

def fundir_chicas(ids, minimo):
    """Absorbe las zonas de menos de `minimo` celdas en la región que más las rodea."""
    ids = ids.copy()
    for _ in range(4):
        cambio = False
        for valor in np.unique(ids):
            etiquetas, n = ndimage.label(ids == valor)
            if n == 0: continue
            tamanos = ndimage.sum(np.ones_like(ids), etiquetas, range(1, n + 1))
            for k, t in enumerate(tamanos, start=1):
                if t >= minimo: continue
                zona = etiquetas == k
                borde = ndimage.binary_dilation(zona) & ~zona
                vecinos = ids[borde]
                if vecinos.size:
                    ids[zona] = np.bincount(vecinos).argmax(); cambio = True
        if not cambio: break
    return ids

def a_regiones(ruta, filas, recorte, niveles=3, suavizado=0.8, minimo=5, detalle=1.6, ovalo=0.47, fondo_claro=None,
               fondo_azul=None, fondo_color=None, silueta=None):
    color = Image.open(ruta).convert("RGB")
    w, h = color.size
    x0, y0, x1, y1 = recorte
    color = color.crop((int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h)))
    im = color.convert("L")
    cols = max(1, round(filas * (im.width / im.height) * mapa.ASPECTO_CELDA))
    SS = 4
    a = np.asarray(im.resize((cols * SS, filas * SS), Image.LANCZOS), dtype=np.float32)
    a = a.reshape(filas, SS, cols, SS).mean(axis=(1, 3))
    asp = mapa.ASPECTO_CELDA
    crudo = a.copy()
    # contraste local: resalta rasgos (ojos, cejas, nariz) por sobre el degradado general
    fondo = ndimage.gaussian_filter(a, (4, 4 * asp))
    a = a + detalle * (a - fondo)
    a = ndimage.gaussian_filter(a, (suavizado, suavizado * asp))
    # medallón: óvalo inscripto en el recorte; afuera queda vacío
    yy, xx = np.mgrid[0:filas, 0:cols]
    dentro = ((xx - cols / 2) / (cols * ovalo)) ** 2 + ((yy - filas / 2) / (filas * ovalo)) ** 2 <= 1
    if silueta:
        # silueta trazada a mano (polígonos en fracciones del recorte): para fondos del mismo
        # tono y color que la cara, donde ningún umbral los separa
        lienzo = Image.new("L", (cols * SS, filas * SS), 0)
        trazo = ImageDraw.Draw(lienzo)
        for poligono in silueta:
            trazo.polygon([(x * cols * SS, y * filas * SS) for x, y in poligono], fill=255)
        dentro = dentro & (np.asarray(lienzo, dtype=np.float32).reshape(filas, SS, cols, SS).mean(axis=(1, 3)) >= 128)
    if fondo_claro is not None or fondo_azul is not None or fondo_color is not None:
        # fondo liso: lo que cumple el criterio y llega al borde del medallón es fondo y queda
        # vacío; la cara, aunque se le parezca, está rodeada por el pelo y la ropa y no llega.
        #   fondo_claro: brillo mínimo (fotos con fondo claro)
        #   fondo_azul: azul menos rojo mínimo (pinturas con fondo azulado; lo oscuro no cuenta)
        #   fondo_color: [R, G, B, tolerancia] (fondos de un color parejo)
        brillo = ndimage.gaussian_filter(crudo, (1, asp))
        if fondo_claro is not None:
            claro = brillo >= fondo_claro
        else:
            rgb = np.asarray(color.resize((cols * SS, filas * SS), Image.LANCZOS), dtype=np.float32)
            rgb = rgb.reshape(filas, SS, cols, SS, 3).mean(axis=(1, 3))
            if fondo_azul is not None:
                azul = ndimage.gaussian_filter(rgb[..., 2] - rgb[..., 0], (1, asp))
                claro = (azul >= fondo_azul) & (brillo >= 60)
            else:
                r, g, b, tolerancia = fondo_color
                rgb = np.stack([ndimage.gaussian_filter(rgb[..., k], (1, asp)) for k in range(3)], axis=-1)
                claro = np.sqrt(((rgb - np.array([r, g, b], dtype=np.float32)) ** 2).sum(-1)) <= tolerancia
        claro = ndimage.binary_opening(claro & dentro, structure=np.ones((2, 3)))
        orilla = dentro & ~ndimage.binary_erosion(dentro, iterations=2)
        etiquetas, n = ndimage.label(claro)
        tocan = set(np.unique(etiquetas[orilla & claro])) - {0}
        fondo_mask = np.isin(etiquetas, list(tocan))
        fondo_mask = ndimage.binary_closing(fondo_mask, structure=np.ones((3, 5)))
        # una celda más: la transición entre el fondo y el pelo quedaba como un anillo claro
        fondo_mask = ndimage.binary_dilation(fondo_mask, structure=np.ones((3, 3))) & dentro
        dentro = dentro & ~fondo_mask
    # tono fino (menos suavizado) normalizado dentro del medallón, para la escala de densidad
    fino = ndimage.gaussian_filter(np.asarray(im.resize((cols * SS, filas * SS), Image.LANCZOS), dtype=np.float32)
                                   .reshape(filas, SS, cols, SS).mean(axis=(1, 3)), (0.35, 0.35 * asp))
    fino = fino + 1.3 * (fino - ndimage.gaussian_filter(fino, (2.5, 2.5 * asp)))
    lo, hi = np.percentile(fino[dentro], [2, 98])
    tono = np.clip((fino - lo) / max(hi - lo, 1e-6), 0, 1)
    cortes = np.percentile(a[dentro], [100 * k / niveles for k in range(1, niveles)])
    ids = np.digitize(a, cortes)                        # 0 = lo más oscuro → vacío (pelo, ojos)
    ids[~dentro] = 0
    ids = fundir_chicas(ids, minimo)
    ids[~dentro] = 0
    # solo la cabeza: se descartan los pedazos sueltos (brillos del pelo, astillas del fondo)
    etiquetas, n = ndimage.label(ids > 0)
    if n > 1:
        tamanos = ndimage.sum(np.ones_like(ids), etiquetas, range(1, n + 1))
        grande = tamanos.max()
        for k, t in enumerate(tamanos, start=1):
            if t < grande * 0.06: ids[etiquetas == k] = 0
    return ids.astype(int).tolist(), tono, fino, dentro

# escala de densidad sin | / \\ _ - : esos quedan reservados para los contornos del mapa
RAMPA = " .,:;+*oO#"
RAMPA_SOMBRA = ".,:;+*"         # las sombras nunca llegan a la densidad de la luz
HUECO_SIN_CONTORNO = 400       # celdas: los huecos más chicos se dibujan solo con densidad
VERSION = 22                    # entra en la firma de la caché del carrusel

def sombras(luz, dentro):
    """Lo oscuro que forma parte de la figura: huecos encerrados por la luz (ojos, boca)
    y lo que la rodea dentro del medallón (pelo, ropa), para que no queden agujeros."""
    cerca = ndimage.binary_dilation(luz, iterations=6, structure=np.ones((3, 3)))
    sombra = ndimage.binary_fill_holes(luz | (cerca & dentro)) & ~luz
    etiquetas, n = ndimage.label(sombra)
    if n:
        tamanos = ndimage.sum(np.ones_like(etiquetas), etiquetas, range(1, n + 1))
        for k, t in enumerate(tamanos, start=1):
            if t < 6: sombra[etiquetas == k] = False
    return sombra

def dibujar(ruta, filas, recorte, ovalo=0.47, sombreado=(), figura=(), fondo_claro=None, fondo_azul=None,
            fondo_color=None, figura_completa=False, silueta=None, contraste_local=0.6, solo_cara=False):
    """Luz con escala de densidad; sombras con su propio contorno y un relleno más tenue.

    sombreado: rectángulos [x0, y0, x1, y1] (fracciones del retrato) que se dibujan solo
    con densidad, sin trazos internos: para ojos o caras donde los contornos ensucian.
    Con un quinto valor "textura" (pelo) se quitan los trazos pero se conserva el relleno de sombra;
    con "interior" (rasgos de la cara) no se toca una franja junto al borde de la figura.
    figura: óvalos [x0, y0, x1, y1] que forman parte de la figura aunque su tono se confunda
    con el fondo (pelo que se funde con un fondo oscuro).
    fondo_claro: umbral de brillo (0-255) para fotos con fondo claro; ese fondo queda vacío.
    fondo_azul: umbral de azul menos rojo para pinturas con fondo azulado; ese fondo queda vacío.
    fondo_color: [R, G, B, tolerancia] para fondos de un color parejo; ese fondo queda vacío.
    figura_completa: con el fondo quitado, todo lo demás es figura (pelo oscuro muy ancho).
    silueta: polígonos [[x, y], ...] en fracciones del recorte; afuera queda vacío.
    contraste_local: cuánto pesa el tono propio de las zonas de sombreado (0 a 1); más alto
    en fotos de cara lavada, donde el tono general deja todos los rasgos iguales.
    solo_cara: ese tono propio se estira solo con la piel clara de la zona (sin pelo ni ropa).
    """
    ids, tono, fino, dentro = a_regiones(ruta, filas, recorte, niveles=2, ovalo=ovalo, fondo_claro=fondo_claro,
                                         fondo_azul=fondo_azul, fondo_color=fondo_color, silueta=silueta)
    luz = np.array(ids) > 0
    if not figura_completa:
        sombra = sombras(luz, dentro)
    else:
        # con el fondo ya quitado, todo lo que queda es figura por más ancho que sea el pelo
        # oscuro (con la regla de cercanía a la luz se cortaba en línea recta)
        sombra = dentro & ~luz
        etiquetas, n = ndimage.label(sombra)
        if n:
            # solo se descartan astillas sueltas en el borde; un hueco chico encerrado por la
            # cara (comisura, fosa nasal) se queda, si no se dibuja como un agujero con contorno
            orilla = ~ndimage.binary_erosion(dentro)
            tamanos = ndimage.sum(np.ones_like(etiquetas), etiquetas, range(1, n + 1))
            for k, t in enumerate(tamanos, start=1):
                # con silueta trazada a mano no hay astillas de fondo: se queda todo
                if t < 6 and not silueta and (orilla & (etiquetas == k)).any(): sombra[etiquetas == k] = False
    F, C = luz.shape
    yy, xx = np.mgrid[0:F, 0:C]
    ovalo_en = lambda x0, y0, x1, y1: (((xx - (x0 + x1) / 2 * C) / ((x1 - x0) / 2 * C)) ** 2 +
                                       ((yy - (y0 + y1) / 2 * F) / ((y1 - y0) / 2 * F)) ** 2 <= 1)
    for caja in figura or ():
        sombra |= ovalo_en(*caja) & dentro & ~luz
    zona = np.zeros_like(luz)
    textura = np.zeros_like(luz)                        # zonas que conservan el relleno de sombra
    interior = np.zeros_like(luz)                       # zonas que no tocan el borde de la figura
    for x0, y0, x1, y1, *modo in sombreado or ():
        # óvalo inscripto en el rectángulo: un corte recto dejaría una línea de contorno recta
        cx, cy, rx, ry = (x0 + x1) / 2 * C, (y0 + y1) / 2 * F, (x1 - x0) / 2 * C, (y1 - y0) / 2 * F
        ovalo_zona = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1
        if modo and modo[0] == "textura": textura |= ovalo_zona
        elif modo and modo[0] == "interior": interior |= ovalo_zona
        else: zona |= ovalo_zona
    # las sombras que caen casi enteras adentro entran completas, así no quedan medio cortadas
    etiquetas, n = ndimage.label(sombra)
    for k in range(1, n + 1):
        parte = etiquetas == k
        if (parte & zona).sum() >= 0.5 * parte.sum(): zona |= parte
    if interior.any():
        # rasgos de la cara (ojos, nariz, boca) sin tocar el pelo de los costados: se deja
        # un margen contra el borde de la figura y las sombras grandes no entran enteras
        borde = ndimage.binary_dilation(~(luz | sombra), structure=np.ones((9, 19)))
        interior &= ~borde
        for k in range(1, n + 1):
            parte = etiquetas == k
            if parte.sum() <= 300 and (parte & interior).sum() >= 0.5 * parte.sum(): interior |= parte & ~borde
        zona |= interior
    zona &= luz | sombra                                # nunca agranda la figura
    # "textura" (pelo): sin contornos, pero con la escala y el brillo de las sombras
    textura &= sombra & ~zona
    if zona.any():
        # tono propio de la zona, mezclado con el general para que lo negro no se aclare de más
        base = zona & luz if solo_cara and (zona & luz).sum() > 50 else zona
        local = np.clip((fino - np.percentile(fino[base], 3)) /
                        max(np.ptp(np.percentile(fino[base], [3, 97])), 1e-6), 0, 1)
        tono = np.where(zona, contraste_local * local + (1 - contraste_local) * tono, tono)
        luz = luz | zona
        sombra = sombra & ~zona
    reg = np.where(luz | textura, 2, np.where(sombra, 1, 0))
    sombra = sombra | textura
    # un margen de una celda: si el medallón toca el borde del recorte, el contorno igual se cierra
    reg, tono, fino, sombra, textura = (np.pad(np.asarray(a), 1, mode="edge" if k in (1, 2) else "constant")
                                        for k, a in enumerate((reg, tono, fino, sombra, textura)))
    # tono propio de las sombras: contraste local y normalizado solo entre ellas,
    # así el pelo y los pliegues oscuros muestran forma en vez de un relleno plano
    asp = mapa.ASPECTO_CELDA
    osc = fino + 1.5 * (fino - ndimage.gaussian_filter(fino, (2.5, 2.5 * asp)))
    lo, hi = np.percentile(osc[sombra], [3, 97]) if sombra.any() else (0, 1)
    tono_sombra = np.clip((osc - lo) / max(hi - lo, 1e-6), 0, 1)
    celdas = mapa.dibujar_regiones(reg.tolist(), lambda i: mapa.CREMA, contorno=mapa.CREMA, limite=mapa.CREMA)
    for y, fila in enumerate(celdas):
        for x, (ch, _) in enumerate(fila):
            if ch != ".": continue
            if reg[y][x] == 2 and not textura[y][x]:
                t = float(tono[y][x]) ** 0.95
                c = RAMPA[min(len(RAMPA) - 1, int(t * len(RAMPA)))]
                if c == " ": c = "."             # lo más oscuro de la cara (pupilas) se marca, no se borra
                fila[x] = (c, tuple(int(v * (0.35 + 0.65 * t)) for v in mapa.CREMA))
            else:
                t = float(tono_sombra[y][x])
                c = RAMPA_SOMBRA[min(len(RAMPA_SOMBRA) - 1, int(t * len(RAMPA_SOMBRA)))]
                fila[x] = (c, tuple(int(v * (0.45 + 0.35 * t)) for v in mapa.CREMA))
    return celdas

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("imagen"); ap.add_argument("--png", required=True)
    ap.add_argument("--filas", type=int, default=70)
    ap.add_argument("--ovalo", type=float, default=0.47, help="radio del medallón (0.5 = toca los bordes)")
    ap.add_argument("--recorte", type=float, nargs=4, default=(0, 0, 1, 1), metavar=("X0", "Y0", "X1", "Y1"))
    a = ap.parse_args()
    celdas = dibujar(a.imagen, a.filas, a.recorte, a.ovalo)
    mapa.png(celdas, a.png)
    print(f"{a.png}: {len(celdas[0])}x{len(celdas)} celdas")
