// "Ojo que se abre de golpe": lo lanza salvapantallas.sh cuando hay actividad.
// Arranca negro (tapa el cierre del carrusel), se abre rápido con la misma
// elipse del parpadeo y deja la pantalla apenas oscurecida y difuminada
// (blur de Hyprland sobre esta capa), que se aclara como al despertarse.
import Quickshell
import Quickshell.Wayland
import QtQuick

ShellRoot {
    PanelWindow {
        id: ventana
        WlrLayershell.layer: WlrLayer.Overlay
        WlrLayershell.namespace: "despertar"
        WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
        exclusionMode: WlrLayershell.Ignore
        color: "transparent"
        anchors { top: true; bottom: true; left: true; right: true }

        property real apertura: 0.0      // 0 = cerrado, 1 = abierto del todo
        property real velo: 0.35         // oscurecido/difuminado de toda la pantalla
        onAperturaChanged: parpados.requestPaint()
        onVeloChanged: parpados.requestPaint()

        Canvas {
            id: parpados
            anchors.fill: parent
            renderTarget: Canvas.FramebufferObject
            onPaint: {
                const ctx = getContext("2d");
                const w = width, h = height;
                ctx.reset();
                ctx.fillStyle = "black";
                ctx.fillRect(0, 0, w, h);
                ctx.globalCompositeOperation = "destination-out";
                if (ventana.apertura > 0.002) {
                    const rx = w * 0.78, ry = Math.max(1, h * 0.80 * ventana.apertura);
                    ctx.save();
                    ctx.translate(w / 2, h / 2);
                    ctx.scale(rx / ry, 1);
                    const g = ctx.createRadialGradient(0, 0, ry * 0.70, 0, 0, ry);
                    g.addColorStop(0, "rgba(0,0,0," + (1 - ventana.velo) + ")");
                    g.addColorStop(1, "rgba(0,0,0,0)");
                    ctx.fillStyle = g;
                    ctx.beginPath(); ctx.arc(0, 0, ry, 0, 2 * Math.PI); ctx.fill();
                    ctx.restore();
                }
                // al terminar de abrirse, las esquinas también se aclaran (sin salto)
                const bordes = Math.max(0, (ventana.apertura - 0.55) / 0.45) * (1 - ventana.velo);
                if (bordes > 0) {
                    ctx.fillStyle = "rgba(0,0,0," + bordes + ")";
                    ctx.fillRect(0, 0, w, h);
                }
            }
        }

        SequentialAnimation {
            running: true
            PauseAnimation { duration: 180 }            // el script cierra el carrusel detrás del negro
            NumberAnimation { target: ventana; property: "apertura"; to: 1.0; duration: 380; easing.type: Easing.OutCubic }
            NumberAnimation { target: ventana; property: "velo"; to: 0.0; duration: 520; easing.type: Easing.InQuad }
            ScriptAction { script: Qt.quit() }
        }
    }
}
