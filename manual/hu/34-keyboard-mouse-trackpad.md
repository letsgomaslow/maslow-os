# Billentyűzet, egér, érintőpad

A Hyprland lehetővé teszi minden bemeneted részletes konfigurálását. A billentyűismétlést szuperszonikusan gyorsra állíthatod, vagy az érintőpadot természetes görgetésre kapcsolhatod. Mindent a `~/.config/hypr/input.lua` fájlban módosítasz, amely az Omarchy menü (`Super + Space`) _Setup > Input_ pontján is elérhető. Bármi, amit ott beállítasz, felülírja az Omarchy alapértelmezéseit.

Íme egy példa:

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

A beviteli beállításokról szóló Hyprland-wikin [az összes beviteli beállítást megtekintheted](https://wiki.hypr.land/Configuring/Basics/Variables/#input).

A CapsLock szokásos Caps Lockként működik, a `Shift + CapsLock` pedig a compose-billentyű a [gyors emojikhoz](07-hotkeys.md#quick-emojis) és [egyéb kiegészítésekhez](07-hotkeys.md#quick-completions). Ha a compose-billentyűt máshová szeretnéd, cseréld ki az `omarchy:shift_caps_compose` értéket a `kb_options`-ben. Például ez a compose-billentyűt a jobb Alt billentyűre mozgatja:

```lua
hl.config({
  input = {
    kb_options = "compose:ralt",
  },
})
```

### Érintőpad-gesztusok

Az [érintőpad-gesztusokat](https://wiki.hypr.land/Configuring/Advanced-and-Cool/Gestures/) is bekapcsolhatod, például a háromujjas csúsztatást munkaterület-váltáshoz:

```lua
hl.gesture({ fingers = 3, direction = "horizontal", action = "workspace" })
```

A haptikus érintőpaddal felszerelt Dell XPS laptopokon a kattintási erőt alacsony, közepes vagy magas értékűre állíthatod az _Trigger > Hardware > Touchpad Haptics_ alatt.

### Gépelés kínai, japán és más nyelveken

Amikor a telepítő billentyűzetet kér, válassz japánt, koreait, kínait (egyszerűsített, Pinyin), Tajvant (Zhuyin) vagy Hongkongot (Cangjie). Az Omarchy automatikusan beállítja a billentyűzetet és a beviteli motort, az első offline indításkor is. A japán Mozcot, a koreai szabványos kétkészletes Hangult, az egyszerűsített kínai Pinyint, Tajvan a Chewing szabványos Zhuyin-kiosztását, Hongkong pedig hongkongi karakteralakokat használó Cangjie-t kap. A japán (US billentyűzet) US-kiosztású Mozcot ad. A Hangul, Zhuyin és Cangjie billentyűk latin Dvorak, Colemak vagy AZERTY gépeléskor is szabványos helyen maradnak. Ha korábban hozzáadtad a Hangult vagy Chewinget, a _Beállítás > Gépelés > Beviteli módok_ alatt vedd ki, majd jelöld be újra a billentyűk áthelyezéséhez; az Omarchy nem módosít már használt motort.

A gépelés latin módban indul. A `Super + I` kombinációval ciklizálhatsz a konfigurált bevitelimódszerek között, a `Super + Shift + I` kombinációval pedig visszafelé. Érintsd meg a `Shift` billentyűt önmagában, hogy kilépj egy olyan bevitelimódszerről, mint a Pinyin, latin betűkre, és ismét érintsd meg a visszalépéshez, ahogyan a Sogou, a Microsoft Pinyin és a macOS működnek; a `Shift` és egy betű továbbra is nagybetűt ír. Japán billentyűzeteken a 全角/半角 kapcsolja az inputot, a 変換 bekapcsolja, a 無変換 pedig kikapcsolja. Koreainál a 한/영 váltja a Hangult, a 한자 Hanjára alakít, akár külön billentyűkkel, akár a sok laptopon küldött Right Alt és Right Ctrl jelekkel; ezért itt nem egyszerű módosítók, a nyomva tartott diktálás pedig F9-en marad. `Ctrl + Space` elérhető marad Tmuxhoz és Herdrhez; a `Shift + CapsLock` marad a compose-billentyű.

A billentyűzetjelző a sáv jobb oldalán megjelenik, ha több billentyűzetkiosztásod vagy bevitelimódszereid vannak. Kattints rá a beviteli nyelvek váltásához; a japán hiragánánál あ-t mutat. Japán karakterválasztékért válts japánra, írj be egy szót, például `nihongo`, majd nyomd meg kétszer a Space billentyűt. Nyomd meg az Entert a kiválasztás elfogadásához. Ha több billentyűzetkiosztásod is van, kattints jobb gombbal a jelzőre az azokon keresztüli ciklizáláshoz.

A _Setup > Typing > Keyboard Layouts_ pontban választhatsz olyan kiosztásokat, mint az angol és a francia, ugyanazok közül a lehetőségek közül, amelyek a telepítéskor fel lett kínálva. A _Setup > Typing > Input Methods_ pontban kiválaszthatod, hogy mely beviteli motorok aktívak. Mindkét választó az Omarchy menüben nyílik meg, az aktuális kiválasztásaiddal bejelölve. Kattints vagy nyomj Entert egy lehetőség kapcsológatásához; minden módosítás azonnal alkalmazandó. Egy bevitelimódszer kijelölésének törlése eltávolítja azt a ciklusból, eltávolítás nélkül; a billentyűzet elérhető marad.

Futtasd az `omarchy setup keyboard` vagy az `omarchy setup input` parancsot ugyanazon választók megnyitásához. Egy nyelv hozzáfűzéséhez a parancssorból használd az `omarchy setup input mozc`, `hangul`, `pinyin`, `chewing`, `cangjie5` parancsot. Az egyéni kapcsolóbillentyűid megmaradnak. Alternatív motor-kiosztásokhoz vagy billentyűkhöz telepítsd a `fcitx5-configtool` csomagot az `omarchy pkg add fcitx5-configtool` paranccsal, és indítsd terminálból. Egy beviteli nyelv kiválasztása nem módosítja az asztal nyelvét. A Quick, Boshiamy és Array a Cangjie csomagjában van, és megjelenik a beviteli módok választójában. A _Beállítás > Nyelv_ alatt japánt, koreait vagy kínait választva hozzáadódik a beviteli mód, ha még nincs ilyen.

A `Super + I` kombinációval ciklizálhatsz a bevitelimódszerek vagy billentyűzetkiosztások között, a `Super + Shift + I` kombinációval pedig visszafelé, így három konfigurálttal két szomszéd között mozoghatsz. A beviteli jelző csak akkor jelenik meg a sáv jobb oldalán, ha egynél több bevitelimódszer vagy kiosztás van konfigurálva. Ez az asztali kötés a meglévő Fcitx-kapcsolóbillentyűiddel együtt működik; a `~/.config/hypr/bindings.lua` fájlban felülírhatod. A beviteli motorok és a compose-szekvenciák a minden munkamenetben már futó [Fcitx5](https://fcitx-im.org/) szolgáltatást használják.

### ALT használata SUPER-ként

Néhány billentyűzeten nem kényelmes az elsődleges metagombot (a Windows/cmd-billentyűt) SUPER-ként használni. Helyette az ALT-ra módosíthatod ezzel a beállítással:

```lua
hl.config({
  input = {
    kb_options = "omarchy:shift_caps_compose,altwin:swap_alt_win",
  },
})
```
