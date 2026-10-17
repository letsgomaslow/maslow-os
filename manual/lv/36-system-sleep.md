# Sistēmas miegs

Omarchy pēc noklusējuma iespējo apturēšanu un ziemas miegu, bet, ja jūsu iekārtā ar kādu no tiem ir problēmas, varat tos izslēgt.

NVIDIA GB10 datoros, piemēram, DGX Spark un ASUS Ascent GX10, miega režīms un hibernācija ir izslēgti tāpat kā NVIDIA DGX OS, jo vēl nav pierādīts, ka tie darbojas šajā aparatūrā. Miega režīma slēdzis un hibernācijas iestatīšana uz tiem neattiecas. Dzēsiet `/etc/systemd/sleep.conf.d/omarchy-sleep-disabled.conf` ar `sudo rm`, lai tos atkal ieslēgtu; miega režīms atgriežas izvēlnē, un hibernāciju var iestatīt kā parasti. `sudo omarchy apply hardware --install-user "$USER"` atjauno failu.

### Jaudas profili

Klēpjdatorā Omarchy atsevišķi atceras jūsu jaudas profilu pie strāvas un uz akumulatora un pārslēdzas starp tiem, kad pievienojat un atvienojat lādētāju. Pēc noklusējuma tas nozīmē veiktspēju pie maiņstrāvas un līdzsvarotu režīmu uz akumulatora.

Ar `omarchy powerprofiles list` varat redzēt, ko jūsu iekārta piedāvā, un ar `omarchy powerprofiles set autodetect power-saver` iestatīt vēlamo pašreizējam stāvoklim. Lai iestatītu otru stāvokli, neko neatvienojot, nosauciet to tieši: `omarchy powerprofiles set battery power-saver`. Ko izvēlēsieties, to arī saņemsiet nākamreiz, kad būsiet šajā stāvoklī.

### Apturēšanas pārslēgšana

Apturēšanu pārslēdzat, terminālī palaižot `omarchy toggle suspend`. Tas vienkārši parāda vai paslēpj opciju sadaļā _Sistēma_ (vai `Super + Esc`), un tad varat pārbaudīt, vai tā jūsu sistēmā darbojas stabili. Ja nē, varat to atkal paslēpt ar to pašu komandu.

### Ziemas miega pārslēgšana

Ziemas miegu iestatāt, terminālī palaižot `omarchy hibernation setup`. Ziemas miegs jūsu sāknēšanas diskā izveido /swap apakšsējumu jūsu fiziskās RAM lielumā, tāpēc pārliecinieties, ka jums ir daudz brīvas vietas. 32GB iekārtā šim sējumam vienmēr vajadzēs 32GB+ brīvas vietas. Ziemas miegam vajadzīgs arī noklusējuma Limine sāknēšanas lādētājs.

Kad tas ir iestatīts, ziemas miega opciju redzēsiet sadaļā _Sistēma_ (vai `Super + Esc`), un tad varat pārbaudīt, vai tā jūsu sistēmā darbojas stabili. Ja nē, varat to atkal noņemt, palaižot `omarchy hibernation remove`.
