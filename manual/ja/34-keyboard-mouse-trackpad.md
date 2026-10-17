# キーボード、マウス、トラックパッド

Hyprland では入力のすべてを細かく設定できます。キーリピートを超音速並みに高速にするか、トラックパッドを自然なスクロールにすることもできます。すべて `~/.config/hypr/input.lua` で変更でき、Omarchy メニュー（`Super + Space`）の _設定 > Input_ 経由でも到達できます。そこで設定したものは Omarchy のデフォルトを置き換えます。

例を示します：

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

入力については、Hyprland の Wiki で入力のすべての入力オプションを [見る](https://wiki.hypr.land/Configuring/Basics/Variables/#input) ことができます。

CapsLock は通常の Caps Lock として動作し、`Shift + CapsLock` は [クイック絵文字](07-hotkeys.md#quick-emojis) と [他の補完](07-hotkeys.md#quick-completions) 用の compose キーです。むしろ compose キーを別の場所に置きたいなら、`kb_options` の `omarchy:shift_caps_compose` を置き換えてください。たとえば次は compose キーを Right Alt へ移動させます：

```lua
hl.config({
  input = {
    kb_options = "compose:ralt",
  },
})
```

### トラックパッドジェスチャー

3本指でスワイプしてワークスペースを切り替えるような [タッチパッドジェスチャー](https://wiki.hypr.land/Configuring/Advanced-and-Cool/Gestures/) もオンにできます：

```lua
hl.gesture({ fingers = 3, direction = "horizontal", action = "workspace" })
```

触覚（振動）タッチパッドを搭載した Dell XPS ノートPCでは、_実行 > Hardware > Touchpad Haptics_ の下でクリックの強さを弱、中、高に設定することもできます。

### 中国語、日本語、その他の言語で入力する

インストーラーでキーボードを尋ねられたら、日本語、韓国語、中国語（簡体字、Pinyin）、台湾（Zhuyin）、香港（Cangjie）を選びます。Omarchy は初回のオフライン設定も含め、キーボードと対応する入力エンジンを自動設定します。日本語は Mozc、韓国語は標準の 2 セット Hangul、簡体字中国語は Pinyin、台湾は Chewing の標準 Zhuyin 配置、香港は香港字形を使う Cangjie です。日本語（US キーボード）では US 配列の Mozc を使えます。ラテン文字を Dvorak、Colemak、AZERTY で入力しても、Hangul、Zhuyin、Cangjie のキーは標準位置に保たれます。以前に Hangul や Chewing を追加した場合は、_設定 > タイピング > 入力方法_ で選択を解除して選び直すとキー位置を移行できます。使用中のエンジンを Omarchy が勝手に変更することはありません。

入力は Latin モードから始まります。`Super + I` を押すと、設定された入力方法を巡回し、`Super + Shift + I` を押すと戻って巡回します。`Shift` を単独でタップすると Pinyin のような入力方法から Latin 文字に脱し、再度タップして戻ります。これは Sogou、Microsoft Pinyin、macOS の振る舞いです。`Shift` プラス文字で大文字が入力されます。日本語キーボード上では、全角/半角 が入力を切り替え、変換 がオンにし、無変換 がオフにします。韓国語では 한/영 で Hangul を切り替え、한자 で Hanja に変換します。専用キーでも、多くのノート PC のように Right Alt と Right Ctrl を送るキーボードでも同じです。この場合これらは通常の修飾キーではなく、押して話すディクテーションは F9 のままです。 `Ctrl + Space` は Tmux と Herdr 向けに保持され、`Shift + CapsLock` は compose キーのままです。

キーボードインジケーターは、複数のキーボード配列や入力方法がある場合にバーの右に現れます。クリックしても入力言語を切り替えられます。Japanese では hiragana 向けに あ が表示されます。日本語の文字選択は、Japanese へ切り替え、`nihongo` のような単語を入力し、それから Space を2回押してください。Enter を押しても自分の選択を受け入れられます。複数のキーボード配列もあれば、インジケーターを右クリックして巡回してください。

_設定 > Typing > Keyboard Layouts_ を使っても English や French のような配列を選択でき、インストール時提示される同じ選択肢から選べます。_設定 > Typing > Input Methods_ を使って、どの組成エンジンが有効かを選択してください。どちらのピッカーも現在の選択内容にチェックの付いた状態で Omarchy メニュー内に開きます。クリックするか Enter を押すことで選択肢を切り替えられます。各変更は即座に適用されます。入力方法の選択を解除してもそれをアンインストールせずに巡回から外します。キーボードは保持されます。

`omarchy setup keyboard` または `omarchy setup input` を実行して同じピッカーを開いてください。コマンドラインから1言語を追加するには、`omarchy setup input mozc`, `hangul`, `pinyin`, `chewing`, `cangjie5` を使ってください。あなたのカスタム切り替えキーは保持されます。代替のエンジンレイアウトやキーの場合は、`omarchy pkg add fcitx5-configtool` で `fcitx5-configtool` をインストールし、ターミナルから起動してください。入力言語を選択してもデスクトップ言語は変更されません。 Quick、Boshiamy、Array は Cangjie と同じパッケージに含まれ、入力メソッドの選択画面に表示されます。_設定 > 言語_ で日本語、韓国語、中国語を選ぶと、まだ入力メソッドがない場合に対応するものが追加されます。

`Super + I` を使うと入力方法やキーボード配列を巡回し、`Super + Shift + I` を使うと逆方向に進みます。そのため、3つを設定しておけば2つの隣接の間で移動できます。入力インジケーターは、複数の入力方法やレイアウトが設定されている場合のみバーの右端に現れます。このデスクトップバインディングは既存の Fcitx の切り替えキーに加えて動作します。`~/.config/hypr/bindings.lua` で上書きできます。入力エンジンとコンポーズシーケンスは、すべてのセッションにおいてすでに実行中の [Fcitx5](https://fcitx-im.org/) サービスを使用します。

### ALT を SUPER として使う

一部のキーボードでは、主要な meta キー（Windows/cmd キー）を SUPER として使うのは不便なことがあります。これを ALT に変更することもでき、この変更を使います：

```lua
hl.config({
  input = {
    kb_options = "omarchy:shift_caps_compose,altwin:swap_alt_win",
  },
})
```
