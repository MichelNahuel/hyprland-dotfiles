#!/usr/bin/env bash
# Tema de GRUB "N.M." (opcional). Uso: sudo bash grub/instalar.sh [--si]
#
# Toca el arranque, así que va con cuidado:
#   - no toca la partición EFI ni reinstala GRUB (no corre grub-install);
#   - respalda /etc/default/grub y /boot/grub/grub.cfg, y deja un restaurar.sh junto al respaldo;
#   - genera el grub.cfg nuevo APARTE y lo compara entrada por entrada con uno generado con la
#     configuración original (verificar.py); si algo no coincide, deshace todo y no aplica nada;
#   - antes de ponerlo en uso pregunta (salvo con --si).
set -Eeuo pipefail

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GRUB_DIR=/boot/grub
TEMA_DIR="$GRUB_DIR/themes/nm"
DEFAULT=/etc/default/grub
GRUBD=/etc/grub.d
CONFIRMAR=1; [ "${1:-}" = "--si" ] && CONFIRMAR=0

info()  { printf '\033[0;32m::\033[0m %s\n' "$1"; }
aviso() { printf '\033[1;33m!!\033[0m %s\n' "$1"; }
error() { printf '\033[0;31mxx\033[0m %s\n' "$1" >&2; exit 1; }

# 1. Verificaciones (antes de tocar nada)
[ "$(id -u)" = 0 ] || error "Correlo con sudo: sudo bash $AQUI/instalar.sh"
USUARIO="${SUDO_USER:-${PKEXEC_UID:+$(id -nu "$PKEXEC_UID")}}"
USUARIO="${USUARIO:-root}"
CASA="$(getent passwd "$USUARIO" | cut -d: -f6)"
for c in grub-mkconfig grub-script-check grub-mkfont python3 findmnt; do
    command -v "$c" >/dev/null || error "Falta $c."
done
[ -f "$GRUB_DIR/grub.cfg" ] || error "No existe $GRUB_DIR/grub.cfg (¿GRUB instalado en otra ruta?). No se toca nada."
[ -f "$DEFAULT" ] || error "No existe $DEFAULT. No se toca nada."
[ -f "$GRUBD/10_linux" ] || error "No existe $GRUBD/10_linux. No se toca nada."
python3 -c "import PIL" 2>/dev/null || error "Falta python-pillow (sudo pacman -S python-pillow)."
if [ -e "$GRUBD/11_nm_orden" ] || [ -e "$TEMA_DIR" ]; then
    error "Ya hay un tema en $TEMA_DIR o un $GRUBD/11_nm_orden. Para rehacerlo, primero ejecutá el restaurar.sh de la instalación anterior."
fi

# Si GRUB_DEFAULT es un número distinto de 0, cambiar el orden cambiaría qué arranca solo: se deja el orden.
ORDEN=1
DEF_ACTUAL="$(sed -n 's/^GRUB_DEFAULT=["'\'']\{0,1\}\([^"'\'']*\).*/\1/p' "$DEFAULT" | tail -1)"
if [[ "$DEF_ACTUAL" =~ ^[0-9]+$ ]] && [ "$DEF_ACTUAL" != 0 ]; then
    aviso "GRUB_DEFAULT=$DEF_ACTUAL: no cambio el orden del menú para no cambiar qué sistema arranca solo."
    ORDEN=0
fi

# 2. Respaldo
B="$CASA/backups/grub-tema-$(date +%Y-%m-%d_%H%M%S)"
mkdir -p "$B"
cp -a "$DEFAULT" "$B/grub.default.original"
cp -a "$GRUB_DIR/grub.cfg" "$B/grub.cfg.original"
stat -c '%a %n' "$GRUBD"/* > "$B/permisos-grub.d.original"
cp "$AQUI/verificar.py" "$B/"
info "Respaldo en $B"

PERM_LINUX="$(stat -c '%a' "$GRUBD/10_linux")"
PERM_OSPROBER="$( [ -f "$GRUBD/30_os-prober" ] && stat -c '%a' "$GRUBD/30_os-prober" || echo -)"
cat > "$B/restaurar.sh" <<EOF
#!/usr/bin/env bash
# Deshace el tema de GRUB N.M. (con sudo): vuelve /etc/default/grub, /etc/grub.d y grub.cfg como estaban.
set -euo pipefail
[ "\$(id -u)" = 0 ] || { echo "Correlo con sudo: sudo bash \$0"; exit 1; }
install -o root -g root -m 644 "$B/grub.default.original" "$DEFAULT"
rm -f "$GRUBD/11_nm_orden"
chmod $PERM_LINUX "$GRUBD/10_linux"
$( [ "$PERM_OSPROBER" != - ] && echo "chmod $PERM_OSPROBER \"$GRUBD/30_os-prober\"" )
install -o root -g root -m 600 "$B/grub.cfg.original" "$GRUB_DIR/grub.cfg"
rm -rf "$TEMA_DIR" "$GRUB_DIR/grub.cfg.nuevo"
echo "Restaurado el arranque original."
EOF
chmod +x "$B/restaurar.sh"

volver_etc() {
    install -o root -g root -m 644 "$B/grub.default.original" "$DEFAULT"
    rm -f "$GRUBD/11_nm_orden" "$GRUB_DIR/grub.cfg.nuevo"
    chmod "$PERM_LINUX" "$GRUBD/10_linux"
    if [ "$PERM_OSPROBER" != - ]; then chmod "$PERM_OSPROBER" "$GRUBD/30_os-prober"; fi
    rm -rf "$TEMA_DIR"
    chown -R "$USUARIO": "$B"
}
deshacer() {
    set +e; trap - ERR     # deshacer todo lo posible aunque un paso falle
    aviso "Algo falló: dejo todo como estaba. El arranque no cambió."
    volver_etc
    exit 1
}

# 3. grub.cfg de referencia, con la configuración original
info "Generando el menú de referencia (configuración original)"
grub-mkconfig -o "$B/grub.cfg.referencia" 2>&1 | sed 's/^/   /'
trap deshacer ERR

# 4. Tema (datos del hardware de este equipo)
info "Generando el tema"
RES="$(python3 "$AQUI/generar_tema.py" resolucion)"
rm -rf "$B/tema-nm"
python3 "$AQUI/generar_tema.py" tema "$B/tema-nm"
mkdir -p "$GRUB_DIR/themes"
rm -rf "$TEMA_DIR"
cp -r "$B/tema-nm" "$TEMA_DIR"
chown -R root:root "$TEMA_DIR"
chmod -R u=rwX,go=rX "$TEMA_DIR"
info "Tema en $TEMA_DIR ($(ls "$TEMA_DIR" | wc -l) archivos, $RES)"

# 5. /etc/default/grub: tema, resolución, menú visible y 10 s; el resto queda igual
poner() {   # poner VARIABLE valor → reemplaza la línea activa o la agrega al final
    if grep -q "^$1=" "$DEFAULT"; then
        sed -i "s|^$1=.*|$1=$2|" "$DEFAULT"
    else
        printf '%s=%s\n' "$1" "$2" >> "$DEFAULT"
    fi
}
grep -q "Tema N.M." "$DEFAULT" || printf '\n# Tema N.M. (hyprland-dotfiles/grub)\n' >> "$DEFAULT"
poner GRUB_TIMEOUT 10
poner GRUB_TIMEOUT_STYLE menu
poner GRUB_GFXMODE "$RES,auto"
poner GRUB_THEME "\"$TEMA_DIR/theme.txt\""
grep -q '^GRUB_TERMINAL_OUTPUT=.*console' "$DEFAULT" && sed -i 's|^GRUB_TERMINAL_OUTPUT=|#GRUB_TERMINAL_OUTPUT=|' "$DEFAULT"

# 6. Orden del menú: Linux, Windows 11, opciones avanzadas
if [ "$ORDEN" = 1 ]; then
    install -o root -g root -m 755 "$AQUI/11_nm_orden" "$GRUBD/11_nm_orden"
    chmod 644 "$GRUBD/10_linux"
    [ "$PERM_OSPROBER" != - ] && chmod 644 "$GRUBD/30_os-prober"
fi

# 7. Generar aparte y verificar
info "Generando el menú nuevo (aparte, sin reemplazar el que está en uso)"
grub-mkconfig -o "$GRUB_DIR/grub.cfg.nuevo" 2>&1 | sed 's/^/   /'
grub-script-check "$GRUB_DIR/grub.cfg.nuevo"
cp "$GRUB_DIR/grub.cfg.nuevo" "$B/grub.cfg.nuevo"
python3 "$AQUI/verificar.py" "$B/grub.cfg.referencia" "$GRUB_DIR/grub.cfg.nuevo" $( [ "$ORDEN" = 0 ] && echo --sin-orden ) | tee "$B/verificacion.txt"
diff "$B/grub.default.original" "$DEFAULT" > "$B/diff-default.txt" || true
trap - ERR
echo
echo "Cambios en $DEFAULT:"
sed 's/^/   /' "$B/diff-default.txt"
echo

# 8. Aplicar
if [ "$CONFIRMAR" = 1 ]; then
    read -r -p "¿Poner en uso el menú nuevo? El cambio se ve al reiniciar. [s/N] " r
    if [[ ! "$r" =~ ^[sS]$ ]]; then
        volver_etc
        rm -f "$B/restaurar.sh"
        info "No se aplicó nada: el arranque quedó como estaba (el respaldo queda en $B)."
        exit 0
    fi
fi
mv "$GRUB_DIR/grub.cfg.nuevo" "$GRUB_DIR/grub.cfg"
chown -R "$USUARIO": "$B"
info "Listo. Se ve en el próximo arranque."
info "Para deshacerlo: sudo bash $B/restaurar.sh"
