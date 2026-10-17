# Lyklaborð, mús, snertiflötur

Hyprland leyfir þér að stilla öll inntök þín í miklum smáatriðum. Þú getur breytt endurtekningu lyklaborðsins í yfirhljóðshraða eða látið snertiflötinn nota náttúrulega skrunun. Þú breytir þessu öllu í `~/.config/hypr/input.lua`, sem þú getur líka náð í í gegnum _Uppsetning > Inntak_ í Omarchy-valmyndinni (`Super + Space`). Allt sem þú stillir þar kemur í stað sjálfgilda Omarchy.

Hér er dæmi:

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

Þú getur [séð alla inntakskosti](https://wiki.hypr.land/Configuring/Basics/Variables/#input) á Hyprland-wikinu fyrir inntök.

CapsLock virkar sem venjulegur Caps Lock, og `Shift + CapsLock` er samsetningarlykillinn fyrir [hrað emoji](07-hotkeys.md#quick-emojis) og [aðrar útfyllingar](07-hotkeys.md#quick-completions). Ef þú vilt frekar hafa samsetningarlykilinn annars staðar skaltu skipta út `omarchy:shift_caps_compose` í `kb_options`. Til dæmis færir þetta samsetningarlykilinn á Right Alt:

```lua
hl.config({
  input = {
    kb_options = "compose:ralt",
  },
})
```

### Snertiflatarbendingar

Þú getur líka kveikt á [snertiflatarbendingum](https://wiki.hypr.land/Configuring/Advanced-and-Cool/Gestures/), eins og að strjúka með þremur fingrum til að skipta um vinnusvæði:

```lua
hl.gesture({ fingers = 3, direction = "horizontal", action = "workspace" })
```

Á Dell XPS-fartölvum með haptískum snertifleti geturðu líka stillt smellstyrkinn á lágan, miðlungs eða háan undir _Kveikja > Vélbúnaður > Snertisvörun flatar_.

### Að skrifa á kínversku, japönsku og öðrum tungumálum

Veldu japönsku, kóresku, kínversku (einfaldaða, Pinyin), Taívan (Zhuyin) eða Hong Kong (Cangjie) þegar uppsetningarforritið spyr um lyklaborð. Omarchy stillir lyklaborð og innsláttarvél sjálfvirkt, einnig við fyrstu ræsingu án nets. Japanska notar Mozc, kóreska staðlað tveggja setta Hangul, einfölduð kínverska Pinyin, Taívan staðlaða Zhuyin-röðun Chewing og Hong Kong Cangjie með stafmyndum Hong Kong. Japanska (US-lyklaborð) gefur Mozc með US-skipan. Hangul-, Zhuyin- og Cangjie-lyklar halda stöðluðum stöðum þótt latneskir stafir séu slegnir með Dvorak, Colemak eða AZERTY. Hafirðu þegar bætt Hangul eða Chewing við, afveldu og veldu það aftur undir _Uppsetning > Innsláttur > Innsláttaraðferðir_ til að færa lyklana; Omarchy breytir ekki vél sem þú notar þegar.

Innsláttur byrjar í latneskum ham. Ýttu á `Super + I` til að fara í gegnum stilltar inntaksaðferðir, og `Super + Shift + I` til að fara til baka. Bankaðu á `Shift` út af fyrir sig til að stíga út úr inntaksaðferð eins og Pinyin yfir í latneska stafi, og bankaðu aftur til að fara til baka, á sama hátt og Sogou, Microsoft Pinyin og macOS virka; `Shift` plús stafur skrifar samt hástaf. Á japönskum lyklaborðum víxlar 全角/半角 inntaki, 変換 kveikir á því og 無変換 slekkur á því. Í kóresku skiptir 한/영 um Hangul og 한자 breytir í Hanja, hvort sem sérstakir lyklar eru til staðar eða lyklaborðið sendir Right Alt og Right Ctrl eins og margar fartölvur; þeir eru því ekki venjulegir breytilyklar hér og talinnsláttur með takka sem haldið er niðri helst á F9. `Ctrl + Space` helst tiltækt fyrir Tmux og Herdr; `Shift + CapsLock` helst samsetningarlykillinn.

Lyklaborðsvísirinn birtist hægra megin á stikunni þegar þú ert með margar lyklaborðskipanir eða inntaksaðferðir. Smelltu á hann til að skipta um inntakstungumál; japanska birtir あ fyrir hiragana. Fyrir val á japönskum táknum skaltu skipta yfir í japönsku, skrifa orð eins og `nihongo`, ýta síðan tvisvar á Space. Ýttu á Enter til að samþykkja val þitt. Ef þú ert líka með margar lyklaborðskipanir skaltu hægrismella á vísi til að fara í gegnum þær.

Notaðu _Uppsetning > Innsláttur > Lyklaborðskipan_ til að velja skipanir eins og ensku og frönsku, úr sömu valkostum og í boði eru við uppsetningu. Notaðu _Uppsetning > Innsláttur > Innsláttaraðferðir_ til að velja hvaða samsetningarvélar eru virkar. Báðir veljararnir opnast inni í Omarchy-valmyndinni með núverandi val þitt hakað við. Smelltu eða ýttu á Enter til að víxla vali; hver breyting tekur strax gildi. Að afvelja inntaksaðferð fjarlægir hana úr hringnum án þess að fjarlægja hana; lyklaborðið helst tiltækt.

Keyrðu `omarchy setup keyboard` eða `omarchy setup input` til að opna sömu veljara. Til að bæta við einu tungumáli úr skipanalínunni skaltu nota `omarchy setup input mozc`, `hangul`, `pinyin`, `chewing`, `cangjie5`. Sérsniðnir skiptilyklar þínir varðveitast. Fyrir aðrar vélarskipanir eða lykla skaltu setja upp `fcitx5-configtool` með `omarchy pkg add fcitx5-configtool` og ræsa það úr terminali. Að velja inntakstungumál breytir ekki skjáborðstungumálinu. Quick, Boshiamy og Array fylgja sama pakka og Cangjie og birtast í innsláttaraðferðavalinu. Ef japanska, kóreska eða kínverska er valin undir _Uppsetning > Tungumál_ bætist innsláttaraðferðin við ef engin er fyrir.

Notaðu `Super + I` til að fara í gegnum inntaksaðferðir eða lyklaborðskipanir, og `Super + Shift + I` til að fara aftur hina leiðina, þannig að með þrjár stilltar geturðu farið á milli tveggja nágranna. Inntaksvísirinn birtist hægra megin á stikunni aðeins þegar fleiri en ein inntaksaðferð eða skipan er stillt. Þessi skjáborðsbinding virkar samhliða núverandi Fcitx-skiptilyklum þínum; þú getur yfirskrifað hana í `~/.config/hypr/bindings.lua`. Inntaksvélar og samsetningarrunurnar nota [Fcitx5](https://fcitx-im.org/) þjónustuna sem þegar keyrir í hverri lotu.

### Notaðu ALT sem SUPER

Á sumum lyklaborðum er ekki þægilegt að nota aðal meta-lykilinn (Windows/cmd-lykillinn) sem SUPER. Þú getur breytt þessu í ALT í staðinn með þessari breytingu:

```lua
hl.config({
  input = {
    kb_options = "omarchy:shift_caps_compose,altwin:swap_alt_win",
  },
})
```
