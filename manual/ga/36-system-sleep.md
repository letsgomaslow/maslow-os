# Codladh an chórais

Cumasaíonn Omarchy fionraí agus geimhriú de réir réamhshocraithe, ach má tá fadhbanna agat le ceachtar acu ar do mheaisín, is féidir leat iad a scoránú as.

Ar ríomhairí NVIDIA GB10, mar DGX Spark agus ASUS Ascent GX10, tá fionraí agus suanú múchta, mar atá in NVIDIA DGX OS, toisc nár léiríodh fós go n-oibríonn siad ar an gcrua-earra seo. Ní bhaineann an lasc fionraí ná socrú an tsuanaithe leo. Bain `/etc/systemd/sleep.conf.d/omarchy-sleep-disabled.conf` le `sudo rm` chun iad a chumasú arís; filleann Fionraigh ar an roghchlár agus is féidir suanú a shocrú mar is gnách. Cuireann `sudo omarchy apply hardware --install-user "$USER"` an comhad ar ais.

### Próifílí cumhachta

Ar ríomhaire glúine, cuimhníonn Omarchy do phróifíl chumhachta ar leithligh do plugáilte isteach agus do rith ar cheallra, agus athraíonn sé idir an dá cheann de réir mar a phlugálann agus a dhíphlugálann tú. Díreach as an mbosca ciallaíonn sé sin feidhmíocht ar AC agus cothrom ar cheallra.

Is féidir leat a fheiceáil cad a thairgeann do mheaisín le `omarchy powerprofiles list`, agus an ceann atá uait a shocrú don staid ina bhfuil tú faoi láthair le `omarchy powerprofiles set autodetect power-saver`. Chun an staid eile a shocrú gan aon rud a dhíphlugáil, ainmnigh go díreach é: `omarchy powerprofiles set battery power-saver`. Cibé rud a roghnaíonn tú is é a gheobhaidh tú ar ais an chéad uair eile a bheidh tú sa staid sin.

### Fionraí a scoránú

Scoránaíonn tú fionraí trí `omarchy toggle suspend` a rith ón teirminéal. Ní dhéanann sé sin ach an rogha a nochtadh/a cheilt faoi _Córas_ (nó `Super + Esc`), agus ansin is féidir leat a fheiceáil an n-oibríonn sé go comhsheasmhach ar do chóras. Mura n-oibríonn, is féidir leat é a cheilt arís leis an ordú céanna.

### Geimhriú a scoránú

Socraíonn tú geimhriú trí `omarchy hibernation setup` a rith ón teirminéal. Cruthaíonn geimhriú fo-imleabhar /swap ar do thiomáint tosaithe ar mhéid do leithdháilte RAM fisiciúil, mar sin déan cinnte go bhfuil neart spáis spártha agat. Ar mheaisín 32GB, beidh 32GB+ saor ag teastáil uait i gcónaí don imleabhar seo. Éilíonn geimhriú an luchtóir tosaithe réamhshocraithe Limine freisin.

Nuair a bheidh sé socraithe, feicfidh tú an rogha geimhrigh faoi _Córas_ (nó `Super + Esc`), agus ansin is féidir leat a fheiceáil an n-oibríonn sé go comhsheasmhach ar do chóras. Mura n-oibríonn, is féidir leat é a bhaint arís trí `omarchy hibernation remove` a rith.
