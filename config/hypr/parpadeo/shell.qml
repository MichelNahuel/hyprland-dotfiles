// Efecto de "ojo que se duerme" al pasar a inactivo (lo lanza hypridle).
// Dibuja una capa negra encima de todo con una abertura elíptica —los párpados—
// que se va cerrando: se entrecierra, se abre de golpe resistiéndose, vuelve a
// caer y finalmente se cierra. Queda cerrado hasta que haya actividad.
import Quickshell
import Quickshell.Wayland
import QtQuick

ShellRoot {
    PanelWindow {
        id: ventana
        WlrLayershell.layer: WlrLayer.Overlay
        WlrLayershell.namespace: "parpadeo"
        WlrLayershell.keyboardFocus: WlrKeyboardFocus.Exclusive   // una tecla también lo cancela
        exclusionMode: WlrLayershell.Ignore
        color: "transparent"
        anchors { top: true; bottom: true; left: true; right: true }

        // 1 = ojo abierto del todo, 0 = cerrado
        property real apertura: 1.0
        onAperturaChanged: parpados.requestPaint()

        Canvas {
            id: parpados
            anchors.fill: parent
            opacity: 0
            renderTarget: Canvas.FramebufferObject
            onPaint: {
                const ctx = getContext("2d");
                const w = width, h = height;
                ctx.reset();
                ctx.globalCompositeOperation = "source-over";
                ctx.fillStyle = "black";
                ctx.fillRect(0, 0, w, h);
                if (ventana.apertura <= 0.002) return;
                // la abertura del ojo: una elipse ancha cuyo alto se achica al cerrar
                const rx = w * 0.78;
                const ry = Math.max(1, h * 0.80 * ventana.apertura);
                ctx.globalCompositeOperation = "destination-out";
                ctx.save();
                ctx.translate(w / 2, h / 2);
                ctx.scale(rx / ry, 1);
                // borde suave: el párpado no corta seco, sombrea
                const g = ctx.createRadialGradient(0, 0, ry * 0.78, 0, 0, ry);
                g.addColorStop(0, "rgba(0,0,0,1)");
                g.addColorStop(1, "rgba(0,0,0,0)");
                ctx.fillStyle = g;
                ctx.beginPath();
                ctx.arc(0, 0, ry, 0, 2 * Math.PI);
                ctx.fill();
                ctx.restore();
            }
        }

        SequentialAnimation {
            running: true
            // los párpados empiezan a pesar
            ParallelAnimation {
                NumberAnimation { target: parpados; property: "opacity"; from: 0; to: 1; duration: 700 }
                NumberAnimation { target: ventana; property: "apertura"; from: 1.0; to: 0.55; duration: 900; easing.type: Easing.InOutSine }
            }
            PauseAnimation { duration: 250 }
            // se abre de golpe, resistiéndose
            NumberAnimation { target: ventana; property: "apertura"; to: 0.85; duration: 320; easing.type: Easing.OutQuad }
            PauseAnimation { duration: 500 }
            // vuelve a caer, más
            NumberAnimation { target: ventana; property: "apertura"; to: 0.28; duration: 1000; easing.type: Easing.InOutSine }
            PauseAnimation { duration: 420 }
            NumberAnimation { target: ventana; property: "apertura"; to: 0.58; duration: 380; easing.type: Easing.OutQuad }
            PauseAnimation { duration: 330 }
            // se duerme
            NumberAnimation { target: ventana; property: "apertura"; to: 0.0; duration: 1300; easing.type: Easing.InQuad }
        }

        // mover el mouse o apretar una tecla lo cierra: salvapantallas.sh lo nota y cancela todo
        property bool armado: false
        Timer { interval: 1200; running: true; onTriggered: ventana.armado = true }   // margen: al apretar la luna la mano sigue en el mouse
        // un temblor de la mano no cuenta: hay que mover el mouse de verdad
        property real x0: -1
        property real y0: -1
        MouseArea {
            anchors.fill: parent
            hoverEnabled: true
            onPositionChanged: (m) => {
                if (ventana.x0 < 0 || !ventana.armado) { ventana.x0 = m.x; ventana.y0 = m.y; return }
                if (Math.hypot(m.x - ventana.x0, m.y - ventana.y0) > 40) Qt.quit()
            }
            onPressed: Qt.quit()
        }
        Item {
            anchors.fill: parent
            focus: true
            Keys.onPressed: if (ventana.armado) Qt.quit()   // con Super+L la tecla recién soltada no cuenta
        }
    }
}
