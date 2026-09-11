#!/usr/bin/env bash
# LED de la tecla de micrófono sincronizado con el mute de PipeWire:
#   micrófono activo  -> LED encendido
#   micrófono muteado -> LED apagado
# Se controla vía logind (SetBrightness), sin necesidad de root.

LED="platform::micmute"

# Una sola instancia
exec 9>"${XDG_RUNTIME_DIR:-/tmp}/mic-led.lock"
flock -n 9 || exit 0

ultimo=""

set_led() {
    busctl call org.freedesktop.login1 /org/freedesktop/login1/session/auto \
        org.freedesktop.login1.Session SetBrightness ssu leds "$LED" "$1" >/dev/null 2>&1
}

actualizar() {
    local estado valor
    estado=$(pactl get-source-mute @DEFAULT_SOURCE@ 2>/dev/null)
    case "$estado" in
        *yes*) valor=0 ;;
        *no*)  valor=1 ;;
        *)     return ;;
    esac
    if [[ "$valor" != "$ultimo" ]]; then
        set_led "$valor" && ultimo="$valor"
    fi
}

# Al iniciar, escribir 0 quita el trigger "audio-micmute" del kernel (que se
# reactiva en cada arranque); así el LED queda controlado solo por este script.
set_led 0

while true; do
    actualizar
    # Reacciona a cambios de fuentes (mute) y del servidor (cambio de micrófono predeterminado)
    while read -r evento; do
        case "$evento" in
            *"on source #"* | *"on server"*) actualizar ;;
        esac
    done < <(pactl subscribe 2>/dev/null)
    # Si PipeWire se reinicia, esperar y volver a suscribirse
    sleep 2
done
