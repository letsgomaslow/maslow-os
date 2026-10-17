# Klaviatuur, hiir, puuteplaat

Hyprland võimaldab kõiki oma sisendeid üksikasjalikult konfigureerida. Saad muuta klaviatuuri korduse ülehelikiiruseliseks või panna puuteplaadi kasutama loomulikku kerimist. Kõike seda muudad failis `~/.config/hypr/input.lua`, millele pääsed ligi ka Omarchy menüü (`Super + Space`) jaotise _Seaded > Sisend_ kaudu. Kõik, mis sinna määrad, asendab Omarchy vaikeväärtused.

Siin on näide:

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

Kõiki sisendivalikuid saad [vaadata Hyprlandi vikis](https://wiki.hypr.land/Configuring/Basics/Variables/#input).

CapsLock töötab tavalise Caps Lockina ja `Shift + CapsLock` on compose klahv [kiirete emojide](07-hotkeys.md#quick-emojis) ja [muude täienduste](07-hotkeys.md#quick-completions) jaoks. Kui eelistad compose klahvi mujale, asenda `kb_options`-is `omarchy:shift_caps_compose`. Näiteks teisaldab see compose klahvi paremale Altile:

```lua
hl.config({
  input = {
    kb_options = "compose:ralt",
  },
})
```

### Puuteplaadi žestid

Samuti saad sisse lülitada [puuteplaadi žeste](https://wiki.hypr.land/Configuring/Advanced-and-Cool/Gestures/), näiteks kolme sõrmega libistamist tööalade vahetamiseks:

```lua
hl.gesture({ fingers = 3, direction = "horizontal", action = "workspace" })
```

Dell XPS sülearvutitel haptilise puuteplaadiga saad määrata klõpsu tugevuse madalaks, keskmiseks või kõrgeks jaotises _Käivita > Riistvara > Touchpad Haptics_.

### Sisestamine hiina, jaapani ja teistes keeltes

Kui paigaldaja küsib klaviatuuri, vali jaapani, korea, hiina (lihtsustatud, Pinyin), Taiwan (Zhuyin) või Hongkong (Cangjie). Omarchy seadistab klaviatuuri ja sisestusmootori automaatselt, ka võrguühenduseta esmakäivitamisel. Jaapani kasutab Mozci, korea standardset kahekomplektilist Hanguli, lihtsustatud hiina Pinyini, Taiwan Chewingi standardset Zhuyini ning Hongkong Cangjiet Hongkongi märgikujudega. Jaapani (US-klaviatuur) annab Mozci US-paigutusega. Hanguli, Zhuyini ja Cangjie klahvid jäävad standardkohtadele ka ladina tähtede tippimisel Dvoraki, Colemaki või AZERTYga. Kui lisasid Hanguli või Chewingi varem, eemalda valik ja vali uuesti jaotises _Seaded > Trükkimine > Sisestusmeetodid_, et klahvid sinna viia; Omarchy ei muuda juba kasutatavat mootorit.

Sisestamine algab Ladina režiimis. Vajuta `Super + I`, et tsüklit läbida konfigureeritud sisendmeetodeid, ja `Super + Shift + I`, et tagasi tsüklit läbida. Puuduta `Shift` üksi, et sisendmeetodist nagu Pinyin Ladina tähtedesse välja astuda, ja puuduta uuesti, et tagasi minna, nii nagu Sogou, Microsoft Pinyin ja macOS töötavad; `Shift` pluss täht sisestab endiselt suurtähte. Jaapani klaviatuuridel lülitab 全角/半角 sisendit, 変換 lülitab selle sisse ja 無変換 lülitab selle välja. Korea puhul vahetab 한/영 Hanguli ja 한자 teisendab Hanjaks, olgu klaviatuuril eriklahvid või saadetagu nagu paljudel sülearvutitel Right Alt ja Right Ctrl; seega pole need siin tavalised muuteklahvid ning allhoidmisega dikteerimine jääb F9 peale. `Ctrl + Space` jääb Tmuxi ja Herdr'i jaoks saadaval; `Shift + CapsLock` jääb compose klahviks.

Klaviatuuri näidik ilmub riba paremal, kui sul on mitu klaviatuuripaigutust või sisendmeetodit. Klõpsa seda sisendkeelte vahetamiseks; jaapani keel kuvab hiragana jaoks あ. Jaapani märkide valikute jaoks lülitu jaapani keelele, sisesta sõna nagu `nihongo`, seejärel vajuta Space kaks korda. Vajuta oma valiku kinnitamiseks Enter. Kui sul on ka mitu klaviatuuripaigutust, tee nende tsükliliseks läbimiseks näidikul paremklõps.

Kasuta jaotist _Seaded > Typing > Keyboard Layouts_, et valida paigutused nagu inglise ja prantsuse, samadest valikutest, mida paigaldamise ajal pakutakse. Kasuta jaotist _Seaded > Typing > Input Methods_, et valida, millised koostemootorid on aktiivsed. Mõlemad valijad avanevad Omarchy menüüs koos sinu praeguste valikute märgistamisega. Klõpsa või vajuta valiku lülitamiseks Enter; iga muudatus kehtib kohe. Sisendmeetodi tühistamine eemaldab selle tsüklist ilma selle desinstallimata; klaviatuur jääb saadaval.

Käivita `omarchy setup keyboard` või `omarchy setup input`, et avada samad valijad. Ühe keele lisamiseks käsurealt kasuta `omarchy setup input mozc`, `hangul`, `pinyin`, `chewing`, `cangjie5`. Sinu kohandatud vahetusklahvid säilinud. Alternatiivsete mootoripaigutuste või klahvide jaoks paigalda `fcitx5-configtool` käsuga `omarchy pkg add fcitx5-configtool` ja käivita see terminalist. Sisendkeele valimine ei muuda töölaua keelt. Quick, Boshiamy ja Array on Cangjiega samas paketis ning ilmuvad sisestusmeetodite valikusse. Jaapani, korea või hiina valimine jaotises _Seaded > Keel_ lisab sisestusmeetodi, kui sul veel ühtki pole.

Kasuta `Super + I`, et tsüklit läbida sisendmeetodeid või klaviatuuripaigutusi, ja `Super + Shift + I`, et minna teistpidi tagasi, nii et kolmega konfigureeritult saad kahe naabri vahel liikuda. Sisendinäidik ilmub riba paremal ainult siis, kui konfigureeritud on rohkem kui üks sisendmeetod või paigutus. See töölaua sidumine töötab koos sinu olemasolevate Fcitx vahetusklahvidega; saad selle failis `~/.config/hypr/bindings.lua` üle kirjutada. Sisendmootorid ja compose järjestused kasutavad [Fcitx5](https://fcitx-im.org/) teenust, mis juba igas seansis töötab.

### ALT kasutamine SUPER-ina

Mõnel klaviatuuril pole mugav kasutada peamist meta klahvi (Windowsi/cmd klahvi) SUPER-ina. Saad selle muuta selle asemel ALT-iks, kasutades seda muudatust:

```lua
hl.config({
  input = {
    kb_options = "omarchy:shift_caps_compose,altwin:swap_alt_win",
  },
})
```
