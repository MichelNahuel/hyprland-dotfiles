# hyprland-dotfiles

Personalización minimalista y "tecno" para [ML4W Dotfiles](https://github.com/mylinuxforwork/dotfiles)
sobre **Hyprland**, pensada para contrastar con fondos de **pinturas históricas y antiguas**:
la interfaz se vuelve translúcida, plana y de líneas finas para que el cuadro sea el protagonista.

![Barra superior](capturas/barra.png)

## Qué incluye

| Componente | Cambio |
|---|---|
| **Barra superior** (Waybar, tema `ml4w-transparent-centered`) | Pegada al borde, plana, translúcida (12%) con blur, línea inferior fina, 34 px de alto. |
| **Fecha** | `Vie 11/09 16:27` a la izquierda, con el día en español (`Lun Mar Mie Jue Vie Sab Dom`) sin depender de locales instalados. Clic abre el calendario. |
| **Íconos de la barra** | Glifos Material Design de contorno de **JetBrainsMono Nerd Font** (volumen, wifi, batería, campana, etc.). Sin quicklinks. |
| **Micrófono** | Ícono de micrófono tachado en la barra cuando está muteado. |
| **LED de la tecla de micrófono** | Se apaga cuando el micrófono está muteado (sincronizado con PipeWire, sin root). |
| **Dock** (nwg-dock-hyprland) | Tema `custom`: translúcido, esquinas rectas, borde fino, flotante, con blur. |
| **Notificaciones** (swaync) | Tema `custom`: translúcidas (5%), esquinas rectas, blur que muestra lo que hay detrás (sin xray). |
| **Cursor** | No salta al centro de la ventana al enfocarla (`cursor:no_warps`). |
| **Pantalla de bloqueo** (hyprlock) | Borde de la foto, hora, usuario y campo de contraseña en crema `#e6dfcf` translúcido. |

## Requisitos

- Arch Linux (o derivada) con **Hyprland ≥ 0.53** (probado en 0.56.2; usa la sintaxis `layerrule = …, match:namespace …`).
- **ML4W Dotfiles** instalados (versión *stable*), con el tema de Waybar `ml4w-transparent-centered`.
- Paquetes: `waybar`, `swaync`, `nwg-dock-hyprland`, `hyprlock`, `libpulse` (`pactl`), `ttf-jetbrains-mono-nerd`.
- Para el LED de micrófono: una laptop con LED `platform::micmute` (ThinkPad y similares) y `systemd-logind` (viene por defecto).

## Instalación

```bash
git clone https://github.com/MichelNahuel/hyprland-dotfiles.git
cd hyprland-dotfiles
bash install.sh
```

`install.sh`:

1. Verifica que ML4W esté instalado.
2. Guarda un respaldo de cada archivo que va a reemplazar en `~/backups/hyprland-dotfiles-<fecha>/`
   y anota los archivos nuevos.
3. Copia los archivos de `config/` a `~/.config/` (respetando los symlinks de ML4W).
4. Ajusta las rutas de `hyprlock.conf` a tu `$HOME`.
5. Recarga Hyprland, Waybar, el dock, swaync e inicia el script del LED.

Todo queda aplicado de forma permanente: al encender la computadora, el autostart de ML4W
lanza Waybar, el dock y swaync con estos temas, y `hypr/conf/custom.conf` inicia el script del LED.

> Para instalar sin recargar nada (por ejemplo, desde una TTY): `NO_RELOAD=1 bash install.sh`

### Imágenes (no incluidas)

Por derechos de autor, el repositorio **no** incluye imágenes:

- **Pantalla de bloqueo**: `hyprlock.conf` espera
  `~/Pictures/pantalla_bloqueo/kcd_fondo.png` (fondo, 1920×1080) y
  `~/Pictures/pantalla_bloqueo/vault_boy.png` (foto de perfil). Poné tus imágenes con esos nombres
  o cambiá las rutas `path =` en `~/.config/hypr/hyprlock.conf`.
- **Wallpapers**: la estética está pensada para pinturas (por ejemplo *La Libertad guiando al pueblo*,
  de Delacroix, de dominio público). Usá el selector de wallpapers de ML4W o `awww img <imagen>`.

### Pintura al azar al iniciar (opcional)

Al iniciar, ML4W restaura el último wallpaper guardado en su caché. Si otro script cambia el
wallpaper al mismo tiempo, gana el que termina último (y los colores quedan calculados a partir
de la imagen equivocada). Para que cada arranque muestre una pintura al azar **aplicada por ML4W**
—con los colores de la interfaz generados a partir de esa pintura—, sin carreras ni `sleep`:

1. `install.sh` instala `hypr/scripts/wallpaper-inicio.sh` y ajusta `ml4w/settings/wallpaper-folder`
   a `$HOME/wallpapers`. Poné tus imágenes (`jpg`, `jpeg`, `png`) en la raíz de esa carpeta.
2. En `~/.config/hypr/conf/autostart.conf`, reemplazá la línea

   ```
   exec-once = ~/.config/ml4w/scripts/ml4w-autostart
   ```

   por

   ```
   exec-once = bash -c "~/.config/hypr/scripts/wallpaper-inicio.sh; ~/.config/ml4w/scripts/ml4w-autostart"
   ```

   y quitá cualquier otro `exec-once` que cambie el wallpaper al iniciar.

El script solo escribe la pintura elegida en la caché de ML4W; al ir encadenado, la caché ya está
lista cuando `ml4w-autostart` la lee. Con `Super + Shift + W` se cambia a otra pintura al azar.

## Volver atrás

Cada instalación genera su propio script de restauración, que devuelve los archivos originales
y borra los que se agregaron:

```bash
bash ~/backups/hyprland-dotfiles-<fecha>/restaurar.sh
```

## Personalizar

| Qué | Dónde |
|---|---|
| Transparencia de la barra | `waybar/themes/ml4w-transparent-centered/default/style-custom.css` → `background: alpha(@surface_container_lowest, 0.12)` |
| Formato de la fecha / días con tilde | `waybar/scripts/fecha.sh` → `'%(%w %d/%m %H:%M)T'` y la lista `dias` |
| Íconos de la barra | `waybar/modules.json` (glifos `md-*` de Nerd Fonts: <https://www.nerdfonts.com/cheat-sheet>) |
| Transparencia de notificaciones | `swaync/themes/custom/style.css` → `alpha(@surface_container_lowest, 0.05)` |
| Estilo del dock | `nwg-dock-hyprland/themes/custom/style.css` |
| LED encendido al mutear (al revés) | `hypr/scripts/mic-led.sh` → intercambiar `valor=0` / `valor=1` |
| Colores de la pantalla de bloqueo | `hypr/hyprlock.conf` → `rgba(e6dfcf..)` |

Después de editar: `Super + Shift + B` recarga Waybar, `swaync-client -rs` recarga las notificaciones
y `hyprctl reload` recarga Hyprland.

## Notas

- Si actualizás ML4W Dotfiles, algunos archivos (`waybar/modules.json`, el `config` del tema de Waybar,
  `hyprlock.conf`) pueden volver a los originales: volvé a ejecutar `bash install.sh`.
- Si cambiás el estilo de decoración desde la app de ML4W, copiá las líneas de `nwg-dock` de
  `hypr/conf/decorations/rounding-all-blur-no-shadows.conf` al nuevo archivo para mantener el blur del dock.
- Si cambiás el tema de Waybar con el selector de ML4W, la barra deja de usar esta configuración.

## Créditos

Basado en [ML4W Dotfiles](https://github.com/mylinuxforwork/dotfiles) de Stephan Raabe (GPL-3.0).
Los archivos de `config/` derivados de ML4W mantienen esa licencia.
