# Spavanje sustava

Omarchy prema zadanim postavkama omogućuje obustavu i hibernaciju, ali ako imate problema s bilo čime od toga na svojem računalu, možete ih isključiti.

Na računalima NVIDIA GB10, kao što su DGX Spark i ASUS Ascent GX10, stanje mirovanja i hibernacija isključeni su kao u NVIDIA DGX OS-u jer njihovo funkcioniranje na tom hardveru još nije dokazano. Prekidač mirovanja i postavljanje hibernacije ovdje se ne primjenjuju. Uklonite `/etc/systemd/sleep.conf.d/omarchy-sleep-disabled.conf` naredbom `sudo rm` da biste ih ponovno omogućili; mirovanje se vraća u izbornik, a hibernacija se može uobičajeno postaviti. `sudo omarchy apply hardware --install-user "$USER"` vraća datoteku.

### Profili napajanja

Na prijenosnom računalu Omarchy pamti vaš profil napajanja odvojeno za priključeno napajanje i rad na bateriji te se prebacuje između njih dok priključujete i isključujete. Odmah po instalaciji to znači performanse na struji i uravnoteženo na bateriji.

Što vaše računalo nudi možete vidjeti s `omarchy powerprofiles list`, a onaj koji želite za trenutačno stanje postaviti s `omarchy powerprofiles set autodetect power-saver`. Za postavljanje drugog stanja bez isključivanja ičega, imenujte ga izravno: `omarchy powerprofiles set battery power-saver`. Što god odaberete, to ćete dobiti natrag sljedeći put kad budete u tom stanju.

### Prebacivanje obustave

Obustavu prebacujete pokretanjem `omarchy toggle suspend` iz terminala. Time se samo otkriva/sakriva opcija pod _Sustav_ (ili `Super + Esc`), a zatim možete vidjeti radi li dosljedno na vašem sustavu. Ako ne, možete je ponovno sakriti istom naredbom.

### Prebacivanje hibernacije

Hibernaciju postavljate pokretanjem `omarchy hibernation setup` iz terminala. Hibernacija stvara podvolumen /swap na vašem pogonu za pokretanje veličine vaše fizičke alokacije RAM-a, pa se pobrinite da imate dovoljno slobodnog prostora. Na računalu s 32GB uvijek će vam trebati 32GB+ slobodno za ovaj volumen. Hibernacija također zahtijeva zadani Limine bootloader.

Kad je postavljena, vidjet ćete opciju hibernacije pod _Sustav_ (ili `Super + Esc`), a zatim možete vidjeti radi li dosljedno na vašem sustavu. Ako ne, možete je ponovno ukloniti pokretanjem `omarchy hibernation remove`.
