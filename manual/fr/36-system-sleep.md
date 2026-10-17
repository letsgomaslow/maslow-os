# Veille du système

Omarchy active la suspension et l'hibernation par défaut, mais si l'une ou l'autre pose problème sur votre machine, vous pouvez les désactiver.

Sur les machines NVIDIA GB10 comme DGX Spark et ASUS Ascent GX10, la veille et l’hibernation sont désactivées, comme dans NVIDIA DGX OS, car leur fonctionnement sur ce matériel n’a pas encore été démontré. Le bouton de veille et la configuration de l’hibernation ne s’y appliquent pas. Supprimez `/etc/systemd/sleep.conf.d/omarchy-sleep-disabled.conf` avec `sudo rm` pour les réactiver : la veille revient au menu et l’hibernation se configure normalement. `sudo omarchy apply hardware --install-user "$USER"` recrée le fichier.

### Profils d'alimentation

Sur un portable, Omarchy mémorise votre profil d'alimentation séparément pour le secteur et pour la batterie, et bascule entre les deux quand vous branchez et débranchez. D'emblée, cela signifie performance sur secteur et équilibré sur batterie.

Vous pouvez voir ce que votre machine propose avec `omarchy powerprofiles list`, et définir celui voulu pour l'état dans lequel vous vous trouvez actuellement avec `omarchy powerprofiles set autodetect power-saver`. Pour définir l'autre état sans rien débrancher, nommez-le directement : `omarchy powerprofiles set battery power-saver`. Ce que vous choisissez est ce que vous retrouverez la prochaine fois que vous serez dans cet état.

### Basculer la suspension

Vous basculez la suspension en lançant `omarchy toggle suspend` depuis le terminal. Cela révèle/masque simplement l'option sous _Système_ (ou `Super + Esc`), et vous pouvez ensuite voir si elle fonctionne de façon fiable sur votre système. Si ce n'est pas le cas, vous pouvez la masquer à nouveau avec la même commande.

### Basculer l'hibernation

Vous configurez l'hibernation en lançant `omarchy hibernation setup` depuis le terminal. L'hibernation crée un sous-volume /swap sur votre disque de démarrage de la taille de votre allocation de RAM physique, alors assurez-vous d'avoir largement la place. Sur une machine de 32 Go, il vous faudra toujours plus de 32 Go libres pour ce volume. L'hibernation requiert aussi le chargeur de démarrage Limine par défaut.

Une fois configurée, vous verrez l'option d'hibernation sous _Système_ (ou `Super + Esc`), et vous pouvez ensuite voir si elle fonctionne de façon fiable sur votre système. Si ce n'est pas le cas, vous pouvez la retirer à nouveau en lançant `omarchy hibernation remove`.
