# कीबोर्ड, माउस, ट्रैकपैड

Hyprland आपको अपने सभी इनपुट को बहुत विस्तार से कॉन्फ़िगर करने देता है। आप कीबोर्ड रिपीट को सुपरसोनिक तेज़ बना सकते हैं या ट्रैकपैड को प्राकृतिक स्क्रॉलिंग का उपयोग करा सकते हैं। आप यह सब `~/.config/hypr/input.lua` में बदलते हैं, जिस तक आप Omarchy मेनू (`Super + Space`) में _Setup > Input_ के माध्यम से भी पहुँच सकते हैं। वहाँ आप जो कुछ भी सेट करते हैं वह Omarchy के डिफ़ॉल्ट को प्रतिस्थापित कर देता है।

यहाँ एक उदाहरण है:

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

आप Hyprland विकी पर इनपुट के लिए [सभी इनपुट विकल्प देख सकते हैं](https://wiki.hypr.land/Configuring/Basics/Variables/#input)।

CapsLock सामान्य Caps Lock के रूप में काम करता है, और `Shift + CapsLock` [त्वरित इमोजी](07-hotkeys.md#quick-emojis) और [अन्य पूर्णताओं](07-hotkeys.md#quick-completions) के लिए कंपोज़ कुंजी है। अगर आप कंपोज़ कुंजी कहीं और रखना पसंद करेंगे, तो `kb_options` में `omarchy:shift_caps_compose` बदल दें। उदाहरण के लिए, यह कंपोज़ कुंजी को Right Alt पर ले जाता है:

```lua
hl.config({
  input = {
    kb_options = "compose:ralt",
  },
})
```

### ट्रैकपैड जेस्चर

आप [टचपैड जेस्चर](https://wiki.hypr.land/Configuring/Advanced-and-Cool/Gestures/) भी चालू कर सकते हैं, जैसे वर्कस्पेस बदलने के लिए तीन उंगलियों से स्वाइप करना:

```lua
hl.gesture({ fingers = 3, direction = "horizontal", action = "workspace" })
```

हैप्टिक टचपैड वाले Dell XPS लैपटॉप पर, आप _Trigger > Hardware > Touchpad Haptics_ के अंतर्गत क्लिक ताकत को low, mid या high पर भी सेट कर सकते हैं।

### चीनी, जापानी और अन्य भाषाओं में टाइप करना

इंस्टॉलर जब कीबोर्ड पूछे तो जापानी, कोरियाई, चीनी (सरलीकृत, Pinyin), ताइवान (Zhuyin) या हांगकांग (Cangjie) चुनें। Omarchy कीबोर्ड और इनपुट इंजन अपने आप सेट करता है, ऑफलाइन पहले बूट में भी। जापानी Mozc, कोरियाई मानक दो-सेट Hangul, सरलीकृत चीनी Pinyin, ताइवान Chewing का मानक Zhuyin और हांगकांग स्थानीय अक्षर रूपों वाला Cangjie इस्तेमाल करता है। जापानी (US कीबोर्ड) US लेआउट के साथ Mozc देता है। Dvorak, Colemak या AZERTY से लैटिन अक्षर लिखते समय भी Hangul, Zhuyin और Cangjie कुंजियाँ मानक जगह रहती हैं। Hangul या Chewing पहले जोड़ा हो तो _सेटअप > टाइपिंग > इनपुट पद्धतियाँ_ में उसे हटाकर फिर चुनें ताकि कुंजियाँ वहाँ जाएँ; Omarchy पहले से इस्तेमाल हो रहे इंजन को नहीं बदलता।

टाइपिंग Latin मोड में शुरू होती है। कॉन्फ़िगर की गई इनपुट विधियों से गुज़रने के लिए `Super + I` दबाएँ, और वापस गुज़रने के लिए `Super + Shift + I` दबाएँ। Pinyin जैसी इनपुट विधि से Latin अक्षरों में बाहर निकलने के लिए अकेले `Shift` टैप करें, और वापस जाने के लिए इसे फिर से टैप करें, जिस तरह Sogou, Microsoft Pinyin और macOS काम करते हैं; `Shift` के साथ अक्षर अभी भी बड़ा अक्षर टाइप करता है। Japanese कीबोर्ड पर, 全角/半角 इनपुट टॉगल करता है, 変換 इसे चालू करता है, और 無変換 इसे बंद करता है। कोरियाई में 한/영 Hangul बदलता है और 한자 Hanja में बदलता है, चाहे अलग कुंजियाँ हों या कई लैपटॉप की तरह कीबोर्ड Right Alt और Right Ctrl भेजे; इसलिए यहाँ वे साधारण मॉडिफ़ायर नहीं हैं और दबाकर बोलने वाला डिक्टेशन F9 पर ही रहता है। `Ctrl + Space` Tmux और Herdr के लिए उपलब्ध रहता है; `Shift + CapsLock` कंपोज़ कुंजी बनी रहती है।

जब आपके पास कई कीबोर्ड लेआउट या इनपुट विधियाँ हों तो कीबोर्ड संकेतक बार के दाईं ओर दिखाई देता है। इनपुट भाषाएँ बदलने के लिए उस पर क्लिक करें; Japanese hiragana के लिए あ दिखाता है। Japanese वर्ण विकल्पों के लिए, Japanese पर स्विच करें, `nihongo` जैसा शब्द टाइप करें, फिर Space दो बार दबाएँ। अपनी पसंद स्वीकार करने के लिए Enter दबाएँ। अगर आपके पास कई कीबोर्ड लेआउट भी हैं, तो उनसे गुज़रने के लिए संकेतक पर राइट-क्लिक करें।

English और French जैसे लेआउट चुनने के लिए _Setup > Typing > Keyboard Layouts_ का उपयोग करें, स्थापना के दौरान दिए गए समान विकल्पों से। कौन से कंपोज़िशन इंजन सक्रिय हैं यह चुनने के लिए _Setup > Typing > Input Methods_ का उपयोग करें। दोनों पिकर आपके वर्तमान चयनों को चेक करके Omarchy मेनू के अंदर खुलते हैं। विकल्प टॉगल करने के लिए क्लिक करें या Enter दबाएँ; प्रत्येक बदलाव तुरंत लागू होता है। इनपुट विधि को अचयनित करने से यह बिना अनइंस्टॉल किए चक्र से हट जाती है; कीबोर्ड उपलब्ध रहता है।

समान पिकर खोलने के लिए `omarchy setup keyboard` या `omarchy setup input` चलाएँ। कमांड लाइन से एक भाषा जोड़ने के लिए, `omarchy setup input mozc`, `hangul`, `pinyin`, `chewing`, `cangjie5` का उपयोग करें। आपकी कस्टम स्विचिंग कुंजियाँ संरक्षित रहती हैं। वैकल्पिक इंजन लेआउट या कुंजियों के लिए, `omarchy pkg add fcitx5-configtool` से `fcitx5-configtool` इंस्टॉल करें और इसे टर्मिनल से लॉन्च करें। इनपुट भाषा चुनने से डेस्कटॉप भाषा नहीं बदलती। Quick, Boshiamy और Array Cangjie के ही पैकेज में आते हैं और इनपुट विधि चयन में दिखते हैं। _सेटअप > भाषा_ में जापानी, कोरियाई या चीनी चुनने से इनपुट विधि जुड़ती है, यदि अभी कोई नहीं है।

इनपुट विधियों या कीबोर्ड लेआउट से गुज़रने के लिए `Super + I` का उपयोग करें, और दूसरी ओर वापस जाने के लिए `Super + Shift + I` का उपयोग करें, ताकि तीन कॉन्फ़िगर होने पर आप दो पड़ोसियों के बीच जा सकें। इनपुट संकेतक बार के दाईं ओर केवल तभी दिखाई देता है जब एक से अधिक इनपुट विधि या लेआउट कॉन्फ़िगर हो। यह डेस्कटॉप बाइंडिंग आपकी मौजूदा Fcitx स्विचिंग कुंजियों के साथ-साथ काम करती है; आप इसे `~/.config/hypr/bindings.lua` में ओवरराइड कर सकते हैं। इनपुट इंजन और कंपोज़ अनुक्रम हर सत्र में पहले से चल रही [Fcitx5](https://fcitx-im.org/) सेवा का उपयोग करते हैं।

### ALT को SUPER के रूप में उपयोग करना

कुछ कीबोर्ड पर, प्राथमिक मेटा कुंजी (Windows/cmd कुंजी) को SUPER के रूप में उपयोग करना सुविधाजनक नहीं होता। आप इस बदलाव का उपयोग करके इसे इसके बजाय ALT में बदल सकते हैं:

```lua
hl.config({
  input = {
    kb_options = "omarchy:shift_caps_compose,altwin:swap_alt_win",
  },
})
```
