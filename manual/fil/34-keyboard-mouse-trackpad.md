# Keyboard, Mouse, Trackpad

Nagbibigay-daan sa iyo ang Hyprland na i-configure ang lahat ng iyong input sa napakadetalyeng paraan. Maaari mong baguhin ang keyboard repeat para maging napakabilis o gawing gumamit ng natural scrolling ang trackpad. Binabago mo ang lahat ng ito sa `~/.config/hypr/input.lua`, na maaari mo ring maabot sa pamamagitan ng _Setup > Input_ sa Omarchy menu (`Super + Space`). Anumang itakda mo roon ay papalitan ang mga default ng Omarchy.

Narito ang isang halimbawa:

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

Maaari mong [makita ang lahat ng input option](https://wiki.hypr.land/Configuring/Basics/Variables/#input) sa Hyprland wiki para sa mga input.

Gumagana ang CapsLock bilang isang normal na Caps Lock, at ang `Shift + CapsLock` ay ang compose key para sa [mabilis na emoji](07-hotkeys.md#quick-emojis) at [iba pang completion](07-hotkeys.md#quick-completions). Kung mas gusto mong nasa ibang lugar ang compose key, palitan ang `omarchy:shift_caps_compose` sa `kb_options`. Halimbawa, inililipat nito ang compose key sa Right Alt:

```lua
hl.config({
  input = {
    kb_options = "compose:ralt",
  },
})
```

### Mga galaw ng trackpad

Maaari mo ring i-on ang [mga touchpad gesture](https://wiki.hypr.land/Configuring/Advanced-and-Cool/Gestures/), tulad ng pag-swipe gamit ang tatlong daliri para baguhin ang mga workspace:

```lua
hl.gesture({ fingers = 3, direction = "horizontal", action = "workspace" })
```

Sa mga Dell XPS laptop na may haptic touchpad, maaari mo ring itakda ang lakas ng click sa low, mid, o high sa ilalim ng _Trigger > Hardware > Touchpad Haptics_.

### Pag-type sa Chinese, Japanese, at iba pang wika

Piliin ang Japanese, Korean, Chinese (Simplified, Pinyin), Taiwan (Zhuyin), o Hong Kong (Cangjie) kapag tinanong ng installer ang keyboard. Awtomatikong inaayos ng Omarchy ang keyboard at input engine, pati sa offline na unang boot. Mozc ang Japanese, karaniwang two-set Hangul ang Korean, Pinyin ang Simplified Chinese, karaniwang Zhuyin ng Chewing ang Taiwan, at Cangjie na may anyong Hong Kong ang Hong Kong. May Mozc na US layout ang Japanese (US keyboard). Nananatili sa karaniwang posisyon ang Hangul, Zhuyin at Cangjie kahit Dvorak, Colemak o AZERTY ang gamit sa Latin na titik. Kung may Hangul o Chewing ka na, alisin at ibalik ang pagpili sa _Pag-setup > Pag-type > Mga Paraan ng Input_ upang ilipat ang mga key; hindi ginagalaw ng Omarchy ang ginagamit mo nang engine.

Nagsisimula ang pag-type sa Latin mode. Pindutin ang `Super + I` para umikot sa mga naka-configure na input method, at ang `Super + Shift + I` para umikot pabalik. I-tap ang `Shift` nang mag-isa para lumabas sa isang input method tulad ng Pinyin papunta sa mga Latin letter, at i-tap ito ulit para bumalik, sa paraang gumagana ang Sogou, Microsoft Pinyin, at macOS; ang `Shift` kasama ang isang titik ay nagta-type pa rin ng kapital. Sa mga Japanese keyboard, ini-toggle ng 全角/半角 ang input, ino-on ito ng 変換, at ino-off ito ng 無変換. Sa Korean, nagpapalit ng Hangul ang 한/영 at nagko-convert sa Hanja ang 한자, may hiwalay mang key o Right Alt at Right Ctrl ang ipinapadala gaya ng maraming laptop; kaya hindi sila karaniwang modifier dito, at nananatili sa F9 ang dikta na pinipindot habang nagsasalita. `Ctrl + Space` para sa Tmux at Herdr; nananatiling compose key ang `Shift + CapsLock`.

Lumalabas ang keyboard indicator sa kanan ng bar kapag mayroon kang maraming keyboard layout o input method. I-click ito para magpalit ng mga input language; nagpapakita ang Japanese ng あ para sa hiragana. Para sa mga pagpipilian ng Japanese character, lumipat sa Japanese, mag-type ng salita tulad ng `nihongo`, pagkatapos ay pindutin ang Space nang dalawang beses. Pindutin ang Enter para tanggapin ang pinili mo. Kung mayroon ka ring maraming keyboard layout, i-right-click ang indicator para umikot sa mga iyon.

Gamitin ang _Setup > Typing > Keyboard Layouts_ para pumili ng mga layout tulad ng English at French, mula sa parehong mga pagpipilian na inaalok sa panahon ng pag-install. Gamitin ang _Setup > Typing > Input Methods_ para pumili kung aling mga composition engine ang aktibo. Bumubukas ang parehong picker sa loob ng Omarchy menu na naka-check ang iyong kasalukuyang mga pinili. I-click o pindutin ang Enter para i-toggle ang isang pagpipilian; nalalapat kaagad ang bawat pagbabago. Ang pag-deselect ng isang input method ay nagtatanggal nito mula sa cycle nang hindi ito ina-uninstall; nananatiling available ang keyboard.

Patakbuhin ang `omarchy setup keyboard` o `omarchy setup input` para buksan ang parehong mga picker. Para magdagdag ng isang wika mula sa command line, gamitin ang `omarchy setup input mozc`, `hangul`, `pinyin`, `chewing`, `cangjie5`. Pinapanatili ang iyong mga custom na switching key. Para sa mga alternatibong engine layout o key, i-install ang `fcitx5-configtool` gamit ang `omarchy pkg add fcitx5-configtool` at ilunsad ito mula sa isang terminal. Ang pagpili ng isang input language ay hindi nagbabago ng wika ng desktop. Kasama ng Cangjie sa iisang package ang Quick, Boshiamy at Array at makikita sila sa pagpili ng input method. Ang pagpili ng Japanese, Korean o Chinese sa _Pag-setup > Wika_ ay nagdadagdag ng input method kung wala ka pa nito.

Gamitin ang `Super + I` para umikot sa mga input method o keyboard layout, at ang `Super + Shift + I` para pumunta sa kabilang direksyon, kaya sa tatlong naka-configure ay maaari kang gumalaw sa pagitan ng dalawang kapitbahay. Lumalabas lang ang input indicator sa kanan ng bar kapag higit sa isang input method o layout ang naka-configure. Gumagana ang desktop binding na ito kasama ng iyong mga umiiral na Fcitx switching key; maaari mo itong patungan sa `~/.config/hypr/bindings.lua`. Ginagamit ng mga input engine at ng mga compose sequence ang [Fcitx5](https://fcitx-im.org/) service na tumatakbo na sa bawat session.

### Gamitin ang ALT bilang SUPER

Sa ilang keyboard, hindi maginhawa na gamitin ang pangunahing meta key (Windows/cmd key) bilang SUPER. Maaari mong baguhin ito para maging ALT sa halip gamit ang pagbabagong ito:

```lua
hl.config({
  input = {
    kb_options = "omarchy:shift_caps_compose,altwin:swap_alt_win",
  },
})
```
