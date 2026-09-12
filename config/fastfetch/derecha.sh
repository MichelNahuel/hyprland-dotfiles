#!/usr/bin/env bash
# Dibuja la M animada a la derecha de las especificaciones de fastfetch.
#
# kitty reproduce el APNG en bucle por su cuenta, así que no bloquea el shell.
# El cursor se guarda y se restaura (\e7 ... \e8) porque `icat --place` lo deja
# donde dibujó: sin eso, el prompt aparecería arriba a la derecha.
#
# Pensado para ejecutarse justo después de fastfetch al abrir la terminal: la
# posición es absoluta en la pantalla, así que cuenta con que el bloque recién
# impreso esté arriba de todo.

IMAGEN="$HOME/.cache/fastfetch/logo-m.png"
COLUMNAS=16        # ancho de la imagen en celdas
FILAS=10           # alto de la imagen en celdas
COLUMNA=72         # a la derecha de la línea más larga (el procesador)
FILA=1             # misma altura que el bloque de fastfetch

# Solo en kitty, con la imagen disponible y si la terminal es lo bastante ancha
[ -f "$IMAGEN" ] || exit 0
[ -n "$KITTY_WINDOW_ID" ] || exit 0
command -v kitten >/dev/null 2>&1 || exit 0
[ "$(tput cols 2>/dev/null || echo 0)" -ge "$((COLUMNA + COLUMNAS + 2))" ] || exit 0

printf '\e7'
kitten icat --place "${COLUMNAS}x${FILAS}@${COLUMNA}x${FILA}" --loop -1 "$IMAGEN" 2>/dev/null
printf '\e8'
