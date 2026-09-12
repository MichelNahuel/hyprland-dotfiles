# hyprland-dotfiles

Personalización minimalista y "tecno" para [ML4W Dotfiles](https://github.com/mylinuxforwork/dotfiles)
sobre **Hyprland**, pensada para contrastar con fondos de **pinturas históricas y antiguas**:
la interfaz se vuelve translúcida, plana y de líneas finas para que el cuadro sea el protagonista.

![Barra superior](capturas/barra.png)

![La N animada de la consola](capturas/consola.png)

## Qué incluye

| Componente | Cambio |
|---|---|
| **Barra superior** (Waybar, tema `ml4w-transparent-centered`) | Pegada al borde, plana, translúcida (12%) con blur, línea inferior fina, 34 px de alto. El logo de ML4W se reemplaza por la marca `N.M.` en JetBrainsMono. |
| **Fecha** | `Vie 11/09 16:27` a la izquierda, con el día en español (`Lun Mar Mie Jue Vie Sab Dom`) sin depender de locales instalados. Clic abre el calendario. |
| **Íconos de la barra** | Glifos Material Design de contorno de **JetBrainsMono Nerd Font** (volumen, wifi, batería, campana, etc.). Sin quicklinks. |
| **Micrófono** | Ícono de micrófono tachado en la barra cuando está muteado. |
| **LED de la tecla de micrófono** | Se apaga cuando el micrófono está muteado (sincronizado con PipeWire, sin root). |
| **Dock** (nwg-dock-hyprland) | Tema `custom`: translúcido, esquinas rectas, borde fino, flotante, con blur. |
| **Notificaciones** (swaync) | Tema `custom`: translúcidas (5%), esquinas rectas, blur que muestra lo que hay detrás (sin xray). |
| **Cursor** | No salta al centro de la ventana al enfocarla (`cursor:no_warps`). |
| **Pantalla de bloqueo** (hyprlock) | Borde de la foto, hora, usuario y campo de contraseña en crema `#e6dfcf` translúcido. |
| **Terminal** (kitty) | Tipografía legible (10), más aire alrededor del texto (18) y cursor en barra fina. |
| **Prompt** (oh-my-posh) | Dos líneas con marco fino: `┌─ ruta ── rama` y `└─›`, con la flecha en rojo si el comando falló. |
| **Bienvenida** (fastfetch) | Lista con el mismo marco fino, sin íconos, y una **N animada** hecha con caracteres. |
| **Wallpaper** | Una pintura al azar en cada arranque, aplicada por ML4W (sin carreras ni `sleep`). |

### La N animada

El logo de fastfetch es una N de "andamio" dibujada con `| / \ _ ▔`:

```
_____        ___
|/|\\\       |/|
|\| \\\      |\|
|/|  \\\     |/|
|\|   \\\    |\|
|/|    \\\   |/|
|\|     \\\  |\|
|/|      \\\ |/|
|\|       \\\|\|
▔▔▔        ▔▔▔▔▔
```

La recorren **salvas de cuatro olas** que suben de abajo hacia arriba, una detrás de otra,
separadas por una fila. Cada ola hace avanzar una fase a la fila que toca, y cada carácter
sigue el ciclo de su papel original:

```
rieles      |  ->  /  ->  -  ->  \  ->  |     (vuelta completa en 4 olas)
andamio     /  ->  \  ->  /  ->  \          (y al revés si nació \)
diagonal    \  ->  /  ->  \  ->  /
remates     _  ->  -  ->  _  ->  -          (lo mismo el ▔ de abajo)
```

Como la salva tiene cuatro olas, al terminar de pasar cada fila volvió exactamente a su lugar
y la N queda entera. Mientras la banda viaja, el resto de la letra se mantiene legible.

La genera `config/fastfetch/logo-n.py` como **APNG** en `~/.cache/fastfetch/logo-n.png`, y
kitty la reproduce en bucle sin bloquear el shell (fastfetch la muestra con `--logo-type kitty-icat`,
disponible desde fastfetch 2.34). Los colores salen de la paleta de matugen, así que la N
acompaña a la pintura de fondo.

> El mismo script deja una versión quieta y blanca en `~/.config/waybar/assets/logo-n.png`, por si
> se la quiere usar como logo de la barra. No viene activada: a 34 px de alto el andamio se agrisa
> y se pierde, así que en la barra va la marca `N.M.` como texto. El CSS tiene anotado cómo cambiarlo.

## Requisitos

- Arch Linux (o derivada) con **Hyprland ≥ 0.53** (probado en 0.56.2; usa la sintaxis `layerrule = …, match:namespace …`).
- **ML4W Dotfiles** instalados (versión *stable*), con el tema de Waybar `ml4w-transparent-centered`.
- Paquetes: `waybar`, `swaync`, `nwg-dock-hyprland`, `hyprlock`, `kitty`, `fastfetch` (≥ 2.34),
  `oh-my-posh`, `libpulse` (`pactl`), `ttf-jetbrains-mono-nerd`, `python-pillow` (para generar la N).
- Para el LED de micrófono: una laptop con LED `platform::micmute` (ThinkPad y similares) y `systemd-logind` (viene por defecto).
- La N animada **solo funciona en kitty**.

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
4. Ajusta las rutas de `hyprlock.conf` a tu `$HOME` y genera la N animada.
5. Recarga Hyprland, Waybar, el dock, swaync e inicia el script del LED.

Todo queda aplicado de forma permanente: al encender la computadora, el autostart de ML4W
lanza Waybar, el dock y swaync con estos temas, y `hypr/conf/custom.conf` inicia el script del LED.

> Para instalar sin recargar nada (por ejemplo, desde una TTY): `NO_RELOAD=1 bash install.sh`

### Dos pasos manuales

Estos tocan archivos grandes de ML4W, así que no se incluyen en el repositorio.

**1. Pintura al azar al iniciar.** En `~/.config/hypr/conf/autostart.conf`, reemplazá

```
exec-once = ~/.config/ml4w/scripts/ml4w-autostart
```

por

```
exec-once = bash -c "~/.config/hypr/scripts/wallpaper-inicio.sh; ~/.config/ml4w/scripts/ml4w-autostart"
```

y quitá cualquier otro `exec-once` que cambie el wallpaper al iniciar. El script solo escribe la
pintura elegida en la caché de ML4W; al ir encadenado, la caché ya está lista cuando
`ml4w-autostart` la lee: sin carreras ni `sleep`. Con `Super + Shift + W` se cambia a otra pintura.

**2. Que la N se regenere con cada pintura.** Agregá al final de `~/.config/matugen/config.toml`:

```toml
[templates.logo_n]
input_path = '~/.config/matugen/templates/logo-n-colores'
output_path = '~/.cache/fastfetch/logo-n-colores'
post_hook = 'python3 ~/.config/fastfetch/logo-n.py'
```

Sin este paso la N funciona igual, pero conserva los colores con los que se generó.

### Imágenes (no incluidas)

Por derechos de autor, el repositorio **no** incluye imágenes:

- **Pantalla de bloqueo**: `hyprlock.conf` espera
  `~/Pictures/pantalla_bloqueo/kcd_fondo.png` (fondo, 1920×1080) y
  `~/Pictures/pantalla_bloqueo/vault_boy.png` (foto de perfil). Poné tus imágenes con esos nombres
  o cambiá las rutas `path =` en `~/.config/hypr/hyprlock.conf`.
- **Wallpapers**: la estética está pensada para pinturas (por ejemplo *La Libertad guiando al pueblo*,
  de Delacroix, de dominio público). Poné las tuyas en `~/wallpapers`.

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
| Alto de la barra | mismo archivo → `#workspaces { padding }` y el tamaño de `#custom-ml4w-welcome` |
| Marca `N.M.` de la barra | `waybar/modules.json` (`custom/ml4w-welcome` → `format`) y el bloque `#custom-ml4w-welcome` del CSS |
| Formato de la fecha / días con tilde | `waybar/scripts/fecha.sh` → `'%(%w %d/%m %H:%M)T'` y la lista `dias` |
| Íconos de la barra | `waybar/modules.json` (glifos `md-*` de Nerd Fonts: <https://www.nerdfonts.com/cheat-sheet>) |
| Transparencia de notificaciones | `swaync/themes/custom/style.css` → `alpha(@surface_container_lowest, 0.05)` |
| Estilo del dock | `nwg-dock-hyprland/themes/custom/style.css` |
| Tipografía y márgenes de la terminal | `kitty/custom.conf` → `font_size`, `window_padding_width` |
| Prompt | `ohmyposh/marco.toml` |
| Datos de la bienvenida | `fastfetch/config.jsonc` |
| Velocidad de la N y tamaño | `fastfetch/logo-n.py` → `MS_PASO` (paso de la ola), `MS_CIERRE` (pausa con la N entera), `COLS`, `FILAS` (si cambiás el tamaño, actualizá `width`/`height` en `fastfetch/config.jsonc`) |
| LED encendido al mutear (al revés) | `hypr/scripts/mic-led.sh` → intercambiar `valor=0` / `valor=1` |
| Colores de la pantalla de bloqueo | `hypr/hyprlock.conf` → `rgba(e6dfcf..)` |

Después de editar: `Super + Shift + B` recarga Waybar, `swaync-client -rs` recarga las notificaciones,
`hyprctl reload` recarga Hyprland y `pkill -USR1 -x kitty` recarga la terminal.

## Notas

- Si actualizás ML4W Dotfiles, algunos archivos (`waybar/modules.json`, el `config` del tema de Waybar,
  `hyprlock.conf`, `fastfetch/config.jsonc`) pueden volver a los originales: volvé a ejecutar `bash install.sh`.
- Si cambiás el estilo de decoración desde la app de ML4W, copiá las líneas de `nwg-dock` de
  `hypr/conf/decorations/rounding-all-blur-no-shadows.conf` al nuevo archivo para mantener el blur del dock.
- Si cambiás el tema de Waybar con el selector de ML4W, la barra deja de usar esta configuración.
- El prompt se carga desde `~/.config/bashrc/custom/20-customization`, el mecanismo que ML4W
  reserva para reemplazar sus propios archivos.

## Créditos

Basado en [ML4W Dotfiles](https://github.com/mylinuxforwork/dotfiles) de Stephan Raabe (GPL-3.0).
Los archivos de `config/` derivados de ML4W mantienen esa licencia.
