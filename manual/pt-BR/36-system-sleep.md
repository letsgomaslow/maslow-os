# Suspensão do sistema

O Omarchy ativa a suspensão e a hibernação por padrão, mas se você estiver tendo problemas com alguma delas na sua máquina, pode desativá-las.

Nos computadores NVIDIA GB10, como DGX Spark e ASUS Ascent GX10, a suspensão e a hibernação estão desativadas, como no NVIDIA DGX OS, pois ainda não foi demonstrado que funcionam nesse hardware. O controle de suspensão e a configuração de hibernação não se aplicam aqui. Remova `/etc/systemd/sleep.conf.d/omarchy-sleep-disabled.conf` com `sudo rm` para reativá-las; Suspender volta ao menu e a hibernação pode ser configurada normalmente. `sudo omarchy apply hardware --install-user "$USER"` recria o arquivo.

### Perfis de energia

Em um notebook, o Omarchy lembra do seu perfil de energia separadamente para quando está conectado à tomada e quando está na bateria, e alterna entre os dois conforme você pluga e despluga. De fábrica, isso significa desempenho na tomada e equilibrado na bateria.

Você pode ver o que sua máquina oferece com `omarchy powerprofiles list` e definir o perfil que quer para o estado em que você está no momento com `omarchy powerprofiles set autodetect power-saver`. Para definir o outro estado sem desplugar nada, nomeie-o diretamente: `omarchy powerprofiles set battery power-saver`. O que você escolher é o que você terá de volta da próxima vez que estiver nesse estado.

### Alternar a suspensão

Você alterna a suspensão executando `omarchy toggle suspend` no terminal. Isso apenas exibe/oculta a opção em _Sistema_ (ou `Super + Esc`), e aí você pode ver se ela funciona de forma consistente no seu sistema. Se não funcionar, você pode ocultá-la de novo com o mesmo comando.

### Alternar a hibernação

Você configura a hibernação executando `omarchy hibernation setup` no terminal. A hibernação cria um subvolume /swap no seu disco de boot do tamanho da sua RAM física, então garanta que você tenha bastante espaço de sobra. Em uma máquina com 32GB, você sempre vai precisar de mais de 32GB livres para esse volume. A hibernação também exige o bootloader Limine padrão.

Depois de configurada, você verá a opção de hibernar em _Sistema_ (ou `Super + Esc`), e aí pode ver se ela funciona de forma consistente no seu sistema. Se não funcionar, você pode removê-la de novo executando `omarchy hibernation remove`.
