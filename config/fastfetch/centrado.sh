#!/usr/bin/env bash
# Dibuja "N · M ·" centrado en la terminal, con los puntos girando,
# y la bandera argentina flameando pegada al margen derecho.
#
# fastfetch imprime las especificaciones pegadas a la izquierda (sin logo) y este
# script coloca las cuatro imágenes con kitten icat. Cada imagen es una animación
# propia de kitty: el punto gira con su ritmo, independiente del de las letras.
#
# El cursor NO se restaura con \e7/\e8: cada llamada a `icat --place` hace su
# propio guardado y pisa el nuestro, así que con varias imágenes el prompt
# terminaba dibujado sobre las especificaciones. En su lugar se le pregunta la
# posición a la terminal (DSR) y se vuelve a ella de forma absoluta.
#
# Las posiciones son absolutas en pantalla, así que el bloque solo tiene sentido
# mientras la pantalla siga siendo la recién impresa. Por eso:
#   - se vuelve a llamar al cambiar el tamaño de la ventana (trap WINCH), para
#     recentrarlo y que no se deshaga al abrir una pestaña o redimensionar;
#   - si el cursor ya bajó (hubo comandos o scroll), no dibuja nada, para no
#     pintar encima de lo que estés haciendo.

CACHE="$HOME/.cache/fastfetch"
LETRA_COLS=16      # ancho de cada letra, en celdas
LETRA_FILAS=10     # alto de cada letra
PUNTO_COLS=5       # ancho del punto (la caja acompaña su proporción cuadrada)
PUNTO_FILAS=2      # alto del punto
HUECO=1            # separación entre piezas
FILA_LETRAS=1      # misma altura que el bloque de fastfetch
DATOS_COLS=46      # ancho de las especificaciones + margen
BANDERA_COLS=40    # ancho de la bandera
BANDERA_FILAS=10   # alto de la bandera, igual al de las letras
MARGEN_DER=2       # aire entre la bandera y el borde derecho
AIRE=3             # separación mínima entre el bloque centrado y la bandera

BLOQUE=$(( LETRA_COLS + HUECO + PUNTO_COLS + HUECO + LETRA_COLS + HUECO + PUNTO_COLS ))
# el piso del salto queda a la altura del ▔ de las letras (arriba de la última fila)
FILA_PUNTOS=$(( FILA_LETRAS + LETRA_FILAS - PUNTO_FILAS - 1 ))
FONDO=$(( FILA_LETRAS + LETRA_FILAS + 4 ))    # hasta dónde se considera "pantalla inicial"

for img in logo-n.png punto.png logo-m.png; do
    [ -f "$CACHE/$img" ] || exit 0
done
# la bandera es opcional: si falta, el resto se dibuja igual
[ -n "$KITTY_WINDOW_ID" ] || exit 0
command -v kitten >/dev/null 2>&1 || exit 0

COLUMNAS=$(tput cols 2>/dev/null || echo 0)
INICIO=$(( (COLUMNAS - BLOQUE) / 2 ))
# si no entra centrado sin pisar las especificaciones, no se dibuja nada
[ "$INICIO" -ge "$DATOS_COLS" ] || exit 0

# Posición actual del cursor, para volver exactamente ahí al terminar
fila=""; columna=""
IFS='[;' read -srt 0.3 -d R -p $'\e[6n' _ fila columna 2>/dev/null

# Si ya se scrolleó o hay comandos ejecutados, no repintar sobre el trabajo
case "$fila" in
    ''|*[!0-9]*) : ;;
    *) [ "$fila" -le "$FONDO" ] || exit 0 ;;
esac

kitten icat --clear 2>/dev/null        # borra la tanda anterior antes de recentrar

colocar() {  # $1 imagen, $2 columna, $3 fila, $4 ancho, $5 alto
    kitten icat --place "${4}x${5}@${2}x${3}" --loop -1 "$CACHE/$1" 2>/dev/null
}

col=$INICIO
colocar logo-n.png "$col" "$FILA_LETRAS" "$LETRA_COLS" "$LETRA_FILAS"
col=$(( col + LETRA_COLS + HUECO ))
colocar punto.png "$col" "$FILA_PUNTOS" "$PUNTO_COLS" "$PUNTO_FILAS"
col=$(( col + PUNTO_COLS + HUECO ))
colocar logo-m.png "$col" "$FILA_LETRAS" "$LETRA_COLS" "$LETRA_FILAS"
col=$(( col + LETRA_COLS + HUECO ))
colocar punto.png "$col" "$FILA_PUNTOS" "$PUNTO_COLS" "$PUNTO_FILAS"

# La bandera, pegada a la derecha. Solo si entra sin acercarse al bloque centrado:
# en una terminal angosta se omite en vez de encimarse.
COL_BANDERA=$(( COLUMNAS - BANDERA_COLS - MARGEN_DER ))
if [ -f "$CACHE/bandera.png" ] && [ "$COL_BANDERA" -ge $(( INICIO + BLOQUE + AIRE )) ]; then
    colocar bandera.png "$COL_BANDERA" "$FILA_LETRAS" "$BANDERA_COLS" "$BANDERA_FILAS"
fi

if [ -n "$fila" ] && [ -n "$columna" ]; then
    printf '\e[%s;%sH' "$fila" "$columna"
else
    printf '\e[%d;1H' "$(( FILA_LETRAS + LETRA_FILAS + 2 ))"   # respaldo
fi
