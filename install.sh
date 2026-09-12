#!/usr/bin/env bash
# Instala la personalización sobre ML4W Dotfiles.
# Uso: bash install.sh            (instala y recarga)
#      NO_RELOAD=1 bash install.sh (instala sin recargar)

set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}"
FECHA="$(date +%Y-%m-%d_%H%M%S)"
BACKUP="$HOME/backups/hyprland-dotfiles-$FECHA"

info()  { printf '\033[0;32m::\033[0m %s\n' "$1"; }
aviso() { printf '\033[1;33m!!\033[0m %s\n' "$1"; }
error() { printf '\033[0;31mxx\033[0m %s\n' "$1" >&2; exit 1; }

# Detiene solo el script del LED de ESTE $CONFIG (y sus procesos hijos),
# sin afectar otros procesos del sistema.
detener_led() {
    local script="$CONFIG/hypr/scripts/mic-led.sh"
    local patron="[${script:0:1}]${script:1}"
    local pid
    for pid in $(pgrep -f "$patron"); do
        pkill -P "$pid" 2>/dev/null
        kill "$pid" 2>/dev/null
    done
}

# 1. Verificaciones
[ -d "$CONFIG/waybar/themes/ml4w-transparent-centered" ] ||
    error "No se encontró ML4W Dotfiles (falta $CONFIG/waybar/themes/ml4w-transparent-centered)."
[ -d "$CONFIG/nwg-dock-hyprland/themes" ] || error "No se encontró la configuración de nwg-dock-hyprland de ML4W."
[ -d "$CONFIG/swaync/themes" ] || error "No se encontró la configuración de swaync de ML4W."
if ! fc-list 2>/dev/null | grep -q "JetBrainsMono Nerd Font"; then
    aviso "JetBrainsMono Nerd Font no está instalada: los íconos de la barra no se verán (sudo pacman -S ttf-jetbrains-mono-nerd)."
fi

# 2. Respaldo + 3. Copia
mkdir -p "$BACKUP/config"
: > "$BACKUP/nuevos.txt"
info "Respaldo en $BACKUP"

cd "$REPO/config" || error "No se encontró la carpeta config/ del repositorio."
while IFS= read -r -d '' f; do
    rel="${f#./}"
    dest="$CONFIG/$rel"
    if [ -e "$dest" ]; then
        mkdir -p "$BACKUP/config/$(dirname "$rel")"
        cp -L "$dest" "$BACKUP/config/$rel" || error "No se pudo respaldar $rel"
    else
        echo "$rel" >> "$BACKUP/nuevos.txt"
    fi
    mkdir -p "$(dirname "$dest")"
    # cp (sin --remove-destination) escribe a través de los symlinks de ML4W
    cp "$f" "$dest" || error "No se pudo instalar $rel"
    info "instalado: $rel"
done < <(find . -type f -print0 | sort -z)

chmod +x "$CONFIG/waybar/scripts/fecha.sh" "$CONFIG/hypr/scripts/mic-led.sh" \
         "$CONFIG/fastfetch/centrado.sh"

# Piezas animadas de la consola. El generador deja también una N quieta en
# waybar/assets/: si no existía, se anota como archivo nuevo para que
# restaurar.sh la borre al deshacer la instalación.
[ -e "$CONFIG/waybar/assets/logo-n.png" ] || echo "waybar/assets/logo-n.png" >> "$BACKUP/nuevos.txt"
if python3 -c "import PIL" 2>/dev/null; then
    python3 "$CONFIG/fastfetch/logo-n.py" >/dev/null && info "N, M, punto y bandera generados en ~/.cache/fastfetch/"
else
    aviso "Falta python-pillow: no se pudieron generar las piezas animadas (sudo pacman -S python-pillow)."
fi
if ! grep -q 'templates.logo_n' "$CONFIG/matugen/config.toml" 2>/dev/null; then
    aviso "Para que las piezas se regeneren con cada pintura, agregá [templates.logo_n] a ~/.config/matugen/config.toml (ver README)."
fi

# 4. Rutas de hyprlock
sed -i --follow-symlinks "s#__HOME__#$HOME#g" "$CONFIG/hypr/hyprlock.conf"
for img in kcd_fondo.png vault_boy.png; do
    [ -f "$HOME/Pictures/pantalla_bloqueo/$img" ] ||
        aviso "Falta ~/Pictures/pantalla_bloqueo/$img (usada por la pantalla de bloqueo; ver README)."
done

# Script de restauración para esta instalación
cat > "$BACKUP/restaurar.sh" <<'EOF'
#!/usr/bin/env bash
# Deshace la instalación de hyprland-dotfiles hecha junto a este respaldo.
B="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}"

# Detener solo el script del LED de este $CONFIG (y sus procesos hijos)
script="$CONFIG/hypr/scripts/mic-led.sh"
for pid in $(pgrep -f "[${script:0:1}]${script:1}"); do
    pkill -P "$pid" 2>/dev/null
    kill "$pid" 2>/dev/null
done

cd "$B/config" && find . -type f -print0 | while IFS= read -r -d '' f; do
    cp "$f" "$CONFIG/${f#./}" && echo "restaurado: ${f#./}"
done
while IFS= read -r rel; do
    [ -n "$rel" ] && rm -f "$CONFIG/$rel" && echo "eliminado: $rel"
done < "$B/nuevos.txt"

# Archivos generados fuera de la configuración
rm -f "$HOME/.cache/fastfetch/logo-n.png" "$HOME/.cache/fastfetch/logo-m.png" \
      "$HOME/.cache/fastfetch/punto.png" "$HOME/.cache/fastfetch/bandera.png" \
      "$HOME/.cache/fastfetch/logo-n-colores"
rmdir "$HOME/.cache/fastfetch" 2>/dev/null

if [ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]; then
    hyprctl reload >/dev/null
    setsid -f "$CONFIG/waybar/launch.sh" >/dev/null 2>&1 </dev/null
    setsid -f "$CONFIG/nwg-dock-hyprland/launch.sh" >/dev/null 2>&1 </dev/null
    swaync-client -rs >/dev/null 2>&1
fi
echo "Listo."
EOF
chmod +x "$BACKUP/restaurar.sh"

# 5. Recargar
if [ "${NO_RELOAD:-0}" != "1" ] && [ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]; then
    info "Recargando Hyprland, Waybar, dock y notificaciones"
    hyprctl reload >/dev/null
    setsid -f "$CONFIG/waybar/launch.sh" >/dev/null 2>&1 </dev/null
    setsid -f "$CONFIG/nwg-dock-hyprland/launch.sh" >/dev/null 2>&1 </dev/null
    swaync-client -rs >/dev/null 2>&1 || true
    pkill -USR1 -x kitty 2>/dev/null
    detener_led
    setsid -f "$CONFIG/hypr/scripts/mic-led.sh" >/dev/null 2>&1 </dev/null
else
    aviso "No se recargó nada: los cambios se aplican al reiniciar la sesión."
fi

info "Instalación completa. Para deshacerla: bash $BACKUP/restaurar.sh"
