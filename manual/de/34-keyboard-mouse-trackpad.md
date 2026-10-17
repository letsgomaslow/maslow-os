# Tastatur, Maus, Trackpad

Hyprland lässt dich alle deine Eingaben im Detail konfigurieren. Du kannst die Tastaturwiederholung überschallschnell machen oder das Trackpad natürliches Scrollen verwenden lassen. Du änderst alles in `~/.config/hypr/input.lua`, das du auch im Omarchy-Menü (`Super + Space`) über _Einrichtung > Eingabe_ erreichst. Alles, was du dort festlegst, ersetzt die Omarchy-Standards.

Hier ist ein Beispiel:

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

Du kannst [alle Eingabeoptionen](https://wiki.hypr.land/Configuring/Basics/Variables/#input) im Hyprland-Wiki für Eingaben sehen.

CapsLock funktioniert als normales Caps Lock, und `Shift + CapsLock` ist die Compose-Taste für [Schnell-Emojis](07-hotkeys.md#quick-emojis) und [andere Vervollständigungen](07-hotkeys.md#quick-completions). Wenn du die Compose-Taste lieber woanders hättest, ersetze `omarchy:shift_caps_compose` in `kb_options`. Dies hier verschiebt die Compose-Taste zum Beispiel auf Right Alt:

```lua
hl.config({
  input = {
    kb_options = "compose:ralt",
  },
})
```

### Trackpad-Gesten

Du kannst auch [Touchpad-Gesten](https://wiki.hypr.land/Configuring/Advanced-and-Cool/Gestures/) einschalten, zum Beispiel mit drei Fingern wischen, um Arbeitsflächen zu wechseln:

```lua
hl.gesture({ fingers = 3, direction = "horizontal", action = "workspace" })
```

Auf Dell-XPS-Laptops mit haptischem Touchpad kannst du unter _Auslösen > Hardware > Touchpad-Haptik_ die Klickstärke auf niedrig, mittel oder hoch einstellen.

### Auf Chinesisch, Japanisch und in anderen Sprachen tippen

Wähle Japanisch, Koreanisch, Chinesisch (vereinfacht, Pinyin), Taiwan (Zhuyin) oder Hongkong (Cangjie), wenn der Installer nach der Tastatur fragt. Omarchy richtet Tastatur und Eingabemethode automatisch ein, auch beim ersten Start ohne Internet. Japanisch nutzt Mozc, Koreanisch Standard-Hangul mit zwei Zeichensätzen, vereinfachtes Chinesisch Pinyin, Taiwan die Standard-Zhuyin-Anordnung von Chewing und Hongkong Cangjie mit Hongkonger Zeichenformen. Japanisch (US-Tastatur) bietet Mozc mit US-Belegung. Hangul-, Zhuyin- und Cangjie-Tasten behalten ihre Standardpositionen, auch wenn du lateinische Buchstaben mit Dvorak, Colemak oder AZERTY tippst. Hast du Hangul oder Chewing schon hinzugefügt, wähle es unter _Einrichtung > Tippen > Eingabemethoden_ ab und wieder an, um die Tasten dorthin zu verschieben; Omarchy lässt eine bereits verwendete Methode unverändert.

Das Tippen beginnt im Latin-Modus. Drücke `Super + I`, um durch die konfigurierten Eingabemethoden zu wechseln, und `Super + Shift + I`, um rückwärts zu wechseln. Tippe `Shift` allein an, um aus einer Eingabemethode wie Pinyin in lateinische Buchstaben auszusteigen, und tippe es erneut an, um zurückzugehen, so wie Sogou, Microsoft Pinyin und macOS funktionieren; `Shift` plus ein Buchstabe gibt weiterhin einen Großbuchstaben ein. Auf japanischen Tastaturen schaltet 全角/半角 die Eingabe um, 変換 schaltet sie ein und 無変換 schaltet sie aus. Bei Koreanisch schaltet 한/영 Hangul um und 한자 wandelt in Hanja um, ob eigene Tasten vorhanden sind oder die Tastatur wie viele Laptops Right Alt und Right Ctrl sendet; deshalb sind sie hier keine gewöhnlichen Modifikatoren, und Diktieren mit gedrückter Taste bleibt auf F9. `Ctrl + Space` bleibt für Tmux und Herdr verfügbar; `Shift + CapsLock` bleibt die Compose-Taste.

Die Tastaturanzeige erscheint rechts in der Leiste, wenn du mehrere Tastaturlayouts oder Eingabemethoden hast. Klicke sie an, um Eingabesprachen zu wechseln; Japanisch zeigt あ für Hiragana. Für die Auswahl japanischer Zeichen wechsle zu Japanisch, tippe ein Wort wie `nihongo` ein und drücke dann zweimal Space. Drücke Enter, um deine Auswahl zu übernehmen. Wenn du zusätzlich mehrere Tastaturlayouts hast, klicke mit der rechten Maustaste auf die Anzeige, um durch diese zu wechseln.

Verwende _Einrichtung > Tippen > Tastaturlayouts_, um Layouts wie English und French auszuwählen, aus denselben Auswahlmöglichkeiten wie während der Installation. Verwende _Einrichtung > Tippen > Eingabemethoden_, um auszuwählen, welche Kompositions-Engines aktiv sind. Beide Auswahlen öffnen sich im Omarchy-Menü mit deinen aktuellen Auswahlmöglichkeiten angekreuzt. Klicke oder drücke Enter, um eine Auswahl umzuschalten; jede Änderung wirkt sofort. Das Abwählen einer Eingabemethode entfernt sie aus dem Zyklus, ohne sie zu deinstallieren; die Tastatur bleibt verfügbar.

Führe `omarchy setup keyboard` oder `omarchy setup input` aus, um dieselben Auswahlen zu öffnen. Um eine Sprache von der Kommandozeile anzuhängen, verwende `omarchy setup input mozc`, `hangul`, `pinyin`, `chewing`, `cangjie5`. Deine benutzerdefinierten Umschalttasten bleiben erhalten. Für alternative Engine-Layouts oder -Tasten installiere `fcitx5-configtool` mit `omarchy pkg add fcitx5-configtool` und starte es von einem Terminal aus. Die Auswahl einer Eingabesprache ändert die Desktop-Sprache nicht. Quick, Boshiamy und Array sind im selben Paket wie Cangjie enthalten und erscheinen in der Eingabemethodenauswahl. Japanisch, Koreanisch oder Chinesisch unter _Einrichtung > Sprache_ fügt die Eingabemethode hinzu, sofern noch keine vorhanden ist.

Verwende `Super + I`, um durch Eingabemethoden oder Tastaturlayouts zu wechseln, und `Super + Shift + I`, um in die andere Richtung zu gehen, sodass du dich bei drei konfigurierten zwischen zwei Nachbarn bewegen kannst. Die Eingabeanzeige erscheint rechts in der Leiste nur, wenn mehr als eine Eingabemethode oder ein Layout konfiguriert ist. Diese Desktop-Bindung funktioniert neben deinen bestehenden Fcitx-Umschalttasten; du kannst sie in `~/.config/hypr/bindings.lua` überschreiben. Die Eingabe-Engines und die Compose-Sequenzen verwenden den Dienst [Fcitx5](https://fcitx-im.org/), der bereits in jeder Sitzung läuft.

### ALT als SUPER verwenden

An einigen Tastaturen ist es unpraktisch, die primäre Meta-Taste (Windows/cmd-Taste) als SUPER zu verwenden. Du kannst dies stattdessen mit dieser Änderung auf ALT umstellen:

```lua
hl.config({
  input = {
    kb_options = "omarchy:shift_caps_compose,altwin:swap_alt_win",
  },
})
```
