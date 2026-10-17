# Järjestelmän lepotila

Omarchy ottaa lepotilan ja horrostilan käyttöön oletuksena, mutta jos sinulla on ongelmia jommankumman kanssa koneellasi, voit kytkeä ne pois päältä.

NVIDIA GB10 -koneissa, kuten DGX Sparkissa ja ASUS Ascent GX10:ssä, valmius- ja lepotila on poistettu käytöstä kuten NVIDIA DGX OS:ssä, koska niiden toimivuutta tällä laitteistolla ei ole vielä osoitettu. Valmiustilan kytkin ja lepotilan määritys eivät koske näitä koneita. Poista `/etc/systemd/sleep.conf.d/omarchy-sleep-disabled.conf` komennolla `sudo rm` ottaaksesi ne käyttöön; valmiustila palaa valikkoon ja lepotilan voi määrittää normaalisti. `sudo omarchy apply hardware --install-user "$USER"` palauttaa tiedoston.

### Virtaprofiiilit

Kannettavalla Omarchy muistaa virtaprofiilisi erikseen verkkovirralla ja akulla ja vaihtaa niiden välillä kytkiessäsi ja irrottaessasi virtalähteen. Suoraan paketista se tarkoittaa suorituskykyä verkkovirralla ja tasapainotettua tilaa akulla.

Näet koneesi tarjoamat vaihtoehdot komennolla `omarchy powerprofiles list` ja asetat haluamasi nykyiseen tilaasi komennolla `omarchy powerprofiles set autodetect power-saver`. Jos haluat asettaa toisen tilan irrottamatta mitään, nimeä se suoraan: `omarchy powerprofiles set battery power-saver`. Valitsemasi profiili tulee käyttöön seuraavan kerran, kun olet kyseisessä tilassa.

### Lepotilan kytkeminen

Kytket lepotilan ajamalla terminaalissa `omarchy toggle suspend`. Se vain näyttää tai piilottaa vaihtoehdon kohdassa _Järjestelmä_ (tai `Super + Esc`), ja voit sen jälkeen katsoa, toimiiko se järjestelmässäsi johdonmukaisesti. Jos ei toimi, voit piilottaa sen uudelleen samalla komennolla.

### Horrostilan kytkeminen

Asetat horrostilan ajamalla terminaalissa `omarchy hibernation setup`. Horrostila luo /swap-alitiedostojärjestelmän käynnistysasemallesi fyysisen RAM-muistisi kokoisena, joten varmista, että tilaa on reilusti. 32 Gt:n koneella tarvitset aina yli 32 Gt vapaata tilaa tätä osiota varten. Horrostila vaatii myös oletuksena olevan Limine-käynnistyslataimen.

Asetettuasi sen näet horrostila-vaihtoehdon kohdassa _Järjestelmä_ (tai `Super + Esc`), ja voit sen jälkeen katsoa, toimiiko se järjestelmässäsi johdonmukaisesti. Jos ei toimi, voit poistaa sen uudelleen komennolla `omarchy hibernation remove`.
