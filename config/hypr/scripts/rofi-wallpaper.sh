#!/usr/bin/env bash
# Selector de fondo de pantalla 100% por teclado (flechas + Enter), sin
# necesidad del touchpad ni el mouse. Reemplaza al selector de Quickshell
# (Super+Ctrl+W), que requiere clic. Usa la misma carpeta y el mismo
# comando ml4w-wallpaper que ya aplican matugen, Waybar, el dock, etc.

CARPETA_SETTING="$HOME/.config/ml4w/settings/wallpaper-folder"
CARPETA="$HOME/wallpapers"
if [ -f "$CARPETA_SETTING" ]; then
    CRUDA=$(cat "$CARPETA_SETTING")
    CRUDA="${CRUDA//\$HOME/$HOME}"
    CRUDA="${CRUDA//\~/$HOME}"
    [ -d "$CRUDA" ] && CARPETA="$CRUDA"
fi

mapfile -d '' -t IMAGENES < <(find "$CARPETA" -maxdepth 1 -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" \) -print0 | sort -z)

if [ "${#IMAGENES[@]}" -eq 0 ]; then
    notify-send -a "Fondo de pantalla" "No hay imágenes en $CARPETA"
    exit 1
fi

ENTRADAS=""
for img in "${IMAGENES[@]}"; do
    nombre="$(basename "$img")"
    nombre="${nombre%.*}"
    nombre="${nombre//_/ }"
    ENTRADAS+="${nombre}\n"
done

INDICE=$(printf "%b" "$ENTRADAS" | rofi -dmenu -i -p "Fondo de pantalla" -format i)

[ -z "$INDICE" ] && exit 0

ELEGIDA="${IMAGENES[$INDICE]}"
[ -f "$ELEGIDA" ] || exit 1

"$HOME/.config/ml4w/scripts/ml4w-wallpaper" "$ELEGIDA"
