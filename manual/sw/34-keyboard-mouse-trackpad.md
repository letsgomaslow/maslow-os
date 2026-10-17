# Kibodi, Kipanya, Kiguso

Hyprland inakuwezesha kusanidi ingizo zako zote kwa undani mkubwa. Unaweza kubadilisha urudiaji wa kibodi kuwa haraka sana au kufanya kiguso kutumia usogeaji asili. Unabadilisha yote katika `~/.config/hypr/input.lua`, ambayo unaweza pia kuifikia kupitia _Sanidi > Ingizo_ katika menyu ya Omarchy (`Super + Space`). Chochote unachokiweka hapo huchukua nafasi ya chaguomsingi za Omarchy.

Huu hapa ni mfano:

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

Unaweza [kuona chaguo zote za ingizo](https://wiki.hypr.land/Configuring/Basics/Variables/#input) kwenye wiki ya Hyprland kwa ingizo.

CapsLock hufanya kazi kama Caps Lock ya kawaida, na `Shift + CapsLock` ni kitufe cha kutunga kwa [emoji za haraka](07-hotkeys.md#quick-emojis) na [ukamilishaji mwingine](07-hotkeys.md#quick-completions). Kama ungependa kitufe cha kutunga kiwe mahali pengine, badilisha `omarchy:shift_caps_compose` katika `kb_options`. Kwa mfano, hii husogeza kitufe cha kutunga hadi Alt ya Kulia:

```lua
hl.config({
  input = {
    kb_options = "compose:ralt",
  },
})
```

### Ishara za kiguso

Unaweza pia kuwasha [ishara za kiguso](https://wiki.hypr.land/Configuring/Advanced-and-Cool/Gestures/), kama kubofya na vidole vitatu kubadilisha nafasi za kazi:

```lua
hl.gesture({ fingers = 3, direction = "horizontal", action = "workspace" })
```

Kwenye kompyuta mpakato za Dell XPS zenye kiguso cha kugusa, unaweza pia kuweka nguvu ya ubofyaji kuwa chini, kati, au juu chini ya _Anzisha > Vifaa > Mtetema wa kiguso_.

### Kuandika kwa Kichina, Kijapani, na lugha nyingine

Kisakinishi kinapouliza kibodi, chagua Kijapani, Kikorea, Kichina (Kilichorahisishwa, Pinyin), Taiwan (Zhuyin) au Hong Kong (Cangjie). Omarchy husanidi kibodi na injini ya uingizaji kiotomatiki, hata katika usanidi wa kwanza bila mtandao. Kijapani hutumia Mozc, Kikorea Hangul ya kawaida ya seti mbili, Kichina Kilichorahisishwa Pinyin, Taiwan mpangilio wa kawaida wa Zhuyin wa Chewing, na Hong Kong Cangjie yenye maumbo ya herufi ya Hong Kong. Kijapani (kibodi US) hutoa Mozc yenye mpangilio US. Funguo za Hangul, Zhuyin na Cangjie hubaki katika nafasi za kawaida hata ukiandika Kilatini kwa Dvorak, Colemak au AZERTY. Ikiwa uliongeza Hangul au Chewing awali, ondoa na urudishe uteuzi chini ya _Sanidi > Kuandika > Mbinu za ingizo_ kuhamisha funguo; Omarchy haibadilishi injini unayotumia tayari.

Kuandika huanza katika hali ya Kilatini. Bonyeza `Super + I` kuzunguka mbinu za ingizo zilizosanidiwa, na `Super + Shift + I` kurudi nyuma. Gonga `Shift` peke yake kutoka kwenye mbinu ya ingizo kama Pinyin kwenda kwenye herufi za Kilatini, na uigonge tena kurudi, jinsi Sogou, Microsoft Pinyin, na macOS hufanya kazi; `Shift` pamoja na herufi bado huandika herufi kubwa. Kwenye kibodi za Kijapani, 全角/半角 hubadilisha ingizo, 変換 huiwasha, na 無変換 huizima. Kwa Kikorea, 한/영 hubadili Hangul na 한자 hubadilisha kwenda Hanja, iwe kuna funguo maalumu au kibodi hutuma Right Alt na Right Ctrl kama kompyuta nyingi mpakato; hivyo hapa si virekebishi vya kawaida, na imla ya kushikilia-kuzungumza hubaki kwenye F9. `Ctrl + Space` hubaki kupatikana kwa Tmux na Herdr; `Shift + CapsLock` hubaki kitufe cha kutunga.

Kiashiria cha kibodi huonekana kulia kwa upau wakati una mpangilio mingi ya kibodi au mbinu za ingizo. Ibofye kubadilisha lugha za ingizo; Kijapani huonyesha あ kwa hiragana. Kwa chaguo za herufi za Kijapani, badilisha hadi Kijapani, andika neno kama `nihongo`, kisha bonyeza Space mara mbili. Bonyeza Enter kukubali chaguo lako. Kama pia una mpangilio mingi ya kibodi, bofya kulia kiashiria kuzunguka hizo.

Tumia _Sanidi > Kuandika > Miundo ya kibodi_ kuchagua miundo kama Kiingereza na Kifaransa, kutoka chaguo zile zile zinazotolewa wakati wa usakinishaji. Tumia _Sanidi > Kuandika > Mbinu za ingizo_ kuchagua injini zipi za utunzi ziko hai. Wateuzi wote wawili hufunguka ndani ya menyu ya Omarchy na chaguo zako za sasa zikiwa zimewekewa alama. Bofya au bonyeza Enter kubadilisha chaguo; kila mabadiliko hutumika mara moja. Kuondoa uteuzi wa mbinu ya ingizo huiondoa kwenye mzunguko bila kuiondoa usakinishaji; kibodi hubakia kupatikana.

Endesha `omarchy setup keyboard` au `omarchy setup input` kufungua wateuzi wale wale. Ili kuambatanisha lugha moja kutoka mstari wa amri, tumia `omarchy setup input mozc`, `hangul`, `pinyin`, `chewing`, `cangjie5`. Vitufe vyako maalum vya kubadilisha huhifadhiwa. Kwa mipangilio mbadala ya injini au vitufe, sakinisha `fcitx5-configtool` kwa `omarchy pkg add fcitx5-configtool` na uizindue kutoka terminali. Kuchagua lugha ya ingizo hakubadilishi lugha ya eneo-kazi. Quick, Boshiamy na Array huja katika kifurushi kimoja na Cangjie na huonekana kwenye kichaguzi cha mbinu za uingizaji. Kuchagua Kijapani, Kikorea au Kichina chini ya _Sanidi > Lugha_ huongeza mbinu ya uingizaji ikiwa bado huna yoyote.

Tumia `Super + I` kuzunguka mbinu za ingizo au mipangilio ya kibodi, na `Super + Shift + I` kurudi upande mwingine, hivyo na tatu zilizosanidiwa unaweza kusonga kati ya majirani wawili. Kiashiria cha ingizo huonekana kulia kwa upau tu wakati zaidi ya mbinu moja ya ingizo au mpangilio umesanidiwa. Kiunganishi hiki cha eneo-kazi hufanya kazi pamoja na vitufe vyako vilivyopo vya kubadilisha vya Fcitx; unaweza kukibatilisha katika `~/.config/hypr/bindings.lua`. Injini za ingizo na mfuatano wa utunzi hutumia huduma ya [Fcitx5](https://fcitx-im.org/) tayari inayofanya kazi katika kila kikao.

### Tumia ALT kama SUPER

Kwenye kibodi fulani, si rahisi kutumia kitufe cha msingi cha meta (kitufe cha Windows/cmd) kama SUPER. Unaweza kubadilisha hili kuwa ALT badala yake kwa kutumia mabadiliko haya:

```lua
hl.config({
  input = {
    kb_options = "omarchy:shift_caps_compose,altwin:swap_alt_win",
  },
})
```
