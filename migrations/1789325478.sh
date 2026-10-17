echo "Install the Omarchy kernel and make it the first Limine boot entry"

# linux-omarchy is an x86_64 kernel. T2 Macs must keep their specialized kernel,
# including when other kernels are installed or the running T2 package is gone.
[[ $(uname -m) == "x86_64" ]] || exit 0
running_kernel=$(uname -r)
if omarchy-pkg-present linux-t2 || [[ ${running_kernel,,} == *-t2* ]]; then
  exit 0
fi

limine_conf="${OMARCHY_KERNEL_LIMINE_CONF:-/etc/default/limine}"
rebuild_marker="${OMARCHY_KERNEL_REBUILD_MARKER:-/var/lib/omarchy/migrations/1789325478}"
kernel="linux-omarchy"

# Completion is machine-wide even though migrations run once per user. Leave
# the old kernel installed so it remains available if the new one cannot boot.
# The new filename and marker also reach users who completed 1789095456.
[[ ! -e $rebuild_marker ]] || exit 0
omarchy-pkg-add "$kernel" "$kernel-headers"

# The requested name can be a fileless meta package (currently selecting BORE).
# Resolve its installed dependency closure to one real, package-owned kernel;
# an unrelated installed variant must not satisfy this migration.
kernel_modules_path="/usr/lib/modules"
packages=$(pactree --unique --linear "$kernel") || exit 1
kernel_names=()
declare -A kernel_paths=()
while IFS= read -r package; do
  [[ -n $package ]] || continue
  package_files=$(pacman -Qql -- "$package") || exit 1
  while IFS= read -r path; do
    [[ $path == "$kernel_modules_path/"*/pkgbase ]] || continue
    kernel_dir=${path%/pkgbase}
    [[ ${kernel_dir%/*} == "$kernel_modules_path" ]] || continue
    [[ -z ${kernel_paths[$path]:-} ]] || continue
    [[ -f $path && -f $kernel_dir/modules.builtin ]] || exit 1
    pkgbase=$(cat "$path") || exit 1
    pkgbase_owner=$(pacman -Qqo -- "$path") || exit 1
    owner=$(pacman -Qqo -- "$kernel_dir/modules.builtin") || exit 1
    if [[ ! $pkgbase =~ ^[a-zA-Z0-9_.+-]+$ || $pkgbase != "$package" || $pkgbase_owner != "$package" || $owner != "$package" ]]; then
      echo "The requested Omarchy kernel has inconsistent package ownership." >&2
      exit 1
    fi
    kernel_paths[$path]=1
    kernel_names+=("$pkgbase")
  done <<<"$package_files"
done <<<"$packages"
if (( ${#kernel_names[@]} != 1 )); then
  echo "The requested Omarchy kernel must resolve to exactly one installed kernel." >&2
  exit 1
fi
resolved_kernel=${kernel_names[0]}
boot_order="$kernel, linux-omarchy-*, *, *fallback, Snapshots"
if [[ $resolved_kernel != "$kernel" ]]; then
  boot_order="$resolved_kernel, $boot_order"
fi

# /etc/default/limine has priority over every drop-in, including old Dell
# settings and customized package files whose updates landed in a .pacnew.
# Set the exact kernel first: linux-omarchy-* only matches its older variants.
# Preserve unrelated settings, especially the root filesystem's kernel cmdline.
sudo mkdir -p "$(dirname "$limine_conf")"
sudo touch "$limine_conf"
sudo sed -i -E '/^[[:space:]]*BOOT_ORDER[[:space:]]*=/d' "$limine_conf"
printf '\nBOOT_ORDER="%s"\n' "$boot_order" | sudo tee -a "$limine_conf" >/dev/null

# Package hooks ran before the config repair. Rebuild the new kernel's image
# and boot entry explicitly, including on retries after a failed rebuild.
sudo limine-mkinitcpio "$resolved_kernel"

# limine-mkinitcpio can return success after skipping a failed kernel build.
# Do not mark the migration complete unless the new kernel is in the menu.
if ! sudo limine-entry-tool --tree | sed -E 's/^[^[:alnum:]_.+-]*//' | grep -Fx -- "$resolved_kernel" >/dev/null; then
  echo "The Omarchy kernel has no Limine boot entry; rerun omarchy-migrate after fixing the boot image build." >&2
  exit 1
fi

# Ask the same shipped configuration reader used by the rebuild for its ESP
# and UKI naming. Do not guess /boot or accept a stale image for another ID.
boot_config=$(sudo bash -ec '
  source /usr/lib/limine/limine-common-functions
  load_config
  prefix=$(cat /etc/machine-id)
  if [[ ${CUSTOM_UKI_NAME:-} =~ ^[a-z0-9]+$ ]]; then
    prefix=$CUSTOM_UKI_NAME
  fi
  printf "%s\n%s\n" "$ESP_PATH" "$prefix"
') || exit 1
mapfile -t boot_values <<<"$boot_config"
if (( ${#boot_values[@]} != 2 )) || [[ ${boot_values[0]} != /* || ! ${boot_values[1]} =~ ^[a-z0-9]+$ ]]; then
  echo "Cannot resolve the Omarchy kernel's UKI location." >&2
  exit 1
fi
uki="${boot_values[0]}/EFI/Linux/${boot_values[1]}_${resolved_kernel}.efi"
if ! sudo test -f "$uki" || ! sudo test -s "$uki"; then
  echo "The Omarchy kernel has no nonempty UKI at $uki; the migration remains pending." >&2
  exit 1
fi

# Keeping the running kernel installed prevents the updater from detecting a
# kernel replacement, so request the reboot explicitly.
omarchy-state set reboot-required
sudo install -Dm644 /dev/null "$rebuild_marker"
