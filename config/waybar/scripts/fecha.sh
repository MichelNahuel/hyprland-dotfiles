#!/usr/bin/env bash
# Fecha para Waybar con el día en español: "Vie 11/09 15:23"
# Salida continua: imprime una línea solo cuando cambia el minuto.

dias=(Dom Lun Mar Mie Jue Vie Sab)
anterior=""

while true; do
    printf -v ahora '%(%w %d/%m %H:%M)T' -1
    if [[ "$ahora" != "$anterior" ]]; then
        read -r w fecha hora <<<"$ahora"
        printf '%s %s %s\n' "${dias[$w]}" "$fecha" "$hora"
        anterior="$ahora"
    fi
    sleep 1
done
