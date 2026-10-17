# Kerfissvefn

Omarchy virkjar svefn og dvala sjálfgefið, en ef þú átt í vandræðum með annaðhvort á vélinni þinni geturðu slökkt á þeim.

Á NVIDIA GB10-tölvum, svo sem DGX Spark og ASUS Ascent GX10, eru bið og dvali óvirk eins og í NVIDIA DGX OS, því enn hefur ekki verið sýnt fram á að þau virki á þessum vélbúnaði. Biðrofi og uppsetning dvala eiga ekki við þar. Fjarlægðu `/etc/systemd/sleep.conf.d/omarchy-sleep-disabled.conf` með `sudo rm` til að virkja þau aftur; bið birtist aftur í valmyndinni og hægt er að setja upp dvala eins og venjulega. `sudo omarchy apply hardware --install-user "$USER"` endurheimtir skrána.

### Orkustillingar

Á fartölvu man Omarchy orkustillinguna þína aðskilið fyrir tengingu við rafmagn og keyrslu á rafhlöðu, og skiptir á milli þeirra þegar þú stingur í samband og tekur úr sambandi. Úr kassanum þýðir það afköst á rafmagni og jafnvægi á rafhlöðu.

Þú getur séð hvað vélin þín býður upp á með `omarchy powerprofiles list` og stillt þá sem þú vilt fyrir ástandið sem þú ert í með `omarchy powerprofiles set autodetect power-saver`. Til að stilla hitt ástandið án þess að taka neitt úr sambandi skaltu nefna það beint: `omarchy powerprofiles set battery power-saver`. Það sem þú velur er það sem þú færð til baka næst þegar þú ert í því ástandi.

### Víxla svefni

Þú víxlar svefni með því að keyra `omarchy toggle suspend` úr terminal. Það sýnir/felur bara valkostinn undir _Kerfi_ (eða `Super + Esc`), og þá geturðu séð hvort það virkar stöðugt á kerfinu þínu. Ef ekki geturðu falið það aftur með sömu skipun.

### Víxla dvala

Þú setur upp dvala með því að keyra `omarchy hibernation setup` úr terminal. Dvali býr til /swap undirmagn á ræsidrifi þínu á stærð við raunminni (RAM) þitt, svo gættu þess að þú hafir nægt pláss til vara. Á 32GB vél þarftu alltaf að hafa 32GB+ laust fyrir þetta magn. Dvali krefst líka sjálfgefna Limine ræsiforritsins.

Þegar hann er uppsettur sérðu dvalavalkostinn undir _Kerfi_ (eða `Super + Esc`), og þá geturðu séð hvort hann virkar stöðugt á kerfinu þínu. Ef ekki geturðu fjarlægt hann aftur með því að keyra `omarchy hibernation remove`.
