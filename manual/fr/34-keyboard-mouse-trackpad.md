# Clavier, souris, pavé tactile

Hyprland vous permet de configurer toutes vos entrées dans les moindres détails. Vous pouvez rendre la répétition du clavier supersonique ou faire utiliser le défilement naturel au pavé tactile. Vous changez tout cela dans `~/.config/hypr/input.lua`, que vous pouvez aussi atteindre via _Configuration > Entrées_ dans le menu Omarchy (`Super + Space`). Tout ce que vous définissez là remplace les valeurs par défaut d'Omarchy.

Voici un exemple :

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

Vous pouvez [voir toutes les options d'entrée](https://wiki.hypr.land/Configuring/Basics/Variables/#input) sur le wiki Hyprland pour les entrées.

CapsLock fonctionne comme un Caps Lock normal, et `Shift + CapsLock` est la touche compose pour les [émojis rapides](07-hotkeys.md#quick-emojis) et les [autres complétions](07-hotkeys.md#quick-completions). Si vous préférez avoir la touche compose ailleurs, remplacez `omarchy:shift_caps_compose` dans `kb_options`. Par exemple, ceci déplace la touche compose sur Alt droit :

```lua
hl.config({
  input = {
    kb_options = "compose:ralt",
  },
})
```

### Gestes du pavé tactile

Vous pouvez aussi activer les [gestes du pavé tactile](https://wiki.hypr.land/Configuring/Advanced-and-Cool/Gestures/), comme glisser avec trois doigts pour changer d'espace de travail :

```lua
hl.gesture({ fingers = 3, direction = "horizontal", action = "workspace" })
```

Sur les ordinateurs portables Dell XPS avec un pavé tactile haptique, vous pouvez aussi régler la force du clic sur bas, moyen ou élevé sous _Déclencher > Matériel > Haptique pavé tactile_.

### Saisir en chinois, japonais et autres langues

Quand l'installateur demande le clavier, choisissez japonais, coréen, chinois (simplifié, Pinyin), Taïwan (Zhuyin) ou Hong Kong (Cangjie). Omarchy configure automatiquement le clavier et le moteur de saisie, même au premier démarrage hors ligne. Le japonais utilise Mozc, le coréen le Hangul standard à deux jeux, le chinois simplifié Pinyin, Taïwan la disposition Zhuyin standard de Chewing et Hong Kong Cangjie avec les formes de caractères de Hong Kong. Japonais (clavier US) fournit Mozc avec une disposition US. Les touches Hangul, Zhuyin et Cangjie gardent leur position standard même avec les lettres latines en Dvorak, Colemak ou AZERTY. Si Hangul ou Chewing est déjà ajouté, désélectionnez-le puis sélectionnez-le à nouveau dans _Configuration > Saisie > Méthodes de saisie_ pour déplacer ses touches ; Omarchy laisse intact un moteur déjà utilisé.

La saisie commence en mode latin. Appuyez sur `Super + I` pour faire défiler les méthodes de saisie configurées, et sur `Super + Shift + I` pour revenir en arrière. Touchez `Shift` seul pour sortir d'une méthode de saisie comme Pinyin vers les lettres latines, et touchez-le à nouveau pour y revenir, comme le font Sogou, Microsoft Pinyin et macOS ; `Shift` plus une lettre tape toujours une majuscule. Sur les claviers japonais, 全角/半角 bascule la saisie, 変換 l'active, et 無変換 la désactive. En coréen, 한/영 bascule Hangul et 한자 convertit en Hanja, qu'il existe des touches dédiées ou que le clavier envoie Right Alt et Right Ctrl comme beaucoup de portables ; ce ne sont donc pas des modificateurs ordinaires ici, et la dictée avec maintien reste sur F9. `Ctrl + Space` reste disponible pour Tmux et Herdr ; `Shift + CapsLock` reste la touche compose.

L'indicateur de clavier apparaît à droite de la barre quand vous avez plusieurs dispositions clavier ou méthodes de saisie. Cliquez dessus pour changer de langue de saisie ; le japonais affiche あ pour les hiragana. Pour les choix de caractères japonais, passez en japonais, tapez un mot comme `nihongo`, puis appuyez deux fois sur Space. Appuyez sur Enter pour accepter votre choix. Si vous avez aussi plusieurs dispositions clavier, faites un clic droit sur l'indicateur pour les faire défiler.

Utilisez _Configuration > Saisie > Dispositions clavier_ pour sélectionner des dispositions comme English et French, parmi les mêmes choix proposés pendant l'installation. Utilisez _Configuration > Saisie > Méthodes de saisie_ pour sélectionner quels moteurs de composition sont actifs. Les deux sélecteurs s'ouvrent dans le menu Omarchy avec vos sélections actuelles cochées. Cliquez ou appuyez sur Enter pour basculer un choix ; chaque changement s'applique immédiatement. Désélectionner une méthode de saisie la retire du cycle sans la désinstaller ; le clavier reste disponible.

Lancez `omarchy setup keyboard` ou `omarchy setup input` pour ouvrir les mêmes sélecteurs. Pour ajouter une langue depuis la ligne de commande, utilisez `omarchy setup input mozc`, `hangul`, `pinyin`, `chewing`, `cangjie5`. Vos touches de bascule personnalisées sont préservées. Pour d'autres dispositions ou touches de moteur, installez `fcitx5-configtool` avec `omarchy pkg add fcitx5-configtool` et lancez-le depuis un terminal. Sélectionner une langue de saisie ne change pas la langue du bureau. Quick, Boshiamy et Array sont fournis dans le même paquet que Cangjie et figurent dans le sélecteur de méthodes de saisie. Choisir japonais, coréen ou chinois dans _Configuration > Langue_ ajoute sa méthode si vous n'en avez pas encore.

Utilisez `Super + I` pour faire défiler les méthodes de saisie ou les dispositions clavier, et `Super + Shift + I` pour aller dans l'autre sens, donc avec trois configurées vous pouvez passer entre deux voisines. L'indicateur de saisie n'apparaît à droite de la barre que quand plus d'une méthode de saisie ou disposition est configurée. Ce raccourci de bureau fonctionne en parallèle de vos touches de bascule Fcitx existantes ; vous pouvez le surcharger dans `~/.config/hypr/bindings.lua`. Les moteurs de saisie et les séquences compose utilisent le service [Fcitx5](https://fcitx-im.org/) qui tourne déjà dans chaque session.

### Utiliser ALT comme SUPER

Sur certains claviers, il n'est pas pratique d'utiliser la touche méta principale (touche Windows/cmd) comme SUPER. Vous pouvez changer cela pour utiliser ALT à la place avec ce changement :

```lua
hl.config({
  input = {
    kb_options = "omarchy:shift_caps_compose,altwin:swap_alt_win",
  },
})
```
