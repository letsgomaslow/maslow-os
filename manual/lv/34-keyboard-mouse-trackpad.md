# Tastatūra, pele, skārienpaliktnis

Hyprland ļauj visas savas ievades konfigurēt ļoti detalizēti. Tastatūras atkārtošanos var nomainīt uz virsskaņas ātru vai likt skārienpaliktnim izmantot dabisko ritināšanu. Visu to maināt failā `~/.config/hypr/input.lua`, kuram var piekļūt arī caur Omarchy izvēlnes (`Super + Space`) sadaļu _Iestatīšana > Input_. Viss, ko tur iestatāt, aizstāj Omarchy noklusējumus.

Šeit ir piemērs:

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

Visas ievades iespējas varat [skatīt Hyprland wiki par ievadēm](https://wiki.hypr.land/Configuring/Basics/Variables/#input).

CapsLock darbojas kā parasts Caps Lock, bet `Shift + CapsLock` ir salikšanas taustiņš [ātrajām emocijzīmēm](07-hotkeys.md#quick-emojis) un [citiem papildinājumiem](07-hotkeys.md#quick-completions). Ja labprātāk salikšanas taustiņu gribat citviet, parametrā `kb_options` aizstājiet `omarchy:shift_caps_compose`. Piemēram, šis salikšanas taustiņu pārvieto uz Right Alt:

```lua
hl.config({
  input = {
    kb_options = "compose:ralt",
  },
})
```

### Skārienpaliktņa žesti

Varat ieslēgt arī [skārienpaliktņa žestus](https://wiki.hypr.land/Configuring/Advanced-and-Cool/Gestures/), piemēram, pavilkt ar trim pirkstiem, lai mainītu darbvietas:

```lua
hl.gesture({ fingers = 3, direction = "horizontal", action = "workspace" })
```

Dell XPS klēpjdatoros ar haptisko skārienpaliktni klikšķa spēku uz zemu, vidēju vai augstu var iestatīt arī sadaļā _Palaist > Hardware > Touchpad Haptics_.

### Rakstīšana ķīniešu, japāņu un citās valodās

Kad instalētājs jautā par tastatūru, izvēlies japāņu, korejiešu, ķīniešu (vienkāršoto, Pinyin), Taivānu (Zhuyin) vai Honkongu (Cangjie). Omarchy automātiski iestata tastatūru un ievades dzinēju arī pirmajā palaišanā bez tīkla. Japāņu izmanto Mozc, korejiešu standarta divu kopu Hangul, vienkāršotā ķīniešu Pinyin, Taivāna Chewing standarta Zhuyin izkārtojumu un Honkonga Cangjie ar Honkongas rakstzīmju formām. Japāņu (US tastatūra) piedāvā Mozc ar US izkārtojumu. Hangul, Zhuyin un Cangjie taustiņi paliek standarta vietās arī ar latīņu Dvorak, Colemak vai AZERTY. Ja Hangul vai Chewing jau pievienots, noņem un atjauno izvēli sadaļā _Iestatīšana > Rakstīšana > Ievades metodes_, lai pārvietotu taustiņus; Omarchy nemaina jau lietotu dzinēju.

Rakstīšana sākas latīņu režīmā. Nospiediet `Super + I`, lai cikliski ietu caur konfigurētajām ievades metodēm, un `Super + Shift + I`, lai cikliski atgrieztos. Uzspiediet tikai uz `Shift`, lai no tādas ievades metodes kā Pinyin izkāptu latīņu burtiem, un uzspiediet vēlreiz, lai atgrieztos atpakaļ — tieši tā, kā darbojas Sogou, Microsoft Pinyin un macOS; `Shift` plus burts joprojām ieraksta lielo burtu. Japāņu tastatūrās 全角/半角 pārslēdz ievadi, 変換 to ieslēdz, bet 無変換 to izslēdz. Korejiešu ievadē 한/영 pārslēdz Hangul un 한자 pārvērš uz Hanja gan ar atsevišķiem taustiņiem, gan tastatūrai sūtot Right Alt un Right Ctrl kā daudzos klēpjdatoros; tāpēc te tie nav parasti modifikatori, un diktēšana ar turētu taustiņu paliek uz F9. `Ctrl + Space` paliek pieejams priekš Tmux un Herdr; `Shift + CapsLock` paliek salikšanas taustiņš.

Tastatūras rādītājs parādās joslas labajā pusē, kad jums ir vairāki tastatūras izkārtojumi vai ievades metodes. Noklikšķiniet uz tā, lai pārslēgtu ievades valodas; japāņu valodā hiraganai tiek attēlots あ. Japāņu rakstu zīmju izvēlei pārslēdzieties uz japāņu valodu, ierakstiet tādu vārdu kā `nihongo`, pēc tam divreiz nospiediet Space. Nospiediet Enter, lai savu izvēli pieņemtu. Ja jums ir arī vairāki tastatūras izkārtojumi, ar labo pogu noklikšķiniet uz rādītāja, lai tos cikliski pārslēgtu.

Izmantojiet _Iestatīšana > Typing > Keyboard Layouts_, lai atlasītu tādus izkārtojumus kā angļu un franču, no tām pašām izvēlēm, kas piedāvātas instalēšanas laikā. Izmantojiet _Iestatīšana > Typing > Input Methods_, lai atlasītu, kuri salikšanas dzinēji ir aktīvi. Abi atlasītāji atveras Omarchy izvēlnes iekšienē ar jūsu pašreizējām atzīmētajām izvēlēm. Noklikšķiniet vai nospiediet Enter, lai izvēli pārslēgtu; katra izmaiņa stājas spēkā nekavējoties. Ievades metodes atlases noņemšana to no cikla izņem, to neatinstalējot; tastatūra paliek pieejama.

Palaidiet `omarchy setup keyboard` vai `omarchy setup input`, lai atvērtu tādus pašus atlasītājus. Lai no komandrindas pievienotu vienu valodu, izmantojiet `omarchy setup input mozc`, `hangul`, `pinyin`, `chewing`, `cangjie5`. Jūsu pielāgotie pārslēgšanas taustiņi tiek saglabāti. Alternatīviem dzinēja izkārtojumiem vai taustiņiem instalējiet `fcitx5-configtool` ar `omarchy pkg add fcitx5-configtool` un palaidiet to no termināļa. Ievades valodas atlase darbvirsmas valodu nemaina. Quick, Boshiamy un Array ietilpst Cangjie paketē un parādās ievades metožu izvēlnē. Japāņu, korejiešu vai ķīniešu izvēle sadaļā _Iestatīšana > Valoda_ pievieno ievades metodi, ja tev tādas vēl nav.

Izmantojiet `Super + I`, lai cikliski ietu caur ievades metodēm vai tastatūras izkārtojumiem, un `Super + Shift + I`, lai ietu atpakaļ otrā virzienā, tāpēc ar trim konfigurētajiem jūs varat pārvietoties starp diviem kaimiņiem. Ievades rādītājs joslas labajā pusē parādās tikai tad, kad ir konfigurēta vairāk nekā viena ievades metode vai izkārtojums. Šī darbvirsmas saīsne darbojas līdzās jūsu esošajiem Fcitx pārslēgšanas taustiņiem; to varat pārrakstīt failā `~/.config/hypr/bindings.lua`. Ievades dzinēji un salikšanas secības izmanto [Fcitx5](https://fcitx-im.org/) pakalpojumu, kurš jau darbojas katrā sesijā.

### ALT izmantošana kā SUPER vietā

Dažās tastatūrās nav ērti kā SUPER izmantot primāro meta taustiņu (Windows/cmd taustiņu). Tā vietā to uz ALT var nomainīt, izmantojot šo izmaiņu:

```lua
hl.config({
  input = {
    kb_options = "omarchy:shift_caps_compose,altwin:swap_alt_win",
  },
})
```
