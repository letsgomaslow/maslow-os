# Keyboard, Mouse, Trackpad

Hyprland memungkinkan kamu mengonfigurasi semua masukanmu dengan sangat detail. Kamu dapat mengubah pengulangan keyboard menjadi sangat cepat atau membuat trackpad menggunakan pengguliran alami. Kamu mengubah semuanya di `~/.config/hypr/input.lua`, yang juga dapat kamu capai melalui _Pengaturan > Masukan_ di menu Omarchy (`Super + Space`). Apa pun yang kamu atur di sana menggantikan bawaan Omarchy.

Berikut contohnya:

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

Kamu dapat [melihat semua pilihan masukan](https://wiki.hypr.land/Configuring/Basics/Variables/#input) di wiki Hyprland untuk masukan.

CapsLock bekerja sebagai Caps Lock biasa, dan `Shift + CapsLock` adalah tombol compose untuk [emoji cepat](07-hotkeys.md#quick-emojis) dan [pelengkapan lain](07-hotkeys.md#quick-completions). Jika kamu lebih suka tombol compose di tempat lain, ganti `omarchy:shift_caps_compose` di `kb_options`. Misalnya, ini memindahkan tombol compose ke Right Alt:

```lua
hl.config({
  input = {
    kb_options = "compose:ralt",
  },
})
```

### Gerakan trackpad

Kamu juga dapat mengaktifkan [gerakan touchpad](https://wiki.hypr.land/Configuring/Advanced-and-Cool/Gestures/), seperti menggesek dengan tiga jari untuk mengubah ruang kerja:

```lua
hl.gesture({ fingers = 3, direction = "horizontal", action = "workspace" })
```

Pada laptop Dell XPS dengan touchpad haptik, kamu juga dapat mengatur kekuatan klik ke rendah, sedang, atau tinggi di bawah _Pemicu > Perangkat Keras > Haptik Touchpad_.

### Mengetik dalam bahasa Mandarin, Jepang, dan bahasa lainnya

Saat pemasang menanyakan keyboard, pilih Jepang, Korea, Tionghoa (Sederhana, Pinyin), Taiwan (Zhuyin), atau Hong Kong (Cangjie). Omarchy mengatur keyboard dan mesin masukan otomatis, termasuk saat penyiapan awal tanpa jaringan. Jepang memakai Mozc, Korea Hangul standar dua set, Tionghoa Sederhana Pinyin, Taiwan susunan Zhuyin standar Chewing, dan Hong Kong Cangjie dengan bentuk karakter Hong Kong. Jepang (keyboard US) menyediakan Mozc dengan tata letak US. Tombol Hangul, Zhuyin dan Cangjie tetap pada posisi standar meski mengetik Latin dengan Dvorak, Colemak atau AZERTY. Jika sudah menambahkan Hangul atau Chewing, batalkan lalu pilih kembali di _Pengaturan > Pengetikan > Metode Masukan_ agar tombol berpindah; Omarchy tidak mengubah mesin yang sudah dipakai.

Pengetikan dimulai dalam mode Latin. Tekan `Super + I` untuk berputar melalui metode masukan yang dikonfigurasi, dan `Super + Shift + I` untuk berputar kembali. Ketuk `Shift` sendiri untuk keluar dari metode masukan seperti Pinyin ke huruf Latin, dan ketuk lagi untuk kembali, seperti cara Sogou, Microsoft Pinyin, dan macOS bekerja; `Shift` ditambah huruf tetap mengetik huruf kapital. Pada keyboard Jepang, 全角/半角 mengalihkan masukan, 変換 menyalakannya, dan 無変換 mematikannya. Dalam bahasa Korea, 한/영 mengganti Hangul dan 한자 mengonversi ke Hanja, baik memakai tombol khusus maupun keyboard yang mengirim Right Alt dan Right Ctrl seperti banyak laptop; jadi keduanya bukan pengubah biasa di sini, dan dikte tekan-untuk-bicara tetap pada F9. `Ctrl + Space` tetap tersedia untuk Tmux dan Herdr; `Shift + CapsLock` tetap tombol compose.

Indikator keyboard muncul di kanan bilah saat kamu memiliki beberapa tata letak keyboard atau metode masukan. Klik untuk beralih bahasa masukan; Jepang menampilkan あ untuk hiragana. Untuk pilihan karakter Jepang, beralih ke Jepang, ketik kata seperti `nihongo`, kemudian tekan Space dua kali. Tekan Enter untuk menerima pilihanmu. Jika kamu juga memiliki beberapa tata letak keyboard, klik kanan indikator untuk memutarnya.

Gunakan _Pengaturan > Pengetikan > Tata Letak Keyboard_ untuk memilih tata letak seperti Inggris dan Prancis, dari pilihan yang sama yang ditawarkan selama pemasangan. Gunakan _Pengaturan > Pengetikan > Metode Masukan_ untuk memilih mesin komposisi mana yang aktif. Kedua pemilih terbuka di dalam menu Omarchy dengan pilihan saat ini dicentang. Klik atau tekan Enter untuk mengalihkan pilihan; setiap perubahan berlaku segera. Membatalkan pilihan metode masukan menghapusnya dari siklus tanpa mencopotnya; keyboard tetap tersedia.

Jalankan `omarchy setup keyboard` atau `omarchy setup input` untuk membuka pemilih yang sama. Untuk menambahkan satu bahasa dari baris perintah, gunakan `omarchy setup input mozc`, `hangul`, `pinyin`, `chewing`, `cangjie5`. Tombol pengalihan kustommu dipertahankan. Untuk tata letak atau tombol mesin alternatif, pasang `fcitx5-configtool` dengan `omarchy pkg add fcitx5-configtool` dan luncurkan dari terminal. Memilih bahasa masukan tidak mengubah bahasa desktop. Quick, Boshiamy dan Array tersedia dalam paket yang sama dengan Cangjie dan muncul di pemilih metode masukan. Memilih Jepang, Korea atau Tionghoa di _Pengaturan > Bahasa_ menambahkan metode masukan jika belum ada.

Gunakan `Super + I` untuk berputar melalui metode masukan atau tata letak keyboard, dan `Super + Shift + I` untuk kembali ke arah lain, jadi dengan tiga yang dikonfigurasi kamu dapat bergerak di antara dua tetangga. Indikator masukan muncul di kanan bilah hanya saat lebih dari satu metode masukan atau tata letak dikonfigurasi. Ikatan desktop ini bekerja bersama tombol pengalihan Fcitx yang ada; kamu dapat menimpanya di `~/.config/hypr/bindings.lua`. Mesin masukan dan urutan compose menggunakan layanan [Fcitx5](https://fcitx-im.org/) yang sudah berjalan di setiap sesi.

### Gunakan ALT sebagai SUPER

Pada beberapa keyboard, tidak nyaman menggunakan tombol meta primer (tombol Windows/cmd) sebagai SUPER. Kamu dapat mengubah ini menjadi ALT sebagai gantinya menggunakan perubahan ini:

```lua
hl.config({
  input = {
    kb_options = "omarchy:shift_caps_compose,altwin:swap_alt_win",
  },
})
```
