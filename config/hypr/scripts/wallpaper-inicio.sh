#!/usr/bin/env bash
# Elige una pintura al azar y la deja en la caché de ML4W.
# Se ejecuta ANTES de ml4w-autostart (en la misma línea de autostart.conf),
# que luego la aplica con awww + matugen y recarga Waybar, dock y swaync.
# Así no hay carrera entre dos scripts cambiando el wallpaper.

CACHE_FOLDER="$HOME/.cache/ml4w/hyprland-dotfiles"
CACHE_FILE="$CACHE_FOLDER/current_wallpaper"
SETTINGS_WALLPAPER_FOLDER="$HOME/.config/ml4w/settings/wallpaper-folder"

# Carpeta: la configurada en ML4W (expandiendo $HOME y ~ igual que ml4w-wallpaper)
CARPETA="$HOME/wallpapers"
if [ -f "$SETTINGS_WALLPAPER_FOLDER" ]; then
    RAW=$(cat "$SETTINGS_WALLPAPER_FOLDER")
    RAW="${RAW//\$HOME/$HOME}"
    RAW="${RAW//\~/$HOME}"
    [ -d "$RAW" ] && CARPETA="$RAW"
fi

# Mismo criterio de selección que ml4w-wallpaper --random
IMAGEN=$(find "$CARPETA" -maxdepth 1 -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" \) | shuf -n 1)

if [ -z "$IMAGEN" ]; then
    echo ":: wallpaper-inicio: no hay imágenes en $CARPETA, se mantiene la caché" >&2
    exit 0
fi

mkdir -p "$CACHE_FOLDER"
echo "$IMAGEN" > "$CACHE_FILE"
echo ":: wallpaper-inicio: $IMAGEN"
