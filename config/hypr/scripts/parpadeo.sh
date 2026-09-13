#!/usr/bin/env bash
# Efecto de parpadeo al pasar a inactivo. Lo usa hypridle:
#   parpadeo.sh start  → cierra los ojos
#   parpadeo.sh stop   → los abre (quita la capa)
CONF="$HOME/.config/hypr/parpadeo"
case "${1:-start}" in
  start) qs kill -p "$CONF" >/dev/null 2>&1; qs -p "$CONF" -d >/dev/null 2>&1 ;;
  stop)  qs kill -p "$CONF" >/dev/null 2>&1 ;;
  *)     echo "uso: $0 start|stop" >&2; exit 1 ;;
esac
