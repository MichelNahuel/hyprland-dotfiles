#!/usr/bin/env bash
# Salvapantallas: parpadeo → carrusel de próceres (una vuelta) → bloqueo → pantalla apagada.
# Lo lanzan hypridle (8 min sin actividad) y el botón de la luna del menú de apagado.
#   salvapantallas.sh          arranca (si ya está corriendo o la sesión está bloqueada, no hace nada)
#   salvapantallas.sh detener  lo corta sin animación
# Si se toca una tecla o se mueve el mouse, se cancela con la animación del ojo que se abre.

APAGAR_TRAS=60                                   # segundos entre el bloqueo y apagar la pantalla
BATERIA_MINIMA=20                                # con esta carga o menos, sin cargador: bloquea sin animación
HYPR="$HOME/.config/hypr"
ESTADO="${XDG_RUNTIME_DIR:-/tmp}/salvapantallas"
CLASE="salvapantallas"

detener() {
    [ -f "$ESTADO/pid" ] && kill "$(cat "$ESTADO/pid")" 2>/dev/null
    qs kill -p "$HYPR/parpadeo" >/dev/null 2>&1
    hyprctl clients -j | jq -r ".[] | select(.class == \"$CLASE\") | .pid" | xargs -r kill 2>/dev/null
    rm -rf "$ESTADO"
}

case "${1:-}" in
    detener) detener; exit 0 ;;
    actividad)                                   # hypridle avisa que volvió la actividad
        [ -d "$ESTADO" ] && [ ! -s "$ESTADO/resultado" ] && echo actividad > "$ESTADO/resultado"
        exit 0 ;;
    _correr) ;;                                  # uso interno (proceso separado de hypridle/quickshell)
    *)
        pidof hyprlock >/dev/null && exit 0      # ya bloqueada
        [ -f "$ESTADO/pid" ] && kill -0 "$(cat "$ESTADO/pid")" 2>/dev/null && exit 0
        setsid -f "$0" _correr >/dev/null 2>&1
        exit 0 ;;
esac

mkdir -p "$ESTADO"; echo $$ > "$ESTADO/pid"

# sin notificaciones mientras corre: "no molestar" de swaync, y al terminar vuelve como estaba
NOTIF_APAGADAS=0
if [ "$(swaync-client -D 2>/dev/null)" = "false" ]; then
    swaync-client -dn >/dev/null 2>&1; NOTIF_APAGADAS=1
fi
devolver_notificaciones() { [ "$NOTIF_APAGADAS" = 1 ] && swaync-client -df >/dev/null 2>&1; NOTIF_APAGADAS=0; }
trap devolver_notificaciones EXIT
REGISTRO="$HOME/.cache/salvapantallas/registro.log"; mkdir -p "${REGISTRO%/*}"
anotar() { echo "$(date '+%F %T') $*" >> "$REGISTRO"; }
anotar "inicio"
rm -f "$ESTADO/listo" "$ESTADO/resultado"
dormir() { python3 -c "import time; time.sleep($1)"; }

despertar() {                                    # ojo que se abre de golpe, tapando lo que se cierra
    qs -p "$HYPR/despertar" >/dev/null 2>&1 &
    dormir 0.12
}

bloquear_y_apagar() {                            # bloquea y, al rato, apaga la pantalla si sigue bloqueada
    ${SALVA_BLOQUEO:-loginctl lock-session}
    for _ in $(seq 1 50); do pidof hyprlock >/dev/null && break; dormir 0.1; done
    dormir 1
    [ -n "${KITTY:-}" ] && kill $KITTY 2>/dev/null
    rm -rf "$ESTADO"
    devolver_notificaciones                      # ya bloqueada: la pantalla de bloqueo las tapa
    dormir $APAGAR_TRAS
    pidof hyprlock >/dev/null && { anotar "pantalla apagada"; hyprctl dispatch dpms off; }
    exit 0
}

# 0) batería baja y sin cargador: nada de animación, se bloquea enseguida para ahorrar
for bat in "${SALVA_BATERIAS:-/sys/class/power_supply}"/BAT*; do      # SALVA_BATERIAS: para pruebas
    [ -r "$bat/capacity" ] || continue
    if [ "$(cat "$bat/status")" = "Discharging" ] && [ "$(cat "$bat/capacity")" -le "$BATERIA_MINIMA" ]; then
        anotar "batería baja ($(cat "$bat/capacity")%): bloqueo directo"
        bloquear_y_apagar
    fi
done

# 1) parpadeo: si se interrumpe (tecla o mouse), la capa se cierra sola antes de tiempo
qs kill -p "$HYPR/parpadeo" >/dev/null 2>&1
qs -p "$HYPR/parpadeo" >/dev/null 2>&1 &
PARPADEO=$!
for _ in $(seq 1 58); do
    dormir 0.1
    kill -0 $PARPADEO 2>/dev/null || { anotar "parpadeo interrumpido"; rm -rf "$ESTADO"; exit 0; }
    if [ -s "$ESTADO/resultado" ]; then          # actividad avisada por hypridle
        anotar "parpadeo interrumpido (hypridle)"; qs kill -p "$HYPR/parpadeo" >/dev/null 2>&1; rm -rf "$ESTADO"; exit 0
    fi
done

# 2) con los ojos cerrados, el carrusel arranca detrás del negro
SALVA_LISTO="$ESTADO/listo" SALVA_RESULTADO="$ESTADO/resultado" \
    kitty --class "$CLASE" --start-as fullscreen -o confirm_os_window_close=0 \
          -o background_opacity=1 -o background=#0e1014 -o cursor_shape=block \
          python3 "$HYPR/salvapantallas/carrusel.py" --una-vuelta >/dev/null 2>&1 &
KITTY=$!
for _ in $(seq 1 600); do                     # la primera vez calcula los retratos (hasta 60 s)
    [ -f "$ESTADO/listo" ] && break
    kill -0 $PARPADEO 2>/dev/null || break       # tocaron algo mientras cargaba
    dormir 0.1
done
if ! kill -0 $PARPADEO 2>/dev/null && [ ! -f "$ESTADO/listo" ]; then
    anotar "interrumpido mientras cargaba el carrusel"; kill $KITTY 2>/dev/null; rm -rf "$ESTADO"; exit 0
fi
# mostrar el escritorio especial del carrusel (queda arriba de todo, aunque haya algo a pantalla completa)
[ "$(hyprctl monitors -j | jq -r '.[0].specialWorkspace.name')" = "special:salvapantallas" ] ||
    hyprctl dispatch togglespecialworkspace salvapantallas >/dev/null
hyprctl dispatch focuswindow "class:^${CLASE}\$" >/dev/null
dormir 0.3
anotar "carrusel en pantalla"
qs kill -p "$HYPR/parpadeo" >/dev/null 2>&1

# 3) esperar a que el carrusel termine la vuelta o que haya actividad. También cuenta como
#    actividad que el carrusel deje de ser la ventana activa (p. ej. un atajo cambió de escritorio)
while kill -0 $KITTY 2>/dev/null && [ ! -s "$ESTADO/resultado" ]; do
    dormir 0.25
    if [ "$(hyprctl activewindow -j 2>/dev/null | jq -r '.class // empty')" != "$CLASE" ]; then
        dormir 0.5                                # un parpadeo de foco al abrir no cuenta
        [ "$(hyprctl activewindow -j 2>/dev/null | jq -r '.class // empty')" != "$CLASE" ] &&
            [ ! -s "$ESTADO/resultado" ] && echo actividad > "$ESTADO/resultado"
    fi
done
RESULTADO=$(cat "$ESTADO/resultado" 2>/dev/null)
anotar "carrusel terminó: ${RESULTADO:-ventana cerrada}"

if [ "$RESULTADO" = "fin" ]; then
    # 4) se desvaneció el pingüino: bloquear (tapa el carrusel) y al rato apagar la pantalla
    bloquear_y_apagar
fi

# actividad (o la ventana se cerró): el ojo se abre de golpe
despertar
kill $KITTY 2>/dev/null
rm -rf "$ESTADO"
