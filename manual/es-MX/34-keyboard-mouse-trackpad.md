# Teclado, mouse, panel táctil

Hyprland te permite configurar todas tus entradas con gran detalle. Puedes cambiar la repetición del teclado para que sea supersónicamente rápida o hacer que el panel táctil use desplazamiento natural. Cambias todo en `~/.config/hypr/input.lua`, al que también puedes llegar mediante _Configurar > Entrada_ en el menú de Omarchy (`Super + Space`). Todo lo que definas ahí reemplaza los valores predeterminados de Omarchy.

Aquí hay un ejemplo:

```lua
hl.config({
  input = {
    -- Use multiple keyboard layouts and switch between them with Left Alt + Right Alt
    kb_layout = "us,dk",
    kb_options = "omarchy:shift_caps_compose,grp:alts_toggle",

    -- Change speed of keyboard repeat
    repeat_rate = 40,
    repeat_delay = 600,

    -- Increase sensitivity for mouse/trackpad (default: 0)
    sensitivity = 0.35,

    touchpad = {
      -- Use natural (inverse) scrolling
      natural_scroll = true,

      -- Use two-finger clicks for right-click instead of lower-right corner
      clickfinger_behavior = true,

      -- Control the speed of your scrolling
      scroll_factor = 0.3,
    },
  },
})

-- Scroll faster in the terminal
o.window("(Alacritty|kitty|foot)", { scroll_touchpad = 1.5 })
```

Puedes [ver todas las opciones de entrada](https://wiki.hypr.land/Configuring/Basics/Variables/#input) en el wiki de Hyprland para entradas.

CapsLock funciona como un Caps Lock normal, y `Shift + CapsLock` es la tecla de composición para los [emojis rápidos](07-hotkeys.md#quick-emojis) y [otros autocompletados](07-hotkeys.md#quick-completions). Si prefieres tener la tecla de composición en otro lugar, reemplaza `omarchy:shift_caps_compose` en `kb_options`. Por ejemplo, esto mueve la tecla de composición a Right Alt:

```lua
hl.config({
  input = {
    kb_options = "compose:ralt",
  },
})
```

### Gestos del panel táctil

También puedes activar [gestos del panel táctil](https://wiki.hypr.land/Configuring/Advanced-and-Cool/Gestures/), como deslizar con tres dedos para cambiar de espacios de trabajo:

```lua
hl.gesture({ fingers = 3, direction = "horizontal", action = "workspace" })
```

En laptops Dell XPS con un panel táctil háptico, también puedes poner la fuerza del clic en baja, media o alta en _Activar > Hardware > Respuesta háptica_.

### Escribir en chino, japonés y otros idiomas

Cuando el instalador pregunte por tu teclado, selecciona japonés, coreano, chino (simplificado, Pinyin), Taiwán (Zhuyin) o Hong Kong (Cangjie). Omarchy configura automáticamente el teclado y el motor de entrada, incluso en el primer arranque sin conexión. El japonés usa Mozc, el coreano Hangul estándar de dos conjuntos, el chino simplificado Pinyin, Taiwán la distribución Zhuyin estándar de Chewing y Hong Kong Cangjie con formas de caracteres de Hong Kong. Japonés (teclado US) ofrece Mozc con distribución US. Las teclas de Hangul, Zhuyin y Cangjie mantienen sus posiciones estándar aunque escribas letras latinas con Dvorak, Colemak o AZERTY. Si ya agregaste Hangul o Chewing, desmárcalo y vuelve a marcarlo en _Configurar > Escritura > Métodos de entrada_ para mover sus teclas; Omarchy deja intacto un motor que ya usas.

La escritura empieza en modo latino. Presiona `Super + I` para recorrer los métodos de entrada configurados, y `Super + Shift + I` para recorrerlos hacia atrás. Toca `Shift` por sí solo para salir de un método de entrada como Pinyin a letras latinas, y tócalo de nuevo para volver, de la forma en que funcionan Sogou, Microsoft Pinyin y macOS; `Shift` más una letra sigue escribiendo una mayúscula. En los teclados japoneses, 全角/半角 alterna la entrada, 変換 la activa y 無変換 la desactiva. Con coreano, 한/영 alterna Hangul y 한자 convierte a Hanja, tanto si el teclado tiene teclas dedicadas como si envía Right Alt y Right Ctrl, como muchas laptops; por eso aquí no son modificadores comunes, y el dictado de mantener para hablar sigue en F9. `Ctrl + Space` sigue disponible para Tmux y Herdr; `Shift + CapsLock` sigue siendo la tecla de composición.

El indicador de teclado aparece a la derecha de la barra cuando tienes varias distribuciones de teclado o métodos de entrada. Haz clic en él para cambiar de idioma de entrada; el japonés muestra あ para hiragana. Para las opciones de caracteres japoneses, cambia a japonés, escribe una palabra como `nihongo`, y luego presiona Space dos veces. Presiona Enter para aceptar tu elección. Si también tienes varias distribuciones de teclado, haz clic derecho en el indicador para recorrerlas.

Usa _Configurar > Escritura > Distribuciones de teclado_ para seleccionar distribuciones como inglés y francés, de las mismas opciones ofrecidas durante la instalación. Usa _Configurar > Escritura > Métodos de entrada_ para seleccionar qué motores de composición están activos. Ambos selectores se abren dentro del menú de Omarchy con tus selecciones actuales marcadas. Haz clic o presiona Enter para alternar una opción; cada cambio se aplica de inmediato. Deseleccionar un método de entrada lo quita del ciclo sin desinstalarlo; el teclado sigue disponible.

Ejecuta `omarchy setup keyboard` o `omarchy setup input` para abrir los mismos selectores. Para agregar un idioma desde la línea de comandos, usa `omarchy setup input mozc`, `hangul`, `pinyin`, `chewing`, `cangjie5`. Tus teclas personalizadas de cambio se conservan. Para distribuciones o teclas alternativas del motor, instala `fcitx5-configtool` con `omarchy pkg add fcitx5-configtool` y lánzalo desde una terminal. Seleccionar un idioma de entrada no cambia el idioma del escritorio. Quick, Boshiamy y Array vienen en el mismo paquete que Cangjie y aparecen en el selector de métodos de entrada. Elegir japonés, coreano o chino en _Configurar > Idioma_ agrega su método si todavía no tienes ninguno.

Usa `Super + I` para recorrer los métodos de entrada o las distribuciones de teclado, y `Super + Shift + I` para ir en la otra dirección, así que con tres configurados puedes moverte entre dos vecinos. El indicador de entrada aparece a la derecha de la barra solo cuando hay más de un método de entrada o distribución configurado. Este atajo de escritorio funciona junto a tus teclas existentes de cambio de Fcitx; puedes sobrescribirlo en `~/.config/hypr/bindings.lua`. Los motores de entrada y las secuencias de composición usan el servicio [Fcitx5](https://fcitx-im.org/) que ya se ejecuta en cada sesión.

### Usar ALT como SUPER

En algunos teclados, no es cómodo usar la tecla meta principal (tecla Windows/cmd) como SUPER. Puedes cambiar esto para que sea ALT en su lugar usando este cambio:

```lua
hl.config({
  input = {
    kb_options = "omarchy:shift_caps_compose,altwin:swap_alt_win",
  },
})
```
