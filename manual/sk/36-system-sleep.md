# Spánok systému

Omarchy predvolene povoľuje uspanie a hibernáciu, ale ak máte na svojom stroji s niektorým z nich problémy, môžete ich vypnúť.

Na počítačoch NVIDIA GB10, napríklad DGX Spark a ASUS Ascent GX10, sú uspávanie a hibernácia vypnuté rovnako ako v NVIDIA DGX OS, pretože ich fungovanie na tomto hardvéri ešte nebolo preukázané. Prepínač uspávania a nastavenie hibernácie tu neplatia. Odstráňte `/etc/systemd/sleep.conf.d/omarchy-sleep-disabled.conf` pomocou `sudo rm`, aby ste ich znova povolili; uspávanie sa vráti do ponuky a hibernáciu možno nastaviť bežne. `sudo omarchy apply hardware --install-user "$USER"` súbor obnoví.

### Profily napájania

Na notebooku si Omarchy pamätá váš profil napájania osobitne pre napájanie zo siete a pre prevádzku na batériu a prepína medzi nimi, keď zapájate a odpájate napájanie. Hneď po vybalení to znamená výkon na striedavom napájaní a vyvážený režim na batériu.

To, čo váš stroj ponúka, zistíte príkazom `omarchy powerprofiles list` a ten, ktorý chcete pre stav, v ktorom sa práve nachádzate, nastavíte príkazom `omarchy powerprofiles set autodetect power-saver`. Ak chcete nastaviť druhý stav bez toho, aby ste čokoľvek odpájali, pomenujte ho priamo: `omarchy powerprofiles set battery power-saver`. Čokoľvek vyberiete, to dostanete späť, keď budete nabudúce v tom stave.

### Prepínanie uspania

Uspanie prepnete spustením príkazu `omarchy toggle suspend` z terminálu. Tým sa len zobrazí alebo skryje možnosť v časti _Systém_ (alebo `Super + Esc`) a potom môžete vyskúšať, či na vašom systéme funguje spoľahlivo. Ak nie, môžete ju tým istým príkazom znova skryť.

### Prepínanie hibernácie

Hibernáciu nastavíte spustením príkazu `omarchy hibernation setup` z terminálu. Hibernácia vytvorí na vašom zavádzacom disku podzväzok /swap vo veľkosti vašej fyzickej pamäte RAM, takže dbajte na to, aby ste mali dostatok voľného miesta. Na 32GB stroji budete pre tento zväzok vždy potrebovať voľných 32GB+. Hibernácia si tiež vyžaduje predvolený zavádzač Limine.

Po nastavení uvidíte možnosť hibernácie v časti _Systém_ (alebo `Super + Esc`) a potom môžete vyskúšať, či na vašom systéme funguje spoľahlivo. Ak nie, môžete ju znova odstrániť spustením príkazu `omarchy hibernation remove`.
