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
         "$CONFIG/fastfetch/centrado.sh" "$CONFIG/hypr/scripts/salvapantallas.sh" \
         "$CONFIG/hypr/scripts/parpadeo.sh" \
         "$CONFIG/hypr/scripts/screenshot.sh" "$CONFIG/hypr/scripts/reloj-bloqueo.py" \
         "$CONFIG/hypr/scripts/wallpaper-inicio.sh" "$CONFIG/hypr/scripts/rofi-wallpaper.sh"

# Salvapantallas: el carrusel necesita numpy, scipy y pillow; el script, jq
if ! python3 -c "import numpy, scipy, PIL" 2>/dev/null; then
    aviso "Faltan módulos de Python para el salvapantallas (sudo pacman -S python-numpy python-scipy python-pillow)."
fi
command -v jq >/dev/null || aviso "Falta jq, que usa el salvapantallas (sudo pacman -S jq)."

# Piezas animadas de la consola. El generador deja también una N quieta en
# waybar/assets/: si no existía, se anota como archivo nuevo para que
# restaurar.sh la borre al deshacer la instalación.
[ -e "$CONFIG/waybar/assets/logo-n.png" ] || echo "waybar/assets/logo-n.png" >> "$BACKUP/nuevos.txt"
if python3 -c "import PIL" 2>/dev/null; then
    python3 "$CONFIG/fastfetch/logo-n.py" >/dev/null && info "N, M, punto y bandera generados en ~/.cache/fastfetch/"
else
    aviso "Falta python-pillow: no se pudieron generar las piezas animadas (sudo pacman -S python-pillow)."
fi

# 4. Rutas de hyprlock
sed -i --follow-symlinks "s#__HOME__#$HOME#g" "$CONFIG/hypr/hyprlock.conf"
for img in kcd_fondo.png vault_boy.png; do
    [ -f "$HOME/Pictures/pantalla_bloqueo/$img" ] ||
        aviso "Falta ~/Pictures/pantalla_bloqueo/$img (usada por la pantalla de bloqueo; ver README)."
done

# 5. Ajustes que antes había que hacer a mano en archivos grandes de ML4W (no
#    incluidos en el repositorio). Cada uno se respalda aparte y no hace nada
#    si ya está aplicado (se puede reinstalar sin duplicar nada) ni si el
#    archivo no tiene la línea esperada (por ejemplo, por otra versión de ML4W).
mkdir -p "$BACKUP/manual"

# 5.1 Pintura al azar al iniciar, encadenada antes de que ML4W aplique la suya
AUTOSTART="$CONFIG/hypr/conf/autostart.conf"
if [ -f "$AUTOSTART" ] && ! grep -q "wallpaper-inicio.sh" "$AUTOSTART"; then
    cp -L "$AUTOSTART" "$BACKUP/manual/autostart.conf"
    sed -i --follow-symlinks -E \
        's|^exec-once[[:space:]]*=[[:space:]]*~/\.config/ml4w/scripts/ml4w-autostart[[:space:]]*$|exec-once = bash -c "~/.config/hypr/scripts/wallpaper-inicio.sh; ~/.config/ml4w/scripts/ml4w-autostart"|' \
        "$AUTOSTART"
    if grep -q "wallpaper-inicio.sh" "$AUTOSTART"; then
        info "autostart.conf: pintura al azar encadenada antes de ml4w-autostart"
    else
        rm -f "$BACKUP/manual/autostart.conf"
        aviso "autostart.conf no tiene la línea esperada de ml4w-autostart: agregá a mano la pintura al azar (ver README)."
    fi
fi

# 5.2 Que las piezas de la consola se regeneren con cada pintura
MATUGEN="$CONFIG/matugen/config.toml"
if [ -f "$MATUGEN" ] && ! grep -q 'templates.logo_n' "$MATUGEN"; then
    cp -L "$MATUGEN" "$BACKUP/manual/config.toml"
    cat >> "$MATUGEN" <<'TOML'

[templates.logo_n]
input_path = '~/.config/matugen/templates/logo-n-colores'
output_path = '~/.cache/fastfetch/logo-n-colores'
post_hook = 'python3 ~/.config/fastfetch/logo-n.py'
TOML
    info "matugen: las piezas de la consola van a regenerarse con cada pintura"
fi

# 5.3 Halo en la ventana activa (una selección de preset más entre las que ya trae ML4W)
WINDOW="$CONFIG/hypr/conf/window.conf"
DECORATION="$CONFIG/hypr/conf/decoration.conf"
if [ -f "$WINDOW" ] && ! grep -q "windows/glow.conf" "$WINDOW"; then
    cp -L "$WINDOW" "$BACKUP/manual/window.conf"
    echo "source = ~/.config/hypr/conf/windows/glow.conf" > "$WINDOW"
fi
if [ -f "$DECORATION" ] && ! grep -q "decorations/rounding-all-blur-glow.conf" "$DECORATION"; then
    cp -L "$DECORATION" "$BACKUP/manual/decoration.conf"
    echo "source = ~/.config/hypr/conf/decorations/rounding-all-blur-glow.conf" > "$DECORATION"
fi
if [ -f "$BACKUP/manual/window.conf" ] || [ -f "$BACKUP/manual/decoration.conf" ]; then
    info "Halo en la ventana activa activado"
fi

# 5.4 Selector de fondo de pantalla por teclado en Super+Ctrl+W
KEYBINDINGS="$CONFIG/hypr/conf/keybindings/default.conf"
if [ -f "$KEYBINDINGS" ] && ! grep -q "rofi-wallpaper.sh" "$KEYBINDINGS"; then
    cp -L "$KEYBINDINGS" "$BACKUP/manual/default.conf"
    sed -i --follow-symlinks -E \
        's|^(bind = \$mainMod CTRL, W, exec,) \$SCRIPTS/ml4w-wallpaper-app([[:space:]].*)?$|\1 ~/.config/hypr/scripts/rofi-wallpaper.sh                  # Open wallpaper selector (teclado: flechas + Enter)|' \
        "$KEYBINDINGS"
    if grep -q "rofi-wallpaper.sh" "$KEYBINDINGS"; then
        info "Super+Ctrl+W: selector de fondo de pantalla por teclado"
    else
        rm -f "$BACKUP/manual/default.conf"
        aviso "No se encontró el atajo de Super+Ctrl+W en default.conf: cambialo a mano (ver README)."
    fi
fi

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

# Deshace los ajustes automáticos en archivos grandes de ML4W (solo los que
# este respaldo realmente tocó: los que no se aplicaron no dejaron copia aquí)
if [ -d "$B/manual" ]; then
    [ -f "$B/manual/autostart.conf" ] && cp "$B/manual/autostart.conf" "$CONFIG/hypr/conf/autostart.conf" && echo "restaurado (manual): autostart.conf"
    [ -f "$B/manual/config.toml" ] && cp "$B/manual/config.toml" "$CONFIG/matugen/config.toml" && echo "restaurado (manual): matugen/config.toml"
    [ -f "$B/manual/window.conf" ] && cp "$B/manual/window.conf" "$CONFIG/hypr/conf/window.conf" && echo "restaurado (manual): window.conf"
    [ -f "$B/manual/decoration.conf" ] && cp "$B/manual/decoration.conf" "$CONFIG/hypr/conf/decoration.conf" && echo "restaurado (manual): decoration.conf"
    [ -f "$B/manual/default.conf" ] && cp "$B/manual/default.conf" "$CONFIG/hypr/conf/keybindings/default.conf" && echo "restaurado (manual): keybindings/default.conf"
fi

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
    pkill -x hypridle; setsid -f hypridle >/dev/null 2>&1 </dev/null
fi
rm -rf "$HOME/.cache/salvapantallas"
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
    pkill -x hypridle; setsid -f hypridle >/dev/null 2>&1 </dev/null     # toma el nuevo hypridle.conf
    # Quickshell no recarga solo el menú de encendido (la luna): se reinicia su instancia principal
    qs kill -p "$CONFIG/quickshell/shell.qml" >/dev/null 2>&1 && (cd "$HOME" && setsid -f qs >/dev/null 2>&1 </dev/null)
    detener_led
    setsid -f "$CONFIG/hypr/scripts/mic-led.sh" >/dev/null 2>&1 </dev/null
else
    aviso "No se recargó nada: los cambios se aplican al reiniciar la sesión."
fi

# 6. Tema de GRUB (opcional: toca el arranque, así que solo se instala si se contesta que sí)
#    GRUB_TEMA=si / GRUB_TEMA=no evita la pregunta. Sin terminal interactiva, no se instala.
RESPUESTA_GRUB="${GRUB_TEMA:-}"
if [ -z "$RESPUESTA_GRUB" ] && [ -t 0 ] && command -v grub-mkconfig >/dev/null && [ -e /boot/grub/grub.cfg ]; then
    echo
    info "Opcional: tema de GRUB N.M. (la pantalla de arranque se corrompe cada segundo; Linux primero, Windows 11 segundo; 10 s)."
    aviso "Toca el arranque: pide sudo, respalda, verifica antes de aplicar y deja un script para deshacerlo."
    read -r -p "¿Instalar el tema de GRUB? [s/N] " RESPUESTA_GRUB
fi
case "$RESPUESTA_GRUB" in
    s|S|si|sí|Si|Sí)
        sudo bash "$REPO/grub/instalar.sh" || aviso "El tema de GRUB no se instaló: el arranque quedó como estaba." ;;
    *)
        info "Tema de GRUB: no se instaló. Para instalarlo más adelante: sudo bash $REPO/grub/instalar.sh" ;;
esac

info "Instalación completa. Para deshacerla: bash $BACKUP/restaurar.sh"
