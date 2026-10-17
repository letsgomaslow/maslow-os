# Usingizi wa mfumo

Omarchy huwezesha kusitisha (suspend) na kusinzia (hibernation) kwa chaguomsingi, lakini kama unapata matatizo na yoyote kati yao kwenye mashine yako, unaweza kuzizima.

Kwenye kompyuta za NVIDIA GB10 kama DGX Spark na ASUS Ascent GX10, kusinzia na hibernesheni zimezimwa kama katika NVIDIA DGX OS, kwa sababu bado hazijathibitishwa kufanya kazi kwenye vifaa hivi. Swichi ya kusinzia na usanidi wa hibernesheni havitumiki hapa. Ondoa `/etc/systemd/sleep.conf.d/omarchy-sleep-disabled.conf` kwa `sudo rm` kuviwasha tena; Kusinzia hurudi kwenye menyu na hibernesheni inaweza kusanidiwa kawaida. `sudo omarchy apply hardware --install-user "$USER"` hurudisha faili hilo.

### Profaili za nguvu

Kwenye kompyuta mpakato, Omarchy hukumbuka profaili yako ya nguvu kando kwa iliyochomekwa na inayotumia betri, na hubadilisha kati ya hizo mbili unapochomeka na kuchomoa. Mara moja hiyo inamaanisha utendaji kwenye AC na usawaziko kwenye betri.

Unaweza kuona kile mashine yako inachotoa kwa `omarchy powerprofiles list`, na kuweka unachotaka kwa hali uliyo nayo sasa kwa `omarchy powerprofiles set autodetect power-saver`. Kuweka hali nyingine bila kuchomoa chochote, itaje moja kwa moja: `omarchy powerprofiles set battery power-saver`. Chochote unachochagua ndicho utakachopata tena mara utakapokuwa katika hali hiyo.

### Badilisha kusitisha

Unabadilisha kusitisha kwa kuendesha `omarchy toggle suspend` kutoka terminali. Hiyo hufichua/huficha tu chaguo chini ya _Mfumo_ (au `Super + Esc`), na kisha unaweza kuona kama inafanya kazi kwa uthabiti kwenye mfumo wako. Kama sivyo, unaweza kuificha tena kwa amri hiyo hiyo.

### Badilisha kusinzia

Unasanidi kusinzia kwa kuendesha `omarchy hibernation setup` kutoka terminali. Kusinzia huunda subvolume ya /swap kwenye kiendeshaji chako cha kuwasha yenye ukubwa wa ugoaji wako wa RAM halisi, kwa hivyo hakikisha una nafasi nyingi ya ziada. Kwenye mashine ya 32GB, utahitaji kila mara 32GB+ ya bure kwa volume hii. Kusinzia pia kunahitaji bootloader chaguomsingi ya Limine.

Ikiwa imesanidiwa, utaona chaguo la kusinzia chini ya _Mfumo_ (au `Super + Esc`), na kisha unaweza kuona kama inafanya kazi kwa uthabiti kwenye mfumo wako. Kama sivyo, unaweza kuiondoa tena kwa kuendesha `omarchy hibernation remove`.
